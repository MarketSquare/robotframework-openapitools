from __future__ import annotations

import builtins
from abc import abstractmethod
from collections import ChainMap
from copy import deepcopy
from functools import cached_property
from random import choice, randint, sample, shuffle, uniform
from sys import float_info
from typing import (
    Annotated,
    Any,
    Callable,
    Generator,
    Generic,
    Iterable,
    Literal,
    Mapping,
    TypeAlias,
    TypeGuard,
    TypeVar,
    Union,
    cast,
)
from uuid import uuid4

import rstr
from pydantic import BaseModel, Field, RootModel
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.data_constraints.dto_base import Dto
from OpenApiLibCore.data_generation.localized_faker import FAKE, fake_string
from OpenApiLibCore.data_generation.value_utils import (
    json_type_name_of_python_type,
    python_type_by_json_type_name,
)
from OpenApiLibCore.models import IGNORE, Ignore
from OpenApiLibCore.models.resource_relations import (
    NOT_SET,
    IdDependency,
    PropertyValueConstraint,
)
from OpenApiLibCore.protocols import ConstraintMappingType
from OpenApiLibCore.utils.id_mapping import dummy_transformer
from OpenApiLibCore.utils.parameter_utils import get_safe_name_for_oas_name

run_keyword = BuiltIn().run_keyword

EPSILON = float_info.epsilon

SENTINEL = object()

O = TypeVar("O")
AI = TypeVar("AI", bound=JSON)


def is_object_schema(schema: SchemaObjectTypes) -> TypeGuard[ObjectSchema]:
    return isinstance(schema, ObjectSchema)


class SchemaBase(BaseModel, Generic[O], frozen=True):
    readOnly: bool = False
    writeOnly: bool = False
    constraint_mapping: ConstraintMappingType = Dto  # type: ignore[assignment]

    @abstractmethod
    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[O, SchemaObjectTypes]: ...

    @abstractmethod
    def get_values_out_of_bounds(self, current_value: O) -> list[O]: ...

    @abstractmethod
    def get_invalid_value_from_const_or_enum(self) -> O: ...

    @abstractmethod
    def get_invalid_value_from_constraint(self, values_from_constraint: list[O]) -> O:
        """
        Return a value of the same type as the values in the values_from_constraints that
        is not in the values_from_constraints, if possible. Otherwise raise ValueError.
        """

    def get_invalid_value(
        self,
        valid_value: O,
        values_from_constraint: Iterable[O] = tuple(),
    ) -> O | str | list[JSON] | Ignore:
        """Return a random value that violates the provided value_schema."""
        invalid_values: list[O | str | list[JSON] | Ignore] = []
        value_type = getattr(self, "type")

        if not isinstance(valid_value, python_type_by_json_type_name(value_type)):
            valid_value = self.get_valid_value()[0]

        if values_from_constraint:
            # if IGNORE is in the values_from_constraints, the parameter needs to be
            # ignored for an OK response so leaving the value at it's original value
            # should result in the specified error response
            if any(map(lambda x: isinstance(x, Ignore), values_from_constraint)):
                return IGNORE
            try:
                return self.get_invalid_value_from_constraint(
                    values_from_constraint=list(values_from_constraint),
                )
            except ValueError:
                pass

        # For schemas with a const or enum, add invalidated values from those
        try:
            invalid_value = self.get_invalid_value_from_const_or_enum()
            invalid_values.append(invalid_value)
        except ValueError:
            pass

        # Violate min / max values or length if possible
        try:
            values_out_of_bounds = self.get_values_out_of_bounds(
                current_value=valid_value
            )
            invalid_values += values_out_of_bounds
        except ValueError:
            pass

        # No value constraints or min / max ranges to violate, so change the data type
        if value_type == "string":
            # Since int / float / bool can always be cast to sting, change
            # the string to a nested object.
            # An array gets exploded in query strings, "null" is then often invalid
            invalid_values.append([{"invalid": [None, False]}, "null", None, True])
        else:
            invalid_values.append(FAKE.uuid())

        return choice(invalid_values)

    def attach_constraint_mapping(
        self, constraint_mapping: ConstraintMappingType
    ) -> None:
        # NOTE: https://github.com/pydantic/pydantic/issues/11495
        self.__dict__["constraint_mapping"] = constraint_mapping


class NullSchema(SchemaBase[None], frozen=True):
    type: Literal["null"] = "null"
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[None, NullSchema]:
        return None, self

    def get_values_out_of_bounds(self, current_value: None) -> list[None]:
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> None:
        raise ValueError

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[None]
    ) -> None:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return False

    @property
    def annotation_string(self) -> str:
        return "None"

    @property
    def python_type(self) -> builtins.type:
        return type(None)


