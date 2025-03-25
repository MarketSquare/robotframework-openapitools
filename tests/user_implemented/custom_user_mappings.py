# pylint: disable=invalid-name
from typing import Type

from OpenApiLibCore import (
    IGNORE,
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    ResourceRelation,
    UniquePropertyValueConstraint,
)


class WagegroupDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
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
                property_name="hourly-rate",
                values=[80.99, 90.99, 99.99],
                error_code=400,
            ),
        ]
        return relations


class WagegroupDeleteDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
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
        ]
        return relations


class ParttimeDayDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="weekday",
                values=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            ),
        ]
        return relations


class ParttimeScheduleDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="parttime_days",
                values=[ParttimeDayDto],
            ),
        ]
        return relations


class EmployeeDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
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
            PropertyValueConstraint(
                property_name="parttime_schedule",
                values=[ParttimeScheduleDto],
                treat_as_mandatory=True,
            ),
        ]
        return relations


class EnergyLabelDto(Dto):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PathPropertiesConstraint(
                path="/energy_label/1111AA/10",
                invalid_value="/energy_label/0123AA",
                invalid_value_error_code=422,
            ),
        ]
        return relations

    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="extension",
                values=["E", "boven", "A4.1"],
                treat_as_mandatory=True,
            )
        ]
        return relations


class MessageDto(Dto):
    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="secret-code",  # note: property name converted by FastAPI
                values=[42],
                error_code=401,
            ),
            PropertyValueConstraint(
                property_name="seal",
                values=[IGNORE],
                error_code=403,
            ),
        ]
        return relations


DTO_MAPPING: dict[tuple[str, str], Type[Dto]] = {
    ("/wagegroups", "post"): WagegroupDto,
    ("/wagegroups/{wagegroup_id}", "delete"): WagegroupDeleteDto,
    ("/wagegroups/{wagegroup_id}", "put"): WagegroupDto,
    ("/employees", "post"): EmployeeDto,
    ("/employees/{employee_id}", "patch"): EmployeeDto,
    ("/energy_label/{zipcode}/{home_number}", "get"): EnergyLabelDto,
    ("/secret_message", "get"): MessageDto,
}

# NOTE: "/available_employees": "identification" is not mapped for testing purposes
ID_MAPPING: dict[str, str] = {
    "/employees": "identification",
    "/employees/{employee_id}": "identification",
    "/wagegroups": "wagegroup_id",
    "/wagegroups/{wagegroup_id}": "wagegroup_id",
    "/wagegroups/{wagegroup_id}/employees": "identification",
}
