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
    StringSchema,
    UnionTypeSchema,
)

unittest_folder = pathlib.Path(__file__).parent.resolve()
spec_path_3_0 = (
    unittest_folder.parent.parent.parent / "files" / "request_data_variations_3.0.json"
)
spec_path_3_1 = (
    unittest_folder.parent.parent.parent / "files" / "request_data_variations_3.1.json"
)


class TestValidData30(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(file=spec_path_3_0) as json_file:
            spec_dict = json.load(json_file)
        cls.spec = OpenApiObject.model_validate(spec_dict)
        for path_item in cls.spec.paths.values():
            path_item.update_operation_parameters()
            path_item.replace_nullable_with_union()
        cls._get_request_data = staticmethod(
            partial(get_request_data, method="POST", openapi_spec=cls.spec)
        )

    def test_bool_schema(self) -> None:
        request_data = self._get_request_data(path="/boolean_schema")
        self.assertIsInstance(request_data.valid_data, bool)
        self.assertIsInstance(request_data.body_schema, BooleanSchema)

    def test_int_schema(self) -> None:
        request_data = self._get_request_data(path="/integer_schema")
        self.assertIsInstance(request_data.valid_data, int)
        self.assertIsInstance(request_data.body_schema, IntegerSchema)

    def test_number_schema(self) -> None:
        request_data = self._get_request_data(path="/number_schema")
        self.assertIsInstance(request_data.valid_data, float)
        self.assertIsInstance(request_data.body_schema, NumberSchema)

    def test_string_schema(self) -> None:
        request_data = self._get_request_data(path="/string_schema")
        self.assertIsInstance(request_data.valid_data, str)
        self.assertIsInstance(request_data.body_schema, StringSchema)

    def test_string_schema_for_byte_format(self) -> None:
        request_data = self._get_request_data(path="/bytes_schema")
        self.assertIsInstance(request_data.valid_data, str)
        self.assertIsInstance(request_data.body_schema, StringSchema)

    def test_object_schema(self) -> None:
        request_data = self._get_request_data(path="/object_schema")
        self.assertIsInstance(request_data.valid_data, dict)
        self.assertIsInstance(request_data.body_schema, ObjectSchema)

    def test_array_schema(self) -> None:
        request_data = self._get_request_data(path="/array_schema")
        self.assertIsInstance(request_data.valid_data, list)
        self.assertIsInstance(request_data.body_schema, ArraySchema)
        self.assertIsInstance(request_data.body_schema.items, NumberSchema)

    def test_union_schema(self) -> None:
        request_data = self._get_request_data(path="/union_schema")
        self.assertIsInstance(request_data.valid_data, (type(None), int, str))
        self.assertTrue(
            isinstance(
                request_data.body_schema, (NullSchema, IntegerSchema, StringSchema)
            )
        )

    def test_array_with_union_schema(self) -> None:
        request_data = self._get_request_data(path="/array_with_union_schema")
        self.assertIsInstance(request_data.valid_data, list)
        self.assertIsInstance(request_data.valid_data[0], (dict, type(None)))
        self.assertTrue(isinstance(request_data.body_schema, ArraySchema))
        items_schema = request_data.body_schema.items
        self.assertIsInstance(items_schema, UnionTypeSchema)
        [object_schema] = items_schema.resolved_schemas
        self.assertIsInstance(object_schema, ObjectSchema)
        self.assertEqual(object_schema.required, ["name"])
        self.assertIsInstance(object_schema.additionalProperties, UnionTypeSchema)
        additional_properties_schemas = (
            object_schema.additionalProperties.resolved_schemas
        )
        self.assertIsInstance(additional_properties_schemas[0], BooleanSchema)
        self.assertIsInstance(
            additional_properties_schemas[1], (IntegerSchema, NumberSchema)
        )


class TestValidData31(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(file=spec_path_3_1) as json_file:
            spec_dict = json.load(json_file)
        cls.spec = OpenApiObject.model_validate(spec_dict)
        for path_item in cls.spec.paths.values():
            path_item.update_operation_parameters()
            path_item.replace_nullable_with_union()
        cls._get_request_data = staticmethod(
            partial(get_request_data, method="POST", openapi_spec=cls.spec)
        )

    def test_null_schema(self) -> None:
        request_data = self._get_request_data(path="/null_schema")
        self.assertEqual(request_data.valid_data, None)
        self.assertIsInstance(request_data.body_schema, NullSchema)

    def test_bool_schema(self) -> None:
        request_data = self._get_request_data(path="/boolean_schema")
        self.assertIsInstance(request_data.valid_data, bool)
        self.assertIsInstance(request_data.body_schema, BooleanSchema)

    def test_int_schema(self) -> None:
        request_data = self._get_request_data(path="/integer_schema")
        self.assertIsInstance(request_data.valid_data, int)
        self.assertIsInstance(request_data.body_schema, IntegerSchema)

    def test_number_schema(self) -> None:
        request_data = self._get_request_data(path="/number_schema")
        self.assertIsInstance(request_data.valid_data, float)
        self.assertIsInstance(request_data.body_schema, NumberSchema)

    def test_string_schema(self) -> None:
        request_data = self._get_request_data(path="/string_schema")
        self.assertIsInstance(request_data.valid_data, str)
        self.assertIsInstance(request_data.body_schema, StringSchema)

    def test_string_schema_for_byte_format(self) -> None:
        request_data = self._get_request_data(path="/bytes_schema")
        self.assertIsInstance(request_data.valid_data, str)
        self.assertIsInstance(request_data.body_schema, StringSchema)

    def test_object_schema(self) -> None:
        request_data = self._get_request_data(path="/object_schema")
        self.assertIsInstance(request_data.valid_data, dict)
        self.assertIsInstance(request_data.body_schema, ObjectSchema)

    def test_array_schema(self) -> None:
        request_data = self._get_request_data(path="/array_schema")
        self.assertIsInstance(request_data.valid_data, list)
        self.assertIsInstance(request_data.body_schema, ArraySchema)
        self.assertIsInstance(request_data.body_schema.items, NumberSchema)

    def test_union_schema(self) -> None:
        request_data = self._get_request_data(path="/union_schema")
        self.assertIsInstance(request_data.valid_data, (type(None), int, str))
        self.assertTrue(
            isinstance(
                request_data.body_schema, (NullSchema, IntegerSchema, StringSchema)
            )
        )

    def test_array_with_union_schema(self) -> None:
        request_data = self._get_request_data(path="/array_with_union_schema")
        self.assertIsInstance(request_data.valid_data, list)
        self.assertIsInstance(request_data.valid_data[0], dict)
        self.assertTrue(isinstance(request_data.body_schema, ArraySchema))
        items_schema = request_data.body_schema.items
        self.assertIsInstance(items_schema, UnionTypeSchema)
        [resolved_schema] = items_schema.resolved_schemas
        self.assertEqual(resolved_schema.required, ["name"])
        self.assertIsInstance(resolved_schema.additionalProperties, UnionTypeSchema)
        additional_properties_schemas = (
            resolved_schema.additionalProperties.resolved_schemas
        )
        self.assertIsInstance(additional_properties_schemas[0], BooleanSchema)
        self.assertIsInstance(
            additional_properties_schemas[1], (IntegerSchema, NumberSchema)
        )


if __name__ == "__main__":
    unittest.main()
