"""
Module holding the (base) classes that can be used by the user of the OpenApiLibCore
to implement custom mappings for dependencies between resources in the API under
test and constraints / restrictions on properties of the resources.
"""

from abc import ABC
from dataclasses import dataclass, fields
from importlib import import_module
from random import choice, shuffle
from typing import Any, Callable, Type
from uuid import uuid4

from robot.api import logger

from OpenApiLibCore.models.oas_models import NullSchema, ObjectSchema, UnionTypeSchema
from OpenApiLibCore.protocols import (
    GetDtoClassType,
    GetIdPropertyNameType,
    GetPathDtoClassType,
)
from OpenApiLibCore.utils import parameter_utils
from OpenApiLibCore.utils.id_mapping import dummy_transformer

NOT_SET = object()
SENTINEL = object()


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
    values: list[Any]
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


@dataclass
class Dto(ABC):
    """Base class for the Dto class."""

    @staticmethod
    def get_path_relations() -> list[PathPropertiesConstraint]:
        """Return the list of Relations for the header and query parameters."""
        return []

    def get_path_relations_for_error_code(
        self, error_code: int
    ) -> list[PathPropertiesConstraint]:
        """Return the list of Relations associated with the given error_code."""
        relations: list[PathPropertiesConstraint] = [
            r
            for r in self.get_path_relations()
            if r.error_code == error_code
            or (
                getattr(r, "invalid_value_error_code", None) == error_code
                and getattr(r, "invalid_value", None) != NOT_SET
            )
        ]
        return relations

    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        """Return the list of Relations for the header and query parameters."""
        return []

    def get_parameter_relations_for_error_code(
        self, error_code: int
    ) -> list[ResourceRelation]:
        """Return the list of Relations associated with the given error_code."""
        relations: list[ResourceRelation] = [
            r
            for r in self.get_parameter_relations()
            if r.error_code == error_code
            or (
                getattr(r, "invalid_value_error_code", None) == error_code
                and getattr(r, "invalid_value", None) != NOT_SET
            )
        ]
        return relations

    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        """Return the list of Relations for the (json) body."""
        return []

    def get_body_relations_for_error_code(
        self, error_code: int
    ) -> list[ResourceRelation]:
        """
        Return the list of Relations associated with the given error_code that are
        applicable to the body / payload of the request.
        """
        relations: list[ResourceRelation] = [
            r
            for r in self.get_relations()
            if r.error_code == error_code
            or (
                getattr(r, "invalid_value_error_code", None) == error_code
                and getattr(r, "invalid_value", None) != NOT_SET
            )
        ]
        return relations

    def get_invalidated_data(
        self,
        schema: ObjectSchema,
        status_code: int,
        invalid_property_default_code: int,
    ) -> dict[str, Any]:
        """Return a data set with one of the properties set to an invalid value or type."""
        properties: dict[str, Any] = self.as_dict()

        relations = self.get_body_relations_for_error_code(error_code=status_code)
        property_names = [r.property_name for r in relations]
        if status_code == invalid_property_default_code:
            # add all properties defined in the schema, including optional properties
            property_names.extend((schema.properties.root.keys()))  # type: ignore[union-attr]
        if not property_names:
            raise ValueError(
                f"No property can be invalidated to cause status_code {status_code}"
            )
        # Remove duplicates, then shuffle the property_names so different properties on
        # the Dto are invalidated when rerunning the test.
        shuffle(list(set(property_names)))
        for property_name in property_names:
            # if possible, invalidate a constraint but send otherwise valid data
            id_dependencies = [
                r
                for r in relations
                if isinstance(r, IdDependency) and r.property_name == property_name
            ]
            if id_dependencies:
                invalid_id = uuid4().hex
                logger.debug(
                    f"Breaking IdDependency for status_code {status_code}: setting "
                    f"{property_name} to {invalid_id}"
                )
                properties[property_name] = invalid_id
                return properties

            invalid_value_from_constraint = [
                r.invalid_value
                for r in relations
                if isinstance(r, PropertyValueConstraint)
                and r.property_name == property_name
                and r.invalid_value_error_code == status_code
            ]
            if (
                invalid_value_from_constraint
                and invalid_value_from_constraint[0] is not NOT_SET
            ):
                properties[property_name] = invalid_value_from_constraint[0]
                logger.debug(
                    f"Using invalid_value {invalid_value_from_constraint[0]} to "
                    f"invalidate property {property_name}"
                )
                return properties

            value_schema = schema.properties.root[property_name]  # type: ignore[union-attr]
            if isinstance(value_schema, UnionTypeSchema):
                # Filter "type": "null" from the possible types since this indicates an
                # optional / nullable property that can only be invalidated by sending
                # invalid data of a non-null type
                non_null_schemas = [
                    s
                    for s in value_schema.resolved_schemas
                    if not isinstance(s, NullSchema)
                ]
                value_schema = choice(non_null_schemas)

            # there may not be a current_value when invalidating an optional property
            current_value = properties.get(property_name, SENTINEL)
            if current_value is SENTINEL:
                # the current_value isn't very relevant as long as the type is correct
                # so no logic to handle Relations / objects / arrays here
                property_type = value_schema.type
                if property_type == "object":
                    current_value = {}
                elif property_type == "array":
                    current_value = []
                else:
                    current_value = value_schema.get_valid_value()

            values_from_constraint = [
                r.values[0]
                for r in relations
                if isinstance(r, PropertyValueConstraint)
                and r.property_name == property_name
            ]

            invalid_value = value_schema.get_invalid_value(
                current_value=current_value,
                values_from_constraint=values_from_constraint,
            )
            properties[property_name] = invalid_value
            logger.debug(
                f"Property {property_name} changed to {invalid_value!r} (received from "
                f"get_invalid_value)"
            )
            return properties
        logger.warn("get_invalidated_data returned unchanged properties")
        return properties  # pragma: no cover

    def as_dict(self) -> dict[Any, Any]:
        """Return the dict representation of the Dto."""
        result = {}

        for field in fields(self):
            field_name = field.name
            if field_name not in self.__dict__:
                continue
            original_name = parameter_utils.get_oas_name_from_safe_name(field_name)
            result[original_name] = getattr(self, field_name)

        return result

    def as_list(self) -> list[Any]:
        """Return the list representation of the Dto."""
        items = self.as_dict()
        return [items] if items else []


