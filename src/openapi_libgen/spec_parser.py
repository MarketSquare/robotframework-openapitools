from os import getenv
from string import Template
from typing import Generator

from robot.utils import is_truthy

from openapi_libgen.parsing_utils import remove_unsafe_characters_from_string
from OpenApiLibCore.models import (
    ObjectSchema,
    OpenApiObject,
    OperationObject,
    PathItemObject,
    SchemaObjectTypes,
)
from OpenApiLibCore.parameter_utils import get_safe_name_for_oas_name

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


class OperationDetails(OperationObject):
    path: str
    method: str


def get_path_items(
    paths: dict[str, PathItemObject],
) -> Generator[OperationDetails, None, None]:
    for path, path_item_object in paths.items():
        operations = path_item_object.get_operations()
        for method, operation_object in operations.items():
            operation_details = OperationDetails(
                path=path,
                method=method,
                operationId=operation_object.operationId,
                parameters=operation_object.parameters,
                requestBody=operation_object.requestBody,
                summary=operation_object.summary,
                description=operation_object.description,
            )
            yield operation_details


def get_keyword_signature(operation_details: OperationDetails) -> str:
    USE_SUMMARY_AS_KEYWORD_NAME = getenv("USE_SUMMARY_AS_KEYWORD_NAME")
    EXPAND_BODY_ARGUMENTS = getenv("EXPAND_BODY_ARGUMENTS")

    if is_truthy(USE_SUMMARY_AS_KEYWORD_NAME):
        keyword_name = remove_unsafe_characters_from_string(
            operation_details.summary
        ).lower()
    elif operation_details.operationId:
        keyword_name = remove_unsafe_characters_from_string(
            operation_details.operationId
        ).lower()
    else:
        keyword_name = remove_unsafe_characters_from_string(
            f"{operation_details.method}_{operation_details.path}"
        )

    parameters = operation_details.parameters or []
    path_parameters = [p for p in parameters if p.in_ == "path" and p.schema_]
    query_parameters = [p for p in parameters if p.in_ == "query" and p.schema_]
    header_parameters = [p for p in parameters if p.in_ == "header" and p.schema_]

    argument_parts: list[str] = []
    # Keep track of the already used argument names. From the OAS:
    # "A unique parameter is defined by a combination of a name and location"
    # To prevent duplicates, a location prefix is added if a duplication would occur.
    keyword_argument_names: set[str] = set()

    for parameter in path_parameters:
        annotation = f"{parameter.schema_.annotation_string} = UNSET"
        safe_name = get_safe_name_for_oas_name(parameter.name)
        keyword_argument_names.add(safe_name)
        argument = f", {safe_name}: {annotation}"
        argument_parts.append(argument)
    arguments = "".join(argument_parts)

    if operation_details.requestBody and operation_details.requestBody.schema_:
        schema = operation_details.requestBody.schema_
        if isinstance(schema, ObjectSchema) and is_truthy(EXPAND_BODY_ARGUMENTS):
            body_properties: dict[str, SchemaObjectTypes] = getattr(
                schema.properties, "root", {}
            )
            for property_name, property_schema in body_properties.items():
                annotation = f"{property_schema.annotation_string} = UNSET"
                safe_name = get_safe_name_for_oas_name(property_name)
                if safe_name in keyword_argument_names:
                    safe_name = "body_" + safe_name
                keyword_argument_names.add(safe_name)
                argument = f", {safe_name}: {annotation}"
                arguments += argument
        else:
            annotation = f"{schema.annotation_string} = UNSET"
            argument = f", body: {annotation}"
            arguments += argument

    for parameter in query_parameters:
        annotation = f"{parameter.schema_.annotation_string} = UNSET"
        safe_name = get_safe_name_for_oas_name(parameter.name)
        if safe_name in keyword_argument_names:
            safe_name = "query_" + safe_name
        keyword_argument_names.add(safe_name)
        argument = f", {safe_name}: {annotation}"
        arguments += argument

    for parameter in header_parameters:
        annotation = f"{parameter.schema_.annotation_string} = UNSET"
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


def get_keyword_data(openapi_object: OpenApiObject) -> Generator[str, None, None]:
    for path_item in get_path_items(openapi_object.paths):
        signature = get_keyword_signature(path_item)
        body = get_keyword_body(path_item)
        yield KEYWORD_TEMPLATE.format(signature=signature, body=body)
