"""5G core utilities and helpers."""

import asyncio
from typing import Literal

from pydantic import IPvAnyAddress, IPvAnyNetwork, TypeAdapter

from orchestrator.models.common import URL
from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.core import CoreDeployment
from orchestrator.models.deployment.k8s import HelmParams
from orchestrator.models.deployment.provisioning import ProvisionableNode
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import (
    Core,
    CoreImplementation,
    SMFComponent,
    UPFComponent,
)
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE, UEConfiguration
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_role,
)
from orchestrator.utils.common import InvalidResourceStateError, generate_random_ip
from orchestrator.utils.common_5g import (
    CoreComponentType,
    get_5g_components_by_type,
    reconcile_5g_component,
)
from orchestrator.utils.defaults import DEFAULT_CORE_DATABASE_IMAGES


def resolve_upf_references(
        core_meta: Core,
        ip_mapping: dict[str, IPvAnyAddress],
    ) -> None:
    """Resolve UPF reference in SMF components."""

    grouped = get_5g_components_by_type(core_meta.components)
    smfs: dict[str, SMFComponent] = grouped.get(CoreComponentType.SMF, {})
    upfs: dict[str, UPFComponent] = grouped.get(CoreComponentType.UPF, {})

    for name, component_meta in smfs.items():
        for i in range(len(component_meta.config.upfs)):
            upf_reference = component_meta.config.upfs[i]
            if isinstance(upf_reference, str):
                target_ip = ip_mapping.get(upf_reference)
                upf_meta = upfs.get(upf_reference)
                if target_ip is None or upf_meta is None:
                    raise ValueError(f"Could not resolve IP for SMF component {name!r} reference to {upf_reference!r}.")
                component_meta.config.upfs[i] = target_ip, upf_meta


def populate_nrf_uri(
        core_meta: Core,
        nrf_uri: URL,
    ) -> None:
    """Populate 'nrfUri' field for all 5G core components."""

    for component_meta in core_meta.components.values():
        if component_meta.config.nrfUri is None:
            component_meta.config.nrfUri = nrf_uri


def reconcile_core(
        core_meta: Core,
        core_deployment: CoreDeployment,
        pod_network_cidr: IPvAnyNetwork,
        slices: dict[str, Slice],
    ) -> None:
    """Ensure 5G core is ready for deployment."""

    # populate database image if not already set
    if core_deployment.database_params.image is None:
        database_image = DEFAULT_CORE_DATABASE_IMAGES.get(core_meta.implementation)

         # if no default database image is available raise an error
        if database_image is None:
             raise ValueError(f"{core_meta.implementation.upper} database has no container image.")

        core_deployment.database_params.image = DEFAULT_CORE_DATABASE_IMAGES.get(core_meta.implementation)


    used_ips: set[IPvAnyAddress] = set()
    ip_mapping: dict[str, IPvAnyAddress] = {}

    nrf_uri = None

    for name, component_meta in core_meta.components.items():
        # meta and deployment keys are supposed to be synced by this point
        component_k8s = core_deployment.components[name]

        reconcile_5g_component(
            component_name=name,
            component_meta=component_meta,
            component_k8s=component_k8s,
            slices=slices,
        )

        if component_meta.type is CoreComponentType.UPF:
            # upf components are assigned static pod ips
            component_k8s.static_pod_ip = component_k8s.static_pod_ip or generate_random_ip(pod_network_cidr, used_ips)

            ip_mapping[name] = component_k8s.static_pod_ip # build mapping between component names and ips
            used_ips.add(component_k8s.static_pod_ip)

        if component_meta.type is CoreComponentType.NRF:
            # look for NRF components to populate nrfUri
            scheme = "https" if component_meta.config.sbi.tls.enabled else "http"
            nrf_uri = TypeAdapter(URL).validate_python(f"{scheme}://{component_meta.implementation}-{name}:{component_meta.config.sbi.port}")

    # resolve upf references after static ips have been assigned
    resolve_upf_references(
        core_meta=core_meta,
        ip_mapping=ip_mapping,
    )

    # populate nrf uri field after nrf component has been found (latest one found takes precedence if many are given)
    populate_nrf_uri(
        core_meta=core_meta,
        nrf_uri=nrf_uri,
    )


async def run_core_database_helm_action(
        core_meta: Core,
        core_deployment: CoreDeployment,
        action: Literal["prepare", "install", "uninstall"],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Run Ansible Helm prepare/install/uninstall role on 5G core database."""

    if not force and (
        (core_deployment.database_params.is_installed and action == "install") or 
        (not core_deployment.database_params.is_installed and action == "uninstall")
        ):
        raise InvalidResourceStateError(f"5G core database is already {action}ed.")

    helm_params = HelmParams(
        chart_name=f"{core_meta.implementation.value}-database",
        helm_build_dir=f"/root/helm-charts/{Category5G.CORE}/{core_meta.implementation.value}-database",
    ).model_dump(mode="json")

    component = {
            "category": Category5G.CORE.value,
            "implementation": core_meta.implementation.value,
            "namespace": f"{core_meta.implementation.value}-{Category5G.CORE.value}",
            "type": "database",
            "rendered_files": ["values.yaml"],
            **core_deployment.database_params.model_dump(mode="json"),
            }

    args = {
        "role": f"helm/{action}",
        "inputs": {"component": component, **helm_params},
        "runner_path": f"{ansible_params.runner_path}/{component["category"]}/database/helm/{action}",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
    }

    # expect database network info output after installation
    if action == "install":
        args["output_keys"] = ["network_info"]

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"5G core database Helm {action} not successful") from e

    # update database status in core deployment
    if action == "install":
        core_deployment.database_params.is_installed = True
        # retrieve database pod ip
        core_deployment.database_params.ip = IPvAnyAddress(result["network_info"])
    elif action == "uninstall":
        core_deployment.database_params.is_installed = False


async def run_single_database_subscriber_action(
        ue_name: str,
        ue_config: UEConfiguration,
        core_implementation: CoreImplementation,
        action: Literal["add", "remove"],
        database_ip: IPvAnyAddress,
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Add/remove a single UE/subscriber on the 5G core database."""

    if not force and database_ip is None:
        raise InvalidResourceStateError(f"{core_implementation.value.upper()} 5G core database has an undefined IP address.")

    args = {
        "role": f"database/subscriber/{action}/{core_implementation}",
        "inputs": {"ue_name": ue_name, "ue_config": ue_config.model_dump(mode="json"), "database_ip": str(database_ip)},
        "runner_path": f"{ansible_params.runner_path}/core/database/subscriber/{action}",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
    }
    try:
        await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"Failed to {action} UE {ue_name!r} on {core_implementation.value.upper()} 5G core database.") from e


async def run_parallel_database_subscriber_action(
        ues: dict[str, UE],
        core_implementation: CoreImplementation,
        action: Literal["add", "remove"],
        database_ip: IPvAnyAddress,
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = False,
        ignore_failures: bool = False,
    ) -> None:
    """Add/remove multiple UEs/subscribers in parallel."""

    tasks: dict[str, asyncio.Task] = {}
    for name, ue in ues.items():
        tasks[name] = asyncio.create_task(
            run_single_database_subscriber_action(
                ue_name=name,
                ue_config=ue.config,
                core_implementation=core_implementation,
                action=action,
                database_ip=database_ip,
                node_name=node_name,
                node_data=node_data,
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
