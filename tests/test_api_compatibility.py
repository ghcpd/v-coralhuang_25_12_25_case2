import json
import pytest
from jsonschema import validate, ValidationError
import os

# Load input data
input_path = os.path.join(os.path.dirname(__file__), "..", "input.json")
with open(input_path, "r") as f:
    INPUT_DATA = json.load(f)

def test_deprecated_endpoint_status():
    """Test that deprecated endpoint returns 404"""
    sample = INPUT_DATA["observations"]["samples"][0]
    assert sample["id"] == "old_client_call_fails_removed_endpoint"
    assert sample["response"]["status"] == 404

def test_deprecated_endpoint_error_schema():
    """Test that deprecated endpoint error matches expected schema"""
    sample = INPUT_DATA["observations"]["samples"][0]
    body = sample["response"]["body"]
    schema = INPUT_DATA["compat_policy"]["deprecated_endpoints"][0]["expected_error_schema"]
    validate(body, schema)

def test_deprecated_endpoint_migration_guidance():
    """Test that error message contains migration guidance"""
    sample = INPUT_DATA["observations"]["samples"][0]
    body = sample["response"]["body"]
    assert "/api/v2/users/{id}" in body["message"]

def test_new_endpoint_auth_header():
    """Test that new endpoint uses bearer auth"""
    sample = INPUT_DATA["observations"]["samples"][1]
    assert sample["id"] == "new_endpoint_success_with_bearer_token"
    headers = sample["request"]["headers"]
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Bearer ")

def test_openapi_auth_requirement():
    """Test that OpenAPI specifies bearer auth for new endpoint"""
    path_spec = INPUT_DATA["server"]["openapi"]["paths"]["/api/v2/users/{id}"]["get"]
    assert "security" in path_spec
    assert path_spec["security"] == [{"bearerAuth": []}]

def test_new_endpoint_response_schema():
    """Test that new endpoint response matches UserV2 schema"""
    sample = INPUT_DATA["observations"]["samples"][1]
    body = sample["response"]["body"]
    schema = INPUT_DATA["server"]["openapi"]["components"]["schemas"]["UserV2"]
    validate(body, schema)

def test_required_response_fields():
    """Test that required fields are present in new response"""
    sample = INPUT_DATA["observations"]["samples"][1]
    body = sample["response"]["body"]
    required = ["id", "username", "last_seen", "_links"]
    for field in required:
        assert field in body, f"Missing required field: {field}"

def test_schema_evolution_about_me_relocation():
    """Test that about_me is relocated to profile.about_me and not at root"""
    sample = INPUT_DATA["observations"]["samples"][1]
    body = sample["response"]["body"]
    assert "about_me" not in body, "about_me should not be at root"
    assert "profile" in body
    assert "about_me" in body["profile"]

def test_field_types_and_formats():
    """Test field types and formats"""
    sample = INPUT_DATA["observations"]["samples"][1]
    body = sample["response"]["body"]
    assert isinstance(body["id"], int)
    assert isinstance(body["username"], str)
    assert isinstance(body["last_seen"], str)
    # Basic date-time format check (ISO 8601)
    assert "T" in body["last_seen"] and "Z" in body["last_seen"]