"""Provisioning utilities and helpers."""

import asyncio
import os
from collections import defaultdict
from ipaddress import IPv4Address
from typing import Any, Literal

from metamodel.models.ue import UEType

from orchestrator.models.ansible import AnsibleParams
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.k8s import K8SStatus
from orchestrator.models.provisioning import (
    ProvisionableResource,
    Provisioner,
    ProvisioningCategory,
    SSHableResource,
    SSHInfo,
)
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_command,
    run_ansible_copy,
    run_ansible_role,
)
from orchestrator.utils.utils import (
    InvalidResourceStateError,
    ReferenceNotFoundError,
    deep_merge,
    resolve_path,
)


def get_provisionable_resources(
        deployment_model: DeploymentModel,
        filter: list[str] | None = None,
    ) -> dict[str, ProvisionableResource]:
    "Extract filtered provisionable resources from deployment model."

    # get all provisionable resources
    target_resources = deployment_model.nodes | deployment_model.rus | {
        k: v for k, v in deployment_model.ues.items() if v.type is UEType.COTS
    }

    # filter
    if filter:
        target_resources = {
            k: v for k, v in target_resources.items() if k in filter
        }

    return target_resources


def get_resources_by_provisioner(
        resources: dict[str, ProvisionableResource],
    ) -> dict[str, dict[str, ProvisionableResource]]:
    "Get provisionable resource names by their provisioner."

    grouped: dict[str, dict[str, ProvisionableResource]] = defaultdict(dict)
    for resource_name, resource_data in resources.items():
        if resource_data.provisioner:
            grouped[resource_data.provisioner][resource_name] = resource_data

    return grouped


def resolve_provisioner(
        resource_name: str,
        resource_data: ProvisionableResource,
        provisioners: dict[str, Provisioner],
    ) -> Provisioner:
    """Resolve resource provisioner and merge provisioning parameters."""

    if resource_data.provisioner is None:
        raise ReferenceNotFoundError(
            f"No provisioner reference found to resolve for {resource_data.category.value} {resource_name!r}."
        )

    provisioner = provisioners.get(resource_data.provisioner)

    if provisioner is None:
        raise ReferenceNotFoundError(
            f"{resource_data.category.value.upper()} {resource_name!r} "
            f"references undefined provisioner {resource_data.provisioner!r}."
        )

    if resource_data.category not in provisioner.supported_categories:
        raise ValueError(f"Provisioner {resource_data.provisioner!r} referenced by {resource_name!r} "
                         f"does not support {resource_data.category.value} provisioning.")

    return provisioner


async def run_reservation_action(  # noqa: PLR0917
        resources: dict[str, ProvisionableResource],
        provisioner_name: str,
        provisioners: dict[str, Provisioner],
        ansible_params: AnsibleParams,
        ignore_failures: bool = False,
        force: bool = False,
        skip_unreservable: bool = True,
        quiet: bool = False,
    ) -> None:
    """Run the 'reserve' Ansible role of the given provisioner once for the given resources list."""

    provisioner_data = provisioners.get(provisioner_name)

    # make sure provisioner exists and is reservable
    # => has attempt_reservation attribute
    # => has reserve and free roles

    if provisioner_data is None:
        raise ValueError(f"Provisioner {provisioner_name!r} could not be found.")

    if not hasattr(provisioner_data.params, "attempt_reservation"):
        if skip_unreservable:
            return
        raise TypeError(f"Provisioner {provisioner_name!r} does not support reservation.")

    if not provisioner_data.params.attempt_reservation and not force: # type: ignore
        return

    args = {
        "role": f"provisioning/{provisioner_data.type.value}/reserve",
        "inputs": {
            "resources": [r.name for r in resources.values()],
            **provisioner_data.params.model_dump(mode="json"),
        },
        "extra_params": {
            "environment": {"PATH": f"{provisioner_data.params.extra_path}:{os.environ.get('PATH', '')}"}}
            if provisioner_data.params.extra_path
            else None,
        "runner_path": f"{ansible_params.runner_path}/reserve/{provisioner_name}",
        "roles_paths": ansible_params.roles_paths,
        "quiet": quiet,
    }
    try:
        await run_ansible_role(**args)
    except Exception as e:
        if ignore_failures:
            return
        raise RuntimeError(
            f"Provisioner {provisioner_name!r} failed to reserve resources: {', '.join(list(resources.keys()))}."
            ) from e


async def run_single_provisioning_action(  # noqa: PLR0917
        resource_name: str,
        resource_data: ProvisionableResource,
        action: Literal["provision", "unprovision"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        quiet: bool = False,
    ) -> None:
    """Run the Ansible role of the provisioner corresponding to the given action on a single resource."""

    if not force and (
        (action == "provision" and resource_data.is_provisioned) or
        (action == "unprovision" and not resource_data.is_provisioned)):

            raise InvalidResourceStateError(
                f"{resource_data.category.value.upper()} {resource_name!r} is already {action}ed."
            )

    if resource_data.category in [ProvisioningCategory.NODE, ProvisioningCategory.UE]:
        # ssh-able resources have ssh_info
        output_keys = ["ssh_info"]
    else:
        output_keys = ["ru_ips"]

    provisioner = resolve_provisioner(
        resource_name=resource_name,
        resource_data=resource_data,
        provisioners=provisioners,
    )

    # merge provisioning params without mutating the provisioner
    # lvl 1 : merge provisioner params with global provisioning_params with priority to non-default provisioner's params
    # lvl 2: merge provisioner params with resource provisioning params with priority to resource's provisioning params
    # NOTE provisioner params model needs to tolerate extra fields and ignore them for this to work with no problems
    merged_prov_params = type(provisioner.params).model_validate(
        provisioning_params |
        provisioner.params.model_dump(mode="json", exclude_defaults=True) |
        resource_data.provisioning_params
    )

    args = {
        "role": f"provisioning/{provisioner.type.value}/{action}",
        "inputs": {
            # NOTE use resource name from its provided data rather that its key in the dictionary
            "resource_name": resource_data.name,
            **merged_prov_params.model_dump(mode="json"),
            # bool used by provisioners that manage ssh-able (nodes and ues) and non-ssh-ables resources (rus)
            # for now, it used to decide whether to return 'ssh_info' or 'ru_ips' instead
            "is_ru": resource_data.category is ProvisioningCategory.RU,
        },
        "extra_params": {"environment": {"PATH": f"{merged_prov_params.extra_path}:{os.environ.get('PATH', '')}"}}
            if merged_prov_params.extra_path
            else None,
        "output_keys": output_keys if action == "provision" else None,
        "runner_path": f"{ansible_params.runner_path}/{resource_data.category.value}/{resource_name}/{action}",
        "roles_paths": ansible_params.roles_paths,
        "quiet": quiet,
    }

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"{resource_data.category.value.upper()} {resource_name!r} {action}ing failed.") from e

    if action == "provision":
        resource_data.is_provisioned = True

        if resource_data.category in [ProvisioningCategory.NODE, ProvisioningCategory.UE]:
            # validate and update resource ssh info for nodes and ues
            # NOTE ssh_info is merged with precedence to the provisioning's ssh_info
            # NOTE deep_merge is used to also merge nested jumphost ssh info
            resource_data.ssh_info = SSHInfo.model_validate( # type: ignore
                deep_merge(resource_data.ssh_info.model_dump(mode="json"), result["ssh_info"])) # type: ignore

        elif resource_data.category is ProvisioningCategory.RU and not resource_data.ips:
            # update ips for rus if not already set
            resource_data.ips = [IPv4Address(ip) for ip in result["ru_ips"]] # type: ignore

    if action == "unprovision":
        resource_data.is_provisioned = False

        if resource_data.category is ProvisioningCategory.NODE:
            # set k8s status to not_configured for nodes
            resource_data.k8s_status = K8SStatus.NOT_CONFIGURED


