"""RAN Intelligent Controller lifecycle management."""

from typing import Any, override

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.ric import RICComponent, RICComponentType

from ifran.deployment.helm import HelmManagement
from ifran.models.ric import DeployedRICComponent, RICImplementation
from ifran.utils.common_5g import ComponentDependencyGraph
from ifran.utils.ric import create_xapp_namespace, reconcile_ric

RIC_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RICComponentType.A1MEDIATOR: frozenset(
        {
            RICComponentType.DBAAS,
        }
    ),
    RICComponentType.XAPP_ONBOARDER: frozenset(
        {
            RICComponentType.APPMGR,
            RICComponentType.DBAAS,
            RICComponentType.CHARTMUSEUM,
        }
    ),
    RICComponentType.APPMGR: frozenset(
        {
            RICComponentType.DBAAS,
            RICComponentType.CHARTMUSEUM,
        }
    ),
    RICComponentType.RTMGR: frozenset(
        {
            RICComponentType.DBAAS,
            RICComponentType.APPMGR,
            RICComponentType.E2MGR,
            RICComponentType.SUBMGR,
        }
    ),
    RICComponentType.E2MGR: frozenset(
        {
            RICComponentType.DBAAS,
            RICComponentType.APPMGR,
        }
    ),
    RICComponentType.E2TERM: frozenset(
        {
            RICComponentType.DBAAS,
            RICComponentType.APPMGR,
            RICComponentType.RTMGR,
            RICComponentType.E2MGR,
        }
    ),
    RICComponentType.SUBMGR: frozenset(
        {
            RICComponentType.DBAAS,
            RICComponentType.APPMGR,
            RICComponentType.E2MGR,
        }
    ),
}


class RICManagement(HelmManagement):
    """RIC lifecycle management class."""

    @override
    def reconcile(self) -> None:
        """Ensure RIC is ready to be managed."""

        super().reconcile()

        reconcile_ric(
            metamodel=self.mutable_metamodel,
            deployment_model=self.deployment_model,
        )

    async def run_action(self, **kwargs) -> dict[str, str] | None:
        """Run Helm action on 5G RIC components."""
        return await super().run_action(category=Category5G.RIC, **kwargs)

    # NOTE don't use kwargs to expose the function signature
    @override
    def add_component(
        self,
        name: str,
        component_meta: RICComponent | None = None,
        component_deployment: DeployedRICComponent | None = None,
        merged: dict[str, Any] | None = None,
    ) -> None:
        """Add or update a RIC component if it exists."""
        super().add_component(
            name=name,
            category=Category5G.RIC,
            component_meta=component_meta,
            component_deployment=component_deployment,
            merged=merged,
        )

    @override
    def remove_component(self, name: str) -> None:
        """Remove a RIC component."""
        super().remove_component(category=Category5G.RIC, name=name)

    @override
    async def install(
        self,
        components: list[str] | None = None,
        node: str | None = None,
        order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
        quiet: bool = False,
        **kwargs,
    ) -> None:
        """Install RIC components."""

        node_name, node_data = self._get_deployment_node(node)

        if self.deployment_model.ric.implementation is RICImplementation.ORAN_SC:
            # osc ric needs an extra xapp namespace
            await create_xapp_namespace(
                node_name=node_name,
                node_data=node_data,
                ansible_params=self.deployment_model.params.ansible,
                quiet=quiet,
            )

        await super().install(components=components, node=node, order=order, quiet=quiet, **kwargs)

    # override dependency graph
    @override
    async def deploy(
        self,
        order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
        **kwargs,
    ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)
