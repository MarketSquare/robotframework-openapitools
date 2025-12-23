# pylint: disable="missing-class-docstring", "missing-function-docstring"
import datetime
import unittest

from OpenApiLibCore.data_generation.localized_faker import LocalizedFaker


class TestLocalizedFaker(unittest.TestCase):
    def test_default_locale(self) -> None:
        default_faker = LocalizedFaker()
        self.assertEqual(default_faker.fake.locales, ["en_US"])

    def test_set_locale(self) -> None:
        faker = LocalizedFaker()

        faker.set_locale("nl_NL")
        self.assertEqual(faker.fake.locales, ["nl_NL"])

        faker.set_locale(["ar_AA", "zh_TW"])
        self.assertEqual(faker.fake.locales, ["ar_AA", "zh_TW"])

    def test_custom_provider_types(self) -> None:
        faker = LocalizedFaker()

        self.assertIsInstance(faker.date(), str)
        self.assertIsInstance(faker.date_time(), datetime.datetime)
        self.assertIsInstance(faker.password(), str)
        self.assertIsInstance(faker.binary(), bytes)
        self.assertIsInstance(faker.email(), str)
        self.assertIsInstance(faker.uuid(), str)
        self.assertIsInstance(faker.uri(), str)
        self.assertIsInstance(faker.url(), str)
        self.assertIsInstance(faker.hostname(), str)
        self.assertIsInstance(faker.ipv4(), str)
        self.assertIsInstance(faker.ipv6(), str)
        self.assertIsInstance(faker.name(), str)
        self.assertIsInstance(faker.text(), str)
        self.assertIsInstance(faker.description(), str)


if __name__ == "__main__":
    unittest.main()
