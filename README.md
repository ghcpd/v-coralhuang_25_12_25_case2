# API Compatibility Test Suite

## Overview

This project implements a comprehensive contract-based compatibility test suite for detecting API breaking changes and enforcing deprecation policies.

The test suite validates:
- ✓ Deprecated endpoint behavior (stable_error with migration guidance)
- ✓ Authentication contract compliance (Bearer token requirements)
- ✓ Response schema compliance (required fields, types, nested structures)
- ✓ Schema evolution rules (field relocation, disallowed dual fields)
- ✓ API versioning separation (v1 vs v2 endpoints)

**All tests operate purely on `input.json` — no external services or live backend required.**

---

## Quick Start

### Run All Tests

```bash
python run_tests.py
```

This command:
1. Validates `input.json` structure
2. Loads OpenAPI contract and compatibility policies
3. Executes all pytest compatibility tests
4. Reports results (exit code 0 = pass, non-zero = fail)

### Run Specific Test Class

```bash
python -m pytest tests/test_api_compatibility.py::TestDeprecatedEndpointBehavior -v
```

### Run Tests with Detailed Output

```bash
python -m pytest tests/test_api_compatibility.py -v --tb=long
```

---

## Project Structure

```
.
├── run_tests.py                  # Single entrypoint to execute tests
├── input.json                    # Single source of truth (data-driven tests)
├── docs/
│   ├── analysis.md              # API changes analysis & breaking points
│   └── compatibility_strategy.md # Test design & coverage strategy
├── tests/
│   └── test_api_compatibility.py # 10+ pytest-based contract tests
└── README.md                     # This file
```

---

## Scenario

A backend API has evolved from v1 (unversioned) to v2:

### Before (Client Code - Deployed)
```python
# Old client using deprecated endpoint + cookie auth
def get_user(user_id: int, session_cookie: str):
    url = f"https://api.example.com/api/users/{user_id}"
    headers = {
        "Accept": "application/json",
        "Cookie": f"session={session_cookie}",
    }
    r = requests.get(url, headers=headers)
    data = r.json()
    return data["about_me"]  # Root-level field
```

### Now (Current API - OpenAPI)
```
GET /api/v2/users/{id}
  Security: Bearer token (required)
  Response:
    - id: integer
    - username: string
    - last_seen: ISO 8601 datetime (NEW, required)
    - profile:
        about_me: string  # MOVED from root
    - _links: HATEOAS links (NEW, required)
```

### Deprecation Policy
- Old endpoint `/api/users/{id}` returns **404 Not Found** (stable_error)
- Error message contains migration hint: **"/api/v2/users/{id}"**
- New endpoint requires Bearer authentication
- Field `about_me` relocated; dual presence is **prohibited**

---

## Test Coverage

### Test Suite 1: Deprecated Endpoint Behavior (4 tests)
Ensures deprecated endpoints fail gracefully with clear migration guidance.

| Test | Purpose |
|------|---------|
| `test_deprecated_endpoint_returns_404_status` | Verify 404 (not 200, 500, 401) |
| `test_deprecated_endpoint_error_schema_valid` | Validate error structure (required fields) |
| `test_deprecated_endpoint_migration_guidance` | Verify message contains new endpoint URL |
| `test_deprecated_endpoint_stable_behavior` | Ensure consistent error responses |

### Test Suite 2: Authentication Contract (4 tests)
Validates OpenAPI security requirements and authentication enforcement.

| Test | Purpose |
|------|---------|
| `test_openapi_requires_bearer_auth` | Verify endpoint declares Bearer requirement |
| `test_openapi_defines_bearer_scheme` | Validate Bearer scheme definition |
| `test_auth_required_on_new_endpoint` | Confirm Authorization header present |
| `test_deprecated_endpoint_no_auth_required_in_policy` | Deprecated endpoint not enforcing auth |

### Test Suite 3: Response Schema Compliance (4 tests)
Validates observed responses match OpenAPI schema definitions.

