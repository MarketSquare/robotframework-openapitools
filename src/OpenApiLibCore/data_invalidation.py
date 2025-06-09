"""
Module holding the functions related to invalidation of valid data (generated
to make 2xx requests) to support testing for 4xx responses.
"""

from copy import deepcopy
from random import choice
from typing import Any

from requests import Response
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.dto_base import (
    NOT_SET,
    Dto,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.models import ParameterObject, UnionTypeSchema
from OpenApiLibCore.request_data import RequestData
from OpenApiLibCore.value_utils import IGNORE, get_invalid_value

run_keyword = BuiltIn().run_keyword


def get_invalid_body_data(
    url: str,
    method: str,
    status_code: int,
    request_data: RequestData,
    invalid_property_default_response: int,
) -> dict[str, Any]:
    method = method.lower()
    data_relations = request_data.dto.get_relations_for_error_code(status_code)
    data_relations = [
        r for r in data_relations if not isinstance(r, PathPropertiesConstraint)
    ]
    if not data_relations:
        if request_data.body_schema is None:
            raise ValueError(
                "Failed to invalidate: request_data does not contain a body_schema."
            )
        json_data = request_data.dto.get_invalidated_data(
            schema=request_data.body_schema,
            status_code=status_code,
            invalid_property_default_code=invalid_property_default_response,
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
        if request_data.body_schema is None:
            raise ValueError(
                "Failed to invalidate: request_data does not contain a body_schema."
            )
        json_data = request_data.dto.get_invalidated_data(
            schema=request_data.body_schema,
            status_code=status_code,
            invalid_property_default_code=invalid_property_default_response,
        )
    return json_data


def get_invalidated_parameters(
    status_code: int, request_data: RequestData, invalid_property_default_response: int
) -> tuple[dict[str, JSON], dict[str, JSON]]:
    if not request_data.parameters:
        raise ValueError("No params or headers to invalidate.")

    # ensure the status_code can be triggered
    relations = request_data.dto.get_parameter_relations_for_error_code(status_code)
    relations_for_status_code = [
        r
        for r in relations
        if isinstance(r, PropertyValueConstraint)
        and (status_code in (r.error_code, r.invalid_value_error_code))
    ]
    parameters_to_ignore = {
        r.property_name
        for r in relations_for_status_code
        if r.invalid_value_error_code == status_code and r.invalid_value == IGNORE
    }
    relation_property_names = {r.property_name for r in relations_for_status_code}
    if not relation_property_names:
        if status_code != invalid_property_default_response:
            raise ValueError(f"No relations to cause status_code {status_code} found.")

    # ensure we're not modifying mutable properties
    params = deepcopy(request_data.params)
    headers = deepcopy(request_data.headers)

    if status_code == invalid_property_default_response:
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
    request_data_parameter_names = [p.name for p in request_data.parameters]
    additional_relation_property_names = {
        n for n in relation_property_names if n not in request_data_parameter_names
    }
    if additional_relation_property_names:
        logger.warn(
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
            if data.name == parameter_to_invalidate
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
    params, headers = ensure_parameter_in_parameters(
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

        value_schema = parameter_data.schema_
        if value_schema is None:
            raise ValueError(f"No schema defined for parameter: {parameter_data}.")

        if isinstance(value_schema, UnionTypeSchema):
            # FIXME: extra handling may be needed in case of values_from_constraint
            value_schema = choice(value_schema.resolved_schemas)

        invalid_value = get_invalid_value(
            value_schema=value_schema,
            current_value=valid_value,
            values_from_constraint=values_from_constraint,
        )
    logger.debug(f"{parameter_to_invalidate} changed to {invalid_value}")

    # update the params / headers and return
    if parameter_to_invalidate in params.keys():
        params[parameter_to_invalidate] = invalid_value
    else:
        headers[parameter_to_invalidate] = str(invalid_value)
    return params, headers


def ensure_parameter_in_parameters(
    parameter_to_invalidate: str,
    params: dict[str, JSON],
    headers: dict[str, JSON],
    parameter_data: ParameterObject,
    values_from_constraint: list[JSON],
) -> tuple[dict[str, JSON], dict[str, JSON]]:
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
            value_schema = parameter_data.schema_
            if value_schema is None:
                raise ValueError(f"No schema defined for parameter: {parameter_data}.")

            if isinstance(value_schema, UnionTypeSchema):
                value_schema = choice(value_schema.resolved_schemas)
            valid_value = value_schema.get_valid_value()
        if (
            parameter_data.in_ == "query"
            and parameter_to_invalidate not in params.keys()
        ):
            params[parameter_to_invalidate] = valid_value
        if (
            parameter_data.in_ == "header"
            and parameter_to_invalidate not in headers.keys()
        ):
            headers[parameter_to_invalidate] = str(valid_value)
    return params, headers


def get_json_data_with_conflict(
    url: str, base_url: str, method: str, dto: Dto, conflict_status_code: int
) -> dict[str, Any]:
    method = method.lower()
    json_data = dto.as_dict()
    unique_property_value_constraints = [
        r for r in dto.get_relations() if isinstance(r, UniquePropertyValueConstraint)
    ]
    for relation in unique_property_value_constraints:
        json_data[relation.property_name] = relation.value
        # create a new resource that the original request will conflict with
        if method in ["patch", "put"]:
            post_url_parts = url.split("/")[:-1]
            post_url = "/".join(post_url_parts)
            # the PATCH or PUT may use a different dto than required for POST
            # so a valid POST dto must be constructed
            path = post_url.replace(base_url, "")
            request_data: RequestData = run_keyword("get_request_data", path, "post")
            post_json = request_data.dto.as_dict()
            for key in post_json.keys():
                if key in json_data:
                    post_json[key] = json_data.get(key)
        else:
            post_url = url
            post_json = json_data
            path = post_url.replace(base_url, "")
            request_data = run_keyword("get_request_data", path, "post")

        response: Response = run_keyword(
            "authorized_request",
            post_url,
            "post",
            request_data.params,
            request_data.headers,
            post_json,
        )
        # conflicting resource may already exist
        assert response.ok or response.status_code == conflict_status_code, (
            f"get_json_data_with_conflict received {response.status_code}: {response.json()}"
        )
        return json_data
    raise ValueError(
        f"No UniquePropertyValueConstraint in the get_relations list on dto {dto}."
    )
