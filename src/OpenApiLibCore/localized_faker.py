import datetime
from typing import Callable

import faker


def fake_string(string_format: str) -> str:
    """
    Generate a random string based on the provided format if the format is supported.
    """
    # format names may contain -, which is invalid in Python naming
    string_format = string_format.replace("-", "_")
    fake_generator = getattr(FAKE, string_format, FAKE.uuid)
    value: str = fake_generator()
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%dT%H:%M:%SZ")
    return value


class LocalizedFaker:
    """Class to support setting a locale post-init."""

    # pylint: disable=missing-function-docstring
    def __init__(self) -> None:
        self.fake = faker.Faker()

    def set_locale(self, locale: str | list[str]) -> None:
        """Update the fake attribute with a Faker instance with the provided locale."""
        self.fake = faker.Faker(locale)

    @property
    def date(self) -> Callable[[], str]:
        return self.fake.date

    @property
    def date_time(self) -> Callable[[], datetime.datetime]:
        return self.fake.date_time

    @property
    def password(self) -> Callable[[], str]:
        return self.fake.password

    @property
    def binary(self) -> Callable[[], bytes]:
        return self.fake.binary

    @property
    def email(self) -> Callable[[], str]:
        return self.fake.safe_email

    @property
    def uuid(self) -> Callable[[], str]:
        return self.fake.uuid4

    @property
    def uri(self) -> Callable[[], str]:
        return self.fake.uri

    @property
    def url(self) -> Callable[[], str]:
        return self.fake.url

    @property
    def hostname(self) -> Callable[[], str]:
        return self.fake.hostname

    @property
    def ipv4(self) -> Callable[[], str]:
        return self.fake.ipv4

    @property
    def ipv6(self) -> Callable[[], str]:
        return self.fake.ipv6

    @property
    def name(self) -> Callable[[], str]:
        return self.fake.name

    @property
    def text(self) -> Callable[[], str]:
        return self.fake.text

    @property
    def description(self) -> Callable[[], str]:
        return self.fake.text


FAKE = LocalizedFaker()
