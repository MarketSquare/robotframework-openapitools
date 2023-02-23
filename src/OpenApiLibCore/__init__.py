"""
The OpenApiLibCore package is intended to be used as a dependency for other
Robot Framework libraries that facilitate the testing of OpenAPI / Swagger APIs.
The following classes and constants are exposed to be used by the library user:
- OpenApiLibCore: The class to be imported in the Robot Framework library.
- IdDependency, IdReference, PathPropertiesConstraint, PropertyValueConstraint,
    UniquePropertyValueConstraint: Classes to be subclassed by the library user
    when implementing a custom mapping module (advanced use).
- Dto, Relation: Base classes that can be used for type annotations.
- IGNORE: A special constant that can be used as a value in the PropertyValueConstraint.
"""
from importlib.metadata import version

from OpenApiLibCore.dto_base import (
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    Relation,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.dto_utils import DefaultDto
from OpenApiLibCore.openapi_libcore import (
    OpenApiLibCore,
    RequestData,
    RequestValues,
    resolve_schema,
)
from OpenApiLibCore.value_utils import IGNORE


try:
    __version__ = version("robotframework-openapitools")
except Exception:  # pragma: no cover
    pass
