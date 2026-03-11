"""Unit tests for text extraction functionality."""

import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
from yarl import URL

from websurfer_mcp.extractor import TextExtractor
from websurfer_mcp.networking import UnsafeAddressError


def _iter_chunks(*chunks: bytes):
    async def _iterator():
        for chunk in chunks:
            yield chunk

    return _iterator()


def _mock_response(
    *,
    status: int = 200,
    headers: dict[str, str] | None = None,
    charset: str = "utf-8",
    chunks: tuple[bytes, ...] = (b"",),
    url: str = "https://example.com",
) -> AsyncMock:
    response = AsyncMock()
    response.status = status
    response.headers = headers or {}
    response.charset = charset
    response.content.iter_any = MagicMock(return_value=_iter_chunks(*chunks))
    response.url = URL(url)
    return response


def _mock_request_context(response: AsyncMock) -> AsyncMock:
    context = AsyncMock()
    context.__aenter__.return_value = response
    context.__aexit__.return_value = False
    return context


class TestTextExtractor(unittest.TestCase):
    """Synchronous tests for helper methods."""

    def setUp(self):
        self.extractor = TextExtractor()

    def test_rate_limiting_check(self):
        self.assertTrue(self.extractor._check_rate_limit())

        current_time = time.monotonic()
        self.extractor.request_times = [current_time] * self.extractor.config.rate_limit_requests
        self.assertFalse(self.extractor._check_rate_limit())

    def test_supported_content_types(self):
        supported_types = [
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "text/xml",
            "application/xml",
            "text/html; charset=utf-8",
        ]
        for content_type in supported_types:
            with self.subTest(content_type=content_type):
                self.assertTrue(self.extractor._is_supported_content_type(content_type))

        unsupported_types = [
            "application/json",
            "image/jpeg",
            "video/mp4",
            "application/pdf",
        ]
        for content_type in unsupported_types:
            with self.subTest(content_type=content_type):
                self.assertFalse(self.extractor._is_supported_content_type(content_type))

    def test_extract_text_content_plain_text(self):
        text, title = self.extractor._extract_text_content(
            "This is plain text content.", "text/plain"
        )
        self.assertEqual(text, "This is plain text content.")
        self.assertIsNone(title)

    def test_extract_text_content_html_with_title(self):
        html_content = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <h1>Main Heading</h1>
            <p>This is a paragraph with some text.</p>
            <script>console.log('should be removed');</script>
            <style>body { color: red; }</style>
        </body>
        </html>
        """

        text, title = self.extractor._extract_text_content(html_content, "text/html")
        self.assertIsNotNone(text)
        self.assertIn("Main Heading", text)
        self.assertIn("paragraph with some text", text)
        self.assertNotIn("console.log", text)
        self.assertNotIn("color: red", text)
        self.assertEqual(title, "Test Page")

    def test_extract_text_content_html_no_title(self):
        text, title = self.extractor._extract_text_content(
            "<html><body><p>Content without title</p></body></html>",
            "text/html",
        )
        self.assertIsNotNone(text)
        self.assertIn("Content without title", text)
        self.assertIsNone(title)


class TestTextExtractorAsync(unittest.IsolatedAsyncioTestCase):
    """Async tests for HTTP interactions and error handling."""

    async def asyncSetUp(self):
        self.extractor = TextExtractor()

    async def asyncTearDown(self):
        await self.extractor.close()

    async def test_extract_text_rate_limit_exceeded(self):
        current_time = time.monotonic()
        self.extractor.request_times = [current_time] * self.extractor.config.rate_limit_requests

        result = await self.extractor.extract_text("https://example.com")
        self.assertFalse(result.success)
        self.assertIn("Rate limit exceeded", result.error_message)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_404_error(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(status=404)

        result = await self.extractor.extract_text("https://example.com/notfound")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Page not found (404)")
        self.assertEqual(result.status_code, 404)
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_403_error(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(status=403)

        result = await self.extractor.extract_text("https://example.com/forbidden")
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Access forbidden (403)")
        self.assertEqual(result.status_code, 403)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_429_error(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(status=429)

        result = await self.extractor.extract_text("https://example.com")
        self.assertFalse(result.success)
        self.assertIn("Too many requests", result.error_message)
        self.assertEqual(result.status_code, 429)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_unsupported_content_type(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(
            headers={"content-type": "application/json"},
        )

        result = await self.extractor.extract_text("https://api.example.com/data.json")
        self.assertFalse(result.success)
        self.assertIn("Unsupported content type", result.error_message)
        self.assertEqual(result.content_type, "application/json")

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_declared_content_too_large(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(
            headers={
                "content-type": "text/html",
                "content-length": str(11 * 1024 * 1024),
            },
        )

        result = await self.extractor.extract_text("https://example.com/large.html")
        self.assertFalse(result.success)
        self.assertIn("Content too large", result.error_message)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_streamed_content_too_large(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(
            headers={"content-type": "text/html"},
            chunks=(b"a" * (11 * 1024 * 1024),),
        )

        result = await self.extractor.extract_text("https://example.com/large.html")
        self.assertFalse(result.success)
        self.assertIn("Content too large", result.error_message)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_success(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(
            headers={"content-type": "text/html"},
            chunks=(
                b"<html><head><title>Test</title></head><body><p>Hello World</p></body></html>",
            ),
        )

        result = await self.extractor.extract_text("https://example.com")
        self.assertTrue(result.success)
        self.assertIsNotNone(result.text_content)
        self.assertIn("Hello World", result.text_content)
        self.assertEqual(result.title, "Test")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(mock_get.call_args.kwargs["allow_redirects"])

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_timeout(self, mock_get):
        mock_get.side_effect = TimeoutError()

        result = await self.extractor.extract_text("https://slow.example.com", timeout=1)
        self.assertFalse(result.success)
        self.assertIn("timed out", result.error_message)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_network_error(self, mock_get):
        mock_get.side_effect = aiohttp.ClientConnectorError(MagicMock(), OSError(1, "boom"))

        result = await self.extractor.extract_text("https://unreachable.example.com")
        self.assertFalse(result.success)
        self.assertIn("Connection error", result.error_message)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_unicode_decode_error(self, mock_get):
        mock_get.return_value.__aenter__.return_value = _mock_response(
            headers={"content-type": "text/html"},
            chunks=(b"<html><body><p>Valid text " + b"\xff\xfe\xfd" + b"</p></body></html>",),
        )

        result = await self.extractor.extract_text("https://example.com")
        self.assertTrue(result.success)
        self.assertIn("Valid text", result.text_content)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_rejects_invalid_initial_url(self, mock_get):
        result = await self.extractor.extract_text("localhost:8080")

        self.assertFalse(result.success)
        self.assertIn("Invalid URL", result.error_message)
        mock_get.assert_not_called()

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_follows_safe_redirects(self, mock_get):
        redirect_response = _mock_response(
            status=302,
            headers={"location": "/final"},
            url="https://example.com/start",
        )
        final_response = _mock_response(
            status=200,
            headers={"content-type": "text/html"},
            chunks=(b"<html><body><p>Redirected</p></body></html>",),
            url="https://example.com/final",
        )
        mock_get.side_effect = [
            _mock_request_context(redirect_response),
            _mock_request_context(final_response),
        ]

        result = await self.extractor.extract_text("https://example.com/start")

        self.assertTrue(result.success)
        self.assertEqual(result.url, "https://example.com/final")
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(mock_get.call_args_list[1].args[0], "https://example.com/final")
        for call in mock_get.call_args_list:
            self.assertFalse(call.kwargs["allow_redirects"])

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_blocks_unsafe_redirect_target(self, mock_get):
        redirect_response = _mock_response(
            status=302,
            headers={"location": "http://127.0.0.1/private"},
            url="https://example.com/start",
        )
        mock_get.side_effect = [_mock_request_context(redirect_response)]

        result = await self.extractor.extract_text("https://example.com/start")

        self.assertFalse(result.success)
        self.assertIn("Redirect target blocked", result.error_message)
        self.assertEqual(mock_get.call_count, 1)

    @patch("aiohttp.ClientSession.get")
    async def test_extract_text_handles_unsafe_resolver_error(self, mock_get):
        mock_get.side_effect = UnsafeAddressError(
            "Access to resolved address 127.0.0.1 for example.com is not allowed"
        )

        result = await self.extractor.extract_text("https://example.com")

        self.assertFalse(result.success)
        self.assertIn("127.0.0.1", result.error_message)


if __name__ == "__main__":
    unittest.main()
