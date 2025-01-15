from typing import Callable

from openapi_core import Spec
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from prance import ResolvingParser

PARSER_CACHE: dict[
    str,
    tuple[
        ResolvingParser,
        Spec,
        Callable[[RequestsOpenAPIRequest, RequestsOpenAPIResponse], None],
    ],
] = {}