@dataclass
class DefaultDto(Dto):
    """A default Dto that can be instantiated."""


def get_dto_class(mappings_module_name: str) -> GetDtoClassType:
    return GetDtoClass(mappings_module_name=mappings_module_name)


class GetDtoClass:
    """Callable class to return Dtos from user-implemented mappings file."""

    def __init__(self, mappings_module_name: str) -> None:
        try:
            mappings_module = import_module(mappings_module_name)
            self.dto_mapping: dict[tuple[str, str], Type[Dto]] = (
                mappings_module.DTO_MAPPING
            )
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"DTO_MAPPING was not imported: {exception}")
            self.dto_mapping = {}

    def __call__(self, path: str, method: str) -> Type[Dto]:
        try:
            return self.dto_mapping[(path, method.lower())]
        except KeyError:
            logger.debug(f"No Dto mapping for {path} {method}.")
            return DefaultDto


def get_path_dto_class(mappings_module_name: str) -> GetPathDtoClassType:
    return GetPathDtoClass(mappings_module_name=mappings_module_name)


class GetPathDtoClass:
    """Callable class to return Dtos from user-implemented mappings file."""

    def __init__(self, mappings_module_name: str) -> None:
        try:
            mappings_module = import_module(mappings_module_name)
            self.dto_mapping: dict[str, Type[Dto]] = mappings_module.PATH_MAPPING
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"PATH_MAPPING was not imported: {exception}")
            self.dto_mapping = {}

    def __call__(self, path: str) -> Type[Dto]:
        raise DeprecationWarning
        try:
            return self.dto_mapping[path]
        except KeyError:
            logger.debug(f"No Dto mapping for {path}.")
            return DefaultDto


def get_id_property_name(
    mappings_module_name: str, default_id_property_name: str
) -> GetIdPropertyNameType:
    return GetIdPropertyName(
        mappings_module_name=mappings_module_name,
        default_id_property_name=default_id_property_name,
    )


class GetIdPropertyName:
    """
    Callable class to return the name of the property that uniquely identifies
    the resource from user-implemented mappings file.
    """

    def __init__(
        self, mappings_module_name: str, default_id_property_name: str
    ) -> None:
        self.default_id_property_name = default_id_property_name
        try:
            mappings_module = import_module(mappings_module_name)
            self.id_mapping: dict[
                str,
                str | tuple[str, Callable[[str], str] | Callable[[int], int]],
            ] = mappings_module.ID_MAPPING
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"ID_MAPPING was not imported: {exception}")
            self.id_mapping = {}

    def __call__(
        self, path: str
    ) -> tuple[str, Callable[[str], str] | Callable[[int], int]]:
        try:
            value_or_mapping = self.id_mapping[path]
            if isinstance(value_or_mapping, str):
                return (value_or_mapping, dummy_transformer)
            return value_or_mapping
        except KeyError:
            return (self.default_id_property_name, dummy_transformer)
