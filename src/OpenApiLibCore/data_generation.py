import re
from copy import deepcopy
from dataclasses import Field, dataclass, field, make_dataclass
from functools import cached_property
from logging import getLogger
from random import choice, sample
from typing import Any, Callable, Type

from OpenApiLibCore import path_functions as pf
from OpenApiLibCore.dto_base import Dto, resolve_schema, ResourceRelation, PropertyValueConstraint, IdDependency
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.value_utils import IGNORE, get_valid_value

logger = getLogger(__name__)


@dataclass
class RequestData:
    """Helper class to manage parameters used when making requests."""

    dto: Dto | DefaultDto = field(default_factory=DefaultDto)
    dto_schema: dict[str, Any] = field(default_factory=dict)
    parameters: list[dict[str, Any]] = field(default_factory=list)
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, Any] = field(default_factory=dict)
    has_body: bool = True

    def __post_init__(self) -> None:
        # prevent modification by reference
        self.dto_schema = deepcopy(self.dto_schema)
        self.parameters = deepcopy(self.parameters)
        self.params = deepcopy(self.params)
        self.headers = deepcopy(self.headers)

    @property
    def has_optional_properties(self) -> bool:
        """Whether or not the dto data (json data) contains optional properties."""

        def is_required_property(property_name: str) -> bool:
            return property_name in self.dto_schema.get("required", [])

        properties = (self.dto.as_dict()).keys()
        return not all(map(is_required_property, properties))

    @property
    def has_optional_params(self) -> bool:
        """Whether or not any of the query parameters are optional."""

        def is_optional_param(query_param: str) -> bool:
            optional_params = [
                p.get("name")
                for p in self.parameters
                if p.get("in") == "query" and not p.get("required")
            ]
            return query_param in optional_params

        return any(map(is_optional_param, self.params))

    @cached_property
    def params_that_can_be_invalidated(self) -> set[str]:
        """
        The query parameters that can be invalidated by violating data
        restrictions, data type or by not providing them in a request.
        """
        result = set()
        params = [h for h in self.parameters if h.get("in") == "query"]
        for param in params:
            # required params can be omitted to invalidate a request
            if param["required"]:
                result.add(param["name"])
                continue

            schema = resolve_schema(param["schema"])
            if schema.get("type", None):
                param_types = [schema]
            else:
                param_types = schema["types"]
            for param_type in param_types:
                # any basic non-string type except "null" can be invalidated by
                # replacing it with a string
                if param_type["type"] not in ["string", "array", "object", "null"]:
                    result.add(param["name"])
                    continue
                # enums, strings and arrays with boundaries can be invalidated
                if set(param_type.keys()).intersection(
                    {
                        "enum",
                        "minLength",
                        "maxLength",
                        "minItems",
                        "maxItems",
                    }
                ):
                    result.add(param["name"])
                    continue
                # an array of basic non-string type can be invalidated by replacing the
                # items in the array with strings
                if param_type["type"] == "array" and param_type["items"][
                    "type"
                ] not in [
                    "string",
                    "array",
                    "object",
                    "null",
                ]:
                    result.add(param["name"])
        return result

    @property
    def has_optional_headers(self) -> bool:
        """Whether or not any of the headers are optional."""

        def is_optional_header(header: str) -> bool:
            optional_headers = [
                p.get("name")
                for p in self.parameters
                if p.get("in") == "header" and not p.get("required")
            ]
            return header in optional_headers

        return any(map(is_optional_header, self.headers))

    @cached_property
    def headers_that_can_be_invalidated(self) -> set[str]:
        """
        The header parameters that can be invalidated by violating data
        restrictions or by not providing them in a request.
        """
        result = set()
        headers = [h for h in self.parameters if h.get("in") == "header"]
        for header in headers:
            # required headers can be omitted to invalidate a request
            if header["required"]:
                result.add(header["name"])
                continue

            schema = resolve_schema(header["schema"])
            if schema.get("type", None):
                header_types = [schema]
            else:
                header_types = schema["types"]
            for header_type in header_types:
                # any basic non-string type except "null" can be invalidated by
                # replacing it with a string
                if header_type["type"] not in ["string", "array", "object", "null"]:
                    result.add(header["name"])
                    continue
                # enums, strings and arrays with boundaries can be invalidated
                if set(header_type.keys()).intersection(
                    {
                        "enum",
                        "minLength",
                        "maxLength",
                        "minItems",
                        "maxItems",
                    }
                ):
                    result.add(header["name"])
                    continue
                # an array of basic non-string type can be invalidated by replacing the
                # items in the array with strings
                if header_type["type"] == "array" and header_type["items"][
                    "type"
                ] not in [
                    "string",
                    "array",
                    "object",
                    "null",
                ]:
                    result.add(header["name"])
        return result

    def get_required_properties_dict(self) -> dict[str, Any]:
        """Get the json-compatible dto data containing only the required properties."""
        relations = self.dto.get_relations()
        mandatory_properties = [
            relation.property_name
            for relation in relations
            if getattr(relation, "treat_as_mandatory", False)
        ]
        required_properties: list[str] = self.dto_schema.get("required", [])
        required_properties.extend(mandatory_properties)

        required_properties_dict: dict[str, Any] = {}
        for key, value in (self.dto.as_dict()).items():
            if key in required_properties:
                required_properties_dict[key] = value
        return required_properties_dict

    def get_minimal_body_dict(self) -> dict[str, Any]:
        required_properties_dict = self.get_required_properties_dict()

        min_properties = self.dto_schema.get("minProperties", 0)
        number_of_optional_properties_to_add = min_properties - len(
            required_properties_dict
        )

        if number_of_optional_properties_to_add < 1:
            return required_properties_dict

        optional_properties_dict = {
            k: v
            for k, v in self.dto.as_dict().items()
            if k not in required_properties_dict
        }
        optional_properties_to_keep = sample(
            sorted(optional_properties_dict), number_of_optional_properties_to_add
        )
        optional_properties_dict = {
            k: v
            for k, v in optional_properties_dict.items()
            if k in optional_properties_to_keep
        }

        return {**required_properties_dict, **optional_properties_dict}

    def get_required_params(self) -> dict[str, str]:
        """Get the params dict containing only the required query parameters."""
        relations = self.dto.get_parameter_relations()
        mandatory_properties = [
            relation.property_name
            for relation in relations
            if getattr(relation, "treat_as_mandatory", False)
        ]
        mandatory_parameters = [p for p in mandatory_properties if p in self.parameters]

        required_parameters = [
            p.get("name") for p in self.parameters if p.get("required")
        ]
        required_parameters.extend(mandatory_parameters)
        return {k: v for k, v in self.params.items() if k in required_parameters}

    def get_required_headers(self) -> dict[str, str]:
        """Get the headers dict containing only the required headers."""
        relations = self.dto.get_parameter_relations()
        mandatory_properties = [
            relation.property_name
            for relation in relations
            if getattr(relation, "treat_as_mandatory", False)
        ]
        mandatory_parameters = [p for p in mandatory_properties if p in self.parameters]

        required_parameters = [
            p.get("name") for p in self.parameters if p.get("required")
        ]
        required_parameters.extend(mandatory_parameters)
        return {k: v for k, v in self.headers.items() if k in required_parameters}


def get_request_data(
    path: str,
    method: str,
    get_dto_class: Callable[[str, str], Type[Dto]],
    get_id_property_name: Callable[
        [str], str | tuple[str, tuple[Callable[[str | int | float], str | int | float]]]
    ],  # FIXME: Protocol for the signature
    openapi_spec: dict[str, Any],
) -> RequestData:
    method = method.lower()
    dto_cls_name = get_dto_cls_name(path=path, method=method)
    # The endpoint can contain already resolved Ids that have to be matched
    # against the parametrized endpoints in the paths section.
    spec_path = pf.get_parametrized_path(path=path, openapi_spec=openapi_spec)
    # TODO: use Protocol to annotate get_dto_class?
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
                        get_id_property_name=get_id_property_name
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
    fields: list[
        str | tuple[str, type[Any]] | tuple[str, type[Any], Field[Any]]
    ] = []
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
            )  # type: ignore[arg-type]
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
