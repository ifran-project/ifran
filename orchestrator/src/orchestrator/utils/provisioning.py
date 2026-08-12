

import asyncio
import os
from typing import Any, Literal

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.deployment import DeploymentModel
from orchestrator.models.deployment.k8s import K8SStatus
from orchestrator.models.deployment.provisioning import (
    ProvisionableResource,
    Provisioner,
    SSHInfo,
)
from orchestrator.utils.ansible import (
    handle_ansible_result_exception,
    run_ansible_role,
)
from orchestrator.utils.common import (
    InvalidResourceStateError,
    ReferenceNotFounError,
)


def get_provisionable_resources(
        deployment_model: DeploymentModel,
        resources: dict[Literal["nodes", "rus", "ues"], list[str]] | None = None,
    ) -> dict[str, ProvisionableResource]:
    "Extract filtered provisionable resources from deployment model."

    target_resources: dict[str, ProvisionableResource] = {}
    rtypes = ["nodes", "rus", "ues"]
    for rtype in rtypes:
        type_resources: dict[str, ProvisionableResource] = getattr(deployment_model, rtype)
        target_resources = (
            target_resources | type_resources
            if resources is None
            else target_resources | {k: v for k, v in type_resources.items() if k in resources}
        )

    return target_resources


def resolve_provisioner(
        resource_name: str,
        resource_data: ProvisionableResource,
        provisioners: dict[str, Provisioner],
        ) -> Provisioner:
    """Resolve resource provisioner and merge provisioning parameters."""

    if resource_data.provisioner is None:
        raise ReferenceNotFounError(f"No provisioner reference found to resolve for {resource_data.category.value} {resource_name!r}.")

    provisioner = provisioners.get(resource_data.provisioner)

    if provisioner is None:
        raise ReferenceNotFounError(f"{resource_data.category.value.capitalize()} {resource_name!r} references undefined provisioner {resource_data.provisioner!r}.")

    if provisioner.category != resource_data.category:
        raise ValueError(f"{resource_data.category.value.capitalize()} {resource_name!r} references "
                         f"provisioner {resource_data.provisioner!r} of category {provisioner.category!r}.")

    if not resource_data.provisioning_params:
        return provisioner


async def run_single_provisioning_action(
        resource_name: str,
        resource_data: ProvisionableResource,
        action: Literal["provision", "unprovision"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        ):
    """Run the Ansible role of the provisioner corresponding to the given action on a single resource."""

    if not force and (
        (action == "provision" and resource_data.is_provisioned) or
        (action == "unprovision" and not resource_data.is_provisioned)):

            raise InvalidResourceStateError(f"{resource_data.category.value.capitalize()} is already {action}ed.")

    provisioner = resolve_provisioner(
        resource_name=resource_name,
        resource_data=resource_data,
        provisioners=provisioners,
    )

    # merge provisioning params without mutating the provisioner
    # lvl 1 : merge provisioner params with global provisioning_params with priority to non-default provisioner's params
    # lvl 2: merge provisioner params with resource provisioning params with priority to resource's provisioning params
    # NOTE provisioner params model needs to tolerate extra fields and ignore them for this to work with no problems
    merged_prov_params = type(provisioner.params).model_validate(provisioning_params | provisioner.params.model_dump(mode="json", exclude_unset=True) | resource_data.provisioning_params)

    args = {
        "role": f"provisioning/{provisioner.category.value}/{provisioner.type.value}/{action}",
        "inputs": {
            "resource_name": resource_name,
            **merged_prov_params.model_dump(mode="json")
        },
        "extra_params": {"environment": {"PATH": f"{merged_prov_params.extra_path}:{os.environ.get('PATH', '')}"}} if merged_prov_params.extra_path else None,
        "output_keys": ["ssh_info"] if action == "provision" else None,
        "runner_path": f"{ansible_params.runner_path}/{resource_data.category.value}/{resource_name}/{action}",
        "roles_path": ansible_params.roles_path,
    }

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"{resource_data.category.value.capitalize()} {resource_name!r} {action}ing failed.") from e

    if action == "provision":
        resource_data.is_provisioned = True
        # validate and update resource ssh info
        resource_data.ssh_info = SSHInfo.model_validate(result["ssh_info"])

    if action == "unprovision":
        resource_data.is_provisioned = False
        # set k8s status to not_configured if resource supports it
        if hasattr(resource_data, "k8s_status"):
            resource_data.k8s_status = K8SStatus.NOT_CONFIGURED


async def run_parallel_provisioning_action(
        resources: dict[str, ProvisionableResource],
        action: Literal["provision", "unprovision"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        ):
    """Provision or unprovision action on provided provisionable resources in parallel."""

    tasks: dict[str, asyncio.Task] = {}
    for name, resource in resources.items():
        tasks[name] = asyncio.create_task(
            run_single_provisioning_action(
                resource_name=name,
                resource_data=resource,
                action=action,
                provisioners=provisioners,
                provisioning_params=provisioning_params,
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
