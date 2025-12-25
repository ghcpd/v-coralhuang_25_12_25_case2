# API Compatibility & Deprecation Strategy

## Objective

Establish a systematic approach to validating API contract compatibility, enforcing deprecation rules, and detecting breaking changes at the contract level—without relying on a live backend service.

## Test Categories

### 1. **Deprecated Endpoint Behavior Tests**
**Purpose**: Verify that deprecated endpoints return consistent error responses with migration guidance.

**Tests**:
- `test_deprecated_endpoint_returns_404_status` — Verify deprecated endpoint returns 404 (not 500, not 200)
- `test_deprecated_endpoint_error_schema_valid` — Validate error response structure matches contract
- `test_deprecated_endpoint_migration_guidance` — Verify error message contains link to new endpoint
- `test_deprecated_endpoint_stable_behavior` — Confirm error behavior is deterministic across samples

**Rationale**: Deprecated endpoints must fail gracefully with clear guidance, preventing client retry loops and data corruption.

---

### 2. **Authentication Contract Tests**
**Purpose**: Verify OpenAPI security requirements and detect authentication mismatches.

**Tests**:
- `test_openapi_requires_bearer_auth` — Confirm new endpoint enforces Bearer token in OpenAPI spec
- `test_openapi_defines_bearer_scheme` — Validate `bearerAuth` security scheme is properly defined
- `test_auth_required_on_new_endpoint` — Verify successful request includes Authorization header
- `test_deprecated_endpoint_no_auth_requirement` — Confirm old endpoint doesn't require token (because it's removed)

**Rationale**: Authentication changes are breaking. The test suite must detect when OpenAPI requires authentication but samples do not provide it, or vice versa.

---

### 3. **Response Schema Compliance Tests**
**Purpose**: Validate observed responses match OpenAPI schema definitions.

**Tests**:
- `test_response_required_fields_present` — Verify all required schema fields exist in samples
- `test_response_field_types_match_schema` — Confirm field types match OpenAPI type definitions
- `test_response_nested_field_access` — Validate nested fields (e.g., `profile.about_me`) are accessible
- `test_response_no_legacy_field_locations` — Enforce that legacy `about_me` at root is NOT present (when `allow_dual_about_me=false`)

**Rationale**: Response schema changes are a common source of client breakage. Validation at contract level catches mismatches before deployment.

---

### 4. **Schema Evolution & Compatibility Rules Tests**
**Purpose**: Enforce explicit compatibility rules defined in `compat_policy`.

**Tests**:
- `test_schema_compat_about_me_field_relocation` — Verify `about_me` exists at new location (`profile.about_me`)
- `test_schema_compat_prohibits_dual_about_me` — Enforce that both locations are NOT simultaneously present (contract violation)
- `test_schema_evolution_new_required_fields` — Confirm new required fields are defined in schema
- `test_schema_field_datetime_format` — Validate `last_seen` follows ISO 8601 format

**Rationale**: Schema evolution rules ensure clients can safely migrate without encountering unexpected field combinations or format mismatches.

---

## Test Data Strategy

### Input Source
All tests derive test cases from `input.json`:
- **Observations**: `input.observations.samples[]` — Real request/response pairs
- **OpenAPI Contract**: `input.server.openapi` — Authoritative schema and security definitions
- **Compatibility Rules**: `input.compat_policy` — Explicit deprecation and schema evolution rules

### Test Execution Flow
1. Load `input.json`
2. Extract OpenAPI paths, schemas, security schemes
3. Extract observation samples (requests and responses)
4. Extract compatibility rules
5. Run assertions against all three sources simultaneously

### No External Services
- ✓ Tests do NOT call a live backend
- ✓ Tests do NOT mock HTTP requests
- ✓ Tests validate **structure and contract**, not **behavior**

---

## Assertion Pattern

Each test follows this pattern:

```python
def test_example():
    # 1. Load contracts and policies from input.json
    openapi = load_openapi()
    sample = load_sample(sample_id)
    compat_rule = load_compat_rule()
    
    # 2. Extract testable facts from contracts
    fact = extract_fact(openapi, sample)
    
    # 3. Assert against rules
    assert fact_satisfies_rule(fact, compat_rule), error_message()
```

---

## Failure Modes & Error Messages

Each test failure must clearly indicate:
1. **What rule was violated** (contract, schema, or policy)
2. **Which sample/endpoint triggered the failure**
3. **What was expected vs. observed**

Example error messages:
```
FAIL: test_deprecated_endpoint_migration_guidance
  Sample: old_client_call_fails_removed_endpoint
  Endpoint: GET /api/users/{id}
  Error: Migration guidance missing
  Expected message to contain: "/api/v2/users/{id}"
  Actual message: "Endpoint not found"
```

---

## Iterative Validation

After implementing tests, run `run_tests` and verify:
- ✓ All 8+ tests pass
- ✓ Each test clearly reports its assertion
- ✓ Failure messages provide migration guidance
- ✓ No external services are required
- ✓ Exit code is 0 for all passes, non-zero for failures

---

## Coverage Goals

| Category | Tests | Coverage |
|----------|-------|----------|
| Deprecated Endpoints | 4 | Path removal, error schema, stable behavior, migration guidance |
| Authentication | 4 | Bearer scheme, security requirements, header validation |
| Response Schema | 4 | Required fields, types, nested access, field relocation |
| Schema Evolution | 4+ | Compat rules, disallowed dual fields, new fields, formats |
| **Total** | **8+** | Breaking changes, contract compliance, deprecation enforcement |

---

## Success Criteria

✓ All compatibility tests pass  
✓ Tests clearly differentiate between breaking changes and backward-compatible evolution  
✓ Error messages guide developers toward correct migration path  
✓ Run `run_tests` produces deterministic, reproducible results  
✓ No external dependencies or services required
