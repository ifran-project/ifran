"""Kubernetes components Helm utilities and helpers."""

import asyncio
from ipaddress import IPv4Address
from typing import Literal

from metamodel.models.common import Component5G, TransportEndpoint

from orchestrator.models.ansible import AnsibleParams
from orchestrator.models.common import (
    ComponentDependencyGraph,
    Deployed5GComponent,
)
from orchestrator.models.k8s import (
    HelmParams,
    MultusNetworkStatus,
)
from orchestrator.models.provisioning import ProvisionableNode
from orchestrator.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_role,
)
from orchestrator.utils.common_5g import (
    EXPOSED_COMPONENT_INTERFACES,
    resolve_component_dependency_levels,
)
from orchestrator.utils.k8s import build_k8s_safe
from orchestrator.utils.utils import InvalidResourceStateError


def update_exposed_endpoints(
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """Update the 5G components's exposed interface endpoints with relevant IPs from network info after deployment."""

    for iface_name in EXPOSED_COMPONENT_INTERFACES.get(component_meta.category, []):

        # some interfaces can be None
        if hasattr(component_meta.config, iface_name) and getattr(component_meta.config, iface_name) is not None:
            iface_meta: TransportEndpoint = getattr(component_meta.config, iface_name)

            # populate interface ip if not explicitly set
            if iface_meta.ipv4EndPointAddress == IPv4Address("0.0.0.0"):

                # multus case
                if component_deployment.multus.enabled:
                    # look for interface ip with same name
                    for multus_iface in component_deployment.network_info: # type: ignore
                        if multus_iface.interface == iface_name:
                            iface_meta.ipv4EndPointAddress =(
                                multus_iface.ips[0] if multus_iface.ips
                                else iface_meta.ipv4EndPointAddress
                            )
                            break

                # non-multus case => pod ip
                else:
                    iface_meta.ipv4EndPointAddress = component_deployment.network_info # type: ignore


async def run_single_helm_action(  # noqa: C901, PLR0912, PLR0917
        component_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
        action: Literal["prepare", "install", "uninstall", "get_logs"],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        force: bool = False,
        quiet: bool = False,
    ) -> None:
    """Run Ansible Helm role corresponding to the given action on a single 5G component."""

    chart_name = build_k8s_safe(f"{component_deployment.implementation}-{component_name}")

    # NOTE preparing a prepared component is not considered in the check given its idempotence
    if not force:
        is_installed = component_deployment.is_installed
        category = component_meta.category.value.upper()

        # cannot install if already installed
        if is_installed and action == "install":
            raise InvalidResourceStateError(
                f"{category} component {component_name!r} is already installed."
            )

        # cannot uninstall or get logs if not installed
        if not is_installed and action in ["uninstall", "get_logs"]:
            if action == "uninstall":
                msg = f"{category} component {component_name!r} is already uninstalled."
            else:
                msg = f"Cannot fetch logs for uninstalled {category} component {component_name!r}."

            raise InvalidResourceStateError(msg)

    helm_params = HelmParams(
        chart_name=chart_name,
        helm_build_dir=f"/root/helm-charts/{component_meta.category}/{chart_name}",
        output_with_multus=component_deployment.multus.enabled,
    )

    args = {
        "role": f"helm/{action}",
        "inputs": {
            "component_name": component_name,
            # merged component (meta + deployment)
            # NOTE use serialize_as_any=True to prevent pydantic from replacing models
            # because of type mismatch after reference resolution
            "component": {**(
                component_meta.model_dump(mode="json", serialize_as_any=True) |
                component_deployment.model_dump(mode="json")
            )},
            **helm_params.model_dump(mode="json"),
        },
        "runner_path": f"{ansible_params.runner_path}/{component_meta.category.value}/{component_name}/helm/{action}",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
        "quiet": quiet,
    }

    # expect network info output after installation
    if action == "install":
        args["output_keys"] = ["network_info"]

    # expect logs output after get_logs actions
    elif action == "get_logs":
        args["output_keys"] = ["logs"]

    try:
        result = await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(
            f"{component_meta.category.value.upper()} component {component_name!r} Helm {action} not successful."
        ) from e

    # update component state
    if action == "install":
        component_deployment.is_installed = True

        # update network information
        if helm_params.output_with_multus:
            # if multus is used, output list of multus network status
            component_deployment.network_info = [
                MultusNetworkStatus.model_validate(item)
                for item in result["network_info"] # type: ignore
            ]

        else:
            # if multus is not used, output pod ip address directly
            component_deployment.network_info = IPv4Address(result["network_info"]) # type: ignore

    elif action == "get_logs":
        component_deployment.logs = result["logs"] # type: ignore

    elif action == "uninstall":
        component_deployment.is_installed = False
        # reset network info to None
        component_deployment.network_info = None


async def run_parallel_helm_action(  # noqa: PLR0917
        components_meta: dict[str, Component5G],
        components_deployment: dict[str, Deployed5GComponent],
        action: Literal["prepare", "install", "uninstall", "get_logs"],
        node_name: str,
        node_data: ProvisionableNode,
        ansible_params: AnsibleParams,
        order: ComponentDependencyGraph | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
    """Run Helm action in parallel on provided 5G components."""

    levels = resolve_component_dependency_levels(
        components=components_meta,
        dependencies=order,
    )

    for level in levels:

        level_components = (
            (name, components_meta[name], components_deployment[name])
            for name in level
            if name in components_meta and name in components_deployment
        )

        results = await asyncio.gather(
            *(
                run_single_helm_action(
                    component_name=name,
                    component_meta=component_meta,
                    component_deployment=component_deployment,
                    action=action,
                    node_name=node_name,
                    node_data=node_data,
                    ansible_params=ansible_params,
                    force=force,
                    quiet=quiet,
                )
                for name, component_meta, component_deployment in level_components
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
