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
    ${url}=    Get Valid Url    path=/employees/{employee_id}   method=get

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
from copy import deepcopy
from enum import Enum
from functools import cached_property
from pathlib import Path
from typing import Any, Callable, Generator

from openapi_core import Config, OpenAPI, Spec
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from openapi_core.exceptions import OpenAPIError
from openapi_core.templating.paths.exceptions import ServerNotFound
from openapi_core.validation.exceptions import ValidationError
from openapi_core.validation.response.exceptions import ResponseValidationError
from openapi_core.validation.schemas.exceptions import InvalidSchemaValue
from prance import ResolvingParser
from prance.util.url import ResolutionError
from requests import Response, Session
from requests.auth import AuthBase, HTTPBasicAuth
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api import logger
from robot.api.deco import keyword, library
from robot.api.exceptions import Failure
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore import data_generation as dg
from OpenApiLibCore import data_invalidation as di
from OpenApiLibCore import path_functions as pf
from OpenApiLibCore import path_invalidation as pi
from OpenApiLibCore.dto_base import (
    Dto,
    IdReference,
    UniquePropertyValueConstraint,
    resolve_schema,
)
from OpenApiLibCore.dto_utils import (
    DEFAULT_ID_PROPERTY_NAME,
    get_dto_class,
    get_id_property_name,
)
from OpenApiLibCore.oas_cache import PARSER_CACHE
from OpenApiLibCore.request_data import RequestData, RequestValues
from OpenApiLibCore.value_utils import FAKE, JSON

run_keyword = BuiltIn().run_keyword


class ValidationLevel(str, Enum):
    """The available levels for the response_validation parameter."""

    DISABLED = "DISABLED"
    INFO = "INFO"
    WARN = "WARN"
    STRICT = "STRICT"


