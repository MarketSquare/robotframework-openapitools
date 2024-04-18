from typing import Callable, Dict, Tuple

from openapi_core import Spec
from openapi_core.contrib.requests import (
    RequestsOpenAPIRequest,
    RequestsOpenAPIResponse,
)
from prance import ResolvingParser

PARSER_CACHE: Dict[
    str,
    Tuple[
        ResolvingParser,
        Spec,
        Callable[[RequestsOpenAPIRequest, RequestsOpenAPIResponse], None],
    ],
] = {}
