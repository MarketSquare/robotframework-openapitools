import base64
from abc import abstractmethod
from random import choice, randint, uniform
from typing import Generator, Literal, TypeAlias, TypeVar

import rstr
from pydantic import BaseModel, Field, JsonValue, RootModel

from OpenApiLibCore.localized_faker import FAKE, fake_string

O = TypeVar("O")


class SchemaBase(BaseModel, frozen=True):
    readOnly: bool = False
    writeOnly: bool = False

    @abstractmethod
    def get_valid_value(self) -> JsonValue: ...

    @abstractmethod
    def get_values_out_of_bounds(self, current_value: O) -> list[O]: ...


class NullSchema(SchemaBase, frozen=True):
    type: Literal["null"]

    def get_valid_value(self) -> None:
        return None

    def get_values_out_of_bounds(self, current_value: None) -> list[None]:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return False

    @property
    def has_const_or_enum(self) -> bool:
        return False


class BooleanSchema(SchemaBase, frozen=True):
    type: Literal["boolean"]
    const: bool | None = None
    nullable: bool = False

    def get_valid_value(self) -> bool:
        if self.const is not None:
            return self.const
        return choice([True, False])

    def get_values_out_of_bounds(self, current_value: bool) -> list[bool]:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def has_const_or_enum(self) -> bool:
        return self.const is not None


class StringSchema(SchemaBase, frozen=True):
    type: Literal["string"]
    format: str = ""
    pattern: str = ""
    maxLength: int | None = None
    minLength: int | None = None
    const: str | None = None
    enum: list[str] | None = None
    nullable: bool = False

    def get_valid_value(self) -> bytes | str:
        """Generate a random string within the min/max length in the schema, if specified."""
        if self.const is not None:
            return self.const
        if self.enum is not None:
            return choice(self.enum)
        # if a pattern is provided, format and min/max length can be ignored
        if pattern := self.pattern:
            return rstr.xeger(pattern)
        minimum = self.minLength if self.minLength is not None else 0
        maximum = self.maxLength if self.maxLength is not None else 36
        maximum = max(minimum, maximum)
        format_ = self.format if self.format else "uuid"
        # byte is a special case due to the required encoding
        if format_ == "byte":
            data = FAKE.uuid()
            return base64.b64encode(data.encode("utf-8"))
        value = fake_string(string_format=format_)
        while len(value) < minimum:
            # use fake.name() to ensure the returned string uses the provided locale
            value = value + FAKE.name()
        if len(value) > maximum:
            value = value[:maximum]
        return value

    def get_values_out_of_bounds(self, current_value: str) -> list[str]:
        invalid_values: list[str] = []
        if self.minLength:
            invalid_values.append(current_value[0 : self.minLength - 1])
        # if there is a maximum length, send 1 character more
        if self.maxLength:
            invalid_string_value = current_value if current_value else "x"
            # add random characters from the current value to prevent adding new characters
            while len(invalid_string_value) <= self.maxLength:
                invalid_string_value += choice(invalid_string_value)
            invalid_values.append(invalid_string_value)
        if invalid_values:
            return invalid_values
        raise ValueError

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
    def has_const_or_enum(self) -> bool:
        if self.enum or self.const is not None:
            return True
        return False


