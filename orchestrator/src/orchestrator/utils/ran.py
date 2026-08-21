"""5G RAN utilities and helpers."""

from pydantic import IPvAnyAddress, IPvAnyNetwork

from orchestrator.models.deployment.k8s import K8SComponent
from orchestrator.models.deployment.provisioning import (
    ProvisionableRU,
    ProvisioningCategory,
)
from orchestrator.models.deployment.ran import RANDeployment
from orchestrator.models.meta.ran import (
    RAN,
    RANComponent,
    RANComponentType,
)
from orchestrator.models.meta.ru import RU, RUType
from orchestrator.models.meta.slice import Slice
from orchestrator.utils.common import generate_random_ip
from orchestrator.utils.common_5g import (
    reconcile_5g_component,
    resolve_component_reference,
    resolve_ru_reference,
)
from orchestrator.utils.radio import (
    derive_ran_radio_config,
)


def resolve_ran_component_references(
        component_name: str,
        component_meta: RANComponent,
        rus_meta: dict[str, RU],
        rus_provisioning: dict[str, ProvisionableRU],
        amfs: dict[str, K8SComponent],
        rics: dict[str, K8SComponent],
    ) -> None:
    """Resolve name references (ru, amf, ric) of 5G components in a RAN component."""

    resolve_ru_reference(
        component_name=component_name,
        component_meta=component_meta,
        rus_meta=rus_meta,
        rus_provisioning=rus_provisioning,
    )

    references = [
        {
            "ref_attribute": "amf", # XXX amfs are assumed to not be using multus. That case should be handled by the advanced user!
            "registry": amfs,
            "ready_attribute": "is_installed",
            "value_attribute": "network_info",
        },
        {
            "ref_attribute": "ric", # XXX same for rics
            "registry": rics,
            "ready_attribute": "is_installed",
            "value_attribute": "network_info",
        },
    ]

    for reference in references:
        resolve_component_reference(
            component_name=component_name,
            component_meta=component_meta,
            **reference,
        )


def resolve_split_ran_references(
        ran_meta: RAN,
        ran_deployment: RANDeployment,
        pod_network_cidr: IPvAnyNetwork,
    ) -> None:
    """Resolve the cyclic dependencies between split RAN components by assigning them static IPs."""

    split_types = {
        RANComponentType.CU,
        RANComponentType.CU_CP,
        RANComponentType.CU_UP,
        RANComponentType.DU,
    }

    # assign a static ip to every split component if not already set
    # if user wants to go with Multus, it's up to them to resolve this
    used_ips: set[IPvAnyAddress] = set()
    ip_mapping: dict[str, IPvAnyAddress] = {}
    for name, component_meta in ran_meta.components.items():
        if component_meta.type in split_types:
            component_k8s = ran_deployment.components[name] # meta and deployment should be in sync by this point
            component_k8s.static_pod_ip = component_k8s.static_pod_ip or generate_random_ip(pod_network_cidr, used_ips)
            ip_mapping[name] = component_k8s.static_pod_ip # build mapping between component names and ips
            used_ips.add(component_k8s.static_pod_ip)

    # resolve the inter-component references
    for name, component_meta in ran_meta.components.items():
        if component_meta.type not in split_types:
            continue

        for ref_attribute in ("du", "cu_cp", "cu_up"):
            if not hasattr(component_meta.config, ref_attribute):
                continue

            reference = getattr(component_meta.config, ref_attribute)

            # already has an ip / resolved value
            if not isinstance(reference, str):
                continue

            target_ip = ip_mapping.get(reference)

            if target_ip is None:
                raise ValueError(f"Could not resolve IP for RAN component {name!r} reference to {reference!r}.")

            setattr(component_meta.config, ref_attribute, target_ip)


def reconcile_ran(
        ran_meta: RAN,
        ran_deployment: RANDeployment,
        pod_network_cidr: IPvAnyNetwork,
        slices: dict[str, Slice],
        rus_meta: dict[str, RU],
        rus_provisioning: dict[str, ProvisionableRU],
        amfs: dict[str, K8SComponent],
        rics: dict[str, K8SComponent],
    ) -> None:
    """Ensure RAN is ready for deployment."""

    resolve_split_ran_references(
        ran_meta=ran_meta,
        ran_deployment=ran_deployment,
        pod_network_cidr=pod_network_cidr,
    )

    # add simulated rus as provisioned to be considered as ready
    merged_rus = rus_provisioning | {
        name: ProvisionableRU(category=ProvisioningCategory.RU, is_provisioned=True)
        for name, ru in rus_meta.items()
        if ru.type is RUType.SIMULATED
        }

    for name, component_meta in ran_meta.components.items():
        # meta and deployment model ran component keys are suppposed to be synced by thi point
        component_k8s = ran_deployment.components[name]

        reconcile_5g_component(
            component_name=name,
            component_meta=component_meta,
            component_k8s=component_k8s,
            slices=slices,
        )

        resolve_ran_component_references(
            component_name=name,
            component_meta=component_meta,
            rus_meta=rus_meta,
            rus_provisioning=merged_rus,
            amfs=amfs,
            rics=rics,
        )

        # derive implementation-specific radio paramaters for gnb and du after ru name reference resolution
        if component_meta.type in [RANComponentType.GNB, RANComponentType.DU]:
            derive_ran_radio_config(component_meta)
