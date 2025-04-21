"""
# OpenApiLibCore for Robot Framework

The OpenApiLibCore library is a utility library that is meant to simplify creation
of other Robot Framework libraries for API testing based on the information in
an OpenAPI document (also known as Swagger document).
This document explains how to use the OpenApiLibCore library.

My RoboCon 2022 talk about OpenApiDriver and OpenApiLibCore can be found
[here](https://www.youtube.com/watch?v=7YWZEHxk9Ps)

For more information about Robot Framework, see http://robotframework.org.

---

> Note: OpenApiLibCore is still being developed so there are currently
restrictions / limitations that you may encounter when using this library to run
tests against an API. See [Limitations](#limitations) for details.

---

## Installation

If you already have Python >= 3.8 with pip installed, you can simply run:

`pip install --upgrade robotframework-openapi-libcore`

---

## OpenAPI (aka Swagger)

The OpenAPI Specification (OAS) defines a standard, language-agnostic interface
to RESTful APIs, see https://swagger.io/specification/

The OpenApiLibCore implements a number of Robot Framework keywords that make it
easy to interact with an OpenAPI implementation by using the information in the
openapi document (Swagger file), for examply by automatic generation of valid values
for requests based on the schema information in the document.

> Note: OpenApiLibCore is designed for APIs based on the OAS v3
The library has not been tested for APIs based on the OAS v2.

---

## Getting started

Before trying to use the keywords exposed by OpenApiLibCore on the target API
it's recommended to first ensure that the openapi document for the API is valid
under the OpenAPI Specification.

This can be done using the command line interface of a package that is installed as
a prerequisite for OpenApiLibCore.
Both a local openapi.json or openapi.yaml file or one hosted by the API server
can be checked using the `prance validate <reference_to_file>` shell command:

```shell
prance validate --backend=openapi-spec-validator http://localhost:8000/openapi.json
Processing "http://localhost:8000/openapi.json"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!

prance validate --backend=openapi-spec-validator /tests/files/petstore_openapi.yaml
Processing "/tests/files/petstore_openapi.yaml"...
 -> Resolving external references.
Validates OK as OpenAPI 3.0.2!
```

You'll have to change the url or file reference to the location of the openapi
document for your API.

> Note: Although recursion is technically allowed under the OAS, tool support is limited
and changing the OAS to not use recursion is recommended.
OpenApiLibCore has limited support for parsing OpenAPI documents with
recursion in them. See the `recursion_limit` and `recursion_default` parameters.

If the openapi document passes this validation, the next step is trying to do a test
run with a minimal test suite.
The example below can be used, with `source`, `origin` and `path` altered to
fit your situation.

``` robotframework
*** Settings ***
Library            OpenApiLibCore
...                    source=http://localhost:8000/openapi.json
...                    origin=http://localhost:8000

*** Test Cases ***
Getting Started
    ${url}=    Get Valid Url    path=/employees/{employee_id}

```

Running the above suite for the first time may result in an error / failed test.
You should look at the Robot Framework `log.html` to determine the reasons
for the failing tests.
Depending on the reasons for the failures, different solutions are possible.

Details about the OpenApiLibCore library parameters and keywords that you may need can be found
[here](https://marketsquare.github.io/robotframework-openapi-libcore/openapi_libcore.html).

The OpenApiLibCore also support handling of relations between resources within the scope
of the API being validated as well as handling dependencies on resources outside the
scope of the API. In addition there is support for handling restrictions on the values
of parameters and properties.

Details about the `mappings_path` variable usage can be found
[here](https://marketsquare.github.io/robotframework-openapi-libcore/advanced_use.html).

---

## Limitations

There are currently a number of limitations to supported API structures, supported
data types and properties. The following list details the most important ones:
- Only JSON request and response bodies are supported.
- No support for per-endpoint authorization levels.
- Parsing of OAS 3.1 documents is supported by the parsing tools, but runtime behavior is untested.

"""

import json as _json
import sys
from collections.abc import Mapping, MutableMapping
from copy import deepcopy
from functools import cached_property
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generator

