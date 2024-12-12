# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest
from typing import Any

from OpenApiLibCore import IGNORE, value_utils


class TestInvalidValueFromConstraint(unittest.TestCase):
    def test_ignore(self) -> None:
        values = [42, IGNORE]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="irrelevant",
        )
        self.assertEqual(value, IGNORE)

    def test_unsupported(self) -> None:
        values = [{"red": 255, "green": 255, "blue": 255}]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="dummy",
        )
        self.assertEqual(value, None)

    def test_bool(self) -> None:
        values = [True]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="boolean",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, bool)

        values = [False]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="boolean",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, bool)

        values = [True, False]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="boolean",
        )
        self.assertEqual(value, None)

    def test_string(self) -> None:
        values = ["foo"]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="string",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, str)

        values = ["foo", "bar", "baz"]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="string",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, str)

        values = [""]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="string",
        )
        self.assertEqual(value, None)

    def test_integer(self) -> None:
        values = [0]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="integer",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, int)

        values = [-3, 0, 3]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="integer",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, int)

    def test_number(self) -> None:
        values = [0.0]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="number",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, float)

        values = [-0.1, 0.0, 0.1]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="number",
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, float)

    def test_array(self) -> None:
        values: list[Any] = [[42]]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="array",
        )
        self.assertNotIn(value, values)

        values = [["spam"], ["ham", "eggs"]]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="array",
        )
        self.assertNotIn(value, values)

        values = []
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="array",
        )
        self.assertEqual(value, None)

        values = [[], []]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="array",
        )
        self.assertEqual(value, [])

    def test_object(self) -> None:
        values = [{"red": 255, "green": 255, "blue": 255}]
        value = value_utils.get_invalid_value_from_constraint(
            values_from_constraint=values,
            value_type="object",
        )
        self.assertNotEqual(value, values[0])
        self.assertIsInstance(value, dict)


if __name__ == "__main__":
    unittest.main()
