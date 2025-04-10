"""Module holding the classes used to manage request data."""

from copy import deepcopy
from dataclasses import dataclass, field
from functools import cached_property
from random import sample
from typing import Any

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.dto_base import Dto
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.models import (
    ObjectSchema,
    ParameterObject,
    ResolvedSchemaObjectTypes,
    UnionTypeSchema,
)


@dataclass
class RequestValues:
    """Helper class to hold parameter values needed to make a request."""

    url: str
    method: str
    params: dict[str, JSON] = field(default_factory=dict)
    headers: dict[str, JSON] = field(default_factory=dict)
    json_data: dict[str, JSON] = field(default_factory=dict)

    def override_body_value(self, name: str, value: JSON) -> None:
        if name in self.json_data:
            self.json_data[name] = value

    def override_header_value(self, name: str, value: JSON) -> None:
        if name in self.headers:
            self.headers[name] = value

    def override_param_value(self, name: str, value: JSON) -> None:
        if name in self.params:
            self.params[name] = str(value)

    def override_request_value(self, name: str, value: JSON) -> None:
        self.override_body_value(name=name, value=value)
        self.override_header_value(name=name, value=value)
        self.override_param_value(name=name, value=value)

    def remove_parameters(self, parameters: list[str]) -> None:
        for parameter in parameters:
            _ = self.params.pop(parameter, None)
            _ = self.headers.pop(parameter, None)
            _ = self.json_data.pop(parameter, None)


@dataclass
class RequestData:
    """Helper class to manage parameters used when making requests."""

    dto: Dto | DefaultDto = field(default_factory=DefaultDto)
    body_schema: ObjectSchema | None = None
    parameters: list[ParameterObject] = field(default_factory=list)
    params: dict[str, JSON] = field(default_factory=dict)
    headers: dict[str, JSON] = field(default_factory=dict)
    has_body: bool = True

    def __post_init__(self) -> None:
        # prevent modification by reference
        self.params = deepcopy(self.params)
        self.headers = deepcopy(self.headers)

    @property
    def has_optional_properties(self) -> bool:
        """Whether or not the dto data (json data) contains optional properties."""

        def is_required_property(property_name: str) -> bool:
            return property_name in self.required_property_names

        properties = (self.dto.as_dict()).keys()
        return not all(map(is_required_property, properties))

    @property
    def required_property_names(self) -> list[str]:
        if self.body_schema:
            return self.body_schema.required
        return []

    @property
    def has_optional_params(self) -> bool:
        """Whether or not any of the query parameters are optional."""

        def is_optional_param(query_param: str) -> bool:
            optional_params = [
                p.name for p in self.parameters if p.in_ == "query" and not p.required
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
        params = [h for h in self.parameters if h.in_ == "query"]
        for param in params:
            # required params can be omitted to invalidate a request
            if param.required:
                result.add(param.name)
                continue

            if param.schema_ is None:
                continue

            possible_schemas: list[ResolvedSchemaObjectTypes] = []
            if isinstance(param.schema_, UnionTypeSchema):
                possible_schemas = param.schema_.resolved_schemas
            else:
                possible_schemas = [param.schema_]

            for param_schema in possible_schemas:
                if param_schema.can_be_invalidated:
                    result.add(param.name)

        return result

    @property
    def has_optional_headers(self) -> bool:
        """Whether or not any of the headers are optional."""

        def is_optional_header(header: str) -> bool:
            optional_headers = [
                p.name for p in self.parameters if p.in_ == "header" and not p.required
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
        headers = [h for h in self.parameters if h.in_ == "header"]
        for header in headers:
            # required headers can be omitted to invalidate a request
            if header.required:
                result.add(header.name)
                continue

            if header.schema_ is None:
                continue

            possible_schemas: list[ResolvedSchemaObjectTypes] = []
            if isinstance(header.schema_, UnionTypeSchema):
                possible_schemas = header.schema_.resolved_schemas
            else:
                possible_schemas = [header.schema_]

            for param_schema in possible_schemas:
                if param_schema.can_be_invalidated:
                    result.add(header.name)

        return result

    def get_required_properties_dict(self) -> dict[str, Any]:
        """Get the json-compatible dto data containing only the required properties."""
        relations = self.dto.get_relations()
        mandatory_properties = [
            relation.property_name
            for relation in relations
            if getattr(relation, "treat_as_mandatory", False)
        ]
        required_properties = self.body_schema.required if self.body_schema else []
        required_properties.extend(mandatory_properties)

        required_properties_dict: dict[str, Any] = {}
        for key, value in (self.dto.as_dict()).items():
            if key in required_properties:
                required_properties_dict[key] = value
        return required_properties_dict

    def get_minimal_body_dict(self) -> dict[str, Any]:
        required_properties_dict = self.get_required_properties_dict()

        min_properties = 0
        if self.body_schema and self.body_schema.minProperties is not None:
            min_properties = self.body_schema.minProperties

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

    def get_required_params(self) -> dict[str, JSON]:
        """Get the params dict containing only the required query parameters."""
        return {
            k: v for k, v in self.params.items() if k in self.required_parameter_names
        }

    def get_required_headers(self) -> dict[str, JSON]:
        """Get the headers dict containing only the required headers."""
        return {
            k: v for k, v in self.headers.items() if k in self.required_parameter_names
        }

    @property
    def required_parameter_names(self) -> list[str]:
        """
        The names of the mandatory parameters, including the parameters configured to be
        treated as mandatory using a PropertyValueConstraint.
        """
        relations = self.dto.get_parameter_relations()
        mandatory_property_names = [
            relation.property_name
            for relation in relations
            if getattr(relation, "treat_as_mandatory", False)
        ]
        parameter_names = [p.name for p in self.parameters]
        mandatory_parameters = [
            p for p in mandatory_property_names if p in parameter_names
        ]

        required_parameters = [p.name for p in self.parameters if p.required]
        required_parameters.extend(mandatory_parameters)
        return required_parameters
