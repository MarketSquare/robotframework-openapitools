from typing import Generator


def remove_unsafe_characters_from_string(string: str) -> str:
    def _remove_unsafe_characters_from_string(
        string: str,
    ) -> Generator[str, None, None]:
        string_iterator = iter(string)
        capitalize_next_character = False

        for character in string_iterator:
            if character.isalpha():
                yield character
                break

        for character in string_iterator:
            if character.isalnum():
                if capitalize_next_character:
                    capitalize_next_character = False
                yield character

            elif not capitalize_next_character:
                capitalize_next_character = True
                yield "_"

    return "".join(_remove_unsafe_characters_from_string(string=string))
