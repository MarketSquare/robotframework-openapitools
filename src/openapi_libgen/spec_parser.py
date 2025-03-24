from dataclasses import dataclass
from os import getenv
from typing import Any, Generator

from openapi_libgen.parsing_utils import remove_unsafe_characters_from_string

KEYWORD_TEMPLATE = r"""@keyword
    {signature}
        {body}"""

SIGNATURE_TEMPLATE = r"def {keyword_name}(self{arguments}) -> Response:"

BODY_TEMPLATE = r"""request_values: RequestValues = self.get_request_values(path="{path}", method="{method}")
        return self._perform_request(request_values=request_values)"""


@dataclass
class ParameterDetails: ...


@dataclass
class OperationDetails:
    path: str
    method: str
    operation_id: str
    parameters: list[dict[str, Any]]
    request_body: dict[str, Any]
    summary: str
    description: str


def get_path_items(paths: dict[str, Any]) -> Generator[OperationDetails, None, None]:
    for path, operation_items in paths.items():
        for method, method_item in operation_items.items():
            operation_details = OperationDetails(
                path=path,
                method=method,
                operation_id=method_item["operationId"],
                parameters=method_item.get("parameters", []),
                request_body=method_item.get("requestBody", {}),
                summary=method_item.get("summary"),
                description=method_item.get("description"),
            )
            yield operation_details


def get_keyword_signature(data: OperationDetails) -> str:
    use_summary_as_keyword_name = getenv("USE_SUMMARY_AS_KEYWORD_NAME")
    if use_summary_as_keyword_name:
        keyword_name = remove_unsafe_characters_from_string(data.summary).lower()
    else:
        keyword_name = remove_unsafe_characters_from_string(data.operation_id).lower()
    parameters = ""
    return SIGNATURE_TEMPLATE.format(keyword_name=keyword_name, arguments=parameters)


def get_keyword_body(data: OperationDetails) -> str:
    return BODY_TEMPLATE.format(path=data.path, method=data.method)


def get_keyword_data(openapi_spec: dict[str, Any]) -> Generator[str, None, None]:
    for path_item in get_path_items(openapi_spec["paths"]):
        signature = get_keyword_signature(path_item)
        body = get_keyword_body(path_item)
        yield KEYWORD_TEMPLATE.format(signature=signature, body=body)
