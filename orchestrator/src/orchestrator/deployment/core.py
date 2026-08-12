"""5G core deployemnt lifecycle management."""

import asyncio
from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
)
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.core import (
    reconcile_core,
    run_core_database_helm_action,
)

CORE_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    CoreComponentType.AMF: frozenset({CoreComponentType.NRF, CoreComponentType.UDM}),
    CoreComponentType.SMF: frozenset({CoreComponentType.NRF, CoreComponentType.UDM}),
}


class CoreManagement(HelmManagement):
    """5G core deployemnt lifecycle management class."""

    def reconcile(self):
        """Ensure the 5G core is ready for deployement by resolving its components' configs."""

        super().reconcile()

        reconcile_core(
            core_meta=self.mutatable_metamodel.core,
            core_deployment=self.deployment_model.core_deployment,
            slices=self.mutatable_metamodel.slices,
        )

    async def run_action(
            self,
            action: Literal["prepare", "install", "uninstall"],
            components: list[str] | None = None,
            node: str | None = None,
            **kwargs,
        ):
        """Run Helm action on 5G core components."""

        await super().run_action(
            category=Category5G.CORE,
            action=action,
            components=components,
            node=node,
            **kwargs,
        )


    async def prepare(self, components: list[str] | None = None, **kwargs):
        """Prepare Helm charts for 5G core components."""
        await self.run_action(action="prepare", components=components, **kwargs)


    async def install(self, components: list[str] | None = None, **kwargs):
        """Install 5G core components via Helm."""
        await self.run_action(action="install", components=components, **kwargs)


    async def uninstall(self, components: list[str] | None = None, **kwargs):
        """Uninstall 5G core components via Helm."""
        await self.run_action(action="uninstall", components=components, **kwargs)


    async def run_database_action(
            self,
            action: Literal["prepare", "install", "uninstall"],
            node: str | None = None,
            force: bool = False,
            **kwargs,
        ):
        """Run 5G core database Helm action."""

        target_node = node or self.deployment_model.params.k8s.master_node
        if not target_node or target_node not in self.deployment_model.nodes:
            raise RuntimeError(
                f"Target node {target_node!r} for database Helm action is invalid or missing from deployment model."
            )

        node_data = self.deployment_model.nodes[target_node]

        result = await run_core_database_helm_action(
            core_meta=self.metamodel.core,
            core_deployment=self.deployment_model.core_deployment,
            action=action,
            node=target_node,
            inventory=get_ansible_inventory_line(resource_name=target_node, resource_data=node_data),
            ansible_params=self.deployment_model.params.ansible,
            force=force,
            )
    
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                **kwargs,
            )


    async def deploy(
            self,
            components: list[str] | None = None,
            node: str | None = None,
            force: bool = False,
            order: ComponentDependencyGraph | None = CORE_COMPONENT_DEPENDENCIES,
            **kwargs,
        ):
        """
        Orchestrate full 5G core deployment.
        Prepares all charts (database + components), installs the database first, then installs 5G core components.
        """

        # prepare everything (database + components)
        await asyncio.gather(
            self.run_database_action(action="prepare", node=node, force=force, **kwargs),
            self.prepare(components=components, node=node, force=force, **kwargs),
        )

        # install database first
        await self.run_database_action(action="install", node=node, **kwargs)

        # install remaining core components in order if desired
        await self.install(components=components, node=node, force=force, order=order, **kwargs)


    async def remove(
            self,
            components: list[str] | None = None,
            node: str | None = None,
            **kwargs,
        ):
        """Remove/tear down 5G core deployment."""

        await asyncio.gather(
            self.uninstall(components=components, node=node, **kwargs),
            self.run_database_action(action="uninstall", node=node, **kwargs),
        )
