"""Command-line interface for WebSurfer MCP."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from typing import Any

from .config import Config
from .extractor import TextExtractor
from .server import WebSurferServer
from .url_validation import URLValidator


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="WebSurfer MCP: securely fetch and extract clean text from public URLs.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the application log level.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("serve", help="Run the MCP server over stdio.")

    test_parser = subparsers.add_parser(
        "test", help="Fetch a single URL and print extraction results."
    )
    test_parser.add_argument("--url", required=True, help="The URL to fetch.")
    test_parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Per-request timeout in seconds.",
    )

    return parser


def configure_logging(level: str) -> None:
    """Configure application logging."""

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )


async def test_url_search(url: str, timeout: int = 10) -> dict[str, Any]:
    """Exercise the validation and extraction stack for a single URL."""

    validator = URLValidator()
    validation_result = validator.validate(url)
    if not validation_result.is_valid:
        return {
            "success": False,
            "stage": "validation",
            "error": validation_result.error_message,
            "url": url,
        }

    normalized_url = validation_result.normalized_url or url
    config = Config()
    async with TextExtractor(config=config) as extractor:
        extraction_result = await extractor.extract_text(
            normalized_url,
            timeout=timeout,
            user_agent=config.user_agent,
        )

    if not extraction_result.success:
        return {
            "success": False,
            "stage": "extraction",
            "error": extraction_result.error_message,
            "url": extraction_result.url or normalized_url,
            "status_code": extraction_result.status_code,
            "content_type": extraction_result.content_type,
        }

    preview = extraction_result.text_content or ""
    return {
        "success": True,
        "url": extraction_result.url or normalized_url,
        "title": extraction_result.title,
        "content_type": extraction_result.content_type,
        "status_code": extraction_result.status_code,
        "text_length": len(preview),
        "text_preview": f"{preview[:200]}..." if len(preview) > 200 else preview,
    }


async def run_cli(args: argparse.Namespace) -> int:
    """Dispatch CLI commands."""

    if args.command == "serve":
        await WebSurferServer().run()
        return 0

    if args.command == "test":
        result = await test_url_search(url=args.url, timeout=args.timeout)
        print(json.dumps(result, indent=2))
        return 0 if result["success"] else 1

    raise ValueError(f"Unsupported command: {args.command}")


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous CLI entrypoint."""

    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)
    return asyncio.run(run_cli(args))
