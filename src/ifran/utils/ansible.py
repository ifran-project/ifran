"""Ansible utilities and helpers."""

import asyncio
import logging
import shlex
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import ansible_runner

from ifran.models.provisioning import (
    SSHableResource,
)
from ifran.utils.utils import InvalidResourceStateError, resolve_path

logger = logging.getLogger(__name__)

def get_ansible_inventory_line(
    resource_name: str,
    resource_data: SSHableResource,
) -> str:
    """Return Ansible .ini inventory line to SSH access a provisionable resource."""

    ssh_info = resource_data.ssh_info

    vars = [
        f"ansible_host={ssh_info.hostname or resource_data.name}",
        f"ansible_port={ssh_info.port}",
        f"ansible_user={ssh_info.user}",
    ]
    if ssh_info.private_key_file:
        vars.append(f"ansible_ssh_private_key_file={shlex.quote(ssh_info.private_key_file)}")
    if ssh_info.password:
        vars.append(f"ansible_password={shlex.quote(ssh_info.password)}")
    if ssh_info.sudo_password:
        vars.append(f"ansible_become_password={shlex.quote(ssh_info.sudo_password)}")
    for key, value in resource_data.provisioning_params.items():
        if key.startswith("ansible_"):
            vars.append(f"{key}={value}")

    args = ssh_info.common_args
    if args:
        vars.append(f"ansible_ssh_common_args={shlex.quote(args)}")

    return f"{resource_name} " + " ".join(vars)


def get_ansible_output(runner: ansible_runner.Runner, output_keys: list[str]) -> dict[str, Any]:
    """Get the returned output of Ansible role returned with set_stats."""

    output = {}
    for event in runner.events:
        if event.get("event") == "playbook_on_stats":
            for name in output_keys:
                output[name] = event.get("event_data", {}).get("artifact_data", {}).get(name)
            break
    return output


def get_ansible_error(runner: ansible_runner.Runner) -> str:
    """Extract detailed errors from Ansible Runner."""

    errors = []

    failure_events = [
        "runner_on_failed",
        "runner_on_unreachable",
        "runner_on_async_failed",
    ]

    for event in runner.events:
        if event.get("event") not in failure_events:
            continue

        # event stdout contains the complete formatted failure
        event_stdout = event.get("stdout", "").strip()
        event_data = event.get("event_data", {})
        task = event_data.get("task", "Unknown task")
        host = event_data.get("host", "Unknown host")
        res = event_data.get("res", {})

        error = [f"Task: {task}", f"Host: {host}"]

        if event_stdout:
            error.append(f"Stdout: {event_stdout}")

        # extract other useful information from task res
        info_keys = ["msg", "cmd"]
        for key in info_keys:
            value = res.get(key)
            if value:
                error.append(f"{key.capitalize()}: {value}")

        errors.append("\n".join(error))

    if not errors:
        # include normal ansible output if no specific error information was found
        stdout = runner.stdout.read() if runner.stdout else ""
        if stdout:
            errors.append(f"Ansible output:\n{stdout}")
        else:
            return "No detailed Ansible error information available."

    return "\n\n".join(errors)



async def run_ansible_playbook(  # noqa: PLR0917
    playbook: list | dict[str, Any] | str,
    runner_path: str,
    inputs: dict[str, Any] | None = None,
    output_keys: list[str] | None = None,
    roles_paths: list[str] | None = None,
    inventory: str | dict[str, Any] | list | None = None,
    quiet: bool = False,
    retries: int = 5,
) -> dict[str, Any] | None:
    """Run an Ansible playbook."""

    # resolve relative paths in roles_paths if it's a list or a single path string
    if isinstance(roles_paths, list):
        resolved_roles_paths = [resolve_path(p) for p in roles_paths]
    else:
        resolved_roles_paths = resolve_path(roles_paths)

    for i in range(retries):
        try:
            # NOTE private_data_dir should be unique per ansible run, as the crucial vars get overridden
            # by other ansible runs if using the same private_data_dir

            # ensure runner path exists

            # add timestamp for more meaningful log collection
            timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H-%M-%S.%fZ")
            run_path = Path(runner_path) / timestamp
            run_path.mkdir(parents=True, exist_ok=True)

            # handle user interruptions cleanly
            stop_requested = threading.Event()

            run_args = {
                "private_data_dir": run_path,
                "roles_path": resolved_roles_paths,
                "inventory": inventory,
                # resolve playbook if it's a relative path
                "playbook": resolve_path(playbook),
                "extravars": inputs,
                "quiet": quiet,
                "cancel_callback": stop_requested.is_set
            }

            thread, runner = ansible_runner.run_async(**run_args)

            # wait until running ansible thread terminates
            try:
                await asyncio.to_thread(thread.join)
            except asyncio.CancelledError as e:
                stop_requested.set()

                # wait for runner to shut down cleanly
                await asyncio.shield(asyncio.to_thread(thread.join))

                raise asyncio.CancelledError("Ansible execution canceled by user.") from e

            if runner.status != "successful" or runner.rc != 0:
                raise RuntimeError(  # noqa: TRY301
                    f"Ansible playbook run not successful (status: {runner.status!r}, return code: {runner.rc!r})\n"
                    f"{get_ansible_error(runner)}" # type: ignore
                    )

            if output_keys is None:
                return None

            output = {}
            for key in output_keys:
                output[key] = get_ansible_output(runner=runner, output_keys=output_keys).get(key) # type: ignore
                if output[key] is None:
                    raise RuntimeError(f"Ansible playbook run completed but did not return expected output for {key!r}")  # noqa: TRY301

            return output  # noqa: TRY300

        except Exception as e:
            if i + 1 == retries:
                raise RuntimeError(f"Ansible playbook failed after {retries} attempts. Last error:\n{e}") from e

            logger.warning("Ansible playbook attempt %d/%d failed: %s\n\nRetrying...\n\n", i + 1, retries, e)

            await asyncio.sleep(2)

    return None


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
    retries: int = 5,
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
        retries=retries,
    )


async def run_ansible_command(  # noqa: PLR0917
    command: list[str],
    runner_path: str,
    hosts: str,
    inventory: str | dict[str, Any] | list,
    become: bool = False,
    quiet: bool = False,
    retries: int = 5,
) -> str:
    """Run a command on an Ansible inventory."""

    playbook = [
        {
            "hosts": hosts,
            "gather_facts": False,
            "become": become,
            "tasks": [
                {
                    "name": f"Run command {' '.join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.command": {
                        "argv": command,
                    },
                    "register": "command_result",
                    "changed_when": False,
                },
                {
                    "name": f"Display command output for {' '.join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.debug": {
                        "var": "command_result.stdout",
                    },
                },
                {
                    "name": f"Return command output for {' '.join(command)!r} on '{{{{ inventory_hostname }}}}'",
                    "ansible.builtin.set_stats": {
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
        retries=retries,
    )

    return result["command_output"]  # type: ignore


async def run_ansible_copy(  # noqa: PLR0917
    local_path: str,
    remote_path: str,
    direction: Literal["to_resource", "from_resource"],
    runner_path: str,
    hosts: str,
    inventory: str | dict[str, Any] | list,
    become: bool = False,
    quiet: bool = False,
    retries: int = 5,
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
        retries=retries,
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
