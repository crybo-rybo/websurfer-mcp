# WebSurfer MCP

WebSurfer is a Model Context Protocol (MCP) server designed to provide Large Language Models (LLMs) with secure and efficient access to web content. It enables AI assistants to fetch, parse, and extract clean text from web pages through a standardized interface.

## Core Features

- **Advanced URL Validation**: Implements strict security controls using the `ipaddress` module to block access to private, loopback, and reserved IP ranges (SSRF protection).
- **Optimized Content Extraction**: Utilizes `trafilatura` and `BeautifulSoup4` to extract high-quality, readable text from HTML, effectively removing boilerplate such as navigation, headers, and scripts.
- **Resource Management**: Enforces strict content size limits and request timeouts to ensure system stability and performance.
- **Rate Limiting**: Built-in request throttling to prevent service abuse and manage resource consumption.
- **Robust Error Handling**: Provides granular feedback for network issues, HTTP errors, and content parsing failures.

## System Architecture

The project is composed of several specialized components:

- **MCPURLSearchServer**: The primary server implementation that handles the MCP lifecycle and tool registration.
- **TextExtractor**: Manages asynchronous HTTP sessions and content parsing logic.
- **URLValidator**: Performs security auditing and normalization on input URLs.
- **Config**: Centralizes configuration management via environment variables.

## Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/crybo-rybo/websurfer-mcp
   cd websurfer-mcp
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

## Usage

### Server Execution

The server communicates via standard I/O (stdio) and is compatible with any MCP-compliant client.

```bash
uv run run_server.py serve
```

### Manual Testing

You can verify the extraction functionality directly from the command line:

```bash
uv run run_server.py test --url "https://example.com"
```

## Desktop Client Integration

### Claude Desktop

To use WebSurfer MCP with Claude Desktop, add the following configuration to your `claude_desktop_config.json` file.

**Path locations:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

**Configuration:**

Replace `/path/to/websurfer-mcp` with the absolute path to your cloned repository.

```json
{
  "mcpServers": {
    "websurfer": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/websurfer-mcp",
        "run",
        "run_server.py",
        "serve"
      ]
    }
  }
}
```

After updating the configuration, restart Claude Desktop to enable the `search_url` tool.

## Configuration

The server can be configured using the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_DEFAULT_TIMEOUT` | `10` | Default request timeout in seconds. |
| `MCP_MAX_TIMEOUT` | `60` | Maximum allowed timeout in seconds. |
| `MCP_USER_AGENT` | `MCP-URL-Search-Server/1.0.0` | User-Agent string for outgoing requests. |
| `MCP_MAX_CONTENT_LENGTH` | `10485760` | Maximum content size in bytes (default 10MB). |

## Testing

The project maintains a comprehensive test suite covering unit and integration scenarios.

### Execute All Tests

```bash
uv run python -m unittest discover tests -v
```

### Component Testing

```bash
# Integration tests
uv run python -m unittest tests.test_integration -v

# URL validation tests
uv run python -m unittest tests.test_url_validator -v
```

## Security

WebSurfer MCP is designed with security as a primary concern. It explicitly blocks:
- Private IP ranges (e.g., 10.0.0.0/8, 192.168.0.0/16)
- Loopback addresses (e.g., 127.0.0.1, ::1)
- Link-local and reserved addresses
- Non-HTTP/HTTPS schemes (e.g., file://, ftp://, javascript:)

---
Developed with the [Model Context Protocol](https://modelcontextprotocol.io/).