class BooleanSchema(SchemaBase[bool], frozen=True):
    type: Literal["boolean"] = "boolean"
    const: bool | None = None
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[bool, BooleanSchema]:
        if self.const is not None:
            return self.const, self
        return choice([True, False]), self

    def get_values_out_of_bounds(self, current_value: bool) -> list[bool]:
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> bool:
        if self.const is not None:
            return not self.const
        raise ValueError

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[bool]
    ) -> bool:
        if len(values_from_constraint) == 1:
            return not values_from_constraint[0]
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "bool"

    @property
    def python_type(self) -> builtins.type:
        return bool


class StringSchema(SchemaBase[str], frozen=True):
    type: Literal["string"] = "string"
    format: str = ""
    pattern: str = ""
    maxLength: int | None = None
    minLength: int | None = None
    const: str | None = None
    enum: list[str] | None = None
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[str, StringSchema]:
        """Generate a random string within the min/max length in the schema, if specified."""
        if self.const is not None:
            return self.const, self
        if self.enum is not None:
            return choice(self.enum), self
        # if a pattern is provided, format and min/max length can be ignored
        if pattern := self.pattern:
            try:
                return rstr.xeger(pattern), self
            except Exception as exception:
                logger.warn(
                    f"An error occured trying to generate a string matching the "
                    f"pattern defined in the specification. To ensure a valid value "
                    f"is generated for this property, a PropertyValueConstraint can be "
                    f"configured. See the Advanced Use section of the OpenApiTools "
                    f"documentation for more details."
                    f"\nThe exception was: {exception}\nThe pattern was: {pattern}"
                )
        minimum = self.minLength if self.minLength is not None else 0
        maximum = self.maxLength if self.maxLength is not None else 36
        maximum = max(minimum, maximum)

        format_ = self.format if self.format else "uuid"
        value = fake_string(string_format=format_)
        while len(value) < minimum:
            value = value + fake_string(string_format=format_)
        if len(value) > maximum:
            value = value[:maximum]
        return value, self

    def get_values_out_of_bounds(self, current_value: str) -> list[str]:
        invalid_values: list[str] = []
        if self.minLength:
            invalid_values.append(current_value[0 : self.minLength - 1])
        # if there is a maximum length, send 1 character more
        if self.maxLength:
            invalid_value = current_value if current_value else "x"
            # add random characters from the current value to prevent adding new characters
            while len(invalid_value) <= self.maxLength:
                invalid_value += choice(invalid_value)
            invalid_values.append(invalid_value)
        if invalid_values:
            return invalid_values
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> str:
        valid_values = []
        if self.const is not None:
            valid_values = [self.const]
        if self.enum is not None:
            valid_values = self.enum

        if not valid_values:
            raise ValueError

        invalid_value = ""
        for value in valid_values:
            invalid_value += value + value

        return invalid_value

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[str]
    ) -> str:
        invalid_values = 2 * values_from_constraint
        invalid_value = invalid_values.pop()
        for value in invalid_values:
            invalid_value = invalid_value + value

        if not invalid_value:
            raise ValueError("Value invalidation yielded an empty string.")
        return invalid_value

    @property
    def can_be_invalidated(self) -> bool:
        if (
            self.maxLength is not None
            or self.minLength is not None
            or self.const is not None
            or self.enum is not None
        ):
            return True
        return False

    @property
    def annotation_string(self) -> str:
        return "str"

    @property
    def python_type(self) -> builtins.type:
        return str


