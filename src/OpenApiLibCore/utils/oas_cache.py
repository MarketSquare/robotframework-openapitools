"""Module holding the (global) spec cache."""

from dataclasses import dataclass
from typing import Mapping

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.protocols import IResponseValidator


@dataclass
class CachedSpec:
    specification: Mapping[str, JSON]
    response_validator: IResponseValidator


SPEC_CACHE: dict[str, CachedSpec] = {}
