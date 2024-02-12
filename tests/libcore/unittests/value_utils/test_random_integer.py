# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestRandomInteger(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = {"maximum": -2147483648}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -2147483648)

        schema = {"minimum": 2147483647}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 2147483647)

    def test_exclusive_min_max_oas_3_0(self) -> None:
        schema = {"maximum": -2147483648, "exclusiveMaximum": False}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -2147483648)

        schema = {"minimum": 2147483647, "exclusiveMinimum": False}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 2147483647)

        schema = {"maximum": -2147483647, "exclusiveMaximum": True}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -2147483648)

        schema = {"minimum": 2147483646, "exclusiveMinimum": True}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 2147483647)

    def test_exclusive_min_max_oas_3_1(self) -> None:
        schema = {"exclusiveMaximum": -2147483647}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -2147483648)

        schema = {"exclusiveMinimum": 2147483646}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 2147483647)

    def test_min_max(self) -> None:
        schema = {"minimum": 42, "maximum": 42}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 42)

        schema = {"minimum": -42, "maximum": -42}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -42)

        schema = {
            "minimum": 41,
            "maximum": 43,
            "exclusiveMinimum": True,
            "exclusiveMaximum": True,
        }
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 42)

        schema = {
            "minimum": -43,
            "maximum": -41,
            "exclusiveMinimum": True,
            "exclusiveMaximum": True,
        }
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -42)

    def test_int64(self) -> None:
        schema = {"maximum": -9223372036854775808, "format": "int64"}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, -9223372036854775808)

        schema = {"minimum": 9223372036854775807, "format": "int64"}
        value = value_utils.get_random_int(schema)
        self.assertEqual(value, 9223372036854775807)


if __name__ == "__main__":
    unittest.main()
