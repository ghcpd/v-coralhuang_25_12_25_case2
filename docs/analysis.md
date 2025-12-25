# Analysis of API changes and compatibility impact

Summary
- The API was versioned: previous endpoint `/api/users/{id}` was removed and replaced by `/api/v2/users/{id}`.
- Authentication changed from cookie-based browser sessions to token-based `Bearer` auth for non-browser clients.
- The user payload schema changed: `about_me` was moved under `profile.about_me` and the response object was extended (e.g. `_links`).

Breaking changes identified
1. Endpoint change
   - `/api/users/{id}` removed → clients calling the old path receive 404 with guidance to use `/api/v2/users/{id}`.
   - Impact: hard 404 for clients that haven't migrated.

2. Authentication change
   - OpenAPI requires `bearerAuth` for `/api/v2/users/{id}`.
   - Impact: clients sending `Cookie: session=...` will receive 401 or be unable to access v2 endpoints.

3. Response schema changes
   - Required properties changed/expanded (UserV2 requires `id`, `username`, `last_seen`, `_links`).
   - `about_me` relocated: old top-level `about_me` was moved to `profile.about_me`.
   - Dual-location for `about_me` is disallowed (compat_policy.allow_dual_about_me = false).
   - Type/format constraints added (e.g. `last_seen` is `date-time`).

Compatibility rules to enforce (derived from input.json)
- Deprecated endpoints must return a stable error (status + predictable schema) for the compat window.
- Error responses for removed endpoints must contain explicit migration guidance (contain `/api/v2/users/{id}`).
- OpenAPI security requirements are authoritative: clients must use bearer tokens for v2 endpoints.
- Response payloads must include all `required` fields from the server schema and respect declared types/formats.
- Schema evolution: fields relocated must not appear in their legacy location when `allow_dual_about_me` is false.

Recommended next steps
1. Add compatibility tests that assert the above rules (see test suite).
2. Communicate migration windows and provide server-side redirects or compatibility shims if feasible.
3. Provide sample bearer-auth examples and SDK updates for clients still using cookie sessions.
