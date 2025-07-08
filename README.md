# 🌐 WebSurfer MCP

A powerful **Model Context Protocol (MCP)** server that enables Large Language Models (LLMs) to fetch and extract readable text content from web pages. This tool provides a secure, efficient, and feature-rich way for AI assistants to access web content through a standardized interface.

## ✨ Features

- **🔒 Secure URL Validation**: Blocks dangerous schemes, private IPs, and localhost domains
- **📄 Smart Content Extraction**: Extracts clean, readable text from HTML pages using advanced parsing
- **⚡ Rate Limiting**: Built-in rate limiting to prevent abuse (60 requests/minute)
- **🛡️ Content Type Filtering**: Only processes supported content types (HTML, plain text, XML)
- **📏 Size Limits**: Configurable content size limits (default: 10MB)
- **⏱️ Timeout Management**: Configurable request timeouts with validation
- **🔧 Comprehensive Error Handling**: Detailed error messages for various failure scenarios
- **🧪 Full Test Coverage**: 45+ unit tests covering all functionality

## 🏗️ Architecture

The project consists of several key components:

### Core Components

- **`MCPURLSearchServer`**: Main MCP server implementation
- **`TextExtractor`**: Handles web content fetching and text extraction
- **`URLValidator`**: Validates and sanitizes URLs for security
- **`Config`**: Centralized configuration management

### Key Features

- **Async/Await**: Built with modern Python async patterns for high performance
- **Resource Management**: Proper cleanup of network connections and resources
- **Context Managers**: Safe resource handling with automatic cleanup
- **Logging**: Comprehensive logging for debugging and monitoring

## 🚀 Installation

### Prerequisites

- Python 3.12 or higher
- [uv](https://github.com/astral-sh/uv) package manager (recommended)

### Quick Start

1. **Clone the repository**:
   ```bash
   git clone https://github.com/crybo-rybo/websurfer-mcp
   cd websurfer-mcp
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Verify installation**:
   ```bash
   uv run python -c "import mcp_url_search_server; print('Installation successful!')"
   ```

## 🎯 Usage

### Starting the MCP Server

The server communicates via stdio (standard input/output) and can be integrated with any MCP-compatible client.

```bash
# Start the server
uv run run_server.py serve

# Start with custom log level
uv run run_server.py serve --log-level DEBUG
```

### Testing URL Search Functionality

Test the URL search functionality directly:

```bash
# Test with a simple URL
uv run run_server.py test --url "https://example.com"

# Test with custom timeout
uv run run_server.py test --url "https://httpbin.org/html" --timeout 15
```

### Example Test Output

```json
{
  "success": true,
  "url": "https://example.com",
  "title": "Example Domain",
  "content_type": "text/html",
  "status_code": 200,
  "text_length": 1250,
  "text_preview": "Example Domain This domain is for use in illustrative examples in documents..."
}
```

## 🛠️ Configuration

The server can be configured using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_DEFAULT_TIMEOUT` | `10` | Default request timeout in seconds |
| `MCP_MAX_TIMEOUT` | `60` | Maximum allowed timeout in seconds |
| `MCP_USER_AGENT` | `MCP-URL-Search-Server/1.0.0` | User agent string for requests |
| `MCP_MAX_CONTENT_LENGTH` | `10485760` | Maximum content size in bytes (10MB) |

### Example Configuration

```bash
export MCP_DEFAULT_TIMEOUT=15
export MCP_MAX_CONTENT_LENGTH=5242880  # 5MB
uv run run_server.py serve
```

## 🧪 Testing

### Running All Tests

```bash
# Run all tests with verbose output
uv run python -m unittest discover tests -v

# Run tests with coverage (if coverage is installed)
uv run coverage run -m unittest discover tests
uv run coverage report
```

### Running Specific Test Files

```bash
# Run only integration tests
uv run python -m unittest tests.test_integration -v

# Run only text extraction tests
uv run python -m unittest tests.test_text_extractor -v

# Run only URL validation tests
uv run python -m unittest tests.test_url_validator -v
```

### Test Results

All 45 tests should pass successfully:

```
test_content_types_immutable (test_config.TestConfig.test_content_types_immutable) ... ok
test_default_configuration_values (test_config.TestConfig.test_default_configuration_values) ... ok
test_404_error_handling (test_integration.TestMCPURLSearchIntegration.test_404_error_handling) ... ok
...
----------------------------------------------------------------------
Ran 45 tests in 1.827s

OK
```

## 🔧 Development

### Project Structure

```
websurfer-mcp/
├── mcp_url_search_server.py  # Main MCP server implementation
├── text_extractor.py         # Web content extraction logic
├── url_validator.py          # URL validation and security
├── config.py                 # Configuration management
├── run_server.py             # Command-line interface
├── run_tests.py              # Test runner utilities
├── tests/                    # Test suite
│   ├── test_integration.py   # Integration tests
│   ├── test_text_extractor.py # Text extraction tests
│   ├── test_url_validator.py # URL validation tests
│   └── test_config.py        # Configuration tests
├── pyproject.toml            # Project configuration
└── README.md                 # This file
```

## 🔒 Security Features

### URL Validation

- **Scheme Blocking**: Blocks `file://`, `javascript:`, `ftp://` schemes
- **Private IP Protection**: Blocks access to private IP ranges (10.x.x.x, 192.168.x.x, etc.)
- **Localhost Protection**: Blocks localhost and local domain access
- **URL Length Limits**: Prevents extremely long URLs
- **Format Validation**: Ensures proper URL structure

### Content Safety

- **Content Type Filtering**: Only processes supported text-based content types
- **Size Limits**: Configurable maximum content size (default: 10MB)
- **Rate Limiting**: Prevents abuse with configurable limits
- **Timeout Protection**: Configurable request timeouts

## 📊 Performance

- **Async Processing**: Non-blocking I/O for high concurrency
- **Connection Pooling**: Efficient HTTP connection reuse
- **DNS Caching**: Reduces DNS lookup overhead
- **Resource Cleanup**: Automatic cleanup prevents memory leaks

## 🙏 Acknowledgments

- Built with the [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- Uses [aiohttp](https://aiohttp.readthedocs.io/) for async HTTP requests
- Leverages [trafilatura](https://trafilatura.readthedocs.io/) for content extraction
- Powered by [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for HTML parsing

---

**Happy web surfing with your AI assistant! 🚀**
