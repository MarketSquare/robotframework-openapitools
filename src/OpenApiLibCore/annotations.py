"""A module holding Protcols and other reusable compound annotations."""

from typing import Callable, Protocol, Type

from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)

from OpenApiLibCore.dto_base import Dto


class ResponseValidatorType(Protocol):
    def __call__(
        self, request: RequestsOpenAPIRequest, response: RequestsOpenAPIResponse
    ) -> None: ...


class GetDtoClassType(Protocol):
    def __init__(self, mappings_module_name: str) -> None: ...

    def __call__(self, path: str, method: str) -> Type[Dto]: ...


class GetIdPropertyNameType(Protocol):
    def __init__(self, mappings_module_name: str) -> None: ...

    def __call__(
        self, path: str
    ) -> tuple[str, Callable[[str], str] | Callable[[int], int]]: ...
