# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore.data_generation import value_utils


class TestTypeNameMappers(unittest.TestCase):
    def test_json_type_name_of_python_types(self) -> None:
        mapper = value_utils.json_type_name_of_python_type
        self.assertEqual(mapper(str), "string")
        self.assertEqual(mapper(bool), "boolean")
        self.assertEqual(mapper(int), "integer")
        self.assertEqual(mapper(float), "number")
        self.assertEqual(mapper(list), "array")
        self.assertEqual(mapper(dict), "object")
        self.assertEqual(mapper(type(None)), "null")

    def test_python_type_by_json_type_name(self) -> None:
        mapper = value_utils.python_type_by_json_type_name
        self.assertEqual(mapper("string"), str)
        self.assertEqual(mapper("boolean"), bool)
        self.assertEqual(mapper("integer"), int)
        self.assertEqual(mapper("number"), float)
        self.assertEqual(mapper("array"), list)
        self.assertEqual(mapper("object"), dict)
        self.assertEqual(mapper("null"), type(None))

    def test_mappers_raise_for_unknown_mappings(self) -> None:
        self.assertRaises(
            ValueError, value_utils.json_type_name_of_python_type, type(self)
        )
        self.assertRaises(
            ValueError, value_utils.python_type_by_json_type_name, "undefined"
        )


if __name__ == "__main__":
    unittest.main()
