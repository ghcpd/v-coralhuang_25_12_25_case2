# API Evolution Analysis

## Breaking Changes Identified

1. **Endpoint Path Change**:
   - Old: `/api/users/{id}`
   - New: `/api/v2/users/{id}`
   - Impact: Existing clients will receive 404 errors.

2. **Authentication Method Change**:
   - Old: Cookie-based session (`session=<cookie>`)
   - New: Bearer token (`Authorization: Bearer <token>`)
   - Impact: Clients must migrate to token-based auth.

3. **Response Schema Changes**:
   - Added required fields: `last_seen`, `_links`
   - Relocated `about_me` from root to `profile.about_me`
   - Impact: Clients expecting old structure will fail to parse responses.

## Compatibility Rules to Enforce

- Deprecated endpoints must return stable 404 errors with schema-compliant error messages containing migration guidance.
- New endpoints must enforce bearer authentication as per OpenAPI spec.
- Response schemas must adhere to UserV2 schema, including required fields and type constraints.
- Schema evolution rules prohibit dual locations for `about_me` (must be in `profile.about_me` only).