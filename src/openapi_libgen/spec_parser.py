from dataclasses import dataclass
from os import getenv
from string import Template
from typing import Any, Generator

from robot.utils import is_truthy

from openapi_libgen.parsing_utils import remove_unsafe_characters_from_string
from OpenApiLibCore.parameter_utils import get_safe_name_for_oas_name
from OpenApiLibCore.value_utils import python_type_by_json_type_name

KEYWORD_TEMPLATE = r"""@keyword
    {signature}
        {body}"""

SIGNATURE_TEMPLATE = r"def {keyword_name}(self{arguments}, validate_against_schema: bool = True) -> Response:"

BODY_TEMPLATE_ = r"""overrides = {key: value for key, value in locals().items() if value is not UNSET and key != "self"}
        _ = overrides.pop("validate_against_schema", None)
        omit_list = overrides.pop("omit_parameters", [])
        body_data = overrides.pop("body", {})
        overrides.update(body_data)
        updated_path: str = substitute_path_parameters(path="{path_value}", substitution_dict=overrides)
        request_values: RequestValues = self.get_request_values(path=f"{updated_path}", method="{method_value}", overrides=overrides)
        request_values.remove_parameters(parameters=omit_list)
        response = self._perform_request(request_values=request_values)
        if validate_against_schema:
            run_keyword('validate_response_using_validator', response)
        return response"""


class BodyTemplate(Template):
    delimiter = ""


BODY_TEMPLATE = BodyTemplate(BODY_TEMPLATE_)


@dataclass
class OperationDetails:
    path: str
    method: str
    parameters: list[dict[str, Any]]
    request_body: dict[str, Any]
    summary: str
    description: str
    operation_id: str | None = (
        None  # operationId MUST be unique within the spec, so no default ""
    )


@dataclass
class ParameterDetails:
    type: str
    name: str
    schema: dict[str, Any]


@dataclass
class BodyDetails:
    schema: dict[str, Any]


def get_path_items(paths: dict[str, Any]) -> Generator[OperationDetails, None, None]:
    for path, operation_items in paths.items():
        for method, method_item in operation_items.items():
            operation_details = OperationDetails(
                path=path,
                method=method,
                operation_id=method_item.get("operationId", None),
                parameters=method_item.get("parameters", []),
                request_body=method_item.get("requestBody", {}),
                summary=method_item.get("summary"),
                description=method_item.get("description"),
            )
            yield operation_details


def get_parameter_details(
    operation_details: OperationDetails,
) -> list[ParameterDetails]:
    def _get_parameter_details(
        data: OperationDetails,
    ) -> Generator[ParameterDetails, None, None]:
        for param_data in data.parameters:
            name = param_data["name"]
            type = param_data["in"]
            if not (schema := param_data.get("schema", {})):
                content = param_data["content"]
                for _, media_data in content.items():
                    schema = media_data["schema"]

            yield ParameterDetails(
                type=type,
                name=name,
                schema=schema,
            )

    return list(_get_parameter_details(data=operation_details))


def get_body_details(operation_details: OperationDetails) -> BodyDetails | None:
    if not (body_data := operation_details.request_body):
        return None
    content = body_data["content"]
    if not (schema := content.get("application/json")):
        return None
    return BodyDetails(schema=schema["schema"])


