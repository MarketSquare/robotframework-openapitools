import base64
from abc import abstractmethod
from collections import ChainMap
from functools import cached_property
from random import choice, randint, uniform
from sys import float_info
from typing import (
    Generator,
    Generic,
    Literal,
    Mapping,
    TypeAlias,
    TypeVar,
)

import rstr
from pydantic import BaseModel, Field, RootModel
from robot.api import logger

from OpenApiLibCore.annotations import JSON
from OpenApiLibCore.localized_faker import FAKE, fake_string

EPSILON = float_info.epsilon

O = TypeVar("O")


class SchemaBase(BaseModel, Generic[O], frozen=True):
    readOnly: bool = False
    writeOnly: bool = False

    @abstractmethod
    def get_valid_value(self) -> JSON: ...

    @abstractmethod
    def get_values_out_of_bounds(self, current_value: O) -> list[O]: ...

    @abstractmethod
    def get_invalid_value_from_const_or_enum(self) -> O: ...


class NullSchema(SchemaBase[None], frozen=True):
    type: Literal["null"] = "null"

    def get_valid_value(self) -> None:
        return None

    def get_values_out_of_bounds(self, current_value: None) -> list[None]:
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> None:
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return False

    @property
    def annotation_string(self) -> str:
        return "None"


class BooleanSchema(SchemaBase[bool], frozen=True):
    type: Literal["boolean"] = "boolean"
    const: bool | None = None
    nullable: bool = False

    def get_valid_value(self) -> bool:
        if self.const is not None:
            return self.const
        return choice([True, False])

    def get_values_out_of_bounds(self, current_value: bool) -> list[bool]:
        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> bool:
        if self.const is not None:
            return not self.const
        raise ValueError

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "bool"


