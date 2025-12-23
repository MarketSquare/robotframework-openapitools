# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore.utils.parameter_utils import (
    get_oas_name_from_safe_name,
    get_safe_name_for_oas_name,
)


class TestParameterUtils(unittest.TestCase):
    def test_get_safe_name_for_oas_name(self) -> None:
        self.assertEqual(get_safe_name_for_oas_name("safe"), "safe")
        self.assertEqual(get_safe_name_for_oas_name("99"), "_99")
        self.assertEqual(get_safe_name_for_oas_name("#unsafe"), "_unsafe")
        self.assertEqual(get_safe_name_for_oas_name("date-time"), "date_time")
        self.assertEqual(get_safe_name_for_oas_name("@key@value"), "_key_value")
        self.assertEqual(get_safe_name_for_oas_name("@key#value"), "_64_key_35_value")
        self.assertEqual(get_safe_name_for_oas_name("@key#value"), "_64_key_35_value")
        self.assertEqual(get_safe_name_for_oas_name("!"), "_")

    def test_get_oas_name_from_safe_name(self) -> None:
        with self.assertRaises(ValueError):
            _ = get_oas_name_from_safe_name("self")

        safe_name = get_safe_name_for_oas_name("id")
        self.assertEqual(get_oas_name_from_safe_name(safe_name=safe_name), "id")


if __name__ == "__main__":
    unittest.main()
