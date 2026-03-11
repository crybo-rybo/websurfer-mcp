"""Unit tests for configuration functionality."""

import os
import unittest
from unittest.mock import patch

from websurfer_mcp.config import DEFAULT_SUPPORTED_CONTENT_TYPES, Config


class TestConfig(unittest.TestCase):
    """Test cases for configuration management."""

    def test_default_configuration_values(self):
        """Test that default configuration values are set correctly."""
        config = Config()

        self.assertEqual(config.default_timeout, 10)
        self.assertEqual(config.max_timeout, 60)
        self.assertEqual(config.user_agent, "websurfer-mcp/0.2.0")
        self.assertEqual(config.max_content_length, 10 * 1024 * 1024)
        self.assertEqual(config.rate_limit_requests, 100)
        self.assertEqual(config.rate_limit_window, 60)

        self.assertEqual(config.supported_content_types, DEFAULT_SUPPORTED_CONTENT_TYPES)

    @patch.dict(
        os.environ,
        {
            "MCP_DEFAULT_TIMEOUT": "15",
            "MCP_MAX_TIMEOUT": "120",
            "MCP_USER_AGENT": "Custom-Agent/2.0.0",
            "MCP_MAX_CONTENT_LENGTH": "5242880",
        },
    )
    def test_environment_variable_override(self):
        """Test that environment variables override default values."""
        config = Config()

        self.assertEqual(config.default_timeout, 15)
        self.assertEqual(config.max_timeout, 120)
        self.assertEqual(config.user_agent, "Custom-Agent/2.0.0")
        self.assertEqual(config.max_content_length, 5242880)

    @patch.dict(
        os.environ,
        {
            "MCP_DEFAULT_TIMEOUT": "100",  # Greater than max_timeout
            "MCP_MAX_TIMEOUT": "60",
        },
    )
    def test_timeout_validation(self):
        """Test that default_timeout is capped at max_timeout."""
        config = Config()

        self.assertEqual(config.default_timeout, 60)
        self.assertEqual(config.max_timeout, 60)

    @patch.dict(os.environ, {"MCP_DEFAULT_TIMEOUT": "0"})
    def test_minimum_timeout_validation(self):
        """Test that default_timeout has a minimum value of 1."""
        config = Config()

        self.assertEqual(config.default_timeout, 1)

    @patch.dict(os.environ, {"MCP_DEFAULT_TIMEOUT": "invalid", "MCP_MAX_TIMEOUT": "not-a-number"})
    def test_invalid_environment_variables(self):
        """Test that invalid environment variables fall back to defaults."""
        config = Config()

        self.assertEqual(config.default_timeout, 10)
        self.assertEqual(config.max_timeout, 60)

    def test_content_types_immutable(self):
        """Test that supported content types are immutable."""
        config = Config()

        self.assertIsInstance(config.supported_content_types, tuple)


if __name__ == "__main__":
    unittest.main()
