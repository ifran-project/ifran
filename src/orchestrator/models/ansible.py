"""Ansible models."""

from pathlib import Path

from metamodel.models.base import StrictBaseModel
from pydantic import Field

from orchestrator.utils.utils import ResolvedPath


def _default_roles_paths() -> list[str]:
    """Look for and return built-in Ansible roles directory as default."""

    builtin = (Path(__file__).resolve().parents[2] / "ansible" / "roles")
    if builtin.exists():
        return([str(builtin)])

    return []


class AnsibleParams(StrictBaseModel):
    """Ansible global parameters."""

    runner_path: ResolvedPath = Field(default=str(Path.home() / "post-5g" / "ansible-runner"))
    """Path to where the Ansible Runner data will be stored."""

    roles_paths: list[ResolvedPath] = Field(default_factory=_default_roles_paths)
    """List of paths to Ansible roles directories."""
