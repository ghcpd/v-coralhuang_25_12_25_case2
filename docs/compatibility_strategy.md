# Compatibility Strategy

## Overview
The API evolution introduces versioning and authentication changes while maintaining backward compatibility through deprecation windows and stable error responses.

## Key Strategies

1. **Deprecation Window**:
   - Maintain deprecated endpoints for 90 days with stable 404 responses.
   - Error messages must include migration guidance to new endpoints.

2. **Authentication Migration**:
   - Enforce bearer token authentication for new endpoints.
   - Old cookie-based auth is no longer supported.

3. **Schema Evolution**:
   - Relocate fields (e.g., `about_me` to `profile.about_me`) without allowing dual presence.
   - Ensure all required fields are present and conform to type/format constraints.

4. **Contract Validation**:
   - All changes must be validated against OpenAPI specifications.
   - Observed samples must match expected behaviors and schemas.

## Enforcement
- Automated tests validate compliance with compatibility policies.
- Failures indicate regressions that must be addressed before deployment.