class IntegerSchema(SchemaBase[int], frozen=True):
    type: Literal["integer"] = "integer"
    format: str = "int32"
    maximum: int | None = None
    exclusiveMaximum: int | bool | None = None
    minimum: int | None = None
    exclusiveMinimum: int | bool | None = None
    multipleOf: int | None = None  # TODO: implement support
    const: int | None = None
    enum: list[int] | None = None
    nullable: bool = False

    @cached_property
    def _max_int(self) -> int:
        if self.format == "int64":
            return 9223372036854775807
        return 2147483647

    @cached_property
    def _min_int(self) -> int:
        if self.format == "int64":
            return -9223372036854775808
        return -2147483648

    @cached_property
    def _max_value(self) -> int:
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer
        if isinstance(self.exclusiveMaximum, int) and not isinstance(
            self.exclusiveMaximum, bool
        ):
            return self.exclusiveMaximum - 1

        if isinstance(self.maximum, int):
            if self.exclusiveMaximum is True:
                return self.maximum - 1
            return self.maximum

        return self._max_int

    @cached_property
    def _min_value(self) -> int:
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer
        if isinstance(self.exclusiveMinimum, int) and not isinstance(
            self.exclusiveMinimum, bool
        ):
            return self.exclusiveMinimum + 1

        if isinstance(self.minimum, int):
            if self.exclusiveMinimum is True:
                return self.minimum + 1
            return self.minimum

        return self._min_int

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[int, IntegerSchema]:
        """Generate a random int within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const, self
        if self.enum is not None:
            return choice(self.enum), self

        return randint(self._min_value, self._max_value), self

    def get_values_out_of_bounds(self, current_value: int) -> list[int]:  # pylint: disable=unused-argument
        invalid_values: list[int] = []

        if self._min_value > self._min_int:
            invalid_values.append(self._min_value - 1)

        if self._max_value < self._max_int:
            invalid_values.append(self._max_value + 1)

        if invalid_values:
            return invalid_values

        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> int:
        valid_values = []
        if self.const is not None:
            valid_values = [self.const]
        if self.enum is not None:
            valid_values = self.enum

        if not valid_values:
            raise ValueError

        invalid_value = 0
        for value in valid_values:
            invalid_value += abs(value) + abs(value)

        return invalid_value

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[int]
    ) -> int:
        invalid_values = 2 * values_from_constraint
        invalid_value = invalid_values.pop()
        for value in invalid_values:
            invalid_value = abs(invalid_value) + abs(value)
        if not invalid_value:
            invalid_value += 1
        return invalid_value

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "int"

    @property
    def python_type(self) -> builtins.type:
        return int


class NumberSchema(SchemaBase[float], frozen=True):
    type: Literal["number"] = "number"
    maximum: int | float | None = None
    exclusiveMaximum: int | float | bool | None = None
    minimum: int | float | None = None
    exclusiveMinimum: int | float | bool | None = None
    multipleOf: int | None = None  # TODO: implement support
    const: int | float | None = None
    enum: list[int | float] | None = None
    nullable: bool = False

    @cached_property
    def _max_float(self) -> float:
        return 9223372036854775807.0

    @cached_property
    def _min_float(self) -> float:
        return -9223372036854775808.0

    @cached_property
    def _max_value(self) -> float:
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer or a float
        if isinstance(self.exclusiveMaximum, (int, float)) and not isinstance(
            self.exclusiveMaximum, bool
        ):
            return self.exclusiveMaximum - 0.0000000001

        if isinstance(self.maximum, (int, float)):
            if self.exclusiveMaximum is True:
                return self.maximum - 0.0000000001
            return self.maximum

        return self._max_float

    @cached_property
    def _min_value(self) -> float:
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer or a float
        if isinstance(self.exclusiveMinimum, (int, float)) and not isinstance(
            self.exclusiveMinimum, bool
        ):
            return self.exclusiveMinimum + 0.0000000001

        if isinstance(self.minimum, (int, float)):
            if self.exclusiveMinimum is True:
                return self.minimum + 0.0000000001
            return self.minimum

        return self._min_float

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[float, NumberSchema]:
        """Generate a random float within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const, self
        if self.enum is not None:
            return choice(self.enum), self

        return uniform(self._min_value, self._max_value), self

    def get_values_out_of_bounds(self, current_value: float) -> list[float]:  # pylint: disable=unused-argument
        invalid_values: list[float] = []

        if self._min_value > self._min_float:
            invalid_values.append(self._min_value - 0.000000001)

        if self._max_value < self._max_float:
            invalid_values.append(self._max_value + 0.000000001)

        if invalid_values:
            return invalid_values

        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> float:
        valid_values = []
        if self.const is not None:
            valid_values = [self.const]
        if self.enum is not None:
            valid_values = self.enum

        if not valid_values:
            raise ValueError

        invalid_value = 0.0
        for value in valid_values:
            invalid_value += abs(value) + abs(value)

        return invalid_value

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[float]
    ) -> float:
        invalid_values = 2 * values_from_constraint
        invalid_value = invalid_values.pop()
        for value in invalid_values:
            invalid_value = abs(invalid_value) + abs(value)
        if not invalid_value:
            invalid_value += 1
        return invalid_value

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "float"

    @property
    def python_type(self) -> builtins.type:
        return float


