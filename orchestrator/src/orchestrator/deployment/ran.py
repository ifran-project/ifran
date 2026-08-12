"""RAN deployemnt lifecycle management."""

from typing import Literal

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

    def reconcile(self):
        """Ensure the 5G RAN is ready for deployement by resolving its components' configs."""

        super().reconcile()

        # get amfs from metamodel
        amfs = get_5g_components_by_type(self.metamodel.core).get(CoreComponentType.AMF, {})

        # get amfs from deployment model (keys of meta and deployment models should be in sync at this point)
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


    async def run_action(
        self,
        action: Literal["prepare", "install", "uninstall"],
        components: list[str] | None = None,
        node: str | None = None,
        **kwargs,
        ):
        """Run Helm action on RAN components."""

        await super().run_action(
            category=Category5G.RAN,
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


    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
            **kwargs,
        ):
        """Orchestrate full RAN deployment."""

        # prepare everything
        await self.prepare(**kwargs)

        # install ran components in order if desired
        await self.install(order=order, **kwargs)


    # only for naming consistency
    async def remove(self, **kwargs):
        """Remove/tear down RAN deployment."""
        await self.uninstall(**kwargs),
