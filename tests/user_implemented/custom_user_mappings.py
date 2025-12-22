# pylint: disable=invalid-name
from typing import Callable

from OpenApiLibCore import (
    IGNORE,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    RelationsMapping,
    ResourceRelation,
    UniquePropertyValueConstraint,
)


class WagegroupMapping(RelationsMapping):
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


class WagegroupDeleteMapping(RelationsMapping):
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


class ParttimeDayMapping(RelationsMapping):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="weekday",
                values=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            ),
        ]
        return relations


class ParttimeScheduleMapping(RelationsMapping):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="parttime_days",
                values=[ParttimeDayMapping],
            ),
        ]
        return relations


class EmployeeMapping(RelationsMapping):
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
                values=[ParttimeScheduleMapping],
                treat_as_mandatory=True,
                invalid_value=IGNORE,
                invalid_value_error_code=400,
            ),
        ]
        return relations


class PatchEmployeeMapping(RelationsMapping):
    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="If-Match",
                values=["overridden by listener"],
                invalid_value="not an etag",
                invalid_value_error_code=412,
            ),
            PropertyValueConstraint(
                property_name="If-Match",
                values=["will be updated by listener"],
                invalid_value=IGNORE,
                invalid_value_error_code=422,
            ),
        ]
        return relations

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
        ]
        return relations


class EnergyLabelMapping(RelationsMapping):
    @staticmethod
    def get_path_relations() -> list[PathPropertiesConstraint]:
        relations: list[PathPropertiesConstraint] = [
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


class MessageMapping(RelationsMapping):
    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="secret-code",  # note: property name converted by FastAPI
                values=[42],
                error_code=401,
            ),
            PropertyValueConstraint(
                property_name="dummy",  # note: error code and property don't exist
                values=[42],
                error_code=402,
            ),
            PropertyValueConstraint(
                property_name="seal",
                values=[IGNORE],
                error_code=403,
            ),
        ]
        return relations


RELATIONS_MAPPING: dict[tuple[str, str], type[RelationsMapping]] = {
    ("/wagegroups", "post"): WagegroupMapping,
    ("/wagegroups/{wagegroup_id}", "delete"): WagegroupDeleteMapping,
    ("/wagegroups/{wagegroup_id}", "put"): WagegroupMapping,
    ("/employees", "post"): EmployeeMapping,
    ("/employees/{employee_id}", "patch"): PatchEmployeeMapping,
    ("/energy_label/{zipcode}/{home_number}", "get"): EnergyLabelMapping,
    ("/secret_message", "get"): MessageMapping,
}


def my_transformer(identifier_name: str) -> str:
    return identifier_name.replace("/", "_")


# NOTE: "/available_employees": "identification" is not mapped for testing purposes
ID_MAPPING: dict[str, str | tuple[str, Callable[[str], str] | Callable[[int], int]]] = {
    "/employees": "identification",
    "/employees/{employee_id}": "identification",
    "/wagegroups": "wagegroup_id",
    "/wagegroups/{wagegroup_id}": ("wagegroup_id", my_transformer),
    "/wagegroups/{wagegroup_id}/employees": "identification",
}

# NOTE: WagegroupDeleteMapping does not have path mappings for testing purposes
PATH_MAPPING: dict[str, type[RelationsMapping]] = {
    "/energy_label/{zipcode}/{home_number}": EnergyLabelMapping,
    "/wagegroups/{wagegroup_id}": WagegroupDeleteMapping,
}
