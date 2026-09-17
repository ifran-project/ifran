"""Common models."""

import configparser
import io
import json
from typing import Annotated, Any, Self

import yaml
from pydantic import (
    AnyUrl,
    BaseModel,
    ConfigDict,
    PlainSerializer,
    UrlConstraints,
    WithJsonSchema,
)


class BlueprintBaseModel(BaseModel):
    """5G blueprint basemodel used to ensure no extra fields tolerance."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @classmethod
    def from_json(cls, text: str) -> Self:
        """Load model from JSON."""
        return cls.model_validate_json(text)

    @classmethod
    def from_yaml(cls, text: str) -> Self:
        """Load model from YAML."""
        return cls.model_validate(yaml.safe_load(text))

    @classmethod
    def from_json_file(cls, path: str) -> Self:
        """Load model from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    @classmethod
    def from_yaml_file(cls, path: str) -> Self:
        """Load model from YAML file."""
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(yaml.safe_load(f))

    def to_yaml(self, exclude_defaults: bool = True) -> str:
        """Export model to YAML."""
        return yaml.safe_dump(
            self.model_dump(
                mode="json",
                exclude_defaults=exclude_defaults,
            ), sort_keys=False,
        )

    def to_yaml_file(self, path: str, exclude_defaults: bool = True) -> None:
        """Export model to YAML file."""
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.to_yaml(exclude_defaults=exclude_defaults))


class BlueprintTolerantBaseModel(BlueprintBaseModel):
    """5G blueprint basemodel with extra fields tolerance."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


type URL = Annotated[AnyUrl, UrlConstraints(preserve_empty_path=True)]
"""
URL type without unwanted trailing slash at the end. See:
    - https://github.com/pydantic/pydantic/issues/7186
    - https://pydantic.dev/articles/pydantic-v2-12-release#preserve-empty-url-paths
"""

# utils
def parse_hex_int(value: str | Any) -> int | Any:
    """Convert an integer or hexadecimal string to an integer."""

    if isinstance(value, str):
        return int(value, 16)
    return value


def serialize_hex_int(value: int | None, width: int) -> str | None:
    """Serialize an integer to a zero-padded uppercase hexadecimal string."""

    if value is None:
        return None
    return f"{value:0{width}X}"


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
    config.optionxform = str

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
