import re
from dataclasses import Field, field, make_dataclass
from random import choice, sample
from typing import Any, Callable

from robot.api import logger

import OpenApiLibCore.path_functions as pf
from OpenApiLibCore.dto_base import (
    Dto,
    IdDependency,
    PropertyValueConstraint,
    ResourceRelation,
    resolve_schema,
)
from OpenApiLibCore.dto_utils import DefaultDto, GetDtoClassType, GetIdPropertyNameType
from OpenApiLibCore.request_data import RequestData
from OpenApiLibCore.value_utils import IGNORE, get_valid_value


def get_request_data(
    path: str,
    method: str,
    get_dto_class: GetDtoClassType,
    get_id_property_name: GetIdPropertyNameType,
    openapi_spec: dict[str, Any],
) -> RequestData:
    method = method.lower()
    dto_cls_name = get_dto_cls_name(path=path, method=method)
    # The endpoint can contain already resolved Ids that have to be matched
    # against the parametrized endpoints in the paths section.
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
        if dto_class == DefaultDto:
            dto_instance: Dto = DefaultDto()
        else:
            dto_class = make_dataclass(
                cls_name=method_spec.get("operationId", dto_cls_name),
                fields=[],
                bases=(dto_class,),
            )
            dto_instance = dto_class()
        return RequestData(
            dto=dto_instance,
            parameters=parameters,
            params=params,
            headers=headers,
            has_body=False,
        )
    content_schema = resolve_schema(get_content_schema(body_spec))
    headers.update({"content-type": get_content_type(body_spec)})
    dto_data = get_json_data_for_dto_class(
        schema=content_schema,
        dto_class=dto_class,
        get_id_property_name=get_id_property_name,
        operation_id=method_spec.get("operationId", ""),
    )
    if dto_data is None:
        dto_instance = DefaultDto()
    else:
        fields = get_fields_from_dto_data(content_schema, dto_data)
        dto_class = make_dataclass(
            cls_name=method_spec.get("operationId", dto_cls_name),
            fields=fields,
            bases=(dto_class,),
        )
        dto_data = {get_safe_key(key): value for key, value in dto_data.items()}
        dto_instance = dto_class(**dto_data)
    return RequestData(
        dto=dto_instance,
        dto_schema=content_schema,
        parameters=parameters,
        params=params,
        headers=headers,
    )


def get_json_data_for_dto_class(
    schema: dict[str, Any],
    dto_class: Dto | type[Dto],
    get_id_property_name: Callable[
        [str], str | tuple[str, tuple[Callable[[str | int | float], str | int | float]]]
    ],  # FIXME: Protocol for the signature
    operation_id: str = "",
) -> dict[str, Any]:
    def get_constrained_values(property_name: str) -> list[Any]:
        relations = dto_class.get_relations()
        values_list = [
            c.values
            for c in relations
            if (
                isinstance(c, PropertyValueConstraint)
                and c.property_name == property_name
            )
        ]
        # values should be empty or contain 1 list of allowed values
        return values_list.pop() if values_list else []

    def get_dependent_id(
        property_name: str, operation_id: str
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
                    path
                    for path, operation in id_get_paths
                    if operation == operation_id
                ]
            # There could be multiple get_paths, but not one for the current operation
            except ValueError:
                return None
        valid_id = pf.get_valid_id_for_path(
            path=id_get_path, method="get", get_id_property_name=get_id_property_name
        )
        logger.debug(f"get_dependent_id for {id_get_path} returned {valid_id}")
        return valid_id

    json_data: dict[str, Any] = {}

    property_names = []
    for property_name in schema.get("properties", []):
        if constrained_values := get_constrained_values(property_name):
            # do not add properties that are configured to be ignored
            if IGNORE in constrained_values:
                continue
        property_names.append(property_name)

    max_properties = schema.get("maxProperties")
    if max_properties and len(property_names) > max_properties:
        required_properties = schema.get("required", [])
        number_of_optional_properties = max_properties - len(required_properties)
        optional_properties = [
            name for name in property_names if name not in required_properties
        ]
        selected_optional_properties = sample(
            optional_properties, number_of_optional_properties
        )
        property_names = required_properties + selected_optional_properties

    for property_name in property_names:
        properties_schema = schema["properties"][property_name]

        property_type = properties_schema.get("type")
        if property_type is None:
            property_types = properties_schema.get("types")
            if property_types is None:
                if properties_schema.get("properties") is not None:
                    nested_data = get_json_data_for_dto_class(
                        schema=properties_schema,
                        dto_class=DefaultDto,
                        get_id_property_name=get_id_property_name,
                    )
                    json_data[property_name] = nested_data
                    continue
            selected_type_schema = choice(property_types)
            property_type = selected_type_schema["type"]
        if properties_schema.get("readOnly", False):
            continue
        if constrained_values := get_constrained_values(property_name):
            json_data[property_name] = choice(constrained_values)
            continue
        if (
            dependent_id := get_dependent_id(
                property_name=property_name, operation_id=operation_id
            )
        ) is not None:
            json_data[property_name] = dependent_id
            continue
        if property_type == "object":
            object_data = get_json_data_for_dto_class(
                schema=properties_schema,
                dto_class=DefaultDto,
                get_id_property_name=get_id_property_name,
                operation_id="",
            )
            json_data[property_name] = object_data
            continue
        if property_type == "array":
            array_data = get_json_data_for_dto_class(
                schema=properties_schema["items"],
                dto_class=DefaultDto,
                get_id_property_name=get_id_property_name,
                operation_id=operation_id,
            )
            json_data[property_name] = [array_data]
            continue
        json_data[property_name] = get_valid_value(properties_schema)

    return json_data


def get_fields_from_dto_data(
    content_schema: dict[str, Any], dto_data: dict[str, Any]
) -> list[str | tuple[str, type[Any]] | tuple[str, type[Any], Field[Any]]]:
    """Get a dataclasses fields list based on the content_schema and dto_data."""
    fields: list[str | tuple[str, type[Any]] | tuple[str, type[Any], Field[Any]]] = []
    for key, value in dto_data.items():
        required_properties = content_schema.get("required", [])
        safe_key = get_safe_key(key)
        metadata = {"original_property_name": key}
        if key in required_properties:
            # The fields list is used to create a dataclass, so non-default fields
            # must go before fields with a default
            fields.insert(0, (safe_key, type(value), field(metadata=metadata)))
        else:
            fields.append(
                (safe_key, type(value), field(default=None, metadata=metadata))
            )
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
