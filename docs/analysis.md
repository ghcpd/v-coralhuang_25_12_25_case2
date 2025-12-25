# Analysis of API changes and compatibility impact

Summary
-------
- The API removed the legacy endpoint `GET /api/users/{id}` and introduced `GET /api/v2/users/{id}`.
- Authentication for non-browser clients migrated from cookie-based sessions to HTTP Bearer tokens.
- The user payload was restructured: `about_me` moved from the top-level to `profile.about_me`.
- Observed samples show: legacy clients receive a 404 with migration guidance; new clients call `/api/v2/users/{id}` with a Bearer token and receive the `UserV2` shape.

Key breaking changes
--------------------
1. Endpoint removal
   - `/api/users/{id}` has been removed (observed 404). Backward-incompatible for clients still calling the old path.
2. Authentication change
   - Non-browser clients must use `Authorization: Bearer <token>` for `/api/v2/users/{id}`. Cookie sessions are no longer accepted for API clients.
3. Response schema migration
   - `about_me` relocated from top-level (`about_me`) to `profile.about_me`.
   - `UserV2` introduces required fields (`last_seen`, `_links`) not present in older payloads.

Compatibility policy enforcement (derived)
-----------------------------------------
- Deprecated endpoints must return a stable, machine-parseable error (status + schema) for the deprecation window.
- Error messages MUST include migration guidance (explicit new path).
- Schema migration MUST either allow dual-location fields during the window or reject legacy fields; here `allow_dual_about_me=false` — legacy field must be rejected.
- Authentication requirements declared in OpenAPI must be enforced and documented for clients migrating off browser sessions.

Tests implemented
-----------------
- Verify deprecated endpoint behaviour and error schema
- Verify migration guidance appears in changelog and error messages
- Verify OpenAPI requires `bearerAuth` for `/api/v2/users/{id}`
- Validate success sample against `UserV2` required fields, types and `date-time` format
- Enforce schema migration rule disallowing legacy `about_me` when policy forbids dual fields
- Surface client-server mismatches so engineers can prioritize client fixes

Recommended remediation priorities
---------------------------------
1. Create and ship a compatibility shim for high-volume legacy clients that translates
   cookie-session requests to token-auth (short-term emergency fix).
2. Publish a migration guide with code snippets and a compatibility timeline aligned to the
   90-day deprecation window in `compat_policy`.
3. Add strong telemetry to detect remaining callers to `/api/users/{id}` and alert owners.
4. Provide a library update for the deprecated client showing how to switch to bearer tokens
   and how to read the new `profile.about_me` field.
