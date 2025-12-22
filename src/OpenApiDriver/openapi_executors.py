"""Module containing the classes to perform automatic OpenAPI contract validation."""

from collections.abc import Mapping, MutableMapping
from http import HTTPStatus
from os import getenv
from pathlib import Path
from random import choice
from types import MappingProxyType
from typing import Literal, overload

from requests import Response
from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api import logger
from robot.api.deco import keyword, library
from robot.api.exceptions import SkipExecution
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore import (
    KEYWORD_NAMES as LIBCORE_KEYWORD_NAMES,
)
from OpenApiLibCore import (
    OpenApiLibCore,
    RequestData,
    RequestValues,
    ValidationLevel,
)
from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.models.oas_models import ObjectSchema

run_keyword = BuiltIn().run_keyword
default_str_mapping: Mapping[str, str] = MappingProxyType({})


KEYWORD_NAMES = [
    "test_unauthorized",
    "test_forbidden",
    "test_invalid_url",
    "test_endpoint",
]


@overload
def _run_keyword(
    keyword_name: Literal["get_valid_url"], *args: str
) -> str: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_invalidated_url"], *args: str | int
) -> str: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["authorized_request"], *args: object
) -> Response: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_request_data"], *args: str
) -> RequestData: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_invalid_body_data"], *args: object
) -> dict[str, JSON] | list[JSON]: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_invalidated_parameters"], *args: object
) -> tuple[dict[str, JSON], dict[str, str]]: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["perform_validated_request"], *args: object
) -> None: ...  # pragma: no cover


def _run_keyword(keyword_name: str, *args: object) -> object:
    return run_keyword(keyword_name, *args)  # pyright: ignore[reportArgumentType]


