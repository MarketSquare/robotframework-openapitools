from typing import Any, overload


@overload
def dummy_transformer(valid_id: str) -> str: ...  # pragma: no cover


@overload
def dummy_transformer(valid_id: int) -> int: ...  # pragma: no cover


def dummy_transformer(valid_id: Any) -> Any:
    return valid_id
