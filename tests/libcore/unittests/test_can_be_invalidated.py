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
)


class TestCanBeInvalidated(unittest.TestCase):
    def test_null_schema(self) -> None:
        schema = NullSchema()
        self.assertEqual(schema.can_be_invalidated, False)

    def test_boolean_schema(self) -> None:
        schema = BooleanSchema()
        self.assertEqual(schema.can_be_invalidated, True)

    def test_string_schema(self) -> None:
        schema = StringSchema()
        self.assertEqual(schema.can_be_invalidated, False)

        schema = StringSchema(maxLength=1)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = StringSchema(minLength=1)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = StringSchema(const="foo")
        self.assertEqual(schema.can_be_invalidated, True)

        schema = StringSchema(enum=["eggs", "spam"])
        self.assertEqual(schema.can_be_invalidated, True)

    def test_integer_schema(self) -> None:
        schema = IntegerSchema()
        self.assertEqual(schema.can_be_invalidated, True)

    def test_number_schema(self) -> None:
        schema = NumberSchema()
        self.assertEqual(schema.can_be_invalidated, True)

    def test_array_schema(self) -> None:
        schema = ArraySchema(items=StringSchema())
        self.assertEqual(schema.can_be_invalidated, False)

        schema = ArraySchema(items=StringSchema(), maxItems=1)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=StringSchema(), minItems=1)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=StringSchema(), uniqueItems=True)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=StringSchema(), const=["foo"])
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=StringSchema(), enum=[["bar"], ["baz"]])
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=BooleanSchema())
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=IntegerSchema())
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ArraySchema(items=NumberSchema())
        self.assertEqual(schema.can_be_invalidated, True)

    def test_object_schema(self) -> None:
        schema = ObjectSchema()
        self.assertEqual(schema.can_be_invalidated, False)

        schema = ObjectSchema(required=["foo"])
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ObjectSchema(maxProperties=2)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ObjectSchema(minProperties=1)
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ObjectSchema(const={"foo": "bar"})
        self.assertEqual(schema.can_be_invalidated, True)

        schema = ObjectSchema(enum=[{"spam": 3}, {"eggs": 7}])
        self.assertEqual(schema.can_be_invalidated, True)


if __name__ == "__main__":
    unittest.main()
