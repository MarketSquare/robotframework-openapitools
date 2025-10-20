"""Module holding the (global) parser cache."""

from dataclasses import dataclass

from openapi_core import Spec
from prance import ResolvingParser

from OpenApiLibCore.protocols import IResponseValidator


@dataclass
class CachedParser:
    parser: ResolvingParser
    validation_spec: Spec
    response_validator: IResponseValidator


PARSER_CACHE: dict[str, CachedParser] = {}
