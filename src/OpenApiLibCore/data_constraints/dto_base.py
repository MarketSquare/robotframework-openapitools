"""
Module holding the (base) classes that can be used by the user of the OpenApiLibCore
to implement custom mappings for dependencies between resources in the API under
test and constraints / restrictions on properties of the resources.
"""

from abc import ABC
from dataclasses import dataclass
from importlib import import_module
from typing import Callable

from robot.api import logger

from OpenApiLibCore.models.resource_relations import (
    NOT_SET,
    PathPropertiesConstraint,
    ResourceRelation,
)
from OpenApiLibCore.protocols import (
    IConstraintMapping,
    IGetIdPropertyName,
)
from OpenApiLibCore.utils.id_mapping import dummy_transformer


@dataclass
class Dto(ABC):
    """Base class for the Dto class."""

    @staticmethod
    def get_path_relations() -> list[PathPropertiesConstraint]:
        """Return the list of path-related Relations."""
        return []

    @staticmethod
    def get_parameter_relations() -> list[ResourceRelation]:
        """Return the list of Relations for the header and query parameters."""
        return []

    @classmethod
    def get_parameter_relations_for_error_code(
        cls, error_code: int
    ) -> list[ResourceRelation]:
        """Return the list of Relations associated with the given error_code."""
        relations: list[ResourceRelation] = [
            r
            for r in cls.get_parameter_relations()
            if r.error_code == error_code
            or (
                getattr(r, "invalid_value_error_code", None) == error_code
                and getattr(r, "invalid_value", None) != NOT_SET
            )
        ]
        return relations

    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        """Return the list of Relations for the (json) body."""
        return []

    @classmethod
    def get_body_relations_for_error_code(
        cls, error_code: int
    ) -> list[ResourceRelation]:
        """
        Return the list of Relations associated with the given error_code that are
        applicable to the body / payload of the request.
        """
        relations: list[ResourceRelation] = [
            r
            for r in cls.get_relations()
            if r.error_code == error_code
            or (
                getattr(r, "invalid_value_error_code", None) == error_code
                and getattr(r, "invalid_value", None) != NOT_SET
            )
        ]
        return relations


def get_constraint_mapping_dict(
    mappings_module_name: str,
) -> dict[tuple[str, str], IConstraintMapping]:
    try:
        mappings_module = import_module(mappings_module_name)
        return mappings_module.DTO_MAPPING  # type: ignore[no-any-return]
    except (ImportError, AttributeError, ValueError) as exception:
        if mappings_module_name != "no mapping":
            logger.error(f"DTO_MAPPING was not imported: {exception}")
        return {}


def get_path_mapping_dict(
    mappings_module_name: str,
) -> dict[str, IConstraintMapping]:
    try:
        mappings_module = import_module(mappings_module_name)
        return mappings_module.PATH_MAPPING  # type: ignore[no-any-return]
    except (ImportError, AttributeError, ValueError) as exception:
        if mappings_module_name != "no mapping":
            logger.error(f"PATH_MAPPING was not imported: {exception}")
        return {}


def get_id_property_name(
    mappings_module_name: str, default_id_property_name: str
) -> IGetIdPropertyName:
    return GetIdPropertyName(
        mappings_module_name=mappings_module_name,
        default_id_property_name=default_id_property_name,
    )


class GetIdPropertyName:
    """
    Callable class to return the name of the property that uniquely identifies
    the resource from user-implemented mappings file.
    """

    def __init__(
        self, mappings_module_name: str, default_id_property_name: str
    ) -> None:
        self.default_id_property_name = default_id_property_name
        try:
            mappings_module = import_module(mappings_module_name)
            self.id_mapping: dict[
                str,
                str | tuple[str, Callable[[str], str]],
            ] = mappings_module.ID_MAPPING
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"ID_MAPPING was not imported: {exception}")
            self.id_mapping = {}

    def __call__(self, path: str) -> tuple[str, Callable[[str], str]]:
        try:
            value_or_mapping = self.id_mapping[path]
            if isinstance(value_or_mapping, str):
                return (value_or_mapping, dummy_transformer)
            return value_or_mapping
        except KeyError:
            return (self.default_id_property_name, dummy_transformer)
