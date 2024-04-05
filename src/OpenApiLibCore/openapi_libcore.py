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
The example below can be used, with `source`, `origin` and 'endpoint' altered to
fit your situation.

``` robotframework
*** Settings ***
Library            OpenApiLibCore
...                    source=http://localhost:8000/openapi.json
...                    origin=http://localhost:8000

*** Test Cases ***
Getting Started
    ${url}=    Get Valid Url    endpoint=/employees/{employee_id}   method=get

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
import re
import sys
from copy import deepcopy
from dataclasses import Field, dataclass, field, make_dataclass
from functools import cached_property
from itertools import zip_longest
from logging import getLogger
from pathlib import Path
from random import choice
from typing import Any, Dict, List, Optional, Set, Tuple, Type, Union
from uuid import uuid4

from openapi_core import Config, OpenAPI, Spec
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from prance import ResolvingParser, ValidationError
from prance.util.url import ResolutionError
from requests import Response, Session
from requests.auth import AuthBase, HTTPBasicAuth
from requests.cookies import RequestsCookieJar as CookieJar
from robot.api.deco import keyword, library
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore import value_utils
from OpenApiLibCore.dto_base import (
    NOT_SET,
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    Relation,
    UniquePropertyValueConstraint,
    resolve_schema,
)
from OpenApiLibCore.dto_utils import (
    DEFAULT_ID_PROPERTY_NAME,
    DefaultDto,
    get_dto_class,
    get_id_property_name,
)
from OpenApiLibCore.oas_cache import PARSER_CACHE
from OpenApiLibCore.value_utils import FAKE, IGNORE, JSON

run_keyword = BuiltIn().run_keyword

logger = getLogger(__name__)


def get_safe_key(key: str) -> str:
    """
    Helper function to convert a valid JSON property name to a string that can be used
    as a Python variable or function / method name.
    """
    key = key.replace("-", "_")
    key = key.replace("@", "_")
    if key[0].isdigit():
        key = f"_{key}"
    return key


@dataclass
class RequestValues:
    """Helper class to hold parameter values needed to make a request."""

    url: str
    method: str
    params: Optional[Dict[str, Any]]
    headers: Optional[Dict[str, str]]
    json_data: Optional[Dict[str, Any]]


@dataclass
class RequestData:
    """Helper class to manage parameters used when making requests."""

    dto: Union[Dto, DefaultDto] = field(default_factory=DefaultDto)
    dto_schema: Dict[str, Any] = field(default_factory=dict)
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    headers: Dict[str, Any] = field(default_factory=dict)
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
    def params_that_can_be_invalidated(self) -> Set[str]:
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
    def headers_that_can_be_invalidated(self) -> Set[str]:
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

    def get_required_properties_dict(self) -> Dict[str, Any]:
        """Get the json-compatible dto data containing only the required properties."""
        required_properties = self.dto_schema.get("required", [])
        required_properties_dict: Dict[str, Any] = {}
        for key, value in (self.dto.as_dict()).items():
            if key in required_properties:
                required_properties_dict[key] = value
        return required_properties_dict

    def get_required_params(self) -> Dict[str, str]:
        """Get the params dict containing only the required query parameters."""
        required_parameters = [
            p.get("name") for p in self.parameters if p.get("required")
        ]
        return {k: v for k, v in self.params.items() if k in required_parameters}

    def get_required_headers(self) -> Dict[str, str]:
        """Get the headers dict containing only the required headers."""
        required_parameters = [
            p.get("name") for p in self.parameters if p.get("required")
        ]
        return {k: v for k, v in self.headers.items() if k in required_parameters}


@library(scope="TEST SUITE", doc_format="ROBOT")
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
        mappings_path: Union[str, Path] = "",
        invalid_property_default_response: int = 422,
        default_id_property_name: str = "id",
        faker_locale: Optional[Union[str, List[str]]] = None,
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
        """
        == Base parameters ==

        === source ===
        An absolute path to an openapi.json or openapi.yaml file or an url to such a file.

        === origin ===
        The server (and port) of the target server. E.g. ``https://localhost:8000``

        === base_path ===
        The routing between ``origin`` and the endpoints as found in the ``paths``
        section in the openapi document.
        E.g. ``/petshop/v2``.

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
        self._recursion_limit = recursion_limit
        self._recursion_default = recursion_default
        self.session = Session()
        # only username and password, security_token or auth object should be provided
        # if multiple are provided, username and password take precedence
        self.security_token = security_token
        self.auth = auth
        if username and password:
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
                logger.warning(
                    f"mappings_path '{mappings_path}' is not a Python module."
                )
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
        # update the globally available DEFAULT_ID_PROPERTY_NAME to the provided value
        DEFAULT_ID_PROPERTY_NAME.id_property_name = default_id_property_name

    @property
    def origin(self) -> str:
        return self._origin

    @keyword
    def set_origin(self, origin: str) -> None:
        """
        Update the `origin` after the library is imported.

        This can be done during the `Suite setup` when using DataDriver in situations
        where the OpenAPI document is available on disk but the target host address is
        not known before the test starts.

        In combination with OpenApiLibCore, the `origin` can be used at any point to
        target another server that hosts an API that complies to the same OAS.
        """
        self._origin = origin

    @property
    def base_url(self) -> str:
        return f"{self.origin}{self._base_path}"

    @cached_property
    def validation_spec(self) -> Spec:
        return Spec.from_dict(self.openapi_spec)

    @property
    def openapi_spec(self) -> Dict[str, Any]:
        """Return a deepcopy of the parsed openapi document."""
        # protect the parsed openapi spec from being mutated by reference
        return deepcopy(self._openapi_spec)

    @cached_property
    def _openapi_spec(self) -> Dict[str, Any]:
        parser = self._load_parser()
        return parser.specification

    def read_paths(self) -> Dict[str, Any]:
        return self.openapi_spec["paths"]

    def _load_parser(self) -> ResolvingParser:
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
            parser = PARSER_CACHE.get(self._source, None)
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

                PARSER_CACHE[self._source] = parser

            return parser

        except ResolutionError as exception:
            BuiltIn().fatal_error(
                f"ResolutionError while trying to load openapi spec: {exception}"
            )
        except ValidationError as exception:
            BuiltIn().fatal_error(
                f"ValidationError while trying to load openapi spec: {exception}"
            )

    def validate_response_vs_spec(
        self, request: RequestsOpenAPIRequest, response: RequestsOpenAPIResponse
    ) -> None:
        """
        Validate the reponse for a given request against the OpenAPI Spec that is
        loaded during library initialization.
        """
        if response.content_type == "application/json":
            config = None
        else:
            extra_deserializer = {response.content_type: _json.loads}
            config = Config(extra_media_type_deserializers=extra_deserializer)

        OpenAPI(spec=self.validation_spec, config=config).validate_response(
            request, response
        )

    @keyword
    def get_valid_url(self, endpoint: str, method: str) -> str:
        """
        This keyword returns a valid url for the given `endpoint` and `method`.

        If the `endpoint` contains path parameters the Get Valid Id For Endpoint
        keyword will be executed to retrieve valid ids for the path parameters.

        > Note: if valid ids cannot be retrieved within the scope of the API, the
        `PathPropertiesConstraint` Relation can be used. More information can be found
        [https://marketsquare.github.io/robotframework-openapi-libcore/advanced_use.html | here].
        """
        method = method.lower()
        try:
            # endpoint can be partially resolved or provided by a PathPropertiesConstraint
            parametrized_endpoint = self.get_parametrized_endpoint(endpoint=endpoint)
            _ = self.openapi_spec["paths"][parametrized_endpoint]
        except KeyError:
            raise ValueError(
                f"{endpoint} not found in paths section of the OpenAPI document."
            ) from None
        dto_class = self.get_dto_class(endpoint=endpoint, method=method)
        relations = dto_class.get_relations()
        paths = [p.path for p in relations if isinstance(p, PathPropertiesConstraint)]
        if paths:
            url = f"{self.base_url}{choice(paths)}"
            return url
        endpoint_parts = list(endpoint.split("/"))
        for index, part in enumerate(endpoint_parts):
            if part.startswith("{") and part.endswith("}"):
                type_endpoint_parts = endpoint_parts[slice(index)]
                type_endpoint = "/".join(type_endpoint_parts)
                existing_id: Union[str, int, float] = run_keyword(
                    "get_valid_id_for_endpoint", type_endpoint, method
                )
                endpoint_parts[index] = str(existing_id)
        resolved_endpoint = "/".join(endpoint_parts)
        url = f"{self.base_url}{resolved_endpoint}"
        return url

    @keyword
    def get_valid_id_for_endpoint(
        self, endpoint: str, method: str
    ) -> Union[str, int, float]:
        """
        Support keyword that returns the `id` for an existing resource at `endpoint`.

        To prevent resource conflicts with other test cases, a new resource is created
        (POST) if possible.
        """

        def dummy_transformer(
            valid_id: Union[str, int, float]
        ) -> Union[str, int, float]:
            return valid_id

        method = method.lower()
        url: str = run_keyword("get_valid_url", endpoint, method)
        # Try to create a new resource to prevent conflicts caused by
        # operations performed on the same resource by other test cases
        request_data = self.get_request_data(endpoint=endpoint, method="post")

        response: Response = run_keyword(
            "authorized_request",
            url,
            "post",
            request_data.get_required_params(),
            request_data.get_required_headers(),
            request_data.get_required_properties_dict(),
        )

        # determine the id property name for this path and whether or not a transformer is used
        mapping = self.get_id_property_name(endpoint=endpoint)
        if isinstance(mapping, str):
            id_property = mapping
            # set the transformer to a dummy callable that returns the original value so
            # the transformer can be applied on any returned id
            id_transformer = dummy_transformer
        else:
            id_property, id_transformer = mapping

        if not response.ok:
            # If a new resource cannot be created using POST, try to retrieve a
            # valid id using a GET request.
            try:
                valid_id = choice(run_keyword("get_ids_from_url", url))
                return id_transformer(valid_id)
            except Exception as exception:
                raise AssertionError(
                    f"Failed to get a valid id using GET on {url}"
                ) from exception

        response_data = response.json()
        if prepared_body := response.request.body:
            if isinstance(prepared_body, bytes):
                send_json = _json.loads(prepared_body.decode("UTF-8"))
            else:
                send_json = _json.loads(prepared_body)
        else:
            send_json = None

        # no support for retrieving an id from an array returned on a POST request
        if isinstance(response_data, list):
            raise NotImplementedError(
                f"Unexpected response body for POST request: expected an object but "
                f"received an array ({response_data})"
            )

        # POST on /resource_type/{id}/array_item/ will return the updated {id} resource
        # instead of a newly created resource. In this case, the send_json must be
        # in the array of the 'array_item' property on {id}
        send_path: str = response.request.path_url
        response_href: Optional[str] = response_data.get("href", None)
        if response_href and (send_path not in response_href) and send_json:
            try:
                property_to_check = send_path.replace(response_href, "")[1:]
                item_list: List[Dict[str, Any]] = response_data[property_to_check]
                # Use the (mandatory) id to get the POSTed resource from the list
                [valid_id] = [
                    item[id_property]
                    for item in item_list
                    if item[id_property] == send_json[id_property]
                ]
            except Exception as exception:
                raise AssertionError(
                    f"Failed to get a valid id from {response_href}"
                ) from exception
        else:
            try:
                valid_id = response_data[id_property]
            except KeyError:
                raise AssertionError(
                    f"Failed to get a valid id from {response_data}"
                ) from None
        return id_transformer(valid_id)

    @keyword
    def get_ids_from_url(self, url: str) -> List[str]:
        """
        Perform a GET request on the `url` and return the list of resource
        `ids` from the response.
        """
        endpoint = self.get_parameterized_endpoint_from_url(url)
        request_data = self.get_request_data(endpoint=endpoint, method="get")
        response = run_keyword(
            "authorized_request",
            url,
            "get",
            request_data.get_required_params(),
            request_data.get_required_headers(),
        )
        response.raise_for_status()
        response_data: Union[Dict[str, Any], List[Dict[str, Any]]] = response.json()

        # determine the property name to use
        mapping = self.get_id_property_name(endpoint=endpoint)
        if isinstance(mapping, str):
            id_property = mapping
        else:
            id_property, _ = mapping

        if isinstance(response_data, list):
            valid_ids: List[str] = [item[id_property] for item in response_data]
            return valid_ids
        # if the response is an object (dict), check if it's hal+json
        if embedded := response_data.get("_embedded"):
            # there should be 1 item in the dict that has a value that's a list
            for value in embedded.values():
                if isinstance(value, list):
                    valid_ids = [item[id_property] for item in value]
                    return valid_ids
        if (valid_id := response_data.get(id_property)) is not None:
            return [valid_id]
        valid_ids = [item[id_property] for item in response_data["items"]]
        return valid_ids

    @keyword
    def get_request_data(self, endpoint: str, method: str) -> RequestData:
        """Return an object with valid request data for body, headers and query params."""
        method = method.lower()
        dto_cls_name = self._get_dto_cls_name(endpoint=endpoint, method=method)
        # The endpoint can contain already resolved Ids that have to be matched
        # against the parametrized endpoints in the paths section.
        spec_endpoint = self.get_parametrized_endpoint(endpoint)
        dto_class = self.get_dto_class(endpoint=spec_endpoint, method=method)
        try:
            method_spec = self.openapi_spec["paths"][spec_endpoint][method]
        except KeyError:
            logger.info(
                f"method '{method}' not supported on '{spec_endpoint}, using empty spec."
            )
            method_spec = {}

        parameters, params, headers = self.get_request_parameters(
            dto_class=dto_class, method_spec=method_spec
        )
        if (body_spec := method_spec.get("requestBody", None)) is None:
            if dto_class == DefaultDto:
                dto_instance: Dto = DefaultDto()
            else:
                dto_class = make_dataclass(
                    cls_name=method_spec.get("operationId", dto_cls_name),
                    fields=[],
                    bases=(dto_class,),
                )
                dto_instance = dto_class()
            return RequestData(
                dto=dto_instance,
                parameters=parameters,
                params=params,
                headers=headers,
                has_body=False,
            )
        content_schema = resolve_schema(self.get_content_schema(body_spec))
        headers.update({"content-type": self.get_content_type(body_spec)})
        dto_data = self.get_json_data_for_dto_class(
            schema=content_schema,
            dto_class=dto_class,
            operation_id=method_spec.get("operationId", ""),
        )
        if dto_data is None:
            dto_instance = DefaultDto()
        else:
            fields = self.get_fields_from_dto_data(content_schema, dto_data)
            dto_class = make_dataclass(
                cls_name=method_spec.get("operationId", dto_cls_name),
                fields=fields,
                bases=(dto_class,),
            )
            dto_data = {get_safe_key(key): value for key, value in dto_data.items()}
            dto_instance = dto_class(**dto_data)
        return RequestData(
            dto=dto_instance,
            dto_schema=content_schema,
            parameters=parameters,
            params=params,
            headers=headers,
        )

    @staticmethod
    def _get_dto_cls_name(endpoint: str, method: str) -> str:
        method = method.capitalize()
        path = endpoint.translate({ord(i): None for i in "{}"})
        path_parts = path.split("/")
        path_parts = [p.capitalize() for p in path_parts]
        result = "".join([method, *path_parts])
        return result

    @staticmethod
    def get_fields_from_dto_data(
        content_schema: Dict[str, Any], dto_data: Dict[str, Any]
    ):
        # FIXME: annotation is not Pyhon 3.8-compatible
        # ) -> List[Union[str, Tuple[str, Type[Any]], Tuple[str, Type[Any], Field[Any]]]]:
        """Get a dataclasses fields list based on the content_schema and dto_data."""
        fields: List[
            Union[str, Tuple[str, Type[Any]], Tuple[str, Type[Any], Field[Any]]]
        ] = []
        for key, value in dto_data.items():
            required_properties = content_schema.get("required", [])
            safe_key = get_safe_key(key)
            metadata = {"original_property_name": key}
            if key in required_properties:
                # The fields list is used to create a dataclass, so non-default fields
                # must go before fields with a default
                fields.insert(0, (safe_key, type(value), field(metadata=metadata)))
            else:
                fields.append((safe_key, type(value), field(default=None, metadata=metadata)))  # type: ignore[arg-type]
        return fields

    def get_request_parameters(
        self, dto_class: Union[Dto, Type[Dto]], method_spec: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, str]]:
        """Get the methods parameter spec and params and headers with valid data."""
        parameters = method_spec.get("parameters", [])
        parameter_relations = dto_class.get_parameter_relations()
        query_params = [p for p in parameters if p.get("in") == "query"]
        header_params = [p for p in parameters if p.get("in") == "header"]
        params = self.get_parameter_data(query_params, parameter_relations)
        headers = self.get_parameter_data(header_params, parameter_relations)
        return parameters, params, headers

    @classmethod
    def get_content_schema(cls, body_spec: Dict[str, Any]) -> Dict[str, Any]:
        """Get the content schema from the requestBody spec."""
        content_type = cls.get_content_type(body_spec)
        content_schema = body_spec["content"][content_type]["schema"]
        return resolve_schema(content_schema)

    @staticmethod
    def get_content_type(body_spec: Dict[str, Any]) -> str:
        """Get and validate the first supported content type from the requested body spec

        Should be application/json like content type,
        e.g "application/json;charset=utf-8" or "application/merge-patch+json"
        """
        content_types: List[str] = body_spec["content"].keys()
        json_regex = r"application/([a-z\-]+\+)?json(;\s?charset=(.+))?"
        for content_type in content_types:
            if re.search(json_regex, content_type):
                return content_type

        # At present no supported for other types.
        raise NotImplementedError(
            f"Only content types like 'application/json' are supported. "
            f"Content types definded in the spec are '{content_types}'."
        )

    def get_parametrized_endpoint(self, endpoint: str) -> str:
        """
        Get the parametrized endpoint as found in the `paths` section of the openapi
        document from a (partially) resolved endpoint.
        """

        def match_parts(parts: List[str], spec_parts: List[str]) -> bool:
            for part, spec_part in zip_longest(parts, spec_parts, fillvalue="Filler"):
                if part == "Filler" or spec_part == "Filler":
                    return False
                if part != spec_part and not spec_part.startswith("{"):
                    return False
            return True

        endpoint_parts = endpoint.split("/")
        # if the last part is empty, the path has a trailing `/` that
        # should be ignored during matching
        if endpoint_parts[-1] == "":
            _ = endpoint_parts.pop(-1)

        spec_endpoints: List[str] = {**self.openapi_spec}["paths"].keys()

        candidates: List[str] = []

        for spec_endpoint in spec_endpoints:
            spec_endpoint_parts = spec_endpoint.split("/")
            # ignore trailing `/` the same way as for endpoint_parts
            if spec_endpoint_parts[-1] == "":
                _ = spec_endpoint_parts.pop(-1)
            if match_parts(endpoint_parts, spec_endpoint_parts):
                candidates.append(spec_endpoint)

        if not candidates:
            raise ValueError(
                f"{endpoint} not found in paths section of the OpenAPI document."
            )

        if len(candidates) == 1:
            return candidates[0]
        # Multiple matches can happen in APIs with overloaded endpoints, e.g.
        # /users/me
        # /users/${user_id}
        # In this case, find the closest (or exact) match
        exact_match = [c for c in candidates if c == endpoint]
        if exact_match:
            return exact_match[0]
        # TODO: Implement a decision mechanism when real-world examples become available
        # In the face of ambiguity, refuse the temptation to guess.
        raise ValueError(f"{endpoint} matched to multiple paths: {candidates}")

    @staticmethod
    def get_parameter_data(
        parameters: List[Dict[str, Any]],
        parameter_relations: List[Relation],
    ) -> Dict[str, str]:
        """Generate a valid list of key-value pairs for all parameters."""
        result: Dict[str, str] = {}
        value: Any = None
        for parameter in parameters:
            parameter_name = parameter["name"]
            parameter_schema = resolve_schema(parameter["schema"])
            relations = [
                r for r in parameter_relations if r.property_name == parameter_name
            ]
            if constrained_values := [
                r.values for r in relations if isinstance(r, PropertyValueConstraint)
            ]:
                value = choice(*constrained_values)
                if value is IGNORE:
                    continue
                result[parameter_name] = value
                continue
            value = value_utils.get_valid_value(parameter_schema)
            result[parameter_name] = value
        return result

    @keyword
    def get_json_data_for_dto_class(
        self,
        schema: Dict[str, Any],
        dto_class: Union[Dto, Type[Dto]],
        operation_id: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a valid (json-compatible) dict for all the `dto_class` properties.
        """

        def get_constrained_values(property_name: str) -> List[Any]:
            relations = dto_class.get_relations()
            values_list = [
                c.values
                for c in relations
                if (
                    isinstance(c, PropertyValueConstraint)
                    and c.property_name == property_name
                )
            ]
            # values should be empty or contain 1 list of allowed values
            return values_list.pop() if values_list else []

        def get_dependent_id(
            property_name: str, operation_id: str
        ) -> Optional[Union[str, int, float]]:
            relations = dto_class.get_relations()
            # multiple get paths are possible based on the operation being performed
            id_get_paths = [
                (d.get_path, d.operation_id)
                for d in relations
                if (isinstance(d, IdDependency) and d.property_name == property_name)
            ]
            if not id_get_paths:
                return None
            if len(id_get_paths) == 1:
                id_get_path, _ = id_get_paths.pop()
            else:
                try:
                    [id_get_path] = [
                        path
                        for path, operation in id_get_paths
                        if operation == operation_id
                    ]
                # There could be multiple get_paths, but not one for the current operation
                except ValueError:
                    return None
            valid_id = self.get_valid_id_for_endpoint(
                endpoint=id_get_path, method="get"
            )
            logger.debug(f"get_dependent_id for {id_get_path} returned {valid_id}")
            return valid_id

        json_data: Dict[str, Any] = {}

        for property_name in schema.get("properties", []):
            properties_schema = schema["properties"][property_name]

            property_type = properties_schema.get("type")
            if property_type is None:
                property_types = properties_schema.get("types")
                if property_types is None:
                    if properties_schema.get("properties") is not None:
                        nested_data = self.get_json_data_for_dto_class(
                            schema=properties_schema,
                            dto_class=DefaultDto,
                        )
                        json_data[property_name] = nested_data
                        continue
                selected_type_schema = choice(property_types)
                property_type = selected_type_schema["type"]
            if properties_schema.get("readOnly", False):
                continue
            if constrained_values := get_constrained_values(property_name):
                # do not add properties that are configured to be ignored
                if IGNORE in constrained_values:
                    continue
                json_data[property_name] = choice(constrained_values)
                continue
            if (
                dependent_id := get_dependent_id(
                    property_name=property_name, operation_id=operation_id
                )
            ) is not None:
                json_data[property_name] = dependent_id
                continue
            if property_type == "object":
                object_data = self.get_json_data_for_dto_class(
                    schema=properties_schema,
                    dto_class=DefaultDto,
                    operation_id="",
                )
                json_data[property_name] = object_data
                continue
            if property_type == "array":
                array_data = self.get_json_data_for_dto_class(
                    schema=properties_schema["items"],
                    dto_class=DefaultDto,
                    operation_id=operation_id,
                )
                json_data[property_name] = [array_data]
                continue
            json_data[property_name] = value_utils.get_valid_value(properties_schema)
        return json_data

    @keyword
    def get_invalidated_url(self, valid_url: str) -> Optional[str]:
        """
        Return an url with all the path parameters in the `valid_url` replaced by a
        random UUID.

        Raises ValueError if the valid_url cannot be invalidated.
        """
        parameterized_endpoint = self.get_parameterized_endpoint_from_url(valid_url)
        parameterized_url = self.base_url + parameterized_endpoint
        valid_url_parts = list(reversed(valid_url.split("/")))
        parameterized_parts = reversed(parameterized_url.split("/"))
        for index, (parameterized_part, _) in enumerate(
            zip(parameterized_parts, valid_url_parts)
        ):
            if parameterized_part.startswith("{") and parameterized_part.endswith("}"):
                valid_url_parts[index] = uuid4().hex
                valid_url_parts.reverse()
                invalid_url = "/".join(valid_url_parts)
                return invalid_url
        raise ValueError(f"{parameterized_endpoint} could not be invalidated.")

    @keyword
    def get_parameterized_endpoint_from_url(self, url: str) -> str:
        """
        Return the endpoint as found in the `paths` section based on the given `url`.
        """
        endpoint = url.replace(self.base_url, "")
        endpoint_parts = endpoint.split("/")
        # first part will be '' since an endpoint starts with /
        endpoint_parts.pop(0)
        parameterized_endpoint = self.get_parametrized_endpoint(endpoint=endpoint)
        return parameterized_endpoint

    @keyword
    def get_invalid_json_data(
        self,
        url: str,
        method: str,
        status_code: int,
        request_data: RequestData,
    ) -> Dict[str, Any]:
        """
        Return `json_data` based on the `dto` on the `request_data` that will cause
        the provided `status_code` for the `method` operation on the `url`.

        > Note: applicable UniquePropertyValueConstraint and IdReference Relations are
            considered before changes to `json_data` are made.
        """
        method = method.lower()
        data_relations = request_data.dto.get_relations_for_error_code(status_code)
        if not data_relations:
            if not request_data.dto_schema:
                raise ValueError(
                    "Failed to invalidate: no data_relations and empty schema."
                )
            json_data = request_data.dto.get_invalidated_data(
                schema=request_data.dto_schema,
                status_code=status_code,
                invalid_property_default_code=self.invalid_property_default_response,
            )
            return json_data
        resource_relation = choice(data_relations)
        if isinstance(resource_relation, UniquePropertyValueConstraint):
            json_data = run_keyword(
                "get_json_data_with_conflict",
                url,
                method,
                request_data.dto,
                status_code,
            )
        elif isinstance(resource_relation, IdReference):
            run_keyword("ensure_in_use", url, resource_relation)
            json_data = request_data.dto.as_dict()
        else:
            json_data = request_data.dto.get_invalidated_data(
                schema=request_data.dto_schema,
                status_code=status_code,
                invalid_property_default_code=self.invalid_property_default_response,
            )
        return json_data

    @keyword
    def get_invalidated_parameters(
        self,
        status_code: int,
        request_data: RequestData,
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Returns a version of `params, headers` as present on `request_data` that has
        been modified to cause the provided `status_code`.
        """
        if not request_data.parameters:
            raise ValueError("No params or headers to invalidate.")

        # ensure the status_code can be triggered
        relations = request_data.dto.get_parameter_relations_for_error_code(status_code)
        relations_for_status_code = [
            r
            for r in relations
            if isinstance(r, PropertyValueConstraint)
            and (
                r.error_code == status_code or r.invalid_value_error_code == status_code
            )
        ]
        parameters_to_ignore = {
            r.property_name
            for r in relations_for_status_code
            if r.invalid_value_error_code == status_code and r.invalid_value == IGNORE
        }
        relation_property_names = {r.property_name for r in relations_for_status_code}
        if not relation_property_names:
            if status_code != self.invalid_property_default_response:
                raise ValueError(
                    f"No relations to cause status_code {status_code} found."
                )

        # ensure we're not modifying mutable properties
        params = deepcopy(request_data.params)
        headers = deepcopy(request_data.headers)

        if status_code == self.invalid_property_default_response:
            # take the params and headers that can be invalidated based on data type
            # and expand the set with properties that can be invalided by relations
            parameter_names = set(request_data.params_that_can_be_invalidated).union(
                request_data.headers_that_can_be_invalidated
            )
            parameter_names.update(relation_property_names)
            if not parameter_names:
                raise ValueError(
                    "None of the query parameters and headers can be invalidated."
                )
        else:
            # non-default status_codes can only be the result of a Relation
            parameter_names = relation_property_names

        # Dto mappings may contain generic mappings for properties that are not present
        # in this specific schema
        request_data_parameter_names = [p.get("name") for p in request_data.parameters]
        additional_relation_property_names = {
            n for n in relation_property_names if n not in request_data_parameter_names
        }
        if additional_relation_property_names:
            logger.warning(
                f"get_parameter_relations_for_error_code yielded properties that are "
                f"not defined in the schema: {additional_relation_property_names}\n"
                f"These properties will be ignored for parameter invalidation."
            )
            parameter_names = parameter_names - additional_relation_property_names

        if not parameter_names:
            raise ValueError(
                f"No parameter can be changed to cause status_code {status_code}."
            )

        parameter_names = parameter_names - parameters_to_ignore
        parameter_to_invalidate = choice(tuple(parameter_names))

        # check for invalid parameters in the provided request_data
        try:
            [parameter_data] = [
                data
                for data in request_data.parameters
                if data["name"] == parameter_to_invalidate
            ]
        except Exception:
            raise ValueError(
                f"{parameter_to_invalidate} not found in provided parameters."
            ) from None

        # get the invalid_value for the chosen parameter
        try:
            [invalid_value_for_error_code] = [
                r.invalid_value
                for r in relations_for_status_code
                if r.property_name == parameter_to_invalidate
                and r.invalid_value_error_code == status_code
            ]
        except ValueError:
            invalid_value_for_error_code = NOT_SET

        # get the constraint values if available for the chosen parameter
        try:
            [values_from_constraint] = [
                r.values
                for r in relations_for_status_code
                if r.property_name == parameter_to_invalidate
            ]
        except ValueError:
            values_from_constraint = []

        # if the parameter was not provided, add it to params / headers
        params, headers = self.ensure_parameter_in_parameters(
            parameter_to_invalidate=parameter_to_invalidate,
            params=params,
            headers=headers,
            parameter_data=parameter_data,
            values_from_constraint=values_from_constraint,
        )

        # determine the invalid_value
        if invalid_value_for_error_code != NOT_SET:
            invalid_value = invalid_value_for_error_code
        else:
            if parameter_to_invalidate in params.keys():
                valid_value = params[parameter_to_invalidate]
            else:
                valid_value = headers[parameter_to_invalidate]

            value_schema = resolve_schema(parameter_data["schema"])
            invalid_value = value_utils.get_invalid_value(
                value_schema=value_schema,
                current_value=valid_value,
                values_from_constraint=values_from_constraint,
            )
        logger.debug(f"{parameter_to_invalidate} changed to {invalid_value}")

        # update the params / headers and return
        if parameter_to_invalidate in params.keys():
            params[parameter_to_invalidate] = invalid_value
        else:
            headers[parameter_to_invalidate] = invalid_value
        return params, headers

    @staticmethod
    def ensure_parameter_in_parameters(
        parameter_to_invalidate: str,
        params: Dict[str, Any],
        headers: Dict[str, str],
        parameter_data: Dict[str, Any],
        values_from_constraint: List[Any],
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Returns the params, headers tuple with parameter_to_invalidate with a valid
        value to params or headers if not originally present.
        """
        if (
            parameter_to_invalidate not in params.keys()
            and parameter_to_invalidate not in headers.keys()
        ):
            if values_from_constraint:
                valid_value = choice(values_from_constraint)
            else:
                parameter_schema = resolve_schema(parameter_data["schema"])
                valid_value = value_utils.get_valid_value(parameter_schema)
            if (
                parameter_data["in"] == "query"
                and parameter_to_invalidate not in params.keys()
            ):
                params[parameter_to_invalidate] = valid_value
            if (
                parameter_data["in"] == "header"
                and parameter_to_invalidate not in headers.keys()
            ):
                headers[parameter_to_invalidate] = valid_value
        return params, headers

    @keyword
    def ensure_in_use(self, url: str, resource_relation: IdReference) -> None:
        """
        Ensure that the (right-most) `id` of the resource referenced by the `url`
        is used by the resource defined by the `resource_relation`.
        """
        resource_id = ""

        endpoint = url.replace(self.base_url, "")
        endpoint_parts = endpoint.split("/")
        parameterized_endpoint = self.get_parametrized_endpoint(endpoint=endpoint)
        parameterized_endpoint_parts = parameterized_endpoint.split("/")
        for part, param_part in zip(
            reversed(endpoint_parts), reversed(parameterized_endpoint_parts)
        ):
            if param_part.endswith("}"):
                resource_id = part
                break
        if not resource_id:
            raise ValueError(f"The provided url ({url}) does not contain an id.")
        request_data = self.get_request_data(
            method="post", endpoint=resource_relation.post_path
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
    ) -> Dict[str, Any]:
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
                endpoint = post_url.replace(self.base_url, "")
                request_data = self.get_request_data(endpoint=endpoint, method="post")
                post_json = request_data.dto.as_dict()
                for key in post_json.keys():
                    if key in json_data:
                        post_json[key] = json_data.get(key)
            else:
                post_url = url
                post_json = json_data
            endpoint = post_url.replace(self.base_url, "")
            request_data = self.get_request_data(endpoint=endpoint, method="post")
            response: Response = run_keyword(
                "authorized_request",
                post_url,
                "post",
                request_data.params,
                request_data.headers,
                post_json,
            )
            # conflicting resource may already exist
            assert (
                response.ok or response.status_code == conflict_status_code
            ), f"get_json_data_with_conflict received {response.status_code}: {response.json()}"
            return json_data
        raise ValueError(
            f"No UniquePropertyValueConstraint in the get_relations list on dto {dto}."
        )

    @keyword
    def authorized_request(  # pylint: disable=too-many-arguments
        self,
        url: str,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[JSON] = None,
    ) -> Response:
        """
        Perform a request using the security token or authentication set in the library.

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
            cookies=self.cookies,
            auth=self.auth,
            proxies=self.proxies,
            verify=self.verify,
            cert=self.cert,
        )
        logger.debug(f"Response text: {response.text}")
        return response
