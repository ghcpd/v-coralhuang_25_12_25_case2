# API Compatibility Tests

This project contains contract/compatibility tests for API evolution.

## Prerequisites
- Python 3.x
- Install dependencies: `pip install -r requirements.txt`

## Running Tests
Execute the `run_tests.py` script to run the full test suite:

```bash
python run_tests.py
```

The script will:
1. Load and validate `input.json`
2. Execute pytest-based compatibility tests
3. Report pass/fail results

If any test fails, the script exits with non-zero code.