"""RAN Intelligent Controller lifecycle management."""

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ric import RICComponentType, RICImplementation
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

    def reconcile(self) -> None:
        """Ensure RIC is ready to be managed."""

        super().reconcile()

        reconcile_ric(
            ric_meta=self.mutable_metamodel.ric,
            ric_k8s=self.deployment_model.ric_deployment,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on 5G RIC components."""
        await super().run_action(category=Category5G.RIC, **kwargs)


    async def install(
            self,
            components: list[str] | None = None,
            node: str | None = None,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Install RIC components."""

        # k8s master node is the deployment entry point by default
        node_name, node_data = self._get_master_node(node)

        if self.mutable_metamodel.ric.implementation is RICImplementation.ORAN_SC:
            await create_xapp_namespace(node_name, node_data, self.deployment_model.params.ansible)

        await super().install(components=components, node=node, order=order, **kwargs)


    # override dependency graph
    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)
