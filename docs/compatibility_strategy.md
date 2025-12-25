# Compatibility Strategy

Objective
- Enforce backwards-compatibility guarantees during a 90-day compatibility window and prevent silent regressions for existing clients.

Key policies (mapped from input.json -> compat_policy)
- Deprecated endpoints
  - Keep deprecated endpoints returning a stable, well-documented error schema.
  - Error messages must include clear migration guidance (target endpoint/path).

- Authentication migration
  - Treat OpenAPI `security` declarations as authoritative.
  - Non-browser clients must adopt bearer tokens to access `/api/v2/*` endpoints.

- Schema evolution rules
  - Required fields in the OpenAPI schema are contractually required in responses.
  - When relocating fields (example: `about_me` -> `profile.about_me`), disallow dual presence unless explicitly allowed.
  - Enforce type/format checks (e.g., `date-time` fields must parse as RFC3339).

Testing & enforcement
- Implement contract-only compatibility tests (no live service) that validate:
  - Deprecated endpoint responses match the stable error schema and include migration guidance.
  - OpenAPI `paths` and `security` constraints align with observed samples.
  - Observed successful responses include all `required` schema fields and correct types/formats.
  - Schema migration invariants (no legacy fields when disallowed).

Operational recommendations
- Provide server-side redirects or feature flags to serve compatibility responses for the deprecation window.
- Update SDKs and publish migration guides emphasizing token-based auth for non-browser clients.
- Monitor telemetry for 404s on deprecated endpoints and authenticate-related failures after migration.
