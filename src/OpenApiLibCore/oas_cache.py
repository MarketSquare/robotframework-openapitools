"""Module holding the (global) parser cache."""

from dataclasses import dataclass

from openapi_core import Spec
from prance import ResolvingParser

from OpenApiLibCore.protocols import ResponseValidatorType


@dataclass
class CachedParser:
    parser: ResolvingParser
    validation_spec: Spec
    response_validator: ResponseValidatorType


PARSER_CACHE: dict[str, CachedParser] = {}