def get_keyword_signature(operation_details: OperationDetails) -> str:
    USE_SUMMARY_AS_KEYWORD_NAME = getenv("USE_SUMMARY_AS_KEYWORD_NAME")
    EXPAND_BODY_ARGUMENTS = getenv("EXPAND_BODY_ARGUMENTS")

    if is_truthy(USE_SUMMARY_AS_KEYWORD_NAME):
        keyword_name = remove_unsafe_characters_from_string(
            operation_details.summary
        ).lower()
    elif operation_details.operation_id:
        keyword_name = remove_unsafe_characters_from_string(
            operation_details.operation_id
        ).lower()
    else:
        keyword_name = remove_unsafe_characters_from_string(
            f"{operation_details.method}_{operation_details.path}"
        )

    parameters = get_parameter_details(operation_details=operation_details)
    path_parameters = [p for p in parameters if p.type == "path"]
    query_parameters = [p for p in parameters if p.type == "query"]
    header_parameters = [p for p in parameters if p.type == "header"]

    body_details = get_body_details(operation_details=operation_details)

    argument_parts: list[str] = []
    # Keep track of the already used argument names. From the OAS:
    # "A unique parameter is defined by a combination of a name and location"
    # To prevent duplicates, a location prefix is added if a duplication would occur.
    keyword_argument_names: set[str] = set()

    for parameter in path_parameters:
        if "anyOf" in parameter.schema:
            parameter_python_type = "Any"
        else:
            parameter_json_type = parameter.schema["type"]
            parameter_python_type = python_type_by_json_type_name(
                parameter_json_type
            ).__name__
        annotation = f"{parameter_python_type} = UNSET"
        safe_name = get_safe_name_for_oas_name(parameter.name)
        keyword_argument_names.add(safe_name)
        argument = f", {safe_name}: {annotation}"
        argument_parts.append(argument)
    arguments = "".join(argument_parts)

    if body_details:
        body_json_type = body_details.schema["type"]
        body_python_type = python_type_by_json_type_name(body_json_type).__name__
        if body_python_type == "dict" and is_truthy(EXPAND_BODY_ARGUMENTS):
            body_properties = body_details.schema["properties"]
            for property_name, property_data in body_properties.items():
                if "anyOf" in property_data:
                    property_python_type = "Any"
                else:
                    property_json_type = property_data["type"]
                    property_python_type = python_type_by_json_type_name(
                        property_json_type
                    ).__name__
                annotation = f"{property_python_type} = UNSET"
                safe_name = get_safe_name_for_oas_name(property_name)
                if safe_name in keyword_argument_names:
                    safe_name = "body_" + safe_name
                keyword_argument_names.add(safe_name)
                argument = f", {safe_name}: {annotation}"
                arguments += argument
        else:
            annotation = f"{body_python_type} = UNSET"
            argument = f", body: {annotation}"
            arguments += argument

    for parameter in query_parameters:
        if "anyOf" in parameter.schema:
            parameter_python_type = "Any"
        else:
            parameter_json_type = parameter.schema["type"]
            parameter_python_type = python_type_by_json_type_name(
                parameter_json_type
            ).__name__
        annotation = f"{parameter_python_type} = UNSET"
        safe_name = get_safe_name_for_oas_name(parameter.name)
        if safe_name in keyword_argument_names:
            safe_name = "query_" + safe_name
        keyword_argument_names.add(safe_name)
        argument = f", {safe_name}: {annotation}"
        arguments += argument

    for parameter in header_parameters:
        if "anyOf" in parameter.schema:
            parameter_python_type = "Any"
        else:
            parameter_json_type = parameter.schema["type"]
            parameter_python_type = python_type_by_json_type_name(
                parameter_json_type
            ).__name__
        annotation = f"{parameter_python_type} = UNSET"
        safe_name = get_safe_name_for_oas_name(parameter.name)
        if safe_name in keyword_argument_names:
            safe_name = "header_" + safe_name
        keyword_argument_names.add(safe_name)
        argument = f", {safe_name}: {annotation}"
        arguments += argument

    if arguments:
        arguments += ", omit_parameters: Iterable[str] = frozenset()"

    return SIGNATURE_TEMPLATE.format(keyword_name=keyword_name, arguments=arguments)


def get_keyword_body(data: OperationDetails) -> str:
    return BODY_TEMPLATE.safe_substitute(path_value=data.path, method_value=data.method)


def get_keyword_data(openapi_spec: dict[str, Any]) -> Generator[str, None, None]:
    for path_item in get_path_items(openapi_spec["paths"]):
        signature = get_keyword_signature(path_item)
        body = get_keyword_body(path_item)
        yield KEYWORD_TEMPLATE.format(signature=signature, body=body)
