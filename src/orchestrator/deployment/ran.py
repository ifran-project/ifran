"""RAN deployment lifecycle management."""

from typing import override

from metamodel.models.common import Category5G
from metamodel.models.ran import RANComponentType

from orchestrator.deployment.helm import HelmManagement
from orchestrator.utils.common_5g import (
    ComponentDependencyGraph,
)
from orchestrator.utils.ran import reconcile_ran

RAN_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RANComponentType.DU: frozenset({
        RANComponentType.CU,
        RANComponentType.CU_CP,
        RANComponentType.CU_UP,
    }),
    RANComponentType.CU_UP: frozenset({RANComponentType.CU_CP}),
}


class RANManagement(HelmManagement):
    """RAN deployment lifecycle management class."""

    @override
    def reconcile(self) -> None:
        """Ensure the 5G RAN is ready for deployment by resolving its components' configs."""

        super().reconcile()

        reconcile_ran(
            metamodel=self.mutable_metamodel,
            deployment_model=self.deployment_model,
        )


    # override category
    @override
    async def run_action(self, **kwargs) -> None:
        """Run Helm action on RAN components."""
        await super().run_action(category=Category5G.RAN, **kwargs)


    # override dependency graph
    @override
    async def install(
            self,
            order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Install RAN components."""
        await super().install(order=order, **kwargs)


    # override dependency graph
    @override
    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate full RAN deployment."""
        await super().deploy(order=order, **kwargs)
