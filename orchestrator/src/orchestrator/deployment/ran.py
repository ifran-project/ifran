"""RAN deployemnt lifecycle management."""

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType
from orchestrator.models.meta.ran import RANComponentType
from orchestrator.utils.common_5g import (
    ComponentDependencyGraph,
    get_5g_components_by_type,
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
    """RAN deployemnt lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the 5G RAN is ready for deployement by resolving its components' configs."""

        super().reconcile()

        # get amfs from metamodel
        amfs = get_5g_components_by_type(self.metamodel.core.components).get(CoreComponentType.AMF, {})

        # get amfs from deployment model (keys of meta and deployment models should be in sync by this point)
        amfs_deployment = {k: self.deployment_model.core_deployment.components[k] for k, v in amfs.items()}

        reconcile_ran(
            ran_meta=self.mutatable_metamodel.ran,
            ran_deployment=self.deployment_model.ran_deployment,
            pod_network_cidr=self.deployment_model.params.k8s.pod_network_cidr,
            slices=self.metamodel.slices,
            rus_meta=self.metamodel.rus,
            rus_provisioning=self.deployment_model.rus,
            amfs=amfs_deployment,
            rics=self.deployment_model.rics,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on RAN components."""
        await super().run_action(category=Category5G.RAN, **kwargs)


    # override dependency graph
    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate full RAN deployment."""
        await super().deploy(order=order, **kwargs)
