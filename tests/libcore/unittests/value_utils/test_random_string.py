# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore import value_utils


class TestRandomString(unittest.TestCase):
    def test_default_min_max(self) -> None:
        schema = {"maxLength": 0}
        value = value_utils.get_random_string(schema)
        self.assertEqual(value, "")

        schema = {"minLength": 36}
        value = value_utils.get_random_string(schema)
        self.assertEqual(len(value), 36)

    def test_min_max(self) -> None:
        schema = {"minLength": 42, "maxLength": 42}
        value = value_utils.get_random_string(schema)
        self.assertEqual(len(value), 42)

        schema = {"minLength": 42}
        value = value_utils.get_random_string(schema)
        self.assertEqual(len(value), 42)

    def test_datetime(self) -> None:
        schema = {"format": "date-time"}
        value = value_utils.get_random_string(schema)
        matcher = r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d*)?)((-(\d{2}):(\d{2})|Z)?)$"
        self.assertRegex(value, matcher)

    def test_pattern(self) -> None:
        pattern = r"^[1-9][0-9]{3} ?(?!sa|sd|ss|SA|SD|SS)[A-Za-z]{2}$"
        schema = {"pattern": pattern}
        value = value_utils.get_random_string(schema)
        self.assertRegex(value, pattern)

    def test_byte(self) -> None:
        schema = {"format": "byte"}
        value = value_utils.get_random_string(schema)
        self.assertIsInstance(value, bytes)


if __name__ == "__main__":
    unittest.main()
