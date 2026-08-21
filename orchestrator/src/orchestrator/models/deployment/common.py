"""Common deployment-related models."""

import re
from typing import Any

from pydantic import Field, model_validator

from orchestrator.models.common import BlueprintBaseModel

SEM_VER_PATTERN = r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?:-(?P<extension>.+))?$"

class Version(BlueprintBaseModel):
    """Conventional semantic version."""

    major: int = Field()
    """Major version."""

    minor: int = Field()
    """Minor version."""

    patch: int = Field()
    """Patch version."""

    extension: str | None = Field(default=None)
    """Version extension (anything after -)."""

    @model_validator(mode="before")
    @classmethod
    def parse_string_or_dict(cls, data) -> dict[str, Any] | Any:
        """Parse version string directly into initialisation dict before validation."""

        if isinstance(data, str):
            match = re.match(SEM_VER_PATTERN, data.strip())
            if not match:
                raise ValueError(f"Invalid version string {data!r}. Expected format: 'X.Y.Z' or 'X.Y.Z-extension'")

            data = match.groupdict()
            return {
                "major": int(data["major"]),
                "minor": int(data["minor"]),
                "patch": int(data["patch"]) if data["patch"] is not None else 0,
                "extension": data["extension"],
            }

        return data
