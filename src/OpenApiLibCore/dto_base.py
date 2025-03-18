"""
Module holding the (base) classes that can be used by the user of the OpenApiLibCore
to implement custom mappings for dependencies between resources in the API under
test and constraints / restrictions on properties of the resources.
"""

from abc import ABC
from copy import deepcopy
from dataclasses import dataclass, fields
from random import choice, shuffle
from typing import Any
from uuid import uuid4

from robot.api import logger

from OpenApiLibCore import value_utils

NOT_SET = object()
SENTINEL = object()


def resolve_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """
    Helper function to resolve allOf, anyOf and oneOf instances in a schema.

    The schemas are used to generate values for headers, query parameters and json
    bodies to be able to make requests.
    """
    # Schema is mutable, so deepcopy to prevent mutation of original schema argument
    resolved_schema = deepcopy(schema)

    # allOf / anyOf / oneOf may be nested, so recursively resolve the dict-typed values
    for key, value in resolved_schema.items():
        if isinstance(value, dict):
            resolved_schema[key] = resolve_schema(value)

    # When handling allOf there should no duplicate keys, so the schema parts can
    # just be merged after resolving the individual parts
    if schema_parts := resolved_schema.pop("allOf", None):
        for schema_part in schema_parts:
            resolved_part = resolve_schema(schema_part)
            resolved_schema = merge_schemas(resolved_schema, resolved_part)
    # Handling anyOf and oneOf requires extra logic to deal with the "type" information.
    # Some properties / parameters may be of different types and each type may have its
    # own restrictions e.g. a parameter that accepts an enum value (string) or an
    # integer value within a certain range.
    # Since the library needs all this information for different purposes, the
    # schema_parts cannot be merged, so a helper property / key "types" is introduced.
    any_of = resolved_schema.pop("anyOf", [])
    one_of = resolved_schema.pop("oneOf", [])
    schema_parts = any_of if any_of else one_of

    for schema_part in schema_parts:
        resolved_part = resolve_schema(schema_part)
        if isinstance(resolved_part, dict) and "type" in resolved_part.keys():
            if "types" in resolved_schema.keys():
                resolved_schema["types"].append(resolved_part)
            else:
                resolved_schema["types"] = [resolved_part]
        else:
            resolved_schema = merge_schemas(resolved_schema, resolved_part)

    return resolved_schema


def merge_schemas(first: dict[str, Any], second: dict[str, Any]) -> dict[str, Any]:
    """Helper method to merge two schemas, recursively."""
    merged_schema = deepcopy(first)
    for key, value in second.items():
        # for existing keys, merge dict and list values, leave others unchanged
        if key in merged_schema.keys():
            if isinstance(value, dict):
                # if the key holds a dict, merge the values (e.g. 'properties')
                merged_schema[key].update(value)
            elif isinstance(value, list):
                # if the key holds a list, extend the values (e.g. 'required')
                merged_schema[key].extend(value)
            elif value != merged_schema[key]:
                logger.debug(
                    f"key '{key}' with value '{merged_schema[key]}'"
                    f" not updated to '{value}'"
                )
        else:
            merged_schema[key] = value
    return merged_schema


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

    def get_relations_for_error_code(self, error_code: int) -> list[ResourceRelation]:
        """Return the list of Relations associated with the given error_code."""
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

    def get_body_relations_for_error_code(
        self, error_code: int
    ) -> list[ResourceRelation]:
        """
        Return the list of Relations associated with the given error_code that are
        applicable to the body / payload of the request.
        """
        all_relations = self.get_relations_for_error_code(error_code=error_code)
        return [r for r in all_relations if not isinstance(r, PathPropertiesConstraint)]

    def get_invalidated_data(
        self,
        schema: dict[str, Any],
        status_code: int,
        invalid_property_default_code: int,
    ) -> dict[str, Any]:
        """Return a data set with one of the properties set to an invalid value or type."""
        properties: dict[str, Any] = self.as_dict()

        schema = resolve_schema(schema)

        relations = self.get_relations_for_error_code(error_code=status_code)
        # filter PathProperyConstraints since in that case no data can be invalidated
        relations = [
            r for r in relations if not isinstance(r, PathPropertiesConstraint)
        ]
        property_names = [r.property_name for r in relations]
        if status_code == invalid_property_default_code and schema.get("properties"):
            # add all properties defined in the schema, including optional properties
            property_names.extend((schema["properties"].keys()))
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
                    f"Breaking IdDependency for status_code {status_code}: replacing "
                    f"{properties[property_name]} with {invalid_id}"
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

            value_schema = schema["properties"][property_name]
            value_schema = resolve_schema(value_schema)

            # Filter "type": "null" from the possible types since this indicates an
            # optional / nullable property that can only be invalidated by sending
            # invalid data of a non-null type
            if value_schemas := value_schema.get("types"):
                if len(value_schemas) > 1:
                    value_schemas = [
                        schema for schema in value_schemas if schema["type"] != "null"
                    ]
                value_schema = choice(value_schemas)

            # there may not be a current_value when invalidating an optional property
            current_value = properties.get(property_name, SENTINEL)
            if current_value is SENTINEL:
                # the current_value isn't very relevant as long as the type is correct
                # so no logic to handle Relations / objects / arrays here
                property_type = value_schema["type"]
                if property_type == "object":
                    current_value = {}
                elif property_type == "array":
                    current_value = []
                else:
                    current_value = value_utils.get_valid_value(value_schema)

            values_from_constraint = [
                r.values[0]
                for r in relations
                if isinstance(r, PropertyValueConstraint)
                and r.property_name == property_name
            ]

            invalid_value = value_utils.get_invalid_value(
                value_schema=value_schema,
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
            original_name = field.metadata["original_property_name"]
            result[original_name] = getattr(self, field_name)

        return result
