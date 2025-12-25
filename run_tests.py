#!/usr/bin/env python3
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(__file__)
INPUT_PATH = os.path.join(ROOT, "input.json")


def load_and_validate_input(path):
    if not os.path.exists(path):
        print(f"ERROR: input.json not found at {path}")
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"ERROR: failed to parse input.json: {e}")
        return False

    # basic sanity checks
    for key in ("client", "server", "observations", "compat_policy"):
        if key not in data:
            print(f"ERROR: input.json missing required top-level key: {key}")
            return False
    return True


def ensure_pytest_available():
    try:
        import pytest  # noqa: F401
        return True
    except Exception:
        print("pytest not found — attempting to install pytest using pip...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pytest"], stdout=subprocess.DEVNULL)
            return True
        except Exception as e:
            print(f"Failed to install pytest: {e}")
            return False


def main():
    ok = load_and_validate_input(INPUT_PATH)
    if not ok:
        sys.exit(2)

    if not ensure_pytest_available():
        sys.exit(3)

    # run pytest
    import pytest

    # -q for concise output
    rc = pytest.main(["-q"]) 
    sys.exit(rc)


if __name__ == "__main__":
    main()
