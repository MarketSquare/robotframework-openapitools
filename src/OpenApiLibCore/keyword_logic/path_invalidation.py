"""Module holding functions related to invalidation of paths and urls."""

from random import choice
from typing import Literal, overload
from uuid import uuid4

from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.models import oas_models

run_keyword = BuiltIn().run_keyword


@overload
def _run_keyword(
    keyword_name: Literal["get_parameterized_path_from_url"], *args: str
) -> str: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["overload_default"], *args: object
) -> object: ...  # pragma: no cover


def _run_keyword(keyword_name: str, *args: object) -> object:
    return run_keyword(keyword_name, *args)  # pyright: ignore[reportArgumentType]


def get_invalidated_url(
    valid_url: str,
    base_url: str,
    openapi_spec: oas_models.OpenApiObject,
    expected_status_code: int,
) -> str:
    path = _run_keyword("get_parameterized_path_from_url", valid_url)
    path_item = openapi_spec.paths[path]

    relations_mapping = path_item.relations_mapping
    relations = relations_mapping.get_path_relations() if relations_mapping else []
    paths = [
        p.invalid_value
        for p in relations
        if p.invalid_value_error_code == expected_status_code
    ]
    if paths:
        url = f"{base_url}{choice(paths)}"
        return url
    parameterized_path = _run_keyword("get_parameterized_path_from_url", valid_url)
    parameterized_url = base_url + parameterized_path
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
    raise ValueError(f"{parameterized_path} could not be invalidated.")
