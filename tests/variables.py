from typing import Any

from requests.auth import HTTPDigestAuth

from OpenApiLibCore import IdReference


def get_variables() -> dict[str, Any]:
    """Automatically called by Robot Framework to load variables."""
    id_reference = IdReference(
        property_name="wagegroup_id",
        post_path="/employees",
        error_code=406,
    )
    invalid_id_reference = IdReference(
        property_name="wagegroup_id",
        post_path="/employees/{employee_id}",
        error_code=406,
    )
    extra_headers: dict[str, str] = {"foo": "bar", "eggs": "bacon"}
    return {
        "ID_REFERENCE": id_reference,
        "INVALID_ID_REFERENCE": invalid_id_reference,
        "EXTRA_HEADERS": extra_headers,
        "API_KEY": {"api_key": "Super secret key"},
        "DIGEST_AUTH": HTTPDigestAuth(username="Jane", password="Joe"),
    }
