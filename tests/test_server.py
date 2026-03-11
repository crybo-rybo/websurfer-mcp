"""Tests for WebSurfer MCP server orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from websurfer_mcp.extractor import ExtractionResult
from websurfer_mcp.server import WebSurferServer


class TestWebSurferServer(unittest.IsolatedAsyncioTestCase):
    """Integration-style tests for the validation and formatting flow."""

    async def asyncSetUp(self):
        self.server = WebSurferServer()

    async def asyncTearDown(self):
        await self.server._cleanup()

    async def test_handle_search_url_requires_url(self):
        result = await self.server.handle_search_url("")
        self.assertEqual(result, "Error: URL parameter is required")

    async def test_handle_search_url_rejects_invalid_timeout(self):
        result = await self.server.handle_search_url("https://example.com", timeout="fast")
        self.assertEqual(result, "Error: timeout must be a positive integer")

    async def test_handle_search_url_rejects_invalid_url(self):
        result = await self.server.handle_search_url("invalid-url")
        self.assertIn("Error: Invalid URL", result)
        self.assertIn("Invalid URL format", result)

    async def test_handle_search_url_formats_success(self):
        extractor = AsyncMock()
        extractor.extract_text = AsyncMock(
            return_value=ExtractionResult(
                success=True,
                text_content="Hello World",
                title="Example",
                content_type="text/html",
                status_code=200,
                url="https://example.com",
            )
        )

        with patch.object(self.server, "_get_extractor", new=AsyncMock(return_value=extractor)):
            result = await self.server.handle_search_url("example.com", timeout=15)

        extractor.extract_text.assert_awaited_once_with(
            "https://example.com",
            timeout=15,
            user_agent=self.server.config.user_agent,
        )
        self.assertIn("Content from: https://example.com", result)
        self.assertIn("Title: Example", result)
        self.assertIn("Hello World", result)

    async def test_handle_search_url_surfaces_extraction_failure(self):
        extractor = AsyncMock()
        extractor.extract_text = AsyncMock(
            return_value=ExtractionResult(
                success=False,
                error_message="Page not found (404)",
                status_code=404,
                url="https://example.com/missing",
            )
        )

        with patch.object(self.server, "_get_extractor", new=AsyncMock(return_value=extractor)):
            result = await self.server.handle_search_url("https://example.com/missing")

        self.assertEqual(
            result,
            "Error fetching content from https://example.com/missing: Page not found (404)",
        )

    async def test_handle_search_url_handles_unexpected_extractor_errors(self):
        with patch.object(
            self.server, "_get_extractor", new=AsyncMock(side_effect=RuntimeError("boom"))
        ):
            result = await self.server.handle_search_url("https://example.com")

        self.assertEqual(result, "Unexpected error: boom")


if __name__ == "__main__":
    unittest.main()
