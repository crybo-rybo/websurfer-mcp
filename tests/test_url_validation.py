"""Unit tests for URL validation functionality."""

from __future__ import annotations

import unittest

from websurfer_mcp.url_validation import URLValidator


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

    def test_url_normalization_preserves_host_ports(self):
        """Test that host:port inputs without a scheme normalize to HTTPS URLs."""
        result = self.validator.validate("example.com:443/path")
        self.assertTrue(result.is_valid)
        self.assertEqual(result.normalized_url, "https://example.com:443/path")

    def test_invalid_url_format(self):
        """Test validation rejects invalid URL formats."""
        invalid_urls = [
            "invalid-url",
            "not a url",
            "http://",
            "://example.com",
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
            ("file://etc/passwd", "Blocked scheme: file"),
            ("ftp://example.com", "Blocked scheme: ftp"),
            ("javascript:alert('xss')", "Blocked scheme: javascript"),
            ("data:text/html,<script>alert('xss')</script>", "Blocked scheme: data"),
        ]

        for url, expected_error in blocked_schemes:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                self.assertEqual(result.error_message, expected_error)

    def test_unsupported_schemes(self):
        """Test validation rejects unsupported schemes."""
        test_urls = [
            "ldap://directory.example.com",
            "mailto:user@example.com",
        ]

        for url in test_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                self.assertIn("Unsupported scheme", result.error_message)

    def test_blocked_localhost_domains(self):
        """Test validation blocks localhost domains."""
        localhost_urls = [
            "http://localhost",
            "localhost:8080",
            "https://127.0.0.1",
            "http://0.0.0.0",
            "https://::1",
        ]

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
            "https://169.254.1.1",
        ]

        for url in private_ips:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertFalse(result.is_valid)
                self.assertIn("private or reserved IP ranges", result.error_message)

    def test_invalid_port(self):
        """Test validation rejects malformed ports."""
        result = self.validator.validate("https://example.com:bad-port")
        self.assertFalse(result.is_valid)
        self.assertIn("Invalid URL format", result.error_message)

    def test_validate_resolved_ip_rejects_private_ip(self):
        """Test that private DNS answers are rejected."""
        result = self.validator.validate_resolved_ip("example.com", "127.0.0.1")
        self.assertFalse(result.is_valid)
        self.assertIn("127.0.0.1", result.error_message)

    def test_url_length_limit(self):
        """Test validation rejects URLs that are too long."""
        long_url = "https://example.com/" + "a" * 2050
        result = self.validator.validate(long_url)
        self.assertFalse(result.is_valid)
        self.assertIn("too long", result.error_message)

    def test_valid_public_domains(self):
        """Test validation allows valid public domains."""
        valid_urls = [
            "https://www.google.com",
            "http://httpbin.org",
            "https://api.github.com",
            "https://example.org/path?query=value",
        ]

        for url in valid_urls:
            with self.subTest(url=url):
                result = self.validator.validate(url)
                self.assertTrue(
                    result.is_valid,
                    f"URL {url} should be valid but got: {result.error_message}",
                )


if __name__ == "__main__":
    unittest.main()
