# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore.models import (
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
        self.assertIsInstance(value[0], int)

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        self.assertRaises(NotImplementedError, schema.get_valid_value)
        # value = schema.get_valid_value()
        # self.assertIsInstance(value, dict)
        # self.assertDictEqual(value, {})

        # schema = ObjectSchema(properties={"foo": StringSchema(), "bar": NumberSchema()})
        # self.assertRaises(NotImplementedError, schema.get_valid_value)
        # value = schema.get_valid_value()
        # self.assertIsInstance(value, dict)
        # self.assertIsInstance(value["foo"], str)
        # self.assertIsInstance(value["bar"], float)

    def test_union_schema(self) -> None:
        schema = UnionTypeSchema(oneOf=[BooleanSchema(), IntegerSchema()])
        self.assertIsInstance(schema.get_valid_value(), int)


class TestGetValidValueFromConst(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        self.assertEqual(schema.has_const_or_enum, False)

    def test_boolean_schema(self) -> None:
        const = False
        schema = BooleanSchema(const=const)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertEqual(schema.get_valid_value(), const)

    def test_string_schema(self) -> None:
        const = "Hello world!"
        schema = StringSchema(const=const)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertEqual(schema.get_valid_value(), const)

    def test_integer_schema(self) -> None:
        const = 42
        schema = IntegerSchema(const=const)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertEqual(schema.get_valid_value(), const)

    def test_number_schema(self) -> None:
        const = 3.14
        schema = NumberSchema(const=const)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertEqual(schema.get_valid_value(), const)

    def test_array_schema(self) -> None:
        const = ["foo", "bar"]
        schema = ArraySchema(items=StringSchema(), const=const)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertEqual(schema.get_valid_value(), const)

    def test_object_schema(self) -> None:
        const = {"foo": 42, "bar": 3.14}
        schema = ObjectSchema(const=const)
        self.assertRaises(NotImplementedError, schema.get_valid_value)
        # self.assertEqual(schema.has_const_or_enum, True)
        # self.assertEqual(schema.get_valid_value(), const)


class TestGetValidValueFromEnum(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        self.assertEqual(schema.has_const_or_enum, False)

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        self.assertEqual(schema.has_const_or_enum, False)

    def test_string_schema(self) -> None:
        enum = ["eggs", "bacon", "spam"]
        schema = StringSchema(enum=enum)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertIn(schema.get_valid_value(), enum)

    def test_integer_schema(self) -> None:
        enum = [1, 3, 5, 7]
        schema = IntegerSchema(enum=enum)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertIn(schema.get_valid_value(), enum)

    def test_number_schema(self) -> None:
        enum = [0.1, 0.01, 0.001]
        schema = NumberSchema(enum=enum)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertIn(schema.get_valid_value(), enum)

    def test_array_schema(self) -> None:
        enum = [["foo", "bar"], ["eggs", "bacon", "spam"]]
        schema = ArraySchema(items=StringSchema(), enum=enum)
        self.assertEqual(schema.has_const_or_enum, True)
        self.assertIn(schema.get_valid_value(), enum)

    def test_object_schema(self) -> None:
        enum: list[dict[str, int | float]] = [{"foo": 42, "bar": 3.14}]
        schema = ObjectSchema(enum=enum)
        self.assertRaises(NotImplementedError, schema.get_valid_value)
        # self.assertEqual(schema.has_const_or_enum, True)
        # self.assertIn(schema.get_valid_value(), enum)


if __name__ == "__main__":
    unittest.main()
