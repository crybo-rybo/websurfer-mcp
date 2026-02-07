"""
MCP Server for URL Search Tool
Provides LLMs with a tool to fetch and return plain-text content from web pages.
"""

import asyncio
import logging
import json
from typing import Any, Sequence
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel
)

from url_validator import URLValidator
from text_extractor import TextExtractor
from config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MCPURLSearchServer:
    """MCP Server that provides URL search functionality for LLMs."""
    
    def __init__(self):
        self.server = Server("url-search-server")
        self.url_validator = URLValidator()
        self.text_extractor = None  # Will be created on demand
        self.config = Config()
        
        # Register handlers
        self._register_handlers()
    
    async def _get_extractor(self) -> TextExtractor:
        """Get or create a text extractor instance."""
        if self.text_extractor is None:
            self.text_extractor = TextExtractor(config=self.config)
        return self.text_extractor
    
    async def _cleanup(self):
        """Clean up resources."""
        if self.text_extractor:
            try:
                await self.text_extractor.close()
            except Exception as e:
                logger.warning(f"Error closing text extractor: {e}")
            finally:
                self.text_extractor = None
    
    def _register_handlers(self):
        """Register MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available tools."""
            return [
                Tool(
                    name="search_url",
                    description="Fetch and return plain-text content from a web page URL. "
                               "Handles various content types and provides comprehensive error handling.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "The URL to fetch content from. Must be a valid HTTP/HTTPS URL."
                            },
                            "timeout": {
                                "type": "number",
                                "description": "Optional timeout in seconds (default: 10)",
                                "default": 10,
                                "minimum": 1,
                                "maximum": 60
                            }
                        },
                        "required": ["url"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            """Handle tool calls."""
            if name != "search_url":
                raise ValueError(f"Unknown tool: {name}")
            
            url = arguments.get("url")
            timeout = arguments.get("timeout", self.config.default_timeout)
            
            if not url:
                return [TextContent(
                    type="text",
                    text="Error: URL parameter is required"
                )]
            
            try:
                # Validate URL
                validation_result = self.url_validator.validate(url)
                if not validation_result.is_valid:
                    return [TextContent(
                        type="text",
                        text=f"Error: Invalid URL - {validation_result.error_message}"
                    )]
                
                # Get extractor and extract text content
                extractor = await self._get_extractor()
                result = await extractor.extract_text(
                    url, 
                    timeout=timeout,
                    user_agent=self.config.user_agent
                )
                
                if result.success:
                    # Prepare response with metadata
                    response_text = f"Content from: {url}\n"
                    response_text += f"Content-Type: {result.content_type}\n"
                    response_text += f"Status Code: {result.status_code}\n"
                    if result.title:
                        response_text += f"Title: {result.title}\n"
                    response_text += "\n--- Content ---\n"
                    response_text += result.text_content
                    
                    return [TextContent(
                        type="text",
                        text=response_text
                    )]
                else:
                    return [TextContent(
                        type="text",
                        text=f"Error fetching content from {url}: {result.error_message}"
                    )]
                    
            except Exception as e:
                logger.exception(f"Unexpected error processing URL {url}")
                return [TextContent(
                    type="text",
                    text=f"Unexpected error: {str(e)}"
                )]
    
    async def run(self):
        """Run the MCP server."""
        logger.info("Starting MCP URL Search Server...")
        
        try:
            # Initialize server with more explicit error handling
            logger.info("Setting up stdio server...")
            async with stdio_server() as (read_stream, write_stream):
                logger.info("Creating initialization options...")
                init_options = InitializationOptions(
                    server_name="url-search-server",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=self.server.notification_options,
                        experimental_capabilities=None
                    )
                )
                
                logger.info("Starting server run...")
                await self.server.run(
                    read_stream,
                    write_stream,
                    init_options
                )
                logger.info("Server run completed")
                
        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            logger.exception("Full traceback:")
            raise
        finally:
            # Ensure cleanup happens
            logger.info("Cleaning up resources...")
            await self._cleanup()
            logger.info("Cleanup completed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._cleanup()

# Main entry point
async def main():
    """Main entry point for the MCP server."""
    server = MCPURLSearchServer()
    try:
        await server.run()
    finally:
        await server._cleanup()

if __name__ == "__main__":
    asyncio.run(main())
