import json
import os
from datetime import datetime

import pytest

HERE = os.path.dirname(__file__)
ROOT = os.path.abspath(os.path.join(HERE, ".."))
INPUT_PATH = os.path.join(ROOT, "input.json")


@pytest.fixture(scope="module")
def data():
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _parse_rfc3339_z(dt_str: str):
    # Accepts timestamps like 2017-10-20T15:04:27Z
    try:
        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        # Try a more forgiving ISO parse (no Z)
        return datetime.fromisoformat(dt_str)


def test_input_json_has_required_top_level_keys(data):
    for key in ("client", "server", "observations", "compat_policy"):
        assert key in data, f"input.json missing top-level key: {key}"


def test_deprecated_endpoint_behaviour_has_sample_and_expected_status(data):
    # Find deprecated endpoint rule
    deprecated = data["compat_policy"].get("deprecated_endpoints", [])
    assert deprecated, "No deprecated_endpoints declared in compat_policy"

    rule = deprecated[0]
    expected_status = rule.get("expected_status")
    assert expected_status is not None

    # Find matching observation sample for the deprecated path
    samples = data["observations"].get("samples", [])
    match = None
    for s in samples:
        if s["request"]["path"].startswith(rule["path"].replace("{id}", "")) or s["request"]["path"].startswith("/api/users/"):
            match = s
            break

    assert match is not None, "No observation sample found for deprecated endpoint"
    assert match["response"]["status"] == expected_status, (
        f"Deprecated endpoint expected status {expected_status} but sample has {match['response']['status']}"
    )


def test_deprecated_endpoint_error_schema_matches_expected_shape(data):
    rule = data["compat_policy"]["deprecated_endpoints"][0]
    expected_schema = rule.get("expected_error_schema")
    assert expected_schema, "compat_policy must include expected_error_schema for deprecated endpoints"

    # use the same observation as previous test
    samples = data["observations"]["samples"]
    sample = next(s for s in samples if s["id"] == "old_client_call_fails_removed_endpoint")
    body = sample["response"]["body"]

    # Very small shape validation: required keys and primitive types
    for req in expected_schema.get("required", []):
        assert req in body, f"Deprecated endpoint error body missing required property '{req}'"
        assert isinstance(body[req], str), f"Expected '{req}' to be a string in error body"


def test_migration_guidance_present_in_deprecation_message(data):
    rule = data["compat_policy"]["deprecated_endpoints"][0]
    must_contain = rule.get("message_must_contain", [])
    assert must_contain, "compat_policy must include message_must_contain for deprecated endpoints"

    sample = next(s for s in data["observations"]["samples"] if s["id"] == "old_client_call_fails_removed_endpoint")
    msg = sample["response"]["body"].get("message", "")
    for fragment in must_contain:
        assert fragment in msg, f"Deprecation message must contain '{fragment}' but was: {msg}"


def test_openapi_enforces_bearer_auth_on_new_user_endpoint(data):
    paths = data["server"]["openapi"]["paths"]
    assert "/api/v2/users/{id}" in paths, "/api/v2/users/{id} must be present in OpenAPI"
    get_op = paths["/api/v2/users/{id}"]["get"]
    security = get_op.get("security", [])
    assert any("bearerAuth" in s for s in security), "GET /api/v2/users/{id} must require bearerAuth according to OpenAPI"


def test_userv2_sample_contains_required_fields_and_types(data):
    schema = data["server"]["openapi"]["components"]["schemas"]["UserV2"]
    required = schema.get("required", [])

    sample = next(s for s in data["observations"]["samples"] if s["id"] == "new_endpoint_success_with_bearer_token")
    body = sample["response"]["body"]

    # Check required fields present
    for f in required:
        assert f in body, f"Response missing required field '{f}' as declared in OpenAPI UserV2"

    # Type checks for specific fields
    assert isinstance(body["id"], int), "UserV2.id must be an integer"
    assert isinstance(body["username"], str), "UserV2.username must be a string"
    assert isinstance(body["_links"], dict), "UserV2._links must be an object"

    # last_seen must be RFC3339 / date-time format
    last_seen = body.get("last_seen")
    assert isinstance(last_seen, str), "UserV2.last_seen must be a string"
    # parse using a tolerant parser that accepts trailing 'Z'
    _ = _parse_rfc3339_z(last_seen)


def test_profile_about_me_relocation_and_no_legacy_field_allowed(data):
    sc = data["compat_policy"]["schema_compat"]["user_payload"]
    new_loc = sc["new_location"]
    old_loc = sc["old_location"]
    allow_dual = sc["allow_dual_about_me"]

    sample = next(s for s in data["observations"]["samples"] if s["id"] == "new_endpoint_success_with_bearer_token")
    body = sample["response"]["body"]

    # Ensure new location exists
    # new_location == "profile.about_me"
    profile = body.get("profile")
    assert isinstance(profile, dict) and "about_me" in profile, "Expected profile.about_me to be present in the new payload"

    # Ensure old top-level field is NOT present when allow_dual_about_me == false
    if not allow_dual:
        assert old_loc not in body, f"Top-level legacy field '{old_loc}' must not be present when allow_dual_about_me is false"


def test_old_deprecated_path_absent_from_openapi(data):
    paths = data["server"]["openapi"]["paths"]
    assert "/api/users/{id}" not in paths, "Deprecated path /api/users/{id} must not exist in the current OpenAPI contract"