async def run_parallel_provisioning_action(  # noqa: PLR0917
        resources: dict[str, ProvisionableResource],
        action: Literal["provision", "unprovision"],
        provisioners: dict[str, Provisioner],
        provisioning_params: dict[str, Any],
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
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


async def run_parallel_reservation_action(  # noqa: PLR0917
        resources: dict[str, ProvisionableResource],
        provisioners: dict[str, Provisioner],
        ansible_params: AnsibleParams,
        force: bool = False,
        ignore_failures: bool = False,
        skip_unreservable: bool = True,
        quiet: bool = False,
    ) -> None:
    """Reserve provided reservable resources in parallel."""

    # only reserve unprovisioned resources and not all of them
    target_resources = {k: v for k, v in resources.items() if not v.is_provisioned} if not force else resources

    grouped: dict[str, dict[str, ProvisionableResource]] = get_resources_by_provisioner(target_resources)
    tasks: dict[str, asyncio.Task] = {}

    for provisioner_name, resources_dict in grouped.items():
        tasks[provisioner_name] = asyncio.create_task(
            run_reservation_action(
                resources=resources_dict,
                provisioner_name=provisioner_name,
                provisioners=provisioners,
                ansible_params=ansible_params,
                ignore_failures=ignore_failures,
                force=force,
                skip_unreservable=skip_unreservable,
                quiet=quiet,
            ))

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=True,
                ignore_failures=ignore_failures,
            )


async def run_parallel_command(  # noqa: PLR0917
        resources: dict[str, SSHableResource],
        command: list[str],
        ansible_params: AnsibleParams,
        become: bool = False,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> dict[str, str]:
    """Run a command on provided SSH-able resources in parallel."""

    if not command:
        raise ValueError(f"Invalid command {command!r}.")

    tasks: dict[str, asyncio.Task] = {}

    for resource_name, resource_data in resources.items():
        if not force and not resource_data.is_provisioned:
            raise InvalidResourceStateError(
                f"{resource_data.category.value.upper()} {resource_name!r} is not provisioned."
            )

        inventory = get_ansible_inventory_line(
            resource_name=resource_name,
            resource_data=resource_data,
        )

        tasks[resource_name] = asyncio.create_task(
            run_ansible_command(
                command=command,
                runner_path=f"{ansible_params.runner_path}/{resource_data.category.value}/{resource_name}/run_cmd",
                inventory=inventory,
                hosts=resource_name,
                become=become,
                quiet=quiet,
            )
        )

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    outputs: dict[str, str] = {}

    for resource_name, result in zip(tasks, results, strict=False):
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )
        else:
            outputs[resource_name] = result # type: ignore

    return outputs


async def run_parallel_copy(  # noqa: PLR0917
        resources: dict[str, SSHableResource],
        local_path: str,
        remote_path: str,
        direction: Literal["to_resource", "from_resource"],
        ansible_params: AnsibleParams,
        become: bool = False,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
    """Copy a file/directory from or to the provided SSH-able resources in parallel."""

    tasks: dict[str, asyncio.Task] = {}

    for resource_name, resource_data in resources.items():
        if not force and not resource_data.is_provisioned:
            raise InvalidResourceStateError(
                f"{resource_data.category.value.upper()} {resource_name!r} is not provisioned."
            )

        inventory = get_ansible_inventory_line(
            resource_name=resource_name,
            resource_data=resource_data,
        )

        tasks[resource_name] = asyncio.create_task(
            run_ansible_copy(
                local_path=resolve_path(local_path), # resolve relative local path
                remote_path=remote_path, # do not resolve remote path
                direction=direction,
                runner_path=f"{ansible_params.runner_path}/{resource_data.category.value}/{resource_name}/copy",
                inventory=inventory,
                hosts=resource_name,
                become=become,
                quiet=quiet,
            )
        )

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            handle_ansible_result_exception(
                result=result,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )
