"""5G core utilities and helpers."""

import asyncio
from ipaddress import IPv4Address
from typing import Literal

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.core import (
    CoreComponentType,
    NSSFComponent,
    SMFComponent,
    UPFComponent,
)
from metamodel_3gpp.models.metamodel import MetaModel
from metamodel_3gpp.models.ran import RANComponentType
from metamodel_3gpp.models.slice import Slice
from metamodel_3gpp.models.ue import UE, UEConfiguration
from metamodel_3gpp.utils import URL
from pydantic import IPvAnyAddress, TypeAdapter

from ifran.models.ansible import AnsibleParams
from ifran.models.core import CoreDeployment, CoreImplementation
from ifran.models.deployment import DeploymentModel
from ifran.models.k8s import HelmParams
from ifran.models.provisioning import ProvisionableNode
from ifran.utils.ansible import (
    get_ansible_inventory_line,
    handle_ansible_result_exception,
    run_ansible_role,
)
from ifran.utils.common_5g import (
    get_5g_components_by_type,
    reconcile_5g_components,
    resolve_plmn_list,
    resolve_snssai_list,
    resolve_snssai_reference,
)
from ifran.utils.defaults import DEFAULT_CORE_DATABASE_IMAGES
from ifran.utils.ue import resolve_gnb_ref, resolve_ue_slices_dnns
from ifran.utils.utils import InvalidResourceStateError, ReferenceNotFoundError


def resolve_smf_refs(
    component_name: str,
    component_meta: SMFComponent,
    upfs: dict[str, UPFComponent],
) -> None:
    """Resolve list of UPF references in an SMF component configuration."""

    # resolve upf references one by one
    for i in range(len(component_meta.config.upfs)):
        upf_reference = component_meta.config.upfs[i]
        upf_meta = upfs.get(upf_reference)

        if upf_meta is None:
            raise ReferenceNotFoundError(f"SMF component {component_name!r} reference undefined UPF {upf_reference!r}.")

        component_meta.config.upfs[i] = upf_meta  # type: ignore


def resolve_nssf_refs(
    component_name: str,
    component_meta: NSSFComponent,
    slices: dict[str, Slice],
) -> None:
    """Resolve slice references in an NSSF component configuration."""

    config = component_meta.config

    # nsiInfoList[*].snssai
    for nsi_info in config.nsiInfoList:
        nsi_info.snssai = resolve_snssai_reference(
            component_name=component_name,
            component_meta=component_meta,
            reference=nsi_info.snssai,
            slices=slices,
            field_name="nsiInfoList.snssai",
        )  # type: ignore

    # taInfoList[*]
    for ta_info in config.taInfoList:
        resolve_snssai_list(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            config=ta_info,
        )

        resolve_snssai_list(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            config=ta_info.restrictedSnssaiList,
        )

    # amfInfoList[*].amfList[*]
    for amf_info_set in config.amfInfoList:
        for amf_info in amf_info_set.amfList:
            resolve_snssai_list(
                component_name=component_name,
                component_meta=component_meta,
                slices=slices,
                config=amf_info.supportedNssaiAvailabilityData,
            )


def populate_core_database_image(core_deployment: CoreDeployment) -> None:
    """Populate 5G core database image from known defaults."""

    if core_deployment.database_params.image is None:
        database_image = DEFAULT_CORE_DATABASE_IMAGES.get(core_deployment.implementation)

        # if no default database image is available raise an error
        if database_image is None:
            raise ValueError(f"{core_deployment.implementation.upper} database has no container image.")

        core_deployment.database_params.image = DEFAULT_CORE_DATABASE_IMAGES.get(core_deployment.implementation)


def reconcile_core(  # noqa: C901
    metamodel: MetaModel,
    deployment_model: DeploymentModel,
) -> None:
    """
    Ensure 5G core is ready for deployment.

    Additional reconciliation:
    - Populate 5G core database image
    - Resolve slice references in 5G core components
    - Find NRF URI in 5G core components
    - Resolve 'gnb' reference in UE components to make them ready for database registration
    """

    core_meta = metamodel.core
    core_deployment = deployment_model.core

    ran_meta = metamodel.ran
    ran_deployment = deployment_model.ran

    slices = metamodel.slices
    k8s_params = deployment_model.params.k8s

    upfs = get_5g_components_by_type(core_meta.components, [CoreComponentType.UPF])  # type: ignore

    gnbs_meta = get_5g_components_by_type(ran_meta.components, [RANComponentType.GNB, RANComponentType.DU])  # type: ignore
    gnbs_deployment = get_5g_components_by_type(ran_deployment.components, [RANComponentType.GNB, RANComponentType.DU])  # type: ignore

    nrf_uri = None

    # populate database image if not already set
    populate_core_database_image(core_deployment=core_deployment)

    # run standard component reconciliation on ALL components first
    # because upf's n4 interface need to be assigned a static ip smf ref resolution
    reconcile_5g_components(
        components_meta=core_meta.components,  # type: ignore
        components_deployment=core_deployment.components,  # type: ignore
        k8s_params=k8s_params,
    )

    for component_name, component_meta in core_meta.components.items():
        component_deployment = core_deployment.components[component_name]

        args = {"component_name": component_name, "component_meta": component_meta}

        # resolve references in core components
        if component_meta.type in [CoreComponentType.SMF, CoreComponentType.UPF]:
            resolve_snssai_list(**args, slices=slices)

        elif component_meta.type is CoreComponentType.NSSF:
            resolve_nssf_refs(**args, slices=slices)

        elif component_meta.type in [CoreComponentType.AMF, CoreComponentType.NRF]:
            resolve_plmn_list(**args, slices=slices)

        # look for the NRF to populate nrfUri
        # NOTE latest NRF found takes precedence if many
        if component_meta.type is CoreComponentType.NRF:
            scheme = "https" if component_meta.config.sbi.tls.enabled else "http"
            service_name = f"{component_deployment.implementation}-{component_name}"
            nrf_uri = TypeAdapter(URL).validate_python(f"{scheme}://{service_name}:{component_meta.config.sbi.port}")

    # second loop: populate NRF URI and resolve SMF's UPF references
    # NOTE UPF's 'snssaiList' needs to be resolved before the SMF's 'upfs' list is resolved with actual UPF components

    # populate nrf uri field only after nrf component has been found
    if nrf_uri is None:
        raise RuntimeError("Couldn't find any NRF component in the 5G core components.")

    for component_name, component_meta in core_meta.components.items():
        if component_meta.config.nrfUri is None:
            component_meta.config.nrfUri = nrf_uri

        if component_meta.type is CoreComponentType.SMF:
            resolve_smf_refs(component_name=component_name, component_meta=component_meta, upfs=upfs)  # type: ignore

    # resolve ues references to prepare them for database registration
    for ue_name, ue_meta in metamodel.ues.items():
        # resolve ue's slice and dnn references
        resolve_ue_slices_dnns(
            component_name=ue_name,
            component_meta=ue_meta,
            slices=slices,
        )

        # resolve ue's gnb reference
        resolve_gnb_ref(
            component_name=ue_name,
            component_meta=ue_meta,
            gnbs_meta=gnbs_meta,  # type: ignore
            gnbs_deployment=gnbs_deployment,  # type: ignore
            populate_address=False,  # don't populate ue's gnb ip (not needed)
        )


