# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest
from typing import Any, Dict

from OpenApiLibCore import value_utils


class TestRandomArray(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema: Dict[str, Any] = {"items": {"type": "string"}}
        value = value_utils.get_random_array(schema)
        self.assertEqual(len(value), 1)

        schema = {"maxItems": 0, "items": {"type": "string"}}
        value = value_utils.get_random_array(schema)
        self.assertEqual(value, [])

    def test_min_max(self) -> None:
        schema = {"maxItems": 3, "items": {"type": "string"}}
        value = value_utils.get_random_array(schema)
        self.assertEqual(len(value), 3)

        schema = {"minItems": 5, "items": {"type": "string"}}
        value = value_utils.get_random_array(schema)
        self.assertEqual(len(value), 5)

        schema = {"minItems": 7, "maxItems": 5, "items": {"type": "string"}}
        value = value_utils.get_random_array(schema)
        self.assertEqual(len(value), 7)


if __name__ == "__main__":
    unittest.main()
