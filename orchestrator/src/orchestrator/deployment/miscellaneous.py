"""Miscellaneous executions using the MetaModel and DeploymenModel as inouts."""

from typing import Any

from orchestrator.deployment.common import BaseBlueprintManagement
from orchestrator.utils.ansible import run_ansible_playbook
from orchestrator.utils.common import deep_merge


class Miscellaneous(BaseBlueprintManagement):
    """Miscellaneous executions management class."""


    async def run_playbook(
            self,
            playbook: list | dict[str, Any] | str,
            inputs: dict[str, Any] | None = None,
            output_keys: list[str] | None = None,
            runner_path: str | None = None,
            roles_path: str | None = None,
            inventory: str | dict[str, Any] | list | None = None,
            store: bool = True,
            ) -> dict[str, Any] | None:
        """
        Run an Ansible playbook with inventory generated from deployment model resources.

        Args:
            playbook: path to the playbook file or a playbook dictionary or list of plays.
            inputs: extravars passed to the playbook (merged dictionary of deployment and meta models are always included).
            output_keys: keys of data to extract from the playbook execution output exported via ansible.builtin.set_stats.
            runner_path: directory path for ansible-runner related data (default to ansible-runner/miscellaneous).
            roles_path: directory path containing Ansible roles (default to ansible/roles).
            inventory: custom inventory source (path, INI string, dict, or list of inventory source) (defaults to deployment model resources inventory).
            store: whether to store the output of this play in the 'miscellaneous' field of the deployment model or not (defaults to True).
        """

        results =  await run_ansible_playbook(
            playbook=playbook,
            inputs=self.get_merged() | inputs if inputs else self.get_merged(),
            output_keys=output_keys,
            runner_path=runner_path if runner_path else self.deployment_model.params.ansible.runner_path,
            roles_path=roles_path if roles_path else self.deployment_model.params.ansible.roles_path,
            inventory=inventory if inventory else self.get_ansible_inventory(),
            )

        if results and store:
            self.deployment_model.miscellaneous = deep_merge(self.deployment_model.miscellaneous, results)

        return results
