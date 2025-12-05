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
from OpenApiLibCore.models import IGNORE
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
from OpenApiLibCore.protocols import IConstraintMapping
from OpenApiLibCore.utils.parameter_utils import get_safe_name_for_oas_name


def get_request_data(
    path: str,
    method: str,
    openapi_spec: OpenApiObject,
) -> RequestData:
    method = method.lower()
    mapping_cls_name = get_mapping_cls_name(path=path, method=method)
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
        constraint_mapping = operation_spec.constraint_mapping
    except AttributeError:
        logger.info(
            f"method '{method}' not supported on '{spec_path}, using empty spec."
        )
        operation_spec = OperationObject(operationId="")
        constraint_mapping = None

    parameters, params, headers = get_request_parameters(
        constraint_mapping=constraint_mapping, method_spec=operation_spec
    )
    if operation_spec.requestBody is None:
        constraint_mapping = _get_mapping_dataclass_for_empty_body(
            constraint_mapping=constraint_mapping,
            mapping_cls_name=mapping_cls_name,
            method_spec=operation_spec,
        )
        return RequestData(
            valid_data=None,
            constraint_mapping=constraint_mapping,
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

    if operation_spec.requestBody.mime_type:
        if "content-type" in headers:  # pragma: no branch
            key_value = "content-type"
        else:
            key_value = "Content-Type"
        headers.update({key_value: operation_spec.requestBody.mime_type})

    if isinstance(body_schema, UnionTypeSchema):
        body_schema = choice(body_schema.resolved_schemas)

    valid_data = get_valid_json_data(
        schema=body_schema,
        constraint_mapping=constraint_mapping,
        operation_id=operation_spec.operationId,
    )
    constraint_mapping = _get_mapping_dataclass_from_valid_data(
        schema=body_schema,
        constraint_mapping=constraint_mapping,
        valid_data=valid_data,
        method_spec=operation_spec,
        mapping_cls_name=mapping_cls_name,
    )
    return RequestData(
        valid_data=valid_data,
        constraint_mapping=constraint_mapping,
        body_schema=body_schema,
        parameters=parameters,
        params=params,
        headers=headers,
    )


def _get_mapping_dataclass_for_empty_body(
    constraint_mapping: type[IConstraintMapping] | None,
    mapping_cls_name: str,
    method_spec: OperationObject,
) -> type[IConstraintMapping]:
    cls_name = method_spec.operationId if method_spec.operationId else mapping_cls_name
    base = constraint_mapping if constraint_mapping else Dto
    mapping_class = make_dataclass(
        cls_name=cls_name,
        fields=[],
        bases=(base,),
    )
    return mapping_class


def _get_mapping_dataclass_from_valid_data(
    schema: ResolvedSchemaObjectTypes,
    constraint_mapping: type[IConstraintMapping] | None,
    valid_data: JSON,
    method_spec: OperationObject,
    mapping_cls_name: str,
) -> type[IConstraintMapping]:
    if not isinstance(schema, (ObjectSchema, ArraySchema)):
        return _get_mapping_dataclass_for_empty_body(
            constraint_mapping=constraint_mapping,
            mapping_cls_name=mapping_cls_name,
            method_spec=method_spec,
        )

    if isinstance(schema, ArraySchema):
        if not valid_data or not isinstance(valid_data, list):
            return _get_mapping_dataclass_for_empty_body(
                constraint_mapping=constraint_mapping,
                mapping_cls_name=mapping_cls_name,
                method_spec=method_spec,
            )
        first_item_data = valid_data[0]
        item_object_schema = schema.items
        if isinstance(item_object_schema, UnionTypeSchema):
            resolved_schemas = item_object_schema.resolved_schemas
            item_object_schema = choice(resolved_schemas)
        mapping_dataclass = _get_mapping_dataclass_from_valid_data(
            schema=item_object_schema,
            constraint_mapping=constraint_mapping,
            valid_data=first_item_data,
            method_spec=method_spec,
            mapping_cls_name=mapping_cls_name,
        )
        return mapping_dataclass

    assert isinstance(valid_data, dict), (
        "Data consistency error: schema is of type ObjectSchema but valid_data is not a dict."
    )
    fields = get_dataclass_fields(object_schema=schema, valid_data=valid_data)
    cls_name = method_spec.operationId if method_spec.operationId else mapping_cls_name
    base = constraint_mapping if constraint_mapping else Dto
    mapping_dataclass = make_dataclass(
        cls_name=cls_name,
        fields=fields,
        bases=(base,),
    )
    return mapping_dataclass


def get_dataclass_fields(
    object_schema: ObjectSchema, valid_data: dict[str, JSON]
) -> list[tuple[str, type[object], Field[object]]]:
    """Get a dataclasses fields list based on the object_schema and valid_data."""
    fields: list[tuple[str, type[object], Field[object]]] = []

    for key, value in valid_data.items():
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


def get_mapping_cls_name(path: str, method: str) -> str:
    method = method.capitalize()
    path = path.translate({ord(i): None for i in "{}"})
    path_parts = path.split("/")
    path_parts = [p.capitalize() for p in path_parts]
    result = "".join([method, *path_parts])
    return result


def get_request_parameters(
    constraint_mapping: type[IConstraintMapping] | None, method_spec: OperationObject
) -> tuple[list[ParameterObject], dict[str, Any], dict[str, str]]:
    """Get the methods parameter spec and params and headers with valid data."""
    parameters = method_spec.parameters if method_spec.parameters else []
    parameter_relations = (
        constraint_mapping.get_parameter_relations() if constraint_mapping else []
    )
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

        if parameter.schema_ is None:  # pragma: no branch
            continue
        value = parameter.schema_.get_valid_value()
        result[parameter_name] = value
    return result
