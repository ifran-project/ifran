"""5G core utilities and helpers."""

from typing import Literal

from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.core import CoreDeployment
from orchestrator.models.deployment.k8s import HelmParams, K8SComponent
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import Core, CoreComponent
from orchestrator.models.meta.slice import Slice
from orchestrator.utils.ansible import run_ansible_role
from orchestrator.utils.common import InvalidResourceStateError
from orchestrator.utils.common_5g import reconcile_5g_component


def reconcile_core_component(
        component_name: str,
        component_meta: CoreComponent,
        component_k8s: K8SComponent,
        slices: dict[str, Slice],
    ): # wrapper function that might be extended later
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
    ):
    """Ensure 5G core is ready for deployment."""

    for name, (component_meta, component_k8s) in {
        k:(core_meta.components[k], core_deployment.components[k])
        for k in (core_meta.components.keys() & core_deployment.components.keys()) # keys supposed to match
        }.items():

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
        ):
    """Run Ansible Helm prepare/install/uninstall role on 5G core database."""

    if not force and (
        (core_deployment.is_database_present and action == "install") or 
        (not core_deployment.is_database_present and action == "uninstall")
        ):
        raise InvalidResourceStateError(f"5G core database is already {action}ed.")

    helm_params = HelmParams(
        chart_name=f"{core_meta.type.value}-database",
        helm_build_dir=f"/root/helm-charts/{Category5G.CORE}/{core_meta.type.value}-database",
        render=False
    ).model_dump(mode="json")

    component = {
            "category": Category5G.CORE.value,
            "implementation": core_meta.type.value,
            "namespace": f"{core_meta.type.value}-{Category5G.CORE.value}",
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
    try:
        await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(f"5G core database Helm {action} not successful") from e

    # update database status in core deployment
    core_deployment.is_database_present = (action == "install")
