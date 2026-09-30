"""RAN Intelligent Controller lifecycle management."""

from typing import override

from metamodel.models.common import Category5G
from metamodel.models.ric import RICComponentType

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.ric import RICImplementation
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.ric import create_xapp_namespace, reconcile_ric

RIC_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RICComponentType.A1MEDIATOR: frozenset({
        RICComponentType.DBAAS,
    }),
    RICComponentType.XAPP_ONBOARDER: frozenset({
        RICComponentType.APPMGR,
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.APPMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.RTMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
        RICComponentType.SUBMGR,
    }),
    RICComponentType.E2MGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
    }),
    RICComponentType.E2TERM: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.RTMGR,
        RICComponentType.E2MGR,
    }),
    RICComponentType.SUBMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
    }),
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


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on 5G RIC components."""
        await super().run_action(category=Category5G.RIC, **kwargs)


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
            **kwargs,
        ) -> None:
        """Install RIC components."""

        node_name, node_data = self._get_deployment_node(node)

        if self.deployment_model.ric.implementation is RICImplementation.ORAN_SC:
            # osc ric needs an extra xapp namespace
            await create_xapp_namespace(node_name, node_data, self.deployment_model.params.ansible)

        await super().install(components=components, node=node, order=order, **kwargs)


    # override dependency graph
    @override
    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)