| Test | Purpose |
|------|---------|
| `test_response_required_fields_present` | All required schema fields exist |
| `test_response_field_types_match_schema` | Fields match OpenAPI types |
| `test_response_nested_field_access` | Nested fields accessible at correct paths |
| `test_response_hateoas_links_present` | HATEOAS _links include required endpoints |

### Test Suite 4: Schema Evolution & Compat Rules (4+ tests)
Enforce explicit compatibility rules for schema evolution.

| Test | Purpose |
|------|---------|
| `test_schema_compat_about_me_field_relocation` | Verify field moved to new location |
| `test_schema_compat_prohibits_dual_about_me` | Disallow simultaneous old + new locations |
| `test_schema_evolution_new_required_fields` | New fields (last_seen, _links) required |
| `test_schema_field_datetime_format` | Validate ISO 8601 format |
| `test_endpoint_path_migration_documented` | Version migration documented in policy |
| `test_api_versioning_separation` | v1 and v2 cleanly separated |

### Test Suite 5: Integration & Consistency (2 tests)
Validate consistency between OpenAPI, samples, and policies.

| Test | Purpose |
|------|---------|
| `test_openapi_sample_alignment` | Samples align with OpenAPI contract |
| `test_compat_policy_enforcement_feasible` | Policy rules verifiable from data |

---

## Test Input Source: `input.json`

All tests derive from a single JSON document with sections:

### `input.client`
Represents deployed, real-world client behavior.
```json
{
  "id": "client_v1_mobile_sdk",
  "language": "python",
  "code": "...",
  "assumptions": {
    "base_url": "https://api.example.com",
    "endpoints": [...],
    "auth": {...}
  }
}
```

### `input.server.openapi`
Current, authoritative OpenAPI 3.0.3 specification.
```json
{
  "openapi": "3.0.3",
  "paths": {
    "/api/v2/users/{id}": {...}
  },
  "components": {
    "securitySchemes": {...},
    "schemas": {...}
  }
}
```

### `input.observations`
Concrete, observed request/response samples.
```json
{
  "samples": [
    {
      "id": "old_client_call_fails_removed_endpoint",
      "request": {...},
      "response": {"status": 404, "body": {...}}
    },
    {
      "id": "new_endpoint_success_with_bearer_token",
      "request": {...},
      "response": {"status": 200, "body": {...}}
    }
  ]
}
```

### `input.compat_policy`
Explicit compatibility and deprecation rules.
```json
{
  "compat_window_days": 90,
  "deprecated_endpoints": [
    {
      "method": "GET",
      "path": "/api/users/{id}",
      "behavior": "stable_error",
      "expected_status": 404,
      "message_must_contain": ["/api/v2/users/{id}"]
    }
  ],
  "schema_compat": {
    "user_payload": {
      "allow_dual_about_me": false,
      "new_location": "profile.about_me",
      "old_location": "about_me"
    }
  }
}
```

---

## Breaking Changes Detected

### 1. Endpoint Path (CRITICAL)
- **Old**: `GET /api/users/{id}`
- **New**: `GET /api/v2/users/{id}`
- **Impact**: All client calls to old path fail with 404
- **Mitigation**: Error message directs to new endpoint

### 2. Authentication (CRITICAL)
- **Old**: Cookie-based (`session` cookie)
- **New**: Bearer token (`Authorization: Bearer <token>`)
- **Impact**: Cookie-only clients cannot authenticate
- **Migration**: Clients must implement token-based auth

### 3. Response Schema (CRITICAL)
- **Old**: `{"id": ..., "username": ..., "about_me": "..."}`
- **New**: `{"id": ..., "username": ..., "last_seen": ..., "profile": {"about_me": "..."}, "_links": {...}}`
- **Impact**: Field `about_me` no longer at root; new required fields
- **Migration**: Clients must update field extraction paths

---

## Running Tests

### Prerequisites

Ensure pytest is installed:
```bash
pip install pytest
```

### Execute Full Suite

```bash
python run_tests.py
```

