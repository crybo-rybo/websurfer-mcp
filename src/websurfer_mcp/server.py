"""MCP server wiring for WebSurfer."""

from __future__ import annotations

import asyncio
import logging

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from ._version import __version__
from .config import Config
from .extractor import ExtractionResult, TextExtractor
from .url_validation import URLValidator

logger = logging.getLogger(__name__)


class WebSurferServer:
    """MCP server that exposes a single `search_url` tool."""

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config()
        self.server = Server("websurfer-mcp")
        self.url_validator = URLValidator()
        self.text_extractor: TextExtractor | None = None
        self._register_handlers()

    async def _get_extractor(self) -> TextExtractor:
        """Get or create the shared text extractor instance."""

        if self.text_extractor is None:
            self.text_extractor = TextExtractor(config=self.config)
        return self.text_extractor

    async def handle_search_url(self, url: str, timeout: int | None = None) -> str:
        """Run the full validate-fetch-extract flow for a single URL."""

        if not url:
            return "Error: URL parameter is required"

        try:
            effective_timeout = (
                self.config.default_timeout
                if timeout is None
                else min(max(int(timeout), 1), self.config.max_timeout)
            )
        except (TypeError, ValueError):
            return "Error: timeout must be a positive integer"

        validation_result = self.url_validator.validate(url)
        if not validation_result.is_valid:
            return f"Error: Invalid URL - {validation_result.error_message}"

        normalized_url = validation_result.normalized_url or url

        try:
            extractor = await self._get_extractor()
            extraction_result = await extractor.extract_text(
                normalized_url,
                timeout=effective_timeout,
                user_agent=self.config.user_agent,
            )
        except Exception as exc:
            logger.exception("Unexpected error processing URL %s", normalized_url)
            return f"Unexpected error: {exc}"

        if not extraction_result.success:
            return (
                f"Error fetching content from {normalized_url}: {extraction_result.error_message}"
            )

        return self._format_success_response(normalized_url, extraction_result)

    def _format_success_response(
        self,
        normalized_url: str,
        extraction_result: ExtractionResult,
    ) -> str:
        """Render a successful tool result as plain text."""

        lines = [
            f"Content from: {normalized_url}",
            f"Content-Type: {extraction_result.content_type}",
            f"Status Code: {extraction_result.status_code}",
        ]
        if extraction_result.title:
            lines.append(f"Title: {extraction_result.title}")

        lines.append("")
        lines.append("--- Content ---")
        lines.append(extraction_result.text_content or "")
        return "\n".join(lines)

    def _register_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            return [
                Tool(
                    name="search_url",
                    description=(
                        "Fetch and return plain-text content from a public web page URL. "
                        "Supports HTML and plain text and applies strict URL safety validation."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "url": {
                                "type": "string",
                                "description": "A valid public HTTP or HTTPS URL.",
                            },
                            "timeout": {
                                "type": "integer",
                                "description": "Optional timeout in seconds.",
                                "default": self.config.default_timeout,
                                "minimum": 1,
                                "maximum": self.config.max_timeout,
                            },
                        },
                        "required": ["url"],
                    },
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            if name != "search_url":
                raise ValueError(f"Unknown tool: {name}")

            response_text = await self.handle_search_url(
                url=arguments.get("url", ""),
                timeout=arguments.get("timeout"),
            )
            return [TextContent(type="text", text=response_text)]

    async def run(self) -> None:
        """Run the MCP server over stdio."""

        logger.info("Starting WebSurfer MCP server")
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="websurfer-mcp",
                        server_version=__version__,
                        capabilities=self.server.get_capabilities(
                            notification_options=self.server.notification_options,
                            experimental_capabilities=None,
                        ),
                    ),
                )
        finally:
            await self._cleanup()

    async def _cleanup(self) -> None:
        """Release extractor resources."""

        if self.text_extractor is None:
            return

        try:
            await self.text_extractor.close()
        except Exception as exc:
            logger.warning("Error closing text extractor: %s", exc)
        finally:
            self.text_extractor = None

    async def __aenter__(self) -> WebSurferServer:
        """Enter the async context manager."""

        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Exit the async context manager and clean up."""

        await self._cleanup()


MCPURLSearchServer = WebSurferServer


async def main() -> None:
    """Async package entrypoint."""

    server = WebSurferServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
