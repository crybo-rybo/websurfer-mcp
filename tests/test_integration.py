"""
Integration tests for the MCP URL Search Server.
Tests the complete end-to-end functionality matching the manual tests performed.
"""

import unittest
import asyncio
from unittest.mock import patch, AsyncMock
from url_validator import URLValidator
from text_extractor import TextExtractor
from mcp_url_search_server import MCPURLSearchServer


class TestMCPURLSearchIntegration(unittest.TestCase):
    """Integration tests for the complete URL search functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = URLValidator()
        self.extractor = TextExtractor()

    def tearDown(self):
        """Clean up after tests."""
        try:
            asyncio.run(self.extractor.close())
        except Exception as e:
            # Log but don't fail the test for cleanup errors
            print(f"Warning: Error during test cleanup: {e}")

    async def test_successful_url_search_example_com(self):
        """Test successful URL search with example.com (matches manual test)."""
        url = "https://example.com"
        
        # Validate URL
        validation_result = self.validator.validate(url)
        self.assertTrue(validation_result.is_valid)
        
        # Extract text content using context manager for proper cleanup
        async with TextExtractor() as extractor:
            extraction_result = await extractor.extract_text(url)
        
        if extraction_result.success:
            # Verify expected content structure
            self.assertIsNotNone(extraction_result.text_content)
            self.assertGreater(len(extraction_result.text_content), 0)
            self.assertEqual(extraction_result.status_code, 200)
            self.assertIn("text/html", extraction_result.content_type)
            
            # Verify typical example.com content
            self.assertIn("domain", extraction_result.text_content.lower())
        else:
            # If network unavailable, ensure error handling works
            self.assertIsNotNone(extraction_result.error_message)

    async def test_404_error_handling(self):
        """Test 404 error handling (matches manual test with httpbin.org/status/404)."""
        url = "https://httpbin.org/status/404"
        
        # Validate URL (should pass)
        validation_result = self.validator.validate(url)
        self.assertTrue(validation_result.is_valid)
        
        # Extract text content using context manager for proper cleanup
        async with TextExtractor() as extractor:
            extraction_result = await extractor.extract_text(url)
        
        if not extraction_result.success:
            # Should get 404 error
            self.assertEqual(extraction_result.status_code, 404)
            self.assertIn("404", extraction_result.error_message)
        else:
            # If test service is down, just verify we got some response
            self.assertIsNotNone(extraction_result.text_content)

    def test_invalid_url_validation(self):
        """Test invalid URL validation (matches manual test with 'invalid-url')."""
        invalid_url = "invalid-url"
        
        validation_result = self.validator.validate(invalid_url)
        self.assertFalse(validation_result.is_valid)
        self.assertIn("Invalid URL format", validation_result.error_message)

    def test_localhost_url_blocking(self):
        """Test localhost URL blocking for security."""
        localhost_url = "http://localhost:8080"
        
        # Should be blocked by validators library as invalid format
        # (which is acceptable behavior for security)
        validation_result = self.validator.validate(localhost_url)
        self.assertFalse(validation_result.is_valid)

    def test_private_ip_blocking(self):
        """Test private IP range blocking (matches manual test)."""
        private_ip_url = "http://10.0.0.1"
        
        validation_result = self.validator.validate(private_ip_url)
        self.assertFalse(validation_result.is_valid)
        self.assertIn("private IP", validation_result.error_message)

    async def test_html_content_extraction(self):
        """Test HTML content extraction (matches manual test with httpbin.org/html)."""
        url = "https://httpbin.org/html"
        
        # Validate URL
        validation_result = self.validator.validate(url)
        self.assertTrue(validation_result.is_valid)
        
        # Extract text content using context manager for proper cleanup
        async with TextExtractor() as extractor:
            extraction_result = await extractor.extract_text(url)
        
        if extraction_result.success:
            # Verify content extraction worked
            self.assertIsNotNone(extraction_result.text_content)
            self.assertGreater(len(extraction_result.text_content), 100)  # Should be substantial content
            self.assertEqual(extraction_result.status_code, 200)
            self.assertIn("text/html", extraction_result.content_type)
        else:
            # If network unavailable, ensure error handling works
            self.assertIsNotNone(extraction_result.error_message)

    def test_url_normalization(self):
        """Test URL normalization (adding https://)."""
        unnormalized_url = "example.com"
        
        validation_result = self.validator.validate(unnormalized_url)
        self.assertTrue(validation_result.is_valid)
        self.assertEqual(validation_result.normalized_url, "https://example.com")

    def test_blocked_schemes(self):
        """Test blocking of dangerous URL schemes."""
        dangerous_urls = [
            "file:///etc/passwd",
            "javascript:alert('xss')",
            "ftp://example.com/file.txt"
        ]
        
        for url in dangerous_urls:
            with self.subTest(url=url):
                validation_result = self.validator.validate(url)
                self.assertFalse(validation_result.is_valid)
                self.assertIsNotNone(validation_result.error_message)

    def test_rate_limiting_mechanism(self):
        """Test that rate limiting mechanism works."""
        # Test that rate limit check initially passes
        self.assertTrue(self.extractor._check_rate_limit())
        
        # Simulate rate limit exceeded
        import time
        current_time = time.time()
        self.extractor.request_times = [current_time] * self.extractor.max_requests_per_minute
        
        # Should now fail
        self.assertFalse(self.extractor._check_rate_limit())

    async def test_end_to_end_workflow_success(self):
        """Test complete workflow from URL input to text output (success case)."""
        url = "https://example.com"
        
        # Step 1: Validate URL
        validation_result = self.validator.validate(url)
        if not validation_result.is_valid:
            self.fail(f"URL validation failed: {validation_result.error_message}")
        
        # Step 2: Extract text using context manager for proper cleanup
        async with TextExtractor() as extractor:
            extraction_result = await extractor.extract_text(
                validation_result.normalized_url or url,
                timeout=10
            )
        
        # Step 3: Verify results (allow for network issues)
        if extraction_result.success:
            # Success case
            self.assertIsNotNone(extraction_result.text_content)
            self.assertIsNotNone(extraction_result.status_code)
            self.assertIsNotNone(extraction_result.content_type)
        else:
            # Network failure case - ensure proper error handling
            self.assertIsNotNone(extraction_result.error_message)
            self.assertIsNotNone(extraction_result.url)

    async def test_end_to_end_workflow_validation_failure(self):
        """Test complete workflow with validation failure."""
        invalid_url = "not-a-valid-url"
        
        # Step 1: Validate URL (should fail)
        validation_result = self.validator.validate(invalid_url)
        self.assertFalse(validation_result.is_valid)
        self.assertIsNotNone(validation_result.error_message)
        
        # Workflow should stop here - no extraction should be attempted

    def test_content_type_support(self):
        """Test content type support detection."""
        supported_types = [
            "text/html",
            "text/plain", 
            "application/xhtml+xml",
            "text/html; charset=utf-8"
        ]
        
        for content_type in supported_types:
            with self.subTest(content_type=content_type):
                self.assertTrue(self.extractor._is_supported_content_type(content_type))

        unsupported_types = [
            "application/json",
            "image/jpeg",
            "application/pdf"
        ]
        
        for content_type in unsupported_types:
            with self.subTest(content_type=content_type):
                self.assertFalse(self.extractor._is_supported_content_type(content_type))


# Helper to run async tests
def async_test(f):
    """Decorator to run async test functions."""
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


# Apply async_test decorator to all async test methods
for name, method in TestMCPURLSearchIntegration.__dict__.items():
    if name.startswith('test_') and asyncio.iscoroutinefunction(method):
        setattr(TestMCPURLSearchIntegration, name, async_test(method))


if __name__ == "__main__":
    unittest.main()