class IntegerSchema(SchemaBase, frozen=True):
    type: Literal["integer"]
    format: str = ""
    maximum: int | None = None
    exclusiveMaximum: int | bool | None = None
    minimum: int | None = None
    exclusiveMinimum: int | bool | None = None
    multipleOf: int | None = None  # FIXME: implement support
    const: int | None = None
    enum: list[int] | None = None
    nullable: bool = False

    def get_valid_value(self) -> int:
        """Generate a random int within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const
        if self.enum is not None:
            return choice(self.enum)
        # Use int32 integers if "format" does not specify int64
        property_format = self.format if self.format else "int32"
        if property_format == "int64":
            min_int = -9223372036854775808
            max_int = 9223372036854775807
        else:
            min_int = -2147483648
            max_int = 2147483647
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer
        minimum = self.minimum if self.minimum is not None else min_int
        maximum = self.maximum if self.maximum is not None else max_int
        if (exclusive_minimum := self.exclusiveMinimum) is not None:
            if isinstance(exclusive_minimum, bool):
                if exclusive_minimum:
                    minimum += 1
            else:
                minimum = exclusive_minimum + 1
        if (exclusive_maximum := self.exclusiveMaximum) is not None:
            if isinstance(exclusive_maximum, bool):
                if exclusive_maximum:
                    maximum -= 1
            else:
                maximum = exclusive_maximum - 1
        return randint(minimum, maximum)

    def get_values_out_of_bounds(self, current_value: int) -> list[int]:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def has_const_or_enum(self) -> bool:
        if self.enum or self.const is not None:
            return True
        return False


class NumberSchema(SchemaBase, frozen=True):
    type: Literal["number"]
    format: str = ""
    maximum: int | float | None = None
    exclusiveMaximum: int | float | bool | None = None
    minimum: int | float | None = None
    exclusiveMinimum: int | float | bool | None = None
    multipleOf: int | None = None  # FIXME: implement support
    const: int | float | None = None
    enum: list[int | float] | None = None
    nullable: bool = False

    def get_valid_value(self) -> float:
        """Generate a random float within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const
        if self.enum is not None:
            return choice(self.enum)
        # Python floats are already double precision, so no check for "format"
        minimum = self.minimum
        maximum = self.maximum
        if minimum is None:
            if maximum is None:
                minimum = -1.0
                maximum = 1.0
            else:
                minimum = maximum - 1.0
        else:
            if maximum is None:
                maximum = minimum + 1.0
            if maximum < minimum:
                raise ValueError(
                    f"maximum of {maximum} is less than minimum of {minimum}"
                )

        # For simplicity's sake, exclude both boundaries if one boundary is exclusive
        exclude_boundaries = False

        exclusive_minimum = (
            self.exclusiveMinimum if self.exclusiveMinimum is not None else False
        )
        exclusive_maximum = (
            self.exclusiveMaximum if self.exclusiveMaximum is not None else False
        )
        # OAS 3.0: exclusiveMinimum/Maximum is a bool in combination with minimum/maximum
        # OAS 3.1: exclusiveMinimum/Maximum is an integer or number
        if not isinstance(exclusive_minimum, bool):
            exclude_boundaries = True
            minimum = exclusive_minimum
        else:
            exclude_boundaries = exclusive_minimum
        if not isinstance(exclusive_maximum, bool):
            exclude_boundaries = True
            maximum = exclusive_maximum
        else:
            exclude_boundaries = exclusive_minimum or exclusive_maximum

        if exclude_boundaries and minimum == maximum:
            raise ValueError(
                f"maximum of {maximum} is equal to minimum of {minimum} and "
                f"exclusiveMinimum or exclusiveMaximum is specified"
            )

        while exclude_boundaries:
            result = uniform(minimum, maximum)
            if minimum < result < maximum:  # pragma: no cover
                return result
        return uniform(minimum, maximum)

    def get_values_out_of_bounds(self, current_value: float) -> list[float]:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def has_const_or_enum(self) -> bool:
        if self.enum or self.const is not None:
            return True
        return False


class ArraySchema(SchemaBase, frozen=True):
    type: Literal["array"]
    items: "SchemaObjectTypes"
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool = False
    const: list[JsonValue] | None = None
    enum: list[list[JsonValue]] | None = None
    nullable: bool = False

    def get_valid_value(self) -> list[JsonValue]:
        if self.const is not None:
            return self.const
        """Generate a list with random elements as specified by the schema."""
        minimum = self.minItems if self.minItems is not None else 0
        maximum = self.maxItems if self.maxItems is not None else 1
        maximum = max(minimum, maximum)
        items_schema = self.items
        value = []
        for _ in range(maximum):
            if self.enum is not None:
                item_value = choice(self.enum)
            else:
                item_value = items_schema.get_valid_value()
            value.append(item_value)
        return value

    def get_values_out_of_bounds(
        self, current_value: list[JsonValue]
    ) -> list[list[JsonValue]]:
        raise ValueError

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
    def has_const_or_enum(self) -> bool:
        if self.enum or self.const is not None:
            return True
        return False


