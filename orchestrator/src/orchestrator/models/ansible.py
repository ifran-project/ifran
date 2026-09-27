"""Ansible models."""

from pathlib import Path

from metamodel.models.base import StrictBaseModel
from pydantic import Field


def _default_roles_paths() -> list[str]:
    """Look for and return built-in Ansible roles directory as default."""

    builtin = (Path(__file__).resolve().parents[2] / "ansible" / "roles")
    if builtin.exists():
        return([str(builtin)])

    return []


class AnsibleParams(StrictBaseModel):
    """Ansible global parameters."""

    runner_path: str = Field(default=str(Path.home() / "post-5g" / "ansible-runner"))
    """Path to where the Ansible Runner data will be stored."""

    roles_paths: list[str] = Field(default_factory=_default_roles_paths)
    """Path to Ansible roles directory."""