class StringSchema(SchemaBase[str], frozen=True):
    type: Literal["string"] = "string"
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

    def get_valid_value(self) -> int:
        """Generate a random int within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const
        if self.enum is not None:
            return choice(self.enum)

        return randint(self._min_value, self._max_value)

    def get_values_out_of_bounds(self, current_value: int) -> list[int]:
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

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "int"


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

    def get_valid_value(self) -> float:
        """Generate a random float within the min/max range of the schema, if specified."""
        if self.const is not None:
            return self.const
        if self.enum is not None:
            return choice(self.enum)

        return uniform(self._min_value, self._max_value)

    def get_values_out_of_bounds(self, current_value: float) -> list[float]:
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

    @property
    def can_be_invalidated(self) -> bool:
        return True

    @property
    def annotation_string(self) -> str:
        return "float"


class ArraySchema(SchemaBase[list[JSON]], frozen=True):
    type: Literal["array"] = "array"
    items: "SchemaObjectTypes"
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool = False
    const: list[JSON] | None = None
    enum: list[list[JSON]] | None = None
    nullable: bool = False

    def get_valid_value(self) -> list[JSON]:
        if self.const is not None:
            return self.const

        if self.enum is not None:
            return choice(self.enum)

        minimum = self.minItems if self.minItems is not None else 0
        maximum = self.maxItems if self.maxItems is not None else 1
        maximum = max(minimum, maximum)

        value: list[JSON] = []
        for _ in range(maximum):
            item_value = self.items.get_valid_value()
            value.append(item_value)
        return value

    def get_values_out_of_bounds(self, current_value: list[JSON]) -> list[list[JSON]]:
        invalid_values: list[list[JSON]] = []

        if self.minItems:
            invalid_value = current_value[0 : self.minItems - 1]
            invalid_values.append(invalid_value)

        if self.maxItems is not None:
            invalid_value = []
            if not current_value:
                current_value = self.get_valid_value()

            if not current_value:
                current_value = [self.items.get_valid_value()]

            while len(invalid_value) <= self.maxItems:
                invalid_value.append(choice(current_value))
            invalid_values.append(invalid_value)

        if invalid_values:
            return invalid_values

        raise ValueError

    def get_invalid_value_from_const_or_enum(self) -> list[JSON]:
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


class PropertiesMapping(RootModel[dict[str, "SchemaObjectTypes"]], frozen=True): ...


class ObjectSchema(SchemaBase[dict[str, JSON]], frozen=True):
    type: Literal["object"] = "object"
    properties: PropertiesMapping | None = None
    additionalProperties: "bool | SchemaObjectTypes" = True
    required: list[str] = []
    maxProperties: int | None = None
    minProperties: int | None = None
    const: dict[str, JSON] | None = None
    enum: list[dict[str, JSON]] | None = None
    nullable: bool = False

    def get_valid_value(self) -> dict[str, JSON]:
        raise NotImplementedError

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
        return "dict[str, Any]"


ResolvedSchemaObjectTypes: TypeAlias = (
    NullSchema
    | BooleanSchema
    | StringSchema
    | IntegerSchema
    | NumberSchema
    | ArraySchema
    | ObjectSchema
)


class UnionTypeSchema(SchemaBase[JSON], frozen=True):
    allOf: list["SchemaObjectTypes"] = []
    anyOf: list["SchemaObjectTypes"] = []
    oneOf: list["SchemaObjectTypes"] = []

    def get_valid_value(self) -> JSON:
        chosen_schema = choice(self.resolved_schemas)
        return chosen_schema.get_valid_value()

    def get_values_out_of_bounds(self, current_value: JSON) -> list[JSON]:
        raise ValueError

    @property
    def resolved_schemas(self) -> list[ResolvedSchemaObjectTypes]:
        return list(self._get_resolved_schemas())

    def _get_resolved_schemas(self) -> Generator[ResolvedSchemaObjectTypes, None, None]:
        if self.allOf:
            properties_list: list[PropertiesMapping] = []
            additional_properties_list = []
            required_list = []
            max_properties_list = []
            min_properties_list = []
            nullable_list = []

            for schema in self.allOf:
                if not isinstance(schema, ObjectSchema):
                    raise NotImplementedError("allOf only supported for ObjectSchemas")

                if schema.const is not None:
                    raise ValueError("allOf and models with a const are not compatible")

                if schema.enum:
                    raise ValueError("allOf and models with enums are not compatible")

                if schema.properties:
                    properties_list.append(schema.properties)
                additional_properties_list.append(schema.additionalProperties)
                required_list += schema.required
                max_properties_list.append(schema.maxProperties)
                min_properties_list.append(schema.minProperties)
                nullable_list.append(schema.nullable)

            properties_dicts = [mapping.root for mapping in properties_list]
            properties = dict(ChainMap(*properties_dicts))

            if True in additional_properties_list:
                additional_properties_value: bool | SchemaObjectTypes = True
            else:
                additional_properties_types = []
                for additional_properties_item in additional_properties_list:
                    if isinstance(
                        additional_properties_item, ResolvedSchemaObjectTypes
                    ):
                        additional_properties_types.append(additional_properties_item)
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
                properties=properties,
                additionalProperties=additional_properties_value,
                required=required_list,
                maxProperties=max_propeties_value,
                minProperties=min_propeties_value,
                nullable=all(nullable_list),
            )
            yield merged_schema
        else:
            for schema in self.anyOf + self.oneOf:
                if isinstance(schema, ResolvedSchemaObjectTypes):
                    yield schema
                else:
                    yield from schema.resolved_schemas

    def get_invalid_value_from_const_or_enum(self) -> JSON:
        raise ValueError

    @property
    def annotation_string(self) -> str:
        unique_annotations = {s.annotation_string for s in self.resolved_schemas}
        return " | ".join(unique_annotations)


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

    @property
    def schema_(self) -> SchemaObjectTypes | None:
        schemas = [
            media_type.schema_
            for mime_type, media_type in self.content.items()
            if "json" in mime_type
        ]
        if None in schemas:
            schemas.remove(None)
        if not schemas:
            return None

        if len(schemas) > 1:
            logger.warn(f"Multiple schemas defined for request body: {self.content}")
        return schemas.pop()


class HeaderObject(BaseModel): ...


class LinkObject(BaseModel): ...


class ResponseObject(BaseModel):
    description: str
    content: dict[str, MediaTypeObject] = {}
    headers: dict[str, HeaderObject] = {}
    links: dict[str, LinkObject] = {}


# class ComponentsObject(BaseModel):
#     schemas: dict[str, SchemaObjectTypes]


class OperationObject(BaseModel):
    operationId: str | None = None
    summary: str = ""
    description: str = ""
    tags: list[str] = []
    parameters: list[ParameterObject] | None = None
    requestBody: RequestBodyObject | None = None
    responses: dict[str, ResponseObject] = {}


class PathItemObject(BaseModel):
    get: OperationObject | None = None
    post: OperationObject | None = None
    patch: OperationObject | None = None
    put: OperationObject | None = None
    delete: OperationObject | None = None
    summary: str = ""
    description: str = ""
    parameters: list[ParameterObject] | None = None

    def get_operations(self) -> dict[str, OperationObject]:
        return {
            k: v for k, v in self.__dict__.items() if isinstance(v, OperationObject)
        }


class InfoObject(BaseModel):
    title: str
    version: str
    summary: str = ""
    description: str = ""


class OpenApiObject(BaseModel):
    info: InfoObject
    paths: dict[str, PathItemObject]
