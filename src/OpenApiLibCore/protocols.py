"""A module holding Protcols."""

from __future__ import annotations

from typing import Callable, Protocol, Type

from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)

from OpenApiLibCore.data_constraints import dto_base


class ResponseValidatorType(Protocol):
    def __call__(
        self, request: RequestsOpenAPIRequest, response: RequestsOpenAPIResponse
    ) -> None: ...  # pragma: no cover


class GetDtoClassType(Protocol):
    def __init__(self, mappings_module_name: str) -> None: ...  # pragma: no cover

    def __call__(
        self, path: str, method: str
    ) -> Type[dto_base.Dto]: ...  # pragma: no cover


class GetIdPropertyNameType(Protocol):
    def __init__(self, mappings_module_name: str) -> None: ...  # pragma: no cover

    def __call__(
        self, path: str
    ) -> tuple[
        str, Callable[[str], str] | Callable[[int], int]
    ]: ...  # pragma: no cover


class GetPathDtoClassType(Protocol):
    def __init__(self, mappings_module_name: str) -> None: ...  # pragma: no cover

    def __call__(self, path: str) -> Type[dto_base.Dto]: ...  # pragma: no cover
