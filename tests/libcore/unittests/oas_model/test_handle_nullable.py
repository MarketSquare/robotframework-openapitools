# pylint: disable="missing-class-docstring", "missing-function-docstring"
import json
import pathlib
import unittest
from functools import partial

from OpenApiLibCore.data_generation.data_generation_core import get_request_data
from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    BooleanSchema,
    IntegerSchema,
    NullSchema,
    NumberSchema,
    ObjectSchema,
    OpenApiObject,
    SchemaObjectTypes,
    StringSchema,
    UnionTypeSchema,
)

unittest_folder = pathlib.Path(__file__).parent.resolve()
spec_path = (
    unittest_folder.parent.parent.parent / "files" / "nullable_schema_variations.json"
)


class TestValidData30(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(file=spec_path) as json_file:
            spec_dict = json.load(json_file)
        cls.spec = OpenApiObject.model_validate(spec_dict)
        for path_item in cls.spec.paths.values():
            path_item.update_operation_parameters()
            path_item.replace_nullable_with_union()
        cls._get_request_data = staticmethod(
            partial(get_request_data, method="POST", openapi_spec=cls.spec)
        )

    def get_body_schema_by_path(self, path: str) -> SchemaObjectTypes:
        return (
            self.spec.paths[path].post.requestBody.content["application/json"].schema_
        )

    def test_boolean_schema(self) -> None:
        python_type = bool
        path = "/boolean_schema"
        schema_type = BooleanSchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        bool_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(bool_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_integer_schema(self) -> None:
        python_type = int
        path = "/integer_schema"
        schema_type = IntegerSchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        type_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(type_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_number_schema(self) -> None:
        python_type = float
        path = "/number_schema"
        schema_type = NumberSchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        type_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(type_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_string_schema(self) -> None:
        python_type = str
        path = "/string_schema"
        schema_type = StringSchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        type_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(type_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_array_schema(self) -> None:
        python_type = list
        path = "/array_schema"
        schema_type = ArraySchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        type_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(type_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_object_schema(self) -> None:
        python_type = dict
        path = "/object_schema"
        schema_type = ObjectSchema
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (python_type, type(None)))
        self.assertIsInstance(request_data.body_schema, (schema_type, NullSchema))
        if isinstance(request_data.body_schema, schema_type):
            self.assertIsInstance(request_data.valid_data, python_type)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        type_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(type_schema, schema_type)
        self.assertIsInstance(null_schema, NullSchema)

    def test_oneof_union_schema(self) -> None:
        path = "/oneof_first"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

        path = "/oneof_second"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

        path = "/oneof_both"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

    def test_anyof_union_schema(self) -> None:
        path = "/anyof_first"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

        path = "/anyof_second"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

        path = "/anyof_both"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (int, str, type(None)))
        self.assertIsInstance(
            request_data.body_schema, (IntegerSchema, StringSchema, NullSchema)
        )
        if isinstance(request_data.body_schema, (IntegerSchema, StringSchema)):
            self.assertIsInstance(request_data.valid_data, (int, str))
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        integer_schema, string_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(integer_schema, IntegerSchema)
        self.assertIsInstance(string_schema, StringSchema)
        self.assertIsInstance(null_schema, NullSchema)

    def test_allof_union_schema(self) -> None:
        path = "/allof_one"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, dict)
        self.assertIsInstance(request_data.body_schema, ObjectSchema)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        [object_schema] = body_schema.resolved_schemas
        self.assertIsInstance(object_schema, ObjectSchema)

        path = "/allof_all"
        request_data = self._get_request_data(path)
        self.assertIsInstance(request_data.valid_data, (dict, type(None)))
        self.assertIsInstance(request_data.body_schema, (ObjectSchema, NullSchema))
        if isinstance(request_data.body_schema, ObjectSchema):
            self.assertIsInstance(request_data.valid_data, dict)
        else:
            self.assertEqual(request_data.valid_data, None)

        body_schema = self.get_body_schema_by_path(path)
        self.assertIsInstance(body_schema, UnionTypeSchema)
        object_schema, null_schema = body_schema.resolved_schemas
        self.assertIsInstance(object_schema, ObjectSchema)
        self.assertIsInstance(null_schema, NullSchema)


if __name__ == "__main__":
    unittest.main()
