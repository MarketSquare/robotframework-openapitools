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


class TestGetInValidValueFromConstOrEnumRaisesWhenNoConstOrEnum(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_string_schema(self) -> None:
        schema = StringSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_integer_schema(self) -> None:
        schema = IntegerSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_number_schema(self) -> None:
        schema = NumberSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_array_schema(self) -> None:
        schema = ArraySchema(items=StringSchema())
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()

    def test_union_schema(self) -> None:
        schema = UnionTypeSchema()
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()


class TestGetInValidValueFromConst(unittest.TestCase):
    def test_boolean_schema(self) -> None:
        const = False
        schema = BooleanSchema(const=const)
        self.assertNotEqual(schema.get_invalid_value_from_const_or_enum(), const)

    def test_string_schema(self) -> None:
        const = "Hello world!"
        schema = StringSchema(const=const)
        self.assertNotEqual(schema.get_invalid_value_from_const_or_enum(), const)

    def test_integer_schema(self) -> None:
        const = 42
        schema = IntegerSchema(const=const)
        self.assertNotEqual(schema.get_invalid_value_from_const_or_enum(), const)

    def test_number_schema(self) -> None:
        const = 3.14
        schema = NumberSchema(const=const)
        self.assertNotEqual(schema.get_invalid_value_from_const_or_enum(), const)

    def test_array_schema(self) -> None:
        const = ["foo", "bar"]
        schema = ArraySchema(items=StringSchema(), const=const)
        self.assertNotEqual(schema.get_invalid_value_from_const_or_enum(), const)

    def test_object_schema(self) -> None:
        const = {"foo": 42, "bar": 3.14}
        schema = ObjectSchema(const=const)
        with self.assertRaises(ValueError):
            schema.get_invalid_value_from_const_or_enum()


class TestGetInValidValueFromEnum(unittest.TestCase):
    def test_string_schema(self) -> None:
        enum = ["eggs", "bacon", "spam"]
        schema = StringSchema(enum=enum)
        self.assertNotIn(schema.get_invalid_value_from_const_or_enum(), enum)

    def test_integer_schema(self) -> None:
        enum = [-1, 0, 1]
        schema = IntegerSchema(enum=enum)
        self.assertNotIn(schema.get_invalid_value_from_const_or_enum(), enum)

    def test_number_schema(self) -> None:
        enum = [-0.1, 0, 0.1]
        schema = NumberSchema(enum=enum)
        self.assertNotIn(schema.get_invalid_value_from_const_or_enum(), enum)

    def test_array_schema(self) -> None:
        enum = [["foo", "bar"], ["eggs", "bacon", "spam"]]
        schema = ArraySchema(items=StringSchema(), enum=enum)
        self.assertNotIn(schema.get_invalid_value_from_const_or_enum(), enum)

    def test_object_schema(self) -> None:
        enum: list[dict[str, int | float]] = [
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
        schema = ObjectSchema(enum=enum)
        self.assertNotIn(schema.get_invalid_value_from_const_or_enum(), enum)


if __name__ == "__main__":
    unittest.main()
