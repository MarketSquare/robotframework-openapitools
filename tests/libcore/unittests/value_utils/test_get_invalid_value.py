# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestGetInvalidValue(unittest.TestCase):
    def test_invalid_from_constraint(self) -> None:
        current_value = "irrelevant"
        values_from_constraints = [42]

        value_schema = {"type": "integer"}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
            values_from_constraint=values_from_constraints,
        )
        self.assertNotIn(value, values_from_constraints)
        self.assertIsInstance(value, int)

        value_schema = {"type": "null"}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
            values_from_constraint=values_from_constraints,
        )
        self.assertIsInstance(value, str)

    def test_invalid_from_enum(self) -> None:
        enum_values = [0.1, 0.3]
        current_value = "irrelevant"

        value_schema = {"type": "number", "enum": enum_values}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertNotIn(value, enum_values)
        self.assertIsInstance(value, float)

        value_schema = {"type": "null", "enum": enum_values}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertIsInstance(value, str)

    def test_invalid_from_bounds(self) -> None:
        min_length = 7
        current_value = "long enough"
        value_schema = {"type": "string", "minLength": min_length}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(len(value), min_length)
        self.assertIsInstance(value, str)

        value_schema = {"type": "string", "minLength": min_length}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertIsInstance(value, str)

    def test_invalid_string(self) -> None:
        # Type "null" is ignore in invalidation since it signals 'nullable' and the
        # goal is to generate an invalid value.
        value_schema = {"types": [{"type": "string"}, {"type": "null"}]}
        current_value = "irrelevant"
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertNotIsInstance(value, str)

    def test_only_null_in_types(self) -> None:
        value_schema = {"types": [{"type": "null"}]}
        value = value_utils.get_invalid_value(
            value_schema=value_schema,
            current_value=None,
        )
        self.assertIsInstance(value, str)


if __name__ == "__main__":
    unittest.main()