class ArraySchema(SchemaBase[list[AI]], frozen=True):
    type: Literal["array"] = "array"
    items: SchemaObjectTypes
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool = False
    const: list[AI] | None = None
    enum: list[list[AI]] | None = None
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[list[AI], ArraySchema[AI]]:
        if self.const is not None:
            return self.const, self

        if self.enum is not None:
            return choice(self.enum), self

        minimum = self.minItems if self.minItems is not None else 0
        maximum = self.maxItems if self.maxItems is not None else 1
        maximum = max(minimum, maximum)

        value: list[AI] = []
        number_of_items_to_generate = randint(minimum, maximum)
        for _ in range(number_of_items_to_generate):
            item_value = cast("AI", self.items.get_valid_value()[0])
            value.append(item_value)
        return value, self

    def get_values_out_of_bounds(self, current_value: list[AI]) -> list[list[AI]]:
        invalid_values: list[list[AI]] = []

        if self.minItems:
            invalid_value = current_value[0 : self.minItems - 1]
            invalid_values.append(invalid_value)

        if self.maxItems is not None:
            invalid_value = []
            if not current_value:
                current_value = self.get_valid_value()[0]

            if not current_value:
                current_value = [self.items.get_valid_value()[0]]  # type: ignore[list-item]

            while len(invalid_value) <= self.maxItems:
                invalid_value.append(choice(current_value))
            invalid_values.append(invalid_value)

        if invalid_values:
            return invalid_values

        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> list[AI]:
        valid_values = []
        if self.const is not None:
            valid_values = [self.const]
        if self.enum is not None:
            valid_values = self.enum

        if not valid_values:
            raise ValueError

        invalid_value = []
        for value in valid_values:
            invalid_value.extend(value)
            invalid_value.extend(value)

        return invalid_value

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[list[AI]]
    ) -> list[AI]:
        values_from_constraint = deepcopy(values_from_constraint)

        valid_array = values_from_constraint.pop()
        invalid_array: list[AI] = []
        for value in valid_array:
            invalid_value = self.items.get_invalid_value_from_constraint(
                values_from_constraint=[value],  # type: ignore[list-item]
            )
            invalid_array.append(invalid_value)  # type: ignore[arg-type]
        return invalid_array

    def get_invalid_data(
        self,
        valid_data: list[AI],
        status_code: int,
        invalid_property_default_code: int,
    ) -> list[AI]:
        """Return a data set with one of the properties set to an invalid value or type."""
        invalid_values: list[list[AI]] = []

        relations = self.constraint_mapping.get_body_relations_for_error_code(
            error_code=status_code
        )
        # TODO: handle relations applicable to arrays / lists

        if status_code == invalid_property_default_code:
            try:
                values_out_of_bounds = self.get_values_out_of_bounds(
                    current_value=valid_data
                )
                invalid_values.extend(values_out_of_bounds)
            except ValueError:
                pass
            try:
                invalid_const_or_enum = self.get_invalid_value_from_const_or_enum()
                invalid_values.append(invalid_const_or_enum)
            except ValueError:
                pass
            if is_object_schema(self.items):
                data_to_invalidate = deepcopy(valid_data)
                valid_item = (
                    data_to_invalidate.pop()
                    if valid_data
                    else self.items.get_valid_value()[0]
                )
                invalid_item = self.items.get_invalid_data(
                    valid_data=valid_item,  # type: ignore[arg-type]
                    status_code=status_code,
                    invalid_property_default_code=invalid_property_default_code,
                )
                invalid_data = [*data_to_invalidate, invalid_item]
                invalid_values.append(invalid_data)

        if not invalid_values:
            raise ValueError(
                f"No constraint can be broken to cause status_code {status_code}"
            )
        return choice(invalid_values)

    @property
    def can_be_invalidated(self) -> bool:
        if (
            self.maxItems is not None
            or self.minItems is not None
            or self.uniqueItems
            or self.const is not None
            or self.enum is not None
        ):
            return True
        if isinstance(self.items, (BooleanSchema, IntegerSchema, NumberSchema)):
            return True
        return False

    @property
    def annotation_string(self) -> str:
        return f"list[{self.items.annotation_string}]"

    @property
    def python_type(self) -> builtins.type:
        return list


# NOTE: Workaround for cyclic PropertiesMapping / SchemaObjectTypes annotations
def _get_properties_mapping_default() -> PropertiesMapping:
    return _get_empty_properties_mapping()


class ObjectSchema(SchemaBase[dict[str, JSON]], frozen=True):
    type: Literal["object"] = "object"
    properties: PropertiesMapping = Field(
        default_factory=_get_properties_mapping_default
    )
    additionalProperties: SchemaObjectTypes | bool = True
    required: list[str] = []
    maxProperties: int | None = None
    minProperties: int | None = None
    const: dict[str, JSON] | None = None
    enum: list[dict[str, JSON]] | None = None
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[dict[str, JSON], ObjectSchema]:
        if self.const is not None:
            return self.const, self

        if self.enum is not None:
            return choice(self.enum), self

        json_data: dict[str, Any] = {}

        property_names = self._get_property_names_to_process()

        for property_name in property_names:
            property_schema = self.properties.root[property_name]
            if property_schema.readOnly:
                continue

            json_data[property_name] = self._get_data_for_property(
                property_name=property_name,
                property_schema=property_schema,
                operation_id=operation_id,
            )

        return json_data, self

    def _get_property_names_to_process(self) -> list[str]:
        property_names = []

        properties = {} if self.properties is None else self.properties.root
        for property_name in properties:
            # register the oas_name
            _ = get_safe_name_for_oas_name(property_name)
            if constrained_values := self._get_constrained_values(
                property_name=property_name
            ):
                # do not add properties that are configured to be ignored
                if IGNORE in constrained_values:  # type: ignore[comparison-overlap]
                    continue
            property_names.append(property_name)

        max_properties = self.maxProperties
        if max_properties and len(property_names) > max_properties:
            required_properties = self.required
            number_of_optional_properties = max_properties - len(required_properties)
            optional_properties = [
                name for name in property_names if name not in required_properties
            ]
            selected_optional_properties = sample(
                optional_properties, number_of_optional_properties
            )
            property_names = required_properties + selected_optional_properties

        return property_names

    def _get_data_for_property(
        self,
        property_name: str,
        property_schema: SchemaObjectTypes,
        operation_id: str | None,
    ) -> JSON:
        if constrained_values := self._get_constrained_values(
            property_name=property_name
        ):
            constrained_value = choice(constrained_values)
            # Check if the chosen value is a nested constraint_mapping; since a
            # mapping is never instantiated, we can use isinstance(..., type) for this.
            if isinstance(constrained_value, type):
                property_schema.attach_constraint_mapping(constrained_value)
                valid_value, _ = property_schema.get_valid_value(
                    operation_id=operation_id
                )
                return valid_value

            return constrained_value

        if (
            dependent_id := get_dependent_id(
                constraint_mapping=self.constraint_mapping,
                property_name=property_name,
                operation_id=operation_id,
            )
        ) is not None:
            return dependent_id

        # Constraints are mapped to endpoints; they are not attached to the property
        # value schemas so update the schema before value generation
        property_schema.attach_constraint_mapping(self.constraint_mapping)
        return property_schema.get_valid_value(operation_id=operation_id)[0]

    def _get_constrained_values(
        self, property_name: str
    ) -> list[JSON | ConstraintMappingType]:
        relations = self.constraint_mapping.get_relations()
        values_list = [
            c.values
            for c in relations
            if (
                isinstance(c, PropertyValueConstraint)
                and c.property_name == property_name
            )
        ]
        # values should be empty or contain 1 list of allowed values
        return values_list.pop() if values_list else []

    def get_values_out_of_bounds(
        self, current_value: Mapping[str, JSON]
    ) -> list[dict[str, JSON]]:
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> dict[str, JSON]:
        valid_values = []
        if self.const is not None:
            valid_values = [self.const]
        if self.enum is not None:
            valid_values = self.enum

        if not valid_values:
            raise ValueError

        # This invalidation will not work for a const and may not work for
        # an enum. In that case a different invalidation approach will be used.
        invalid_value = {**valid_values[0]}
        for value in valid_values:
            for key in invalid_value.keys():
                invalid_value[key] = value.get(key)
                if invalid_value not in valid_values:
                    return invalid_value

        raise ValueError

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[dict[str, JSON]]
    ) -> dict[str, JSON]:
        values_from_constraint = deepcopy(values_from_constraint)

        valid_object = values_from_constraint.pop()
        invalid_object: dict[str, JSON] = {}
        for key, value in valid_object.items():
            python_type_of_value = type(value)
            json_type_of_value = json_type_name_of_python_type(python_type_of_value)
            schema = MediaTypeObject(schema={"type": json_type_of_value}).schema_  # pyright: ignore[reportArgumentType]
            invalid_value = schema.get_invalid_value_from_constraint(  # type: ignore[union-attr]
                values_from_constraint=[value],  # type: ignore[list-item]
            )
            invalid_object[key] = invalid_value
        return invalid_object

    def get_invalid_data(
        self,
        valid_data: dict[str, JSON],
        status_code: int,
        invalid_property_default_code: int,
    ) -> dict[str, JSON]:
        """Return a data set with one of the properties set to an invalid value or type."""
        properties: dict[str, JSON] = deepcopy(valid_data)

        relations = self.constraint_mapping.get_body_relations_for_error_code(
            error_code=status_code
        )
        property_names = [r.property_name for r in relations]

        if status_code == invalid_property_default_code:
            # add all properties defined in the schema, including optional properties
            property_names.extend((self.properties.root.keys()))
        if not property_names:
            raise ValueError(
                f"No property can be invalidated to cause status_code {status_code}"
            )
        # Remove duplicates, then shuffle the property_names so different properties in
        # the data dict are invalidated when rerunning the test.
        shuffle(list(set(property_names)))
        # The value of 1 property will be changed and since they are shuffled, take the first
        property_name = property_names[0]
        # if possible, invalidate a constraint but send otherwise valid data
        id_dependencies = [
            r
            for r in relations
            if isinstance(r, IdDependency) and r.property_name == property_name
        ]
        if id_dependencies:
            invalid_id = uuid4().hex
            logger.debug(
                f"Breaking IdDependency for status_code {status_code}: setting "
                f"{property_name} to {invalid_id}"
            )
            properties[property_name] = invalid_id
            return properties

        invalid_value_from_constraint = [
            r.invalid_value
            for r in relations
            if isinstance(r, PropertyValueConstraint)
            and r.property_name == property_name
            and r.invalid_value_error_code == status_code
        ]
        if (
            invalid_value_from_constraint
            and invalid_value_from_constraint[0] is not NOT_SET
        ):
            invalid_value = invalid_value_from_constraint[0]
            if isinstance(invalid_value, Ignore):
                properties.pop(property_name)
                logger.debug(
                    f"Property {property_name} removed since the invalid_value "
                    f"was IGNORE (received from get_invalid_value)"
                )
            else:
                properties[property_name] = invalid_value
                logger.debug(
                    f"Using invalid_value {invalid_value_from_constraint[0]} to "
                    f"invalidate property {property_name}"
                )
            return properties

        value_schema = self.properties.root[property_name]
        if isinstance(value_schema, UnionTypeSchema):
            # Filter "type": "null" from the possible types since this indicates an
            # optional / nullable property that can only be invalidated by sending
            # invalid data of a non-null type
            non_null_schemas = [
                s
                for s in value_schema.resolved_schemas
                if not isinstance(s, NullSchema)
            ]
            value_schema = choice(non_null_schemas)

        # there may not be a current_value when invalidating an optional property
        current_value = properties.get(property_name, SENTINEL)
        if current_value is SENTINEL:
            current_value = value_schema.get_valid_value()[0]

        values_from_constraint = [
            r.values[0]
            for r in relations
            if isinstance(r, PropertyValueConstraint)
            and r.property_name == property_name
        ]

        invalid_value = value_schema.get_invalid_value(
            valid_value=current_value,  # type: ignore[arg-type]
            values_from_constraint=values_from_constraint,
        )
        if isinstance(invalid_value, Ignore):
            properties.pop(property_name)
            logger.debug(
                f"Property {property_name} removed since the invalid_value "
                f"was IGNORE (received from get_invalid_value)"
            )
        else:
            properties[property_name] = invalid_value
            logger.debug(
                f"Property {property_name} changed to {invalid_value} "
                f"(received from get_invalid_value)"
            )
        return properties

    def contains_properties(self, property_names: list[str]) -> bool:
        if self.properties is None:
            return False  # pragma: no cover
        for property_name in property_names:
            if property_name not in self.properties.root:
                return False
        return True

    @property
    def can_be_invalidated(self) -> bool:
        if (
            self.required
            or self.maxProperties is not None
            or self.minProperties is not None
            or self.const is not None
            or self.enum is not None
        ):
            return True
        return False

    @property
    def annotation_string(self) -> str:
        return "dict[str, JSON]"

    @property
    def python_type(self) -> builtins.type:
        return dict


