"""UEs lifecycle management."""

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
            ues_k8s=self.deployment_model.containerized_ues,
            slices=self.mutatable_metamodel.slices,
            gnb_components_meta=gnb_components_meta,
            gnb_components_k8s=gnb_components_k8s,
            rus_meta=self.mutatable_metamodel.rus,
            rus_provisioning=self.deployment_model.rus,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on containerized UEs."""
        await super().run_action(category=Category5G.UE, **kwargs)
