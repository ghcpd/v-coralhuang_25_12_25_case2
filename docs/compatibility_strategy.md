# Compatibility Strategy

## Goal
Provide deterministic, contract-level verification that the API evolution conforms to the compatibility rules declared in `input.json` and that observed traffic behaves consistently with the OpenAPI contract.

## Approach
- Tests operate solely on data available in `input.json` (no network or live servers).
- Validate OpenAPI contract (`input.server.openapi`) against observed samples (`input.observations.samples`).
- Encode `input.compat_policy` rules as assertions in a pytest suite.

## Key Checks
- Deprecated endpoint behavior: ensure `deprecated_endpoints` entries indicate the expected status code and stable error schema; validate observed sample(s) for the deprecated endpoint follow this contract and that message contains required migration hint.
- Authentication requirements: derive from OpenAPI `security` section and verify observed requests include required auth headers (or that the sample demonstrates lack/need for them).
- Response schema validation: use the schema defined under `components.schemas` to validate observed sample `response.body` structures, ensuring required properties, types, and formats match.
- Schema evolution rules: implement explicit checks for field relocation (e.g., `about_me`) and policy constraints such as `allow_dual_about_me`.

## Test granularity
Each test focuses on a single rule described in `input.compat_policy` for clarity of failure modes.

## Determinism and Reporting
- Use pytest assertions with descriptive messages to indicate which compatibility rule was violated.
- `run_tests` entrypoint will load `input.json` and run pytest; on failure it will exit non-zero and print failing assertions.

## Next steps
Implement tests and scripts in the repository and run them locally via `run_tests`.
