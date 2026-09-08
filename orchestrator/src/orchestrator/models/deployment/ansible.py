"""Ansible models."""

from pathlib import Path

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel


def _default_roles_path() -> str:
    """Prefer the live project role directory over any installed package copy."""

    search_roots = [Path.cwd().resolve(), *Path.cwd().resolve().parents]
    search_roots.extend(Path(__file__).resolve().parents)

    for root in search_roots:
        for candidate in (root / "orchestrator" / "ansible" / "roles", root / "ansible" / "roles"):
            if candidate.exists():
                return str(candidate)

    return str(Path(__file__).resolve().parents[4] / "ansible" / "roles")


class AnsibleParams(BlueprintBaseModel):
    """Ansible global parameters."""

    runner_path: str = Field(default=str(Path.home() / ".ansible-runner"))
    """Path to where the Ansible Runner data will be stored."""

    roles_path: str = Field(default_factory=_default_roles_path)
    """Path to Ansible roles directory."""
