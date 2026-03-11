"""Configuration management for WebSurfer MCP."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Final

logger = logging.getLogger(__name__)

DEFAULT_SUPPORTED_CONTENT_TYPES: Final[tuple[str, ...]] = (
    "text/html",
    "text/plain",
    "application/xhtml+xml",
    "text/xml",
    "application/xml",
)


def _read_int_env(name: str, default: int) -> int:
    """Read an integer environment variable, falling back to the default on errors."""

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        return int(raw_value)
    except ValueError:
        logger.warning("Ignoring invalid integer value for %s: %r", name, raw_value)
        return default


@dataclass(slots=True)
class Config:
    """Runtime configuration for the WebSurfer MCP server."""

    default_timeout: int = 10
    max_timeout: int = 60
    max_redirects: int = 10
    user_agent: str = "websurfer-mcp/0.2.0"
    max_content_length: int = 10 * 1024 * 1024
    supported_content_types: tuple[str, ...] = DEFAULT_SUPPORTED_CONTENT_TYPES
    rate_limit_requests: int = 100
    rate_limit_window: int = 60

    def __post_init__(self) -> None:
        """Apply environment variable overrides and normalize settings."""

        self.default_timeout = _read_int_env("MCP_DEFAULT_TIMEOUT", self.default_timeout)
        self.max_timeout = _read_int_env("MCP_MAX_TIMEOUT", self.max_timeout)
        self.max_redirects = _read_int_env("MCP_MAX_REDIRECTS", self.max_redirects)
        self.user_agent = os.getenv("MCP_USER_AGENT", self.user_agent)
        self.max_content_length = _read_int_env(
            "MCP_MAX_CONTENT_LENGTH",
            self.max_content_length,
        )

        self.max_timeout = max(self.max_timeout, 1)
        self.default_timeout = min(max(self.default_timeout, 1), self.max_timeout)
        self.max_redirects = max(self.max_redirects, 0)
        self.max_content_length = max(self.max_content_length, 1)
        self.rate_limit_requests = max(self.rate_limit_requests, 1)
        self.rate_limit_window = max(self.rate_limit_window, 1)
