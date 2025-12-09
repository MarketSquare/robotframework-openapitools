"""Module holding the (global) parser cache."""

from dataclasses import dataclass

from prance import ResolvingParser

from OpenApiLibCore.protocols import IResponseValidator


@dataclass
class CachedParser:
    parser: ResolvingParser
    response_validator: IResponseValidator


PARSER_CACHE: dict[str, CachedParser] = {}
