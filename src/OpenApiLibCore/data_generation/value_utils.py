"""Utility module with functions to handle OpenAPI value types and restrictions."""


def json_type_name_of_python_type(python_type: type) -> str:
    """Return the JSON type name for supported Python types."""
    if python_type == str:
        return "string"
    if python_type == bool:
        return "boolean"
    if python_type == int:
        return "integer"
    if python_type == float:
        return "number"
    if python_type == list:
        return "array"
    if python_type == dict:
        return "object"
    if python_type == type(None):
        return "null"
    raise ValueError(f"No json type mapping for Python type {python_type} available.")


def python_type_by_json_type_name(type_name: str) -> type:
    """Return the Python type based on the JSON type name."""
    if type_name == "string":
        return str
    if type_name == "boolean":
        return bool
    if type_name == "integer":
        return int
    if type_name == "number":
        return float
    if type_name == "array":
        return list
    if type_name == "object":
        return dict
    if type_name == "null":
        return type(None)
    raise ValueError(f"No Python type mapping for JSON type '{type_name}' available.")