ResolvedSchemaObjectTypes = Annotated[
    Union[
        ArraySchema,  # type: ignore[type-arg]
        BooleanSchema,
        IntegerSchema,
        NullSchema,
        NumberSchema,
        ObjectSchema,
        StringSchema,
    ],
    Field(discriminator="type"),
]

RESOLVED_SCHEMA_CLASS_TUPLE = (
    NullSchema,
    BooleanSchema,
    StringSchema,
    IntegerSchema,
    NumberSchema,
    ArraySchema,
    ObjectSchema,
)


class UnionTypeSchema(SchemaBase[JSON], frozen=True):
    allOf: list["SchemaObjectTypes"] = []
    anyOf: list["SchemaObjectTypes"] = []
    oneOf: list["SchemaObjectTypes"] = []
    nullable: bool = False

    def get_valid_value(
        self,
        operation_id: str | None = None,
    ) -> tuple[JSON, ResolvedSchemaObjectTypes]:
        relations = (
            self.constraint_mapping.get_relations()
            + self.constraint_mapping.get_parameter_relations()
        )
        constrained_property_names = [relation.property_name for relation in relations]

        if not constrained_property_names:
            resolved_schemas = self.resolved_schemas
            chosen_schema = choice(resolved_schemas)
            return chosen_schema.get_valid_value(operation_id=operation_id)

        valid_values = []
        valid_schemas = []
        for candidate in self.resolved_schemas:
            if isinstance(candidate, ObjectSchema):
                if candidate.contains_properties(constrained_property_names):
                    valid_schemas.append(candidate)

            if isinstance(candidate, UnionTypeSchema):
                candidate.attach_constraint_mapping(self.constraint_mapping)
                try:
                    valid_value = candidate.get_valid_value(operation_id=operation_id)
                    valid_values.append(valid_value)
                except ValueError:
                    pass
        for valid_schema in valid_schemas:
            valid_value = valid_schema.get_valid_value(operation_id=operation_id)
            valid_values.append(valid_value)

        if valid_values:
            return choice(valid_values)

        # The constraints from the parent may not be applicable, resulting in no
        # valid_values being generated. In that case, generated a random value as normal.
        chosen_schema = choice(self.resolved_schemas)
        return chosen_schema.get_valid_value(operation_id=operation_id)

    def get_values_out_of_bounds(self, current_value: JSON) -> list[JSON]:
        raise ValueError

    @cached_property
    def resolved_schemas(self) -> list[ResolvedSchemaObjectTypes]:
        schemas_to_return: list[ResolvedSchemaObjectTypes] = []
        null_schema = None

        resolved_schemas = list(self._get_resolved_schemas())
        for schema in resolved_schemas:
            # Prevent duplication of NullSchema when handling nullable models.
            if isinstance(schema, NullSchema):
                null_schema = schema
            else:
                schemas_to_return.append(schema)
        if null_schema is not None:
            schemas_to_return.append(null_schema)
        return schemas_to_return

    def _get_resolved_schemas(self) -> Generator[ResolvedSchemaObjectTypes, None, None]:
        if self.allOf:
            properties_list: list[PropertiesMapping] = []
            additional_properties_list = []
            required_list = []
            max_properties_list = []
            min_properties_list = []
            nullable_list = []

            schemas_to_process = []
            for schema in self.allOf:
                if isinstance(schema, UnionTypeSchema):
                    schemas_to_process.extend(schema.resolved_schemas)
                else:
                    schemas_to_process.append(schema)

            for schema in schemas_to_process:
                if not isinstance(schema, ObjectSchema):
                    raise ValueError("allOf is only supported for ObjectSchemas")

                if schema.const is not None:
                    raise ValueError("allOf and models with a const are not compatible")

                if schema.enum:
                    raise ValueError("allOf and models with enums are not compatible")

                if schema.properties.root:
                    properties_list.append(schema.properties)
                additional_properties_list.append(schema.additionalProperties)
                required_list += schema.required
                max_properties_list.append(schema.maxProperties)
                min_properties_list.append(schema.minProperties)
                nullable_list.append(schema.nullable)

            properties_dicts = [mapping.root for mapping in properties_list]
            merged_properties = dict(ChainMap(*properties_dicts))

            if True in additional_properties_list:
                additional_properties_value: bool | SchemaObjectTypes = True
            else:
                additional_properties_types = []
                for additional_properties_item in additional_properties_list:
                    if isinstance(
                        additional_properties_item, RESOLVED_SCHEMA_CLASS_TUPLE
                    ):
                        additional_properties_types.append(additional_properties_item)
                    if isinstance(additional_properties_item, UnionTypeSchema):
                        additional_properties_types.extend(
                            additional_properties_item.resolved_schemas
                        )
                if not additional_properties_types:
                    additional_properties_value = False
                else:
                    additional_properties_value = UnionTypeSchema(
                        anyOf=additional_properties_types,
                    )

            max_properties = [max for max in max_properties_list if max is not None]
            min_properties = [min for min in min_properties_list if min is not None]
            max_propeties_value = max(max_properties) if max_properties else None
            min_propeties_value = min(min_properties) if min_properties else None

            merged_schema = ObjectSchema(
                type="object",
                properties=PropertiesMapping(root=merged_properties),
                additionalProperties=additional_properties_value,
                required=required_list,
                maxProperties=max_propeties_value,
                minProperties=min_propeties_value,
                nullable=False,
            )
            merged_schema.attach_constraint_mapping(self.constraint_mapping)
            yield merged_schema
            # If all schemas are nullable the merged schema is treated as nullable.
            if all(nullable_list):
                null_schema = NullSchema()
                null_schema.attach_constraint_mapping(self.constraint_mapping)
                yield null_schema
        else:
            for schema in self.anyOf + self.oneOf:
                if isinstance(schema, RESOLVED_SCHEMA_CLASS_TUPLE):
                    if schema.nullable:
                        schema.__dict__["nullable"] = False
                        null_schema = NullSchema()
                        null_schema.attach_constraint_mapping(self.constraint_mapping)
                        yield null_schema
                    yield schema
                else:
                    yield from schema.resolved_schemas

    def get_invalid_value_from_const_or_enum(self) -> JSON:
        raise ValueError

    def get_invalid_value_from_constraint(
        self, values_from_constraint: list[JSON]
    ) -> JSON:
        raise ValueError

    @property
    def annotation_string(self) -> str:
        unique_annotations = {s.annotation_string for s in self.resolved_schemas}
        return " | ".join(unique_annotations)


