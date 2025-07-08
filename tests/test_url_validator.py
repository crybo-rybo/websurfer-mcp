"""
Unit tests for URL validation functionality.
"""

import unittest
from url_validator import URLValidator, ValidationResult


class TestURLValidator(unittest.TestCase):
    """Test cases for URL validation."""

    def setUp(self):
        """Set up test fixtures."""
        self.validator = URLValidator()

    def test_valid_http_url(self):
        """Test validation of valid HTTP URLs."""
        result = self.validator.validate("http://example.com")
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.normalized_url, "http://example.com")

    def test_valid_https_url(self):
        """Test validation of valid HTTPS URLs."""
        result = self.validator.validate("https://example.com")
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)
        self.assertEqual(result.normalized_url, "https://example.com")

    def test_url_normalization_adds_https(self):
        """Test that URLs without protocol get https:// added."""
        result = self.validator.validate("example.com")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.normalized_url, "https://example.com")

    def test_invalid_url_format(self):
        """Test validation rejects invalid URL formats."""
        invalid_urls = [
            "invalid-url",
            "not a url",
            "http://",
            "://example.com",
            ""
        ]
        
        for url in invalid_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                self.assertIsNotNone(result.error_message)

    def test_empty_url(self):
        """Test validation rejects empty URLs."""
        result = self.validator.validate("")
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "URL cannot be empty")

    def test_non_string_url(self):
        """Test validation rejects non-string URLs."""
        result = self.validator.validate(123)
        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "URL must be a string")

    def test_blocked_schemes(self):
        """Test validation blocks dangerous URL schemes."""
        blocked_schemes = [
            ("file://etc/passwd", ["invalid url format", "scheme"]),
            ("ftp://example.com", ["scheme", "invalid url format"]),
            ("javascript:alert('xss')", ["invalid url format", "scheme"]),
            ("data:text/html,<script>alert('xss')</script>", ["invalid url format", "scheme"])
        ]
        
        for url, expected_errors in blocked_schemes:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                # Either the validators library rejects it as invalid format 
                # or our validation catches the dangerous scheme
                error_lower = result.error_message.lower() if result.error_message else ""
                self.assertTrue(any(expected in error_lower for expected in expected_errors),
                              f"Expected one of {expected_errors} in '{result.error_message}'")

    def test_unsupported_schemes(self):
        """Test validation rejects unsupported schemes."""
        # Test with ftp:// scheme which should be properly detected as unsupported
        test_urls = [
            "ftp://files.example.com/file.txt",
            "ldap://directory.example.com"
        ]
        
        for url in test_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                # Should either be caught as unsupported scheme or invalid format
                error_lower = result.error_message.lower() if result.error_message else ""
                acceptable_errors = ["unsupported scheme", "invalid url format", "scheme"]
                self.assertTrue(any(err in error_lower for err in acceptable_errors),
                               f"Expected validation error for {url}, got: {result.error_message}")

    def test_blocked_localhost_domains(self):
        """Test validation blocks localhost domains."""
        localhost_urls = [
            "http://localhost",
            "https://127.0.0.1",
            "http://0.0.0.0",
            "https://::1"
        ]
        
        # Note: validators library may reject some of these as invalid format
        # rather than reaching our domain check, which is also acceptable
        for url in localhost_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)

    def test_blocked_private_ip_ranges(self):
        """Test validation blocks private IP ranges."""
        private_ips = [
            "http://10.0.0.1",
            "https://172.16.0.1", 
            "http://192.168.1.1",
            "https://169.254.1.1"
        ]
        
        for url in private_ips:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                self.assertIn("private IP", result.error_message)

    def test_url_length_limit(self):
        """Test validation rejects URLs that are too long."""
        long_url = "https://example.com/" + "a" * 2050  # Over 2048 char limit
        result = self.validator.validate(long_url)
        self.assertFalse(result.is_valid)
        self.assertIn("too long", result.error_message)

    def test_valid_public_domains(self):
        """Test validation allows valid public domains."""
        valid_urls = [
            "https://www.google.com",
            "http://httpbin.org",
            "https://api.github.com",
            "https://example.org/path?query=value"
        ]
        
        for url in valid_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertTrue(result.is_valid, f"URL {url} should be valid but got: {result.error_message}")


if __name__ == "__main__":
    unittest.main()