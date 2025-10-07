"""
Module holding the main functions related to data generation
for the requests made as part of keyword exection.
"""

from dataclasses import Field, field, make_dataclass
from itertools import chain
from random import choice
from typing import Any, cast

from robot.api import logger

import OpenApiLibCore.keyword_logic.path_functions as _path_functions
from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.data_constraints.dto_base import Dto
from OpenApiLibCore.data_generation.value_utils import IGNORE
from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    ObjectSchema,
    OpenApiObject,
    OperationObject,
    ParameterObject,
    ResolvedSchemaObjectTypes,
    UnionTypeSchema,
    get_valid_json_data,
)
from OpenApiLibCore.models.request_data import RequestData
from OpenApiLibCore.models.resource_relations import (
    PropertyValueConstraint,
    ResourceRelation,
)
from OpenApiLibCore.protocols import ConstraintMappingType
from OpenApiLibCore.utils.parameter_utils import get_safe_name_for_oas_name


def get_request_data(
    path: str,
    method: str,
    openapi_spec: OpenApiObject,
) -> RequestData:
    method = method.lower()
    dto_cls_name = get_dto_cls_name(path=path, method=method)
    # The path can contain already resolved Ids that have to be matched
    # against the parametrized paths in the paths section.
    spec_path = _path_functions.get_parametrized_path(
        path=path, openapi_spec=openapi_spec
    )
    try:
        path_item = openapi_spec.paths[spec_path]
        operation_spec: OperationObject | None = getattr(path_item, method)
        if operation_spec is None:
            raise AttributeError
        dto_class = operation_spec.dto
    except AttributeError:
        logger.info(
            f"method '{method}' not supported on '{spec_path}, using empty spec."
        )
        operation_spec = OperationObject(operationId="")
        dto_class = None

    parameters, params, headers = get_request_parameters(
        dto_class=dto_class, method_spec=operation_spec
    )
    if operation_spec.requestBody is None:
        dto_instance = _get_dto_instance_for_empty_body(
            dto_class=dto_class,
            dto_cls_name=dto_cls_name,
            method_spec=operation_spec,
        )
        return RequestData(
            valid_data=None,
            dto=dto_instance,
            parameters=parameters,
            params=params,
            headers=headers,
            has_body=False,
        )

    body_schema = operation_spec.requestBody.schema_

    if not body_schema:
        raise ValueError(
            f"No supported content schema found: {operation_spec.requestBody.content}"
        )

    headers.update({"content-type": operation_spec.requestBody.mime_type})

    if isinstance(body_schema, UnionTypeSchema):
        resolved_schemas = body_schema.resolved_schemas
        body_schema = choice(resolved_schemas)

    valid_data = get_valid_json_data(
        schema=body_schema,
        dto_class=dto_class,
        operation_id=operation_spec.operationId,
    )
    dto_instance = _get_dto_instance_from_dto_data(
        schema=body_schema,
        dto_class=dto_class,
        dto_data=valid_data,
        method_spec=operation_spec,
        dto_cls_name=dto_cls_name,
    )
    return RequestData(
        valid_data=valid_data,
        dto=dto_instance,
        body_schema=body_schema,
        parameters=parameters,
        params=params,
        headers=headers,
    )


def _get_dto_instance_for_empty_body(
    dto_class: type[ConstraintMappingType] | None,
    dto_cls_name: str,
    method_spec: OperationObject,
) -> type[Dto]:
    cls_name = method_spec.operationId if method_spec.operationId else dto_cls_name
    base = dto_class if dto_class else Dto
    dto_class_ = make_dataclass(
        cls_name=cls_name,
        fields=[],
        bases=(base,),
    )
    return dto_class_


