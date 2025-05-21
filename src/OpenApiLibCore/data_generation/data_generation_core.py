"""
Module holding the main functions related to data generation
for the requests made as part of keyword exection.
"""

import re
from dataclasses import Field, field, make_dataclass
from random import choice
from typing import Any, cast

from robot.api import logger

import OpenApiLibCore.path_functions as pf
from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.dto_base import (
    Dto,
    PropertyValueConstraint,
    ResourceRelation,
    resolve_schema,
)
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.parameter_utils import get_safe_name_for_oas_name
from OpenApiLibCore.protocols import GetDtoClassType, GetIdPropertyNameType
from OpenApiLibCore.request_data import RequestData
from OpenApiLibCore.value_utils import IGNORE, get_valid_value

from .body_data_generation import (
    get_json_data_for_dto_class as _get_json_data_for_dto_class,
)


def get_request_data(
    path: str,
    method: str,
    get_dto_class: GetDtoClassType,
    get_id_property_name: GetIdPropertyNameType,
    openapi_spec: dict[str, Any],
) -> RequestData:
    method = method.lower()
    dto_cls_name = get_dto_cls_name(path=path, method=method)
    # The path can contain already resolved Ids that have to be matched
    # against the parametrized paths in the paths section.
    spec_path = pf.get_parametrized_path(path=path, openapi_spec=openapi_spec)
    dto_class = get_dto_class(path=spec_path, method=method)
    try:
        method_spec = openapi_spec["paths"][spec_path][method]
    except KeyError:
        logger.info(
            f"method '{method}' not supported on '{spec_path}, using empty spec."
        )
        method_spec = {}

    parameters, params, headers = get_request_parameters(
        dto_class=dto_class, method_spec=method_spec
    )
    if (body_spec := method_spec.get("requestBody", None)) is None:
        dto_instance = _get_dto_instance_for_empty_body(
            dto_class=dto_class,
            dto_cls_name=dto_cls_name,
            method_spec=method_spec,
        )
        return RequestData(
            dto=dto_instance,
            parameters=parameters,
            params=params,
            headers=headers,
            has_body=False,
        )

    headers.update({"content-type": get_content_type(body_spec)})

    content_schema = resolve_schema(get_content_schema(body_spec))
    dto_data = _get_json_data_for_dto_class(
        schema=content_schema,
        dto_class=dto_class,
        get_id_property_name=get_id_property_name,
        operation_id=method_spec.get("operationId", ""),
    )
    dto_instance = _get_dto_instance_from_dto_data(
        content_schema=content_schema,
        dto_class=dto_class,
        dto_data=dto_data,
        method_spec=method_spec,
        dto_cls_name=dto_cls_name,
    )
    return RequestData(
        dto=dto_instance,
        dto_schema=content_schema,
        parameters=parameters,
        params=params,
        headers=headers,
    )


def _get_dto_instance_for_empty_body(
    dto_class: type[Dto],
    dto_cls_name: str,
    method_spec: dict[str, Any],
) -> Dto:
    if dto_class == DefaultDto:
        dto_instance: Dto = DefaultDto()
    else:
        dto_class = make_dataclass(
            cls_name=method_spec.get("operationId", dto_cls_name),
            fields=[],
            bases=(dto_class,),
        )
        dto_instance = dto_class()
    return dto_instance


def _get_dto_instance_from_dto_data(
    content_schema: dict[str, Any],
    dto_class: type[Dto],
    dto_data: JSON,
    method_spec: dict[str, Any],
    dto_cls_name: str,
) -> Dto:
    if not isinstance(dto_data, (dict, list)):
        return DefaultDto()

    if isinstance(dto_data, list):
        raise NotImplementedError

    fields = get_fields_from_dto_data(content_schema, dto_data)
    dto_class_ = make_dataclass(
        cls_name=method_spec.get("operationId", dto_cls_name),
        fields=fields,
        bases=(dto_class,),
    )
    dto_data = {get_safe_key(key): value for key, value in dto_data.items()}
    return cast(Dto, dto_class_(**dto_data))


