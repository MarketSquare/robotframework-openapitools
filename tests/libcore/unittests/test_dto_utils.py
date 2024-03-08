# pylint: disable="missing-class-docstring", "missing-function-docstring"
import pathlib
import sys
import unittest

from OpenApiLibCore import (
    Dto,
    IdDependency,
    IdReference,
    PathPropertiesConstraint,
    PropertyValueConstraint,
    UniquePropertyValueConstraint,
    dto_utils,
)

unittest_folder = pathlib.Path(__file__).parent.resolve()
mappings_path = (
    unittest_folder.parent.parent / "user_implemented" / "custom_user_mappings.py"
)


class TestDefaultDto(unittest.TestCase):
    def test_can_init(self):
        default_dto = dto_utils.DefaultDto()
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

    def test_no_mapping(self):
        get_dto_class_instance = dto_utils.get_dto_class("dummy")
        self.assertDictEqual(get_dto_class_instance.dto_mapping, {})

    def test_valid_mapping(self):
        get_dto_class_instance = dto_utils.get_dto_class(self.mappings_module_name)
        self.assertIsInstance(get_dto_class_instance.dto_mapping, dict)
        self.assertGreater(len(get_dto_class_instance.dto_mapping.keys()), 0)

    def mapped_returns_dto_instance(self):
        get_dto_class_instance = dto_utils.get_dto_class(self.mappings_module_name)
        keys = get_dto_class_instance.dto_mapping.keys()
        for key in keys:
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertIsInstance(
                get_dto_class_instance(key),
                (
                    IdDependency,
                    IdReference,
                    PathPropertiesConstraint,
                    PropertyValueConstraint,
                    UniquePropertyValueConstraint,
                ),
            )

    def unmapped_returns_defaultdto(self):
        get_dto_class_instance = dto_utils.get_dto_class(self.mappings_module_name)
        self.assertIsInstance(
            get_dto_class_instance(("dummy", "post")), dto_utils.DefaultDto
        )


if __name__ == "__main__":
    unittest.main()
