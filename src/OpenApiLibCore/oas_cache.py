from typing import Dict, Tuple

from openapi_core import Spec
from prance import ResolvingParser

PARSER_CACHE: Dict[str, Tuple[ResolvingParser, Spec]] = {}
