"""Ansible models."""

from pathlib import Path

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel


class AnsibleParams(BlueprintBaseModel):
    """Ansible global parameters."""

    runner_path: str = Field(default=str(Path.home() / ".ansible-runner"))
    """Path to where the Ansible Runner data will be stored."""

    roles_path: str = Field(default=str(Path(__file__).resolve().parents[3] / "ansible/roles"))
    """Path to Ansible roles directory."""
