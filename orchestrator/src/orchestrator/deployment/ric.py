"""RICs lifecycle management."""

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ric import RICComponentType
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.ric import reconcile_rics


RIC_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RICComponentType.APPMGR: frozenset({RICComponentType.DBAAS}),
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
    """RICs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the RICs are ready to be managed."""

        super().reconcile()

        reconcile_rics(
            rics_meta=self.mutatable_metamodel.rics,
            rics_k8s=self.deployment_model.rics,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on RICs."""
        await super().run_action(category=Category5G.RIC, **kwargs)


    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)
