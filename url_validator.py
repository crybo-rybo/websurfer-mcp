"""
URL validation utilities for the MCP URL Search Server.
"""

import re
import ipaddress
import validators
from urllib.parse import urlparse
from dataclasses import dataclass
from typing import Optional

@dataclass
class ValidationResult:
    """Result of URL validation."""
    is_valid: bool
    error_message: Optional[str] = None
    normalized_url: Optional[str] = None

class URLValidator:
    """Validates and normalizes URLs for safe processing."""
    
    def __init__(self):
        # Blocked schemes for security
        self.blocked_schemes = {'file', 'ftp', 'sftp', 'data', 'javascript'}
        
        # Blocked domains (explicit list)
        self.blocked_domains = {
            'localhost',
            'local'
        }
    
    def validate(self, url: str) -> ValidationResult:
        """
        Validate a URL for safety and accessibility.
        
        Args:
            url: The URL to validate
            
        Returns:
            ValidationResult with validation status and details
        """
        
        if not url:
            return ValidationResult(
                is_valid=False,
                error_message="URL cannot be empty"
            )
        
        # Basic format validation
        if not isinstance(url, str):
            return ValidationResult(
                is_valid=False,
                error_message="URL must be a string"
            )
        
        # Normalize URL (add protocol if missing)
        normalized_url = self._normalize_url(url)
        
        # Use validators library for basic validation
        if not validators.url(normalized_url):
            return ValidationResult(
                is_valid=False,
                error_message="Invalid URL format"
            )
        
        # Parse URL for detailed validation
        try:
            parsed = urlparse(normalized_url)
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                error_message=f"Failed to parse URL: {str(e)}"
            )
        
        # Check scheme
        scheme = parsed.scheme.lower()
        if scheme not in {'http', 'https'}:
            if scheme in self.blocked_schemes:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Blocked scheme: {scheme}"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported scheme: {scheme}. Only HTTP and HTTPS are allowed."
                )
        
        # Check for blocked domains and IP ranges
        hostname = parsed.hostname
        if hostname:
            hostname_lower = hostname.lower()
            
            # 1. Check explicit blocked domains
            if hostname_lower in self.blocked_domains or hostname_lower.endswith('.local'):
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Access to {hostname} is not allowed"
                )
            
            # 2. Check if hostname is an IP address and validate it
            try:
                ip = ipaddress.ip_address(hostname_lower)
                if self._is_blocked_ip(ip):
                    return ValidationResult(
                        is_valid=False,
                        error_message="Access to private or reserved IP ranges is not allowed"
                    )
            except ValueError:
                # Not an IP address, which is fine (it's a domain name)
                pass
        
        # Check URL length
        if len(normalized_url) > 2048:
            return ValidationResult(
                is_valid=False,
                error_message="URL is too long (max 2048 characters)"
            )
        
        return ValidationResult(
            is_valid=True,
            normalized_url=normalized_url
        )
    
    def _is_blocked_ip(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        """Check if an IP address should be blocked."""
        return (
            ip.is_loopback or 
            ip.is_private or 
            ip.is_link_local or 
            ip.is_multicast or 
            ip.is_reserved or
            ip.is_unspecified
        )

    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL by adding protocol if missing.
        
        Args:
            url: Raw URL string
            
        Returns:
            Normalized URL with protocol
        """
        url = url.strip()
        
        # Add https:// if no protocol specified
        if not url.startswith(('http://', 'https://')):
            # Check if it looks like a protocol is specified but malformed
            if '://' in url:
                return url  # Let validation catch the error
            else:
                return f"https://{url}"
        
        return url
