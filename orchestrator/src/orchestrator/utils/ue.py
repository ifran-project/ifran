"""UE utilities and helpers."""

from pydantic import IPvAnyAddress

from orchestrator.models.deployment.provisioning import ProvisionableRU
from orchestrator.models.deployment.ue import UEDeployment
from orchestrator.models.meta.ran import DUComponent, GNBComponent
from orchestrator.models.meta.ru import RU
from orchestrator.models.meta.ue import UE, UEType
from orchestrator.utils.common import ReferenceNotFoundError
from orchestrator.utils.common_5g import (
    K8SComponent,
    Slice,
    reconcile_5g_component,
    resolve_component_reference,
    resolve_ru_reference,
)
from orchestrator.utils.radio import derive_ue_radio_config


class _TempMergedGNB(K8SComponent):
    """GNB/DU merged model to temporarily resolve the 'gnb' reference in the UE's config."""
    resolved_reference: tuple[IPvAnyAddress, GNBComponent | DUComponent]


def resolve_gnb_reference(
        ue_name: str,
        ue_meta: UE,
        gnb_components_meta: dict[str, GNBComponent | DUComponent],
        gnb_components_k8s: dict[str, K8SComponent] | None = None,
    ) -> None:
    """Resolve gNB name reference in a containerized UE."""


    if gnb_components_k8s is None:
        # if the gnb hasn't been installed yet
        # this case is mainly used for the core to be able to resolve the gnb reference before it is installed
        resolve_component_reference(
            component_name=ue_name,
            component_meta=ue_meta,
            ref_attribute="gnb",
            registry=gnb_components_meta,
        )
        # add placeholder ip to respect the expected tuple structure
        ue_meta.config.gnb = IPvAnyAddress("0.0.0.0"), ue_meta.config.gnb
        return

    # merge gnbs (we need the meta for ran config parameters and k8s deployment for readiness state and network info)
    # ran meta and deployment models are supposed to be synchronized by this point
    gnb_components : dict[str, _TempMergedGNB] = {
        gnb_name: _TempMergedGNB.model_validate({
            **gnb_components_k8s[gnb_name].model_dump(mode="json"),
            "resolved_reference": (gnb_components_k8s[gnb_name].network_info, gnb_meta)
            })
        for gnb_name, gnb_meta in gnb_components_meta.items()
        }

    gnb_reference = ue_meta.config.gnb # used only for error handling if smth goes wrong

    resolve_component_reference( # also manages the case where the referenced gnb is None (not needed) or is not found in the registry 
        component_name=ue_name,
        component_meta=ue_meta,
        ref_attribute="gnb",
        registry=gnb_components,
        ready_attribute="is_installed",
        value_attribute="resolved_reference",
    )

    # handle gnb multus case
    if isinstance(ue_meta.config.gnb, tuple): # if the reference was resolved
        if isinstance(ue_meta.config.gnb[1], list): # multus case
            # get first ip from ips list of eth0 interface (pod interface)
            gnb_ip = next(
                (
                    ip
                    for item in ue_meta.config.gnb[1]
                    if item.get("interface") == "eth0"
                    for ip in item.get("ips", [])
                ),
                None,
            )
            ue_meta.config.gnb[1] = gnb_ip

        if ue_meta.config.gnb[1] is None:
            raise ReferenceNotFoundError(f"UE {ue_name!r} references gNB {gnb_reference!r} with unresolved network information.")


def reconcile_ues(
        ues_meta: dict[str, UE],
        ues_k8s: dict[str, UEDeployment],
        slices: dict[str, Slice],
        gnb_components_meta: dict[str, GNBComponent | DUComponent],
        gnb_components_k8s: dict[str, K8SComponent],
        rus_meta: dict[str, RU],
        rus_provisioning: dict[str, ProvisionableRU],
    ) -> None:
    """Ensure UEs are ready to be managed by resolving their configs."""

    for name, ue_meta in ues_meta.items():

        if ue_meta.type is UEType.CONTAINERIZED:
            resolve_gnb_reference(
                ue_name=name,
                ue_meta=ue_meta,
                gnb_components_meta=gnb_components_meta,
                gnb_components_k8s=gnb_components_k8s,
            )

            resolve_ru_reference(
                component_name=name,
                component_meta=ue_meta,
                rus_meta=rus_meta,
                rus_provisioning=rus_provisioning,
            )

            reconcile_5g_component(
                component_name=name,
                component_meta=ue_meta,
                component_k8s=ues_k8s[name], # ues meta and deployment keys should be synced by this point
                slices=slices,
            )

            # derive implementation-specific radio parameters for ue after ru name reference resolution
            derive_ue_radio_config(ue_meta)
