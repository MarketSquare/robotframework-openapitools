"""
Module holding the functions related to invalidation of valid data (generated
to make 2xx requests) to support testing for 4xx responses.
"""

from copy import deepcopy
from random import choice
from typing import Any, Literal, overload

from requests import Response
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.data_constraints.dto_base import (
    Dto,
)
from OpenApiLibCore.models import IGNORE, Ignore
from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    ObjectSchema,
    ParameterObject,
    UnionTypeSchema,
)
from OpenApiLibCore.models.request_data import RequestData
from OpenApiLibCore.models.resource_relations import (
    NOT_SET,
    IdReference,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
)

run_keyword = BuiltIn().run_keyword


@overload
def _run_keyword(
    keyword_name: Literal["get_json_data_with_conflict"], *args: object
) -> dict[str, JSON]: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["ensure_in_use"], *args: object
) -> None: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["get_request_data"], *args: str
) -> RequestData: ...  # pragma: no cover


@overload
def _run_keyword(
    keyword_name: Literal["authorized_request"], *args: object
) -> Response: ...  # pragma: no cover


def _run_keyword(keyword_name: str, *args: object) -> object:
    return run_keyword(keyword_name, *args)


def get_invalid_body_data(
    url: str,
    method: str,
    status_code: int,
    request_data: RequestData,
    invalid_data_default_response: int,
) -> JSON:
    method = method.lower()
    data_relations = request_data.constraint_mapping.get_body_relations_for_error_code(
        status_code
    )
    if not data_relations:
        if request_data.body_schema is None:
            raise ValueError(
                "Failed to invalidate: request_data does not contain a body_schema."
            )

        if not isinstance(request_data.body_schema, (ArraySchema, ObjectSchema)):
            raise NotImplementedError("primitive types not supported for body data.")

        if isinstance(request_data.body_schema, ArraySchema):
            if not isinstance(request_data.valid_data, list):
                raise ValueError("Type of valid_data does not match body_schema type.")
            invalid_item_data: list[JSON] = request_data.body_schema.get_invalid_data(
                valid_data=request_data.valid_data,
                constraint_mapping=request_data.constraint_mapping,
                status_code=status_code,
                invalid_property_default_code=invalid_data_default_response,
            )
            return [invalid_item_data]

        if not isinstance(request_data.valid_data, dict):
            raise ValueError("Type of valid_data does not match body_schema type.")
        json_data = request_data.body_schema.get_invalid_data(
            valid_data=request_data.valid_data,
            constraint_mapping=request_data.constraint_mapping,
            status_code=status_code,
            invalid_property_default_code=invalid_data_default_response,
        )
        return json_data

    resource_relation = choice(data_relations)
    if isinstance(resource_relation, UniquePropertyValueConstraint):
        return _run_keyword(
            "get_json_data_with_conflict",
            url,
            method,
            request_data.valid_data,
            request_data.constraint_mapping,
            status_code,
        )
    if isinstance(resource_relation, IdReference):
        _run_keyword("ensure_in_use", url, resource_relation)
        return request_data.valid_data

    if request_data.body_schema is None:
        raise ValueError(
            "Failed to invalidate: request_data does not contain a body_schema."
        )
    if not isinstance(request_data.body_schema, (ArraySchema, ObjectSchema)):
        raise NotImplementedError("primitive types not supported for body data.")

    if isinstance(request_data.body_schema, ArraySchema):
        if not isinstance(request_data.valid_data, list):
            raise ValueError("Type of valid_data does not match body_schema type.")
        invalid_item_data = request_data.body_schema.get_invalid_data(
            valid_data=request_data.valid_data,
            constraint_mapping=request_data.constraint_mapping,
            status_code=status_code,
            invalid_property_default_code=invalid_data_default_response,
        )
        return [invalid_item_data]

    if not isinstance(request_data.valid_data, dict):
        raise ValueError("Type of valid_data does not match body_schema type.")
    return request_data.body_schema.get_invalid_data(
        valid_data=request_data.valid_data,
        constraint_mapping=request_data.constraint_mapping,
        status_code=status_code,
        invalid_property_default_code=invalid_data_default_response,
    )


def get_invalidated_parameters(
    status_code: int, request_data: RequestData, invalid_data_default_response: int
) -> tuple[dict[str, JSON], dict[str, str]]:
    if not request_data.parameters:
        raise ValueError("No params or headers to invalidate.")

    # ensure the status_code can be triggered
    relations = request_data.constraint_mapping.get_parameter_relations_for_error_code(
        status_code
    )
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
        if status_code != invalid_data_default_response:
            raise ValueError(f"No relations to cause status_code {status_code} found.")

    # ensure we're not modifying mutable properties
    params = deepcopy(request_data.params)
    headers = deepcopy(request_data.headers)

    if status_code == invalid_data_default_response:
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

    # Constraint mappings may contain generic mappings for properties that are
    # not present in this specific schema
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

    parameter_names = parameter_names - parameters_to_ignore
    if not parameter_names:
        if parameters_to_ignore:
            for parameter_to_ignore in parameters_to_ignore:
                params.pop(parameter_to_ignore, None)
                headers.pop(parameter_to_ignore, None)
            return params, headers
        raise ValueError(
            f"No parameter can be changed to cause status_code {status_code}."
        )

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
            value_schema = choice(value_schema.resolved_schemas)

        invalid_value = value_schema.get_invalid_value(
            valid_value=valid_value,  # type: ignore[arg-type]
            values_from_constraint=values_from_constraint,
        )
    logger.debug(f"{parameter_to_invalidate} changed to {invalid_value}")

    # update the params / headers and return
    if parameter_to_invalidate in params.keys():
        params[parameter_to_invalidate] = invalid_value  # pyright: ignore[reportArgumentType]
    else:
        headers[parameter_to_invalidate] = str(invalid_value)
    return params, headers


def ensure_parameter_in_parameters(
    parameter_to_invalidate: str,
    params: dict[str, JSON],
    headers: dict[str, str],
    parameter_data: ParameterObject,
    values_from_constraint: list[JSON],
) -> tuple[dict[str, JSON], dict[str, str]]:
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
    url: str,
    base_url: str,
    method: str,
    json_data: dict[str, JSON],
    constraint_mapping: type[Dto],
    conflict_status_code: int,
) -> dict[str, Any]:
    method = method.lower()
    unique_property_value_constraints = [
        r
        for r in constraint_mapping.get_relations()
        if isinstance(r, UniquePropertyValueConstraint)
    ]
    for relation in unique_property_value_constraints:
        json_data[relation.property_name] = relation.value
        # create a new resource that the original request will conflict with
        if method in ["patch", "put"]:
            post_url_parts = url.split("/")[:-1]
            post_url = "/".join(post_url_parts)
            # the PATCH or PUT may use a different constraint_mapping than required for
            # POST so valid POST data must be constructed
            path = post_url.replace(base_url, "")
            request_data = _run_keyword("get_request_data", path, "post")
            post_json = request_data.valid_data
            if isinstance(post_json, dict):
                for key in post_json.keys():
                    if key in json_data:
                        post_json[key] = json_data.get(key)
        else:
            post_url = url
            post_json = json_data
            path = post_url.replace(base_url, "")
            request_data = _run_keyword("get_request_data", path, "post")

        response = _run_keyword(
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
        f"No UniquePropertyValueConstraint in the get_relations list on "
        f"constraint_mapping {constraint_mapping}."
    )