async def run_core_database_helm_action(  # noqa: PLR0917
    core_deployment: CoreDeployment,
    action: Literal["prepare", "install", "uninstall"],
    node_name: str,
    node_data: ProvisionableNode,
    ansible_params: AnsibleParams,
    force: bool = False,
    quiet: bool = False,
) -> None:
    """Run Ansible Helm prepare/install/uninstall role on 5G core database."""

    if not force:
        is_installed = core_deployment.database_params.is_installed

        if is_installed and action == "install" or not is_installed and action == "uninstall":
            raise InvalidResourceStateError(f"5G core database is already {action}ed.")

        if is_installed and action == "prepare":
            return

    helm_params = HelmParams(
        chart_name=f"{core_deployment.implementation.value}-database",
        helm_build_dir=f"$HOME/helm-charts/{Category5G.CORE}/{core_deployment.implementation.value}-database",
    ).model_dump(mode="json")

    component = {
        "category": Category5G.CORE.value,
        "implementation": core_deployment.implementation.value,
        "namespace": f"{core_deployment.implementation.value}-{Category5G.CORE.value}",
        "type": "database",
        "rendered_files": ["values.yaml"],
        **core_deployment.database_params.model_dump(mode="json"),
    }

    args = {
        "role": f"helm/{action}",
        "inputs": {"component": component, **helm_params},
        "runner_path": f"{ansible_params.runner_path}/{component['category']}/database/helm/{action}",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
        "quiet": quiet,
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
        core_deployment.database_params.is_installed = True
        # retrieve database pod ip
        core_deployment.database_params.ip = IPv4Address(result["network_info"])  # type: ignore
    elif action == "uninstall":
        core_deployment.database_params.is_installed = False


async def run_single_database_subscriber_action(  # noqa: PLR0917
    ue_name: str,
    ue_config: UEConfiguration,
    core_implementation: CoreImplementation,
    action: Literal["add", "remove"],
    database_ip: IPvAnyAddress | None,
    node_name: str,
    node_data: ProvisionableNode,
    ansible_params: AnsibleParams,
    force: bool = False,
    quiet: bool = False,
) -> None:
    """Add/remove a single UE/subscriber on the 5G core database."""

    if not force and database_ip is None:
        raise InvalidResourceStateError(
            f"{core_implementation.value.upper()} 5G core database has an undefined IP address."
        )

    args = {
        "role": f"database/subscriber/{action}/{core_implementation}",
        "inputs": {
            "ue_name": ue_name,
            # NOTE use serialize_as_any=True to prevent pydantic from replacing models
            # because of type mismatch after reference resolution (e.g. slice: str -> Slice, gnb: str -> GNBComponent)
            "ue_config": ue_config.model_dump(mode="json", serialize_as_any=True),
            "database_ip": str(database_ip),
        },
        "runner_path": f"{ansible_params.runner_path}/core/database/subscriber/{action}",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
        "quiet": quiet,
    }
    try:
        await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(
            f"Failed to {action} UE {ue_name!r} on {core_implementation.value.upper()} 5G core database."
        ) from e


async def run_parallel_database_subscriber_action(  # noqa: PLR0917
    ues: dict[str, UE],
    core_implementation: CoreImplementation,
    action: Literal["add", "remove"],
    database_ip: IPvAnyAddress | None,
    node_name: str,
    node_data: ProvisionableNode,
    ansible_params: AnsibleParams,
    force: bool = False,
    ignore_invalid_states: bool = False,
    ignore_failures: bool = False,
    quiet: bool = False,
) -> None:
    """Add/remove multiple UEs in parallel."""

    tasks: dict[str, asyncio.Task] = {}
    for name, ue in ues.items():
        tasks[name] = asyncio.create_task(
            run_single_database_subscriber_action(
                ue_name=name,
                ue_config=ue.config,
                core_implementation=core_implementation,
                action=action,
                database_ip=database_ip,
                node_name=node_name,
                node_data=node_data,
                ansible_params=ansible_params,
                force=force,
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
