"""Module holding the functions related to relations between resources."""

from typing import Literal, overload

from requests import Response
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

import OpenApiLibCore.keyword_logic.path_functions as _path_functions
from OpenApiLibCore.models.oas_models import OpenApiObject
from OpenApiLibCore.models.request_data import RequestData
from OpenApiLibCore.models.resource_relations import IdReference

run_keyword = BuiltIn().run_keyword


@overload
def _run_keyword(
    keyword_name: Literal["get_request_data"], *args: str
) -> RequestData: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_valid_url"], *args: str
) -> str: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["authorized_request"], *args: object
) -> Response: ...  # pragma: no cover


def _run_keyword(keyword_name: str, *args: object) -> object:
    return run_keyword(keyword_name, *args)


def ensure_in_use(
    url: str,
    base_url: str,
    openapi_spec: OpenApiObject,
    resource_relation: IdReference,
) -> None:
    resource_id = ""

    path = url.replace(base_url, "")
    path_parts = path.split("/")
    parameterized_path = _path_functions.get_parametrized_path(
        path=path, openapi_spec=openapi_spec
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
    request_data = _run_keyword("get_request_data", resource_relation.post_path, "post")
    json_data = request_data.valid_data if request_data.valid_data else {}
    # FIXME: currently only works for object / dict data
    if isinstance(json_data, dict):
        json_data[resource_relation.property_name] = resource_id
    post_url = _run_keyword("get_valid_url", resource_relation.post_path)
    response = _run_keyword(
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
