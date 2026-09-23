"""UE utilities and helpers."""

import asyncio
import os
from typing import Any, Literal

from pydantic import IPvAnyAddress

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.provisioning import (
    ProvisionableRU,
    ProvisionableUE,
    Provisioner,
)
from orchestrator.models.deployment.ue import K8SComponent, UEDeployment
from orchestrator.models.meta.ran import DUComponent, GNBComponent, RANImplementation
from orchestrator.models.meta.ru import RU, RUType
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE, UEType
from orchestrator.utils.ansible import handle_ansible_result_exception, run_ansible_role
from orchestrator.utils.common import InvalidResourceStateError, ReferenceNotFoundError
from orchestrator.utils.common_5g import (
    reconcile_5g_component,
    resolve_component_reference,
    resolve_ru_reference,
)
from orchestrator.utils.provisioning import resolve_provisioner
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
        if isinstance(ue_meta.config.gnb[0], list): # multus case
            # get first ip from ips list of eth0 interface (pod interface)
            gnb_ip = next(
                (
                    ip
                    for item in ue_meta.config.gnb[0]
                    if item.get("interface") == "eth0"
                    for ip in item.get("ips", [])
                ),
                None,
            )
            ue_meta.config.gnb[0] = gnb_ip

        if ue_meta.config.gnb[0] is None:
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

    used_ips = set() # set used to ensure that only one ue per ocudu zmq gnb/du

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

            if ue_meta.config.ru.type is RUType.SIMULATED and ue_meta.config.gnb[1].implementation is RANImplementation.OCUDU:
                # zmq in ocudu gnb/du needs both gnb ip and ue ip
                # the gnb/du should have generated a ue_ip in their advanced_config by this point (ran reconciled)
                adv_config = ue_meta.config.gnb[1].advanced_config

                if not ues_k8s[name].static_pod_ip and (not adv_config or not adv_config.ue_ip):
                    raise ValueError(f"UE {name} needs a static pod IP for ZMQ simulated RF with OCUDU RAN, but none was provided.")

                ue_ip = ues_k8s[name].static_pod_ip or adv_config.ue_ip

                if ue_ip in used_ips:
                    raise ValueError(
                        f"UE {name} can't get static pod IP {ue_ip} for ZMQ simulated RF with OCUDU RAN; "
                        "another UE is already using it and only one UE is alloweed per OCUDU ZMQ GNB/DU."
                        )

                ues_k8s[name].static_pod_ip = ue_ip

                used_ips.add(ues_k8s[name].static_pod_ip)


async def run_single_ue_action(
        ue_name: str,
        ue_meta: UE,
        ue_prov: ProvisionableUE,
        action: Literal["connect", "disconnect"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Run the 'ue/connect' or 'ue/disconnect' Ansible role of the provisioner on a single provisionable UE."""

    if not force and (
        (action == "connect" and ue_prov.is_connected) or
        (action == "disconnect" and not ue_prov.is_connected)):

            raise InvalidResourceStateError(f"UE {ue_name!r} is already {action}ed.")

    provisioner = resolve_provisioner(
        resource_name=ue_name,
        resource_data=ue_prov,
        provisioners=provisioners,
    )

    # merge provisioning params without mutating the provisioner
    merged_prov_params = type(provisioner.params).model_validate(provisioning_params | provisioner.params.model_dump(mode="json", exclude_defaults=True) | ue_prov.provisioning_params)

    args = {
        "role": f"provisioning/{provisioner.type.value}/ue/{action}",
        "inputs": {
            "ue_name": ue_name,
            "ue": ue_meta,
            **merged_prov_params.model_dump(mode="json"),
        },
        "extra_params": {"environment": {"PATH": f"{merged_prov_params.extra_path}:{os.environ.get('PATH', '')}"}} if merged_prov_params.extra_path else None,
        "runner_path": f"{ansible_params.runner_path}/ue/{ue_name}/{action}",
        "roles_paths": ansible_params.roles_paths,
    }

    try:
        return await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"UE {ue_name!r} {action} action failed.") from e


async def run_parallel_ue_action(
        ues_meta: dict[str, UE],
        ues_prov: dict[str, ProvisionableUE],
        action: Literal["connect", "disconnect"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
    ) -> None:
    """Connect or disconnect UEs in parallel."""

    tasks: dict[str, asyncio.Task] = {}
    for ue_name, ue_meta in ues_meta.items():
        ue_prov = ues_prov[ue_name] # dicts should be synced by now
        tasks[ue_name] = asyncio.create_task(
            run_single_ue_action(
                ue_name=ue_name,
                ue_meta=ue_meta,
                ue_prov=ue_prov,
                action=action,
                provisioners=provisioners,
                provisioning_params=provisioning_params,
                ansible_params=ansible_params,
                force=force,
        ))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for _, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )
