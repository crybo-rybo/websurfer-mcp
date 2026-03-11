"""WebSurfer MCP package."""

from ._version import __version__
from .config import Config
from .extractor import ExtractionResult, TextExtractor
from .networking import SafeResolver, UnsafeAddressError
from .server import MCPURLSearchServer, WebSurferServer
from .url_validation import URLValidator, ValidationResult

__all__ = [
    "__version__",
    "Config",
    "ExtractionResult",
    "MCPURLSearchServer",
    "SafeResolver",
    "TextExtractor",
    "UnsafeAddressError",
    "URLValidator",
    "ValidationResult",
    "WebSurferServer",
]
