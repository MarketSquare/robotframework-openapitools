# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestValueOutOfBounds(unittest.TestCase):
    def test_minimum_integer(self) -> None:
        minimum = -42
        value_schema = {"type": "integer", "minimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(value, minimum)
        self.assertIsInstance(value, int)

        minimum = 3
        value_schema = {"type": "integer", "minimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(value, minimum)
        self.assertIsInstance(value, int)

    def test_minimum_number(self) -> None:
        minimum = -0.6
        value_schema = {"type": "integer", "minimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(value, minimum)
        self.assertIsInstance(value, float)

        minimum = 3.14159
        value_schema = {"type": "integer", "minimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(value, minimum)
        self.assertIsInstance(value, float)

    def test_maximum_integer(self) -> None:
        maximum = -42
        value_schema = {"type": "integer", "maximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(value, maximum)
        self.assertIsInstance(value, int)

        maximum = 3
        value_schema = {"type": "integer", "maximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(value, maximum)
        self.assertIsInstance(value, int)

    def test_maximum_number(self) -> None:
        maximum = -0.6
        value_schema = {"type": "integer", "maximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(value, maximum)
        self.assertIsInstance(value, float)

        maximum = 3.14159
        value_schema = {"type": "integer", "maximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(value, maximum)
        self.assertIsInstance(value, float)

    def test_exclusive_minimum_integer_oas_3_0(self) -> None:
        minimum = -42
        value_schema = {"type": "integer", "minimum": minimum, "exclusiveMinimum": True}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, minimum)
        self.assertIsInstance(value, int)

    def test_exclusive_minimum_integer_oas_3_1(self) -> None:
        minimum = -42
        value_schema = {"type": "integer", "exclusiveMinimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, minimum)
        self.assertIsInstance(value, int)

    def test_exclusive_maximum_integer_oas_3_0(self) -> None:
        maximum = -42
        value_schema = {"type": "integer", "maximum": maximum, "exclusiveMaximum": True}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, maximum)
        self.assertIsInstance(value, int)

    def test_exclusive_maximum_integer_oas_3_1(self) -> None:
        maximum = -42
        value_schema = {"type": "integer", "exclusiveMaximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, maximum)
        self.assertIsInstance(value, int)

    def test_exclusive_minimum_number_oas_3_0(self) -> None:
        minimum = 3.14159
        value_schema = {"type": "integer", "minimum": minimum, "exclusiveMinimum": True}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, minimum)
        self.assertIsInstance(value, float)

    def test_exclusive_minimum_number_oas_3_1(self) -> None:
        minimum = 3.14159
        value_schema = {"type": "integer", "exclusiveMinimum": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, minimum)
        self.assertIsInstance(value, float)

    def test_exclusive_maximum_number_oas_3_0(self) -> None:
        maximum = -273.15
        value_schema = {"type": "integer", "maximum": maximum, "exclusiveMaximum": True}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, maximum)
        self.assertIsInstance(value, float)

    def test_exclusive_maximum_number_oas_3_1(self) -> None:
        maximum = -273.15
        value_schema = {"type": "integer", "exclusiveMaximum": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, maximum)
        self.assertIsInstance(value, float)

    def test_minimum_length(self) -> None:
        minimum = 1
        value_schema = {"type": "string", "minLength": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(len(value), minimum)
        self.assertIsInstance(value, str)

    def test_maximum_length(self) -> None:
        maximum = 7
        value_schema = {"type": "string", "maxLength": maximum}
        current_value = "valid"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(len(value), maximum)
        self.assertIsInstance(value, str)

        maximum = 7
        value_schema = {"type": "string", "maxLength": maximum}
        current_value = ""
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(len(value), maximum)
        self.assertIsInstance(value, str)

    def test_minimum_length_zero(self) -> None:
        minimum = 0
        value_schema = {"type": "string", "minLength": minimum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

    def test_maximum_length_zero(self) -> None:
        maximum = 0
        value_schema = {"type": "string", "maxLength": maximum}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

    def test_min_items(self) -> None:
        minimum = 1
        value_schema = {
            "type": "array",
            "minItems": minimum,
            "items": {"type": "string"},
        }
        current_value = ["irrelevant"]
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertLess(len(value), minimum)
        self.assertIsInstance(value, list)

    def test_max_items(self) -> None:
        maximum = 3
        value_schema = {
            "type": "array",
            "maxItems": maximum,
            "items": {"type": "boolean"},
        }
        current_value = [True, False]
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertGreater(len(value), maximum)
        self.assertIsInstance(value, list)

    def test_min_items_zero(self) -> None:
        minimum = 0
        value_schema = {
            "type": "array",
            "minItems": minimum,
            "items": {"type": "number"},
        }
        current_value = [42]
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

    def test_unbound(self) -> None:
        value_schema = {"type": "integer"}
        current_value = "irrelvant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

        value_schema = {"type": "number"}
        current_value = "irrelvant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

        value_schema = {"type": "string"}
        current_value = "irrelvant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)

    def test_unsupported(self) -> None:
        value_schema = {"type": "boolean"}
        current_value = "irrelevant"
        value = value_utils.get_value_out_of_bounds(
            value_schema=value_schema,
            current_value=current_value,
        )
        self.assertEqual(value, None)


if __name__ == "__main__":
    unittest.main()