def get_fields_from_dto_data(
    content_schema: dict[str, Any], dto_data: dict[str, JSON]
) -> list[tuple[str, type[Any], Field[Any]]]:
    """Get a dataclasses fields list based on the content_schema and dto_data."""
    fields: list[tuple[str, type[Any], Field[Any]]] = []
    for key, value in dto_data.items():
        required_properties = content_schema.get("required", [])
        safe_key = get_safe_key(key)
        metadata = {"original_property_name": key}
        if key in required_properties:
            # The fields list is used to create a dataclass, so non-default fields
            # must go before fields with a default
            field_ = cast(Field[Any], field(metadata=metadata))  # pylint: disable=invalid-field-call
            fields.insert(0, (safe_key, type(value), field_))
        else:
            field_ = cast(Field[Any], field(default=None, metadata=metadata))  # pylint: disable=invalid-field-call
            fields.append((safe_key, type(value), field_))
    return fields


def get_safe_key(key: str) -> str:
    """
    Helper function to convert a valid JSON property name to a string that can be used
    as a Python variable or function / method name.
    """
    key = key.replace("-", "_")
    key = key.replace("@", "_")
    if key[0].isdigit():
        key = f"_{key}"
    return key


def get_dto_cls_name(path: str, method: str) -> str:
    method = method.capitalize()
    path = path.translate({ord(i): None for i in "{}"})
    path_parts = path.split("/")
    path_parts = [p.capitalize() for p in path_parts]
    result = "".join([method, *path_parts])
    return result


def get_content_schema(body_spec: dict[str, Any]) -> dict[str, Any]:
    """Get the content schema from the requestBody spec."""
    content_type = get_content_type(body_spec)
    content_schema = body_spec["content"][content_type]["schema"]
    return resolve_schema(content_schema)


def get_content_type(body_spec: dict[str, Any]) -> str:
    """Get and validate the first supported content type from the requested body spec

    Should be application/json like content type,
    e.g "application/json;charset=utf-8" or "application/merge-patch+json"
    """
    content_types: list[str] = body_spec["content"].keys()
    json_regex = r"application/([a-z\-]+\+)?json(;\s?charset=(.+))?"
    for content_type in content_types:
        if re.search(json_regex, content_type):
            return content_type

    # At present no supported for other types.
    raise NotImplementedError(
        f"Only content types like 'application/json' are supported. "
        f"Content types definded in the spec are '{content_types}'."
    )


def get_request_parameters(
    dto_class: Dto | type[Dto], method_spec: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    """Get the methods parameter spec and params and headers with valid data."""
    parameters = method_spec.get("parameters", [])
    parameter_relations = dto_class.get_parameter_relations()
    query_params = [p for p in parameters if p.get("in") == "query"]
    header_params = [p for p in parameters if p.get("in") == "header"]
    params = get_parameter_data(query_params, parameter_relations)
    headers = get_parameter_data(header_params, parameter_relations)
    return parameters, params, headers


def get_parameter_data(
    parameters: list[dict[str, Any]],
    parameter_relations: list[ResourceRelation],
) -> dict[str, str]:
    """Generate a valid list of key-value pairs for all parameters."""
    result: dict[str, str] = {}
    value: Any = None
    for parameter in parameters:
        parameter_name = parameter["name"]
        # register the oas_name
        _ = get_safe_name_for_oas_name(parameter_name)
        parameter_schema = resolve_schema(parameter["schema"])
        relations = [
            r for r in parameter_relations if r.property_name == parameter_name
        ]
        if constrained_values := [
            r.values for r in relations if isinstance(r, PropertyValueConstraint)
        ]:
            value = choice(*constrained_values)
            if value is IGNORE:
                continue
            result[parameter_name] = value
            continue
        value = get_valid_value(parameter_schema)
        result[parameter_name] = value
    return result
