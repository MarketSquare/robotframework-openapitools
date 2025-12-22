# pylint: disable="missing-class-docstring", "missing-function-docstring"
import pathlib
import sys
import unittest

from OpenApiLibCore import RelationsMapping
from OpenApiLibCore.data_relations.relations_base import (
    GetIdPropertyName,
    get_id_property_name,
    get_path_mapping_dict,
    get_relations_mapping_dict,
)
from OpenApiLibCore.utils.id_mapping import dummy_transformer

unittest_folder = pathlib.Path(__file__).parent.resolve()
mappings_path = (
    unittest_folder.parent.parent / "user_implemented" / "custom_user_mappings.py"
)


class TestRelationsMapping(unittest.TestCase):
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
        value_relations_mapping_dict = get_relations_mapping_dict("dummy")
        self.assertDictEqual(value_relations_mapping_dict, {})

    def test_valid_mapping(self) -> None:
        value_relations_mapping_dict = get_relations_mapping_dict(
            self.mappings_module_name
        )
        self.assertIsInstance(value_relations_mapping_dict, dict)
        self.assertGreater(len(value_relations_mapping_dict.keys()), 0)

    def test_mapped_returns_relationsmapping_class(self) -> None:
        value_relations_mapping_dict = get_relations_mapping_dict(
            self.mappings_module_name
        )
        keys = value_relations_mapping_dict.keys()
        for key in keys:
            self.assertIsInstance(key, tuple)
            self.assertEqual(len(key), 2)
            self.assertTrue(
                issubclass(value_relations_mapping_dict[key], RelationsMapping)
            )


class TestPathMapping(unittest.TestCase):
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

    def test_no_mapping(self) -> None:
        path_mapping_dict = get_path_mapping_dict("dummy")
        self.assertDictEqual(path_mapping_dict, {})

    def test_valid_mapping(self) -> None:
        path_mapping_dict = get_path_mapping_dict(self.mappings_module_name)
        self.assertIsInstance(path_mapping_dict, dict)
        self.assertGreater(len(path_mapping_dict.keys()), 0)


class TestIdPropertyNameMapping(unittest.TestCase):
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

    def test_no_mapping(self) -> None:
        id_property_name_mapping = get_id_property_name("dummy", "identifier")
        self.assertIsInstance(id_property_name_mapping, GetIdPropertyName)
        self.assertEqual(
            id_property_name_mapping.default_id_property_name, "identifier"
        )
        self.assertDictEqual(id_property_name_mapping.id_mapping, {})

    def test_valid_mapping(self) -> None:
        id_property_name_mapping = get_id_property_name(
            self.mappings_module_name,
            "id",
        )
        self.assertIsInstance(id_property_name_mapping, GetIdPropertyName)
        self.assertEqual(id_property_name_mapping.default_id_property_name, "id")
        self.assertIsInstance(id_property_name_mapping.id_mapping, dict)

        not_mapped = id_property_name_mapping("/secret_message")
        self.assertEqual(not_mapped[0], "id")
        self.assertEqual(not_mapped[1], dummy_transformer)

        default_transformer = id_property_name_mapping("/wagegroups")
        self.assertEqual(default_transformer[0], "wagegroup_id")
        self.assertEqual(default_transformer[1], dummy_transformer)

        custom_transformer = id_property_name_mapping("/wagegroups/{wagegroup_id}")
        self.assertEqual(custom_transformer[0], "wagegroup_id")
        self.assertEqual(custom_transformer[1].__name__, "my_transformer")


if __name__ == "__main__":
    unittest.main()