SchemaObjectTypes: TypeAlias = ResolvedSchemaObjectTypes | UnionTypeSchema


class PropertiesMapping(RootModel[dict[str, SchemaObjectTypes]], frozen=True): ...


def _get_empty_properties_mapping() -> PropertiesMapping:
    return PropertiesMapping(root={})


class ParameterObject(BaseModel):
    name: str
    in_: str = Field(..., alias="in")
    required: bool = False
    description: str = ""
    schema_: SchemaObjectTypes | None = Field(None, alias="schema")
    constraint_mapping: ConstraintMappingType | None = None

    def attach_constraint_mapping(
        self, constraint_mapping: ConstraintMappingType
    ) -> None:
        if self.schema_:  # pragma: no branch
            self.schema_.attach_constraint_mapping(constraint_mapping)

    def replace_nullable_with_union(self) -> None:
        if self.schema_:  # pragma: no branch
            processed_schema = nullable_schema_to_union_schema(self.schema_)
            self.schema_ = processed_schema


class MediaTypeObject(BaseModel):
    schema_: SchemaObjectTypes | None = Field(None, alias="schema")


class RequestBodyObject(BaseModel):
    content: dict[str, MediaTypeObject]
    required: bool = False
    description: str = ""

    @cached_property
    def schema_(self) -> SchemaObjectTypes | None:
        if not self.mime_type:
            return None

        if len(self._json_schemas) > 1:
            logger.info(
                f"Multiple JSON media types defined for requestBody, "
                f"using the first candidate from {self.content}"
            )
        return self._json_schemas[self.mime_type]

    @cached_property
    def mime_type(self) -> str | None:
        if not self._json_schemas:
            return None

        return next(iter(self._json_schemas))

    @cached_property
    def _json_schemas(self) -> dict[str, SchemaObjectTypes]:
        json_schemas = {
            mime_type: media_type.schema_
            for mime_type, media_type in self.content.items()
            if "json" in mime_type and media_type.schema_ is not None
        }
        return json_schemas

    def attach_constraint_mapping(
        self, constraint_mapping: ConstraintMappingType
    ) -> None:
        for media_object_type in self.content.values():
            if media_object_type and media_object_type.schema_:  # pragma: no branch
                media_object_type.schema_.attach_constraint_mapping(constraint_mapping)

    def replace_nullable_with_union(self) -> None:
        for media_object_type in self.content.values():
            if media_object_type and media_object_type.schema_:  # pragma: no branch
                processed_schema = nullable_schema_to_union_schema(
                    media_object_type.schema_
                )
                media_object_type.schema_ = processed_schema


