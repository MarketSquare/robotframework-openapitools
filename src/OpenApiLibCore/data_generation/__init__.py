"""
Module holding the functions related to data generation
for the requests made as part of keyword exection.
"""

from .body_data_generation import get_json_data_for_dto_class
from .data_generation_core import get_request_data

__all__ = [
    "get_json_data_for_dto_class",
    "get_request_data",
]
