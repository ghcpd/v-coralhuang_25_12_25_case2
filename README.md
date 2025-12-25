# API Compatibility Test Suite

This repository contains contract-level compatibility tests derived from a single source of truth: `input.json`.

Requirements:
- Python 3.8+
- pytest (install with `pip install pytest`)

Running tests:

1. Ensure `input.json` is present in the project root (already included).
2. Run the provided entrypoint script:

```bash
python run_tests.py
```

`run_tests.py` will load `input.json` and execute `pytest`. The script exits with a non-zero code if any test fails.

Test goals:
- Validate deprecated endpoint behavior and migration guidance
- Verify authentication requirements from OpenAPI
- Assert response payload conforms to the `UserV2` schema
- Enforce schema evolution and compatibility policy (e.g., `about_me` relocation)
