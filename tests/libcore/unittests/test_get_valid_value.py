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
        self.assertEqual(schema.get_valid_value(), None)

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        self.assertIsInstance(schema.get_valid_value(), bool)

    def test_string_schema(self) -> None:
        schema = StringSchema()
        self.assertIsInstance(schema.get_valid_value(), str)

    def test_integer_schema(self) -> None:
        schema = IntegerSchema()
        self.assertIsInstance(schema.get_valid_value(), int)

    def test_number_schema(self) -> None:
        schema = NumberSchema()
        self.assertIsInstance(schema.get_valid_value(), float)

    def test_array_schema(self) -> None:
        schema = ArraySchema(items=IntegerSchema())
        value = schema.get_valid_value()
        self.assertIsInstance(value, list)
        if value:
            self.assertIsInstance(value[0], int)

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        value = schema.get_valid_value()
        self.assertIsInstance(value, dict)

    def test_union_schema(self) -> None:
        schema = UnionTypeSchema(oneOf=[BooleanSchema(), IntegerSchema()])
        self.assertIsInstance(schema.get_valid_value(), int)


class TestGetValidValueFromConst(unittest.TestCase):
    def test_boolean_schema(self) -> None:
        const = False
        schema = BooleanSchema(const=const)
        self.assertEqual(schema.get_valid_value(), const)

    def test_string_schema(self) -> None:
        const = "Hello world!"
        schema = StringSchema(const=const)
        self.assertEqual(schema.get_valid_value(), const)

    def test_integer_schema(self) -> None:
        const = 42
        schema = IntegerSchema(const=const)
        self.assertEqual(schema.get_valid_value(), const)

    def test_number_schema(self) -> None:
        const = 3.14
        schema = NumberSchema(const=const)
        self.assertEqual(schema.get_valid_value(), const)

    def test_array_schema(self) -> None:
        const = ["foo", "bar"]
        schema = ArraySchema(items=StringSchema(), const=const)
        self.assertEqual(schema.get_valid_value(), const)

    def test_object_schema(self) -> None:
        const = {"foo": 42, "bar": 3.14}
        schema = ObjectSchema(const=const)
        self.assertEqual(schema.get_valid_value(), const)


class TestGetValidValueFromEnum(unittest.TestCase):
    def test_string_schema(self) -> None:
        enum = ["eggs", "bacon", "spam"]
        schema = StringSchema(enum=enum)
        self.assertIn(schema.get_valid_value(), enum)

    def test_integer_schema(self) -> None:
        enum = [1, 3, 5, 7]
        schema = IntegerSchema(enum=enum)
        self.assertIn(schema.get_valid_value(), enum)

    def test_number_schema(self) -> None:
        enum = [0.1, 0.01, 0.001]
        schema = NumberSchema(enum=enum)
        self.assertIn(schema.get_valid_value(), enum)

    def test_array_schema(self) -> None:
        enum = [["foo", "bar"], ["eggs", "bacon", "spam"]]
        schema = ArraySchema(items=StringSchema(), enum=enum)
        self.assertIn(schema.get_valid_value(), enum)

    def test_object_schema(self) -> None:
        enum: list[dict[str, int | float]] = [{"foo": 42, "bar": 3.14}]
        schema = ObjectSchema(enum=enum)
        value = schema.get_valid_value()
        self.assertIn(value, enum)


class TestStringSchemaVariations(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = StringSchema(maxLength=0)
        value = schema.get_valid_value()
        self.assertEqual(value, "")

        schema = StringSchema(minLength=36)
        value = schema.get_valid_value()
        self.assertEqual(len(value), 36)

    def test_min_max(self) -> None:
        schema = StringSchema(minLength=42, maxLength=42)
        value = schema.get_valid_value()
        self.assertEqual(len(value), 42)

        schema = StringSchema(minLength=42)
        value = schema.get_valid_value()
        self.assertEqual(len(value), 42)

    def test_datetime(self) -> None:
        schema = StringSchema(format="date-time")
        value = schema.get_valid_value()
        matcher = r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?)$"
        self.assertRegex(value, matcher)

    def test_date(self) -> None:
        schema = StringSchema(format="date")
        value = schema.get_valid_value()
        matcher = r"^(\d{4})-(\d{2})-(\d{2})$"
        self.assertRegex(value, matcher)

    def test_pattern(self) -> None:
        pattern = r"^[1-9][0-9]{3} ?(?!sa|sd|ss|SA|SD|SS)[A-Za-z]{2}$"
        schema = StringSchema(pattern=pattern)
        value = schema.get_valid_value()
        self.assertRegex(value, pattern)

    def test_byte(self) -> None:
        schema = StringSchema(format="byte")
        value = schema.get_valid_value()
        self.assertIsInstance(value, bytes)


class TestArraySchemaVariations(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = ArraySchema(items=StringSchema())
        value = schema.get_valid_value()
        self.assertIn(len(value), (0, 1))

        schema = {"maxItems": 0, "items": {"type": "string"}}
        schema = ArraySchema(items=StringSchema(), maxItems=0)
        value = schema.get_valid_value()
        self.assertEqual(value, [])

    def test_min_max(self) -> None:
        schema = ArraySchema(items=StringSchema(), maxItems=3, minItems=2)
        value = schema.get_valid_value()
        self.assertIn(len(value), (2, 3))

        schema = ArraySchema(items=StringSchema(), minItems=5)
        value = schema.get_valid_value()
        self.assertEqual(len(value), 5)

        schema = ArraySchema(items=StringSchema(), minItems=7, maxItems=5)
        value = schema.get_valid_value()
        self.assertEqual(len(value), 7)


if __name__ == "__main__":
    unittest.main()
