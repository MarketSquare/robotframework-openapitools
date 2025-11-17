from typing import Generator


def remove_unsafe_characters_from_string(unsafe_string: str) -> str:
    def _remove_unsafe_characters_from_string(
        string_: str,
    ) -> Generator[str, None, None]:
        string_iterator = iter(string_)
        capitalize_next_character = False

        # The first character must be A-z or _
        first_character = next(string_iterator, "_")
        if first_character.isalpha() or first_character == "_":
            yield first_character
        elif first_character.isnumeric():
            yield "_" + first_character

        for character in string_iterator:
            if character.isalnum():
                if capitalize_next_character:
                    capitalize_next_character = False
                    yield character.upper()
                else:
                    yield character

            elif not capitalize_next_character:
                capitalize_next_character = True
                yield "_"

    unsafe_string = unsafe_string.strip()
    safe_string = "".join(_remove_unsafe_characters_from_string(string_=unsafe_string))
    without_trailing_underscore = safe_string.rstrip("_")
    return without_trailing_underscore or "_"
