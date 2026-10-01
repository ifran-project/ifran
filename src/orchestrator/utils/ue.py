"""UE utilities and helpers."""

import asyncio
import os
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Literal

from metamodel.models.metamodel import MetaModel
from metamodel.models.ran import DUComponent, GNBComponent, RANComponentType
from metamodel.models.ru import RUType
from metamodel.models.slice import Slice
from metamodel.models.ue import UE, UEType

from orchestrator.models.ansible import AnsibleParams
from orchestrator.models.common import Deployed5GComponent
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.provisioning import (
    ProvisionableUE,
    Provisioner,
)
from orchestrator.models.ran import RANImplementation, UEReferencedDU, UEReferencedGNB
from orchestrator.models.ue import DeployedUE
from orchestrator.utils.ansible import handle_ansible_result_exception, run_ansible_role
from orchestrator.utils.common_5g import (
    get_5g_components_by_type,
    reconcile_5g_component,
    resolve_ru_reference,
    resolve_snssai_reference,
)
from orchestrator.utils.provisioning import resolve_provisioner
from orchestrator.utils.radio import derive_ue_radio_config
from orchestrator.utils.utils import InvalidResourceStateError, ReferenceNotFoundError


def resolve_ue_slices_dnns(
        component_name: str,
        component_meta: UE,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve UE slice and DNN references."""

    ue_config = component_meta.config

    # resolve snssai and dnn for every ue subscription
    for subscription in ue_config.subscriptions:
        # resolve snssai/slice
        subscription.snssai = resolve_snssai_reference(
            component_name=component_meta, # type: ignore
            component_meta=component_name, # type: ignore
            reference=subscription.snssai,
            slices=slices,
            field_name="subscription.snssai",
        )

        # resolve dnn after resolving slice
        subscription_dnn = subscription.snssai.dnns.get(subscription.dnn) # type: ignore
        if subscription_dnn is None:
            raise ReferenceNotFoundError(f"UE {component_name!r} references undefined DNN {subscription.dnn!r}.")

        subscription.dnn = subscription_dnn


def resolve_gnb_ref(
        component_name: str,
        component_meta: UE,
        gnbs_meta: dict[str, GNBComponent | DUComponent],
        gnbs_deployment: dict[str, Deployed5GComponent],
        populate_address: bool = True,
    ) -> None:
    """
    Resolve gNB/DU name reference in a containerized UE's 'gnbs' field.

    If 'populate_address' is False, the resolved gnbs will not include 'gnb_ip'.
    (Mainly used when resolving ue's gnb references during core reconciliation)
    """

    # resolve gnb references one by one
    for i in range(len(component_meta.config.gnbs)):
        gnb_reference = component_meta.config.gnbs[i]
        gnb_meta = gnbs_meta.get(gnb_reference)

        if gnb_meta is None:
            raise ReferenceNotFoundError(
                f"Containarized UE {component_name!r} reference undefined gNB/DU {gnb_reference!r}."
            )

        gnb_deployment = gnbs_deployment[gnb_reference]
        merged_gnb = {**gnb_meta.model_dump(mode="json"), **gnb_deployment.model_dump(mode="json")}
        merge_model = UEReferencedGNB if gnb_meta.type is RANComponentType.GNB else UEReferencedDU

        # NOTE if ue is containarized, ue's ru reference should be resolved before
        if (populate_address and
            component_meta.type is UEType.CONTAINERIZED and
            component_meta.config.ru.type is RUType.SIMULATED # type: ignore
            ):
            # if gnb/du has non-multus network info (one IP address), use it
            # else, use the static_pod_ip that is supposed to populated before RAN deployment
            if isinstance(gnb_deployment.network_info, (IPv4Address, IPv6Address)):
                gnb_ip = gnb_deployment.network_info
            else:
                gnb_ip = gnb_deployment.static_pod_ip

            if gnb_ip is None:
                raise ReferenceNotFoundError(
                    f"Containarized UE {component_name!r} reference gNB/DU {gnb_reference!r} with unknown address."
                )

            component_meta.config.gnbs[i] = merge_model.model_validate({**merged_gnb, "gnb_ip": gnb_ip}) # type: ignore
        else:
            # gnb ip is not needed in non-simulated ue
            component_meta.config.gnbs[i] = merge_model.model_validate(merged_gnb) # type: ignore


def resolve_ocudu_zmq_ran(
        component_name: str,
        component_meta: UE,
        component_deployment: DeployedUE,
    ) -> None:
    """Resolve dependency between OCUDU simulated RAN and the UE."""

    # NOTE ue's ru and gnb references should be resolved before
    if component_meta.config.ru.type is not RUType.SIMULATED: # type: ignore
        return

    # evaluate whether ue is zmq-based or not and find OCUDU gnb
    is_zmq_based = False
    for gnb in component_meta.config.gnbs:
        if gnb.implementation is RANImplementation.OCUDU: # type: ignore
            is_zmq_based = True
            break

    if is_zmq_based:
        # zmq in ocudu gnb/du needs both gnb ip and ue ip
        # NOTE the gnb/du should have generated a ue_ip in their advanced_config by this point
        if gnb.advanced_config is None or gnb.advanced_config.ue_ip is None: # type: ignore
            raise ValueError(
                f"UE {component_name} needs a static pod IP for ZMQ simulated RF with OCUDU RAN, "
                "but none was found in gNB/DU's 'ue_ip' advanced config field."
            )

        component_deployment.static_pod_ip = gnb.advanced_config.ue_ip # type: ignore


def reconcile_ues(
        metamodel: MetaModel,
        deployment_model: DeploymentModel,
    ) -> None:
    """Ensure UEs are ready to be managed by resolving their configs."""

    ues_meta = metamodel.ues
    ues_deployment = deployment_model.ues

    ran_meta = metamodel.ran
    ran_deployment = deployment_model.ran

    rus_meta = metamodel.rus
    rus_provisioning = deployment_model.rus

    slices = metamodel.slices
    k8s_params = deployment_model.params.k8s

    gnbs_meta = get_5g_components_by_type(ran_meta.components, [RANComponentType.GNB, RANComponentType.DU]) # type: ignore
    gnbs_deployment = get_5g_components_by_type(ran_deployment.components, [RANComponentType.GNB, RANComponentType.DU]) # type: ignore

    for ue_name, ue_meta in ues_meta.items():
        args = {"component_name": ue_name, "component_meta": ue_meta}

        # resolve slice and dnn references
        resolve_ue_slices_dnns(
            **args,
            slices=slices,
        )

        # resolve ru reference for containarozed ues
        if ue_meta.type is UEType.CONTAINERIZED:
            resolve_ru_reference(
                **args,
                rus_meta=rus_meta,
                rus_provisioning=rus_provisioning,
            )

        # resolve gnb references after ru name reference resolution
        resolve_gnb_ref(
            **args,
            gnbs_meta=gnbs_meta, # type: ignore
            gnbs_deployment=gnbs_deployment, # type: ignore
            populate_address=True,
        )

        if ue_meta.type is UEType.CONTAINERIZED:
            ue_deployment = ues_deployment[ue_name]

            reconcile_5g_component(
                **args,
                component_deployment=ue_deployment, # type: ignore
                k8s_params=k8s_params,
            )

            # derive implementation-specific radio parameters for ue after ru name reference resolution
            derive_ue_radio_config(
                ue_meta=ue_meta,
                ue_deployment=ue_deployment # type: ignore
                )

            # zmq-based ue specific case
            resolve_ocudu_zmq_ran(
                **args,
                component_deployment=ue_deployment, # type: ignore
            )


async def run_single_ue_action(  # noqa: PLR0917
        ue_name: str,
        ue_meta: UE,
        ue_prov: ProvisionableUE,
        action: Literal["connect", "disconnect"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        quiet: bool = False,
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
    merged_prov_params = type(provisioner.params).model_validate( # type: ignore
        provisioning_params |
        provisioner.params.model_dump(mode="json") | # type: ignore
        ue_prov.provisioning_params
    )

    args = {
        "role": f"provisioning/{provisioner.type.value}/ue/{action}", # type: ignore
        "inputs": {
            "ue_name": ue_name,
            # NOTE use serialize_as_any=True to prevent pydantic from replacing models
            # because of type mismatch after reference resolution (e.g. slice: str -> Slice, gnb: str -> GNBComponent)
            "ue": ue_meta.model_dump(mode="json", serialize_as_any=True),
            **merged_prov_params.model_dump(mode="json"),
        },
        "extra_params": {"environment": {"PATH": f"{merged_prov_params.extra_path}:{os.environ.get('PATH', '')}"}}
                        if merged_prov_params.extra_path else None,
        "runner_path": f"{ansible_params.runner_path}/ue/{ue_name}/{action}",
        "roles_paths": ansible_params.roles_paths,
        "quiet": quiet,
    }

    try:
        await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"UE {ue_name!r} {action} action failed.") from e


async def run_parallel_ue_action(  # noqa: PLR0917
        ues_meta: dict[str, UE],
        ues_prov: dict[str, ProvisionableUE],
        action: Literal["connect", "disconnect"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
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
                quiet=quiet,
        ))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )
