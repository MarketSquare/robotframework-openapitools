# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

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


class TestResolvedSchemasPropery(unittest.TestCase):
    def test_allof_only_supports_object_schemas(self) -> None:
        schema = UnionTypeSchema(allOf=[NullSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[BooleanSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[StringSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[BytesSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[IntegerSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[NumberSchema()])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

        schema = UnionTypeSchema(allOf=[ArraySchema(items=StringSchema())])
        with self.assertRaises(NotImplementedError):
            schema.resolved_schemas

    def test_allof_not_compatible_with_const(self) -> None:
        schema = UnionTypeSchema(allOf=[ObjectSchema(const={"foo": "bar"})])
        with self.assertRaises(ValueError):
            schema.resolved_schemas

    def test_allof_not_compatible_with_enum(self) -> None:
        schema = UnionTypeSchema(
            allOf=[ObjectSchema(enum=[{"foo": "bar"}, {"eggs": "spam"}])]
        )
        with self.assertRaises(ValueError):
            schema.resolved_schemas

    def test_nested_union_schemas(self) -> None:
        oneof = UnionTypeSchema(oneOf=[IntegerSchema(), NumberSchema()])
        anyof = UnionTypeSchema(oneOf=[StringSchema(), NullSchema()])
        schema = UnionTypeSchema(anyOf=[oneof, anyof])
        self.assertEqual(len(schema.resolved_schemas), 4)

    def test_allof_for_objects_with_additional_properties(self) -> None:
        any_additional = ObjectSchema(additionalProperties=True)
        no_additional = ObjectSchema(additionalProperties=False)
        bool_additional = ObjectSchema(additionalProperties=BooleanSchema())
        int_additional = ObjectSchema(additionalProperties=IntegerSchema())
        schema = UnionTypeSchema(
            allOf=[any_additional, no_additional, bool_additional, int_additional]
        )
        [resolved] = schema.resolved_schemas
        self.assertEqual(resolved.additionalProperties, True)

        schema = UnionTypeSchema(allOf=[no_additional, bool_additional, int_additional])
        [resolved] = schema.resolved_schemas
        self.assertIsInstance(resolved.additionalProperties, UnionTypeSchema)
        resolved_additional_properties = resolved.additionalProperties.resolved_schemas
        self.assertEqual(
            resolved_additional_properties, [BooleanSchema(), IntegerSchema()]
        )

        schema = UnionTypeSchema(allOf=[no_additional, no_additional])
        [resolved] = schema.resolved_schemas
        self.assertEqual(resolved.additionalProperties, False)


if __name__ == "__main__":
    unittest.main()
