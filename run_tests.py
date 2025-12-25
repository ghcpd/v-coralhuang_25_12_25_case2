#!/usr/bin/env python3
"""
run_tests: Single command entrypoint for API compatibility test suite.

Usage:
    python run_tests.py
    
This script:
1. Validates input.json structure
2. Loads the OpenAPI contract and compatibility policies
3. Executes all pytest compatibility tests
4. Reports pass/fail with clear error messages
5. Exits with code 0 (pass) or 1+ (failure)
"""

import sys
import json
import subprocess
from pathlib import Path


def validate_input_json() -> bool:
    """Validate that input.json exists and has required structure."""
    input_file = Path(__file__).parent / "input.json"
    
    if not input_file.exists():
        print(f"ERROR: input.json not found at {input_file}")
        return False
    
    try:
        with open(input_file, "r") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: input.json is not valid JSON: {e}")
        return False
    
    # Validate required sections
    required_sections = ["client", "server", "observations", "compat_policy"]
    for section in required_sections:
        if section not in data:
            print(f"ERROR: input.json missing required section '{section}'")
            return False
    
    # Validate server.openapi
    if "openapi" not in data["server"]:
        print("ERROR: input.json missing server.openapi")
        return False
    
    # Validate observations.samples
    if "samples" not in data["observations"]:
        print("ERROR: input.json missing observations.samples")
        return False
    
    # Validate compat_policy.deprecated_endpoints
    if "deprecated_endpoints" not in data["compat_policy"]:
        print("ERROR: input.json missing compat_policy.deprecated_endpoints")
        return False
    
    print("[OK] input.json validation passed")
    return True


def run_pytest() -> int:
    """Execute pytest compatibility tests."""
    tests_file = Path(__file__).parent / "tests" / "test_api_compatibility.py"
    
    if not tests_file.exists():
        print(f"ERROR: tests/test_api_compatibility.py not found at {tests_file}")
        return 1
    
    print("\n" + "="*70)
    print("RUNNING API COMPATIBILITY TESTS")
    print("="*70 + "\n")
    
    # Run pytest with verbose output
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(tests_file), "-v", "--tb=short"],
        capture_output=False
    )
    
    return result.returncode


def main() -> int:
    """Main entrypoint."""
    print("="*70)
    print("API COMPATIBILITY TEST SUITE - ENTRYPOINT")
    print("="*70)
    print()
    
    # Step 1: Validate input.json
    print("Step 1: Validating input.json...")
    if not validate_input_json():
        print("\n❌ input.json validation failed")
        return 1
    
    # Step 2: Run tests
    print("\nStep 2: Running pytest compatibility tests...\n")
    exit_code = run_pytest()
    
    # Step 3: Report results
    print("\n" + "="*70)
    if exit_code == 0:
        print("[PASS] ALL TESTS PASSED - API is backward compatible")
        print("="*70)
    else:
        print("[FAIL] SOME TESTS FAILED - API has compatibility issues")
        print("="*70)
        print("\nRefer to test output above for details.")
        print("See docs/analysis.md and docs/compatibility_strategy.md for context.")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
