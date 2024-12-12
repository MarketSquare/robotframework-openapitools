"""Module for helper methods and classes used by the openapi_executors module."""

from dataclasses import dataclass
from importlib import import_module
from logging import getLogger
from typing import Callable, Type

from OpenApiLibCore.dto_base import Dto

logger = getLogger(__name__)


@dataclass
class _DefaultIdPropertyName:
    id_property_name: str = "id"


DEFAULT_ID_PROPERTY_NAME = _DefaultIdPropertyName()


@dataclass
class DefaultDto(Dto):
    """A default Dto that can be instantiated."""


# pylint: disable=invalid-name, too-few-public-methods
class get_dto_class:
    """Callable class to return Dtos from user-implemented mappings file."""

    def __init__(self, mappings_module_name: str) -> None:
        try:
            mappings_module = import_module(mappings_module_name)
            self.dto_mapping: dict[tuple[str, str], Type[Dto]] = (
                mappings_module.DTO_MAPPING
            )
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"DTO_MAPPING was not imported: {exception}")
            self.dto_mapping = {}

    def __call__(self, endpoint: str, method: str) -> Type[Dto]:
        try:
            return self.dto_mapping[(endpoint, method.lower())]
        except KeyError:
            logger.debug(f"No Dto mapping for {endpoint} {method}.")
            return DefaultDto


# pylint: disable=invalid-name, too-few-public-methods
class get_id_property_name:
    """
    Callable class to return the name of the property that uniquely identifies
    the resource from user-implemented mappings file.
    """

    def __init__(self, mappings_module_name: str) -> None:
        try:
            mappings_module = import_module(mappings_module_name)
            self.id_mapping: dict[
                str,
                str
                | tuple[str, tuple[Callable[[str | int | float], str | int | float]]],
            ] = mappings_module.ID_MAPPING
        except (ImportError, AttributeError, ValueError) as exception:
            if mappings_module_name != "no mapping":
                logger.error(f"ID_MAPPING was not imported: {exception}")
            self.id_mapping = {}

    def __call__(
        self, endpoint: str
    ) -> str | tuple[str, tuple[Callable[[str | int | float], str | int | float]]]:
        try:
            return self.id_mapping[endpoint]
        except KeyError:
            default_id_name = DEFAULT_ID_PROPERTY_NAME.id_property_name
            logger.debug(
                f"No id mapping for {endpoint} ('{default_id_name}' will be used)"
            )
            return default_id_name