def _get_dto_instance_from_dto_data(
    schema: ResolvedSchemaObjectTypes,
    dto_class: type[ConstraintMappingType] | None,
    dto_data: JSON,
    method_spec: OperationObject,
    dto_cls_name: str,
) -> type[Dto]:
    if not isinstance(schema, (ObjectSchema, ArraySchema)):
        return _get_dto_instance_for_empty_body(
            dto_class=dto_class, dto_cls_name=dto_cls_name, method_spec=method_spec
        )

    if isinstance(schema, ArraySchema):
        if not dto_data or not isinstance(dto_data, list):
            return _get_dto_instance_for_empty_body(
                dto_class=dto_class, dto_cls_name=dto_cls_name, method_spec=method_spec
            )
        first_item_data = dto_data[0]
        item_object_schema = schema.items
        if isinstance(item_object_schema, UnionTypeSchema):
            resolved_schemas = item_object_schema.resolved_schemas
            item_object_schema = choice(resolved_schemas)
        item_dto = _get_dto_instance_from_dto_data(
            schema=item_object_schema,
            dto_class=dto_class,
            dto_data=first_item_data,
            method_spec=method_spec,
            dto_cls_name=dto_cls_name,
        )
        return item_dto

    assert isinstance(dto_data, dict), (
        "Data consistency error: schema is of type ObjectSchema but dto_data is not a dict."
    )
    fields = get_fields_from_dto_data(schema, dto_data)
    cls_name = method_spec.operationId if method_spec.operationId else dto_cls_name
    base = dto_class if dto_class else Dto
    dto_class_ = make_dataclass(
        cls_name=cls_name,
        fields=fields,
        bases=(base,),
    )
    dto_data = {
        get_safe_name_for_oas_name(key): value for key, value in dto_data.items()
    }
    return cast(Dto, dto_class_(**dto_data))


def get_fields_from_dto_data(
    object_schema: ObjectSchema, dto_data: dict[str, JSON]
) -> list[tuple[str, type[object], Field[object]]]:
    """Get a dataclasses fields list based on the content_schema and dto_data."""
    fields: list[tuple[str, type[object], Field[object]]] = []

    for key, value in dto_data.items():
        safe_key = get_safe_name_for_oas_name(key)
        if key in object_schema.required:
            # The fields list is used to create a dataclass, so non-default fields
            # must go before fields with a default
            field_ = cast(Field[Any], field())  # pylint: disable=invalid-field-call
            fields.insert(0, (safe_key, type(value), field_))
        else:
            field_ = cast(Field[Any], field(default=None))  # pylint: disable=invalid-field-call
            fields.append((safe_key, type(value), field_))
    return fields


def get_dto_cls_name(path: str, method: str) -> str:
    method = method.capitalize()
    path = path.translate({ord(i): None for i in "{}"})
    path_parts = path.split("/")
    path_parts = [p.capitalize() for p in path_parts]
    result = "".join([method, *path_parts])
    return result


def get_request_parameters(
    dto_class: type[ConstraintMappingType] | None, method_spec: OperationObject
) -> tuple[list[ParameterObject], dict[str, Any], dict[str, str]]:
    """Get the methods parameter spec and params and headers with valid data."""
    parameters = method_spec.parameters if method_spec.parameters else []
    parameter_relations = dto_class.get_parameter_relations() if dto_class else []
    query_params = [p for p in parameters if p.in_ == "query"]
    header_params = [p for p in parameters if p.in_ == "header"]
    params = get_parameter_data(query_params, parameter_relations)
    headers = get_parameter_data(header_params, parameter_relations)
    return parameters, params, headers


def get_parameter_data(
    parameters: list[ParameterObject],
    parameter_relations: list[ResourceRelation],
) -> dict[str, str]:
    """Generate a valid list of key-value pairs for all parameters."""
    result: dict[str, str] = {}
    value: Any = None
    for parameter in parameters:
        parameter_name = parameter.name
        # register the oas_name
        _ = get_safe_name_for_oas_name(parameter_name)
        relations = [
            r for r in parameter_relations if r.property_name == parameter_name
        ]
        if constrained_values := [
            r.values for r in relations if isinstance(r, PropertyValueConstraint)
        ]:
            values_to_choose_from = list(chain.from_iterable(constrained_values))
            value = choice(values_to_choose_from)
            if value is IGNORE:
                continue
            result[parameter_name] = value
            continue

        if parameter.schema_ is None:
            continue
        value = parameter.schema_.get_valid_value()
        result[parameter_name] = value
    return result
