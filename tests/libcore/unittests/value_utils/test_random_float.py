# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest
from sys import float_info
from typing import Any, Dict

from OpenApiLibCore import value_utils

EPSILON = float_info.epsilon


class TestRandomFloat(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema: Dict[str, Any] = {}
        value = value_utils.get_random_float(schema)
        self.assertGreaterEqual(value, -1.0)
        self.assertLessEqual(value, 1.0)

        schema = {"minimum": -2.0}
        value = value_utils.get_random_float(schema)
        self.assertGreaterEqual(value, -2.0)
        self.assertLessEqual(value, -1.0)

        schema = {"maximum": -2.0}
        value = value_utils.get_random_float(schema)
        self.assertGreaterEqual(value, -3.0)
        self.assertLessEqual(value, -2.0)

    def test_exclusive_min_max_oas_3_0(self) -> None:
        schema = {
            "minimum": 1.0 - EPSILON,
            "maximum": 1.0 + EPSILON,
            "exclusiveMinimum": True,
        }
        value = value_utils.get_random_float(schema)
        self.assertAlmostEqual(value, 1.0)

        schema = {
            "minimum": -1.0 - EPSILON,
            "maximum": -1.0 + EPSILON,
            "exclusiveMaximum": True,
        }
        value = value_utils.get_random_float(schema)
        self.assertAlmostEqual(value, -1.0)

    def test_exclusive_min_max_oas_3_1(self) -> None:
        schema = {
            "exclusiveMinimum": 1.0 - EPSILON,
            "maximum": 1.0 + EPSILON,
        }
        value = value_utils.get_random_float(schema)
        self.assertAlmostEqual(value, 1.0)

        schema = {
            "minimum": -1.0 - EPSILON,
            "exclusiveMaximum": -1.0 + EPSILON,
        }
        value = value_utils.get_random_float(schema)
        self.assertAlmostEqual(value, -1.0)

    def test_raises(self) -> None:
        schema = {"minimum": 1.0 + EPSILON, "maximum": 1.0}
        self.assertRaises(ValueError, value_utils.get_random_float, schema)

        schema = {"minimum": -1.0, "maximum": -1.0 - EPSILON}
        self.assertRaises(ValueError, value_utils.get_random_float, schema)

        schema = {"minimum": 1.0, "maximum": 1.0, "exclusiveMinimum": True}
        self.assertRaises(ValueError, value_utils.get_random_float, schema)

        schema = {"minimum": 1.0, "maximum": 1.0, "exclusiveMaximum": True}
        self.assertRaises(ValueError, value_utils.get_random_float, schema)

    def test_min_max(self) -> None:
        schema = {"minimum": 1.1, "maximum": 1.1}
        value = value_utils.get_random_float(schema)
        self.assertEqual(value, 1.1)

        schema = {"minimum": -1.1, "maximum": -1.1}
        value = value_utils.get_random_float(schema)
        self.assertEqual(value, -1.1)

        schema = {"minimum": 2.1, "maximum": 2.2, "exclusiveMinimum": True}
        value = value_utils.get_random_float(schema)
        self.assertGreater(value, 2.1)
        self.assertLess(value, 2.2)

        schema = {"minimum": -0.2, "maximum": -0.1, "exclusiveMaximum": True}
        value = value_utils.get_random_float(schema)
        self.assertGreater(value, -0.2)
        self.assertLess(value, -0.1)


if __name__ == "__main__":
    unittest.main()
