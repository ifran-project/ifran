"""5G core utilities and helpers."""

import asyncio
from typing import Literal

from pydantic import IPvAnyAddress

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.core import CoreDeployment
from orchestrator.models.deployment.k8s import HelmParams, K8SComponent
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import Core, CoreComponent, CoreImplementation
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE, UEConfiguration
from orchestrator.utils.ansible import handle_ansible_result_exception, run_ansible_role
from orchestrator.utils.common import InvalidResourceStateError
from orchestrator.utils.common_5g import reconcile_5g_component


# wrapper function that might be extended later
def reconcile_core_component(
        component_name: str,
        component_meta: CoreComponent,
        component_k8s: K8SComponent,
        slices: dict[str, Slice],
    ) -> None:
    """Ensure the core component deployment model and meta model are ready for deployment."""

    reconcile_5g_component(
        component_name=component_name,
        component_meta=component_meta,
        component_k8s=component_k8s,
        slices=slices,
    )


def reconcile_core(
        core_meta: Core,
        core_deployment: CoreDeployment,
        slices: dict[str, Slice],
    ) -> None:
    """Ensure 5G core is ready for deployment."""

    for name, component_meta in core_meta.components.items():
        # meta and deployment keys are supposed to be synced by this point
        component_k8s = core_deployment.components[name]

        reconcile_core_component(
            component_name=name,
            component_meta=component_meta,
            component_k8s=component_k8s,
            slices=slices,
        )


async def run_core_database_helm_action(
        core_meta: Core,
        core_deployment: CoreDeployment,
        action: Literal["prepare", "install", "uninstall"],
        node: str,
        inventory: str,
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Run Ansible Helm prepare/install/uninstall role on 5G core database."""

    if not force and (
        (core_deployment.is_database_present and action == "install") or 
        (not core_deployment.is_database_present and action == "uninstall")
        ):
        raise InvalidResourceStateError(f"5G core database is already {action}ed.")

    helm_params = HelmParams(
        chart_name=f"{core_meta.implementation.value}-database",
        helm_build_dir=f"/root/helm-charts/{Category5G.CORE}/{core_meta.implementation.value}-database",
        render=False
    ).model_dump(mode="json")

    component = {
            "category": Category5G.CORE.value,
            "implementation": core_meta.implementation.value,
            "namespace": f"{core_meta.implementation.value}-{Category5G.CORE.value}",
            "type": "database",
            }

    args = {
        "role": f"helm/{action}",
        "inputs": {"component": component, **helm_params},
        "runner_path": f"{ansible_params.runner_path}/{component["category"]}/database/helm/{action}",
        "roles_path": ansible_params.roles_path,
        "hosts": node,
        "inventory": inventory,
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
        core_deployment.is_database_present = True
        # retreive database pod ip
        core_deployment.database_ip = IPvAnyAddress(result["network_info"])
    elif action == "uninstall":
        core_deployment.is_database_present = False


async def run_single_database_subscriber_action(
        ue_name: str,
        ue_config: UEConfiguration,
        core_implementation: CoreImplementation,
        action: Literal["add", "remove"],
        database_ip: IPvAnyAddress,
        node: str,
        inventory: str,
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
        "roles_path": ansible_params.roles_path,
        "hosts": node,
        "inventory": inventory,
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
        node: str,
        inventory: str,
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
                node=node,
                inventory=inventory,
                ansible_params=ansible_params,
                force=force,
        ))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for name, result in zip(tasks.keys(), results):
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )
