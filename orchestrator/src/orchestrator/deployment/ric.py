"""RICs lifecycle management."""

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.utils.ric import reconcile_rics


class RICManagement(HelmManagement):
    """RICs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the RICs are ready to be managed."""

        super().reconcile()

        reconcile_rics(
            rics_meta=self.mutable_metamodel.rics,
            rics_k8s=self.deployment_model.rics,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on RICs."""
        await super().run_action(category=Category5G.RIC, **kwargs)
