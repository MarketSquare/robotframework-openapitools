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
)
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.models import (
    ObjectSchema,
    OpenApiObject,
    OperationObject,
    ParameterObject,
    RequestBodyObject,
    UnionTypeSchema,
)
from OpenApiLibCore.parameter_utils import get_safe_name_for_oas_name
from OpenApiLibCore.protocols import GetDtoClassType, GetIdPropertyNameType
from OpenApiLibCore.request_data import RequestData
from OpenApiLibCore.value_utils import IGNORE

from .body_data_generation import (
    get_json_data_for_dto_class as _get_json_data_for_dto_class,
)


def get_request_data(
    path: str,
    method: str,
    get_dto_class: GetDtoClassType,
    get_id_property_name: GetIdPropertyNameType,
    openapi_spec: OpenApiObject,
) -> RequestData:
    method = method.lower()
    dto_cls_name = get_dto_cls_name(path=path, method=method)
    # The path can contain already resolved Ids that have to be matched
    # against the parametrized paths in the paths section.
    spec_path = pf.get_parametrized_path(path=path, openapi_spec=openapi_spec)
    dto_class = get_dto_class(path=spec_path, method=method)
    try:
        path_item = openapi_spec.paths[spec_path]
        operation_spec = getattr(path_item, method)
        if operation_spec is None:
            raise AttributeError
    except AttributeError:
        logger.info(
            f"method '{method}' not supported on '{spec_path}, using empty spec."
        )
        operation_spec = OperationObject(operationId="")

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
            dto=dto_instance,
            parameters=parameters,
            params=params,
            headers=headers,
            has_body=False,
        )

    headers.update({"content-type": get_content_type(operation_spec.requestBody)})

    body_schema = operation_spec.requestBody
    media_type_dict = body_schema.content
    supported_types = [v for k, v in media_type_dict.items() if "json" in k]
    supported_schemas = [t.schema_ for t in supported_types if t.schema_ is not None]

    if not supported_schemas:
        raise ValueError(f"No supported content schema found: {media_type_dict}")

    if len(supported_schemas) > 1:
        logger.warn(
            f"Multiple JSON media types defined for requestBody, using the first candidate {media_type_dict}"
        )

    schema = supported_schemas[0]

    if isinstance(schema, UnionTypeSchema):
        resolved_schemas = schema.resolved_schemas
        schema = choice(resolved_schemas)

    if not isinstance(schema, ObjectSchema):
        raise ValueError(f"Selected schema is not an object schema: {schema}")

    dto_data = _get_json_data_for_dto_class(
        schema=schema,
        dto_class=dto_class,
        get_id_property_name=get_id_property_name,
        operation_id=operation_spec.operationId,
    )
    dto_instance = _get_dto_instance_from_dto_data(
        object_schema=schema,
        dto_class=dto_class,
        dto_data=dto_data,
        method_spec=operation_spec,
        dto_cls_name=dto_cls_name,
    )
    return RequestData(
        dto=dto_instance,
        body_schema=schema,
        parameters=parameters,
        params=params,
        headers=headers,
    )


def _get_dto_instance_for_empty_body(
    dto_class: type[Dto],
    dto_cls_name: str,
    method_spec: OperationObject,
) -> Dto:
    if dto_class == DefaultDto:
        dto_instance: Dto = DefaultDto()
    else:
        cls_name = method_spec.operationId if method_spec.operationId else dto_cls_name
        dto_class = make_dataclass(
            cls_name=cls_name,
            fields=[],
            bases=(dto_class,),
        )
        dto_instance = dto_class()
    return dto_instance


def _get_dto_instance_from_dto_data(
    object_schema: ObjectSchema,
    dto_class: type[Dto],
    dto_data: JSON,
    method_spec: OperationObject,
    dto_cls_name: str,
) -> Dto:
    if not isinstance(dto_data, (dict, list)):
        return DefaultDto()

    if isinstance(dto_data, list):
        raise NotImplementedError

    fields = get_fields_from_dto_data(object_schema, dto_data)
    cls_name = method_spec.operationId if method_spec.operationId else dto_cls_name
    dto_class_ = make_dataclass(
        cls_name=cls_name,
        fields=fields,
        bases=(dto_class,),
    )
    # dto_data = {get_safe_key(key): value for key, value in dto_data.items()}
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
        # safe_key = get_safe_key(key)
        safe_key = get_safe_name_for_oas_name(key)
        # metadata = {"original_property_name": key}
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


def get_content_type(body_spec: RequestBodyObject) -> str:
    """Get and validate the first supported content type from the requested body spec

    Should be application/json like content type,
    e.g "application/json;charset=utf-8" or "application/merge-patch+json"
    """
    content_types: list[str] = list(body_spec.content.keys())
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
    dto_class: Dto | type[Dto], method_spec: OperationObject
) -> tuple[list[ParameterObject], dict[str, Any], dict[str, str]]:
    """Get the methods parameter spec and params and headers with valid data."""
    parameters = method_spec.parameters if method_spec.parameters else []
    parameter_relations = dto_class.get_parameter_relations()
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
            value = choice(*constrained_values)
            if value is IGNORE:
                continue
            result[parameter_name] = value
            continue

        if parameter.schema_ is None:
            continue
        value = parameter.schema_.get_valid_value()
        result[parameter_name] = value
    return result
