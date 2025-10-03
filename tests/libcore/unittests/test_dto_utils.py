# pylint: disable="missing-class-docstring", "missing-function-docstring"
import pathlib
import sys
import unittest

from OpenApiLibCore import Dto
from OpenApiLibCore.data_constraints.dto_base import get_value_constraints_mapping_dict

unittest_folder = pathlib.Path(__file__).parent.resolve()
mappings_path = (
    unittest_folder.parent.parent / "user_implemented" / "custom_user_mappings.py"
)


class TestGetDtoClass(unittest.TestCase):
    mappings_module_name = ""

    @classmethod
    def setUpClass(cls) -> None:
        if mappings_path.is_file():
            mappings_folder = str(mappings_path.parent)
            sys.path.append(mappings_folder)
            cls.mappings_module_name = mappings_path.stem
            print(f"added {mappings_folder} to path")
        else:
            assert False, "The mappings_path is not a file."

    @classmethod
    def tearDownClass(cls) -> None:
        if mappings_path.is_file():
            print(f"removed {sys.path.pop()} from path")

    def test_no_mapping(self) -> None:
        value_constraints_mapping_dict = get_value_constraints_mapping_dict("dummy")
        self.assertDictEqual(value_constraints_mapping_dict, {})

    def test_valid_mapping(self) -> None:
        value_constraints_mapping_dict = get_value_constraints_mapping_dict(
            self.mappings_module_name
        )
        self.assertIsInstance(value_constraints_mapping_dict, dict)
        self.assertGreater(len(value_constraints_mapping_dict.keys()), 0)

    def test_mapped_returns_dto_instance(self) -> None:
        value_constraints_mapping_dict = get_value_constraints_mapping_dict(
            self.mappings_module_name
        )
        keys = value_constraints_mapping_dict.keys()
        for key in keys:
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertIsInstance(value_constraints_mapping_dict[key](), Dto)


if __name__ == "__main__":
    unittest.main()
