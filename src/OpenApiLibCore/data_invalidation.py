from random import choice
from typing import Any

from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.dto_base import (
    IdReference,
    PathPropertiesConstraint,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.request_data import RequestData

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
