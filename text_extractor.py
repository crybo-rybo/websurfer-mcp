"""
Text extraction utilities for the MCP URL Search Server.
"""

import asyncio
import aiohttp
import trafilatura
import logging
from dataclasses import dataclass
from typing import Optional
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

@dataclass
class ExtractionResult:
    """Result of text extraction from a URL."""
    success: bool
    text_content: Optional[str] = None
    title: Optional[str] = None
    content_type: Optional[str] = None
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    url: Optional[str] = None

class TextExtractor:
    """Extracts readable text content from web pages."""
    
    def __init__(self):
        self.session = None
        self._session_created = False
        
        # Rate limiting state
        self.request_times = []
        self.max_requests_per_minute = 60
    
    async def _ensure_session(self, timeout: int = 10):
        """Ensure a session exists, creating one if necessary."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            timeout_config = aiohttp.ClientTimeout(total=timeout)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout_config
            )
            self._session_created = True
    
    async def extract_text(self, url: str, timeout: int = 10, user_agent: str = None) -> ExtractionResult:
        """
        Extract text content from a URL.
        
        Args:
            url: The URL to fetch content from
            timeout: Request timeout in seconds
            user_agent: User agent string for the request
            
        Returns:
            ExtractionResult with extracted content or error details
        """
        
        # Apply rate limiting
        if not self._check_rate_limit():
            return ExtractionResult(
                success=False,
                error_message="Rate limit exceeded. Please try again later.",
                url=url
            )
        
        # Record request time for rate limiting
        self.request_times.append(time.time())
        
        try:
            # Ensure session exists
            await self._ensure_session(timeout)
            
            headers = {
                'User-Agent': user_agent or 'MCP-URL-Search-Server/1.0.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            async with self.session.get(url, headers=headers) as response:
                status_code = response.status
                content_type = response.headers.get('content-type', '').lower()
                
                # Check status code
                if status_code == 404:
                    return ExtractionResult(
                        success=False,
                        error_message="Page not found (404)",
                        status_code=status_code,
                        url=url
                    )
                elif status_code == 403:
                    return ExtractionResult(
                        success=False,
                        error_message="Access forbidden (403)",
                        status_code=status_code,
                        url=url
                    )
                elif status_code == 429:
                    return ExtractionResult(
                        success=False,
                        error_message="Too many requests (429). Please try again later.",
                        status_code=status_code,
                        url=url
                    )
                elif status_code >= 400:
                    return ExtractionResult(
                        success=False,
                        error_message=f"HTTP error {status_code}",
                        status_code=status_code,
                        url=url
                    )
                
                # Check content type
                if not self._is_supported_content_type(content_type):
                    return ExtractionResult(
                        success=False,
                        error_message=f"Unsupported content type: {content_type}",
                        content_type=content_type,
                        status_code=status_code,
                        url=url
                    )
                
                # Check content length
                content_length = response.headers.get('content-length')
                if content_length and int(content_length) > 10 * 1024 * 1024:  # 10MB
                    return ExtractionResult(
                        success=False,
                        error_message="Content too large (>10MB)",
                        content_type=content_type,
                        status_code=status_code,
                        url=url
                    )
                
                # Read content
                try:
                    content = await response.text()
                except UnicodeDecodeError as e:
                    return ExtractionResult(
                        success=False,
                        error_message=f"Failed to decode content: {str(e)}",
                        content_type=content_type,
                        status_code=status_code,
                        url=url
                    )
                
                # Extract text content
                extracted_text, title = self._extract_text_content(content, content_type)
                
                if not extracted_text:
                    return ExtractionResult(
                        success=False,
                        error_message="No readable text content found",
                        content_type=content_type,
                        status_code=status_code,
                        url=url
                    )
                
                return ExtractionResult(
                    success=True,
                    text_content=extracted_text,
                    title=title,
                    content_type=content_type,
                    status_code=status_code,
                    url=url
                )
                
        except asyncio.TimeoutError:
            return ExtractionResult(
                success=False,
                error_message=f"Request timed out after {timeout} seconds",
                url=url
            )
        except aiohttp.ClientError as e:
            return ExtractionResult(
                success=False,
                error_message=f"Network error: {str(e)}",
                url=url
            )
        except Exception as e:
            logger.exception(f"Unexpected error extracting text from {url}")
            return ExtractionResult(
                success=False,
                error_message=f"Unexpected error: {str(e)}",
                url=url
            )
    
    def _extract_text_content(self, content: str, content_type: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract readable text from content based on content type.
        
        Args:
            content: Raw content string
            content_type: MIME type of the content
            
        Returns:
            Tuple of (extracted_text, title)
        """
        
        if 'text/plain' in content_type:
            # Plain text - return as is
            return content.strip(), None
        
        # HTML content - use trafilatura for better extraction
        try:
            # First try trafilatura for clean text extraction
            extracted_text = trafilatura.extract(content)
            
            # Get title using BeautifulSoup
            title = None
            try:
                soup = BeautifulSoup(content, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()
            except Exception:
                pass  # Continue without title if parsing fails
            
            if extracted_text:
                return extracted_text.strip(), title
            
            # Fallback to BeautifulSoup if trafilatura fails
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "meta", "link"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text.strip() if text.strip() else None, title
            
        except Exception as e:
            logger.warning(f"Failed to extract text content: {str(e)}")
            return None, None
    
    def _is_supported_content_type(self, content_type: str) -> bool:
        """Check if content type is supported for text extraction."""
        supported_types = [
            'text/html',
            'text/plain',
            'application/xhtml+xml',
            'text/xml',
            'application/xml'
        ]
        
        return any(supported_type in content_type for supported_type in supported_types)
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        current_time = time.time()
        
        # Remove requests older than 1 minute
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < 60
        ]
        
        # Check if we're under the limit
        return len(self.request_times) < self.max_requests_per_minute
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and self._session_created:
            try:
                # Close the session
                await self.session.close()
                # Wait a bit for connections to close
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.warning(f"Error closing session: {e}")
            finally:
                self.session = None
                self._session_created = False
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
