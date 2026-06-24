# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

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


class TestDefaults(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        self.assertEqual(schema.get_valid_value()[0], None)

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        self.assertIsInstance(schema.get_valid_value()[0], bool)

    def test_string_schema(self) -> None:
        schema = StringSchema()
        self.assertIsInstance(schema.get_valid_value()[0], str)

    def test_integer_schema(self) -> None:
        schema = IntegerSchema()
        self.assertIsInstance(schema.get_valid_value()[0], int)

    def test_number_schema(self) -> None:
        schema = NumberSchema()
        self.assertIsInstance(schema.get_valid_value()[0], float)

    def test_array_schema(self) -> None:
        schema = ArraySchema(items=IntegerSchema())
        value = schema.get_valid_value()[0]
        self.assertIsInstance(value, list)
        if value:
            self.assertIsInstance(value[0], int)

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        value = schema.get_valid_value()[0]
        self.assertIsInstance(value, dict)

    def test_union_schema(self) -> None:
        schema = UnionTypeSchema(oneOf=[BooleanSchema(), IntegerSchema()])
        self.assertIsInstance(schema.get_valid_value()[0], int)


class TestGetValidValueFromConst(unittest.TestCase):
    def test_boolean_schema(self) -> None:
        const = False
        schema = BooleanSchema(const=const)
        self.assertEqual(schema.get_valid_value()[0], const)

    def test_string_schema(self) -> None:
        const = "Hello world!"
        schema = StringSchema(const=const)
        self.assertEqual(schema.get_valid_value()[0], const)

    def test_integer_schema(self) -> None:
        const = 42
        schema = IntegerSchema(const=const)
        self.assertEqual(schema.get_valid_value()[0], const)

    def test_number_schema(self) -> None:
        const = 3.14
        schema = NumberSchema(const=const)
        self.assertEqual(schema.get_valid_value()[0], const)

    def test_array_schema(self) -> None:
        const = ["foo", "bar"]
        schema = ArraySchema(items=StringSchema(), const=const)
        self.assertEqual(schema.get_valid_value()[0], const)

    def test_object_schema(self) -> None:
        const = {"foo": 42, "bar": 3.14}
        schema = ObjectSchema(const=const)
        self.assertEqual(schema.get_valid_value()[0], const)


class TestGetValidValueFromEnum(unittest.TestCase):
    def test_string_schema(self) -> None:
        enum = ["eggs", "bacon", "spam"]
        schema = StringSchema(enum=enum)
        self.assertIn(schema.get_valid_value()[0], enum)

    def test_integer_schema(self) -> None:
        enum = [1, 3, 5, 7]
        schema = IntegerSchema(enum=enum)
        self.assertIn(schema.get_valid_value()[0], enum)

    def test_number_schema(self) -> None:
        enum = [0.1, 0.01, 0.001]
        schema = NumberSchema(enum=enum)
        self.assertIn(schema.get_valid_value()[0], enum)

    def test_array_schema(self) -> None:
        enum = [["foo", "bar"], ["eggs", "bacon", "spam"]]
        schema = ArraySchema(items=StringSchema(), enum=enum)
        self.assertIn(schema.get_valid_value()[0], enum)

    def test_object_schema(self) -> None:
        enum: list[dict[str, int | float]] = [{"foo": 42, "bar": 3.14}]
        schema = ObjectSchema(enum=enum)
        value = schema.get_valid_value()[0]
        self.assertIn(value, enum)


class TestStringSchemaVariations(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = StringSchema(maxLength=0)
        value = schema.get_valid_value()[0]
        self.assertEqual(value, "")

        schema = StringSchema(minLength=36)
        value = schema.get_valid_value()[0]
        self.assertEqual(len(value), 36)

    def test_min_max(self) -> None:
        schema = StringSchema(minLength=42, maxLength=42)
        value = schema.get_valid_value()[0]
        self.assertEqual(len(value), 42)

        schema = StringSchema(minLength=42)
        value = schema.get_valid_value()[0]
        self.assertEqual(len(value), 42)

    def test_datetime(self) -> None:
        schema = StringSchema(format="date-time")
        value = schema.get_valid_value()[0]
        matcher = r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?)$"
        self.assertRegex(value, matcher)

    def test_date(self) -> None:
        schema = StringSchema(format="date")
        value = schema.get_valid_value()[0]
        matcher = r"^(\d{4})-(\d{2})-(\d{2})$"
        self.assertRegex(value, matcher)

    def test_pattern(self) -> None:
        pattern = r"^[1-9][0-9]{3} ?(?!sa|sd|ss|SA|SD|SS)[A-Za-z]{2}$"
        schema = StringSchema(pattern=pattern)
        value = schema.get_valid_value()[0]
        self.assertRegex(value, pattern)

        pattern = r"^(?:[\p{L}\p{Mn}\p{Nd}.,()'-]+(?:['.’ ]|\s?[&\/\p{Pd}]\s?)?)+[\p{L}\p{Mn}\p{Nd}]\.?$"
        schema = StringSchema(pattern=pattern)
        with self.assertLogs(level="WARN") as logs:
            value = schema.get_valid_value()[0]

        self.assertTrue(len(logs.output) > 0)
        last_log_entry = logs.output[-1]
        self.assertTrue(
            last_log_entry.startswith(
                "WARNING:RobotFramework:An error occured trying to generate a string "
                "matching the pattern defined in the specification."
            ),
            last_log_entry,
        )
        self.assertTrue(
            last_log_entry.endswith(f"The pattern was: {pattern}"), last_log_entry
        )


class TestIntegerSchemaVariations(unittest.TestCase):
    def test_unbounded_multipleof(self) -> None:
        # Always true, shouldn't cause any issues
        multiple_of = 1
        schema = IntegerSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer(), f"{factor=} {value=}")

        # The multipleOf is a float, for integers this means the factor will be a
        # mutliple of 10, 100, 1000, etc. depending on the decimals
        multiple_of = 0.71
        schema = IntegerSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer(), f"{factor=} {value=}")

    def test_multipleof_with_min(self) -> None:
        # This multiple_of is just within the min/max value of the JSON spec
        # for (default) int32 so the unbounded factors can only be -1, 0 and 1
        multiple_of = 2000000000
        schema = IntegerSchema(multipleOf=multiple_of, minimum=1)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == 1, f"{factor=} {value=}")

    def test_multipleof_with_max(self) -> None:
        multiple_of = 2000000000
        schema = IntegerSchema(multipleOf=multiple_of, maximum=-1)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == -1, f"{factor=} {value=}")

    def test_multipleof_with_multiple_outside_min_max(self) -> None:
        # The multiple_of is larger than the min/max value, so the only factor for which
        # factor * multiple_of = value is factor=0 (and, thus, value=0)
        multiple_of = 20000000000
        schema = IntegerSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == 0, f"{factor=} {value=}")

    def test_multipleof_with_min_and_max(self) -> None:
        multiple_of = 3.0
        schema = IntegerSchema(multipleOf=multiple_of, minimum=-7, maximum=5)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertIn(value, [-6, -3, 0, 3], f"{factor=} {value=}")


