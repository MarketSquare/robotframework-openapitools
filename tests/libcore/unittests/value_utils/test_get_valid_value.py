# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestGetValidValue(unittest.TestCase):
    def test_const(self) -> None:
        magic_number = 42
        # If "const" is in the schema, anything else is ignored
        schema = {"const": magic_number, "type": "string", "minimum": magic_number + 1}
        value = value_utils.get_valid_value(schema)
        self.assertEqual(value, magic_number)

    def test_enum(self) -> None:
        # Enum values are returned directly from the list, anything else is ignored
        schema = {"enum": ["foo", "bar"], "type": "number", "minimum": -1}
        value = value_utils.get_valid_value(schema)
        self.assertIn(value, ["foo", "bar"])

    def test_bool(self) -> None:
        schema = {"type": "boolean"}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, bool)

    def test_integer(self) -> None:
        schema = {"type": "integer"}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, int)

    def test_number(self) -> None:
        schema = {"type": "number"}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, float)

    def test_string(self) -> None:
        schema = {"type": "string"}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, str)

    def test_bool_array(self) -> None:
        schema = {"type": "array", "items": {"type": "boolean"}}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], bool)

    def test_int_array(self) -> None:
        schema = {"type": "array", "items": {"type": "integer"}}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], int)

    def test_number_array(self) -> None:
        schema = {"type": "array", "items": {"type": "number"}}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], float)

    def test_string_array(self) -> None:
        schema = {"type": "array", "items": {"type": "string"}}
        value = value_utils.get_valid_value(schema)
        self.assertIsInstance(value, list)
        self.assertIsInstance(value[0], str)

    def test_raises(self) -> None:
        schema = {"type": "object"}
        self.assertRaises(NotImplementedError, value_utils.get_valid_value, schema)


if __name__ == "__main__":
    unittest.main()