from openapi_core import Config, OpenAPI, Spec
from openapi_core.validation.exceptions import ValidationError
from prance import ResolvingParser
from prance.util.url import ResolutionError
from requests import Response, Session
from requests.auth import AuthBase, HTTPBasicAuth
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api import logger
from robot.api.deco import keyword, library
from robot.api.exceptions import FatalError
from robot.libraries.BuiltIn import BuiltIn

import OpenApiLibCore.data_generation as _data_generation
import OpenApiLibCore.data_invalidation as di
import OpenApiLibCore.path_functions as pf
import OpenApiLibCore.path_invalidation as pi
import OpenApiLibCore.resource_relations as rr
import OpenApiLibCore.validation as val
from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.dto_base import Dto, IdReference
from OpenApiLibCore.dto_utils import (
    DEFAULT_ID_PROPERTY_NAME,
    get_dto_class,
    get_id_property_name,
)
from OpenApiLibCore.localized_faker import FAKE
from OpenApiLibCore.models import (
    OpenApiObject,
    PathItemObject,
)
from OpenApiLibCore.oas_cache import PARSER_CACHE, CachedParser
from OpenApiLibCore.parameter_utils import (
    get_oas_name_from_safe_name,
    register_path_parameters,
)
from OpenApiLibCore.protocols import ResponseValidatorType
from OpenApiLibCore.request_data import RequestData, RequestValues

run_keyword = BuiltIn().run_keyword
default_str_mapping: Mapping[str, str] = MappingProxyType({})
default_json_mapping: Mapping[str, JSON] = MappingProxyType({})


