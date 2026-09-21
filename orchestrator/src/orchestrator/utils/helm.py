"""Kubernetes components Helm utilities and helpers."""

import asyncio
from typing import Literal

from pydantic import IPvAnyAddress

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.k8s import (
    HelmParams,
    K8SComponent,
    MultusNetworkStatus,
)
from orchestrator.models.deployment.provisioning import ProvisionableNode
from orchestrator.models.meta.common import Component5G
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_role,
)
from orchestrator.utils.common import (
    InvalidResourceStateError,
    build_k8s_safe,
)
from orchestrator.utils.common_5g import (
    ComponentDependencyGraph,
    resolve_component_dependency_levels,
)


async def run_single_helm_action(
        component_name: str,
        component_meta: Component5G,
        component_k8s: K8SComponent,
        action: Literal["prepare", "install", "uninstall"],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Run Ansible Helm role corresponding to the given action on a single 5G component."""

    chart_name = build_k8s_safe(f"{component_meta.implementation}-{component_name}")

    # preparing a prepared component is not considered in the check given the idempotence
    if not force and (
        (component_k8s.is_installed and action == "install") or 
        (not component_k8s.is_installed and action == "uninstall")
        ):
        raise InvalidResourceStateError(f"{component_meta.category.value.upper()} component {component_name!r} is already {action}ed.")

    helm_params = HelmParams(
        chart_name=chart_name,
        helm_build_dir=f"/root/helm-charts/{component_meta.category}/{chart_name}",
        output_with_multus=component_k8s.multus.enabled,
    )

    args = {
        "role": f"helm/{action}",
        "inputs": {
            "component_name": component_name,
            "component": {**(component_meta.model_dump(mode="json") | component_k8s.model_dump(mode="json"))}, # merge component
            **helm_params.model_dump(mode="json"),
        },
        "runner_path": f"{ansible_params.runner_path}/{component_meta.category.value}/{component_name}/helm/{action}",
        "roles_path": ansible_params.roles_path,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
    }

    # expect network info output after installation
    if action == "install":
        args["output_keys"] = ["network_info"]

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"{component_meta.category.value.upper()} component {component_name!r} Helm {action} not successful.") from e

    # update component state
    if action == "install":
        component_k8s.is_installed = True
        if helm_params.output_with_multus:
            # if multus is used, output list of multus network status
            component_k8s.network_info = [MultusNetworkStatus.model_validate(item) for item in result["network_info"]]
        else:
            # if multus is not used, output ip address directly
            component_k8s.network_info = IPvAnyAddress(result["network_info"])
    elif action == "uninstall":
        component_k8s.is_installed = False


async def run_parallel_helm_action(
        components_meta: dict[str, Component5G],
        components_k8s: dict[str, K8SComponent],
        action: Literal["prepare", "install", "uninstall"],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        order: ComponentDependencyGraph | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
    ) -> dict[str, K8SComponent]:
    """Run Helm action in parallel on provided 5G components."""

    levels = resolve_component_dependency_levels(
        components=components_meta,
        dependencies=order,
    )

    for level in levels:
        # components_meta and components_k8s are supposed to already be synced
        level_components = (
            (name, components_meta[name], components_k8s[name])
            for name in level
            if name in components_meta and name in components_k8s
        )

        results = await asyncio.gather(
            *(
                run_single_helm_action(
                    component_name=name,
                    component_meta=component_meta,
                    component_k8s=component_k8s,
                    action=action,
                    node_name=node_name,
                    node_data=node_data,
                    ansible_params=ansible_params,
                    force=force,
                )
                for name, component_meta, component_k8s in level_components
            ),
            return_exceptions=True,
        )

        for result in results:
            # NOTE ignoring errors here means we would pass to the next level even tough this required level has failed
            if isinstance(result, Exception):
                handle_ansible_result_exception(
                    result=result,
                    ignore_invalid_states=ignore_invalid_states,
                    ignore_failures=ignore_failures,
                )
