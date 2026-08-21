"""Kubernetes setup utilities and helpers."""

import asyncio
from typing import Literal

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.k8s import (
    K8SParams,
    K8SStatus,
)
from orchestrator.models.deployment.provisioning import (
    ProvisionableNode,
)
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_role,
)
from orchestrator.utils.common import InvalidResourceStateError


async def run_single_k8s_setup_action(
        node_name: str,
        node_data: ProvisionableNode,
        action: Literal["prepare", "create", "join", "remove"],
        k8s_params: K8SParams,
        ansible_params: AnsibleParams,
        force: bool = False,
    ) -> None:
    """Run Kubernetes setup Ansible role corresponding to the given action on a single provisioned node_data."""

    if not force:
        if not node_data.is_provisioned:
            raise InvalidResourceStateError(f"Node {node_name!r} is not provisioned")

        if ((node_data.k8s_status.value in ["configured", "in_cluster"] and action == "prepare") or
            (node_data.k8s_status.value == "in_cluster" and action in ["create", "join"]) or
            (node_data.k8s_status.value == "not_configured" and action == "remove")):

            raise InvalidResourceStateError(f"Node {node_name!r} Kubernetes status is already {node_data.k8s_status.value}.")

    # merge k8s params with priority to node's k8s params
    merged_params = K8SParams.model_validate(k8s_params.model_dump(mode="json") | node_data.k8s_params)

    if action == "join" and merged_params.join_command is None:
        raise RuntimeError(f"Node {node_name!r} cannot join Kubernetes cluster. Join command is undefined.")

    args = {
        "role": f"k8s/{action}",
        "inputs": {
            "node": {
                "name": node_name,
                **node_data.model_dump(mode="json"),
            },
            **merged_params.model_dump(mode="json"),
        },
        "output_keys": ["join_command"] if action == "create" else None, # retrieve the join command
        "runner_path": f"{ansible_params.runner_path}/{node_data.category.value}/{node_name}/k8s/{action}",
        "roles_path": ansible_params.roles_path,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
    }

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"Node {node_name!r} Kubernetes {action} not successful.") from e

    # update k8s status of node
    match action:
        case "prepare":
            node_data.k8s_status = K8SStatus.CONFIGURED
        case "remove":
            node_data.k8s_status = K8SStatus.NOT_CONFIGURED
        case "join":
            node_data.k8s_status = K8SStatus.IN_CLUSTER
        case "create":
            node_data.k8s_status = K8SStatus.IN_CLUSTER
            # update join command
            k8s_params.join_command = result["join_command"]


async def run_parallel_k8s_setup_action(
        nodes: dict[str, ProvisionableNode],
        action: Literal["prepare", "create", "join", "remove"],
        k8s_params: K8SParams,
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
    ) -> None:
    """Run Kubernetes setup action in parallel on provided nodes."""

    tasks: dict[str, asyncio.Task] = {}
    for name, node in nodes.items():
        tasks[name] = asyncio.create_task(
            run_single_k8s_setup_action(
                node_name=name,
                node_data=node,
                action=action,
                k8s_params=k8s_params,
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
