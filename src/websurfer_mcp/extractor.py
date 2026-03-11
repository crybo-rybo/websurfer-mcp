"""Content fetching and text extraction utilities."""

from __future__ import annotations

import asyncio
import logging
import socket
import time
from dataclasses import dataclass

import aiohttp
import trafilatura
from bs4 import BeautifulSoup
from yarl import URL

from .config import Config
from .networking import SafeResolver, UnsafeAddressError
from .url_validation import URLValidator

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExtractionResult:
    """Result of extracting readable text from a URL."""

    success: bool
    text_content: str | None = None
    title: str | None = None
    content_type: str | None = None
    status_code: int | None = None
    error_message: str | None = None
    url: str | None = None


class TextExtractor:
    """Fetch remote content and extract clean text for LLM consumption."""

    redirect_statuses = frozenset({301, 302, 303, 307, 308})

    def __init__(
        self,
        config: Config | None = None,
        validator: URLValidator | None = None,
    ) -> None:
        self.config = config or Config()
        self.validator = validator or URLValidator()
        self.session: aiohttp.ClientSession | None = None
        self._session_created = False
        self.request_times: list[float] = []

    async def _ensure_session(self, timeout: int) -> None:
        """Create an HTTP client session on demand."""

        if self.session is not None:
            return

        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            family=socket.AF_UNSPEC,
            resolver=SafeResolver(self.validator),
            ttl_dns_cache=300,
            use_dns_cache=True,
        )
        timeout_config = aiohttp.ClientTimeout(total=timeout + 5, connect=min(timeout, 10))
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout_config)
        self._session_created = True

    async def extract_text(
        self,
        url: str,
        timeout: int | None = None,
        user_agent: str | None = None,
    ) -> ExtractionResult:
        """Fetch a URL and extract readable text from it."""

        effective_timeout = self._normalize_timeout(timeout)
        validation_result = self.validator.validate(url)
        if not validation_result.is_valid:
            return ExtractionResult(
                success=False,
                error_message=f"Invalid URL - {validation_result.error_message}",
                url=url,
            )

        current_url = validation_result.normalized_url or url
        if not self._check_rate_limit():
            return ExtractionResult(
                success=False,
                error_message="Rate limit exceeded. Please try again later.",
                url=current_url,
            )

        self.request_times.append(time.monotonic())

        try:
            await self._ensure_session(effective_timeout)
            assert self.session is not None

            redirects_followed = 0
            visited_urls: set[str] = set()
            while True:
                if current_url in visited_urls:
                    return ExtractionResult(
                        success=False,
                        error_message="Redirect loop detected",
                        url=current_url,
                    )
                visited_urls.add(current_url)

                async with self.session.get(
                    current_url,
                    headers=self._build_headers(user_agent),
                    timeout=effective_timeout,
                    allow_redirects=False,
                ) as response:
                    redirect_result = self._get_redirect_target(response)
                    if isinstance(redirect_result, ExtractionResult):
                        return redirect_result

                    if redirect_result is not None:
                        if redirects_followed >= self.config.max_redirects:
                            return ExtractionResult(
                                success=False,
                                error_message=(
                                    f"Too many redirects (max {self.config.max_redirects})"
                                ),
                                status_code=response.status,
                                url=current_url,
                            )
                        current_url = redirect_result
                        redirects_followed += 1
                        continue

                    return await self._handle_response(response, current_url)
        except UnsafeAddressError as exc:
            return ExtractionResult(
                success=False,
                error_message=str(exc),
                url=current_url,
            )
        except TimeoutError:
            return ExtractionResult(
                success=False,
                error_message=f"Request timed out after {effective_timeout} seconds",
                url=current_url,
            )
        except aiohttp.ClientConnectorError as exc:
            return ExtractionResult(
                success=False,
                error_message=f"Connection error: {exc}",
                url=current_url,
            )
        except aiohttp.ClientError as exc:
            return ExtractionResult(
                success=False,
                error_message=f"Network error: {exc}",
                url=current_url,
            )
        except Exception as exc:
            logger.exception("Unexpected error extracting text from %s", current_url)
            return ExtractionResult(
                success=False,
                error_message=f"Unexpected error: {exc}",
                url=current_url,
            )

    async def _handle_response(
        self,
        response: aiohttp.ClientResponse,
        url: str,
    ) -> ExtractionResult:
        """Validate and decode an HTTP response before text extraction."""

        status_code = response.status
        content_type = response.headers.get("content-type", "").lower()

        if status_code == 404:
            return ExtractionResult(
                success=False,
                error_message="Page not found (404)",
                status_code=status_code,
                url=url,
            )
        if status_code == 403:
            return ExtractionResult(
                success=False,
                error_message="Access forbidden (403)",
                status_code=status_code,
                url=url,
            )
        if status_code == 429:
            return ExtractionResult(
                success=False,
                error_message="Too many requests (429). Please try again later.",
                status_code=status_code,
                url=url,
            )
        if status_code >= 400:
            return ExtractionResult(
                success=False,
                error_message=f"HTTP error {status_code}",
                status_code=status_code,
                url=url,
            )

        if not self._is_supported_content_type(content_type):
            return ExtractionResult(
                success=False,
                error_message=f"Unsupported content type: {content_type}",
                content_type=content_type,
                status_code=status_code,
                url=url,
            )

        declared_size = response.headers.get("content-length")
        if (
            declared_size
            and declared_size.isdigit()
            and int(declared_size) > self.config.max_content_length
        ):
            return ExtractionResult(
                success=False,
                error_message=(
                    "Content too large "
                    f"(exceeds {self.config.max_content_length / (1024 * 1024):.1f}MB limit)"
                ),
                content_type=content_type,
                status_code=status_code,
                url=url,
            )

        content = await self._read_response_body(response, content_type, status_code, url)
        if isinstance(content, ExtractionResult):
            return content

        extracted_text, title = self._extract_text_content(content, content_type)
        if not extracted_text:
            return ExtractionResult(
                success=False,
                error_message="No readable text content found",
                content_type=content_type,
                status_code=status_code,
                url=url,
            )

        return ExtractionResult(
            success=True,
            text_content=extracted_text,
            title=title,
            content_type=content_type,
            status_code=status_code,
            url=url,
        )

    async def _read_response_body(
        self,
        response: aiohttp.ClientResponse,
        content_type: str,
        status_code: int,
        url: str,
    ) -> str | ExtractionResult:
        """Read and decode the response body while enforcing the configured size limit."""

        content_bytes = bytearray()
        max_size = self.config.max_content_length

        try:
            async for chunk in response.content.iter_any():
                content_bytes.extend(chunk)
                if len(content_bytes) > max_size:
                    return ExtractionResult(
                        success=False,
                        error_message=(
                            f"Content too large (exceeds {max_size / (1024 * 1024):.1f}MB limit)"
                        ),
                        content_type=content_type,
                        status_code=status_code,
                        url=url,
                    )
        except Exception as exc:
            return ExtractionResult(
                success=False,
                error_message=f"Error reading response: {exc}",
                url=url,
            )

        return content_bytes.decode(response.charset or "utf-8", errors="replace")

    def _extract_text_content(
        self, content: str, content_type: str
    ) -> tuple[str | None, str | None]:
        """Extract readable text and an optional title from response content."""

        if "text/plain" in content_type:
            return content.strip(), None

        try:
            soup = BeautifulSoup(content, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else None

            extracted_text = trafilatura.extract(
                content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )
            if extracted_text and len(extracted_text.strip()) > 50:
                return extracted_text.strip(), title

            for element in soup(
                ["script", "style", "meta", "link", "noscript", "header", "footer", "nav"]
            ):
                element.decompose()

            main_content = (
                soup.find("main")
                or soup.find("article")
                or soup.find("div", id="content")
                or soup.body
            )
            if main_content is None:
                return None, title

            text = main_content.get_text(separator="\n\n")
            lines = (line.strip() for line in text.splitlines())
            cleaned_text = "\n".join(line for line in lines if line)
            return (cleaned_text.strip() or None), title
        except Exception as exc:
            logger.warning("Failed to extract text content: %s", exc)
            return None, None

    def _build_headers(self, user_agent: str | None) -> dict[str, str]:
        """Build default request headers."""

        return {
            "User-Agent": user_agent or self.config.user_agent,
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "DNT": "1",
            "Connection": "keep-alive",
        }

    def _get_redirect_target(
        self, response: aiohttp.ClientResponse
    ) -> str | ExtractionResult | None:
        """Validate and normalize the next redirect target, if any."""

        if response.status not in self.redirect_statuses:
            return None

        location = response.headers.get("location")
        if not location:
            return ExtractionResult(
                success=False,
                error_message=f"Redirect response ({response.status}) missing Location header",
                status_code=response.status,
                url=str(response.url),
            )

        try:
            redirect_url = str(response.url.join(URL(location)))
        except ValueError as exc:
            return ExtractionResult(
                success=False,
                error_message=f"Invalid redirect target: {exc}",
                status_code=response.status,
                url=str(response.url),
            )

        validation_result = self.validator.validate(redirect_url)
        if not validation_result.is_valid:
            return ExtractionResult(
                success=False,
                error_message=f"Redirect target blocked: {validation_result.error_message}",
                status_code=response.status,
                url=str(response.url),
            )

        return validation_result.normalized_url or redirect_url

    def _normalize_timeout(self, timeout: int | None) -> int:
        """Clamp timeouts to a valid, configured range."""

        if timeout is None:
            return self.config.default_timeout

        return min(max(int(timeout), 1), self.config.max_timeout)

    def _is_supported_content_type(self, content_type: str) -> bool:
        """Check whether the response content type can be converted into text."""

        return any(
            supported_content_type in content_type
            for supported_content_type in self.config.supported_content_types
        )

    def _check_rate_limit(self) -> bool:
        """Check whether a request fits within the configured sliding window."""

        current_time = time.monotonic()
        self.request_times = [
            request_time
            for request_time in self.request_times
            if current_time - request_time < self.config.rate_limit_window
        ]
        return len(self.request_times) < self.config.rate_limit_requests

    async def close(self) -> None:
        """Close the HTTP session when this extractor owns it."""

        if self.session and self._session_created:
            try:
                await self.session.close()
                await asyncio.sleep(0.1)
            except Exception as exc:
                logger.warning("Error closing session: %s", exc)
            finally:
                self.session = None
                self._session_created = False

    async def __aenter__(self) -> TextExtractor:
        """Enter the async context manager."""

        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit the async context manager and close the session."""

        await self.close()
