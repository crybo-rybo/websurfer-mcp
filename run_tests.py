#!/usr/bin/env python3
"""Unittest runner for the repository."""

from __future__ import annotations

import argparse
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_ROOT = PROJECT_ROOT / "src"


def _bootstrap_path() -> None:
    """Ensure the src-layout package can be imported during local test runs."""

    src_root = str(SRC_ROOT)
    if src_root not in sys.path:
        sys.path.insert(0, src_root)


def discover_and_run_tests(
    test_pattern: str = "test_*.py",
    verbosity: int = 2,
    start_dir: str = "tests",
) -> unittest.result.TestResult:
    """Discover and run all matching tests."""

    _bootstrap_path()
    suite = unittest.TestLoader().discover(start_dir, pattern=test_pattern)
    return unittest.TextTestRunner(verbosity=verbosity, buffer=True).run(suite)


def run_specific_test_module(
    module_name: str,
    verbosity: int = 2,
) -> unittest.result.TestResult:
    """Run a single named test module."""

    _bootstrap_path()
    suite = unittest.TestLoader().loadTestsFromName(f"tests.{module_name}")
    return unittest.TextTestRunner(verbosity=verbosity, buffer=True).run(suite)


def main() -> int:
    """Main entrypoint for the test runner."""

    parser = argparse.ArgumentParser(description="Run the WebSurfer MCP test suite.")
    parser.add_argument(
        "--module",
        help="Run a specific test module, for example: test_url_validation",
    )
    parser.add_argument(
        "--pattern",
        default="test_*.py",
        help="Pattern to match test files during discovery.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Increase test output verbosity."
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce test output verbosity.")
    parser.add_argument("--list", action="store_true", help="List the supported test modules.")

    args = parser.parse_args()

    verbosity = 0 if args.quiet else 3 if args.verbose else 2

    if args.list:
        print("Available test modules:")
        modules = [
            "test_config - configuration management",
            "test_extractor - content fetching and extraction",
            "test_server - MCP server orchestration",
            "test_url_validation - URL validation rules",
        ]
        for module in modules:
            print(f"  - {module}")
        return 0

    if args.module:
        print(f"Running tests for module: {args.module}")
        result = run_specific_test_module(args.module, verbosity)
    else:
        print("Running all tests...")
        result = discover_and_run_tests(args.pattern, verbosity)

    print(f"\n{'=' * 60}")
    print("TEST SUMMARY")
    print(f"{'=' * 60}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")

    if result.failures:
        print("\nFAILURES:")
        for test, _traceback in result.failures:
            print(f"  - {test}")

    if result.errors:
        print("\nERRORS:")
        for test, _traceback in result.errors:
            print(f"  - {test}")

    if result.failures or result.errors:
        print("\nTests FAILED")
        return 1

    print("\nAll tests PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
