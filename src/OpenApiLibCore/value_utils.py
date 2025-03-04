# mypy: disable-error-code=no-any-return
"""Utility module with functions to handle OpenAPI value types and restrictions."""

import base64
import datetime
from copy import deepcopy
from random import choice, randint, uniform
from typing import Any, Callable

import faker
import rstr
from robot.api import logger

JSON = dict[str, "JSON"] | list["JSON"] | str | int | float | bool | None

IGNORE = object()


class LocalizedFaker:
    """Class to support setting a locale post-init."""

    # pylint: disable=missing-function-docstring
    def __init__(self) -> None:
        self.fake = faker.Faker()

    def set_locale(self, locale: str | list[str]) -> None:
        """Update the fake attribute with a Faker instance with the provided locale."""
        self.fake = faker.Faker(locale)

    @property
    def date(self) -> Callable[[], str]:
        return self.fake.date

    @property
    def date_time(self) -> Callable[[], datetime.datetime]:
        return self.fake.date_time

    @property
    def password(self) -> Callable[[], str]:
        return self.fake.password

    @property
    def binary(self) -> Callable[[], bytes]:
        return self.fake.binary

    @property
    def email(self) -> Callable[[], str]:
        return self.fake.safe_email

    @property
    def uuid(self) -> Callable[[], str]:
        return self.fake.uuid4

    @property
    def uri(self) -> Callable[[], str]:
        return self.fake.uri

    @property
    def url(self) -> Callable[[], str]:
        return self.fake.url

    @property
    def hostname(self) -> Callable[[], str]:
        return self.fake.hostname

    @property
    def ipv4(self) -> Callable[[], str]:
        return self.fake.ipv4

    @property
    def ipv6(self) -> Callable[[], str]:
        return self.fake.ipv6

    @property
    def name(self) -> Callable[[], str]:
        return self.fake.name

    @property
    def text(self) -> Callable[[], str]:
        return self.fake.text

    @property
    def description(self) -> Callable[[], str]:
        return self.fake.text


FAKE = LocalizedFaker()


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


def python_type_by_json_type_name(type_name: str) -> Any:
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


def get_valid_value(value_schema: dict[str, Any]) -> Any:
    """Return a random value that is valid under the provided value_schema."""
    value_schema = deepcopy(value_schema)

    if value_schema.get("types"):
        value_schema = choice(value_schema["types"])

    if (from_const := value_schema.get("const")) is not None:
        return from_const
    if from_enum := value_schema.get("enum"):
        return choice(from_enum)

    value_type = value_schema["type"]

    if value_type == "null":
        return None
    if value_type == "boolean":
        return FAKE.fake.boolean()
    if value_type == "integer":
        return get_random_int(value_schema=value_schema)
    if value_type == "number":
        return get_random_float(value_schema=value_schema)
    if value_type == "string":
        return get_random_string(value_schema=value_schema)
    if value_type == "array":
        return get_random_array(value_schema=value_schema)
    raise NotImplementedError(f"Type '{value_type}' is currently not supported")


def get_invalid_value(
    value_schema: dict[str, Any],
    current_value: Any,
    values_from_constraint: list[Any] | None = None,  # FIXME: default empty list?
) -> Any:
    """Return a random value that violates the provided value_schema."""
    value_schema = deepcopy(value_schema)

    if value_schemas := value_schema.get("types"):
        if len(value_schemas) > 1:
            value_schemas = [
                schema for schema in value_schemas if schema["type"] != "null"
            ]
        value_schema = choice(value_schemas)

    invalid_value: Any = None
    value_type = value_schema["type"]

    if not isinstance(current_value, python_type_by_json_type_name(value_type)):
        current_value = get_valid_value(value_schema=value_schema)

    if (
        values_from_constraint
        and (
            invalid_value := get_invalid_value_from_constraint(
                values_from_constraint=values_from_constraint,
                value_type=value_type,
            )
        )
        is not None
    ):
        return invalid_value
    # If an enum is possible, combine the values from the enum to invalidate the value
    if enum_values := value_schema.get("enum"):
        if (
            invalid_value := get_invalid_value_from_enum(
                values=enum_values, value_type=value_type
            )
        ) is not None:
            return invalid_value
    # Violate min / max values or length if possible
    if (
        invalid_value := get_value_out_of_bounds(
            value_schema=value_schema, current_value=current_value
        )
    ) is not None:
        return invalid_value
    # No value constraints or min / max ranges to violate, so change the data type
    if value_type == "string":
        # Since int / float / bool can always be cast to sting, change
        # the string to a nested object.
        # An array gets exploded in query strings, "null" is then often invalid
        return [{"invalid": [None, False]}, "null", None, True]
    logger.debug(f"property type changed from {value_type} to random string")
    return FAKE.uuid()


