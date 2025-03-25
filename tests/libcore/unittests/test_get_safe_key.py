# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore.data_generation.data_generation_core import get_safe_key


class TestGetSafeKey(unittest.TestCase):
    def test_get_safe_key(self) -> None:
        self.assertEqual(get_safe_key("99"), "_99")
        self.assertEqual(get_safe_key("date-time"), "date_time")
        self.assertEqual(get_safe_key("key@value"), "key_value")


if __name__ == "__main__":
    unittest.main()
