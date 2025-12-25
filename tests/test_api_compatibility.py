import json
from pathlib import Path
from datetime import datetime
import re
import pytest

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "input.json"


def load_input():
    with INPUT_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def data():
    return load_input()


def find_sample_by_id(samples, sample_id):
    for s in samples:
        if s.get("id") == sample_id:
            return s
    return None


def assert_is_int(value, msg=""):
    assert isinstance(value, int), msg or f"Expected int, got {type(value).__name__}"


def assert_is_str(value, msg=""):
    assert isinstance(value, str), msg or f"Expected str, got {type(value).__name__}"


def assert_datetime_rfc3339_z(s, msg=""):
    # Accepts format like: 2017-10-20T15:04:27Z
    try:
        datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        pytest.fail(msg or f"Value '{s}' is not a RFC3339 UTC timestamp (YYYY-MM-DDTHH:MM:SSZ)")


# 1) Basic input.json integrity
def test_input_contains_expected_top_level_keys(data):
    for k in ("client", "server", "observations", "compat_policy"):
        assert k in data, f"input.json missing top-level key: {k}"


# 2) Deprecated endpoint observed behavior: status code & error schema
def test_deprecated_endpoint_returns_expected_stable_error(data):
    samples = data["observations"]["samples"]
    sample = find_sample_by_id(samples, "old_client_call_fails_removed_endpoint")
    assert sample is not None, "Missing sample for deprecated endpoint"

    response = sample["response"]
    expected = None
    for dep in data["compat_policy"].get("deprecated_endpoints", []):
        if dep["path"] == "/api/users/{id}" and dep["method"] == "GET":
            expected = dep
            break
    assert expected is not None, "Compatibility policy missing deprecated endpoint entry for /api/users/{id}"

    assert response["status"] == expected["expected_status"], (
        f"Deprecated endpoint responded with status {response['status']}, expected {expected['expected_status']}"
    )

    body = response.get("body") or {}
    # Check required keys
    for key in expected.get("expected_error_schema", {}).get("required", []):
        assert key in body, f"Deprecated endpoint error body missing required key '{key}'"

    # Types
    props = expected.get("expected_error_schema", {}).get("properties", {})
    if "error" in props:
        assert_is_str(body.get("error"), "Deprecated endpoint 'error' must be a string")
    if "message" in props:
        assert_is_str(body.get("message"), "Deprecated endpoint 'message' must be a string")

    # Migration hint
    must_contain = expected.get("message_must_contain", [])
    for substr in must_contain:
        assert substr in body.get("message", ""), (
            f"Deprecated endpoint message does not contain required hint '{substr}'"
        )


# 3) Authentication derived from OpenAPI
def test_new_endpoint_requires_bearer_auth_in_openapi(data):
    paths = data["server"]["openapi"]["paths"]
    # Ensure /api/v2/users/{id} exists and requires bearerAuth
    p = "/api/v2/users/{id}"
    assert p in paths, f"OpenAPI missing path {p}"
    get_op = paths[p].get("get")
    assert get_op is not None, f"GET operation missing for path {p}"

    security = get_op.get("security", [])
    assert any("bearerAuth" in s for s in security), "GET /api/v2/users/{id} must require bearerAuth per OpenAPI"


def test_sample_for_new_endpoint_includes_authorization_header(data):
    samples = data["observations"]["samples"]
    sample = find_sample_by_id(samples, "new_endpoint_success_with_bearer_token")
    assert sample is not None, "Missing sample: new_endpoint_success_with_bearer_token"
    headers = sample["request"].get("headers", {})
    auth = headers.get("Authorization") or headers.get("authorization")
    assert auth is not None, "Observed successful request to new endpoint lacks Authorization header"
    assert re.match(r"Bearer\s+\S+", auth), "Authorization header must be a Bearer token"


