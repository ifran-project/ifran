"""Provisioning lifecycle management."""

from typing import Literal

from orchestrator.deployment.common import BaseBlueprintManagement
from orchestrator.utils.provisioning import (
    get_provisionable_resources,
    get_resources_by_provisioner,
    run_parallel_provisioning_action,
    run_reservation_action,
)


class ProvisioningManagement(BaseBlueprintManagement):
    """Provisioning management class."""

    async def run_action(
            self,
            action: Literal["provision", "unprovision", "reserve"],
            resources: dict[Literal['nodes', 'rus', 'ues'], list[str]] | None = None,
            force: bool = False,
            ignore_invalid_states: bool = True,
            ignore_failures: bool = False,
        ) -> None:
        """Run provisioning/reservation action on all provisionable resources or a given subset."""

        target_resources = get_provisionable_resources(
            deployment_model=self.deployment_model,
            resources=resources
            )

        # reservations are attempted before provisioning
        if action in ["provision", "reserve"]:
            grouped = get_resources_by_provisioner(target_resources)

            for provisioner_name, resources_list in grouped.items():
                await run_reservation_action(
                    resources=resources_list,
                    provisioner_name=provisioner_name,
                    provisioners=self.deployment_model.provisioners,
                    ansible_params=self.deployment_model.params.ansible,
                    ignore_failures=ignore_failures,
                    force=force if action == "reserve" else False, # don't force reservation when the main action is provisioning
                    skip_unreservable=(action == "provision"),  # skip unreservable resources when provisioning
                )


        if action in ["provision", "unprovision"]:
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


    async def reserve(self, **kwargs) -> None:
        """Reserve all reservable resources."""
        await self.run_action(action="reserve", **kwargs)


    async def _run_type_action(
            self,
            rtype: Literal["nodes", "rus", "ues"],
            action: Literal["provision", "unprovision", "reserve"],
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


    # wrappers for each resource type and action for convenience
    async def provision_nodes(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of nodes."""
        await self._run_type_action("nodes", "provision", nodes, **kwargs)


    async def unprovision_nodes(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of nodes."""
        await self._run_type_action("nodes", "unprovision", nodes, **kwargs)


    async def reserve_nodes(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Reserve all or a targeted list of nodes."""
        await self._run_type_action("nodes", "reserve", nodes, **kwargs)


    async def provision_rus(self, rus: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of RUs."""
        await self._run_type_action("rus", "provision", rus, **kwargs)


    async def unprovision_rus(self, rus: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of RUs."""
        await self._run_type_action("rus", "unprovision", rus, **kwargs)


    async def reserve_rus(self, rus: list[str] | None = None, **kwargs) -> None:
        """Reserve all or a targeted list of RUs."""
        await self._run_type_action("rus", "reserve", rus, **kwargs)


    async def provision_ues(self, ues: list[str] | None = None, **kwargs) -> None:
        """Provision all or a targeted list of UEs."""
        await self._run_type_action("ues", "provision", ues, **kwargs)


    async def unprovision_ues(self, ues: list[str] | None = None, **kwargs) -> None:
        """Unprovision all or a targeted list of UEs."""
        await self._run_type_action("ues", "unprovision", ues, **kwargs)


    async def reserve_ues(self, ues: list[str] | None = None, **kwargs) -> None:
        """Reserve all or a targeted list of UEs."""
        await self._run_type_action("ues", "reserve", ues, **kwargs)

