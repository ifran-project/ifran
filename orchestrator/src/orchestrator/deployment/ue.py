"""UEs lifecycle management."""

from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.utils.common_5g import RANComponentType, get_5g_components_by_type
from orchestrator.utils.ue import reconcile_ues


class UEManagement(HelmManagement):
    """UEs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the UEs are ready to be managed."""

        super().reconcile()

        # get gnbs and dus from metamodel
        grouped = get_5g_components_by_type(self.mutatable_metamodel.ran.components)
        gnbs = grouped.get(RANComponentType.GNB, {})
        dus = grouped.get(RANComponentType.DU, {})
        gnb_components_meta = gnbs | dus # gnbs + dus

        # get gnbs and dus from deployment model (keys of meta and deployment models should be in sync by this point)
        gnb_components_k8s = {k: self.deployment_model.ran_deployment.components[k] for k, v in gnb_components_meta.items()}

        reconcile_ues(
            ues_meta=self.mutatable_metamodel.ues,
            ues_k8s=self.deployment_model.simulated_ues,
            slices=self.mutatable_metamodel.slices,
            gnb_components_meta=gnb_components_meta,
            gnb_components_k8s=gnb_components_k8s,
            rus_meta=self.mutatable_metamodel.rus,
            rus_provisioning=self.deployment_model.rus,
        )


    async def run_action(
        self,
        action: Literal["prepare", "install", "uninstall"],
        ues: list[str] | None = None,
        node: str | None = None,
        **kwargs,
        ) -> None:
        """Run Helm action on simulated UEs."""

        await super().run_action(
            category=Category5G.UE,
            action=action,
            components=ues,
            node=node,
            **kwargs,
        )


    async def prepare(self, ues: list[str] | None = None, **kwargs) -> None:
        """Prepare Helm charts for simulated UEs."""
        await self.run_action(action="prepare", ues=ues, **kwargs)


    async def install(self, ues: list[str] | None = None, **kwargs) -> None:
        """Install simulated UEs via Helm."""
        await self.run_action(action="install", ues=ues, **kwargs)


    async def uninstall(self, ues: list[str] | None = None, **kwargs) -> None:
        """Uninstall simulated UEs via Helm."""
        await self.run_action(action="uninstall", ues=ues, **kwargs)


    async def deploy(self, **kwargs) -> None:
        """Prepare and install simulated UEs via Helm."""
        await self.prepare(**kwargs)
        await self.install(**kwargs)


    # only for naming consistency
    async def remove(self, **kwargs) -> None:
        """Remove/uninstall simulated UEs via Helm."""
        await self.uninstall(**kwargs)