@library(scope="SUITE", doc_format="ROBOT")
class OpenApiExecutors(OpenApiLibCore):
    """Main class providing the keywords and core logic to perform endpoint validations."""

    def __init__(  # noqa: PLR0913, pylint: disable=dangerous-default-value
        self,
        source: str,
        origin: str = "",
        base_path: str = "",
        response_validation: ValidationLevel = ValidationLevel.WARN,
        disable_server_validation: bool = True,
        mappings_path: str | Path = "",
        invalid_data_default_response: int = 422,
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
        super().__init__(
            source=source,
            origin=origin,
            base_path=base_path,
            response_validation=response_validation,
            disable_server_validation=disable_server_validation,
            mappings_path=mappings_path,
            default_id_property_name=default_id_property_name,
            invalid_data_default_response=invalid_data_default_response,
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

    @keyword
    def test_unauthorized(self, path: str, method: str) -> None:
        """
        Perform a request for `method` on the `path`, with no authorization.

        This keyword only passes if the response code is 401: Unauthorized.

        Any authorization parameters used to initialize the library are
        ignored for this request.
        > Note: No headers or (json) body are send with the request. For security
        reasons, the authorization validation should be checked first.
        """
        url = _run_keyword("get_valid_url", path)
        response = self.session.request(
            method=method,
            url=url,
            verify=False,
        )
        if response.status_code != int(HTTPStatus.UNAUTHORIZED):
            raise AssertionError(f"Response {response.status_code} was not 401.")

    @keyword
    def test_forbidden(self, path: str, method: str) -> None:
        """
        Perform a request for `method` on the `path`, with the provided authorization.

        This keyword only passes if the response code is 403: Forbidden.

        For this keyword to pass, the authorization parameters used to initialize the
        library should grant insufficient access rights to the target endpoint.
        > Note: No headers or (json) body are send with the request. For security
        reasons, the access rights validation should be checked first.
        """
        url = _run_keyword("get_valid_url", path)
        response = _run_keyword("authorized_request", url, method)
        if response.status_code != int(HTTPStatus.FORBIDDEN):
            raise AssertionError(f"Response {response.status_code} was not 403.")

    @keyword
    def test_invalid_url(
        self, path: str, method: str, expected_status_code: int = 404
    ) -> None:
        """
        Perform a request for the provided 'path' and 'method' where the url for
        the `path` is invalidated.

        This keyword will be `SKIPPED` if the path contains no parts
        that can be invalidated and there is no mapping for a
        PathPropertiesConstraint for the `expected_status_code`.

        The optional `expected_status_code` parameter (default: 404) can be set to the
        expected status code for APIs that do not return a 404 on invalid urls.

        > Note: Depending on API design, the url may be validated before or after
        validation of headers, query parameters and / or (json) body. By default, no
        parameters are send with the request. The `require_body_for_invalid_url`
        parameter can be set to `True` if needed.
        """
        valid_url = _run_keyword("get_valid_url", path)

        try:
            url = _run_keyword("get_invalidated_url", valid_url, expected_status_code)
        except Exception as exception:
            message = getattr(exception, "message", "")
            if not message.startswith("ValueError"):
                raise exception  # pragma: no cover

            raise SkipExecution(
                f"Path {path} does not contain resource references that "
                f"can be invalidated."
            )

        params, headers, json_data = None, None, None
        if self.require_body_for_invalid_url:
            request_data = _run_keyword("get_request_data", path, method)
            params = request_data.params
            headers = request_data.headers
            json_data = request_data.valid_data
        response = _run_keyword(
            "authorized_request", url, method, params, headers, json_data
        )
        if response.status_code != expected_status_code:
            raise AssertionError(
                f"Response {response.status_code} was not {expected_status_code}"
            )

    @keyword
    def test_endpoint(self, path: str, method: str, status_code: int) -> None:
        """
        Validate that performing the `method` operation on `path` results in a
        `status_code` response.

        This is the main keyword to be used in the `Test Template` keyword when using
        the OpenApiDriver.

        The keyword calls other keywords to generate the neccesary data to perform
        the desired operation and validate the response against the openapi document.
        """
        original_data = {}

        url = _run_keyword("get_valid_url", path)
        request_data = _run_keyword("get_request_data", path, method)
        params = request_data.params
        headers = request_data.headers
        json_data = request_data.valid_data
        # when patching, get the original data to check only patched data has changed
        if method == "PATCH":
            original_data = self.get_original_data(url=url)
        # in case of a status code indicating an error, ensure the error occurs
        if status_code >= int(HTTPStatus.BAD_REQUEST):
            invalidation_keywords: list[str] = []

            if request_data.constraint_mapping.get_body_relations_for_error_code(
                status_code
            ):
                invalidation_keywords.append("get_invalid_body_data")
            if request_data.constraint_mapping.get_parameter_relations_for_error_code(
                status_code
            ):
                invalidation_keywords.append("get_invalidated_parameters")
            if invalidation_keywords:
                invalidation_keyword = choice(invalidation_keywords)
                if invalidation_keyword == "get_invalid_body_data":
                    json_data = _run_keyword(
                        "get_invalid_body_data",
                        url,
                        method,
                        status_code,
                        request_data,
                    )
                else:
                    params, headers = _run_keyword(
                        "get_invalidated_parameters", status_code, request_data
                    )
            # if there are no relations to invalide and the status_code is the default
            # response_code for invalid properties, invalidate properties instead
            elif status_code == self.invalid_data_default_response:
                if (
                    request_data.params_that_can_be_invalidated
                    or request_data.headers_that_can_be_invalidated
                ):
                    params, headers = _run_keyword(
                        "get_invalidated_parameters", status_code, request_data
                    )
                    if request_data.body_schema:
                        json_data = _run_keyword(
                            "get_invalid_body_data",
                            url,
                            method,
                            status_code,
                            request_data,
                        )
                elif request_data.body_schema:
                    json_data = _run_keyword(
                        "get_invalid_body_data", url, method, status_code, request_data
                    )
                else:
                    raise SkipExecution(
                        "No properties or parameters can be invalidated."
                    )
            else:
                raise AssertionError(
                    f"No constraint mapping found to cause status_code {status_code}."
                )
        _run_keyword(
            "perform_validated_request",
            path,
            status_code,
            RequestValues(
                url=url,
                method=method,
                params=params,
                headers=headers,
                json_data=json_data,
            ),
            original_data,
        )
        if status_code < int(HTTPStatus.MULTIPLE_CHOICES) and (
            request_data.has_optional_properties
            or request_data.has_optional_params
            or request_data.has_optional_headers
        ):
            logger.info("Performing request without optional properties and parameters")
            url = _run_keyword("get_valid_url", path)
            request_data = _run_keyword("get_request_data", path, method)
            params = request_data.get_required_params()
            headers = request_data.get_required_headers()
            if isinstance(request_data.body_schema, ObjectSchema):
                json_data = (
                    request_data.get_minimal_body_dict()
                    if request_data.has_body
                    else {}
                )
            original_data = {}
            if method == "PATCH":
                original_data = self.get_original_data(url=url)
            _run_keyword(
                "perform_validated_request",
                path,
                status_code,
                RequestValues(
                    url=url,
                    method=method,
                    params=params,
                    headers=headers,
                    json_data=json_data,
                ),
                original_data,
            )

    def get_original_data(self, url: str) -> dict[str, JSON]:
        """
        Attempt to GET the current data for the given url and return it.

        If the GET request fails, an empty dict is returned.
        """
        original_data = {}
        path = self.get_parameterized_path_from_url(url)
        get_request_data = _run_keyword("get_request_data", path, "GET")
        get_params = get_request_data.params
        get_headers = get_request_data.headers
        response = _run_keyword(
            "authorized_request", url, "GET", get_params, get_headers
        )
        if response.ok:
            original_data = response.json()
        return original_data

    @staticmethod
    def get_keyword_names() -> list[str]:
        """Curated keywords for libdoc and libspec."""
        if getenv("HIDE_INHERITED_KEYWORDS") == "true":
            return KEYWORD_NAMES  # pragma: no cover
        return KEYWORD_NAMES + LIBCORE_KEYWORD_NAMES