class PropertiesMapping(RootModel):
    root: dict[str, "SchemaObjectTypes"]


class ObjectSchema(SchemaBase, frozen=True):
    type: Literal["object"]
    properties: PropertiesMapping
    additionalProperties: bool | dict[str, PropertiesMapping] = True
    required: list[str] = []
    maxProperties: int | None = None
    minProperties: int | None = None
    const: dict[str, JsonValue] | None = None
    enum: list[dict[str, JsonValue]] | None = None
    nullable: bool = False

    def get_valid_value(self) -> dict[str, JsonValue]:
        raise NotImplementedError

    def get_values_out_of_bounds(
        self, current_value: dict[str, JsonValue]
    ) -> list[dict[str, JsonValue]]:
        raise ValueError

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
    def has_const_or_enum(self) -> bool:
        if self.enum or self.const is not None:
            return True
        return False


ResolvedSchemaObjectTypes: TypeAlias = (
    NullSchema
    | BooleanSchema
    | StringSchema
    | IntegerSchema
    | NumberSchema
    | ArraySchema
    | ObjectSchema
)


class UnionTypeSchema(SchemaBase, frozen=True):
    allOf: list["SchemaObjectTypes"] = []
    anyOf: list["SchemaObjectTypes"] = []
    oneOf: list["SchemaObjectTypes"] = []

    def get_valid_value(self) -> JsonValue:
        schemas_to_choose_from = self.anyOf + self.oneOf
        chosen_schema = choice(schemas_to_choose_from)
        return chosen_schema.get_valid_value()

    def get_values_out_of_bounds(self, current_value: JsonValue) -> list[JsonValue]:
        raise ValueError

    @property
    def resolved_schemas(self) -> list[ResolvedSchemaObjectTypes]:
        return list(self._get_resolved_schemas())

    def _get_resolved_schemas(self) -> Generator[ResolvedSchemaObjectTypes, None, None]:
        for schema in self.anyOf:
            if isinstance(schema, ResolvedSchemaObjectTypes):
                yield schema
            else:
                yield from schema._get_resolved_schemas()


SchemaObjectTypes: TypeAlias = ResolvedSchemaObjectTypes | UnionTypeSchema


class ParameterObject(BaseModel):
    name: str
    in_: str = Field(..., alias="in")
    required: bool = False
    description: str = ""
    schema_: SchemaObjectTypes | None = Field(None, alias="schema")


class MediaTypeObject(BaseModel):
    schema_: SchemaObjectTypes | None = Field(None, alias="schema")


class RequestBodyObject(BaseModel):
    content: dict[str, MediaTypeObject]
    required: bool = False
    description: str = ""


# class ResponseObject(BaseModel): ...


# class ComponentsObject(BaseModel):
#     schemas: dict[str, SchemaObjectTypes]


class OperationObject(BaseModel):
    operationId: str | None = None
    summary: str = ""
    description: str = ""
    parameters: list[ParameterObject] | None = None
    requestBody: RequestBodyObject | None = None
    # responses: list[ResponseObject] = []


class PathItemObject(BaseModel):
    get: OperationObject | None = None
    post: OperationObject | None = None
    patch: OperationObject | None = None
    put: OperationObject | None = None
    delete: OperationObject | None = None
    summary: str = ""
    description: str = ""
    parameters: list[ParameterObject] | None = None

    def get_operations(self) -> list[OperationObject]:
        return [v for v in self.__dict__.values() if isinstance(v, OperationObject)]


class OpenApiObject(BaseModel):
    paths: dict[str, PathItemObject]
    # components: ComponentsObject | None = None