# 4) Response schema required fields and types for UserV2
def test_new_endpoint_response_conforms_to_userv2_schema(data):
    samples = data["observations"]["samples"]
    sample = find_sample_by_id(samples, "new_endpoint_success_with_bearer_token")
    body = sample["response"]["body"]

    # Schema from openapi
    schema = data["server"]["openapi"]["components"]["schemas"]["UserV2"]

    # required top-level props
    for prop in schema.get("required", []):
        assert prop in body, f"UserV2 response missing required property '{prop}'"

    # id
    assert_is_int(body.get("id"), "UserV2.id must be integer")
    # username
    assert_is_str(body.get("username"), "UserV2.username must be string")
    # last_seen format
    assert_is_str(body.get("last_seen"), "UserV2.last_seen must be a string date-time")
    assert_datetime_rfc3339_z(body.get("last_seen"))

    # profile.about_me exists and is string
    profile = body.get("profile")
    assert isinstance(profile, dict), "UserV2.profile must be an object"
    assert_is_str(profile.get("about_me"), "UserV2.profile.about_me must be string")

    # _links check
    links = body.get("_links")
    assert isinstance(links, dict), "UserV2._links must be an object"
    for link in ("self", "followers", "followed"):
        assert_is_str(links.get(link), f"UserV2._links.{link} must be string")


# 5) Schema evolution rule: about_me relocation and disallow dual presence
def test_about_me_relocation_policy_enforced(data):
    policy = data["compat_policy"]["schema_compat"]["user_payload"]
    allow_dual = policy.get("allow_dual_about_me", False)
    new_loc = policy.get("new_location")  # 'profile.about_me'
    old_loc = policy.get("old_location")  # 'about_me'

    samples = data["observations"]["samples"]
    new_sample = find_sample_by_id(samples, "new_endpoint_success_with_bearer_token")
    body = new_sample["response"]["body"]

    # Helper to check presence
    def present(path, obj):
        parts = path.split(".")
        cur = obj
        for p in parts:
            if not isinstance(cur, dict) or p not in cur:
                return False
            cur = cur[p]
        return True

    old_present = present(old_loc, body)
    new_present = present(new_loc, body)

    assert new_present, f"New location '{new_loc}' must be present in response"
    if not allow_dual:
        assert not (old_present and new_present), (
            "Policy disallows dual presence of 'about_me' at both old and new locations"
        )


# 6) Required fields in schema must be present (already partially tested) - test generic
def test_userv2_required_list_matches_sample(data):
    schema_required = data["server"]["openapi"]["components"]["schemas"]["UserV2"].get("required", [])
    sample = find_sample_by_id(data["observations"]["samples"], "new_endpoint_success_with_bearer_token")
    body = sample["response"]["body"]
    for prop in schema_required:
        assert prop in body, f"Required property '{prop}' declared in schema is absent in sample"


# 7) Response field types and formats - negative checks too
def test_field_types_and_formats_strict(data):
    sample = find_sample_by_id(data["observations"]["samples"], "new_endpoint_success_with_bearer_token")
    body = sample["response"]["body"]

    # id must be int (not string)
    assert isinstance(body["id"], int), "UserV2.id must be integer type"

    # last_seen should be parseable and be in UTC Z-suffix
    assert isinstance(body["last_seen"], str), "UserV2.last_seen must be a string"
    assert body["last_seen"].endswith("Z"), "UserV2.last_seen must use 'Z' to indicate UTC timezone"
    assert_datetime_rfc3339_z(body["last_seen"])


# 8) Deprecated endpoint message is actionable and precise
def test_deprecation_message_points_to_new_endpoint(data):
    sample = find_sample_by_id(data["observations"]["samples"], "old_client_call_fails_removed_endpoint")
    msg = sample["response"]["body"].get("message", "")
    assert "/api/v2/users/{id}" in msg or "/api/v2/users/123" in msg, (
        "Deprecation message must explicitly reference the new endpoint path to guide migration"
    )
