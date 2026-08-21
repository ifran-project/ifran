"""Provisioning lifecycle management."""

from typing import Literal

from orchestrator.deployment.common import BaseBlueprintManagement
from orchestrator.utils.provisioning import (
    get_provisionable_resources,
    run_parallel_provisioning_action,
)


class ProvisioningManagement(BaseBlueprintManagement):
    """Provisioning management class."""

    async def run_action(
            self,
            action: Literal["provision", "unprovision"] = "provision",
            resources: dict[Literal['nodes', 'rus', 'ues'], list[str]] | None = None,
            force: bool = False,
            ignore_invalid_states: bool = True,
            ignore_failures: bool = False,
        ) -> None:
        """Run provisioning action on all provisionable resources or a given subset."""

        target_resources = get_provisionable_resources(
            deployment_model=self.deployment_model,
            resources=resources
            )

        await run_parallel_provisioning_action(
            resources=target_resources,
            action=action,
            provisioners=self.deployment_model.provisioners,
            provisioning_params=self.deployment_model.params.provisioning,
            ansible_params=self.deployment_model.params.ansible,
            force=force,
            ignore_invalid_states=ignore_invalid_states,
            ignore_failures=ignore_failures,
        )


    async def provision(self, **kwargs) -> None:
        """Provision all nodes, RUs, and UEs."""
        await self.run_action(action="provision", resources=None, **kwargs)


    async def unprovision(self, **kwargs) -> None:
        """Unprovision all nodes, RUs, and UEs."""
        await self.run_action(action="unprovision", resources=None, **kwargs)


    async def _run_type_action(
            self,
            rtype: Literal["nodes", "rus", "ues"],
            action: Literal["provision", "unprovision"],
            names: list[str] | None = None,
            **kwargs,
        ) -> None:
        """Internal helper to dispatch action for a single resource type."""

        # if no specific names passed, default to all keys for that resource type
        if names is None:
            names = list(getattr(self.deployment_model, rtype, {}).keys())

        await self.run_action(
            action=action,
            resources={rtype: names},
            **kwargs,
        )


    async def provision_nodes(self, names: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of nodes."""
        await self._run_type_action("nodes", "provision", names, **kwargs)


    async def unprovision_nodes(self, names: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of nodes."""
        await self._run_type_action("nodes", "unprovision", names, **kwargs)


    async def provision_rus(self, names: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of RUs."""
        await self._run_type_action("rus", "provision", names, **kwargs)


    async def unprovision_rus(self, names: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of RUs."""
        await self._run_type_action("rus", "unprovision", names, **kwargs)


    async def provision_ues(self, names: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of UEs."""
        await self._run_type_action("ues", "provision", names, **kwargs)


    async def unprovision_ues(self, names: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of UEs."""
        await self._run_type_action("ues", "unprovision", names, **kwargs)
