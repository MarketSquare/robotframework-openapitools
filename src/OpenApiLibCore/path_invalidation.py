"""Module holding functions related to invalidation of paths and urls."""

from random import choice
from uuid import uuid4

from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.dto_base import PathPropertiesConstraint
from OpenApiLibCore.protocols import GetDtoClassType

run_keyword = BuiltIn().run_keyword


def get_invalidated_url(
    valid_url: str,
    path: str,
    base_url: str,
    get_dto_class: GetDtoClassType,
    expected_status_code: int,
) -> str:
    dto_class = get_dto_class(path=path, method="get")
    relations = dto_class.get_relations()
    paths = [
        p.invalid_value
        for p in relations
        if isinstance(p, PathPropertiesConstraint)
        and p.invalid_value_error_code == expected_status_code
    ]
    if paths:
        url = f"{base_url}{choice(paths)}"
        return url
    parameterized_path: str = run_keyword("get_parameterized_path_from_url", valid_url)
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
