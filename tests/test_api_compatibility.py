"""
API Compatibility & Contract Tests

Tests validate:
- Deprecated endpoint behavior (stable_error, 404 status, migration guidance)
- Authentication contract compliance (Bearer token requirements)
- Response schema compliance (required fields, types, field locations)
- Schema evolution rules (field relocation, disallowed dual fields)

All tests load contracts from input.json and validate without external services.
"""

import json
import os
import pytest
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


# ============================================================================
# Test Fixtures & Helpers
# ============================================================================

@pytest.fixture(scope="session")
def input_data() -> Dict[str, Any]:
    """Load input.json from workspace root."""
    input_file = Path(__file__).parent.parent / "input.json"
    assert input_file.exists(), f"input.json not found at {input_file}"
    
    with open(input_file, "r") as f:
        data = json.load(f)
    
    # Validate structure
    assert "client" in data, "input.json missing 'client' key"
    assert "server" in data, "input.json missing 'server' key"
    assert "observations" in data, "input.json missing 'observations' key"
    assert "compat_policy" in data, "input.json missing 'compat_policy' key"
    
    return data


@pytest.fixture(scope="session")
def openapi_spec(input_data: Dict) -> Dict[str, Any]:
    """Extract OpenAPI specification."""
    return input_data["server"]["openapi"]


@pytest.fixture(scope="session")
def observations(input_data: Dict) -> Dict[str, Any]:
    """Extract observations samples."""
    return input_data["observations"]


@pytest.fixture(scope="session")
def compat_policy(input_data: Dict) -> Dict[str, Any]:
    """Extract compatibility policy."""
    return input_data["compat_policy"]


@pytest.fixture(scope="session")
def client_code(input_data: Dict) -> str:
    """Extract client code for context."""
    return input_data["client"]["code"]


# ============================================================================
# Test Suite 1: Deprecated Endpoint Behavior (4 tests)
# ============================================================================

