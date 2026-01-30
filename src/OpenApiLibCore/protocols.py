"""A module holding Protcols."""

from __future__ import annotations

import builtins
from typing import Any, Callable, Protocol

from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from OpenApiLibCore.models.resource_relations import (
    PathPropertiesConstraint,
    ResourceRelation,
)


class IResponseValidator(Protocol):
    def __call__(
        self, request: RequestsOpenAPIRequest, response: RequestsOpenAPIResponse
    ) -> None: ...


class IGetIdPropertyName(Protocol):
    def __init__(
        self, mappings_module_name: str, default_id_property_name: str
    ) -> None: ...

    def __call__(self, path: str) -> tuple[str, Callable[[str], str]]: ...

    @property
    def default_id_property_name(self) -> str: ...

    @property
    def id_mapping(
        self,
    ) -> dict[str, str | tuple[str, Callable[[object], str]]]: ...


class IRelationsMapping(Protocol):
    # NOTE: This Protocol is used as annotation in a number of the oas_models, which
    # requires this method to prevent a PydanticSchemaGenerationError.
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(cls, handler(str))

    @staticmethod
    def get_path_relations() -> list[PathPropertiesConstraint]: ...

    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]: ...

    @classmethod
    def get_parameter_relations_for_error_code(
        cls, error_code: int
    ) -> list[ResourceRelation]: ...

    @staticmethod
    def get_relations() -> list[ResourceRelation]: ...

    @classmethod
    def get_body_relations_for_error_code(
        cls, error_code: int
    ) -> list[ResourceRelation]: ...


RelationsMappingType = builtins.type[IRelationsMapping]
