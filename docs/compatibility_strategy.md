# Compatibility & migration strategy

Goal
----
Minimize customer impact while moving clients from `GET /api/users/{id}` + cookie sessions to
`GET /api/v2/users/{id}` + bearer tokens and the new `UserV2` payload.

Short-term (0–14 days) ✅
- Implement a reverse-proxy compatibility shim that:
  - Accepts `Cookie: session=` from known client user-agents and exchanges it for a short-lived
    bearer token for the backend.
  - Emits detailed logs when a legacy request is proxied (client id, IP, timestamp).
- Publish an urgent migration guide and sample code for major languages.

Medium-term (14–60 days) ⚙️
- Ship client library updates and server-side feature flagging to roll out stricter validation.
- Add deprecation telemetry and an automated alert if legacy traffic does not fall within expected %.

Long-term (60–90 days) 🔒
- Remove shim after customers have migrated (respecting the 90-day deprecation window).
- Harden schema validation and add contract tests (the tests in this repo) to CI.

Developer guidance
------------------
- Use `Authorization: Bearer <token>` for non-browser clients. Authenticate via the official
  token issuance endpoint and follow token rotation guidance.
- Expect `about_me` at `profile.about_me`. Do not rely on top-level `about_me` once
  `allow_dual_about_me` is false.

Rollback & safety
-----------------
- If migration causes large-scale failures, re-enable the compatibility shim and open a
  communication channel to affected customers. Track and fix root causes before proceeding
  with removal.

Monitoring
----------
- Track: requests to `/api/users/`, requests to `/api/v2/users/` without Authorization,
  and occurrences of top-level `about_me` in v2 responses.
- Alert when legacy traffic > 1% after 30 days or > 0.1% after 60 days.