def get_random_int(value_schema: dict[str, Any]) -> int:
    """Generate a random int within the min/max range of the schema, if specified."""
    # Use int32 integers if "format" does not specify int64
    property_format = value_schema.get("format", "int32")
    if property_format == "int64":
        min_int = -9223372036854775808
        max_int = 9223372036854775807
    else:
        min_int = -2147483648
        max_int = 2147483647
    # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
    # OAS 3.1: exclusiveMinimum/Maximum is an integer
    minimum = value_schema.get("minimum", min_int)
    maximum = value_schema.get("maximum", max_int)
    if (exclusive_minimum := value_schema.get("exclusiveMinimum")) is not None:
        if isinstance(exclusive_minimum, bool):
            if exclusive_minimum:
                minimum += 1
        else:
            minimum = exclusive_minimum + 1
    if (exclusive_maximum := value_schema.get("exclusiveMaximum")) is not None:
        if isinstance(exclusive_maximum, bool):
            if exclusive_maximum:
                maximum -= 1
        else:
            maximum = exclusive_maximum - 1
    return randint(minimum, maximum)


def get_random_float(value_schema: dict[str, Any]) -> float:
    """Generate a random float within the min/max range of the schema, if specified."""
    # Python floats are already double precision, so no check for "format"
    minimum = value_schema.get("minimum")
    maximum = value_schema.get("maximum")
    if minimum is None:
        if maximum is None:
            minimum = -1.0
            maximum = 1.0
        else:
            minimum = maximum - 1.0
    else:
        if maximum is None:
            maximum = minimum + 1.0
        if maximum < minimum:
            raise ValueError(f"maximum of {maximum} is less than minimum of {minimum}")

    # For simplicity's sake, exclude both boundaries if one boundary is exclusive
    exclude_boundaries = False

    exclusive_minimum = value_schema.get("exclusiveMinimum", False)
    exclusive_maximum = value_schema.get("exclusiveMaximum", False)
    # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
    # OAS 3.1: exclusiveMinimum/Maximum is an integer or number
    if not isinstance(exclusive_minimum, bool):
        exclude_boundaries = True
        minimum = exclusive_minimum
    else:
        exclude_boundaries = exclusive_minimum
    if not isinstance(exclusive_maximum, bool):
        exclude_boundaries = True
        maximum = exclusive_maximum
    else:
        exclude_boundaries = exclusive_minimum or exclusive_maximum

    if exclude_boundaries and minimum == maximum:
        raise ValueError(
            f"maximum of {maximum} is equal to minimum of {minimum} and "
            f"exclusiveMinimum or exclusiveMaximum is specified"
        )

    while exclude_boundaries:
        result = uniform(minimum, maximum)
        if minimum < result < maximum:  # pragma: no cover
            return result
    return uniform(minimum, maximum)


def get_random_string(value_schema: dict[str, Any]) -> bytes | str:
    """Generate a random string within the min/max length in the schema, if specified."""
    # if a pattern is provided, format and min/max length can be ignored
    if pattern := value_schema.get("pattern"):
        return rstr.xeger(pattern)
    minimum = value_schema.get("minLength", 0)
    maximum = value_schema.get("maxLength", 36)
    maximum = max(minimum, maximum)
    format_ = value_schema.get("format", "uuid")
    # byte is a special case due to the required encoding
    if format_ == "byte":
        data = FAKE.uuid()
        return base64.b64encode(data.encode("utf-8"))
    value = fake_string(string_format=format_)
    while len(value) < minimum:
        # use fake.name() to ensure the returned string uses the provided locale
        value = value + FAKE.name()
    if len(value) > maximum:
        value = value[:maximum]
    return value


def fake_string(string_format: str) -> str:
    """
    Generate a random string based on the provided format if the format is supported.
    """
    # format names may contain -, which is invalid in Python naming
    string_format = string_format.replace("-", "_")
    fake_generator = getattr(FAKE, string_format, FAKE.uuid)
    value: str = fake_generator()
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


