"""Module holding the functions related to relations between resources."""

from requests import Response
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

import OpenApiLibCore.path_functions as pf
from OpenApiLibCore.dto_base import IdReference
from OpenApiLibCore.models import OpenApiObject
from OpenApiLibCore.request_data import RequestData

run_keyword = BuiltIn().run_keyword


def ensure_in_use(
    url: str,
    base_url: str,
    openapi_spec: OpenApiObject,
    resource_relation: IdReference,
) -> None:
    resource_id = ""

    path = url.replace(base_url, "")
    path_parts = path.split("/")
    parameterized_path = pf.get_parametrized_path(path=path, openapi_spec=openapi_spec)
    parameterized_path_parts = parameterized_path.split("/")
    for part, param_part in zip(
        reversed(path_parts), reversed(parameterized_path_parts)
    ):
        if param_part.endswith("}"):
            resource_id = part
            break
    if not resource_id:
        raise ValueError(f"The provided url ({url}) does not contain an id.")
    request_data: RequestData = run_keyword(
        "get_request_data", resource_relation.post_path, "post"
    )
    json_data = request_data.dto.as_dict()
    json_data[resource_relation.property_name] = resource_id
    post_url: str = run_keyword("get_valid_url", resource_relation.post_path)
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
