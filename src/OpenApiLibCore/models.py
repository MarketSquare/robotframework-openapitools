from typing import Literal, TypeAlias

from pydantic import BaseModel, Field, RootModel


class NullSchema(BaseModel):
    type: Literal["null"]


class BooleanSchema(BaseModel):
    type: Literal["boolean"]
    nullable: bool = False


class StringSchema(BaseModel):
    type: Literal["string"]
    format: str = ""
    pattern: str = ""
    maxLength: int | None = None
    minLength: int | None = None
    enum: list[str] | None = None
    nullable: bool = False


class IntegerSchema(BaseModel):
    type: Literal["integer"]
    format: str = ""
    maximum: int | None = None
    exclusiveMaximum: int | None = None
    minimum: int | None = None
    exclusiveMinimum: int | None = None
    enum: list[int] | None = None
    nullable: bool = False


class NumberSchema(BaseModel):
    type: Literal["number"]
    format: str = ""
    maximum: int | float | None = None
    exclusiveMaximum: int | float | None = None
    minimum: int | float | None = None
    exclusiveMinimum: int | float | None = None
    enum: list[int | float] | None = None
    nullable: bool = False


class ArraySchema(BaseModel):
    type: Literal["array"]
    items: "SchemaObjectTypes"
    maxItems: int | None = None
    minItems: int | None = None
    uniqueItems: bool = False
    enum: list["ArraySchema"] | None = None
    nullable: bool = False


class PropertiesMapping(RootModel):
    root: dict[str, "PropertySchemaObjectTypes"]


class ObjectSchema(BaseModel):
    type: Literal["object"]
    properties: PropertiesMapping
    additionalProperties: bool | dict[str, PropertiesMapping] = True
    required: list[str] = []
    maxProperties: int | None = None
    minProperties: int | None = None
    enum: list["ObjectSchema"] | None = None
    nullable: bool = False


class UnionTypeSchema(BaseModel):
    allOf: list["SchemaObjectTypes"] = []
    anyOf: list["SchemaObjectTypes"] = []
    oneOf: list["SchemaObjectTypes"] = []
    multipleOf: list["SchemaObjectTypes"] = []


SchemaObjectTypes: TypeAlias = (
    NullSchema
    | BooleanSchema
    | StringSchema
    | IntegerSchema
    | NumberSchema
    | ArraySchema
    | ObjectSchema
    | UnionTypeSchema
)


class PropertySchema(BaseModel):
    readOnly: bool = False
    writeOnly: bool = False


class NullProperty(NullSchema, PropertySchema): ...


class BooleanProperty(BooleanSchema, PropertySchema): ...


class StringProperty(StringSchema, PropertySchema): ...


class IntegerProperty(IntegerSchema, PropertySchema): ...


class NumberProperty(NumberSchema, PropertySchema): ...


class ArrayProperty(ArraySchema, PropertySchema): ...


class ObjectProperty(ObjectSchema, PropertySchema): ...


class UnionProperty(BaseModel):
    allOf: list["PropertySchemaObjectTypes"] = []
    anyOf: list["PropertySchemaObjectTypes"] = []
    oneOf: list["PropertySchemaObjectTypes"] = []
    multipleOf: list["PropertySchemaObjectTypes"] = []


PropertySchemaObjectTypes: TypeAlias = (
    NullProperty
    | BooleanProperty
    | StringProperty
    | IntegerProperty
    | NumberProperty
    | ArrayProperty
    | ObjectProperty
    | UnionProperty
)


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
    operationId: str
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
