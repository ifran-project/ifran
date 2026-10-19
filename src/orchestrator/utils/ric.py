"""RIC utilities and helpers."""

from metamodel.models.metamodel import MetaModel

from orchestrator.models.ansible import AnsibleParams
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.provisioning import ProvisionableNode
from orchestrator.models.ric import (
    ORANSCAdvancedRICConfig,
    RICComponentType,
    RICImplementation,
)
from orchestrator.utils.ansible import get_ansible_inventory_line, run_ansible_playbook
from orchestrator.utils.common_5g import reconcile_5g_component
from orchestrator.utils.k8s import build_k8s_safe

OFFICIAL_ORAN_SC_M_TYPES = {
    RICComponentType.A1MEDIATOR,
    RICComponentType.DBAAS,
    RICComponentType.E2MGR,
    RICComponentType.E2TERM,
    RICComponentType.RTMGR,
    RICComponentType.SUBMGR,
}

# Namespace names defined by the O-RAN SC deployment convention.
# Keep these here as the single source of truth:
# component reconciliation feeds the namespace into Helm values and generated Service names.
ORAN_SC_PLATFORM_NAMESPACE = "ricplt"
ORAN_SC_XAPP_NAMESPACE = "ricxapp"


async def create_xapp_namespace(
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        quiet: bool = False,
    ) -> None:
    """Run playbook to create xApp namespace before OSC RIC installation."""

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
        roles_paths=ansible_params.roles_paths,
        quiet=quiet,
    )


def build_official_oran_sc_service_name(
        component_type: RICComponentType,
        namespace: str,
    ) -> str:
    """Return the primary service exposed by an official M-release chart."""

    if component_type is RICComponentType.E2TERM:
        return f"service-{namespace}-e2term-sctp-alpha"
    if component_type is RICComponentType.DBAAS:
        return f"service-{namespace}-dbaas-tcp"
    return f"service-{namespace}-{component_type.value}-http"


def reconcile_ric(
        metamodel: MetaModel,
        deployment_model: DeploymentModel,
    ) -> None:
    """Ensure RIC is ready to be managed."""

    ric_meta = metamodel.ric
    ric_deployment = deployment_model.ric

    k8s_params = deployment_model.params.k8s

    ric_services: dict[str, str] = {}

    for component_name, component_meta in ric_meta.components.items():
        component_deployment = ric_deployment.components[component_name]

        # reconcile first because osc-ric official chart service names include the computed namespace
        reconcile_5g_component(
            component_name=component_name,
            component_meta=component_meta,
            component_deployment=component_deployment,
            k8s_params=k8s_params,
        )

        if component_deployment.implementation is RICImplementation.ORAN_SC:
            component_deployment.namespace = ORAN_SC_PLATFORM_NAMESPACE

            # some osc ric components don't have a config.yaml template file to be rendered
            if component_meta.type in OFFICIAL_ORAN_SC_M_TYPES:
                component_deployment.rendered_files = ["values.yaml"]

                service_name = build_official_oran_sc_service_name(
                    component_type=component_meta.type,
                    namespace=component_deployment.namespace,
                )
            else:
                service_name = build_k8s_safe(f"{component_deployment.implementation}-{component_name}")

            ric_services[component_name] = service_name

            if component_meta.type is RICComponentType.DBAAS:
                # osc ric dbaas is a statefulset
                component_deployment.kind = "StatefulSet"

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
        if type_counts[component_meta.type] == 1 and component_deployment.implementation is RICImplementation.ORAN_SC
    }

    # populate 'service_name' and 'ric_type_services' in osc ric advanced config
    for component_name, component_deployment in ric_deployment.components.items():
        if component_deployment.implementation is RICImplementation.ORAN_SC:
            component_deployment.advanced_config = component_deployment.advanced_config or ORANSCAdvancedRICConfig(
                service_name=ric_services[component_name],
                ric_type_services=ric_type_services.copy(),
            )
