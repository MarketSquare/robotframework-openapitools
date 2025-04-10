"""
Module holding the functions related to data generation
for the requests made as part of keyword exection.
"""

from .body_data_generation import get_request_body_data
from .data_generation_core import get_request_data

__all__ = [
    "get_request_body_data",
    "get_request_data",
]
