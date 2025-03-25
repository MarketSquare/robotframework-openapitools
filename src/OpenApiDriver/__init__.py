# pylint: disable=invalid-name
"""
The OpenApiDriver package is intended to be used as a Robot Framework library.
The following classes and constants are exposed to be used by the library user:
- OpenApiDriver: The class to be used as a Library in the *** Settings *** section
- IdDependency, IdReference, PathPropertiesConstraint, PropertyValueConstraint,
    UniquePropertyValueConstraint: Classes to be subclassed by the library user
    when implementing a custom mapping module (advanced use).
- Dto, Relation: Base classes that can be used for type annotations.
- IGNORE: A special constant that can be used as a value in the PropertyValueConstraint.
"""

from importlib.metadata import version

from OpenApiDriver.openapidriver import OpenApiDriver
from OpenApiLibCore.dto_base import (
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    ResourceRelation,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.validation import ValidationLevel
from OpenApiLibCore.value_utils import IGNORE

try:
    __version__ = version("robotframework-openapidriver")
except Exception:  # pragma: no cover pylint: disable=broad-exception-caught
    pass

__all__ = [
    "IGNORE",
    "Dto",
    "IdDependency",
    "IdReference",
    "OpenApiDriver",
    "PathPropertiesConstraint",
    "PropertyValueConstraint",
    "ResourceRelation",
    "UniquePropertyValueConstraint",
    "ValidationLevel",
]
