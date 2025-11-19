# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest
from typing import Any

from OpenApiLibCore import IGNORE
from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    BooleanSchema,
    IntegerSchema,
    NullSchema,
    NumberSchema,
    ObjectSchema,
    StringSchema,
    UnionTypeSchema,
)


class TestInvalidValueFromConstraint(unittest.TestCase):
    def test_bool(self) -> None:
        schema = BooleanSchema()
        values = [True]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, bool)

        values = [False]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, bool)

        values = [True, False]
        with self.assertRaises(ValueError):
            _ = schema.get_invalid_value_from_constraint(
                values_from_constraint=values,
            )

    def test_string(self) -> None:
        schema = StringSchema()
        values = ["foo"]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, str)

        values = ["foo", "bar", "baz"]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, str)

        values = [""]
        with self.assertRaises(ValueError):
            _ = schema.get_invalid_value_from_constraint(
                values_from_constraint=values,
            )

    def test_integer(self) -> None:
        schema = IntegerSchema()
        values = [0]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, int)

        values = [-3, 0, 3]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, int)

    def test_number(self) -> None:
        schema = NumberSchema()
        values = [0.0]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, float)

        values = [-0.1, 0.0, 0.1]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        self.assertIsInstance(value, float)

    def test_array(self) -> None:
        schema = ArraySchema(items=IntegerSchema())
        values = [[42]]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        for item in value:
            self.assertIsInstance(item, int)

        schema = ArraySchema(items=StringSchema())
        values = [["spam"], ["ham", "eggs"]]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotIn(value, values)
        for item in value:
            self.assertIsInstance(item, str)

        schema = ArraySchema(items=ArraySchema(items=StringSchema()))
        values = [[], []]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertEqual(value, [])

    def test_object(self) -> None:
        schema = ObjectSchema()
        values = [{"red": 255, "green": 255, "blue": 255}]
        value = schema.get_invalid_value_from_constraint(
            values_from_constraint=values,
        )
        self.assertNotEqual(value, values[0])
        self.assertIsInstance(value, dict)

    def test_union(self) -> None:
        schema = UnionTypeSchema()
        values = [None]
        with self.assertRaises(ValueError):
            _ = schema.get_invalid_value_from_constraint(
                values_from_constraint=values,
            )

    def test_null(self) -> None:
        schema = NullSchema()
        values = [None]
        with self.assertRaises(ValueError):
            _ = schema.get_invalid_value_from_constraint(
                values_from_constraint=values,
            )


if __name__ == "__main__":
    unittest.main()