class TestDeprecatedEndpointBehavior:
    """
    Verify deprecated /api/users/{id} endpoint returns stable 404 error
    with clear migration guidance.
    """

    def test_deprecated_endpoint_returns_404_status(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: Deprecated endpoint must return 404 Not Found (stable_error behavior).
        
        The old endpoint /api/users/{id} should not return:
        - 200 (would break migration detection)
        - 500 (would appear as server error, not deprecation)
        - 401 (would suggest auth issue, not deprecation)
        
        Only 404 clearly indicates endpoint removal.
        """
        sample = observations["samples"][0]
        assert sample["id"] == "old_client_call_fails_removed_endpoint"
        
        # Verify status is 404
        assert sample["response"]["status"] == 404, (
            f"Expected deprecated endpoint to return 404, got {sample['response']['status']}"
        )
        
        # Verify compat_policy requires this behavior
        deprecated = compat_policy["deprecated_endpoints"][0]
        assert deprecated["behavior"] == "stable_error"
        assert deprecated["expected_status"] == 404

    def test_deprecated_endpoint_error_schema_valid(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: Error response must match the expected error schema (required fields).
        
        Schema requires: 'error' (string) and 'message' (string)
        """
        sample = observations["samples"][0]
        response_body = sample["response"]["body"]
        expected_schema = compat_policy["deprecated_endpoints"][0]["expected_error_schema"]
        required_fields = expected_schema["required"]
        
        # Verify all required fields present
        for field in required_fields:
            assert field in response_body, (
                f"Error response missing required field '{field}'. "
                f"Response: {response_body}"
            )
            assert isinstance(response_body[field], str), (
                f"Field '{field}' must be string, got {type(response_body[field])}"
            )
        
        # Verify error field is descriptive
        assert response_body["error"], "Error field must not be empty"
        assert response_body["message"], "Message field must not be empty"

    def test_deprecated_endpoint_migration_guidance(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: Error message must contain migration guidance (new endpoint URL).
        
        Policy specifies: message_must_contain = ["/api/v2/users/{id}"]
        This ensures clients receive clear instructions to migrate.
        """
        sample = observations["samples"][0]
        response_body = sample["response"]["body"]
        message = response_body["message"]
        
        migration_hints = compat_policy["deprecated_endpoints"][0]["message_must_contain"]
        
        for hint in migration_hints:
            assert hint in message, (
                f"Error message must contain migration hint '{hint}'\n"
                f"Actual message: '{message}'\n"
                f"Migration hints required: {migration_hints}"
            )

    def test_deprecated_endpoint_stable_behavior(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: Deprecated endpoint must return STABLE error (consistent across calls).
        
        All calls to deprecated endpoint must return same status and error schema.
        This prevents clients from encountering unexpected behaviors (e.g., 
        retry logic that might succeed sometimes).
        """
        # Current observations only have one deprecated sample, but the test
        # validates the structure is deterministic.
        sample = observations["samples"][0]
        response = sample["response"]
        
        deprecated = compat_policy["deprecated_endpoints"][0]
        assert response["status"] == deprecated["expected_status"]
        
        # Verify response has proper error structure (not malformed)
        body = response["body"]
        assert isinstance(body, dict)
        assert "error" in body
        assert "message" in body
        
        # For stable_error, the status code should never vary
        assert deprecated["behavior"] == "stable_error"


# ============================================================================
# Test Suite 2: Authentication Contract (4 tests)
# ============================================================================

class TestAuthenticationContract:
    """
    Verify OpenAPI security requirements and authentication enforcement.
    """

    def test_openapi_requires_bearer_auth(
        self,
        openapi_spec: Dict
    ):
        """
        RULE: New endpoint /api/v2/users/{id} must require Bearer token auth.
        
        OpenAPI must explicitly define security requirement on the path.
        """
        new_endpoint = openapi_spec["paths"]["/api/v2/users/{id}"]["get"]
        
        assert "security" in new_endpoint, (
            "Endpoint /api/v2/users/{id} must define security requirement"
        )
        
        security_reqs = new_endpoint["security"]
        assert isinstance(security_reqs, list)
        assert len(security_reqs) > 0, "Security requirements must not be empty"
        
        # Verify bearerAuth is included
        bearer_required = False
        for req in security_reqs:
            if "bearerAuth" in req:
                bearer_required = True
                break
        
        assert bearer_required, (
            "Endpoint must require 'bearerAuth'. "
            f"Found security requirements: {security_reqs}"
        )

    def test_openapi_defines_bearer_scheme(
        self,
        openapi_spec: Dict
    ):
        """
        RULE: OpenAPI must define the bearerAuth security scheme.
        
        Schema must specify: type='http', scheme='bearer'
        """
        assert "components" in openapi_spec
        assert "securitySchemes" in openapi_spec["components"]
        
        schemes = openapi_spec["components"]["securitySchemes"]
        assert "bearerAuth" in schemes, (
            f"bearerAuth security scheme not defined. "
            f"Available schemes: {list(schemes.keys())}"
        )
        
        bearer_scheme = schemes["bearerAuth"]
        assert bearer_scheme["type"] == "http", (
            f"Bearer scheme type must be 'http', got '{bearer_scheme['type']}'"
        )
        assert bearer_scheme["scheme"] == "bearer", (
            f"Bearer scheme must be 'bearer', got '{bearer_scheme['scheme']}'"
        )

    def test_auth_required_on_new_endpoint(
        self,
        observations: Dict,
        openapi_spec: Dict
    ):
        """
        RULE: Successful requests to new endpoint must include Authorization header.
        
        OpenAPI requires Bearer token; samples must demonstrate proper usage.
        """
        # Find successful new endpoint sample
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        assert sample is not None, "No successful new endpoint sample found"
        
        request_headers = sample["request"]["headers"]
        assert "Authorization" in request_headers, (
            "Successful request to new endpoint must include Authorization header"
        )
        
        auth_value = request_headers["Authorization"]
        assert auth_value.startswith("Bearer "), (
            f"Authorization header must start with 'Bearer ', got '{auth_value}'"
        )

    def test_deprecated_endpoint_no_auth_required_in_policy(
        self,
        compat_policy: Dict
    ):
        """
        RULE: Deprecated endpoint policy does not enforce Bearer auth.
        
        Old endpoint is removed (404), so auth is irrelevant.
        The policy should focus on stable error behavior, not auth.
        """
        deprecated = compat_policy["deprecated_endpoints"][0]
        
        # Policy behavior is 'stable_error', not enforcing auth
        assert deprecated["behavior"] == "stable_error"
        
        # Error schema is defined, but no bearer auth requirement in policy
        # (endpoint is deprecated, not being secured)
        assert "expected_error_schema" in deprecated


# ============================================================================
# Test Suite 3: Response Schema Compliance (4 tests)
# ============================================================================

class TestResponseSchemaCompliance:
    """
    Validate observed responses match OpenAPI schema definitions.
    """

    def test_response_required_fields_present(
        self,
        observations: Dict,
        openapi_spec: Dict
    ):
        """
        RULE: Response must include all required schema fields.
        
        OpenAPI UserV2 schema requires: id, username, last_seen, _links
        """
        # Find new endpoint successful response
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        assert sample is not None
        response_body = sample["response"]["body"]
        
        # Extract required fields from schema
        user_schema = openapi_spec["components"]["schemas"]["UserV2"]
        required_fields = user_schema["required"]
        
        for field in required_fields:
            assert field in response_body, (
                f"Response missing required field '{field}'. "
                f"Required: {required_fields}, "
                f"Actual keys: {list(response_body.keys())}"
            )

    def test_response_field_types_match_schema(
        self,
        observations: Dict,
        openapi_spec: Dict
    ):
        """
        RULE: Response fields must match OpenAPI type definitions.
        
        - id must be integer
        - username must be string
        - last_seen must be string (ISO 8601 format)
        - _links must be object
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        user_schema = openapi_spec["components"]["schemas"]["UserV2"]
        schema_props = user_schema["properties"]
        
        # Validate types for key fields
        assert isinstance(response_body["id"], int), (
            f"'id' must be integer, got {type(response_body['id'])}"
        )
        assert isinstance(response_body["username"], str), (
            f"'username' must be string, got {type(response_body['username'])}"
        )
        assert isinstance(response_body["last_seen"], str), (
            f"'last_seen' must be string, got {type(response_body['last_seen'])}"
        )
        assert isinstance(response_body["_links"], dict), (
            f"'_links' must be object, got {type(response_body['_links'])}"
        )

    def test_response_nested_field_access(
        self,
        observations: Dict
    ):
        """
        RULE: Nested fields must be accessible at documented locations.
        
        Profile.about_me is nested under 'profile' object.
        Must be accessible as: response["profile"]["about_me"]
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        
        # Verify profile exists and contains about_me
        assert "profile" in response_body, (
            f"Response missing 'profile' object. Keys: {list(response_body.keys())}"
        )
        
        profile = response_body["profile"]
        assert isinstance(profile, dict)
        assert "about_me" in profile, (
            f"Profile missing 'about_me'. Profile keys: {list(profile.keys())}"
        )
        
        about_me = profile["about_me"]
        assert isinstance(about_me, str)
        assert len(about_me) > 0, "about_me should not be empty"

    def test_response_hateoas_links_present(
        self,
        observations: Dict
    ):
        """
        RULE: Response must include HATEOAS _links for API navigation.
        
        _links must include 'self', 'followers', 'followed' endpoints.
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        links = response_body["_links"]
        
        required_links = ["self", "followers", "followed"]
        for link in required_links:
            assert link in links, (
                f"_links missing required link '{link}'. "
                f"Available: {list(links.keys())}"
            )
            assert isinstance(links[link], str), (
                f"Link '{link}' must be string URL, got {type(links[link])}"
            )


# ============================================================================
# Test Suite 4: Schema Evolution & Compatibility Rules (4+ tests)
# ============================================================================

class TestSchemaEvolution:
    """
    Enforce explicit compatibility rules for schema evolution.
    """

    def test_schema_compat_about_me_field_relocation(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: 'about_me' field has been relocated to profile.about_me.
        
        This is tracked in compat_policy.schema_compat.user_payload.
        New location: profile.about_me
        Old location: about_me (root)
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        compat_rule = compat_policy["schema_compat"]["user_payload"]
        
        # Verify new location exists
        assert compat_rule["new_location"] == "profile.about_me"
        assert "profile" in response_body
        assert "about_me" in response_body["profile"]
        
        about_me_value = response_body["profile"]["about_me"]
        assert isinstance(about_me_value, str)

    def test_schema_compat_prohibits_dual_about_me(
        self,
        observations: Dict,
        compat_policy: Dict
    ):
        """
        RULE: Dual 'about_me' (both root and profile) is explicitly PROHIBITED.
        
        compat_policy.schema_compat.user_payload.allow_dual_about_me = false
        
        This prevents inconsistency: clients cannot rely on either location
        without checking both. The policy enforces a clean migration path.
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        compat_rule = compat_policy["schema_compat"]["user_payload"]
        
        # Verify dual presence is explicitly prohibited
        assert compat_rule["allow_dual_about_me"] is False, (
            "Dual about_me must be prohibited"
        )
        
        # Verify response does NOT have about_me at root
        assert "about_me" not in response_body, (
            "Response must not have 'about_me' at root when allow_dual_about_me=false. "
            f"Response keys: {list(response_body.keys())}"
        )
        
        # Verify about_me only exists in new location
        assert "profile" in response_body
        assert "about_me" in response_body["profile"]

    def test_schema_evolution_new_required_fields(
        self,
        openapi_spec: Dict
    ):
        """
        RULE: New schema introduces required fields not in old version.
        
        New required fields (v2): last_seen, _links
        Old response had: id, username, about_me
        
        These are breaking changes requiring client code updates.
        """
        user_schema = openapi_spec["components"]["schemas"]["UserV2"]
        required = user_schema["required"]
        
        # New required fields that didn't exist in v1
        new_required = ["last_seen", "_links"]
        for field in new_required:
            assert field in required, (
                f"Schema should require '{field}' (new in v2). "
                f"Required fields: {required}"
            )
            assert field in user_schema["properties"], (
                f"Schema must define '{field}' property"
            )

    def test_schema_field_datetime_format(
        self,
        observations: Dict,
        openapi_spec: Dict
    ):
        """
        RULE: last_seen field must follow ISO 8601 datetime format.
        
        OpenAPI specifies: type=string, format=date-time
        Sample must demonstrate valid ISO 8601 format.
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        response_body = sample["response"]["body"]
        last_seen = response_body["last_seen"]
        
        # Verify ISO 8601 format (YYYY-MM-DDTHH:MM:SSZ or similar)
        try:
            # Python's fromisoformat doesn't handle Z suffix, so strip it
            datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
        except ValueError:
            pytest.fail(
                f"'last_seen' must be valid ISO 8601 format. "
                f"Got: '{last_seen}'"
            )
        
        # Verify schema definition
        user_schema = openapi_spec["components"]["schemas"]["UserV2"]
        last_seen_prop = user_schema["properties"]["last_seen"]
        assert last_seen_prop["type"] == "string"
        assert last_seen_prop["format"] == "date-time"

    def test_endpoint_path_migration_documented(
        self,
        openapi_spec: Dict,
        compat_policy: Dict
    ):
        """
        RULE: API versioning requires documenting path migration.
        
        Old path: /api/users/{id}
        New path: /api/v2/users/{id}
        
        OpenAPI must define new path; compat_policy must list deprecated old path.
        """
        # New endpoint exists
        assert "/api/v2/users/{id}" in openapi_spec["paths"], (
            "OpenAPI must define new /api/v2/users/{id} endpoint"
        )
        
        # Deprecated endpoint is documented in policy
        deprecated = compat_policy["deprecated_endpoints"]
        assert len(deprecated) > 0
        
        deprecated_path = deprecated[0]["path"]
        assert deprecated_path == "/api/users/{id}", (
            f"Deprecated endpoint should be /api/users/{{id}}, got {deprecated_path}"
        )

    def test_api_versioning_separation(
        self,
        openapi_spec: Dict
    ):
        """
        RULE: API versioning must cleanly separate v2 from v1 (removed) endpoints.
        
        OpenAPI should only define v2 endpoints, not unversioned v1.
        This enforces clear deprecation boundaries.
        """
        paths = list(openapi_spec["paths"].keys())
        
        # Must have v2 endpoint
        assert "/api/v2/users/{id}" in paths, "v2 endpoint missing"
        
        # Should NOT have unversioned endpoint (it's deprecated)
        unversioned_patterns = [
            path for path in paths
            if path.startswith("/api/users")
        ]
        assert len(unversioned_patterns) == 0, (
            f"Unversioned /api/users paths should not exist (deprecated). "
            f"Found: {unversioned_patterns}"
        )


# ============================================================================
# Test Suite 5: Integration & Contract Consistency (2 tests)
# ============================================================================

class TestContractConsistency:
    """
    Validate consistency between OpenAPI, samples, and policies.
    """

    def test_openapi_sample_alignment(
        self,
        openapi_spec: Dict,
        observations: Dict
    ):
        """
        RULE: Observed samples must align with OpenAPI contract.
        
        Success sample must:
        - Use endpoint defined in OpenAPI (matching path template)
        - Use response schema defined in OpenAPI
        - Return status codes defined in OpenAPI
        """
        sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                sample = s
                break
        
        assert sample is not None
        
        endpoint_path = sample["request"]["path"]
        status = sample["response"]["status"]
        
        # Verify endpoint matches a defined OpenAPI path template
        # Sample uses concrete path /api/v2/users/123, but OpenAPI defines /api/v2/users/{id}
        # Need to match path patterns
        openapi_paths = list(openapi_spec["paths"].keys())
        matched_path = None
        
        for openapi_path in openapi_paths:
            # Simple pattern matching: /api/v2/users/123 matches /api/v2/users/{id}
            pattern_parts = openapi_path.split("/")
            sample_parts = endpoint_path.split("/")
            
            if len(pattern_parts) == len(sample_parts):
                match = True
                for pattern_part, sample_part in zip(pattern_parts, sample_parts):
                    # Either exact match or pattern is templated {id}
                    if pattern_part != sample_part and not (pattern_part.startswith("{") and pattern_part.endswith("}")):
                        match = False
                        break
                if match:
                    matched_path = openapi_path
                    break
        
        assert matched_path is not None, (
            f"Sample endpoint {endpoint_path} does not match any OpenAPI path. "
            f"Available: {openapi_paths}"
        )
        
        # Verify status is documented
        endpoint_def = openapi_spec["paths"][matched_path]["get"]
        assert "200" in endpoint_def["responses"], (
            f"OpenAPI must document 200 response for {matched_path}"
        )
        assert status == 200, f"Sample must demonstrate success (200), got {status}"

    def test_compat_policy_enforcement_feasible(
        self,
        compat_policy: Dict,
        observations: Dict
    ):
        """
        RULE: Compatibility policy must be enforceable from observed samples.
        
        All rules in compat_policy must be verifiable from the data
        (not require external services or runtime behavior).
        """
        # Verify deprecated endpoint rule is observable in samples
        deprecated_rule = compat_policy["deprecated_endpoints"][0]
        
        sample = None
        for s in observations["samples"]:
            if s["id"] == "old_client_call_fails_removed_endpoint":
                sample = s
                break
        
        assert sample is not None, (
            "No sample demonstrates deprecated endpoint behavior"
        )
        
        # Verify rule matches sample
        assert sample["response"]["status"] == deprecated_rule["expected_status"]
        
        # Verify schema rule is observable
        schema_compat = compat_policy["schema_compat"]["user_payload"]
        success_sample = None
        for s in observations["samples"]:
            if s["id"] == "new_endpoint_success_with_bearer_token":
                success_sample = s
                break
        
        assert success_sample is not None
        response = success_sample["response"]["body"]
        
        # Verify new_location exists
        new_loc = schema_compat["new_location"]
        parts = new_loc.split(".")
        val = response
        for part in parts:
            assert part in val, f"Cannot navigate to {new_loc} in response"
            val = val[part]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
