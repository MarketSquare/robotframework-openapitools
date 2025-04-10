# mypy: disable-error-code=no-any-return
"""Utility module with functions to handle OpenAPI value types and restrictions."""

from copy import deepcopy
from random import choice
from typing import Any, Iterable, cast, overload

from robot.api import logger

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.localized_faker import FAKE
from OpenApiLibCore.models import ResolvedSchemaObjectTypes


class Ignore:
    """Helper class to flag properties to be ignored in data generation."""

    def __str__(self) -> str:
        return "IGNORE"


class UnSet:
    """Helper class to flag arguments that have not been set in a keyword call."""

    def __str__(self) -> str:
        return "UNSET"


IGNORE = Ignore()

UNSET = UnSet()


def json_type_name_of_python_type(python_type: Any) -> str:
    """Return the JSON type name for supported Python types."""
    if python_type == str:
        return "string"
    if python_type == bool:
        return "boolean"
    if python_type == int:
        return "integer"
    if python_type == float:
        return "number"
    if python_type == list:
        return "array"
    if python_type == dict:
        return "object"
    if python_type == type(None):
        return "null"
    raise ValueError(f"No json type mapping for Python type {python_type} available.")


def python_type_by_json_type_name(type_name: str) -> type:
    """Return the Python type based on the JSON type name."""
    if type_name == "string":
        return str
    if type_name == "boolean":
        return bool
    if type_name == "integer":
        return int
    if type_name == "number":
        return float
    if type_name == "array":
        return list
    if type_name == "object":
        return dict
    if type_name == "null":
        return type(None)
    raise ValueError(f"No Python type mapping for JSON type '{type_name}' available.")


def get_invalid_value(
    value_schema: ResolvedSchemaObjectTypes,
    current_value: JSON,
    values_from_constraint: Iterable[JSON] = tuple(),
) -> JSON | Ignore:
    """Return a random value that violates the provided value_schema."""
    invalid_values: list[JSON | Ignore] = []
    value_type = value_schema.type

    if not isinstance(current_value, python_type_by_json_type_name(value_type)):
        current_value = value_schema.get_valid_value()

    if (
        values_from_constraint
        and (
            invalid_value := get_invalid_value_from_constraint(
                values_from_constraint=list(values_from_constraint),
                value_type=value_type,
            )
        )
        is not None
    ):
        invalid_values.append(invalid_value)

    # If an enum is possible, combine the values from the enum to invalidate the value
    if value_schema.has_const_or_enum:
        if (
            invalid_value := get_invalid_value_from_enum(
                values=value_schema.enum, value_type=value_type
            )
        ) is not None:
            invalid_values.append(invalid_value)

    # Violate min / max values or length if possible
    try:
        invalid_values += value_schema.get_values_out_of_bounds(
            current_value=current_value
        )
    except ValueError:
        pass

    # No value constraints or min / max ranges to violate, so change the data type
    if value_type == "string":
        # Since int / float / bool can always be cast to sting, change
        # the string to a nested object.
        # An array gets exploded in query strings, "null" is then often invalid
        invalid_values.append([{"invalid": [None, False]}, "null", None, True])
    else:
        invalid_values.append(FAKE.uuid())

    return choice(invalid_values)


def get_invalid_value_from_constraint(
    values_from_constraint: list[JSON | Ignore], value_type: str
) -> JSON | Ignore:
    """
    Return a value of the same type as the values in the values_from_constraints that
    is not in the values_from_constraints, if possible. Otherwise returns None.
    """
    # if IGNORE is in the values_from_constraints, the parameter needs to be
    # ignored for an OK response so leaving the value at it's original value
    # should result in the specified error response
    if any(map(lambda x: isinstance(x, Ignore), values_from_constraint)):
        return IGNORE
    # if the value is forced True or False, return the opposite to invalidate
    if len(values_from_constraint) == 1 and value_type == "boolean":
        return not values_from_constraint[0]
    # for unsupported types or empty constraints lists return None
    if (
        value_type not in ["string", "integer", "number", "array", "object"]
        or not values_from_constraint
    ):
        return None

    values_from_constraint = deepcopy(values_from_constraint)
    # for objects, keep the keys intact but update the values
    if value_type == "object":
        valid_object = cast(dict[str, JSON], values_from_constraint.pop())
        invalid_object: dict[str, JSON] = {}
        for key, value in valid_object.items():
            python_type_of_value = type(value)
            json_type_of_value = json_type_name_of_python_type(python_type_of_value)
            invalid_value = cast(
                JSON,
                get_invalid_value_from_constraint(
                    values_from_constraint=[value],
                    value_type=json_type_of_value,
                ),
            )
            invalid_object[key] = invalid_value
        return invalid_object

    # for arrays, update each value in the array to a value of the same type
    if value_type == "array":
        valid_array = cast(list[JSON], values_from_constraint.pop())
        invalid_array: list[JSON] = []
        for value in valid_array:
            python_type_of_value = type(value)
            json_type_of_value = json_type_name_of_python_type(python_type_of_value)
            invalid_value = cast(
                JSON,
                get_invalid_value_from_constraint(
                    values_from_constraint=[value],
                    value_type=json_type_of_value,
                ),
            )
            invalid_array.append(invalid_value)
        return invalid_array

    if value_type in ["integer", "number"]:
        int_or_number_list = cast(list[int | float], values_from_constraint)
        return get_invalid_int_or_number(values_from_constraint=int_or_number_list)

    str_or_bytes_list = cast(list[str] | list[bytes], values_from_constraint)
    invalid_value = get_invalid_str_or_bytes(values_from_constraint=str_or_bytes_list)
    # None for empty string
    return invalid_value if invalid_value else None


