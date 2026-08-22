"""5G core deployemnt lifecycle management."""

import asyncio
from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType
from orchestrator.utils.ansible import (
    handle_ansible_result_exception,
)
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.core import (
    reconcile_core,
    run_core_database_helm_action,
    run_parallel_database_subscriber_action,
)

CORE_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    CoreComponentType.AMF: frozenset({
        CoreComponentType.NRF,
        CoreComponentType.UDM,
        CoreComponentType.UDR
    }),
    CoreComponentType.AUSF: frozenset({
        CoreComponentType.NRF,
        CoreComponentType.UDM,
        CoreComponentType.UDR
    }),
    CoreComponentType.SMF: frozenset({
        CoreComponentType.NRF,
        CoreComponentType.UDM,
        CoreComponentType.UDR
    }),
}


class CoreManagement(HelmManagement):
    """5G core deployemnt lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the 5G core is ready for deployement by resolving its components' configs."""

        super().reconcile()

        reconcile_core(
            core_meta=self.mutatable_metamodel.core,
            core_deployment=self.deployment_model.core_deployment,
            slices=self.mutatable_metamodel.slices,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on 5G core components."""
        await super().run_action(category=Category5G.CORE, **kwargs)


    async def run_database_action(
            self,
            action: Literal["prepare", "install", "uninstall"],
            node: str | None = None,
            force: bool = False,
            **kwargs,
        ) -> None:
        """Run 5G core database Helm action."""

        node_name, node_data = self._get_master_node(node)

        result = await run_core_database_helm_action(
            core_meta=self.metamodel.core,
            core_deployment=self.deployment_model.core_deployment,
            action=action,
            node_name=node_name,
            node_data=node_data,
            ansible_params=self.deployment_model.params.ansible,
            force=force,
            )
    
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                **kwargs,
            )


    async def run_database_subscriber_action(
            self,
            action: Literal["add", "remove"],
            ues: list[str] | None = None,
            node: str | None = None,
            **kwargs,
        ) -> None:
        """Add/remove UEs/subscribers on the 5G core database."""

        node_name, node_data = self._get_master_node(node)

        all_ues = self.metamodel.ues

        # filter for specific components if requested
        if ues is None:
            target_ues = all_ues
        else:
            target_ues = {k: v for k, v in all_ues.items() if k in ues}

        await run_parallel_database_subscriber_action(
            ues=target_ues,
            core_implementation=self.metamodel.core.implementation,
            database_ip=self.deployment_model.core_deployment.database_ip,
            action=action,
            node_name=node_name,
            node_data=node_data,
            ansible_params=self.deployment_model.params.ansible,
            **kwargs,
            )


    async def register_ues(self, ues: list[str] | None = None, node: str | None = None, **kwargs) -> None:
        """Add UEs/subscribers to the 5G core database."""
        await self.run_database_subscriber_action("add", ues, node, **kwargs)


    async def unregister_ues(self, ues: list[str] | None = None, node: str | None = None, **kwargs) -> None:
        """Remove UEs/subscribers from the 5G core database."""
        await self.run_database_subscriber_action("remove", ues, node, **kwargs)


    async def deploy(
            self,
            node: str | None = None,
            order: ComponentDependencyGraph | None = CORE_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """
        Orchestrate full 5G core deployment.
        Prepares all charts (database + components), installs the database first, then installs 5G core components.
        """

        # prepare everything (database + components)
        await asyncio.gather(
            self.run_database_action(action="prepare", node=node, **kwargs),
            self.prepare(node=node, **kwargs),
        )

        # install database first
        await self.run_database_action(action="install", node=node, **kwargs)

        # install remaining core components in order if desired
        await self.install(node=node, order=order, **kwargs)

        # add subscribers
        await self.register_ues(node=node)


    async def remove(
            self,
            components: list[str] | None = None,
            **kwargs,
        ) -> None:
        """Remove/tear down 5G core deployment."""

        await asyncio.gather(
            self.uninstall(components=components, **kwargs),
            self.run_database_action(action="uninstall", **kwargs),
        )
