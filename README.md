# API Compatibility Test Suite

This repository contains contract-only compatibility tests that validate API changes described in `input.json`.

How to run

- Windows / any platform with Python 3.8+:
  - python run_tests.py

What run_tests does
- Validates `input.json` is present and well-formed
- Runs the pytest-based compatibility tests located in `tests/`
- Exits non-zero if any compatibility assertion fails

Files of interest
- `input.json` — single source of truth (provided)
- `tests/test_api_compatibility.py` — compatibility assertions
- `docs/analysis.md` — short analysis of changes and breakages
- `docs/compatibility_strategy.md` — rules and mitigation guidance
