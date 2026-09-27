"""Miscellaneous executions using the MetaModel and DeploymentModel as inputs."""

from typing import Any

from orchestrator.deployment.base import BaseManagement
from orchestrator.utils.ansible import run_ansible_playbook
from orchestrator.utils.utils import deep_merge


class Miscellaneous(BaseManagement):
    """Miscellaneous executions management class."""

    async def run_playbook(  # noqa: PLR0917
            self,
            playbook: list | dict[str, Any] | str,
            inputs: dict[str, Any] | None = None,
            output_keys: list[str] | None = None,
            runner_path: str | None = None,
            roles_paths: str | None = None,
            inventory: str | dict[str, Any] | list | None = None,
            store: bool = True,
            ) -> dict[str, Any] | None:
        """
        Run a custom Ansible playbook on deployment model resources (nodes and UEs) or a custom inventory of resources.

        Args:
            playbook: path to the playbook file or a playbook dictionary or list of plays.
            inputs: extravars passed to the playbook
                (by default, merged dictionary of deployment and meta models are always included).
            output_keys: keys of data to extract from the playbook execution output
                exported via 'ansible.builtin.set_stats'.
            runner_path: directory path for ansible-runner's related data and logs
                (defaults to '~/post-5g/ansible-runner/miscellaneous').
            roles_paths: directory path containing Ansible roles (default to ansible/roles).
            inventory: custom inventory source (path, INI string, dict, or list of inventory source)
                (defaults to deployment model resources inventory).
            store: whether to store the output of this play in the 'miscellaneous' field of the deployment model or not
                (defaults to True).

        """

        results =  await run_ansible_playbook(
            playbook=playbook,
            inputs=self.get_merged() | inputs if inputs else self.get_merged(),
            output_keys=output_keys,
            runner_path=(
                runner_path if runner_path
                else f"{self.deployment_model.params.ansible.runner_path}/miscellaneous"),
            roles_paths=roles_paths if roles_paths else self.deployment_model.params.ansible.roles_paths,
            inventory=inventory if inventory else self.get_ansible_inventory(),
            )

        if results and store:
            self.deployment_model.miscellaneous = deep_merge(self.deployment_model.miscellaneous, results)

        return results
