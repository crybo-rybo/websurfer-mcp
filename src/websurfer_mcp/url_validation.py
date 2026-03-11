"""URL validation utilities for WebSurfer MCP."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlsplit

HOSTNAME_LABEL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?=.{1,63}$)(?!-)[a-z0-9-]{1,63}(?<!-)$",
    re.IGNORECASE,
)
SCHEME_RE: Final[re.Pattern[str]] = re.compile(r"^[a-z][a-z0-9+.-]*:", re.IGNORECASE)


@dataclass(slots=True)
class ValidationResult:
    """Result of validating and normalizing a URL."""

    is_valid: bool
    error_message: str | None = None
    normalized_url: str | None = None


class URLValidator:
    """Validate untrusted URLs before attempting an outbound request."""

    blocked_schemes: Final[set[str]] = {"data", "file", "ftp", "javascript", "sftp"}
    blocked_domains: Final[set[str]] = {"local", "localhost"}

    def validate(self, url: str) -> ValidationResult:
        """Validate a user-provided URL."""

        if url == "":
            return ValidationResult(is_valid=False, error_message="URL cannot be empty")

        if not isinstance(url, str):
            return ValidationResult(is_valid=False, error_message="URL must be a string")

        normalized_url = self._normalize_url(url)
        if not normalized_url:
            return ValidationResult(is_valid=False, error_message="URL cannot be empty")

        if len(normalized_url) > 2048:
            return ValidationResult(
                is_valid=False,
                error_message="URL is too long (max 2048 characters)",
            )

        try:
            parsed = urlsplit(normalized_url)
            _ = parsed.port
        except ValueError as exc:
            return ValidationResult(
                is_valid=False,
                error_message=f"Invalid URL format: {exc}",
            )

        scheme = parsed.scheme.lower()
        if scheme in self.blocked_schemes:
            return ValidationResult(
                is_valid=False,
                error_message=f"Blocked scheme: {scheme}",
            )

        if scheme not in {"http", "https"}:
            return ValidationResult(
                is_valid=False,
                error_message=f"Unsupported scheme: {scheme}. Only HTTP and HTTPS are allowed.",
            )

        hostname = parsed.hostname
        if not parsed.netloc or hostname is None:
            return ValidationResult(is_valid=False, error_message="Invalid URL format")

        hostname = hostname.rstrip(".").lower()
        if hostname in self.blocked_domains or hostname.endswith(".local"):
            return ValidationResult(
                is_valid=False,
                error_message=f"Access to {hostname} is not allowed",
            )

        if self._is_ip_address(hostname):
            ip_address = ipaddress.ip_address(hostname)
            if self._is_blocked_ip(ip_address):
                return ValidationResult(
                    is_valid=False,
                    error_message="Access to private or reserved IP ranges is not allowed",
                )
            return ValidationResult(is_valid=True, normalized_url=normalized_url)

        if not self._is_valid_public_hostname(hostname):
            return ValidationResult(is_valid=False, error_message="Invalid URL format")

        return ValidationResult(is_valid=True, normalized_url=normalized_url)

    def _normalize_url(self, url: str) -> str:
        """Normalize a URL by trimming whitespace and defaulting to HTTPS."""

        normalized_url = url.strip()
        if not normalized_url:
            return ""

        if self._looks_like_host_with_port(normalized_url):
            return f"https://{normalized_url}"

        if SCHEME_RE.match(normalized_url):
            return normalized_url

        if "://" not in normalized_url:
            return f"https://{normalized_url}"

        return normalized_url

    def validate_resolved_ip(self, hostname: str, resolved_ip: str) -> ValidationResult:
        """Validate an IP address returned from DNS resolution."""

        try:
            ip_address = ipaddress.ip_address(resolved_ip)
        except ValueError:
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"DNS resolution for {hostname} returned a non-IP host: {resolved_ip}"
                ),
            )

        if self._is_blocked_ip(ip_address):
            return ValidationResult(
                is_valid=False,
                error_message=(
                    f"Access to resolved address {resolved_ip} for {hostname} is not allowed"
                ),
            )

        return ValidationResult(is_valid=True)

    @staticmethod
    def _is_ip_address(hostname: str) -> bool:
        """Check whether a hostname string is a literal IP address."""

        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            return False
        return True

    @staticmethod
    def _is_blocked_ip(ip_address: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Return True when the IP falls into a non-routable or local-only range."""

        return (
            ip_address.is_loopback
            or ip_address.is_private
            or ip_address.is_link_local
            or ip_address.is_multicast
            or ip_address.is_reserved
            or ip_address.is_unspecified
        )

    def _is_valid_public_hostname(self, hostname: str) -> bool:
        """Apply a conservative hostname validation rule for public internet URLs."""

        if "." not in hostname:
            return False

        labels = hostname.split(".")
        if any(not HOSTNAME_LABEL_RE.fullmatch(label) for label in labels):
            return False

        return not labels[-1].isdigit()

    @staticmethod
    def _looks_like_host_with_port(url: str) -> bool:
        """Detect host:port inputs that should be normalized to HTTPS URLs."""

        if "://" in url or url.startswith("/"):
            return False

        if url.startswith("["):
            return "]:" in url

        if ":" not in url:
            return False

        host, remainder = url.split(":", 1)
        if not host or any(character in host for character in "/?#@"):
            return False

        port = remainder.split("/", 1)[0].split("?", 1)[0].split("#", 1)[0]
        return port.isdigit()
