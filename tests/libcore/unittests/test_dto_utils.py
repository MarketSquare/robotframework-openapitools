# pylint: disable="missing-class-docstring", "missing-function-docstring"
import pathlib
import sys
import unittest

from OpenApiLibCore import (
    DefaultDto,
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
)
from OpenApiLibCore.data_constraints.dto_base import get_dto_class

unittest_folder = pathlib.Path(__file__).parent.resolve()
mappings_path = (
    unittest_folder.parent.parent / "user_implemented" / "custom_user_mappings.py"
)


class TestDefaultDto(unittest.TestCase):
    def test_can_init(self) -> None:
        default_dto = DefaultDto()
        self.assertIsInstance(default_dto, Dto)


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
        get_dto_class_instance = get_dto_class("dummy")
        self.assertDictEqual(get_dto_class_instance.dto_mapping, {})

    def test_valid_mapping(self) -> None:
        get_dto_class_instance = get_dto_class(self.mappings_module_name)
        self.assertIsInstance(get_dto_class_instance.dto_mapping, dict)
        self.assertGreater(len(get_dto_class_instance.dto_mapping.keys()), 0)

    def mapped_returns_dto_instance(self) -> None:
        get_dto_class_instance = get_dto_class(self.mappings_module_name)
        keys = get_dto_class_instance.dto_mapping.keys()
        for key in keys:
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertIsInstance(
                get_dto_class_instance(key),
                (
                    IdDependency,
                    IdReference,
                    PropertyValueConstraint,
                    UniquePropertyValueConstraint,
                ),
            )

    def unmapped_returns_defaultdto(self) -> None:
        get_dto_class_instance = get_dto_class(self.mappings_module_name)
        self.assertIsInstance(get_dto_class_instance(("dummy", "post")), DefaultDto)


if __name__ == "__main__":
    unittest.main()
