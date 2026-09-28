"""Basic utilities and helpers."""

import configparser
import io
from typing import Annotated, Any

from pydantic import (
    BaseModel,
    PlainSerializer,
    WithJsonSchema,
)


class InvalidResourceStateError(Exception):
    """Exception when a resource's state/status contradicts the desired action to be done."""


class ReferenceNotFoundError(Exception):
    """Exception when a resource references an undefined resource."""


def sync_dict_keys(
        target_dict: dict,
        source_dict: dict,
        default_factory: Any,
        populate_type: bool = False,
        remove_extra: bool = True,
    ) -> None:
    """Synchronize 'target_dict' keys with 'source_dict' keys."""

    missing_keys = source_dict.keys() - target_dict.keys()
    extra_keys = target_dict.keys() - source_dict.keys()

    # add missing keys
    for key in missing_keys:
        if populate_type:
            # ran, core, and ric components need the type field
            target_dict[key] = default_factory(type=source_dict[key].type)
        else:
            target_dict[key] = default_factory()

    # remove extra keys
    if remove_extra:
        for key in extra_keys:
            del target_dict[key]


def _to_jsonable(value: Any) -> Any:
    """Helper to recursively convert Pydantic models to JSON-compatible values."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_to_jsonable(item) for item in value)

    return value


def deep_merge(left: dict[str, Any] | BaseModel, right: dict[str, Any] | BaseModel) -> dict[str, Any]:
    """
    Recursively merge two dictionaries or pydantic models (converted to dictionaries).

    Values from 'right' dict take precedence when the same leaf field exists in both dicts.
    """

    left = _to_jsonable(left)
    right = _to_jsonable(right)

    result = dict(left)

    for key, right_value in right.items(): # type: ignore
        left_value = result.get(key)
        if (isinstance(left_value, dict) and isinstance(right_value, dict)):
            result[key] = deep_merge(left=left_value, right=right_value)
        else:
            result[key] = right_value

    return result


def serialize_libconfig_scalar(value: Any) -> str:
    """Serialize a scalar Python value to libconfig syntax."""

    if isinstance(value, bool):
        return "true" if value else "false"

    if isinstance(value, str):
        escaped = (
            value
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return f'"{escaped}"'

    if value is None:
        return "NULL"

    return str(value)


def serialize_libconfig(value: Any) -> str:
    """Serialize Python data to libconfig syntax."""

    if isinstance(value, dict):
        fields = "; ".join(
            f"{key} = {serialize_libconfig(child)}"
            for key, child in value.items()
        )

        return f"{{ {fields}; }}"

    if isinstance(value, list):
        values = ", ".join(serialize_libconfig(item) for item in value)

        return f"( {values} )"

    return serialize_libconfig_scalar(value)


type SerializableLibconfigDict = Annotated[
    dict[str, Any],
    PlainSerializer(serialize_libconfig, return_type=str),
    WithJsonSchema({'type': 'string'}, mode='serialization'),
]
"""Python dictionary type for Pydantic that can be serialized into a libconfig block."""


def serialize_ini_section(value: Any) -> str:
    """Serialize a dictionary to INI syntax without the section header."""

    if not isinstance(value, dict):
        return str(value)

    config = configparser.ConfigParser()

    # By default, ConfigParser converts all keys to lowercase.
    # Setting optionxform to str prevents this and preserves original casing.
    config.optionxform = str # type: ignore

    # configparser requires string values. We handle special types here.
    processed_dict = {}
    for key, val in value.items():
        if isinstance(val, bool):
            processed_dict[str(key)] = "true" if val else "false"
        elif val is None:
            # Usually, if a value is None, we want to omit it entirely from the config
            continue
        else:
            processed_dict[str(key)] = str(val)

    config["_DUMMY_"] = processed_dict

    with io.StringIO() as buffer:
        config.write(buffer)

        # Read lines, removing the [_DUMMY_] section header and empty trailing lines
        lines = buffer.getvalue().splitlines()

        if lines and lines[0] == "[_DUMMY_]":
            lines = lines[1:]

        return "\n".join(lines).strip()


SerializableINIConfigDict = Annotated[
    dict[str, Any],
    PlainSerializer(serialize_ini_section, return_type=str),
    WithJsonSchema({'type': 'string'}, mode='serialization'),
]
"""Python dictionary type for Pydantic that can be serialized into INI block fields."""
