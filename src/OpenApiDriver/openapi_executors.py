"""Module containing the classes to perform automatic OpenAPI contract validation."""

from logging import getLogger
from pathlib import Path
from random import choice
from typing import Any, Dict, List, Optional, Tuple, Union

from requests import Response
from requests.auth import AuthBase
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api import SkipExecution
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore import OpenApiLibCore, RequestData, RequestValues, ValidationLevel

run_keyword = BuiltIn().run_keyword


logger = getLogger(__name__)


@library(scope="TEST SUITE", doc_format="ROBOT")
class OpenApiExecutors(OpenApiLibCore):  # pylint: disable=too-many-instance-attributes
    """Main class providing the keywords and core logic to perform endpoint validations."""

    def __init__(  # pylint: disable=too-many-arguments
        self,
        source: str,
        origin: str = "",
        base_path: str = "",
        response_validation: ValidationLevel = ValidationLevel.WARN,
        disable_server_validation: bool = True,
        mappings_path: Union[str, Path] = "",
        invalid_property_default_response: int = 422,
        default_id_property_name: str = "id",
        faker_locale: Optional[Union[str, List[str]]] = None,
        require_body_for_invalid_url: bool = False,
        recursion_limit: int = 1,
        recursion_default: Any = {},
        username: str = "",
        password: str = "",
        security_token: str = "",
        auth: Optional[AuthBase] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
        verify_tls: Optional[Union[bool, str]] = True,
        extra_headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[Dict[str, str], CookieJar]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> None:
        super().__init__(
            source=source,
            origin=origin,
            base_path=base_path,
            response_validation=response_validation,
            disable_server_validation=disable_server_validation,
            mappings_path=mappings_path,
            default_id_property_name=default_id_property_name,
            invalid_property_default_response=invalid_property_default_response,
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
        url: str = run_keyword("get_valid_url", path, method)
        response = self.session.request(
            method=method,
            url=url,
            verify=False,
        )
        if response.status_code != 401:
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
        url: str = run_keyword("get_valid_url", path, method)
        response: Response = run_keyword("authorized_request", url, method)
        if response.status_code != 403:
            raise AssertionError(f"Response {response.status_code} was not 403.")

    @keyword
    def test_invalid_url(
        self, path: str, method: str, expected_status_code: int = 404
    ) -> None:
        """
        Perform a request for the provided 'path' and 'method' where the url for
        the `path` is invalidated.

        This keyword will be `SKIPPED` if the path contains no parts that
        can be invalidated.

        The optional `expected_status_code` parameter (default: 404) can be set to the
        expected status code for APIs that do not return a 404 on invalid urls.

        > Note: Depending on API design, the url may be validated before or after
        validation of headers, query parameters and / or (json) body. By default, no
        parameters are send with the request. The `require_body_for_invalid_url`
        parameter can be set to `True` if needed.
        """
        valid_url: str = run_keyword("get_valid_url", path, method)

        if not (url := run_keyword("get_invalidated_url", valid_url)):
            raise SkipExecution(
                f"Path {path} does not contain resource references that "
                f"can be invalidated."
            )

        params, headers, json_data = None, None, None
        if self.require_body_for_invalid_url:
            request_data = self.get_request_data(method=method, endpoint=path)
            params = request_data.params
            headers = request_data.headers
            dto = request_data.dto
            json_data = dto.as_dict()
        response: Response = run_keyword(
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
        json_data: Optional[Dict[str, Any]] = None
        original_data = None

        url: str = run_keyword("get_valid_url", path, method)
        request_data: RequestData = self.get_request_data(method=method, endpoint=path)
        params = request_data.params
        headers = request_data.headers
        if request_data.has_body:
            json_data = request_data.dto.as_dict()
        # when patching, get the original data to check only patched data has changed
        if method == "PATCH":
            original_data = self.get_original_data(url=url)
        # in case of a status code indicating an error, ensure the error occurs
        if status_code >= 400:
            invalidation_keyword_data = {
                "get_invalid_json_data": [
                    "get_invalid_json_data",
                    url,
                    method,
                    status_code,
                    request_data,
                ],
                "get_invalidated_parameters": [
                    "get_invalidated_parameters",
                    status_code,
                    request_data,
                ],
            }
            invalidation_keywords = []

            if request_data.dto.get_relations_for_error_code(status_code):
                invalidation_keywords.append("get_invalid_json_data")
            if request_data.dto.get_parameter_relations_for_error_code(status_code):
                invalidation_keywords.append("get_invalidated_parameters")
            if invalidation_keywords:
                if (
                    invalidation_keyword := choice(invalidation_keywords)
                ) == "get_invalid_json_data":
                    json_data = run_keyword(
                        *invalidation_keyword_data[invalidation_keyword]
                    )
                else:
                    params, headers = run_keyword(
                        *invalidation_keyword_data[invalidation_keyword]
                    )
            # if there are no relations to invalide and the status_code is the default
            # response_code for invalid properties, invalidate properties instead
            elif status_code == self.invalid_property_default_response:
                if (
                    request_data.params_that_can_be_invalidated
                    or request_data.headers_that_can_be_invalidated
                ):
                    params, headers = run_keyword(
                        *invalidation_keyword_data["get_invalidated_parameters"]
                    )
                    if request_data.dto_schema:
                        json_data = run_keyword(
                            *invalidation_keyword_data["get_invalid_json_data"]
                        )
                elif request_data.dto_schema:
                    json_data = run_keyword(
                        *invalidation_keyword_data["get_invalid_json_data"]
                    )
                else:
                    raise SkipExecution(
                        "No properties or parameters can be invalidated."
                    )
            else:
                raise AssertionError(
                    f"No Dto mapping found to cause status_code {status_code}."
                )
        run_keyword(
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
        if status_code < 300 and (
            request_data.has_optional_properties
            or request_data.has_optional_params
            or request_data.has_optional_headers
        ):
            logger.info("Performing request without optional properties and parameters")
            url = run_keyword("get_valid_url", path, method)
            request_data = self.get_request_data(method=method, endpoint=path)
            params = request_data.get_required_params()
            headers = request_data.get_required_headers()
            json_data = (
                request_data.get_minimal_body_dict() if request_data.has_body else None
            )
            original_data = None
            if method == "PATCH":
                original_data = self.get_original_data(url=url)
            run_keyword(
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

    def get_original_data(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Attempt to GET the current data for the given url and return it.

        If the GET request fails, None is returned.
        """
        original_data = None
        path = self.get_parameterized_endpoint_from_url(url)
        get_request_data = self.get_request_data(endpoint=path, method="GET")
        get_params = get_request_data.params
        get_headers = get_request_data.headers
        response: Response = run_keyword(
            "authorized_request", url, "GET", get_params, get_headers
        )
        if response.ok:
            original_data = response.json()
        return original_data
