from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from random import sample
from typing import Any

from OpenApiLibCore.dto_base import (
    Dto,
    resolve_schema,
)
from OpenApiLibCore.dto_utils import DefaultDto


@dataclass
class RequestValues:
    """Helper class to hold parameter values needed to make a request."""

    url: str
    method: str
    params: dict[str, Any] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    json_data: dict[str, Any] = field(default_factory=dict)


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
