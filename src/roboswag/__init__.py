from importlib.metadata import version

from roboswag.cli import cli
from roboswag.core import APIModel


try:
    __version__ = version("robotframework-openapitools")
except Exception:  # pragma: no cover
    pass
