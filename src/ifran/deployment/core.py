"""5G core deployment lifecycle management."""

import asyncio
from typing import Any, Literal, override

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.core import CoreComponent, CoreComponentType

from ifran.deployment.helm import HelmManagement
from ifran.models.core import DeployedCoreComponent
from ifran.utils.ansible import (
    handle_ansible_result_exception,
)
from ifran.utils.common_5g import ComponentDependencyGraph
from ifran.utils.core import (
    reconcile_core,
    run_core_database_helm_action,
    run_parallel_database_subscriber_action,
)

CORE_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    CoreComponentType.BSF: frozenset(
        {
            CoreComponentType.NSSF,
        }
    ),
    CoreComponentType.NSSF: frozenset(
        {
            CoreComponentType.UDR,
        }
    ),
    CoreComponentType.UDR: frozenset(
        {
            CoreComponentType.UDM,
        }
    ),
    CoreComponentType.UDM: frozenset(
        {
            CoreComponentType.PCF,
        }
    ),
    CoreComponentType.PCF: frozenset(
        {
            CoreComponentType.SMF,
        }
    ),
    CoreComponentType.UPF: frozenset(
        {
            CoreComponentType.SMF,
        }
    ),
    CoreComponentType.SMF: frozenset(
        {
            CoreComponentType.AUSF,
        }
    ),
    CoreComponentType.AUSF: frozenset(
        {
            CoreComponentType.AMF,
        }
    ),
    CoreComponentType.AMF: frozenset(
        {
            CoreComponentType.NRF,
        }
    ),
    CoreComponentType.CHF: frozenset(
        {
            CoreComponentType.NRF,
        }
    ),
    CoreComponentType.NEF: frozenset(
        {
            CoreComponentType.NRF,
        }
    ),
}


class CoreManagement(HelmManagement):
    """5G core deployment lifecycle management class."""

    @override
    def reconcile(self) -> None:
        """Ensure the 5G core is ready for deployment by resolving its components' configs."""

        super().reconcile()

        reconcile_core(
            metamodel=self.mutable_metamodel,
            deployment_model=self.deployment_model,
        )

    # override category
    @override
    async def run_action(self, **kwargs) -> dict[str, str] | None:
        """Run Helm action on 5G core components."""
        return await super().run_action(category=Category5G.CORE, **kwargs)

    # NOTE don't use kwargs to expose the function signature
    @override
    def add_component(
        self,
        name: str,
        component_meta: CoreComponent | None = None,
        component_deployment: DeployedCoreComponent | None = None,
        merged: dict[str, Any] | None = None,
    ) -> None:
        """Add or update a 5G core component if it exists."""
        super().add_component(
            name=name,
            category=Category5G.CORE,
            component_meta=component_meta,
            component_deployment=component_deployment,
            merged=merged,
        )

    @override
    def remove_component(self, name: str) -> None:
        """Remove a 5G core component."""
        super().remove_component(category=Category5G.CORE, name=name)

    async def run_database_action(  # noqa: PLR0917
        self,
        action: Literal["prepare", "install", "uninstall"],
        node: str | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
        """Run 5G core database Helm action."""

        node_name, node_data = self._get_deployment_node(node)

        try:
            await run_core_database_helm_action(
                core_deployment=self.deployment_model.core,
                action=action,
                node_name=node_name,
                node_data=node_data,
                ansible_params=self.deployment_model.params.ansible,
                force=force,
                quiet=quiet,
            )
        except Exception as e:
            handle_ansible_result_exception(
                result=e,
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

        node_name, node_data = self._get_deployment_node(node)

        all_ues = self.mutable_metamodel.ues

        # filter for specific components if requested
        target_ues = all_ues if ues is None else {k: v for k, v in all_ues.items() if k in ues}

        await run_parallel_database_subscriber_action(
            ues=target_ues,
            core_implementation=self.deployment_model.core.implementation,
            database_ip=self.deployment_model.core.database_params.ip,
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
    @override
    async def install(
        self,
        order: ComponentDependencyGraph | None = CORE_COMPONENT_DEPENDENCIES,
        **kwargs,
    ) -> None:
        """Install 5G core components."""
        await super().install(order=order, **kwargs)

    @override
    async def deploy(
        self,
        node: str | None = None,
        order: ComponentDependencyGraph | None = CORE_COMPONENT_DEPENDENCIES,
        **kwargs,
    ) -> None:
        """
        Orchestrate full 5G core deployment.

        - Prepare all charts (database + components)
        - Install the database first
        - Install all 5G core components.
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
        await self.register_ues(node=node, **kwargs)

    @override
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
