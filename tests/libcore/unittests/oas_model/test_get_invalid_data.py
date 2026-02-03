# pylint: disable="missing-class-docstring", "missing-function-docstring"
# pyright: reportArgumentType=false
import unittest

from OpenApiLibCore import PropertyValueConstraint, RelationsMapping, ResourceRelation
from OpenApiLibCore.models.oas_models import ArraySchema, IntegerSchema


class ArrayConstraint(RelationsMapping):
    @staticmethod
    def get_relations() -> list[ResourceRelation]:
        relations: list[ResourceRelation] = [
            PropertyValueConstraint(
                property_name="something",
                values=[24, 42],
                invalid_value=33,
                invalid_value_error_code=422,
            ),
        ]
        return relations


class TestArraySchema(unittest.TestCase):
    def test_raises_for_no_matching_status_code(self) -> None:
        schema = ArraySchema(items=IntegerSchema())
        schema.attach_relations_mapping(ArrayConstraint)
        with self.assertRaises(ValueError) as context:
            _ = schema.get_invalid_data(
                valid_data=[42],
                status_code=500,
                invalid_property_default_code=422,
            )
        self.assertEqual(
            str(context.exception),
            "No constraint can be broken to cause status_code 500",
        )

    def test_status_code_is_default_code_without_constraints_raises(self) -> None:
        schema = ArraySchema(items=IntegerSchema(maximum=43))
        schema.attach_relations_mapping(RelationsMapping)
        with self.assertRaises(ValueError) as context:
            _ = schema.get_invalid_data(
                valid_data=[42],
                status_code=422,
                invalid_property_default_code=422,
            )
        self.assertEqual(
            str(context.exception),
            "No constraint can be broken to cause status_code 422",
        )

    def test_status_code_is_default_code(self) -> None:
        schema = ArraySchema(items=IntegerSchema(maximum=43), minItems=1)
        schema.attach_relations_mapping(RelationsMapping)
        invalid_data = schema.get_invalid_data(
            valid_data=[42],
            status_code=422,
            invalid_property_default_code=422,
        )
        self.assertEqual(invalid_data, [])

        valid_value = [42]
        schema = ArraySchema(items=IntegerSchema(maximum=43), const=valid_value)
        schema.attach_relations_mapping(RelationsMapping)
        invalid_data = schema.get_invalid_data(
            valid_data=valid_value,
            status_code=422,
            invalid_property_default_code=422,
        )
        self.assertNotEqual(invalid_data, valid_value)


if __name__ == "__main__":
    unittest.main()
