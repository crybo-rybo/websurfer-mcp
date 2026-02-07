#!/usr/bin/env python3
"""
Command-line runner for the MCP URL Search Server.
Provides a simple interface to start and test the server.
"""

import asyncio
import sys
import argparse
import logging
import json
from typing import Dict, Any

from mcp_url_search_server import MCPURLSearchServer
from url_validator import URLValidator
from text_extractor import TextExtractor
from config import Config

def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr)
        ]
    )

async def test_url_search(url: str, timeout: int = 10) -> Dict[str, Any]:
    """
    Test the URL search functionality directly.
    
    Args:
        url: URL to test
        timeout: Request timeout
        
    Returns:
        Dictionary with test results
    """
    
    # Test URL validation
    validator = URLValidator()
    validation_result = validator.validate(url)
    
    if not validation_result.is_valid:
        return {
            "success": False,
            "stage": "validation",
            "error": validation_result.error_message,
            "url": url
        }
    
    # Test text extraction
    config = Config()
    async with TextExtractor(config=config) as extractor:
        try:
            extraction_result = await extractor.extract_text(
                validation_result.normalized_url or url,
                timeout=timeout
            )
            
            if extraction_result.success:
                return {
                    "success": True,
                    "url": extraction_result.url,
                    "title": extraction_result.title,
                    "content_type": extraction_result.content_type,
                    "status_code": extraction_result.status_code,
                    "text_length": len(extraction_result.text_content) if extraction_result.text_content else 0,
                    "text_preview": extraction_result.text_content[:200] + "..." if extraction_result.text_content and len(extraction_result.text_content) > 200 else extraction_result.text_content
                }
            else:
                return {
                    "success": False,
                    "stage": "extraction",
                    "error": extraction_result.error_message,
                    "url": extraction_result.url,
                    "status_code": extraction_result.status_code,
                    "content_type": extraction_result.content_type
                }
                
        except Exception as e:
            return {
                "success": False,
                "stage": "extraction",
                "error": f"Unexpected error: {str(e)}",
                "url": url
            }

async def main():
    """Main entry point for the command-line interface."""
    
    parser = argparse.ArgumentParser(
        description="MCP URL Search Server - Provides LLMs with URL content fetching capabilities"
    )
    
    parser.add_argument(
        "command",
        choices=["serve", "test"],
        help="Command to execute"
    )
    
    parser.add_argument(
        "--url",
        help="URL to test (required for test command)"
    )
    
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    logger = logging.getLogger(__name__)
    
    if args.command == "serve":
        logger.info("Starting MCP URL Search Server...")
        logger.info("Server will communicate via stdio (standard input/output)")
        logger.info("Connect your MCP client to this process to use the URL search tool")
        
        try:
            server = MCPURLSearchServer()
            await server.run()
        except KeyboardInterrupt:
            logger.info("Server stopped by user")
        except Exception as e:
            logger.error(f"Server error: {e}")
            sys.exit(1)
    
    elif args.command == "test":
        if not args.url:
            parser.error("--url is required for test command")
        
        logger.info(f"Testing URL search functionality with: {args.url}")
        
        try:
            result = await test_url_search(args.url, args.timeout)
            
            print("\n" + "="*50)
            print("URL Search Test Results")
            print("="*50)
            print(json.dumps(result, indent=2))
            
            if result["success"]:
                print(f"\n SUCCESS: Extracted {result.get('text_length', 0)} characters of text")
                if result.get("title"):
                    print(f"Title: {result['title']}")
                print(f"Content-Type: {result.get('content_type', 'Unknown')}")
                print(f"Status Code: {result.get('status_code', 'Unknown')}")
            else:
                print(f"\nFAILED at {result.get('stage', 'unknown')} stage")
                print(f"Error: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Test failed with unexpected error: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
