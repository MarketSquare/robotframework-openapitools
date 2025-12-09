"""Module holding reusable compound annotations."""

from typing import Union

from typing_extensions import TypeAliasType

JSON = TypeAliasType(
    "JSON",
    "Union[dict[str, JSON], list[JSON], str, int, float, bool, None]",
)
