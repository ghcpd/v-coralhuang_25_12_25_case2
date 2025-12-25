# API Compatibility test suite

What this repo provides
- Contract & compatibility tests that operate on a single source of truth: `input.json`.
- Enforces deprecation rules, authentication migration, and schema evolution policies.

Quickstart ✅

- Run the full test-suite:

  - Unix/macOS: ./run_tests
  - Windows / any platform: python run_tests.py

What the tests check (high level)
- Deprecated endpoint returns stable migration error
- OpenAPI declares `bearerAuth` for `/api/v2/users/{id}`
- Observed successful responses conform to `UserV2` schema
- Schema migration rules (e.g. `about_me` relocation) are enforced

If a test fails
- The failure message will indicate which compatibility rule was violated and point to
  the relevant section of `input.json` (observations, server.openapi, or compat_policy).
