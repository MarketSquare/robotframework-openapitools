# pylint: disable=invalid-name
"""
The OpenApiLibCore package is intended to be used as a dependency for other
Robot Framework libraries that facilitate the testing of OpenAPI / Swagger APIs.
The following classes and constants are exposed to be used by the library user:
- OpenApiLibCore: The class to be imported in the Robot Framework library.
- IdDependency, IdReference, PathPropertiesConstraint, PropertyValueConstraint,
    UniquePropertyValueConstraint: Classes to be subclassed by the library user
    when implementing a custom mapping module (advanced use).
- RelationsMapping, Relation: Base classes that can be used for type annotations.
- IGNORE: A special constant that can be used as a value in the PropertyValueConstraint.
"""

from importlib.metadata import version

from OpenApiLibCore.data_relations.relations_base import RelationsMapping
from OpenApiLibCore.keyword_logic.validation import ValidationLevel
from OpenApiLibCore.models import IGNORE, UNSET
from OpenApiLibCore.models.request_data import RequestData, RequestValues
from OpenApiLibCore.models.resource_relations import (
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    ResourceRelation,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.openapi_libcore import OpenApiLibCore

try:
    __version__ = version("robotframework-openapi-libcore")
except Exception:  # pragma: no cover pylint: disable=broad-exception-caught
    pass


KEYWORD_NAMES = [
    "set_origin",
    "set_security_token",
    "set_basic_auth",
    "set_auth",
    "set_extra_headers",
    "get_request_values",
    "get_request_values_object",
    "get_request_data",
    "get_invalid_body_data",
    "get_invalidated_parameters",
    "get_json_data_with_conflict",
    "get_valid_url",
    "get_valid_id_for_path",
    "get_parameterized_path_from_url",
    "get_ids_from_url",
    "get_invalidated_url",
    "ensure_in_use",
    "authorized_request",
    "perform_authorized_request",
    "validated_request",
    "perform_validated_request",
    "validate_response_using_validator",
    "assert_href_to_resource_is_valid",
    "validate_response",
    "validate_send_response",
]


__all__ = [
    "IGNORE",
    "UNSET",
    "IdDependency",
    "IdReference",
    "OpenApiLibCore",
    "PathPropertiesConstraint",
    "PropertyValueConstraint",
    "RelationsMapping",
    "RequestData",
    "RequestValues",
    "ResourceRelation",
    "UniquePropertyValueConstraint",
    "ValidationLevel",
]
