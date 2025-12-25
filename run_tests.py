#!/usr/bin/env python3

import json
import sys
import subprocess
import os

def main():
    # Load and validate input.json
    input_file = "input.json"
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        sys.exit(1)

    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        print("input.json loaded successfully.")
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {input_file}: {e}")
        sys.exit(1)

    # Run pytest
    result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], capture_output=True, text=True)
    print(result.stdout)
    if result.stderr:
        print(result.stderr)
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()