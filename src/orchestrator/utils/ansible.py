"""Ansible utilities and helpers."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import ansible_runner

from orchestrator.models.provisioning import (
    SSHableResource,
)
from orchestrator.utils.utils import InvalidResourceStateError, resolve_path


def get_ansible_inventory_line(
        resource_name: str,
        resource_data: SSHableResource,
    ) -> str:
    """Return Ansible .ini inventory line to SSH access a provisionable resource."""

    ssh_info = resource_data.ssh_info

    vars = [
        f"ansible_host={ssh_info.hostname or resource_name}",
        f"ansible_port={ssh_info.port}",
        f"ansible_user={ssh_info.user}",
    ]
    if ssh_info.private_key_file:
        vars.append(f"ansible_ssh_private_key_file={ssh_info.private_key_file}")
    if ssh_info.password:
        vars.append(f"ansible_password={ssh_info.password}")
    if ssh_info.sudo_password:
        vars.append(f"ansible_become_password={ssh_info.sudo_password}")
    for key, value in resource_data.provisioning_params.items():
        if key.startswith("ansible_"):
            vars.append(f"{key}={value}")

    args = ssh_info.common_args
    if args:
        vars.append(f"ansible_ssh_common_args={args!r}")

    return f"{resource_name} " + " ".join(vars)


def get_ansible_output(runner, output_keys: list[str]) -> dict[str, Any]:
    """Get the returned output of Ansible role returned with set_stats."""

    output = {}
    for event in runner.events:
        if event.get("event") == "playbook_on_stats":
            for name in output_keys:
                output[name] = event.get("event_data", {}).get("artifact_data", {}).get(name)
            break
    return output


async def run_ansible_playbook(  # noqa: PLR0917
        playbook: list | dict[str, Any] | str,
        runner_path: str,
        inputs: dict[str, Any] | None = None,
        output_keys: list[str] | None = None,
        roles_paths: list[str] | None = None,
        inventory: str | dict[str, Any] | list | None = None,
        quiet: bool = False,
    ) -> dict[str, Any] | None:
    """Run an Ansible playbook."""

    # NOTE private_data_dir should be unique per ansible run, as the crucial vars get overridden by other ansible runs
    # if using the same private_data_dir

    # ensure runner path exists

    # add timestamp for more meaningful log collection
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S.%fZ")
    run_path = Path(runner_path) / timestamp
    run_path.mkdir(parents=True, exist_ok=True)

    # resolve relative paths in roles_paths if it's a list or a single path string
    if isinstance(roles_paths, list):
        resolved_roles_paths = [resolve_path(p) for p in roles_paths]
    else:
        resolved_roles_paths = resolve_path(roles_paths)

    run_args = {
        "private_data_dir": run_path,
        "roles_path": resolved_roles_paths,
        "inventory": inventory,
        # resolve playbook if it's a relative path
        "playbook": resolve_path(playbook),
        "extravars": inputs,
        "quiet": quiet,
    }

    thread, runner = ansible_runner.run_async(**run_args)

    # wait until running ansible thread terminates
    await asyncio.to_thread(thread.join)
    if runner.status != "successful" or runner.rc != 0:
        raise RuntimeError(f"Playbook run not successful (status: {runner.status!r}, return code: {runner.rc!r})")

    if output_keys is None:
        return None

    output = {}
    for key in output_keys:
        output[key] = get_ansible_output(runner=runner, output_keys=output_keys).get(key)
        if output[key] is None:
            raise RuntimeError(f"Playbook run completed but did not return expected output for {key!r}")

    return output


async def run_ansible_role(  # noqa: PLR0917
        role: str,
        runner_path: str,
        inputs: dict[str, Any] | None = None,
        extra_params: dict[str, Any] | None = None,
        output_keys: list[str] | None = None,
        roles_paths: list[str] | None = None,
        hosts: str = "localhost",
        inventory: str | dict[str, Any] | list | None = None,
        become: bool = False,
        quiet: bool = False,
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
        roles_paths=roles_paths,
        inventory=inventory,
        quiet=quiet,
        )


async def run_ansible_command(  # noqa: PLR0917
        command: list[str],
        runner_path: str,
        hosts: str,
        inventory: str | dict[str, Any] | list,
        become: bool = False,
        quiet: bool = False,
    ) -> str:
    """Run a command on an Ansible inventory."""

    playbook = [
        {
            "hosts": hosts,
            "gather_facts": False,
            "become": become,
            "tasks": [
                {
                    "name": f"Run command {" ".join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.command": {
                        "argv": command,
                    },
                    "register": "command_result",
                    "changed_when": False,
                },
                {
                    "name": f"Display command output for {" ".join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.debug": {
                        "var": "command_result.stdout",
                    },
                },
                {
                    "name": f"Return command output for {" ".join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.set_stats":
                    {
                        "data": {
                            "command_output": "{{ command_result.stdout }}",
                        },
                    },
                },
            ],
        }
    ]

    result = await run_ansible_playbook(
        playbook=playbook,
        runner_path=runner_path,
        inventory=inventory,
        output_keys=["command_output"],
        quiet=quiet,
    )

    return result["command_output"] # type: ignore


async def run_ansible_copy(  # noqa: PLR0917
    local_path: str,
    remote_path: str,
    direction: Literal["to_resource", "from_resource"],
    runner_path: str,
    hosts: str,
    inventory: str | dict[str, Any] | list,
    become: bool = False,
    quiet: bool = False,
    ) -> None:
    """Copy a file/directory to or from an Ansible inventory host."""

    if direction == "to_resource":
        transfer_task = {
            "name": f"Copy {local_path!r} to '{{{{ inventory_hostname }}}}' at {remote_path!r}",
            "ansible.builtin.copy": {
                "src": local_path,
                "dest": remote_path,
            },
        }
    else:
        transfer_task = {
            "name": f"Copy {local_path!r} from '{{{{ inventory_hostname }}}}' at {remote_path!r}",
            "ansible.builtin.fetch": {
                "src": remote_path,
                "dest": local_path,
                "flat": True,
            },
        }

    playbook = [
        {
            "hosts": hosts,
            "gather_facts": False,
            "become": become,
            "tasks": [transfer_task],
        }
    ]

    await run_ansible_playbook(
        playbook=playbook,
        runner_path=runner_path,
        inventory=inventory,
        quiet=quiet,
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
