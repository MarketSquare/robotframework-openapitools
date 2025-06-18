from collections.abc import Mapping, MutableMapping
from pathlib import Path
from types import MappingProxyType
from typing import Iterable

from DataDriver.DataDriver import DataDriver
from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api.deco import library

from OpenApiDriver.openapi_executors import OpenApiExecutors
from OpenApiDriver.openapi_reader import OpenApiReader
from OpenApiLibCore import ValidationLevel
from OpenApiLibCore.annotations import JSON
from openapitools_docs.docstrings import (
    OPENAPIDRIVER_INIT_DOCSTRING,
    OPENAPIDRIVER_LIBRARY_DOCSTRING,
    OPENAPIDRIVER_MODULE_DOCSTRING,
)

__doc__ = OPENAPIDRIVER_MODULE_DOCSTRING

default_str_mapping: Mapping[str, str] = MappingProxyType({})


@library(scope="SUITE", doc_format="HTML")
class OpenApiDriver(OpenApiExecutors, DataDriver):
    __doc__ = OPENAPIDRIVER_LIBRARY_DOCSTRING

    def __init__(  # noqa: PLR0913, pylint: disable=dangerous-default-value
        self,
        source: str,
        origin: str = "",
        base_path: str = "",
        included_paths: Iterable[str] = frozenset(),
        ignored_paths: Iterable[str] = frozenset(),
        ignored_responses: Iterable[int] = frozenset(),
        ignored_testcases: Iterable[tuple[str, str, int]] = frozenset(),
        response_validation: ValidationLevel = ValidationLevel.WARN,
        disable_server_validation: bool = True,
        mappings_path: str | Path = "",
        invalid_property_default_response: int = 422,
        default_id_property_name: str = "id",
        faker_locale: str | list[str] = "",
        require_body_for_invalid_url: bool = False,
        recursion_limit: int = 1,
        recursion_default: JSON = {},
        username: str = "",
        password: str = "",
        security_token: str = "",
        auth: AuthBase | None = None,
        cert: str | tuple[str, str] = "",
        verify_tls: bool | str = True,
        extra_headers: Mapping[str, str] = default_str_mapping,
        cookies: MutableMapping[str, str] | CookieJar | None = None,
        proxies: MutableMapping[str, str] | None = None,
    ) -> None:
        self.__doc__ = OPENAPIDRIVER_INIT_DOCSTRING

        included_paths = included_paths if included_paths else ()
        ignored_paths = ignored_paths if ignored_paths else ()
        ignored_responses = ignored_responses if ignored_responses else ()
        ignored_testcases = ignored_testcases if ignored_testcases else ()

        mappings_path = Path(mappings_path).as_posix()
        OpenApiExecutors.__init__(
            self,
            source=source,
            origin=origin,
            base_path=base_path,
            response_validation=response_validation,
            disable_server_validation=disable_server_validation,
            mappings_path=mappings_path,
            invalid_property_default_response=invalid_property_default_response,
            default_id_property_name=default_id_property_name,
            faker_locale=faker_locale,
            require_body_for_invalid_url=require_body_for_invalid_url,
            recursion_limit=recursion_limit,
            recursion_default=recursion_default,
            username=username,
            password=password,
            security_token=security_token,
            auth=auth,
            cert=cert,
            verify_tls=verify_tls,
            extra_headers=extra_headers,
            cookies=cookies,
            proxies=proxies,
        )

        read_paths_method = self.read_paths
        DataDriver.__init__(
            self,
            reader_class=OpenApiReader,
            read_paths_method=read_paths_method,
            included_paths=included_paths,
            ignored_paths=ignored_paths,
            ignored_responses=ignored_responses,
            ignored_testcases=ignored_testcases,
        )


class DocumentationGenerator(OpenApiDriver):
    __doc__ = OpenApiDriver.__doc__

    @staticmethod
    def get_keyword_names() -> list[str]:
        """Curated keywords for libdoc and libspec."""
        return [
            "test_unauthorized",
            "test_forbidden",
            "test_invalid_url",
            "test_endpoint",
        ]  # pragma: no cover
