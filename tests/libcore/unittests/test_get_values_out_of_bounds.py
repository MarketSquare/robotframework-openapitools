# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest
from sys import float_info

from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    BooleanSchema,
    BytesSchema,
    IntegerSchema,
    NullSchema,
    NumberSchema,
    ObjectSchema,
    StringSchema,
    UnionTypeSchema,
)

EPSILON = float_info.epsilon


class TestGetValuesOutOfBounds(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=None)

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=True)

    def test_string_schema(self) -> None:
        schema = StringSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(
                current_value="minLength and maxLength not set"
            )

        schema = StringSchema(minLength=0)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(
                current_value="minLength 0 and maxLength not set"
            )

        schema = StringSchema(minLength=2)
        self.assertEqual(
            schema.get_values_out_of_bounds(
                current_value="minLength 2 and maxLength not set"
            ),
            ["m"],
        )

        schema = StringSchema(maxLength=5)
        self.assertEqual(
            schema.get_values_out_of_bounds(current_value=""),
            ["xxxxxx"],
        )

        schema = StringSchema(minLength=3, maxLength=5)
        self.assertEqual(
            schema.get_values_out_of_bounds(current_value="TTTT"), ["TT", "TTTTTT"]
        )

    def test_bytes_schema(self) -> None:
        schema = BytesSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(
                current_value=b"minLength and maxLength not set"
            )

        schema = BytesSchema(minLength=0)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(
                current_value=b"minLength 0 and maxLength not set"
            )

        schema = BytesSchema(minLength=2)
        self.assertEqual(
            schema.get_values_out_of_bounds(
                current_value=b"minLength 2 and maxLength not set"
            ),
            [b"m"],
        )

        schema = BytesSchema(maxLength=5)
        self.assertEqual(
            schema.get_values_out_of_bounds(current_value=b""),
            [b"eHh4eH"],
        )

        schema = BytesSchema(minLength=3, maxLength=5)
        self.assertEqual(
            schema.get_values_out_of_bounds(current_value=b"TTTT"), [b"TT", b"VFRUVF"]
        )

    def test_integer_schema(self) -> None:
        schema = IntegerSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = IntegerSchema(format="int64")
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = IntegerSchema(minimum=-10)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=0), [-11])

        schema = IntegerSchema(maximum=-10)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=-99), [-9])

        schema = IntegerSchema(minimum=-99, exclusiveMinimum=True, maximum=99)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [-99, 100])

        schema = IntegerSchema(minimum=-99, maximum=99, exclusiveMaximum=True)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [-100, 99])

        schema = IntegerSchema(
            minimum=-99, exclusiveMinimum=True, maximum=99, exclusiveMaximum=True
        )
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [-99, 99])

        schema = IntegerSchema(exclusiveMinimum=-99, exclusiveMaximum=99)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [-99, 99])

        schema = IntegerSchema(minimum=-2147483648)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = IntegerSchema(minimum=-2147483648, maximum=50)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [51])

        schema = IntegerSchema(maximum=2147483647)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = IntegerSchema(minimum=1, maximum=2147483647)
        self.assertEqual(schema.get_values_out_of_bounds(current_value=42), [0])

        schema = IntegerSchema(format="int64", minimum=-9223372036854775808)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = IntegerSchema(format="int64", maximum=9223372036854775807)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

    def test_number_schema(self) -> None:
        schema = NumberSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = NumberSchema(minimum=-10.0)
        values = schema.get_values_out_of_bounds(current_value=0)
        self.assertEqual(len(values), 1)
        self.assertLess(values[0], 10.0)
        self.assertAlmostEqual(values[0], -10.0)

        schema = NumberSchema(maximum=-10.0)
        values = schema.get_values_out_of_bounds(current_value=-99)
        self.assertEqual(len(values), 1)
        self.assertGreater(values[0], -10.0)
        self.assertAlmostEqual(values[0], -10.0)

        schema = NumberSchema(minimum=-9.9, exclusiveMinimum=True, maximum=9.9)
        values = schema.get_values_out_of_bounds(current_value=4.2)
        self.assertEqual(len(values), 2)
        self.assertLess(values[0], -9.9)
        self.assertAlmostEqual(values[0], -9.9)
        self.assertGreater(values[1], 9.9)
        self.assertAlmostEqual(values[1], 9.9)

        schema = NumberSchema(minimum=-9.9, maximum=9.9, exclusiveMaximum=True)
        values = schema.get_values_out_of_bounds(current_value=4.2)
        self.assertEqual(len(values), 2)
        self.assertLess(values[0], -9.9)
        self.assertAlmostEqual(values[0], -9.9)
        self.assertGreater(values[1], 9.9)
        self.assertAlmostEqual(values[1], 9.9)

        schema = NumberSchema(exclusiveMinimum=-9.9, exclusiveMaximum=9.9)
        values = schema.get_values_out_of_bounds(current_value=4.2)
        self.assertEqual(len(values), 2)
        self.assertLess(values[0], -9.9)
        self.assertAlmostEqual(values[0], -9.9)
        self.assertGreater(values[1], 9.9)
        self.assertAlmostEqual(values[1], 9.9)

        schema = NumberSchema(minimum=-9223372036854775808.0)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = NumberSchema(minimum=-9223372036854775808, maximum=50)
        values = schema.get_values_out_of_bounds(current_value=4.2)
        self.assertEqual(len(values), 1)
        self.assertGreater(values[0], 50.0)
        self.assertAlmostEqual(values[0], 50.0)

        schema = NumberSchema(maximum=9223372036854775807.0)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=42)

        schema = NumberSchema(minimum=0.1, maximum=9223372036854775807.0)
        values = schema.get_values_out_of_bounds(current_value=4.2)
        self.assertEqual(len(values), 1)
        self.assertLess(values[0], 0.1)
        self.assertAlmostEqual(values[0], 0.1)

    def test_array_schema(self) -> None:
        schema = ArraySchema(items=IntegerSchema())
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=[1])

        schema = ArraySchema(items=IntegerSchema(), minItems=0)
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value=[])

        schema = ArraySchema(items=IntegerSchema(), maxItems=0)
        values = schema.get_values_out_of_bounds(current_value=[])
        self.assertEqual(len(values), 1)
        self.assertIsInstance(values[0][0], int)

        schema = ArraySchema(items=IntegerSchema(), minItems=2)
        current_value = [1, 3, 5]
        values = schema.get_values_out_of_bounds(current_value=current_value)
        self.assertEqual(len(values), 1)
        self.assertIn(values[0][0], current_value)

        schema = ArraySchema(items=IntegerSchema(), maxItems=3)
        current_value = [1, 3, 5]
        values = schema.get_values_out_of_bounds(current_value=current_value)
        self.assertEqual(len(values), 1)
        self.assertEqual(len(values[0]), 4)
        self.assertIn(values[0][3], current_value)

        schema = ArraySchema(items=IntegerSchema(), minItems=1, maxItems=2)
        current_value = [7]
        values = schema.get_values_out_of_bounds(current_value=current_value)
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0], [])
        self.assertIn(current_value[0], values[1])

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value={})

    def test_union_schema(self) -> None:
        schema = UnionTypeSchema(oneOf=[BooleanSchema(), IntegerSchema()])
        with self.assertRaises(ValueError):
            schema.get_values_out_of_bounds(current_value={})


if __name__ == "__main__":
    unittest.main()
