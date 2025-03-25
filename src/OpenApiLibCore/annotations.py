"""Module holding reusable compound annotations."""

JSON = dict[str, "JSON"] | list["JSON"] | str | bytes | int | float | bool | None
