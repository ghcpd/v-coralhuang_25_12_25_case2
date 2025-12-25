#!/usr/bin/env python3
"""
Run the compatibility test suite.

Steps performed:
- Load and validate `input.json` presence
- Execute pytest to run tests in `tests/`
- Exit with non-zero on test failure
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT_PATH = ROOT / "input.json"


def load_input_or_exit():
    if not INPUT_PATH.exists():
        print("ERROR: input.json not found in project root.")
        sys.exit(2)
    try:
        with INPUT_PATH.open() as f:
            json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to load input.json: {e}")
        sys.exit(2)


if __name__ == "__main__":
    load_input_or_exit()

    try:
        import pytest
    except Exception:
        print("ERROR: pytest is not installed. Install it with: pip install pytest")
        sys.exit(2)

    # Run pytest
    rc = pytest.main(["-q"])  # returns exit code
    sys.exit(rc)