def get_invalid_int_or_number(values_from_constraint: list[int | float]) -> int | float:
    invalid_values = 2 * values_from_constraint
    invalid_value = invalid_values.pop()
    for value in invalid_values:
        invalid_value = abs(invalid_value) + abs(value)
    if not invalid_value:
        invalid_value += 1
    return invalid_value


@overload
def get_invalid_str_or_bytes(values_from_constraint: list[str]) -> str: ...


@overload
def get_invalid_str_or_bytes(values_from_constraint: list[bytes]) -> bytes: ...


def get_invalid_str_or_bytes(values_from_constraint: list[Any]) -> Any:
    invalid_values = 2 * values_from_constraint
    invalid_value = invalid_values.pop()
    for value in invalid_values:
        invalid_value = invalid_value + value
    return invalid_value


def get_invalid_value_from_enum(values: list[JSON], value_type: str) -> JSON:
    """Return a value not in the enum by combining the enum values."""
    if value_type == "string":
        invalid_value: JSON = ""
    elif value_type in ["integer", "number"]:
        invalid_value = 0
    elif value_type == "array":
        invalid_value = []
    elif value_type == "object":
        # force creation of a new object since we will be modifying it
        invalid_value = {**values[0]}
    else:
        logger.warn(f"Cannot invalidate enum value with type {value_type}")
        return None
    for value in values:
        # repeat each addition to ensure single-item enums are invalidated
        if value_type in ["integer", "number"]:
            invalid_value += abs(value) + abs(value)
        if value_type == "string":
            invalid_value += value + value
        if value_type == "array":
            invalid_value.extend(value)
            invalid_value.extend(value)
        # objects are a special case, since they must be of the same type / class
        # invalid_value.update(value) will end up with the last value in the list,
        # which is a valid value, so another approach is needed
        if value_type == "object":
            for key in invalid_value.keys():
                invalid_value[key] = value.get(key)
                if invalid_value not in values:
                    return invalid_value
    return invalid_value


# def get_value_out_of_bounds(
#     value_schema: ResolvedSchemaObjectTypes, current_value: JSON
# ) -> JSON:
#     """
#     Return a value just outside the value or length range if specified in the
#     provided schema, otherwise None is returned.
#     """
#     value_type = value_schema.type

#     if value_type in ["integer", "number"]:
#         if (minimum := value_schema.get("minimum")) is not None:
#             if value_schema.get("exclusiveMinimum") is True:
#                 return minimum
#             return minimum - 1
#         if (maximum := value_schema.get("maximum")) is not None:
#             if value_schema.get("exclusiveMaximum") is True:
#                 return maximum
#             return maximum + 1
#         # In OAS 3.1 exclusveMinimum/Maximum are no longer boolean but instead integer
#         # or number and minimum/maximum should not be used with exclusiveMinimum/Maximum
#         if (exclusive_minimum := value_schema.get("exclusiveMinimum")) is not None:
#             return exclusive_minimum
#         if (exclusive_maximum := value_schema.get("exclusiveMaximum")) is not None:
#             return exclusive_maximum
#     if value_type == "array":
#         current_list = cast(list[JSON], current_value)
#         if minimum := value_schema.get("minItems", 0) > 0:
#             return current_list[0 : minimum - 1]
#         if (maximum := value_schema.get("maxItems")) is not None:
#             invalid_value = current_list if current_list else ["x"]
#             while len(invalid_value) <= maximum:
#                 invalid_value.append(choice(invalid_value))  # pyright: ignore[reportArgumentType]
#             return invalid_value  # type: ignore[unused-ignore]
#     if value_type == "string":
#         current_string = cast(str, current_value)
#         # if there is a minimum length, send 1 character less
#         if minimum := value_schema.get("minLength", 0):
#             return current_string[0 : minimum - 1]
#         # if there is a maximum length, send 1 character more
#         if maximum := value_schema.get("maxLength"):
#             invalid_string_value = current_string if current_string else "x"
#             # add random characters from the current value to prevent adding new characters
#             while len(invalid_string_value) <= maximum:
#                 invalid_string_value += choice(invalid_string_value)
#             return invalid_string_value
#     return None
