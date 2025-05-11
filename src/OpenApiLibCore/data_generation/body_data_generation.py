"""
Module holding the functions related to (json) data generation
for the body of requests made as part of keyword exection.
"""

from random import choice, randint, sample
from typing import Any

from robot.api import logger

import OpenApiLibCore.path_functions as pf
from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.dto_base import (
    Dto,
    IdDependency,
    PropertyValueConstraint,
)
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.models import (
    ArraySchema,
    ObjectSchema,
    SchemaObjectTypes,
    UnionTypeSchema,
)
from OpenApiLibCore.parameter_utils import get_safe_name_for_oas_name
from OpenApiLibCore.protocols import GetIdPropertyNameType
from OpenApiLibCore.value_utils import IGNORE


def get_json_data_for_dto_class(
    schema: SchemaObjectTypes,
    dto_class: type[Dto],
    get_id_property_name: GetIdPropertyNameType,
    operation_id: str | None = None,
) -> JSON:
    if isinstance(schema, UnionTypeSchema):
        chosen_schema = choice(schema.resolved_schemas)
        return get_json_data_for_dto_class(
            schema=chosen_schema,
            dto_class=dto_class,
            get_id_property_name=get_id_property_name,
            operation_id=operation_id,
        )

    match schema:
        case ObjectSchema():
            return get_dict_data_for_dto_class(
                schema=schema,
                dto_class=dto_class,
                get_id_property_name=get_id_property_name,
                operation_id=operation_id,
            )
        case ArraySchema():
            return get_list_data_for_dto_class(
                schema=schema,
                dto_class=dto_class,
                get_id_property_name=get_id_property_name,
                operation_id=operation_id,
            )
        case _:
            return schema.get_valid_value()


def get_dict_data_for_dto_class(
    schema: ObjectSchema,
    dto_class: type[Dto],
    get_id_property_name: GetIdPropertyNameType,
    operation_id: str | None = None,
) -> dict[str, Any]:
    json_data: dict[str, Any] = {}

    property_names = get_property_names_to_process(schema=schema, dto_class=dto_class)

    for property_name in property_names:
        property_schema = schema.properties.root[property_name]
        if property_schema.readOnly:
            continue

        json_data[property_name] = get_data_for_property(
            property_name=property_name,
            property_schema=property_schema,
            get_id_property_name=get_id_property_name,
            dto_class=dto_class,
            operation_id=operation_id,
        )

    return json_data


def get_list_data_for_dto_class(
    schema: ArraySchema,
    dto_class: type[Dto],
    get_id_property_name: GetIdPropertyNameType,
    operation_id: str | None = None,
) -> list[JSON]:
    json_data: list[JSON] = []
    list_item_schema = schema.items
    min_items = schema.minItems if schema.minItems is not None else 0
    max_items = schema.maxItems if schema.maxItems is not None else 1
    number_of_items_to_generate = randint(min_items, max_items)
    for _ in range(number_of_items_to_generate):
        list_item_data = get_json_data_for_dto_class(
            schema=list_item_schema,
            dto_class=dto_class,
            get_id_property_name=get_id_property_name,
            operation_id=operation_id,
        )
        json_data.append(list_item_data)
    return json_data


def get_data_for_property(
    property_name: str,
    property_schema: SchemaObjectTypes,
    get_id_property_name: GetIdPropertyNameType,
    dto_class: type[Dto],
    operation_id: str | None,
) -> JSON:
    if constrained_values := get_constrained_values(
        dto_class=dto_class, property_name=property_name
    ):
        constrained_value = choice(constrained_values)
        # Check if the chosen value is a nested Dto; since a Dto is never
        # instantiated, we can use isinstance(..., type) for this.
        if isinstance(constrained_value, type):
            return get_value_constrained_by_nested_dto(
                property_schema=property_schema,
                nested_dto_class=constrained_value,
                get_id_property_name=get_id_property_name,
                operation_id=operation_id,
            )
        return constrained_value

    if (
        dependent_id := get_dependent_id(
            dto_class=dto_class,
            property_name=property_name,
            operation_id=operation_id,
            get_id_property_name=get_id_property_name,
        )
    ) is not None:
        return dependent_id

    return get_json_data_for_dto_class(
        schema=property_schema,
        dto_class=DefaultDto,
        get_id_property_name=get_id_property_name,
    )


def get_value_constrained_by_nested_dto(
    property_schema: SchemaObjectTypes,
    nested_dto_class: type[Dto],
    get_id_property_name: GetIdPropertyNameType,
    operation_id: str | None,
) -> JSON:
    nested_schema = get_schema_for_nested_dto(property_schema=property_schema)
    nested_value = get_json_data_for_dto_class(
        schema=nested_schema,
        dto_class=nested_dto_class,
        get_id_property_name=get_id_property_name,
        operation_id=operation_id,
    )
    return nested_value


def get_schema_for_nested_dto(property_schema: SchemaObjectTypes) -> SchemaObjectTypes:
    if isinstance(property_schema, UnionTypeSchema):
        chosen_schema = choice(property_schema.resolved_schemas)
        return get_schema_for_nested_dto(chosen_schema)

    return property_schema


def get_property_names_to_process(
    schema: ObjectSchema,
    dto_class: type[Dto],
) -> list[str]:
    property_names = []

    for property_name in schema.properties.root:
        # register the oas_name
        _ = get_safe_name_for_oas_name(property_name)
        if constrained_values := get_constrained_values(
            dto_class=dto_class, property_name=property_name
        ):
            # do not add properties that are configured to be ignored
            if IGNORE in constrained_values:  # type: ignore[comparison-overlap]
                continue
        property_names.append(property_name)

    max_properties = schema.maxProperties
    if max_properties and len(property_names) > max_properties:
        required_properties = schema.required
        number_of_optional_properties = max_properties - len(required_properties)
        optional_properties = [
            name for name in property_names if name not in required_properties
        ]
        selected_optional_properties = sample(
            optional_properties, number_of_optional_properties
        )
        property_names = required_properties + selected_optional_properties

    return property_names


def get_constrained_values(
    dto_class: type[Dto], property_name: str
) -> list[JSON | type[Dto]]:
    relations = dto_class.get_relations()
    values_list = [
        c.values
        for c in relations
        if (isinstance(c, PropertyValueConstraint) and c.property_name == property_name)
    ]
    # values should be empty or contain 1 list of allowed values
    return values_list.pop() if values_list else []


def get_dependent_id(
    dto_class: type[Dto],
    property_name: str,
    operation_id: str | None,
    get_id_property_name: GetIdPropertyNameType,
) -> str | int | float | None:
    relations = dto_class.get_relations()
    # multiple get paths are possible based on the operation being performed
    id_get_paths = [
        (d.get_path, d.operation_id)
        for d in relations
        if (isinstance(d, IdDependency) and d.property_name == property_name)
    ]
    if not id_get_paths:
        return None
    if len(id_get_paths) == 1:
        id_get_path, _ = id_get_paths.pop()
    else:
        try:
            [id_get_path] = [
                path for path, operation in id_get_paths if operation == operation_id
            ]
        # There could be multiple get_paths, but not one for the current operation
        except ValueError:
            return None

    valid_id = pf.get_valid_id_for_path(
        path=id_get_path, get_id_property_name=get_id_property_name
    )
    logger.debug(f"get_dependent_id for {id_get_path} returned {valid_id}")
    return valid_id
