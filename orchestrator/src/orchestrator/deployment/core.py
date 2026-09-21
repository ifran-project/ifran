"""5G core deployment lifecycle management."""

import asyncio
from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType
from orchestrator.models.meta.ran import RANComponentType
from orchestrator.utils.ansible import (
    handle_ansible_result_exception,
)
from orchestrator.utils.common_5g import (
    ComponentDependencyGraph,
    resolve_component_slices,
)
from orchestrator.utils.core import (
    get_5g_components_by_type,
    reconcile_core,
    run_core_database_helm_action,
    run_parallel_database_subscriber_action,
)
from orchestrator.utils.ue import resolve_gnb_reference

CORE_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    CoreComponentType.BSF: frozenset({
        CoreComponentType.NSSF,
    }),
    CoreComponentType.NSSF: frozenset({
        CoreComponentType.UDR,
    }),
    CoreComponentType.UDR: frozenset({
        CoreComponentType.UDM,
    }),
    CoreComponentType.UDM: frozenset({
        CoreComponentType.PCF,
    }),
    CoreComponentType.PCF: frozenset({
        CoreComponentType.SMF,
    }),
    CoreComponentType.UPF: frozenset({
        CoreComponentType.SMF,
    }),
    CoreComponentType.SMF: frozenset({
        CoreComponentType.AUSF,
    }),
    CoreComponentType.AUSF: frozenset({
        CoreComponentType.AMF,
    }),
    CoreComponentType.AMF: frozenset({
        CoreComponentType.NRF,
    }),
    CoreComponentType.CHF: frozenset({
        CoreComponentType.NRF,
    }),
    CoreComponentType.NEF: frozenset({
        CoreComponentType.NRF,
    }),
}


class CoreManagement(HelmManagement):
    """5G core deployment lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the 5G core is ready for deployment by resolving its components' configs."""

        super().reconcile()

        reconcile_core(
            core_meta=self.mutable_metamodel.core,
            core_deployment=self.deployment_model.core_deployment,
            pod_network_cidr=self.deployment_model.params.k8s.pod_network_cidr,
            slices=self.mutable_metamodel.slices,
        )

        # get gnbs and dus from metamodel
        grouped = get_5g_components_by_type(self.mutable_metamodel.ran.components)
        gnbs = grouped.get(RANComponentType.GNB, {})
        dus = grouped.get(RANComponentType.DU, {})
        gnb_components_meta = gnbs | dus # gnbs + dus

        # resolve slices references and gnb reference in ues to prepare them for database registration
        for ue_name, ue_meta in self.mutable_metamodel.ues.items():
            resolve_component_slices(
                component_name=ue_name,
                component_meta=ue_meta,
                slices=self.mutable_metamodel.slices,
            )

            resolve_gnb_reference(
                ue_name=ue_name,
                ue_meta=ue_meta,
                gnb_components_meta=gnb_components_meta,
            )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on 5G core components."""
        await super().run_action(category=Category5G.CORE, **kwargs)


    async def run_database_action(
            self,
            action: Literal["prepare", "install", "uninstall"],
            node: str | None = None,
            force: bool = False,
            ignore_invalid_states: bool = True,
            ignore_failures: bool = False,
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
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
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

        all_ues = self.mutable_metamodel.ues

        # filter for specific components if requested
        if ues is None:
            target_ues = all_ues
        else:
            target_ues = {k: v for k, v in all_ues.items() if k in ues}

        await run_parallel_database_subscriber_action(
            ues=target_ues,
            core_implementation=self.metamodel.core.implementation,
            database_ip=self.deployment_model.core_deployment.database.ip,
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


    # override dependency graph
    async def install(
            self,
            order: ComponentDependencyGraph | None = CORE_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Install 5G core components."""
        await super().install(order=order, **kwargs)


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
