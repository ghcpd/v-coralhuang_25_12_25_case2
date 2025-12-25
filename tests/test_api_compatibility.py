import json
import re
from datetime import datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INPUT_PATH = ROOT / "input.json"


def load_input():
    with INPUT_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def data():
    return load_input()


def _match_path_template(template: str, path: str) -> bool:
    # Convert /api/users/{id} -> ^/api/users/[^/]+$
    pattern = re.sub(r"\{[^/]+\}", "[^/]+", template)
    pattern = "^" + pattern + "$"
    return re.match(pattern, path) is not None


def _is_rfc3339_z(dt: str) -> bool:
    # Accepts timestamps like 2017-10-20T15:04:27Z
    try:
        datetime.strptime(dt, "%Y-%m-%dT%H:%M:%SZ")
        return True
    except Exception:
        return False


def _find_sample_for_path(samples, path_template):
    for s in samples:
        if _match_path_template(path_template, s["request"]["path"]):
            return s
    return None


def _assert_schema_user_v2(obj):
    # components.schemas.UserV2 required: id, username, last_seen, _links
    assert isinstance(obj, dict), "User object must be a JSON object"
    for k in ("id", "username", "last_seen", "_links"):
        assert k in obj, f"missing required field '{k}' in UserV2"

    assert isinstance(obj["id"], int), "UserV2.id must be integer"
    assert isinstance(obj["username"], str), "UserV2.username must be string"
    assert isinstance(obj["last_seen"], str), "UserV2.last_seen must be string"
    assert _is_rfc3339_z(obj["last_seen"]), (
        "UserV2.last_seen must be RFC3339 UTC (eg 2017-10-20T15:04:27Z)"
    )

    links = obj["_links"]
    assert isinstance(links, dict), "UserV2._links must be an object"
    for rel in ("self", "followers", "followed"):
        assert rel in links, f"UserV2._links missing '{rel}'"
        assert isinstance(links[rel], str), f"UserV2._links.{rel} must be string"

    # profile.about_me is optional in schema but present in observed sample — if present, must be string
    if "profile" in obj:
        assert isinstance(obj["profile"], dict), "profile must be an object"
        if "about_me" in obj["profile"]:
            assert isinstance(obj["profile"]["about_me"], str), (
                "profile.about_me must be a string"
            )


def test_input_json_loadable(data):
    assert "server" in data and "openapi" in data["server"], "input.json missing server.openapi"
    assert "observations" in data, "input.json missing observations"


def test_deprecated_endpoint_is_listed_in_policy(data):
    deprecated = data.get("compat_policy", {}).get("deprecated_endpoints", [])
    assert any(
        ep["path"] == "/api/users/{id}" and ep["method"] == "GET" for ep in deprecated
    ), "Deprecated endpoint /api/users/{id} (GET) must be recorded in compat_policy"


def test_removed_endpoint_returns_stable_error_as_observed(data):
    samples = data["observations"]["samples"]
    ep_policy = next(
        ep for ep in data["compat_policy"]["deprecated_endpoints"] if ep["path"] == "/api/users/{id}"
    )

    sample = _find_sample_for_path(samples, "/api/users/{id}")
    assert sample is not None, "No observed sample found for deprecated endpoint /api/users/{id}"

    resp = sample["response"]
    assert resp["status"] == ep_policy["expected_status"], (
        f"Deprecated endpoint must return status {ep_policy['expected_status']}, got {resp['status']}"
    )

    # validate error schema
    schema = ep_policy.get("expected_error_schema")
    assert schema is not None, "compat_policy must provide expected_error_schema for deprecated endpoint"
    assert isinstance(resp["body"], dict), "error response body must be an object"
    for req in schema.get("required", []):
        assert req in resp["body"], f"error response missing required field '{req}'"

    # message must contain migration guidance
    for fragment in ep_policy.get("message_must_contain", []):
        assert fragment in resp["body"].get("message", ""), (
            f"error.message must mention migration guidance '{fragment}'"
        )


