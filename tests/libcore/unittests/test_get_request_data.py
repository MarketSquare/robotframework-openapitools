# pylint: disable="missing-class-docstring", "missing-function-docstring"
import json
import pathlib
import unittest
from functools import partial

from OpenApiLibCore.data_generation.data_generation_core import get_request_data
from OpenApiLibCore.models.oas_models import (
    ArraySchema,
    BooleanSchema,
    BytesSchema,
    IntegerSchema,
    NullSchema,
    NumberSchema,
    ObjectSchema,
    OpenApiObject,
    StringSchema,
)

unittest_folder = pathlib.Path(__file__).parent.resolve()
spec_path = unittest_folder.parent.parent / "files" / "request_data_variations.json"


class TestValidData(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        with open(file=spec_path) as json_file:
            spec_dict = json.load(json_file)
        cls.spec = OpenApiObject.model_validate(spec_dict)
        cls._get_request_data = partial(
            get_request_data, method="POST", openapi_spec=cls.spec
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

    def test_bytes_schema(self) -> None:
        request_data = self._get_request_data(path="/bytes_schema")
        self.assertIsInstance(request_data.valid_data, bytes)
        self.assertIsInstance(request_data.body_schema, BytesSchema)

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


if __name__ == "__main__":
    unittest.main()
