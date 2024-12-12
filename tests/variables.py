from typing import Any

from requests.auth import HTTPDigestAuth

from OpenApiLibCore import (
    IGNORE,
    DefaultDto,
    Dto,
    IdDependency,
    IdReference,
    PropertyValueConstraint,
    Relation,
    UniquePropertyValueConstraint,
)


class WagegroupDto(Dto):
    @staticmethod
    def get_relations() -> list[Relation]:
        relations: list[Relation] = [
            UniquePropertyValueConstraint(
                property_name="id",
                value="Teapot",
                error_code=418,
            ),
            IdReference(
                property_name="wagegroup_id",
                post_path="/employees",
                error_code=406,
            ),
            PropertyValueConstraint(
                property_name="overtime_percentage",
                values=[IGNORE],
                invalid_value=110,
                invalid_value_error_code=422,
            ),
            PropertyValueConstraint(
                property_name="hourly_rate",
                values=[80.50, 90.95, 99.99],
            ),
        ]
        return relations


class EmployeeDto(Dto):
    @staticmethod
    def get_relations() -> list[Relation]:
        relations: list[Relation] = [
            IdDependency(
                property_name="wagegroup_id",
                get_path="/wagegroups",
                error_code=451,
            ),
            PropertyValueConstraint(
                property_name="date_of_birth",
                values=["1970-07-07", "1980-08-08", "1990-09-09"],
                invalid_value="2020-02-20",
                invalid_value_error_code=403,
                error_code=422,
            ),
        ]
        return relations


def get_variables() -> dict[str, Any]:
    """Automatically called by Robot Framework to load variables."""
    id_reference = IdReference(
        property_name="wagegroup_id",
        post_path="/employees",
        error_code=406,
    )
    invalid_id_reference = IdReference(
        property_name="wagegroup_id",
        post_path="/employees/{employee_id}",
        error_code=406,
    )
    wagegroup_dto = WagegroupDto
    employee_dto = EmployeeDto
    default_dto = DefaultDto
    extra_headers: dict[str, str] = {"foo": "bar", "eggs": "bacon"}
    return {
        "ID_REFERENCE": id_reference,
        "INVALID_ID_REFERENCE": invalid_id_reference,
        "DEFAULT_DTO": default_dto,
        "WAGEGROUP_DTO": wagegroup_dto,
        "EMPLOYEE_DTO": employee_dto,
        "EXTRA_HEADERS": extra_headers,
        "API_KEY": {"api_key": "Super secret key"},
        "DIGEST_AUTH": HTTPDigestAuth(username="Jane", password="Joe"),
    }
