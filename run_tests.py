"""Entrypoint to run the compatibility test-suite.

- Loads and performs a basic validation of `input.json`.
- Runs pytest and returns pytest's exit code.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "input.json"


def validate_input_json(path: Path):
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        print(f"ERROR: failed to load {path}: {exc}")
        return False

    # quick sanity checks
    required_top_level = {"client", "server", "observations", "compat_policy"}
    missing = required_top_level - set(data.keys())
    if missing:
        print(f"ERROR: input.json missing top-level keys: {sorted(missing)}")
        return False
    print("input.json loaded and sanity-checked OK")
    return True


def main():
    if not INPUT.exists():
        print("ERROR: input.json not found in repository root")
        return 2

    ok = validate_input_json(INPUT)
    if not ok:
        return 3

    # run pytest
    print("Running compatibility tests (pytest)...")
    # -q for concise output, --maxfail=1 to fail fast in CI
    rc = pytest.main(["-q", "--maxfail=1", "tests/test_api_compatibility.py"])
    return rc


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
