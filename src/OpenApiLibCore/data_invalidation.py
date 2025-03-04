from copy import deepcopy
from random import choice
from typing import Any

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.dto_base import (
    NOT_SET,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
    resolve_schema,
)
from OpenApiLibCore.request_data import RequestData
from OpenApiLibCore.value_utils import IGNORE, get_invalid_value, get_valid_value

run_keyword = BuiltIn().run_keyword


def get_invalid_json_data(
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
        if not request_data.dto_schema:
            raise ValueError(
                "Failed to invalidate: no data_relations and empty schema."
            )
        json_data = request_data.dto.get_invalidated_data(
            schema=request_data.dto_schema,
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
        json_data = request_data.dto.get_invalidated_data(
            schema=request_data.dto_schema,
            status_code=status_code,
            invalid_property_default_code=invalid_property_default_response,
        )
    return json_data


def get_invalidated_parameters(
    status_code: int, request_data: RequestData, invalid_property_default_response: int
) -> tuple[dict[str, Any], dict[str, str]]:
    if not request_data.parameters:
        raise ValueError("No params or headers to invalidate.")

    # ensure the status_code can be triggered
    relations = request_data.dto.get_parameter_relations_for_error_code(status_code)
    relations_for_status_code = [
        r
        for r in relations
        if isinstance(r, PropertyValueConstraint)
        and (r.error_code == status_code or r.invalid_value_error_code == status_code)
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
    request_data_parameter_names = [p.get("name") for p in request_data.parameters]
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
            if data["name"] == parameter_to_invalidate
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

        value_schema = resolve_schema(parameter_data["schema"])
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
        headers[parameter_to_invalidate] = invalid_value
    return params, headers


def ensure_parameter_in_parameters(
    parameter_to_invalidate: str,
    params: dict[str, Any],
    headers: dict[str, str],
    parameter_data: dict[str, Any],
    values_from_constraint: list[Any],
) -> tuple[dict[str, Any], dict[str, str]]:
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
            parameter_schema = resolve_schema(parameter_data["schema"])
            valid_value = get_valid_value(parameter_schema)
        if (
            parameter_data["in"] == "query"
            and parameter_to_invalidate not in params.keys()
        ):
            params[parameter_to_invalidate] = valid_value
        if (
            parameter_data["in"] == "header"
            and parameter_to_invalidate not in headers.keys()
        ):
            headers[parameter_to_invalidate] = valid_value
    return params, headers
