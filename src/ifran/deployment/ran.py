"""RAN deployment lifecycle management."""

from typing import Any, override

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.ran import RANComponent, RANComponentType

from ifran.deployment.helm import HelmManagement
from ifran.models.ran import DeployedRANComponent
from ifran.utils.common_5g import (
    ComponentDependencyGraph,
)
from ifran.utils.ran import reconcile_ran

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
    async def run_action(self, **kwargs) -> dict[str, str] | None:
        """Run Helm action on RAN components."""
        return await super().run_action(category=Category5G.RAN, **kwargs)


    # NOTE don't use kwargs to expose the function signature
    @override
    def add_component(
        self,
        name: str,
        component_meta: RANComponent | None = None,
        component_deployment: DeployedRANComponent | None = None,
        merged: dict[str, Any] | None = None,
        ) -> None:
        """Add or update a RAN component if it exists."""
        super().add_component(
            name=name,
            category=Category5G.RAN,
            component_meta=component_meta,
            component_deployment=component_deployment,
            merged=merged,
        )

    @override
    def remove_component(self, name: str) -> None:
        """Remove a RAN component."""
        super().remove_component(category=Category5G.RAN, name=name)


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
