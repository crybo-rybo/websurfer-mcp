"""
Text extraction utilities for the MCP URL Search Server.
"""

import asyncio
import aiohttp
import trafilatura
import logging
from dataclasses import dataclass
from typing import Optional, Tuple
from bs4 import BeautifulSoup
import time
from config import Config

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
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.session = None
        self._session_created = False
        
        # Rate limiting state
        self.request_times = []
    
    async def _ensure_session(self, timeout: int = 10):
        """Ensure a session exists, creating one if necessary."""
        if self.session is None:
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )
            # We set a slightly longer total timeout for the session to allow for streaming
            timeout_config = aiohttp.ClientTimeout(total=timeout + 5, connect=10)
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
                'User-Agent': user_agent or self.config.user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,text/plain;q=0.8,*/*;q=0.5',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive',
            }
            
            async with self.session.get(url, headers=headers, timeout=timeout) as response:
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
                
                # Read content with size limit enforcement
                try:
                    content_bytes = bytearray()
                    max_size = self.config.max_content_length
                    
                    async for chunk in response.content.iter_any():
                        content_bytes.extend(chunk)
                        if len(content_bytes) > max_size:
                            return ExtractionResult(
                                success=False,
                                error_message=f"Content too large (exceeds {max_size / (1024*1024):.1f}MB limit)",
                                content_type=content_type,
                                status_code=status_code,
                                url=url
                            )
                    
                    # Try to decode content
                    try:
                        # aiohttp usually handles encoding, but we can be more robust
                        content = content_bytes.decode(response.charset or 'utf-8', errors='replace')
                    except Exception as e:
                        return ExtractionResult(
                            success=False,
                            error_message=f"Failed to decode content: {str(e)}",
                            content_type=content_type,
                            status_code=status_code,
                            url=url
                        )
                except Exception as e:
                    return ExtractionResult(
                        success=False,
                        error_message=f"Error reading response: {str(e)}",
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
        except aiohttp.ClientConnectorError as e:
            return ExtractionResult(
                success=False,
                error_message=f"Connection error: {str(e)}",
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
    
    def _extract_text_content(self, content: str, content_type: str) -> Tuple[Optional[str], Optional[str]]:
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
            # Get title using BeautifulSoup
            title = None
            try:
                soup = BeautifulSoup(content, 'html.parser')
                title_tag = soup.find('title')
                if title_tag:
                    title = title_tag.get_text().strip()
            except Exception:
                pass  # Continue without title if parsing fails
            
            # First try trafilatura for clean text extraction
            # We use a more aggressive extraction setting
            extracted_text = trafilatura.extract(
                content, 
                include_comments=False,
                include_tables=True,
                no_fallback=False
            )
            
            if extracted_text and len(extracted_text.strip()) > 50:
                return extracted_text.strip(), title
            
            # Fallback to BeautifulSoup if trafilatura fails or returns too little
            if not title:
                soup = BeautifulSoup(content, 'html.parser')
            
            # Remove script and style elements
            for element in soup(["script", "style", "meta", "link", "noscript", "header", "footer", "nav"]):
                element.decompose()
            
            # Focus on main content if possible
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.body
            
            if main_content:
                # Use get_text with a separator to preserve some structure
                text = main_content.get_text(separator='\n\n')
                
                # Clean up text
                lines = (line.strip() for line in text.splitlines())
                text = '\n'.join(line for line in lines if line)
                
                if text.strip():
                    return text.strip(), title
            
            return None, title
            
        except Exception as e:
            logger.warning(f"Failed to extract text content: {str(e)}")
            return None, None
    
    def _is_supported_content_type(self, content_type: str) -> bool:
        """Check if content type is supported for text extraction."""
        return any(supported_type in content_type for supported_type in self.config.supported_content_types)
    
    def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits."""
        current_time = time.time()
        
        # Remove requests older than the window
        self.request_times = [
            req_time for req_time in self.request_times 
            if current_time - req_time < self.config.rate_limit_window
        ]
        
        # Check if we're under the limit
        return len(self.request_times) < self.config.rate_limit_requests
    
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
