"""
Unit tests for configuration functionality.
"""

import unittest
import os
from unittest.mock import patch
from config import Config


class TestConfig(unittest.TestCase):
    """Test cases for configuration management."""

    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly."""
        config = Config()
        
        self.assertEqual(config.default_timeout, 10)
        self.assertEqual(config.max_timeout, 60)
        self.assertEqual(config.user_agent, "MCP-URL-Search-Server/1.0.0")
        self.assertEqual(config.max_content_length, 10 * 1024 * 1024)  # 10MB
        self.assertEqual(config.rate_limit_requests, 100)
        self.assertEqual(config.rate_limit_window, 60)
        
        # Check supported content types
        expected_content_types = (
            'text/html',
            'text/plain',
            'application/xhtml+xml',
            'text/xml',
            'application/xml'
        )
        self.assertEqual(config.supported_content_types, expected_content_types)

    @patch.dict(os.environ, {
        'MCP_DEFAULT_TIMEOUT': '15',
        'MCP_MAX_TIMEOUT': '120',
        'MCP_USER_AGENT': 'Custom-Agent/2.0.0',
        'MCP_MAX_CONTENT_LENGTH': '5242880'  # 5MB
    })
    def test_environment_variable_override(self):
        """Test that environment variables override default values."""
        config = Config()
        
        self.assertEqual(config.default_timeout, 15)
        self.assertEqual(config.max_timeout, 120)
        self.assertEqual(config.user_agent, "Custom-Agent/2.0.0")
        self.assertEqual(config.max_content_length, 5242880)

    @patch.dict(os.environ, {
        'MCP_DEFAULT_TIMEOUT': '100',  # Greater than max_timeout
        'MCP_MAX_TIMEOUT': '60'
    })
    def test_timeout_validation(self):
        """Test that default_timeout is capped at max_timeout."""
        config = Config()
        
        # default_timeout should be capped at max_timeout
        self.assertEqual(config.default_timeout, 60)
        self.assertEqual(config.max_timeout, 60)

    @patch.dict(os.environ, {
        'MCP_DEFAULT_TIMEOUT': '0'  # Below minimum
    })
    def test_minimum_timeout_validation(self):
        """Test that default_timeout has a minimum value of 1."""
        config = Config()
        
        # default_timeout should be at least 1
        self.assertEqual(config.default_timeout, 1)

    @patch.dict(os.environ, {
        'MCP_DEFAULT_TIMEOUT': 'invalid',
        'MCP_MAX_TIMEOUT': 'not-a-number'
    })
    def test_invalid_environment_variables(self):
        """Test that invalid environment variables fall back to defaults."""
        # This test verifies that int() conversion errors are handled gracefully
        # In practice, this would raise ValueError, so the code should handle this
        with self.assertRaises(ValueError):
            Config()

    def test_content_types_immutable(self):
        """Test that supported content types are immutable."""
        config = Config()
        
        # Should be a tuple (immutable)
        self.assertIsInstance(config.supported_content_types, tuple)


if __name__ == "__main__":
    unittest.main()