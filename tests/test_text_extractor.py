"""
Unit tests for text extraction functionality.
"""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from text_extractor import TextExtractor, ExtractionResult


class TestTextExtractor(unittest.TestCase):
    """Test cases for text extraction."""

    def setUp(self):
        """Set up test fixtures."""
        self.extractor = TextExtractor()

    def tearDown(self):
        """Clean up after tests."""
        try:
            asyncio.run(self.extractor.close())
        except Exception as e:
            # Log but don't fail the test for cleanup errors
            print(f"Warning: Error during test cleanup: {e}")

    def test_rate_limiting_check(self):
        """Test rate limiting functionality."""
        # Initially should pass
        self.assertTrue(self.extractor._check_rate_limit())
        
        # Fill up the rate limit
        import time
        current_time = time.time()
        self.extractor.request_times = [current_time] * self.extractor.max_requests_per_minute
        
        # Should now fail rate limit check
        self.assertFalse(self.extractor._check_rate_limit())

    def test_supported_content_types(self):
        """Test content type support detection."""
        supported_types = [
            "text/html",
            "text/plain",
            "application/xhtml+xml",
            "text/xml",
            "application/xml",
            "text/html; charset=utf-8"
        ]
        
        for content_type in supported_types:
            with self.subTest(content_type=content_type):
                self.assertTrue(self.extractor._is_supported_content_type(content_type))

        unsupported_types = [
            "application/json",
            "image/jpeg",
            "video/mp4",
            "application/pdf"
        ]
        
        for content_type in unsupported_types:
            with self.subTest(content_type=content_type):
                self.assertFalse(self.extractor._is_supported_content_type(content_type))

    def test_extract_text_content_plain_text(self):
        """Test text extraction from plain text content."""
        content = "This is plain text content."
        text, title = self.extractor._extract_text_content(content, "text/plain")
        
        self.assertEqual(text, "This is plain text content.")
        self.assertIsNone(title)

    def test_extract_text_content_html_with_title(self):
        """Test text extraction from HTML with title."""
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
        self.assertNotIn("console.log", text)  # Script should be removed
        self.assertNotIn("color: red", text)   # Style should be removed
        self.assertEqual(title, "Test Page")

    def test_extract_text_content_html_no_title(self):
        """Test text extraction from HTML without title."""
        html_content = "<html><body><p>Content without title</p></body></html>"
        
        text, title = self.extractor._extract_text_content(html_content, "text/html")
        
        self.assertIsNotNone(text)
        self.assertIn("Content without title", text)
        self.assertIsNone(title)

    async def test_extract_text_rate_limit_exceeded(self):
        """Test extraction when rate limit is exceeded."""
        # Use context manager for proper cleanup
        async with TextExtractor() as extractor:
            # Fill rate limit
            import time
            current_time = time.time()
            extractor.request_times = [current_time] * extractor.max_requests_per_minute
            
            result = await extractor.extract_text("https://example.com")
            
            self.assertFalse(result.success)
            self.assertIn("Rate limit exceeded", result.error_message)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_404_error(self, mock_get):
        """Test extraction handles 404 errors properly."""
        # Mock 404 response
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_response.headers = {}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com/notfound")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Page not found (404)")
        self.assertEqual(result.status_code, 404)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_403_error(self, mock_get):
        """Test extraction handles 403 errors properly."""
        # Mock 403 response
        mock_response = AsyncMock()
        mock_response.status = 403
        mock_response.headers = {}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com/forbidden")
        
        self.assertFalse(result.success)
        self.assertEqual(result.error_message, "Access forbidden (403)")
        self.assertEqual(result.status_code, 403)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_429_error(self, mock_get):
        """Test extraction handles 429 errors properly."""
        # Mock 429 response
        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.headers = {}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com")
        
        self.assertFalse(result.success)
        self.assertIn("Too many requests", result.error_message)
        self.assertEqual(result.status_code, 429)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_unsupported_content_type(self, mock_get):
        """Test extraction rejects unsupported content types."""
        # Mock response with unsupported content type
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'application/json'}
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://api.example.com/data.json")
        
        self.assertFalse(result.success)
        self.assertIn("Unsupported content type", result.error_message)
        self.assertEqual(result.content_type, "application/json")

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_content_too_large(self, mock_get):
        """Test extraction rejects content that's too large."""
        # Mock response with large content-length
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {
            'content-type': 'text/html',
            'content-length': str(15 * 1024 * 1024)  # 15MB > 10MB limit
        }
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com/large.html")
        
        self.assertFalse(result.success)
        self.assertIn("Content too large", result.error_message)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_success(self, mock_get):
        """Test successful text extraction."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.text.return_value = '<html><head><title>Test</title></head><body><p>Hello World</p></body></html>'
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com")
        
        self.assertTrue(result.success)
        self.assertIsNotNone(result.text_content)
        self.assertIn("Hello World", result.text_content)
        self.assertEqual(result.title, "Test")
        self.assertEqual(result.status_code, 200)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_timeout(self, mock_get):
        """Test extraction handles timeout errors."""
        # Mock timeout
        mock_get.side_effect = asyncio.TimeoutError()
        
        result = await self.extractor.extract_text("https://slow.example.com", timeout=1)
        
        self.assertFalse(result.success)
        self.assertIn("timed out", result.error_message)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_network_error(self, mock_get):
        """Test extraction handles network errors."""
        import aiohttp
        # Mock network error
        mock_get.side_effect = aiohttp.ClientError("Connection failed")
        
        result = await self.extractor.extract_text("https://unreachable.example.com")
        
        self.assertFalse(result.success)
        self.assertIn("Network error", result.error_message)

    @patch('aiohttp.ClientSession.get')
    async def test_extract_text_unicode_decode_error(self, mock_get):
        """Test extraction handles unicode decode errors."""
        # Mock response with decode error
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {'content-type': 'text/html'}
        mock_response.text.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
        mock_get.return_value.__aenter__.return_value = mock_response
        
        result = await self.extractor.extract_text("https://example.com")
        
        self.assertFalse(result.success)
        self.assertIn("Failed to decode content", result.error_message)


# Helper to run async tests
def async_test(f):
    """Decorator to run async test functions."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Apply async_test decorator to all async test methods
for name, method in TestTextExtractor.__dict__.items():
    if name.startswith('test_') and asyncio.iscoroutinefunction(method):
        setattr(TestTextExtractor, name, async_test(method))


if __name__ == "__main__":
    unittest.main()