@library(scope="SUITE", doc_format="ROBOT")
class OpenApiLibCore:  # pylint: disable=too-many-public-methods
    """
    Main class providing the keywords and core logic to interact with an OpenAPI server.

    Visit the [https://github.com/MarketSquare/robotframework-openapi-libcore | library page]
    for an introduction.
    """

    def __init__(  # noqa: PLR0913, pylint: disable=dangerous-default-value
        self,
        source: str,
        origin: str = "",
        base_path: str = "",
        response_validation: val.ValidationLevel = val.ValidationLevel.WARN,
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
        """
        == Base parameters ==

        === source ===
        An absolute path to an openapi.json or openapi.yaml file or an url to such a file.

        === origin ===
        The server (and port) of the target server. E.g. ``https://localhost:8000``

        === base_path ===
        The routing between ``origin`` and the paths as found in the ``paths``
        section in the openapi document.
        E.g. ``/petshop/v2``.

        == Test case execution ==

        === response_validation ===
         By default, a ``WARN`` is logged when the Response received after a Request does not
         comply with the schema as defined in the openapi document for the given operation. The
         following values are supported:

         - ``DISABLED``: All Response validation errors will be ignored
         - ``INFO``: Any Response validation erros will be logged at ``INFO`` level
         - ``WARN``: Any Response validation erros will be logged at ``WARN`` level
         - ``STRICT``: The Test Case will fail on any Response validation errors

         === disable_server_validation ===
         If enabled by setting this parameter to ``True``, the Response validation will also
         include possible errors for Requests made to a server address that is not defined in
         the list of servers in the openapi document. This generally means that if there is a
         mismatch, every Test Case will raise this error. Note that ``localhost`` and
         ``127.0.0.1`` are not considered the same by Response validation.

        == API-specific configurations ==

        === mappings_path ===
        See [https://marketsquare.github.io/robotframework-openapi-libcore/advanced_use.html | this page]
        for an in-depth explanation.

        === invalid_property_default_response ===
        The default response code for requests with a JSON body that does not comply
        with the schema.
        Example: a value outside the specified range or a string value
        for a property defined as integer in the schema.

        === default_id_property_name ===
        The default name for the property that identifies a resource (i.e. a unique
        entity) within the API.
        The default value for this property name is ``id``.
        If the target API uses a different name for all the resources within the API,
        you can configure it globally using this property.

        If different property names are used for the unique identifier for different
        types of resources, an ``ID_MAPPING`` can be implemented using the ``mappings_path``.

        === faker_locale ===
        A locale string or list of locale strings to pass to the Faker library to be
        used in generation of string data for supported format types.

        === require_body_for_invalid_url ===
         When a request is made against an invalid url, this usually is because of a "404" request;
         a request for a resource that does not exist. Depending on API implementation, when a
         request with a missing or invalid request body is made on a non-existent resource,
         either a 404 or a 422 or 400 Response is normally returned. If the API being tested
         processes the request body before checking if the requested resource exists, set
         this parameter to True.

        == Parsing parameters ==

        === recursion_limit ===
        The recursion depth to which to fully parse recursive references before the
        `recursion_default` is used to end the recursion.

        === recursion_default ===
        The value that is used instead of the referenced schema when the
        `recursion_limit` has been reached.
        The default `{}` represents an empty object in JSON.
        Depending on schema definitions, this may cause schema validation errors.
        If this is the case, 'None' (``${NONE}`` in Robot Framework) or an empty list
        can be tried as an alternative.

        == Security-related parameters ==
        _Note: these parameters are equivalent to those in the ``requests`` library._

        === username ===
        The username to be used for Basic Authentication.

        === password ===
        The password to be used for Basic Authentication.

        === security_token ===
        The token to be used for token based security using the ``Authorization`` header.

        === auth ===
        A [https://requests.readthedocs.io/en/latest/api/#authentication | requests ``AuthBase`` instance]
        to be used for authentication instead of the ``username`` and ``password``.

        === cert ===
        The SSL certificate to use with all requests.
        If string: the path to ssl client cert file (.pem).
        If tuple: the ('cert', 'key') pair.

        === verify_tls ===
        Whether or not to verify the TLS / SSL certificate of the server.
        If boolean: whether or not to verify the server TLS certificate.
        If string: path to a CA bundle to use for verification.

        === extra_headers ===
        A dictionary with extra / custom headers that will be send with every request.
        This parameter can be used to send headers that are not documented in the
        openapi document or to provide an API-key.

        === cookies ===
        A dictionary or
        [https://docs.python.org/3/library/http.cookiejar.html#http.cookiejar.CookieJar | CookieJar object]
        to send with all requests.

        === proxies ===
        A dictionary of 'protocol': 'proxy url' to use for all requests.
        """
        self._source = source
        self._origin = origin
        self._base_path = base_path
        self.response_validation = response_validation
        self.disable_server_validation = disable_server_validation
        self._recursion_limit = recursion_limit
        self._recursion_default = deepcopy(recursion_default)
        self.session = Session()
        # Only username and password, security_token or auth object should be provided
        # if multiple are provided, username and password take precedence
        self.security_token = security_token
        self.auth = auth
        if username:
            self.auth = HTTPBasicAuth(username, password)
        # Requests only allows a string or a tuple[str, str], so ensure cert is a tuple
        # if the passed argument is not a string.
        if not isinstance(cert, str):
            cert = (cert[0], cert[1])
        self.cert = cert
        self.verify = verify_tls
        self.extra_headers = extra_headers
        self.cookies = cookies
        self.proxies = proxies
        self.invalid_property_default_response = invalid_property_default_response
        if mappings_path and str(mappings_path) != ".":
            mappings_path = Path(mappings_path)
            if not mappings_path.is_file():
                logger.warn(f"mappings_path '{mappings_path}' is not a Python module.")
            # Intermediate variable to ensure path.append is possible so we'll never
            # path.pop a location that we didn't append.
            mappings_folder = str(mappings_path.parent)
            sys.path.append(mappings_folder)
            mappings_module_name = mappings_path.stem
            self.get_dto_class = get_dto_class(
                mappings_module_name=mappings_module_name
            )
            self.get_id_property_name = get_id_property_name(
                mappings_module_name=mappings_module_name
            )
            sys.path.pop()
        else:
            self.get_dto_class = get_dto_class(mappings_module_name="no mapping")
            self.get_id_property_name = get_id_property_name(
                mappings_module_name="no mapping"
            )
        if faker_locale:
            FAKE.set_locale(locale=faker_locale)
        self.require_body_for_invalid_url = require_body_for_invalid_url
        # update the globally available DEFAULT_ID_PROPERTY_NAME to the provided value
        DEFAULT_ID_PROPERTY_NAME.id_property_name = default_id_property_name
        self._server_validation_warning_logged = False

    # region: library configuration keywords
    @keyword
    def set_origin(self, origin: str) -> None:
        """
        Set the `origin` after the library is imported.

        This can be done during the `Suite setup` when using DataDriver in situations
        where the OpenAPI document is available on disk but the target host address is
        not known before the test starts.

        In combination with OpenApiLibCore, the `origin` can be used at any point to
        target another server that hosts an API that complies to the same OAS.
        """
        self._origin = origin

    @keyword
    def set_security_token(self, security_token: str) -> None:
        """
        Set the `security_token` after the library is imported.

        After calling this keyword, subsequent requests will use the provided token.
        """
        self.security_token = security_token

    @keyword
    def set_basic_auth(self, username: str, password: str) -> None:
        """
        Set the `username` and `password` used for basic
        authentication after the library is imported.

        After calling this keyword, subsequent requests
        will use the provided credentials.
        """
        if username:
            self.auth = HTTPBasicAuth(username, password)

    @keyword
    def set_auth(self, auth: AuthBase) -> None:
        """
        Set the `auth` used for authentication after the library is imported.

        After calling this keyword, subsequent requests
        will use the provided `auth` instance.
        """
        self.auth = auth

    @keyword
    def set_extra_headers(self, extra_headers: dict[str, str]) -> None:
        """
        Set the `extra_headers` used in requests after the library is imported.

        After calling this keyword, subsequent requests
        will use the provided `extra_headers`.
        """
        self.extra_headers = extra_headers

    # endregion
    # region: data generation keywords
    @keyword
    def get_request_values(
        self,
        path: str,
        method: str,
        overrides: Mapping[str, JSON] = default_json_mapping,
    ) -> RequestValues:
        """Return an object with all (valid) request values needed to make a request."""
        json_data: dict[str, JSON] = {}

        url: str = run_keyword("get_valid_url", path)
        request_data: RequestData = run_keyword("get_request_data", path, method)
        params = request_data.params
        headers = request_data.headers
        if request_data.has_body:
            json_data = request_data.dto.as_dict()

        request_values = RequestValues(
            url=url,
            method=method,
            params=params,
            headers=headers,
            json_data=json_data,
        )

        for name, value in overrides.items():
            if name.startswith(("body_", "header_", "query_")):
                location, _, name_ = name.partition("_")
                oas_name = get_oas_name_from_safe_name(name_)
                if location == "body":
                    request_values.override_body_value(name=oas_name, value=value)
                if location == "header":
                    request_values.override_header_value(name=oas_name, value=value)
                if location == "query":
                    request_values.override_param_value(name=oas_name, value=str(value))
            else:
                oas_name = get_oas_name_from_safe_name(name)
                request_values.override_request_value(name=oas_name, value=value)

        return request_values

    @keyword
    def get_request_data(self, path: str, method: str) -> RequestData:
        """Return an object with valid request data for body, headers and query params."""
        return _data_generation.get_request_data(
            path=path,
            method=method,
            get_dto_class=self.get_dto_class,
            get_id_property_name=self.get_id_property_name,
            openapi_spec=self.openapi_spec,
        )

    @keyword
    def get_invalid_body_data(
        self,
        url: str,
        method: str,
        status_code: int,
        request_data: RequestData,
    ) -> dict[str, JSON]:
        """
        Return `json_data` based on the `dto` on the `request_data` that will cause
        the provided `status_code` for the `method` operation on the `url`.

        > Note: applicable UniquePropertyValueConstraint and IdReference Relations are
            considered before changes to `json_data` are made.
        """
        return di.get_invalid_body_data(
            url=url,
            method=method,
            status_code=status_code,
            request_data=request_data,
            invalid_property_default_response=self.invalid_property_default_response,
        )

    @keyword
    def get_invalidated_parameters(
        self,
        status_code: int,
        request_data: RequestData,
    ) -> tuple[dict[str, JSON], dict[str, JSON]]:
        """
        Returns a version of `params, headers` as present on `request_data` that has
        been modified to cause the provided `status_code`.
        """
        return di.get_invalidated_parameters(
            status_code=status_code,
            request_data=request_data,
            invalid_property_default_response=self.invalid_property_default_response,
        )

    @keyword
    def get_json_data_with_conflict(
        self, url: str, method: str, dto: Dto, conflict_status_code: int
    ) -> dict[str, JSON]:
        """
        Return `json_data` based on the `UniquePropertyValueConstraint` that must be
        returned by the `get_relations` implementation on the `dto` for the given
        `conflict_status_code`.
        """
        return di.get_json_data_with_conflict(
            url=url,
            base_url=self.base_url,
            method=method,
            dto=dto,
            conflict_status_code=conflict_status_code,
        )

    # endregion
    # region: path-related keywords
    @keyword
    def get_valid_url(self, path: str) -> str:
        """
        This keyword returns a valid url for the given `path`.

        If the `path` contains path parameters the Get Valid Id For Path
        keyword will be executed to retrieve valid ids for the path parameters.

        > Note: if valid ids cannot be retrieved within the scope of the API, the
        `PathPropertiesConstraint` Relation can be used. More information can be found
        [https://marketsquare.github.io/robotframework-openapitools/advanced_use.html | here].
        """
        return pf.get_valid_url(
            path=path,
            base_url=self.base_url,
            get_dto_class=self.get_dto_class,
            openapi_spec=self.openapi_spec,
        )

    @keyword
    def get_valid_id_for_path(self, path: str) -> str | int | float:
        """
        Support keyword that returns the `id` for an existing resource at `path`.

        To prevent resource conflicts with other test cases, a new resource is created
        (by a POST operation) if possible.
        """
        return pf.get_valid_id_for_path(
            path=path, get_id_property_name=self.get_id_property_name
        )

    @keyword
    def get_parameterized_path_from_url(self, url: str) -> str:
        """
        Return the path as found in the `paths` section based on the given `url`.
        """
        path = url.replace(self.base_url, "")
        path_parts = path.split("/")
        # first part will be '' since a path starts with /
        path_parts.pop(0)
        parameterized_path = pf.get_parametrized_path(
            path=path, openapi_spec=self.openapi_spec
        )
        return parameterized_path

    @keyword
    def get_ids_from_url(self, url: str) -> list[str]:
        """
        Perform a GET request on the `url` and return the list of resource
        `ids` from the response.
        """
        return pf.get_ids_from_url(
            url=url, get_id_property_name=self.get_id_property_name
        )

    @keyword
    def get_invalidated_url(
        self,
        valid_url: str,
        path: str = "",
        expected_status_code: int = 404,
    ) -> str:
        """
        Return an url with all the path parameters in the `valid_url` replaced by a
        random UUID if no PathPropertiesConstraint is mapped for the `"get"` operation
        on the mapped `path` and `expected_status_code`.
        If a PathPropertiesConstraint is mapped, the `invalid_value` is returned.

        Raises ValueError if the valid_url cannot be invalidated.
        """
        return pi.get_invalidated_url(
            valid_url=valid_url,
            path=path,
            base_url=self.base_url,
            get_dto_class=self.get_dto_class,
            expected_status_code=expected_status_code,
        )

    # endregion
    # region: resource relations keywords
    @keyword
    def ensure_in_use(self, url: str, resource_relation: IdReference) -> None:
        """
        Ensure that the (right-most) `id` of the resource referenced by the `url`
        is used by the resource defined by the `resource_relation`.
        """
        rr.ensure_in_use(
            url=url,
            base_url=self.base_url,
            openapi_spec=self.openapi_spec,
            resource_relation=resource_relation,
        )

    # endregion
    # region: request keywords
    @keyword
    def authorized_request(  # pylint: disable=too-many-arguments
        self,
        url: str,
        method: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_data: JSON = None,
        data: Any = None,
        files: Any = None,
    ) -> Response:
        """
        Perform a request using the security token or authentication set in the library.

        `json_data`, `data` and `files` are passed to `requests.request`s `json`,
        `data` and `files` parameters unaltered.
        See the requests documentation for details:
        https://requests.readthedocs.io/en/latest/api/#requests.request

        > Note: provided username / password or auth objects take precedence over token
            based security
        """
        headers = deepcopy(headers) if headers else {}
        if self.extra_headers:
            headers.update(self.extra_headers)
        # if both an auth object and a token are available, auth takes precedence
        if self.security_token and not self.auth:
            security_header = {"Authorization": self.security_token}
            headers.update(security_header)
        headers = {k: str(v) for k, v in headers.items()}
        response = self.session.request(
            url=url,
            method=method,
            params=params,
            headers=headers,
            json=json_data,
            data=data,
            files=files,
            cookies=self.cookies,
            auth=self.auth,
            proxies=self.proxies,
            verify=self.verify,
            cert=self.cert,
        )
        logger.debug(f"Response text: {response.text}")
        return response

    # endregion
    # region: validation keywords
    @keyword
    def perform_validated_request(
        self,
        path: str,
        status_code: int,
        request_values: RequestValues,
        original_data: Mapping[str, JSON] = default_json_mapping,
    ) -> None:
        """
        This keyword first calls the Authorized Request keyword, then the Validate
        Response keyword and finally validates, for `DELETE` operations, whether
        the target resource was indeed deleted (OK response) or not (error responses).
        """
        val.perform_validated_request(
            path=path,
            status_code=status_code,
            request_values=request_values,
            original_data=original_data,
        )

    @keyword
    def validate_response_using_validator(self, response: Response) -> None:
        """
        Validate the `response` against the OpenAPI Spec that is
        loaded during library initialization.
        """
        val.validate_response_using_validator(
            response=response,
            response_validator=self.response_validator,
        )

    @keyword
    def assert_href_to_resource_is_valid(
        self, href: str, referenced_resource: dict[str, JSON]
    ) -> None:
        """
        Attempt to GET the resource referenced by the `href` and validate it's equal
        to the provided `referenced_resource` object / dictionary.
        """
        val.assert_href_to_resource_is_valid(
            href=href,
            origin=self.origin,
            base_url=self.base_url,
            referenced_resource=referenced_resource,
        )

    @keyword
    def validate_response(
        self,
        path: str,
        response: Response,
        original_data: Mapping[str, JSON] = default_json_mapping,
    ) -> None:
        """
        Validate the `response` by performing the following validations:
        - validate the `response` against the openapi schema for the `path`
        - validate that the response does not contain extra properties
        - validate that a href, if present, refers to the correct resource
        - validate that the value for a property that is in the response is equal to
            the property value that was send
        - validate that no `original_data` is preserved when performing a PUT operation
        - validate that a PATCH operation only updates the provided properties
        """
        val.validate_response(
            path=path,
            response=response,
            response_validator=self.response_validator,
            server_validation_warning_logged=self._server_validation_warning_logged,
            disable_server_validation=self.disable_server_validation,
            invalid_property_default_response=self.invalid_property_default_response,
            response_validation=self.response_validation,
            openapi_spec=self.openapi_spec,
            original_data=original_data,
        )

    @staticmethod
    @keyword
    def validate_send_response(
        response: Response,
        original_data: Mapping[str, JSON] = default_json_mapping,
    ) -> None:
        """
        Validate that each property that was send that is in the response has the value
        that was send.
        In case a PATCH request, validate that only the properties that were patched
        have changed and that other properties are still at their pre-patch values.
        """
        val.validate_send_response(response=response, original_data=original_data)

    # endregion

    @property
    def origin(self) -> str:
        return self._origin

    @property
    def base_url(self) -> str:
        return f"{self.origin}{self._base_path}"

    @cached_property
    def validation_spec(self) -> Spec:
        _, validation_spec, _ = self._load_specs_and_validator()
        return validation_spec

    @property
    def openapi_spec(self) -> OpenApiObject:
        """Return a deepcopy of the parsed openapi document."""
        # protect the parsed openapi spec from being mutated by reference
        return deepcopy(self._openapi_spec)

    @cached_property
    def _openapi_spec(self) -> OpenApiObject:
        parser, _, _ = self._load_specs_and_validator()
        spec_model = OpenApiObject.model_validate(parser.specification)
        register_path_parameters(spec_model.paths)
        return spec_model

    @cached_property
    def response_validator(
        self,
    ) -> ResponseValidatorType:
        _, _, response_validator = self._load_specs_and_validator()
        return response_validator

    def _get_json_types_from_spec(self, spec: dict[str, JSON]) -> set[str]:
        json_types: set[str] = set(self._get_json_types(spec))
        return {json_type for json_type in json_types if json_type is not None}

    def _get_json_types(self, item: object) -> Generator[str, None, None]:
        if isinstance(item, dict):
            content_dict = item.get("content")
            if content_dict is None:
                for value in item.values():
                    yield from self._get_json_types(value)

            else:
                for content_type in content_dict:
                    if "json" in content_type:
                        content_type_without_charset, _, _ = content_type.partition(";")
                        yield content_type_without_charset

        if isinstance(item, list):
            for list_item in item:
                yield from self._get_json_types(list_item)

    def _load_specs_and_validator(
        self,
    ) -> tuple[
        ResolvingParser,
        Spec,
        ResponseValidatorType,
    ]:
        def recursion_limit_handler(
            limit: int,  # pylint: disable=unused-argument
            refstring: str,  # pylint: disable=unused-argument
            recursions: JSON,  # pylint: disable=unused-argument
        ) -> JSON:
            return self._recursion_default

        try:
            # Since parsing of the OAS and creating the Spec can take a long time,
            # they are cached. This is done by storing them in an imported module that
            # will have a global scope due to how the Python import system works. This
            # ensures that in a Suite of Suites where multiple Suites use the same
            # `source`, that OAS is only parsed / loaded once.
            cached_parser = PARSER_CACHE.get(self._source, None)
            if cached_parser:
                return (
                    cached_parser.parser,
                    cached_parser.validation_spec,
                    cached_parser.response_validator,
                )

            parser = ResolvingParser(
                self._source,
                backend="openapi-spec-validator",
                recursion_limit=self._recursion_limit,
                recursion_limit_handler=recursion_limit_handler,
            )

            if parser.specification is None:  # pragma: no cover
                raise FatalError(
                    "Source was loaded, but no specification was present after parsing."
                )

            validation_spec = Spec.from_dict(parser.specification)  # pyright: ignore[reportArgumentType]

            json_types_from_spec: set[str] = self._get_json_types_from_spec(
                parser.specification
            )
            extra_deserializers = {
                json_type: _json.loads for json_type in json_types_from_spec
            }
            config = Config(extra_media_type_deserializers=extra_deserializers)  # type: ignore[arg-type]
            openapi = OpenAPI(spec=validation_spec, config=config)
            response_validator: ResponseValidatorType = openapi.validate_response  # type: ignore[assignment]

            PARSER_CACHE[self._source] = CachedParser(
                parser=parser,
                validation_spec=validation_spec,
                response_validator=response_validator,
            )

            return parser, validation_spec, response_validator

        except ResolutionError as exception:
            raise FatalError(
                f"ResolutionError while trying to load openapi spec: {exception}"
            ) from exception
        except ValidationError as exception:
            raise FatalError(
                f"ValidationError while trying to load openapi spec: {exception}"
            ) from exception

    def read_paths(self) -> dict[str, PathItemObject]:
        return self.openapi_spec.paths
