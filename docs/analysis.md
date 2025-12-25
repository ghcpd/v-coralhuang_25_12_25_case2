# API Compatibility Analysis

## Summary

The API has evolved from `/api/users/{id}` to `/api/v2/users/{id}`. Observed client requests to the old endpoint now receive a 404 with a clear migration message. The OpenAPI contract (`input.server.openapi`) indicates the new endpoint `/api/v2/users/{id}` is the authoritative path and requires bearer token authentication (`bearerAuth`). The response payload has also been changed: previously-flat `about_me` was relocated to `profile.about_me` and new required fields such as `last_seen` and `_links` were introduced.

## Breaking changes identified

- Endpoint change:
  - `/api/users/{id}` is removed/redirected. Observed behavior: 404 with an explanatory message telling clients to use `/api/v2/users/{id}`.

- Authentication change:
  - Non-browser clients must now use `Authorization: Bearer <token>` (per OpenAPI `bearerAuth`) instead of relying on a browser session cookie named `session`.

- Response schema changes:
  - `about_me` was moved into `profile.about_me` (schema evolution).
  - New required properties introduced in `UserV2`: `last_seen` and `_links`.
  - `profile` is now an object containing `about_me`.

## Compatibility policy to enforce

From `input.compat_policy`:
- Deprecated endpoint `/api/users/{id}` must return a stable error with status 404 and error body matching the expected error schema (fields `error` and `message`) and the message must contain `/api/v2/users/{id}` to guide clients.
- Schema compatibility for user payload:
  - `allow_dual_about_me`: false — clients must not expect both `about_me` at root and at `profile.about_me` simultaneously.
  - New location: `profile.about_me`; old location: `about_me`.

## Tests to implement

Tests will validate:
- Deprecated endpoint returns 404 and matches the expected error schema and migration message.
- New endpoint requires bearer token in security requirements.
- The `UserV2` response contains required fields and correct types/formats (`id` integer, `username` string, `last_seen` date-time, `profile.about_me` string, and `_links` object with `self`, `followers`, `followed` strings).
- That observed samples conform to the OpenAPI schema and satisfy compatibility rules (e.g., `new_endpoint_success_with_bearer_token` matches `UserV2`).
- Schema evolution rule enforcement: clients using old `about_me` field should fail policy when `allow_dual_about_me` is false.

## Next steps

1. Draft a short compatibility strategy document outlining verification approach and test mapping.
2. Implement a pytest test suite that loads `input.json` and asserts the above rules deterministically.
