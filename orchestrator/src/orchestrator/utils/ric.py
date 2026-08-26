"""RIC utilities and helpers."""

from orchestrator.models.deployment.ric import K8SRICComponent, RICDeployment
from orchestrator.models.meta.ric import RIC, RICComponentType
from orchestrator.utils.common import build_safe_helm_name, sync_dict_keys
from orchestrator.utils.common_5g import reconcile_5g_component


E2_COMPONENT_TYPES = {RICComponentType.RIC, RICComponentType.E2TERM}


def build_ric_service_name(
        ric_name: str,
        component_name: str,
        ric_meta: RIC,
    ) -> str:
    """Build the Helm-managed service name for a RIC component."""

    return build_safe_helm_name(
        f"{ric_meta.implementation.value}-{ric_name}-{component_name}"
    )


def get_ric_e2_components(
        rics_meta: dict[str, RIC],
        rics_k8s: dict[str, RICDeployment],
    ) -> dict[str, K8SRICComponent]:
    """Build RIC references pointing to E2-facing components."""

    registry: dict[str, K8SRICComponent] = {}
    for ric_name, ric_meta in rics_meta.items():
        e2_components = {
            component_name: rics_k8s[ric_name].components[component_name]
            for component_name, component_meta in ric_meta.components.items()
            if component_meta.type in E2_COMPONENT_TYPES
            and component_name in rics_k8s[ric_name].components
        }

        for component_name, component_k8s in e2_components.items():
            # Explicit reference, e.g. osc.alpha
            registry[f"{ric_name}.{component_name}"] = component_k8s

        # Allow ric: osc only when the E2 target is unambiguous
        if len(e2_components) == 1:
            registry[ric_name] = next(iter(e2_components.values()))

    return registry


def reconcile_rics(
        rics_meta: dict[str, RIC],
        rics_k8s: dict[str, RICDeployment],
    ) -> None:
    """Ensure RICs are ready to be managed."""

    for ric_name, ric_meta in rics_meta.items():
        ric_k8s = rics_k8s[ric_name]

        sync_dict_keys(
            target_dict=ric_k8s.components,
            source_dict=ric_meta.components,
            default_factory=K8SRICComponent,
        )

        ric_services = {
            component_name: build_ric_service_name(
                ric_name=ric_name,
                component_name=component_name,
                ric_meta=ric_meta,
            )
            for component_name in ric_meta.components
        }
        type_counts = {
            component_meta.type: sum(
                sibling.type is component_meta.type
                for sibling in ric_meta.components.values()
            )
            for component_meta in ric_meta.components.values()
        }
        ric_type_services = {
            component_meta.type.value: ric_services[component_name]
            for component_name, component_meta in ric_meta.components.items()
            if type_counts[component_meta.type] == 1
        }

        for component_name, component_meta in ric_meta.components.items():
            component_k8s = ric_k8s.components[component_name]
            component_k8s.service_name = ric_services[component_name]
            component_k8s.ric_services = ric_services.copy()
            component_k8s.ric_type_services = ric_type_services.copy()

            reconcile_5g_component(
                component_name=component_name,
                component_meta=component_meta,
                component_k8s=component_k8s,
            )
