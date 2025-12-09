class Ignore:
    """Helper class to flag properties to be ignored in data generation."""

    def __str__(self) -> str:
        return "IGNORE"  # pragma: no cover


class UnSet:
    """Helper class to flag arguments that have not been set in a keyword call."""

    def __str__(self) -> str:
        return "UNSET"  # pragma: no cover


IGNORE = Ignore()

UNSET = UnSet()
