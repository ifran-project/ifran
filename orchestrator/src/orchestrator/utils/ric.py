"""RIC utilities and helpers."""

from orchestrator.models.deployment.ric import RICDeployment
from orchestrator.models.meta.ric import RIC
from orchestrator.utils.common_5g import reconcile_5g_component


def reconcile_rics(
        rics_meta: dict[str, RIC],
        rics_k8s: dict[str, RICDeployment],
    ) -> None:
    """Ensure RICs are ready to be managed."""

    for name, ue_meta in rics_meta.items():

        reconcile_5g_component(
            component_name=name,
            component_meta=ue_meta,
            component_k8s=rics_k8s[name], # rics meta and deployment keys should be synced by this point
        )
