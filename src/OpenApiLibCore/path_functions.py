import json as _json
from itertools import zip_longest
from random import choice
from typing import Any, Callable, Type

from requests import Response
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.dto_base import Dto, PathPropertiesConstraint

run_keyword = BuiltIn().run_keyword


def match_parts(parts: list[str], spec_parts: list[str]) -> bool:
    for part, spec_part in zip_longest(parts, spec_parts, fillvalue="Filler"):
        if part == "Filler" or spec_part == "Filler":
            return False
        if part != spec_part and not spec_part.startswith("{"):
            return False
    return True


def get_parametrized_path(path: str, openapi_spec: dict[str, Any]) -> str:
    """
    Get the parametrized path as found in the `paths` section of the openapi
    document from a (partially) resolved path.
    """

    path_parts = path.split("/")
    # if the last part is empty, the path has a trailing `/` that
    # should be ignored during matching
    if path_parts[-1] == "":
        _ = path_parts.pop(-1)

    spec_paths: list[str] = {**openapi_spec}["paths"].keys()

    candidates: list[str] = []

    for spec_path in spec_paths:
        spec_path_parts = spec_path.split("/")
        # ignore trailing `/` the same way as for path_parts
        if spec_path_parts[-1] == "":
            _ = spec_path_parts.pop(-1)
        if match_parts(path_parts, spec_path_parts):
            candidates.append(spec_path)

    if not candidates:
        raise ValueError(f"{path} not found in paths section of the OpenAPI document.")

    if len(candidates) == 1:
        return candidates[0]
    # Multiple matches can happen in APIs with overloaded paths, e.g.
    # /users/me
    # /users/${user_id}
    # In this case, find the closest (or exact) match
    exact_match = [c for c in candidates if c == path]
    if exact_match:
        return exact_match[0]
    # TODO: Implement a decision mechanism when real-world examples become available
    # In the face of ambiguity, refuse the temptation to guess.
    raise ValueError(f"{path} matched to multiple paths: {candidates}")


# FIXME: Refacor to no longer require `method`
def get_valid_url(
    path: str,
    method: str,
    base_url: str,
    get_dto_class: Callable[[str, str], Type[Dto]],
    openapi_spec: dict[str, Any],
) -> str:
    method = method.lower()
    try:
        # path can be partially resolved or provided by a PathPropertiesConstraint
        parametrized_path = get_parametrized_path(path=path, openapi_spec=openapi_spec)
        _ = openapi_spec["paths"][parametrized_path]
    except KeyError:
        raise ValueError(
            f"{path} not found in paths section of the OpenAPI document."
        ) from None
    dto_class = get_dto_class(path=path, method=method)
    relations = dto_class.get_relations()
    paths = [p.path for p in relations if isinstance(p, PathPropertiesConstraint)]
    if paths:
        url = f"{base_url}{choice(paths)}"
        return url
    path_parts = list(path.split("/"))
    for index, part in enumerate(path_parts):
        if part.startswith("{") and part.endswith("}"):
            type_path_parts = path_parts[slice(index)]
            type_path = "/".join(type_path_parts)
            existing_id: str | int | float = run_keyword(
                "get_valid_id_for_path", type_path, method
            )
            path_parts[index] = str(existing_id)
    resolved_path = "/".join(path_parts)
    url = f"{base_url}{resolved_path}"
    return url


# FIXME: Refacor to no longer require `method`
def get_valid_id_for_path(
    path: str,
    method: str,
    get_id_property_name: Callable[
        [str], str | tuple[str, tuple[Callable[[str | int | float], str | int | float]]]
    ],  # FIXME: Protocol for the signature
) -> str | int | float:
    def dummy_transformer(valid_id: str | int | float) -> str | int | float:
        return valid_id

    method = method.lower()
    url: str = run_keyword("get_valid_url", path, method)
    # Try to create a new resource to prevent conflicts caused by
    # operations performed on the same resource by other test cases
    request_data = run_keyword("get_request_data", path, "post")

    response: Response = run_keyword(
        "authorized_request",
        url,
        "post",
        request_data.get_required_params(),
        request_data.get_required_headers(),
        request_data.get_required_properties_dict(),
    )

    # determine the id property name for this path and whether or not a transformer is used
    mapping = get_id_property_name(path=path)
    if isinstance(mapping, str):
        id_property = mapping
        # set the transformer to a dummy callable that returns the original value so
        # the transformer can be applied on any returned id
        # TODO: annotation should be a Generic
        id_transformer: Callable[[str | int | float], str | int | float] = (
            dummy_transformer
        )
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
    response_href: str = response_data.get("href", "")
    if response_href and (send_path not in response_href) and send_json:
        try:
            property_to_check = send_path.replace(response_href, "")[1:]
            item_list: list[dict[str, Any]] = response_data[property_to_check]
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