class HeaderObject(BaseModel): ...


class LinkObject(BaseModel): ...


class ResponseObject(BaseModel):
    description: str
    content: dict[str, MediaTypeObject] = {}
    headers: dict[str, HeaderObject] = {}
    links: dict[str, LinkObject] = {}


class OperationObject(BaseModel):
    operationId: str | None = None
    summary: str = ""
    description: str = ""
    tags: list[str] = []
    parameters: list[ParameterObject] = []
    requestBody: RequestBodyObject | None = None
    responses: dict[str, ResponseObject] = {}
    constraint_mapping: ConstraintMappingType | None = None

    def update_parameters(self, parameters: list[ParameterObject]) -> None:
        self.parameters.extend(parameters)

    def attach_constraint_mappings(self) -> None:
        if not self.constraint_mapping:
            return

        if self.requestBody:
            self.requestBody.attach_constraint_mapping(self.constraint_mapping)

        for parameter_object in self.parameters:
            parameter_object.attach_constraint_mapping(self.constraint_mapping)

    def replace_nullable_with_union(self) -> None:
        if self.requestBody:
            self.requestBody.replace_nullable_with_union()

        for parameter_object in self.parameters:
            parameter_object.replace_nullable_with_union()


class PathItemObject(BaseModel):
    get: OperationObject | None = None
    post: OperationObject | None = None
    patch: OperationObject | None = None
    put: OperationObject | None = None
    delete: OperationObject | None = None
    summary: str = ""
    description: str = ""
    parameters: list[ParameterObject] = []
    constraint_mapping: ConstraintMappingType | None = None
    id_mapper: tuple[str, Callable[[str], str]] = (
        "id",
        dummy_transformer,
    )

    @property
    def operations(self) -> dict[str, OperationObject]:
        return {
            k: v for k, v in self.__dict__.items() if isinstance(v, OperationObject)
        }

    def update_operation_parameters(self) -> None:
        if not self.parameters:
            return

        operations_to_update = self.operations
        for operation_object in operations_to_update.values():
            operation_object.update_parameters(self.parameters)

    def attach_constraint_mappings(self) -> None:
        for operation_object in self.operations.values():
            operation_object.attach_constraint_mappings()

    def replace_nullable_with_union(self) -> None:
        for operation_object in self.operations.values():
            operation_object.attach_constraint_mappings()
            operation_object.replace_nullable_with_union()


class InfoObject(BaseModel):
    title: str
    version: str
    summary: str = ""
    description: str = ""


class OpenApiObject(BaseModel):
    info: InfoObject
    paths: dict[str, PathItemObject]


def nullable_schema_to_union_schema(schema: SchemaObjectTypes) -> SchemaObjectTypes:
    if not schema.nullable:
        return schema

    schema.__dict__["nullable"] = False
    null_schema = NullSchema()
    null_schema.attach_constraint_mapping(schema.constraint_mapping)
    union_schema = UnionTypeSchema(oneOf=[schema, null_schema])
    union_schema.attach_constraint_mapping(schema.constraint_mapping)
    return union_schema


# TODO: move to keyword_logic?
def get_dependent_id(
    constraint_mapping: ConstraintMappingType | None,
    property_name: str,
    operation_id: str | None,
) -> str | int | float | None:
    relations = constraint_mapping.get_relations() if constraint_mapping else []
    # multiple get paths are possible based on the operation being performed
    id_get_paths = [
        (d.get_path, d.operation_id)
        for d in relations
        if (isinstance(d, IdDependency) and d.property_name == property_name)
    ]
    if not id_get_paths:
        return None
    if len(id_get_paths) == 1:
        id_get_path, _ = id_get_paths.pop()
    else:
        try:
            [id_get_path] = [
                path for path, operation in id_get_paths if operation == operation_id
            ]
        # There could be multiple get_paths, but not one for the current operation
        except ValueError:
            return None

    valid_id = cast(
        str | int | float, run_keyword("get_valid_id_for_path", id_get_path)
    )
    logger.debug(f"get_dependent_id for {id_get_path} returned {valid_id}")
    return valid_id
