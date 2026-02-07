# websurfer-mcp

**websurfer-mcp** is a Model Context Protocol (MCP) server that empowers Large Language Models (LLMs) to safely fetch and extract readable text from web pages. It serves as a bridge between an AI assistant and the open web, prioritizing security, content cleanliness, and reliability.

## Project Overview

*   **Language:** Python 3.12+
*   **Core Framework:** Model Context Protocol (MCP)
*   **Key Dependencies:** `mcp`, `aiohttp`, `trafilatura`, `beautifulsoup4`, `validators`
*   **Package Manager:** `uv`

## Architecture

The project is structured around a few core components:

*   **`mcp_url_search_server.py`**: The main server class `MCPURLSearchServer`. It initializes the MCP server, registers the `search_url` tool, and handles incoming requests via standard input/output (stdio).
*   **`text_extractor.py`**: Contains the `TextExtractor` class responsible for making asynchronous HTTP requests and parsing the HTML content into clean, readable text.
*   **`url_validator.py`**: The `URLValidator` class ensures security by blocking local/private IP ranges, unsupported schemes, and malformed URLs.
*   **`run_server.py`**: The CLI entry point. It handles argument parsing and allows running the server in `serve` mode (for MCP clients) or `test` mode (for manual verification).
*   **`config.py`**: Manages configuration settings (timeouts, limits, user agents) via environment variables.

## Building and Running

This project uses `uv` for dependency management and execution.

### Prerequisites

*   Python 3.12 or higher
*   `uv` (Universal Python Package Manager)

### Installation

```bash
# Install dependencies
uv sync
```

### Running the Server

To start the MCP server (communicates via stdio):

```bash
uv run run_server.py serve
```

To run with a custom log level:

```bash
uv run run_server.py serve --log-level DEBUG
```

### Manual Testing (CLI)

You can test the extraction logic directly without an MCP client:

```bash
uv run run_server.py test --url "https://example.com"
```

## Testing

The project has a comprehensive test suite located in the `tests/` directory.

### Run All Tests

```bash
uv run python -m unittest discover tests -v
```

### Run Specific Tests

```bash
# Integration tests
uv run python -m unittest tests.test_integration -v

# Unit tests
uv run python -m unittest tests.test_text_extractor -v
uv run python -m unittest tests.test_url_validator -v
```

## Available Tools

The server exposes a single tool to the connected LLM:

### `search_url`

Fetches and extracts text content from a given URL.

*   **Input:**
    *   `url` (string, required): The valid HTTP/HTTPS URL to visit.
    *   `timeout` (number, optional): Request timeout in seconds (default: 10).
*   **Output:**
    *   Returns the clean text content, content type, status code, and page title.

## Configuration

Configuration is handled via environment variables:

*   `MCP_DEFAULT_TIMEOUT`: Default request timeout (default: 10s).
*   `MCP_MAX_TIMEOUT`: Maximum allowed timeout (default: 60s).
*   `MCP_MAX_CONTENT_LENGTH`: Max content size in bytes (default: 10MB).
*   `MCP_USER_AGENT`: Custom User-Agent string.

## Development Conventions

*   **Asyncio:** The project is fully asynchronous. Use `async/await` for all I/O operations.
*   **Type Hinting:** All functions and methods should have Python type hints.
*   **Security:** Always use `URLValidator` before making any external requests.
*   **Logging:** Use the `logging` module for all output, never `print` (except in CLI test mode).
