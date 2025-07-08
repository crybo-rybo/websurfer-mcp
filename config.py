"""
Configuration settings for the MCP URL Search Server.
"""

import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Config:
    """Configuration class for the URL search server."""
    
    # Default timeout for HTTP requests (seconds)
    default_timeout: int = 10
    
    # Maximum timeout allowed (seconds)
    max_timeout: int = 60
    
    # User agent string for HTTP requests
    user_agent: str = "MCP-URL-Search-Server/1.0.0"
    
    # Maximum content length to process (bytes)
    max_content_length: int = 10 * 1024 * 1024  # 10MB
    
    # Supported content types for text extraction
    supported_content_types: tuple = (
        'text/html',
        'text/plain',
        'application/xhtml+xml',
        'text/xml',
        'application/xml'
    )
    
    # Rate limiting settings
    rate_limit_requests: int = 100  # requests per minute
    rate_limit_window: int = 60     # window in seconds
    
    def __post_init__(self):
        """Post-initialization to override with environment variables."""
        
        # Override with environment variables if present
        self.default_timeout = int(os.getenv("MCP_DEFAULT_TIMEOUT", self.default_timeout))
        self.max_timeout = int(os.getenv("MCP_MAX_TIMEOUT", self.max_timeout))
        self.user_agent = os.getenv("MCP_USER_AGENT", self.user_agent)
        self.max_content_length = int(os.getenv("MCP_MAX_CONTENT_LENGTH", self.max_content_length))
        
        # Validate configuration
        if self.default_timeout > self.max_timeout:
            self.default_timeout = self.max_timeout
        
        if self.default_timeout < 1:
            self.default_timeout = 1
