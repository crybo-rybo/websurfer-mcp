# Repository Guidelines

## Project Structure & Module Organization
This repository uses a `src` layout. Application code lives in `src/websurfer_mcp/`: `server.py` wires the MCP tool, `extractor.py` handles fetching and text extraction, `networking.py` enforces DNS-level destination safety, `url_validation.py` validates user-facing URLs, `config.py` manages runtime settings, and `cli.py` provides local entrypoints. Tests live in `tests/`, documentation assets live in `docs/images/`, and `run_tests.py` is the project’s built-in unittest runner.

## Build, Test, and Development Commands
Install dependencies with:

```bash
uv sync
uv sync --group dev
```

Run the MCP server over stdio:

```bash
uv run websurfer-mcp serve
uv run python -m websurfer_mcp serve
```

Smoke-test extraction against a URL:

```bash
uv run websurfer-mcp test --url "https://example.com"
```

Run the full suite, one module, or lint/format checks:

```bash
uv run pytest
uv run python run_tests.py
uv run python run_tests.py --module test_url_validation
uv run ruff check .
uv run ruff format .
```

## Coding Style & Naming Conventions
Target Python 3.12+ and keep code importable from `src/websurfer_mcp/`. Use 4-space indentation, `snake_case` for modules/functions, `PascalCase` for classes, and concise docstrings on public behavior. Prefer explicit type hints on public APIs and keep modules focused by domain instead of collecting miscellaneous helpers in `utils.py`. `ruff` is configured in `pyproject.toml`; run it before opening a PR.

## Testing Guidelines
Tests live in `tests/test_*.py` and are written with `unittest`, while `pytest` is the preferred test runner. Mirror the module or behavior under test, and prefer `AsyncMock` or other local mocks over live network calls. Keep tests hermetic: server tests should mock extraction, and extractor tests should mock `aiohttp` responses. Run the focused module first, then `uv run pytest` before opening a PR.

## Commit & Pull Request Guidelines
Recent commits use short, imperative subjects such as `Add logo to README.md` and `Optimize URL validation and text extraction logic`. Keep commits narrowly scoped and describe the user-visible change first. PRs should include a brief summary, the commands you ran, related issue links when available, and any configuration or documentation updates required by the change.

## Security & Configuration Tips
Preserve the repository’s security posture: only allow `http`/`https`, keep SSRF protections intact, and do not relax content-length, redirect, or timeout limits without tests. Runtime tuning belongs in environment variables such as `MCP_DEFAULT_TIMEOUT`, `MCP_MAX_TIMEOUT`, `MCP_MAX_REDIRECTS`, `MCP_USER_AGENT`, and `MCP_MAX_CONTENT_LENGTH`.
