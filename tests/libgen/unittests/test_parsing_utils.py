import unittest

from openapi_libgen.parsing_utils import remove_unsafe_characters_from_string


class TestRemoveUnsafeCharactersFromString(unittest.TestCase):
    def test_first_char_isalpha(self) -> None:
        lower_alpha = "alpha"
        result = remove_unsafe_characters_from_string(lower_alpha)
        self.assertEqual(result, lower_alpha)

        caps_alpha = "ALPHA"
        result = remove_unsafe_characters_from_string(caps_alpha)
        self.assertEqual(result, caps_alpha)

    def test_first_char_isnum(self) -> None:
        the_answer = "42"
        result = remove_unsafe_characters_from_string(the_answer)
        self.assertEqual(result, f"_{the_answer}")

    def test_starts_with_underscore(self) -> None:
        private_answer = "_42"
        result = remove_unsafe_characters_from_string(private_answer)
        self.assertEqual(result, private_answer)

    def test_empty_string(self) -> None:
        empty = ""
        result = remove_unsafe_characters_from_string(empty)
        self.assertEqual(result, "_")

    def test_non_alnum(self) -> None:
        questionable = "???"
        result = remove_unsafe_characters_from_string(questionable)
        self.assertEqual(result, "_")

    def test_capitalize_next_alpha_after_removed_char(self) -> None:
        path = "my/path/part?2a"
        result = remove_unsafe_characters_from_string(path)
        self.assertEqual(result, "my_Path_Part_2a")

    def test_whitespace_is_stripped(self) -> None:
        description = "\tAdd a new user\n\r"
        result = remove_unsafe_characters_from_string(description)
        self.assertEqual(result, "Add_A_New_User")

    def test_trailing_underscore_is_stripped(self) -> None:
        description = "Add a new user."
        result = remove_unsafe_characters_from_string(description)
        self.assertEqual(result, "Add_A_New_User")


if __name__ == "__main__":
    unittest.main()
