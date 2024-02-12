# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestInvalidValueFromEnum(unittest.TestCase):
    def test_string(self) -> None:
        value_list = ["foo", "bar"]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="string",
        )
        self.assertNotIn(result, value_list)

    def test_integer(self) -> None:
        value_list = [-1, 0, 1]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="integer",
        )
        self.assertNotIn(result, value_list)

    def test_float(self) -> None:
        value_list = [-0.1, 0, 0.1]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="integer",
        )
        self.assertNotIn(result, value_list)

    def test_array(self) -> None:
        value_list = [["foo", "bar", "baz"], ["spam", "ham", "eggs"]]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="array",
        )
        self.assertNotIn(result, value_list)

    def test_object(self) -> None:
        value_list = [
            {
                "red": 255,
                "blue": 0,
                "green": 0,
            },
            {
                "red": 0,
                "blue": 255,
                "green": 0,
            },
            {
                "red": 0,
                "blue": 0,
                "green": 255,
            },
        ]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="object",
        )
        self.assertNotIn(result, value_list)

    def test_unsupported(self) -> None:
        value_list = [True, False]
        result = value_utils.get_invalid_value_from_enum(
            values=value_list,
            value_type="bool",
        )
        self.assertEqual(result, None)


if __name__ == "__main__":
    unittest.main()