**Expected output:**
```
======================================================================
API COMPATIBILITY TEST SUITE - ENTRYPOINT
======================================================================

Step 1: Validating input.json...
✓ input.json validation passed

Step 2: Running pytest compatibility tests...

======================================================================
RUNNING API COMPATIBILITY TESTS
======================================================================

tests/test_api_compatibility.py::TestDeprecatedEndpointBehavior::test_deprecated_endpoint_returns_404_status PASSED
tests/test_api_compatibility.py::TestDeprecatedEndpointBehavior::test_deprecated_endpoint_error_schema_valid PASSED
tests/test_api_compatibility.py::TestDeprecatedEndpointBehavior::test_deprecated_endpoint_migration_guidance PASSED
tests/test_api_compatibility.py::TestDeprecatedEndpointBehavior::test_deprecated_endpoint_stable_behavior PASSED
tests/test_api_compatibility.py::TestAuthenticationContract::test_openapi_requires_bearer_auth PASSED
tests/test_api_compatibility.py::TestAuthenticationContract::test_openapi_defines_bearer_scheme PASSED
tests/test_api_compatibility.py::TestAuthenticationContract::test_auth_required_on_new_endpoint PASSED
tests/test_api_compatibility.py::TestAuthenticationContract::test_deprecated_endpoint_no_auth_required_in_policy PASSED
tests/test_api_compatibility.py::TestResponseSchemaCompliance::test_response_required_fields_present PASSED
tests/test_api_compatibility.py::TestResponseSchemaCompliance::test_response_field_types_match_schema PASSED
tests/test_api_compatibility.py::TestResponseSchemaCompliance::test_response_nested_field_access PASSED
tests/test_api_compatibility.py::TestResponseSchemaCompliance::test_response_hateoas_links_present PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_schema_compat_about_me_field_relocation PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_schema_compat_prohibits_dual_about_me PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_schema_evolution_new_required_fields PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_schema_field_datetime_format PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_endpoint_path_migration_documented PASSED
tests/test_api_compatibility.py::TestSchemaEvolution::test_api_versioning_separation PASSED
tests/test_api_compatibility.py::TestContractConsistency::test_openapi_sample_alignment PASSED
tests/test_api_compatibility.py::TestContractConsistency::test_compat_policy_enforcement_feasible PASSED

======================================================================
✅ ALL TESTS PASSED - API is backward compatible
======================================================================
```

---

## Documentation

### [docs/analysis.md](docs/analysis.md)
Detailed analysis of API changes, breaking points, and impact assessment.

### [docs/compatibility_strategy.md](docs/compatibility_strategy.md)
Test design strategy, assertion patterns, coverage goals, and failure modes.

---

## Key Design Principles

1. **Contract-Based Testing**
   - Tests validate OpenAPI contracts, not live behavior
   - No external services or mocked backends required

2. **Data-Driven**
   - Single source of truth: `input.json`
   - All test cases derived from actual samples and policies

3. **Clear Assertions**
   - Each test failure clearly indicates which rule was violated
   - Error messages provide migration guidance

4. **Deterministic**
   - No randomness, external calls, or timing dependencies
   - Reproducible results across runs

5. **Comprehensive**
   - Covers deprecated endpoints, authentication, schema, versioning
   - Enforces explicit compatibility policies

---

## Exit Codes

- **0**: All tests pass (API is compatible with policies)
- **1+**: One or more tests fail (breaking changes detected)

---

## Troubleshooting

### pytest not found
```bash
pip install pytest
```

### input.json validation fails
Ensure `input.json` contains all required sections:
- `client`
- `server`
- `observations`
- `compat_policy`

### Test failures
Review test output for specific assertion failures.
See [docs/analysis.md](docs/analysis.md) for context on breaking changes.

---

## License & Usage

This compatibility test suite is designed to validate API contracts and enforce deprecation policies. Use it to:
- Detect breaking changes before deployment
- Document API evolution and versioning
- Guide clients on migration paths
- Prevent regressions in API contracts

---

## Further Reading

- [OpenAPI 3.0.3 Specification](https://spec.openapis.org/oas/v3.0.3)
- [API Versioning Best Practices](https://swagger.io/resources/articles/best-practices-in-api-versioning/)
- [Deprecation Strategies](https://en.wikipedia.org/wiki/Deprecation)
