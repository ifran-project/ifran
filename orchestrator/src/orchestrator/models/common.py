"""Common models."""

import json

import yaml
from pydantic import BaseModel, ConfigDict


class BlueprintBaseModel(BaseModel):
    """5G blueprint basemodel used to ensure no extra fields tolerance."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    @classmethod
    def from_json(cls, text: str):
        """Load model from JSON."""
        return cls.model_validate_json(text)

    @classmethod
    def from_yaml(cls, text: str):
        """Load model from YAML."""
        return cls.model_validate(yaml.safe_load(text))

    @classmethod
    def from_json_file(cls, path: str):
        """Load model from JSON file."""
        with open(path, encoding="utf-8") as f:
            return cls.model_validate(json.load(f))

    @classmethod
    def from_yaml_file(cls, path: str):
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

    model_config = ConfigDict(populate_by_name=True)


# utils
def parse_hex_int(value: int | str) -> int:
    """Convert an integer or hexadecimal string to an integer."""

    if isinstance(value, str):
        return int(value, 16)
    return value


def serialize_hex_int(value: int | None, width: int) -> str | None:
    """Serialize an integer to a zero-padded uppercase hexadecimal string."""

    if value is None:
        return None
    return f"{value:0{width}X}"
