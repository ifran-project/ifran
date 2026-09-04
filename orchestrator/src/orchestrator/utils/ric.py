"""RIC utilities and helpers."""

from orchestrator.models.deployment.ric import K8SRICComponent, RICDeployment
from orchestrator.models.meta.ric import RIC, RICComponent, RICComponentType, RICImplementation
from orchestrator.utils.common import build_safe_helm_name, sync_dict_keys
from orchestrator.utils.common_5g import ComponentDependencyGraph, reconcile_5g_component
from orchestrator.utils.ansible import get_ansible_inventory_line, run_ansible_playbook
from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.provisioning import ProvisionableNode


E2_COMPONENT_TYPES = {RICComponentType.RIC, RICComponentType.E2TERM}


RIC_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RICComponentType.A1MEDIATOR: frozenset({
        RICComponentType.DBAAS,
    }),
    RICComponentType.XAPP_ONBOARDER: frozenset({
        RICComponentType.APPMGR,
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.APPMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.RTMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
        RICComponentType.SUBMGR,
    }),
    RICComponentType.E2MGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
    }),
    RICComponentType.E2TERM: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.RTMGR,
        RICComponentType.E2MGR,
    }),
    RICComponentType.SUBMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
    }),
}


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


async def create_ric_namespaces(
        components: dict[str, RICComponent],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
    ) -> None:
    """Create the cross-namespace prerequisite when installing OSC components.

    Use the existing remote runner and cluster credentials, without a new role
    or shell commands. state=present also succeeds when the namespace exists.
    The release namespace remains Helm's responsibility.
    """
    if not any(meta.implementation == RICImplementation.ORAN_SC for meta in components.values()):
        return
    await run_ansible_playbook(
        playbook=[{
            "hosts": node_name,
            "gather_facts": False,
            "become": True,
            "tasks": [{
                "name": "Create xApp namespace before OSC installation",
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


def build_ric_component_name(ric_name: str, component_name: str) -> str:
    """Build the RIC-scoped key used by Helm and component selection."""
    return f"{ric_name}-{component_name}"


def get_ric_helm_inputs(meta: RICComponent) -> dict:
    """Supply upstream chart conventions to the standard Helm roles."""
    if meta.implementation == RICImplementation.ORAN_SC and meta.type in OFFICIAL_ORAN_SC_M_TYPES:
        return {"rendered_files": ["values.yaml"]}
    return {}


def get_ric_helm_components(
        rics_meta: dict[str, RIC],
        rics_k8s: dict[str, RICDeployment],
    ) -> tuple[dict[str, RICComponent], dict[str, K8SRICComponent]]:
    """Flatten RIC components with matching, collision-checked deployment keys."""
    meta, deployed = {}, {}
    normalized_names = set()
    for ric_name, ric_meta in rics_meta.items():
        for component_name, component_meta in ric_meta.components.items():
            name = build_ric_component_name(ric_name, component_name)
            normalized = build_safe_helm_name(name)
            if normalized in normalized_names:
                raise ValueError(f"Duplicate normalized RIC component name: {name}")
            normalized_names.add(normalized)
            meta[name] = component_meta
            deployed[name] = rics_k8s[ric_name].components[component_name]
    return meta, deployed


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


def build_ric_service_name(
        ric_name: str,
        component_name: str,
        ric_meta: RIC,
    ) -> str:
    """Build the Helm-managed service name for a RIC component."""

    return build_safe_helm_name(
        f"{ric_meta.implementation.value}-{build_ric_component_name(ric_name, component_name)}"
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

        # Reconcile first because official chart service names include the
        # computed namespace.
        for component_name, component_meta in ric_meta.components.items():
            reconcile_5g_component(
                component_name=component_name,
                component_meta=component_meta,
                component_k8s=ric_k8s.components[component_name],
            )
            if ric_meta.implementation is RICImplementation.ORAN_SC:
                ric_k8s.components[component_name].namespace = (
                    ORAN_SC_PLATFORM_NAMESPACE
                )

        ric_services = {}
        for component_name, component_meta in ric_meta.components.items():
            component_k8s = ric_k8s.components[component_name]
            if (
                ric_meta.implementation is RICImplementation.ORAN_SC
                and component_meta.type in OFFICIAL_ORAN_SC_M_TYPES
            ):
                service_name = build_official_oran_sc_service_name(
                    component_type=component_meta.type,
                    namespace=component_k8s.namespace,
                )
            else:
                service_name = build_ric_service_name(
                    ric_name=ric_name,
                    component_name=component_name,
                    ric_meta=ric_meta,
                )
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
            component_k8s = ric_k8s.components[component_name]
            component_k8s.service_name = ric_services[component_name]
            component_k8s.ric_type_services = ric_type_services.copy()
