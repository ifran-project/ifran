"""RIC utilities and helpers."""

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.provisioning import ProvisionableNode
from orchestrator.models.deployment.ric import K8SRICComponent, RICDeployment
from orchestrator.models.meta.ric import (
    RIC,
    ORANSCAdvancedRICConfig,
    RICComponentType,
    RICImplementation,
)
from orchestrator.utils.ansible import get_ansible_inventory_line, run_ansible_playbook
from orchestrator.utils.common import build_k8s_safe
from orchestrator.utils.common_5g import reconcile_5g_component

OFFICIAL_ORAN_SC_M_TYPES = {
    RICComponentType.A1MEDIATOR,
    RICComponentType.DBAAS,
    RICComponentType.E2MGR,
    RICComponentType.E2TERM,
    RICComponentType.RTMGR,
    RICComponentType.SUBMGR,
}

# Namespace names defined by the O-RAN SC deployment convention.  Keep these
# here as the single source of truth: component reconciliation feeds the
# namespace into Helm values and generated Service names.
ORAN_SC_PLATFORM_NAMESPACE = "ricplt"
ORAN_SC_XAPP_NAMESPACE = "ricxapp"


async def create_xapp_namespace(
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
    ) -> None:
    """Create xApp namespace before OSC RIC installation."""

    await run_ansible_playbook(
        playbook=[{
            "hosts": node_name,
            "gather_facts": False,
            "become": True,
            "tasks": [{
                "name": "Create xApp namespace before OSC RIC installation",
                "kubernetes.core.k8s": {
                    "api_version": "v1",
                    "kind": "Namespace",
                    "name": ORAN_SC_XAPP_NAMESPACE,
                    "state": "present",
                },
            }],
        }],
        runner_path=f"{ansible_params.runner_path}/ric/namespaces",
        inventory=get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        roles_path=ansible_params.roles_path,
    )


def build_official_oran_sc_service_name(
        component_type: RICComponentType,
        namespace: str,
    ) -> str:
    """Return the primary service exposed by an official M-release chart."""

    if component_type is RICComponentType.E2TERM:
        return f"service-{namespace}-e2term-sctp-alpha"
    elif component_type is RICComponentType.DBAAS:
        return f"service-{namespace}-dbaas-tcp"
    else:
        return f"service-{namespace}-{component_type.value}-http"


def get_ric_e2_components(
        ric_meta: RIC,
        ric_k8s: RICDeployment,
    ) -> dict[str, K8SRICComponent]:
    """Build RIC references pointing to E2-facing components."""

    # keys of meta and deployment models should be in sync by this point
    return {
        component_name: ric_k8s.components[component_name]
        for component_name, component_meta in ric_meta.components.items()
        if component_meta.type in [RICComponentType.RIC, RICComponentType.E2TERM]
    }


def reconcile_ric(
        ric_meta: RIC,
        ric_k8s: RICDeployment,
    ) -> None:
    """Ensure RIC is ready to be managed."""

    ric_services: dict[str, str] = {}

    # reconcile first because official chart service names include the computed namespace
    for component_name, component_meta in ric_meta.components.items():
        component_k8s = ric_k8s.components[component_name]

        reconcile_5g_component(
            component_name=component_name,
            component_meta=component_meta,
            component_k8s=component_k8s,
        )

        if component_meta.implementation is RICImplementation.ORAN_SC:
            component_k8s.namespace = ORAN_SC_PLATFORM_NAMESPACE

            # some osc ric components don't have a config.yaml template file to be rendered
            if component_meta.type in OFFICIAL_ORAN_SC_M_TYPES:
                component_k8s.rendered_files = ["values.yaml"]

                service_name = build_official_oran_sc_service_name(
                    component_type=component_meta.type,
                    namespace=component_k8s.namespace,
                )
            else:
                service_name = build_k8s_safe(f"{component_meta.implementation}-{component_name}")

            ric_services[component_name] = service_name

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
        if component_meta.implementation is RICImplementation.ORAN_SC:
            component_meta.advanced_config = component_meta.advanced_config or ORANSCAdvancedRICConfig(
                service_name=ric_services[component_name],
                ric_type_services=ric_type_services.copy(),
            )
