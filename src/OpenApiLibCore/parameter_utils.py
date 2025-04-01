"""
Module holding the functions to support mapping between Python-safe parameter
names and the original names in the parsed OpenApi Specification document.
"""

from typing import Generator

from OpenApiLibCore.annotations import JSON

PARAMETER_REGISTRY: dict[str, str] = {"body": "body"}


def get_oas_name_from_safe_name(safe_name: str) -> str:
    oas_name = PARAMETER_REGISTRY.get(safe_name)
    if not oas_name:
        raise ValueError(f"No entry for '{safe_name}' registered {PARAMETER_REGISTRY}.")
    return oas_name


def get_safe_name_for_oas_name(oas_name: str) -> str:
    if is_python_safe(oas_name):
        PARAMETER_REGISTRY[oas_name] = oas_name
        return oas_name

    safe_name = convert_string_to_python_identifier(oas_name)

    if safe_name not in PARAMETER_REGISTRY:
        PARAMETER_REGISTRY[safe_name] = oas_name
        return safe_name

    registered_oas_name = PARAMETER_REGISTRY[safe_name]
    if registered_oas_name == oas_name:
        return safe_name
    # We're dealing with multiple oas_names that convert to the same safe_name.
    # To resolve this, a more verbose safe_name is generated. This is less user-friendly
    # but necessary to ensure an one-to-one mapping.
    verbose_safe_name = convert_string_to_python_identifier(oas_name, verbose=True)
    if verbose_safe_name not in PARAMETER_REGISTRY:
        PARAMETER_REGISTRY[verbose_safe_name] = oas_name
    return verbose_safe_name


def is_python_safe(name: str) -> bool:
    return name.isidentifier()


def convert_string_to_python_identifier(string: str, verbose: bool = False) -> str:
    def _convert_string_to_python_identifier() -> Generator[str, None, None]:
        string_iterator = iter(string)

        # The first character must be A-z or _
        first_character = next(string_iterator, "_")
        if first_character.isalpha() or first_character == "_":
            yield first_character
        elif first_character.isnumeric():
            yield "_" + first_character
        elif not verbose:
            yield "_"
        else:
            ascii_code = ord(first_character)
            yield f"_{ascii_code}_"
        # Further characters must be A-z, 0-9 or _
        for character in string_iterator:
            if character.isalnum() or character == "_":
                yield character
            elif not verbose:
                yield "_"
            else:
                ascii_code = ord(character)
                yield f"_{ascii_code}_"

    if is_python_safe(string):
        return string

    converted_string = "".join(_convert_string_to_python_identifier())
    if not is_python_safe(converted_string):
        raise ValueError(f"Failed to convert '{string}' to Python identifier.")
    return converted_string


def register_path_parameters(paths_data: dict[str, dict[str, JSON]]) -> None:
    for operations_data in paths_data.values():
        for method_data in operations_data.values():
            parameters_data: list[dict[str, str]] = method_data.get("parameters", [])
            path_parameter_names = [
                p["name"] for p in parameters_data if p["in"] == "path"
            ]
            for name in path_parameter_names:
                _ = get_safe_name_for_oas_name(name)
