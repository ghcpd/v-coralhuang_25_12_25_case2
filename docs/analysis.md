# API Evolution Analysis: Breaking Changes & Compatibility Issues

## Executive Summary

The API has undergone significant evolution from a v1 (unversioned) to v2 model, introducing **three major breaking changes** that will cause existing clients to fail. This analysis identifies the breaking changes, their impact, and the compatibility strategies in place.

## Current State

### Client (Deployed)
- **ID**: `client_v1_mobile_sdk` (Python)
- **Endpoint**: `GET /api/users/{user_id}`
- **Authentication**: Cookie-based (`session` cookie)
- **Expected Response Fields**: `id`, `username`, `about_me` (root level)

### Server (Current)
- **OpenAPI Version**: 3.0.3
- **New Endpoint**: `GET /api/v2/users/{id}`
- **Authentication**: Bearer token (required, enforced by OpenAPI security)
- **Response Schema**: User profile under `UserV2` schema
  - **Required fields**: `id`, `username`, `last_seen`, `_links`
  - **Optional nested field**: `profile.about_me` (previously at root)

## Breaking Changes

### 1. Endpoint Path Migration (CRITICAL)
- **Old**: `/api/users/{id}`
- **New**: `/api/v2/users/{id}`
- **Status**: Deprecated endpoint returns `404 Not Found`
- **Client Impact**: All existing client calls targeting `/api/users/{id}` will fail
- **Mitigation**: Error response includes migration guidance message

### 2. Authentication Scheme Change (CRITICAL)
- **Old**: Cookie-based session authentication
  - Cookie name: `session`
  - Expects browser session context
  - No explicit header required
- **New**: HTTP Bearer token authentication
  - Header: `Authorization: Bearer <token>`
  - Stateless, API client friendly
- **Client Impact**: Clients using cookie auth will receive `401 Unauthorized` or `404` (old endpoint)
- **Compatibility Impact**: Cookie-based clients cannot authenticate with new endpoint without code changes

### 3. Response Schema Restructuring (CRITICAL)
- **Field Relocation**: `about_me` moved from root to nested `profile.about_me`
  - Old: `data["about_me"]` → String value
  - New: `data["profile"]["about_me"]` → String value (nested)
- **New Required Fields**: 
  - `last_seen` (ISO 8601 datetime)
  - `_links` (HATEOAS links for API navigation)
- **Client Impact**: Clients expecting root-level `about_me` will break when accessing `data["about_me"]` (now missing/undefined)
- **Compatibility Rule**: Dual `about_me` (both locations) is **explicitly prohibited** (`allow_dual_about_me: false`)

## Compatibility Policy Enforcement

### Deprecated Endpoint Behavior
- **Endpoint**: `GET /api/users/{id}`
- **Behavior Type**: `stable_error` (consistent error response)
- **Expected Status**: `404 Not Found`
- **Error Schema**: Object with required fields `error` and `message`
- **Validation Rule**: Error message must contain text `/api/v2/users/{id}` (migration guidance)

### Compatibility Window
- **Duration**: 90 days from deprecation announcement
- **Current Status**: All tests assume enforcement is active

## Impact Assessment

| Aspect | Severity | Details |
|--------|----------|---------|
| Endpoint availability | CRITICAL | Old endpoint returns 404; clients receive error |
| Authentication | CRITICAL | Bearer token required; cookies no longer work |
| Response parsing | CRITICAL | `about_me` field location changed; client extraction code will fail |
| Required fields | HIGH | New fields (`last_seen`, `_links`) required by schema |
| Field types | MEDIUM | All fields must match OpenAPI schema types |

## Migration Path

1. **Client Code Changes Required**:
   - Update endpoint from `/api/users/{id}` to `/api/v2/users/{id}`
   - Implement Bearer token authentication (replace cookie handling)
   - Update response field extraction: `data["about_me"]` → `data["profile"]["about_me"]`
   - Handle new required fields: `last_seen`, `_links`

2. **Testing Strategy**:
   - Validate deprecated endpoint returns stable 404 error
   - Validate new endpoint requires Bearer token (no fallback to cookies)
   - Validate response schema matches OpenAPI contract
   - Validate error messages include migration guidance

## Conclusions

The API evolution is **not backward compatible** with cookie-based clients expecting the old endpoint and response schema. The compatibility policy enforces a stable deprecation path with clear error messages guiding clients toward the new `/api/v2` endpoint. However, clients must implement code changes to handle:
- New authentication mechanism
- New endpoint URL
- Restructured response schema

No automatic retry logic or transparent fallback is feasible; client code migration is mandatory.
