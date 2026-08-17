"""Ansible utilities and helpers."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ansible_runner

from orchestrator.models.deployment.provisioning import (
    ProvisionableResource,
)
from orchestrator.utils.common import InvalidResourceStateError


def get_ansible_inventory_line(
        resource_name: str,
        resource_data: ProvisionableResource,
        ) -> str:
    """Return Ansible .ini inventory line to SSH access a provisionable resource."""

    ssh_info = resource_data.ssh_info

    vars = [
        f"ansible_host={ssh_info.hostname or resource_name}",
        f"ansible_port={ssh_info.port}",
        f"ansible_user={ssh_info.user}",
    ]
    if ssh_info.private_key_file:
        vars.append(f"ansible_ssh_info_private_key_file={ssh_info.private_key_file}")
    if ssh_info.password:
        vars.append(f"ansible_password={ssh_info.password}")
    if ssh_info.sudo_password:
        vars.append(f"ansible_become_password={ssh_info.sudo_password}")

    args = ssh_info.common_args
    if args:
        vars.append(f"ansible_ssh_common_args={args!r}")

    return f"{resource_name} " + " ".join(vars)


def get_ansible_output(runner: ansible_runner.runner.Runner, output_keys: list[str]) -> dict[str, Any]:
    """Get the returned output of Ansible role returned with set_stats."""

    output = {}
    for event in runner.events:
        if event.get("event") == "playbook_on_stats":
            for name in output_keys:
                output[name] = event.get("event_data", {}).get("artifact_data", {}).get(name)
            break
    return output


async def run_ansible_playbook(
        playbook: list | dict[str, Any] | str,
        runner_path: str,
        inputs: dict[str, Any] | None = None,
        output_keys: list[str] | None = None,
        roles_path: str | None = None,
        inventory: str | dict[str, Any] | list | None = None,
        ) -> dict[str, Any] | None:
        """Run an Ansible playbook."""

        # NOTE private_data_dir should be unique per ansible run, as the crucial vars get overriden by other ansible runs if using the same private_data_dir
        # ensure runner path exists
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S.%fZ") # add timestamp for more meaningful log collection
        run_path = Path(runner_path) / timestamp
        run_path.mkdir(parents=True, exist_ok=True)

        run_args = {
            "private_data_dir": run_path,
            "roles_path": roles_path,
            "inventory": inventory,
            "playbook": playbook,
            "extravars": inputs,
        }

        thread, runner = ansible_runner.run_async(**run_args)

        # wait until runnng ansible thread terminates
        await asyncio.to_thread(thread.join)
        if runner.status != "successful" or runner.rc != 0:
            raise RuntimeError(f"Playbook run not successful (status: {runner.status!r}, return code: {runner.rc!r})")

        if output_keys is None:
            return

        output = {}
        for key in output_keys:
            output[key] = get_ansible_output(runner=runner, output_keys=output_keys).get(key)
            if output[key] is None:
                raise RuntimeError(f"Playbook run completed but did not return expected output for {key!r}")

        return output


async def run_ansible_role(
        role: str,
        runner_path: str,
        inputs: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
        output_keys: list[str] | None = None,
        roles_path: str | None = None,
        hosts: str = "localhost",
        inventory: str | dict[str, Any] | list | None = None,
        become: bool = False,
        ) -> dict[str, Any] | None:
    """Run an Ansible role."""

    playbook = [
        {
            "hosts": hosts,
            "gather_facts": False,
            "roles": [{"role": role}],
            "become": become,
        }
    ]
    if extra_params:
        playbook[0] |= extra_params

    return await run_ansible_playbook(
        playbook=playbook,
        runner_path=runner_path,
        inputs=inputs,
        output_keys=output_keys,
        roles_path=roles_path,
        inventory=inventory,
        )


def handle_ansible_result_exception(
        result: Exception,
        ignore_invalid_states: bool,
        ignore_failures: bool,
        ) -> Exception | None:
    """Handle Ansible run exception based on its type and provided options."""

    if isinstance(result, InvalidResourceStateError):
        if not ignore_invalid_states:
            raise result
    elif not ignore_failures:
        raise result
    else:
        return None