def test_openapi_defines_v2_user_get_and_requires_bearer(data):
    openapi = data["server"]["openapi"]
    paths = openapi.get("paths", {})
    assert "/api/v2/users/{id}" in paths, "/api/v2/users/{id} must be present in OpenAPI"
    get_op = paths["/api/v2/users/{id}"].get("get")
    assert get_op is not None, "GET operation missing for /api/v2/users/{id}"

    # security requirement present and references bearerAuth
    security = get_op.get("security", [])
    assert any("bearerAuth" in list(s.keys()) for s in security), (
        "GET /api/v2/users/{id} must require bearerAuth according to OpenAPI"
    )

    # security scheme defined
    schemes = openapi.get("components", {}).get("securitySchemes", {})
    assert "bearerAuth" in schemes, "securitySchemes must define bearerAuth"
    ba = schemes["bearerAuth"]
    assert ba.get("type") == "http" and ba.get("scheme") == "bearer", (
        "bearerAuth must be HTTP bearer scheme"
    )


def test_observed_success_sample_matches_openapi_user_v2_schema(data):
    samples = data["observations"]["samples"]
    sample = _find_sample_for_path(samples, "/api/v2/users/{id}")
    assert sample is not None, "No observed sample for /api/v2/users/{id}"

    # request-level assertions
    req_headers = sample["request"].get("headers", {})
    assert "Authorization" in req_headers and req_headers["Authorization"].startswith(
        "Bearer"
    ), "Non-browser clients must authenticate with a Bearer token when calling /api/v2/users/{id}"

    # response-level assertions
    resp = sample["response"]
    assert resp["status"] == 200, "Expected 200 success in observed sample for /api/v2/users/{id}"
    assert resp["headers"].get("Content-Type", "").startswith(
        "application/json"
    ), "Response Content-Type must be application/json"

    body = resp["body"]
    _assert_schema_user_v2(body)


def test_schema_migration_disallows_legacy_about_me_when_policy_forbids_it(data):
    policy = data["compat_policy"]["schema_compat"]["user_payload"]
    allow_dual = policy["allow_dual_about_me"]
    old_loc = policy["old_location"]
    new_loc = policy["new_location"]

    samples = data["observations"]["samples"]
    success = _find_sample_for_path(samples, "/api/v2/users/{id}")
    assert success is not None, "missing success sample for /api/v2/users/{id}"
    body = success["response"]["body"]

    # resolve old and new locations in the sample
    def has_path(obj, dotted):
        cur = obj
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return False
            cur = cur[part]
        return True

    if not allow_dual:
        assert not has_path(body, old_loc), (
            f"legacy field '{old_loc}' must NOT be present when allow_dual_about_me is false"
        )
    # new location MUST exist in the successful v2 sample
    assert has_path(body, new_loc), f"new location '{new_loc}' must be present in v2 responses"


def test_client_assumption_conflicts_with_server_contract(data):
    # The deployed client in input.client assumes cookie-based session and /api/users/{id} endpoint
    client = data["client"]
    assert "code" in client
    assert "Cookie" in client.get("code", "") or "session" in json.dumps(client), (
        "Client appears to rely on cookie-based session authentication"
    )

    # But the OpenAPI requires bearer token for v2 and the old endpoint is removed -> incompatibility
    openapi = data["server"]["openapi"]
    assert "/api/users/{id}" not in openapi.get("paths", {}), (
        "Old endpoint /api/users/{id} must not appear in OpenAPI (it was removed)"
    )


def test_observations_cover_migration_guidance_in_changelog_and_errors(data):
    # Ensure changelog mentions migration and observed error points to new endpoint
    changelog = data["observations"].get("changelog", "")
    assert "/api/v2" in changelog, "Changelog should mention /api/v2 migration"

    # The error sample message should also mention the v2 path (checked earlier) -- reinforce here
    samples = data["observations"]["samples"]
    err = _find_sample_for_path(samples, "/api/users/{id}")
    assert err is not None
    assert "/api/v2/users/{id}" in err["response"]["body"].get("message", ""), (
        "Error message should point callers to /api/v2/users/{id}"
    )
