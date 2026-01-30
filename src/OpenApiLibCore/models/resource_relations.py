from abc import ABC
from dataclasses import dataclass
from typing import Any

from OpenApiLibCore.models import Ignore

NOT_SET = object()


class ResourceRelation(ABC):
    """ABC for all resource relations or restrictions within the API."""

    property_name: str
    error_code: int


@dataclass
class PathPropertiesConstraint(ResourceRelation):
    """The value to be used as the ``path`` for related requests."""

    path: str
    property_name: str = "id"
    invalid_value: Any = NOT_SET
    invalid_value_error_code: int = 422
    error_code: int = 404


@dataclass
class PropertyValueConstraint(ResourceRelation):
    """The allowed values for property_name."""

    property_name: str
    values: list[Any] | Ignore
    invalid_value: Any = NOT_SET
    invalid_value_error_code: int = 422
    error_code: int = 422
    treat_as_mandatory: bool = False


@dataclass
class IdDependency(ResourceRelation):
    """The path where a valid id for the property_name can be gotten (using GET)."""

    property_name: str
    get_path: str
    operation_id: str = ""
    error_code: int = 422


@dataclass
class IdReference(ResourceRelation):
    """The path where a resource that needs this resource's id can be created (using POST)."""

    property_name: str
    post_path: str
    error_code: int = 422


@dataclass
class UniquePropertyValueConstraint(ResourceRelation):
    """The value of the property must be unique within the resource scope."""

    property_name: str
    value: Any
    error_code: int = 422
