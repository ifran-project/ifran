"""Ansible models."""

from pathlib import Path

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel


def _default_roles_paths() -> list[str]:
    """Look for and return built-in Ansible roles directory as default."""

    builtin = (Path(__file__).resolve().parents[3] / "ansible" / "roles")
    if builtin.exists():
        return([str(builtin)])
    else:
        return []


class AnsibleParams(BlueprintBaseModel):
    """Ansible global parameters."""

    runner_path: str = Field(default=str(Path.home() / ".ansible-runner"))
    """Path to where the Ansible Runner data will be stored."""

    roles_paths: list[str] = Field(default_factory=_default_roles_paths)
    """Path to Ansible roles directory."""
