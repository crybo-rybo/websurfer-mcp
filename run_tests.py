#!/usr/bin/env python3
"""
Test runner for the MCP URL Search Server.
Provides a simple interface to run all tests or specific test modules.
"""

import sys
import unittest
import argparse
import os


def discover_and_run_tests(test_pattern="test_*.py", verbosity=2, start_dir="tests"):
    """
    Discover and run tests with the given pattern.
    
    Args:
        test_pattern: Pattern to match test files
        verbosity: Test output verbosity level
        start_dir: Directory to start test discovery
        
    Returns:
        TestResult object
    """
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Discover tests
    loader = unittest.TestLoader()
    suite = loader.discover(start_dir, pattern=test_pattern)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    result = runner.run(suite)
    
    return result


def run_specific_test_module(module_name, verbosity=2):
    """
    Run a specific test module.
    
    Args:
        module_name: Name of the test module (e.g., 'test_url_validator')
        verbosity: Test output verbosity level
        
    Returns:
        TestResult object
    """
    
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    
    # Import and run specific module
    module_path = f"tests.{module_name}"
    suite = unittest.TestLoader().loadTestsFromName(module_path)
    
    runner = unittest.TextTestRunner(verbosity=verbosity, buffer=True)
    result = runner.run(suite)
    
    return result


def main():
    """Main entry point for the test runner."""
    
    parser = argparse.ArgumentParser(
        description="Test runner for MCP URL Search Server"
    )
    
    parser.add_argument(
        "--module",
        help="Run specific test module (e.g., test_url_validator, test_text_extractor, test_integration, test_config)"
    )
    
    parser.add_argument(
        "--pattern", 
        default="test_*.py",
        help="Pattern to match test files (default: test_*.py)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Increase test output verbosity"
    )
    
    parser.add_argument(
        "--quiet", "-q",
        action="store_true", 
        help="Decrease test output verbosity"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available test modules"
    )
    
    args = parser.parse_args()
    
    # Determine verbosity level
    if args.quiet:
        verbosity = 0
    elif args.verbose:
        verbosity = 3
    else:
        verbosity = 2
    
    # List available test modules
    if args.list:
        print("Available test modules:")
        test_modules = [
            "test_url_validator - URL validation functionality",
            "test_text_extractor - Text extraction functionality", 
            "test_integration - End-to-end integration tests",
            "test_config - Configuration management"
        ]
        for module in test_modules:
            print(f"  - {module}")
        return
    
    # Run tests
    try:
        if args.module:
            print(f"Running tests for module: {args.module}")
            result = run_specific_test_module(args.module, verbosity)
        else:
            print("Running all tests...")
            result = discover_and_run_tests(args.pattern, verbosity)
        
        # Print summary
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Tests run: {result.testsRun}")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
        print(f"Skipped: {len(result.skipped)}")
        
        if result.failures:
            print(f"\nFAILURES:")
            for test, traceback in result.failures:
                print(f"  - {test}")
        
        if result.errors:
            print(f"\nERRORS:")
            for test, traceback in result.errors:
                print(f"  - {test}")
        
        # Exit with appropriate code
        if result.failures or result.errors:
            print(f"\nTests FAILED")
            sys.exit(1)
        else:
            print(f"\nAll tests PASSED")
            sys.exit(0)
            
    except Exception as e:
        print(f"Error running tests: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()