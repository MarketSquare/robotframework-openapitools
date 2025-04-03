"""Module holding the functions related to validation of requests and responses."""

import json as _json
from enum import Enum
from http import HTTPStatus
from typing import Any, Mapping

from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from openapi_core.exceptions import OpenAPIError
from openapi_core.templating.paths.exceptions import ServerNotFound
from openapi_core.validation.exceptions import ValidationError
from openapi_core.validation.response.exceptions import ResponseValidationError
from requests import Response
from robot.api import logger
from robot.api.exceptions import Failure
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.dto_base import resolve_schema
from OpenApiLibCore.protocols import ResponseValidatorType
from OpenApiLibCore.request_data import RequestData, RequestValues

run_keyword = BuiltIn().run_keyword


class ValidationLevel(str, Enum):
    """The available levels for the response_validation parameter."""

    DISABLED = "DISABLED"
    INFO = "INFO"
    WARN = "WARN"
    STRICT = "STRICT"


def perform_validated_request(
    path: str,
    status_code: int,
    request_values: RequestValues,
    original_data: Mapping[str, Any],
) -> None:
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
        request_data: RequestData = run_keyword("get_request_data", path, "GET")
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
                    f"{get_response.status_code} was received after trying to get "
                    f"{request_values.url} after sucessfully deleting it."
                )
        elif not get_response.ok:
            raise AssertionError(
                f"Resource could not be retrieved after failed deletion. "
                f"Url was {request_values.url}, status_code was {get_response.status_code}"
            )


def assert_href_to_resource_is_valid(
    href: str, origin: str, base_url: str, referenced_resource: dict[str, Any]
) -> None:
    url = f"{origin}{href}"
    path = url.replace(base_url, "")
    request_data: RequestData = run_keyword("get_request_data", path, "GET")
    params = request_data.params
    headers = request_data.headers
    get_response = run_keyword("authorized_request", url, "GET", params, headers)
    assert get_response.json() == referenced_resource, (
        f"{get_response.json()} not equal to original {referenced_resource}"
    )


def validate_response(
    path: str,
    response: Response,
    response_validator: ResponseValidatorType,
    server_validation_warning_logged: bool,
    disable_server_validation: bool,
    invalid_property_default_response: int,
    response_validation: str,
    openapi_spec: dict[str, Any],
    original_data: Mapping[str, Any],
) -> None:
    if response.status_code == int(HTTPStatus.NO_CONTENT):
        assert not response.content
        return None

    try:
        _validate_response(
            response=response,
            response_validator=response_validator,
            server_validation_warning_logged=server_validation_warning_logged,
            disable_server_validation=disable_server_validation,
            invalid_property_default_response=invalid_property_default_response,
            response_validation=response_validation,
        )
    except OpenAPIError as exception:
        raise Failure(
            f"Response did not pass schema validation: {exception}"
        ) from exception

    request_method = response.request.method
    if request_method is None:
        logger.warn(
            f"Could not validate response for path {path}; no method found "
            f"on the request property of the provided response."
        )
        return None

    response_spec = _get_response_spec(
        path=path,
        method=request_method,
        status_code=response.status_code,
        openapi_spec=openapi_spec,
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
    response_schema = resolve_schema(response_spec["content"][content_type]["schema"])

    response_types = response_schema.get("types")
    if response_types:
        # In case of oneOf / anyOf there can be multiple possible response types
        # which makes generic validation too complex
        return None
    response_type = response_schema.get("type", "undefined")
    if response_type not in ["object", "array"]:
        _validate_value_type(value=json_response, expected_type=response_type)
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
                run_keyword("validate_resource_properties", resource, list_item_schema)
        else:
            for item in json_response:
                _validate_value_type(value=item, expected_type=type_of_list_items)
        # no further validation; value validation of individual resources should
        # be performed on the path for the specific resources
        return None

    run_keyword("validate_resource_properties", json_response, response_schema)
    # ensure the href is valid if present in the response
    if href := json_response.get("href"):
        run_keyword("assert_href_to_resource_is_valid", href, json_response)
    # every property that was sucessfully send and that is in the response
    # schema must have the value that was send
    if response.ok and response.request.method in ["POST", "PUT", "PATCH"]:
        run_keyword("validate_send_response", response, original_data)
    return None


def validate_resource_properties(
    resource: dict[str, Any], schema: dict[str, Any]
) -> None:
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
                _validate_type_of_extra_properties(
                    extra_properties=extra_properties,
                    expected_type=allowed_additional_properties_type,
                )
            # If allowed, validation should not fail on extra properties
            extra_property_names = set()

        required_properties = set(schema.get("required", []))
        missing_properties = required_properties.difference(property_names_in_resource)

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


def validate_send_response(
    response: Response,
    original_data: Mapping[str, Any],
) -> None:
    def validate_list_response(send_list: list[Any], received_list: list[Any]) -> None:
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


def validate_response_using_validator(
    response: Response,
    response_validator: ResponseValidatorType,
) -> None:
    openapi_request = RequestsOpenAPIRequest(response.request)
    openapi_response = RequestsOpenAPIResponse(response)
    response_validator(request=openapi_request, response=openapi_response)


def _validate_response(
    response: Response,
    response_validator: ResponseValidatorType,
    server_validation_warning_logged: bool,
    disable_server_validation: bool,
    invalid_property_default_response: int,
    response_validation: str,
) -> None:
    try:
        validate_response_using_validator(
            response=response,
            response_validator=response_validator,
        )
    except (ResponseValidationError, ServerNotFound) as exception:
        error: BaseException | None = exception.__cause__
        validation_errors: list[ValidationError] = getattr(error, "schema_errors", [])
        if validation_errors:
            error_message = "\n".join(
                [
                    f"{list(getattr(error, 'schema_path', ''))}: {getattr(error, 'message', '')}"
                    for error in validation_errors
                ]
            )
        else:
            error_message = str(exception)

        if isinstance(exception, ServerNotFound):
            if not server_validation_warning_logged:
                logger.warn(
                    f"ServerNotFound was raised during response validation. "
                    f"Due to this, no full response validation will be performed."
                    f"\nThe original error was: {error_message}"
                )
                server_validation_warning_logged = True
            if disable_server_validation:
                return

        if response.status_code == invalid_property_default_response:
            logger.debug(error_message)
            return
        if response_validation == ValidationLevel.STRICT:
            logger.error(error_message)
            raise exception
        if response_validation == ValidationLevel.WARN:
            logger.warn(error_message)
        elif response_validation == ValidationLevel.INFO:
            logger.info(error_message)


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
        raise AssertionError(f"Validation of type '{expected_type}' is not supported.")
    if not isinstance(value, python_type):
        raise AssertionError(f"{value} is not of type {expected_type}")


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


def _get_response_spec(
    path: str, method: str, status_code: int, openapi_spec: dict[str, Any]
) -> dict[str, Any]:
    method = method.lower()
    status = str(status_code)
    spec: dict[str, Any] = {**openapi_spec}["paths"][path][method]["responses"][status]
    return spec