def get_random_array(value_schema: dict[str, Any]) -> list[Any]:
    """Generate a list with random elements as specified by the schema."""
    minimum = value_schema.get("minItems", 0)
    maximum = value_schema.get("maxItems", 1)
    maximum = max(minimum, maximum)
    items_schema = value_schema["items"]
    value = []
    for _ in range(maximum):
        item_value = get_valid_value(items_schema)
        value.append(item_value)
    return value


def get_invalid_value_from_constraint(
    values_from_constraint: list[Any], value_type: str
) -> Any:
    """
    Return a value of the same type as the values in the values_from_constraints that
    is not in the values_from_constraints, if possible. Otherwise returns None.
    """
    # if IGNORE is in the values_from_constraints, the parameter needs to be
    # ignored for an OK response so leaving the value at it's original value
    # should result in the specified error response
    if IGNORE in values_from_constraint:
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
        valid_object = values_from_constraint.pop()
        invalid_object = {}
        for key, value in valid_object.items():
            python_type_of_value = type(value)
            json_type_of_value = json_type_name_of_python_type(python_type_of_value)
            invalid_object[key] = get_invalid_value_from_constraint(
                values_from_constraint=[value],
                value_type=json_type_of_value,
            )
        return invalid_object

    # for arrays, update each value in the array to a value of the same type
    if value_type == "array":
        valid_array = values_from_constraint.pop()
        invalid_array = []
        for value in valid_array:
            python_type_of_value = type(value)
            json_type_of_value = json_type_name_of_python_type(python_type_of_value)
            invalid_value = get_invalid_value_from_constraint(
                values_from_constraint=[value],
                value_type=json_type_of_value,
            )
            invalid_array.append(invalid_value)
        return invalid_array

    invalid_values = 2 * values_from_constraint
    invalid_value = invalid_values.pop()
    if value_type in ["integer", "number"]:
        for value in invalid_values:
            invalid_value = abs(invalid_value) + abs(value)
        if not invalid_value:
            invalid_value += 1
        return invalid_value
    for value in invalid_values:
        invalid_value = invalid_value + value
    # None for empty string
    return invalid_value if invalid_value else None


def get_invalid_value_from_enum(values: list[Any], value_type: str) -> Any:
    """Return a value not in the enum by combining the enum values."""
    if value_type == "string":
        invalid_value: Any = ""
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


def get_value_out_of_bounds(value_schema: dict[str, Any], current_value: Any) -> Any:
    """
    Return a value just outside the value or length range if specified in the
    provided schema, otherwise None is returned.
    """
    value_type = value_schema["type"]

    if value_type in ["integer", "number"]:
        if (minimum := value_schema.get("minimum")) is not None:
            if value_schema.get("exclusiveMinimum") is True:
                return minimum
            return minimum - 1
        if (maximum := value_schema.get("maximum")) is not None:
            if value_schema.get("exclusiveMaximum") is True:
                return maximum
            return maximum + 1
        # In OAS 3.1 exclusveMinimum/Maximum are no longer boolean but instead integer
        # or number and minimum/maximum should not be used with exclusiveMinimum/Maximum
        if (exclusive_minimum := value_schema.get("exclusiveMinimum")) is not None:
            return exclusive_minimum
        if (exclusive_maximum := value_schema.get("exclusiveMaximum")) is not None:
            return exclusive_maximum
    if value_type == "array":
        if minimum := value_schema.get("minItems", 0) > 0:
            return current_value[0 : minimum - 1]
        if (maximum := value_schema.get("maxItems")) is not None:
            invalid_value = current_value if current_value else ["x"]
            while len(invalid_value) <= maximum:
                invalid_value.append(choice(invalid_value))
            return invalid_value
    if value_type == "string":
        # if there is a minimum length, send 1 character less
        if minimum := value_schema.get("minLength", 0):
            return current_value[0 : minimum - 1]
        # if there is a maximum length, send 1 character more
        if maximum := value_schema.get("maxLength"):
            invalid_value = current_value if current_value else "x"
            # add random characters from the current value to prevent adding new characters
            while len(invalid_value) <= maximum:
                invalid_value += choice(invalid_value)
            return invalid_value
    return None
