# pylint: disable="missing-class-docstring", "missing-function-docstring"
import unittest

from OpenApiLibCore.models.oas_models import (
    BooleanSchema,
    IntegerSchema,
    StringSchema,
)


class TestGetInvalidValue(unittest.TestCase):
    def test_value_error_handling(self) -> None:
        values_from_constraints = [True, False]
        schema = BooleanSchema()
        invalid_value = schema.get_invalid_value(
            valid_value=True, values_from_constraint=values_from_constraints
        )
        self.assertIsInstance(invalid_value, str)

    def test_out_of_bounds(self) -> None:
        schema = StringSchema(maxLength=3)
        invalid_value = schema.get_invalid_value(valid_value="x")
        self.assertIsInstance(invalid_value, (str, list))
        if isinstance(invalid_value, str):
            self.assertTrue(len(invalid_value) > 3)
        else:
            self.assertEqual(
                invalid_value, [{"invalid": [None, False]}, "null", None, True]
            )

        schema = IntegerSchema(minimum=5)
        invalid_value = schema.get_invalid_value(valid_value=7)
        self.assertIsInstance(invalid_value, (int, str))
        if isinstance(invalid_value, int):
            self.assertTrue(invalid_value < 5)


if __name__ == "__main__":
    unittest.main()
