"""
URL validation utilities for the MCP URL Search Server.
"""

import re
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
        
        # Blocked domains (local/private networks)
        self.blocked_domains = {
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '::1'
        }
        
        # Blocked IP ranges (private networks)
        self.blocked_ip_patterns = [
            r'^10\.',                    # 10.0.0.0/8
            r'^172\.(1[6-9]|2[0-9]|3[01])\.',  # 172.16.0.0/12
            r'^192\.168\.',              # 192.168.0.0/16
            r'^169\.254\.',              # 169.254.0.0/16 (link-local)
        ]
    
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
        if parsed.scheme.lower() not in {'http', 'https'}:
            if parsed.scheme.lower() in self.blocked_schemes:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Blocked scheme: {parsed.scheme}"
                )
            else:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Unsupported scheme: {parsed.scheme}. Only HTTP and HTTPS are allowed."
                )
        
        # Check for blocked domains
        hostname = parsed.hostname
        if hostname:
            hostname_lower = hostname.lower()
            
            # Check blocked domains
            if hostname_lower in self.blocked_domains:
                return ValidationResult(
                    is_valid=False,
                    error_message=f"Access to {hostname} is not allowed"
                )
            
            # Check blocked IP ranges
            for pattern in self.blocked_ip_patterns:
                if re.match(pattern, hostname_lower):
                    return ValidationResult(
                        is_valid=False,
                        error_message=f"Access to private IP ranges is not allowed"
                    )
        
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