@library(scope="SUITE", doc_format="ROBOT")
class OpenApiLibCore:  # pylint: disable=too-many-instance-attributes
    """
    Main class providing the keywords and core logic to interact with an OpenAPI server.

    Visit the [https://github.com/MarketSquare/robotframework-openapi-libcore | library page]
    for an introduction.
    """

    def __init__(  # pylint: disable=too-many-arguments, too-many-locals, dangerous-default-value
        self,
        source: str,
        origin: str = "",
        base_path: str = "",
        response_validation: ValidationLevel = ValidationLevel.WARN,
        disable_server_validation: bool = True,
        mappings_path: str | Path = "",
        invalid_property_default_response: int = 422,
        default_id_property_name: str = "id",
        faker_locale: str | list[str] = "",
        require_body_for_invalid_url: bool = False,
        recursion_limit: int = 1,
        recursion_default: Any = {},
        username: str = "",
        password: str = "",
        security_token: str = "",
        auth: AuthBase | None = None,
        cert: str | tuple[str, str] | None = None,
        verify_tls: bool | str = True,
        extra_headers: dict[str, str] = {},
        cookies: dict[str, str] | CookieJar = {},
        proxies: dict[str, str] = {},
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
        self._recursion_default = recursion_default
        self.session = Session()
        # only username and password, security_token or auth object should be provided
        # if multiple are provided, username and password take precedence
        self.security_token = security_token
        self.auth = auth
        if username:
            self.auth = HTTPBasicAuth(username, password)
        # Robot Framework does not allow users to create tuples and requests
        # does not accept lists, so perform the conversion here
        if isinstance(cert, list):
            cert = tuple(cert)
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
            # intermediate variable to ensure path.append is possible so we'll never
            # path.pop a location that we didn't append
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
    def get_request_data(self, path: str, method: str) -> RequestData:
        """Return an object with valid request data for body, headers and query params."""
        return dg.get_request_data(
            path=path,
            method=method,
            get_dto_class=self.get_dto_class,
            get_id_property_name=self.get_id_property_name,
            openapi_spec=self.openapi_spec,
        )

    @keyword
    def get_json_data_for_dto_class(
        self,
        schema: dict[str, Any],
        dto_class: Dto | type[Dto],
        operation_id: str = "",
    ) -> dict[str, Any]:
        """
        Generate a valid (json-compatible) dict for all the `dto_class` properties.
        """
        return dg.get_json_data_for_dto_class(
            schema=schema,
            dto_class=dto_class,
            get_id_property_name=self.get_id_property_name,
            operation_id=operation_id,
        )

    @keyword
    def get_invalid_json_data(
        self,
        url: str,
        method: str,
        status_code: int,
        request_data: RequestData,
    ) -> dict[str, Any]:
        """
        Return `json_data` based on the `dto` on the `request_data` that will cause
        the provided `status_code` for the `method` operation on the `url`.

        > Note: applicable UniquePropertyValueConstraint and IdReference Relations are
            considered before changes to `json_data` are made.
        """
        return di.get_invalid_json_data(
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
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """
        Returns a version of `params, headers` as present on `request_data` that has
        been modified to cause the provided `status_code`.
        """
        return di.get_invalidated_parameters(
            status_code=status_code,
            request_data=request_data,
            invalid_property_default_response=self.invalid_property_default_response,
        )

    # endregion
    # region: path-related keywords
    # FIXME: Refacor to no longer require `method`
    @keyword
    def get_valid_url(self, path: str, method: str) -> str:
        """
        This keyword returns a valid url for the given `path` and `method`.

        If the `path` contains path parameters the Get Valid Id For Path
        keyword will be executed to retrieve valid ids for the path parameters.

        > Note: if valid ids cannot be retrieved within the scope of the API, the
        `PathPropertiesConstraint` Relation can be used. More information can be found
        [https://marketsquare.github.io/robotframework-openapitools/advanced_use.html | here].
        """
        return pf.get_valid_url(
            path=path,
            method=method,
            base_url=self.base_url,
            get_dto_class=self.get_dto_class,
            openapi_spec=self.openapi_spec,
        )

    @keyword
    def get_valid_id_for_path(self, path: str, method: str) -> str | int | float:
        """
        Support keyword that returns the `id` for an existing resource at `path`.

        To prevent resource conflicts with other test cases, a new resource is created
        (by a POST operation) if possible.
        """
        return pf.get_valid_id_for_path(
            path=path, method=method, get_id_property_name=self.get_id_property_name
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
        method: str = "",
        expected_status_code: int = 404,
    ) -> str:
        """
        Return an url with all the path parameters in the `valid_url` replaced by a
        random UUID if no PathPropertiesConstraint is mapped for the `path`, `method`
        and `expected_status_code`.
        If a PathPropertiesConstraint is mapped, the `invalid_value` is returned.

        Raises ValueError if the valid_url cannot be invalidated.
        """
        return pi.get_invalidated_url(
            valid_url=valid_url,
            path=path,
            method=method,
            base_url=self.base_url,
            get_dto_class=self.get_dto_class,
            expected_status_code=expected_status_code,
        )

    # endregion
    # region: response validation keywords
    @keyword
    def validate_response_using_validator(
        self, request: RequestsOpenAPIRequest, response: RequestsOpenAPIResponse
    ) -> None:
        """
        Validate the reponse for a given request against the OpenAPI Spec that is
        loaded during library initialization.
        """
        self.response_validator(request=request, response=response)

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
    def openapi_spec(self) -> dict[str, Any]:
        """Return a deepcopy of the parsed openapi document."""
        # protect the parsed openapi spec from being mutated by reference
        return deepcopy(self._openapi_spec)

    @cached_property
    def _openapi_spec(self) -> dict[str, Any]:
        parser, _, _ = self._load_specs_and_validator()
        return parser.specification

    @cached_property
    def response_validator(
        self,
    ) -> Callable[[RequestsOpenAPIRequest, RequestsOpenAPIResponse], None]:
        _, _, response_validator = self._load_specs_and_validator()
        return response_validator

    def _get_json_types_from_spec(self, spec: dict[str, Any]) -> set[str]:
        json_types: set[str] = set(self._get_json_types(spec))
        return {json_type for json_type in json_types if json_type is not None}

    def _get_json_types(self, item: Any) -> Generator[str, None, None]:
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
        Callable[[RequestsOpenAPIRequest, RequestsOpenAPIResponse], None],
    ]:
        try:

            def recursion_limit_handler(
                limit: int, refstring: str, recursions: Any
            ) -> Any:
                return self._recursion_default

            # Since parsing of the OAS and creating the Spec can take a long time,
            # they are cached. This is done by storing them in an imported module that
            # will have a global scope due to how the Python import system works. This
            # ensures that in a Suite of Suites where multiple Suites use the same
            # `source`, that OAS is only parsed / loaded once.
            parser, validation_spec, response_validator = PARSER_CACHE.get(
                self._source, (None, None, None)
            )

            if parser is None:
                parser = ResolvingParser(
                    self._source,
                    backend="openapi-spec-validator",
                    recursion_limit=self._recursion_limit,
                    recursion_limit_handler=recursion_limit_handler,
                )

                if parser.specification is None:  # pragma: no cover
                    BuiltIn().fatal_error(
                        "Source was loaded, but no specification was present after parsing."
                    )

                validation_spec = Spec.from_dict(parser.specification)

                json_types_from_spec: set[str] = self._get_json_types_from_spec(
                    parser.specification
                )
                extra_deserializers = {
                    json_type: _json.loads for json_type in json_types_from_spec
                }
                config = Config(extra_media_type_deserializers=extra_deserializers)
                openapi = OpenAPI(spec=validation_spec, config=config)
                response_validator = openapi.validate_response

                PARSER_CACHE[self._source] = (
                    parser,
                    validation_spec,
                    response_validator,
                )

            return parser, validation_spec, response_validator

        except ResolutionError as exception:
            BuiltIn().fatal_error(
                f"ResolutionError while trying to load openapi spec: {exception}"
            )
        except ValidationError as exception:
            BuiltIn().fatal_error(
                f"ValidationError while trying to load openapi spec: {exception}"
            )

    def read_paths(self) -> dict[str, Any]:
        return self.openapi_spec["paths"]

    @keyword
    def ensure_in_use(self, url: str, resource_relation: IdReference) -> None:
        """
        Ensure that the (right-most) `id` of the resource referenced by the `url`
        is used by the resource defined by the `resource_relation`.
        """
        resource_id = ""

        path = url.replace(self.base_url, "")
        path_parts = path.split("/")
        parameterized_path = pf.get_parametrized_path(
            path=path, openapi_spec=self.openapi_spec
        )
        parameterized_path_parts = parameterized_path.split("/")
        for part, param_part in zip(
            reversed(path_parts), reversed(parameterized_path_parts)
        ):
            if param_part.endswith("}"):
                resource_id = part
                break
        if not resource_id:
            raise ValueError(f"The provided url ({url}) does not contain an id.")
        # TODO: change to run_keyword?
        request_data = self.get_request_data(
            method="post", path=resource_relation.post_path
        )
        json_data = request_data.dto.as_dict()
        json_data[resource_relation.property_name] = resource_id
        post_url: str = run_keyword(
            "get_valid_url",
            resource_relation.post_path,
            "post",
        )
        response: Response = run_keyword(
            "authorized_request",
            post_url,
            "post",
            request_data.params,
            request_data.headers,
            json_data,
        )
        if not response.ok:
            logger.debug(
                f"POST on {post_url} with json {json_data} failed: {response.json()}"
            )
            response.raise_for_status()

    @keyword
    def get_json_data_with_conflict(
        self, url: str, method: str, dto: Dto, conflict_status_code: int
    ) -> dict[str, Any]:
        """
        Return `json_data` based on the `UniquePropertyValueConstraint` that must be
        returned by the `get_relations` implementation on the `dto` for the given
        `conflict_status_code`.
        """
        method = method.lower()
        json_data = dto.as_dict()
        unique_property_value_constraints = [
            r
            for r in dto.get_relations()
            if isinstance(r, UniquePropertyValueConstraint)
        ]
        for relation in unique_property_value_constraints:
            json_data[relation.property_name] = relation.value
            # create a new resource that the original request will conflict with
            if method in ["patch", "put"]:
                post_url_parts = url.split("/")[:-1]
                post_url = "/".join(post_url_parts)
                # the PATCH or PUT may use a different dto than required for POST
                # so a valid POST dto must be constructed
                path = post_url.replace(self.base_url, "")
                # TODO: change to run_keyword/
                request_data = self.get_request_data(path=path, method="post")
                post_json = request_data.dto.as_dict()
                for key in post_json.keys():
                    if key in json_data:
                        post_json[key] = json_data.get(key)
            else:
                post_url = url
                post_json = json_data
            path = post_url.replace(self.base_url, "")
            # TODO: change to run_keyword?
            request_data = self.get_request_data(path=path, method="post")
            response: Response = run_keyword(
                "authorized_request",
                post_url,
                "post",
                request_data.params,
                request_data.headers,
                post_json,
            )
            # conflicting resource may already exist
            assert response.ok or response.status_code == conflict_status_code, (
                f"get_json_data_with_conflict received {response.status_code}: {response.json()}"
            )
            return json_data
        raise ValueError(
            f"No UniquePropertyValueConstraint in the get_relations list on dto {dto}."
        )

    @keyword
    def authorized_request(  # pylint: disable=too-many-arguments
        self,
        url: str,
        method: str,
        params: dict[str, Any] = {},
        headers: dict[str, str] = {},
        json_data: JSON = {},
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
        headers = headers if headers else {}
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

    @keyword
    def perform_validated_request(
        self,
        path: str,
        status_code: int,
        request_values: RequestValues,
        original_data: dict[str, Any] = {},
    ) -> None:
        """
        This keyword first calls the Authorized Request keyword, then the Validate
        Response keyword and finally validates, for `DELETE` operations, whether
        the target resource was indeed deleted (OK response) or not (error responses).
        """
        response = run_keyword(
            "authorized_request",
            request_values.url,
            request_values.method,
            request_values.params,
            request_values.headers,
            request_values.json_data,
        )
        if response.status_code != status_code:
            try:
                response_json = response.json()
            except Exception as _:  # pylint: disable=broad-except
                logger.info(
                    f"Failed to get json content from response. "
                    f"Response text was: {response.text}"
                )
                response_json = {}
            if not response.ok:
                if description := response_json.get("detail"):
                    pass
                else:
                    description = response_json.get(
                        "message", "response contains no message or detail."
                    )
                logger.error(f"{response.reason}: {description}")

            logger.debug(
                f"\nSend: {_json.dumps(request_values.json_data, indent=4, sort_keys=True)}"
                f"\nGot: {_json.dumps(response_json, indent=4, sort_keys=True)}"
            )
            raise AssertionError(
                f"Response status_code {response.status_code} was not {status_code}"
            )

        run_keyword("validate_response", path, response, original_data)

        if request_values.method == "DELETE":
            # TODO: change to run_keyword?
            request_data = self.get_request_data(path=path, method="GET")
            get_params = request_data.params
            get_headers = request_data.headers
            get_response = run_keyword(
                "authorized_request", request_values.url, "GET", get_params, get_headers
            )
            if response.ok:
                if get_response.ok:
                    raise AssertionError(
                        f"Resource still exists after deletion. Url was {request_values.url}"
                    )
                # if the path supports GET, 404 is expected, if not 405 is expected
                if get_response.status_code not in [404, 405]:
                    logger.warn(
                        f"Unexpected response after deleting resource: Status_code "
                        f"{get_response.status_code} was received after trying to get {request_values.url} "
                        f"after sucessfully deleting it."
                    )
            elif not get_response.ok:
                raise AssertionError(
                    f"Resource could not be retrieved after failed deletion. "
                    f"Url was {request_values.url}, status_code was {get_response.status_code}"
                )

    @keyword
    def validate_response(
        self,
        path: str,
        response: Response,
        original_data: dict[str, Any] = {},
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
        if response.status_code == 204:
            assert not response.content
            return None

        try:
            self._validate_response(response)
        except OpenAPIError as exception:
            raise Failure(f"Response did not pass schema validation: {exception}")

        request_method = response.request.method
        if request_method is None:
            logger.warn(
                f"Could not validate response for path {path}; no method found "
                f"on the request property of the provided response."
            )
            return None

        response_spec = self._get_response_spec(
            path=path,
            method=request_method,
            status_code=response.status_code,
        )

        content_type_from_response = response.headers.get("Content-Type", "unknown")
        mime_type_from_response, _, _ = content_type_from_response.partition(";")

        if not response_spec.get("content"):
            logger.warn(
                "The response cannot be validated: 'content' not specified in the OAS."
            )
            return None

        # multiple content types can be specified in the OAS
        content_types = list(response_spec["content"].keys())
        supported_types = [
            ct for ct in content_types if ct.partition(";")[0].endswith("json")
        ]
        if not supported_types:
            raise NotImplementedError(
                f"The content_types '{content_types}' are not supported. "
                f"Only json types are currently supported."
            )
        content_type = supported_types[0]
        mime_type = content_type.partition(";")[0]

        if mime_type != mime_type_from_response:
            raise ValueError(
                f"Content-Type '{content_type_from_response}' of the response "
                f"does not match '{mime_type}' as specified in the OpenAPI document."
            )

        json_response = response.json()
        response_schema = resolve_schema(
            response_spec["content"][content_type]["schema"]
        )

        response_types = response_schema.get("types")
        if response_types:
            # In case of oneOf / anyOf there can be multiple possible response types
            # which makes generic validation too complex
            return None
        response_type = response_schema.get("type", "undefined")
        if response_type not in ["object", "array"]:
            self._validate_value_type(value=json_response, expected_type=response_type)
            return None

        if list_item_schema := response_schema.get("items"):
            if not isinstance(json_response, list):
                raise AssertionError(
                    f"Response schema violation: the schema specifies an array as "
                    f"response type but the response was of type {type(json_response)}."
                )
            type_of_list_items = list_item_schema.get("type")
            if type_of_list_items == "object":
                for resource in json_response:
                    run_keyword(
                        "validate_resource_properties", resource, list_item_schema
                    )
            else:
                for item in json_response:
                    self._validate_value_type(
                        value=item, expected_type=type_of_list_items
                    )
            # no further validation; value validation of individual resources should
            # be performed on the path for the specific resources
            return None

        run_keyword("validate_resource_properties", json_response, response_schema)
        # ensure the href is valid if present in the response
        if href := json_response.get("href"):
            self._assert_href_is_valid(href, json_response)
        # every property that was sucessfully send and that is in the response
        # schema must have the value that was send
        if response.ok and response.request.method in ["POST", "PUT", "PATCH"]:
            run_keyword("validate_send_response", response, original_data)
        return None

    def _assert_href_is_valid(self, href: str, json_response: dict[str, Any]) -> None:
        url = f"{self.origin}{href}"
        path = url.replace(self.base_url, "")
        # TODO: change to run_keyword?
        request_data = self.get_request_data(path=path, method="GET")
        params = request_data.params
        headers = request_data.headers
        get_response = run_keyword("authorized_request", url, "GET", params, headers)
        assert get_response.json() == json_response, (
            f"{get_response.json()} not equal to original {json_response}"
        )

    def _validate_response(self, response: Response) -> None:
        try:
            self.validate_response_using_validator(
                request=RequestsOpenAPIRequest(response.request),
                response=RequestsOpenAPIResponse(response),
            )
        except (ResponseValidationError, ServerNotFound) as exception:
            errors: list[InvalidSchemaValue] = exception.__cause__
            validation_errors: list[ValidationError] = getattr(
                errors, "schema_errors", []
            )
            if validation_errors:
                error_message = "\n".join(
                    [
                        f"{list(error.schema_path)}: {error.message}"
                        for error in validation_errors
                    ]
                )
            else:
                error_message = str(exception)

            if isinstance(exception, ServerNotFound):
                if not self._server_validation_warning_logged:
                    logger.warn(
                        f"ServerNotFound was raised during response validation. "
                        f"Due to this, no full response validation will be performed."
                        f"\nThe original error was: {error_message}"
                    )
                    self._server_validation_warning_logged = True
                if self.disable_server_validation:
                    return
            if response.status_code == self.invalid_property_default_response:
                logger.debug(error_message)
                return
            if self.response_validation == ValidationLevel.STRICT:
                logger.error(error_message)
                raise exception
            if self.response_validation == ValidationLevel.WARN:
                logger.warn(error_message)
            elif self.response_validation == ValidationLevel.INFO:
                logger.info(error_message)

    @keyword
    def validate_resource_properties(
        self, resource: dict[str, Any], schema: dict[str, Any]
    ) -> None:
        """
        Validate that the `resource` does not contain any properties that are not
        defined in the `schema_properties`.
        """
        schema_properties = schema.get("properties", {})
        property_names_from_schema = set(schema_properties.keys())
        property_names_in_resource = set(resource.keys())

        if property_names_from_schema != property_names_in_resource:
            # The additionalProperties property determines whether properties with
            # unspecified names are allowed. This property can be boolean or an object
            # (dict) that specifies the type of any additional properties.
            additional_properties = schema.get("additionalProperties", True)
            if isinstance(additional_properties, bool):
                allow_additional_properties = additional_properties
                allowed_additional_properties_type = None
            else:
                allow_additional_properties = True
                allowed_additional_properties_type = additional_properties["type"]

            extra_property_names = property_names_in_resource.difference(
                property_names_from_schema
            )
            if allow_additional_properties:
                # If a type is defined for extra properties, validate them
                if allowed_additional_properties_type:
                    extra_properties = {
                        key: value
                        for key, value in resource.items()
                        if key in extra_property_names
                    }
                    self._validate_type_of_extra_properties(
                        extra_properties=extra_properties,
                        expected_type=allowed_additional_properties_type,
                    )
                # If allowed, validation should not fail on extra properties
                extra_property_names = set()

            required_properties = set(schema.get("required", []))
            missing_properties = required_properties.difference(
                property_names_in_resource
            )

            if extra_property_names or missing_properties:
                extra = (
                    f"\n\tExtra properties in response: {extra_property_names}"
                    if extra_property_names
                    else ""
                )
                missing = (
                    f"\n\tRequired properties missing in response: {missing_properties}"
                    if missing_properties
                    else ""
                )
                raise AssertionError(
                    f"Response schema violation: the response contains properties that are "
                    f"not specified in the schema or does not contain properties that are "
                    f"required according to the schema."
                    f"\n\tReceived in the response: {property_names_in_resource}"
                    f"\n\tDefined in the schema:    {property_names_from_schema}"
                    f"{extra}{missing}"
                )

    @staticmethod
    def _validate_value_type(value: Any, expected_type: str) -> None:
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        python_type = type_mapping.get(expected_type, None)
        if python_type is None:
            raise AssertionError(
                f"Validation of type '{expected_type}' is not supported."
            )
        if not isinstance(value, python_type):
            raise AssertionError(f"{value} is not of type {expected_type}")

    @staticmethod
    def _validate_type_of_extra_properties(
        extra_properties: dict[str, Any], expected_type: str
    ) -> None:
        type_mapping = {
            "string": str,
            "number": float,
            "integer": int,
            "boolean": bool,
            "array": list,
            "object": dict,
        }

        python_type = type_mapping.get(expected_type, None)
        if python_type is None:
            logger.warn(
                f"Additonal properties were not validated: "
                f"type '{expected_type}' is not supported."
            )
            return

        invalid_extra_properties = {
            key: value
            for key, value in extra_properties.items()
            if not isinstance(value, python_type)
        }
        if invalid_extra_properties:
            raise AssertionError(
                f"Response contains invalid additionalProperties: "
                f"{invalid_extra_properties} are not of type {expected_type}."
            )

    @staticmethod
    @keyword
    def validate_send_response(
        response: Response,
        original_data: dict[str, Any] = {},
    ) -> None:
        """
        Validate that each property that was send that is in the response has the value
        that was send.
        In case a PATCH request, validate that only the properties that were patched
        have changed and that other properties are still at their pre-patch values.
        """

        def validate_list_response(
            send_list: list[Any], received_list: list[Any]
        ) -> None:
            for item in send_list:
                if item not in received_list:
                    raise AssertionError(
                        f"Received value '{received_list}' does "
                        f"not contain '{item}' in the {response.request.method} request."
                        f"\nSend: {_json.dumps(send_json, indent=4, sort_keys=True)}"
                        f"\nGot: {_json.dumps(response_data, indent=4, sort_keys=True)}"
                    )

        def validate_dict_response(
            send_dict: dict[str, Any], received_dict: dict[str, Any]
        ) -> None:
            for send_property_name, send_property_value in send_dict.items():
                # sometimes, a property in the request is not in the response, e.g. a password
                if send_property_name not in received_dict.keys():
                    continue
                if send_property_value is not None:
                    # if a None value is send, the target property should be cleared or
                    # reverted to the default value (which cannot be specified in the
                    # openapi document)
                    received_value = received_dict[send_property_name]
                    # In case of lists / arrays, the send values are often appended to
                    # existing data
                    if isinstance(received_value, list):
                        validate_list_response(
                            send_list=send_property_value, received_list=received_value
                        )
                        continue

                    # when dealing with objects, we'll need to iterate the properties
                    if isinstance(received_value, dict):
                        validate_dict_response(
                            send_dict=send_property_value, received_dict=received_value
                        )
                        continue

                    assert received_value == send_property_value, (
                        f"Received value for {send_property_name} '{received_value}' does not "
                        f"match '{send_property_value}' in the {response.request.method} request."
                        f"\nSend: {_json.dumps(send_json, indent=4, sort_keys=True)}"
                        f"\nGot: {_json.dumps(response_data, indent=4, sort_keys=True)}"
                    )

        if response.request.body is None:
            logger.warn(
                "Could not validate send response; the body of the request property "
                "on the provided response was None."
            )
            return None
        if isinstance(response.request.body, bytes):
            send_json = _json.loads(response.request.body.decode("UTF-8"))
        else:
            send_json = _json.loads(response.request.body)

        response_data = response.json()
        # POST on /resource_type/{id}/array_item/ will return the updated {id} resource
        # instead of a newly created resource. In this case, the send_json must be
        # in the array of the 'array_item' property on {id}
        send_path: str = response.request.path_url
        response_path = response_data.get("href", None)
        if response_path and send_path not in response_path:
            property_to_check = send_path.replace(response_path, "")[1:]
            if response_data.get(property_to_check) and isinstance(
                response_data[property_to_check], list
            ):
                item_list: list[dict[str, Any]] = response_data[property_to_check]
                # Use the (mandatory) id to get the POSTed resource from the list
                [response_data] = [
                    item for item in item_list if item["id"] == send_json["id"]
                ]

        # incoming arguments are dictionaries, so they can be validated as such
        validate_dict_response(send_dict=send_json, received_dict=response_data)

        # In case of PATCH requests, ensure that only send properties have changed
        if original_data:
            for send_property_name, send_value in original_data.items():
                if send_property_name not in send_json.keys():
                    assert send_value == response_data[send_property_name], (
                        f"Received value for {send_property_name} '{response_data[send_property_name]}' does not "
                        f"match '{send_value}' in the pre-patch data"
                        f"\nPre-patch: {_json.dumps(original_data, indent=4, sort_keys=True)}"
                        f"\nGot: {_json.dumps(response_data, indent=4, sort_keys=True)}"
                    )
        return None

    def _get_response_spec(
        self, path: str, method: str, status_code: int
    ) -> dict[str, Any]:
        method = method.lower()
        status = str(status_code)
        spec: dict[str, Any] = {**self.openapi_spec}["paths"][path][method][
            "responses"
        ][status]
        return spec