class TestNumberSchemaVariations(unittest.TestCase):
    def test_unbounded_multipleof(self) -> None:
        multiple_of = 2
        schema = NumberSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer(), f"{factor=} {value=}")

        multiple_of = 0.7
        schema = NumberSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer(), f"{factor=} {value=}")

    def test_multipleof_with_min(self) -> None:
        # This multiple_of is just within the min/max value of the JSON spec
        # so the unbounded factors can only be -1, 0 and 1
        multiple_of = 9000000000000000000
        schema = NumberSchema(multipleOf=multiple_of, minimum=0.1)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == 1, f"{factor=} {value=}")

    def test_multipleof_with_max(self) -> None:
        multiple_of = 9000000000000000000
        schema = NumberSchema(multipleOf=multiple_of, maximum=-0.1)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == -1, f"{factor=} {value=}")

    def test_multipleof_with_multiple_outside_min_max(self) -> None:
        # The multiple_of is larger than the min/max value, so the only factor for which
        # factor * multiple_of = value is factor=0 (and, thus, value=0)
        multiple_of = 90000000000000000000
        schema = NumberSchema(multipleOf=multiple_of)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertTrue((int(factor)) == 0, f"{factor=} {value=}")

    def test_multipleof_with_min_and_max(self) -> None:
        multiple_of = 3.11
        schema = NumberSchema(multipleOf=multiple_of, minimum=-7, maximum=6)
        value = schema.get_valid_value()[0]
        factor = value / multiple_of
        self.assertTrue(factor.is_integer())
        self.assertIn(value, [-6.22, -3.11, 0, 3.11], f"{factor=} {value=}")


class TestArraySchemaVariations(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = ArraySchema(items=StringSchema())
        value = schema.get_valid_value()[0]
        self.assertIn(len(value), (0, 1))

        schema = {"maxItems": 0, "items": {"type": "string"}}
        schema = ArraySchema(items=StringSchema(), maxItems=0)
        value = schema.get_valid_value()[0]
        self.assertEqual(value, [])

    def test_min_max(self) -> None:
        schema = ArraySchema(items=StringSchema(), maxItems=3, minItems=2)
        value = schema.get_valid_value()[0]
        self.assertIn(len(value), (2, 3))

        schema = ArraySchema(items=StringSchema(), minItems=5)
        value = schema.get_valid_value()[0]
        self.assertEqual(len(value), 5)

        schema = ArraySchema(items=StringSchema(), minItems=7, maxItems=5)
        value = schema.get_valid_value()[0]
        self.assertEqual(len(value), 7)


if __name__ == "__main__":
    unittest.main()
