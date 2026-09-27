"""5G RAN utilities and helpers."""

from metamodel.models.core import AMFComponent, CoreComponentType
from metamodel.models.metamodel import MetaModel
from metamodel.models.ran import RANComponent, RANComponentType
from metamodel.models.ric import RICComponentType, ValidatedRICComponent
from metamodel.models.ru import RUType

from orchestrator.models.common import Deployed5GComponent
from orchestrator.models.core import MergedAMF
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.ran import ADVANCED_RAN_CONFIG_MAPPING, DeployedRANComponent, RANImplementation
from orchestrator.models.ric import MergedRIC
from orchestrator.utils.common_5g import (
    get_5g_components_by_type,
    populate_iface_for_deployed,
    reconcile_5g_component,
    reconcile_5g_components,
    resolve_component_reference,
    resolve_plmn_list,
    resolve_ru_reference,
)
from orchestrator.utils.k8s import K8SParams, generate_random_ip
from orchestrator.utils.radio import (
    derive_ran_radio_config,
)


def resolve_amf_ref(
        component_name: str,
        component_meta: RANComponent,
        amfs_meta: dict[str, AMFComponent],
        amfs_deployment: dict[str, Deployed5GComponent],
    ) -> None:
    """Resolve name reference of AMF in a RAN component."""

    amfs: dict[str, MergedAMF] = {}

    # before resolving amf reference, amf's n2 interface needs to be populated from its network info
    for amf_name, amf_meta in amfs_meta.items():
        amf_deployment = amfs_deployment[amf_name]

        populate_iface_for_deployed(
            iface_name="n2",
            component_meta=amf_meta,
            component_deployment=amf_deployment,
        )

        amfs[amf_name] = MergedAMF.model_validate({
            **amf_meta.model_dump(mode="json"),
            **amf_deployment.model_dump(mode="json"),
        })

    # resolve amf reference with amf's n2 ip address
    resolve_component_reference(
        component_name=component_name,
        component_meta=component_meta,
        ref_attribute="amf",
        registry=amfs,
        ready_attribute="is_installed",
        value_attribute="config.n2.ipv4EndPointAddress",
    )


def resolve_ric_ref(
        component_name: str,
        component_meta: RANComponent,
        rics_meta: dict[str, ValidatedRICComponent],
        rics_deployment: dict[str, Deployed5GComponent],
    ) -> None:
    """Resolve name reference of RIC in a RAN component."""

    rics: dict[str, MergedRIC] = {}

    # before resolving ric references, its e2 interface needs to be populated from its network info
    for ric_name, ric_meta in rics_meta.items():
        ric_deployment = rics_deployment[ric_name]

        populate_iface_for_deployed(
            iface_name="e2",
            component_meta=ric_meta,
            component_deployment=ric_deployment,
        )

        rics[ric_name] = MergedRIC.model_validate({
            **ric_meta.model_dump(mode="json"),
            **ric_deployment.model_dump(mode="json"),
        })

    # resolve ric reference with ric's e2 ip address
    resolve_component_reference(
        component_name=component_name,
        component_meta=component_meta,
        ref_attribute="ric",
        registry=rics,
        ready_attribute="is_installed",
        value_attribute="config.e2.ipv4EndPointAddress",
    )


def resolve_ocudu_zmq_ran(
        component_meta: RANComponent,
        component_deployment: DeployedRANComponent,
        k8s_params: K8SParams,
    ) -> None:
    """Resolve dependency between OCUDU simulated RAN and the UE."""

    if (
        component_meta.config.ru.type is RUType.SIMULATED and
        component_deployment.implementation is RANImplementation.OCUDU
        ):
        # simulated ocudu gnb/du (zmq) needs to know ue ip in advance
        ue_ip = generate_random_ip(k8s_params)

        # make sure advanced_config is populated
        if component_deployment.advanced_config is None:
            component_deployment.advanced_config = ADVANCED_RAN_CONFIG_MAPPING[
                RANImplementation.OCUDU][component_meta.type]

        component_deployment.advanced_config.ue_ip = component_deployment.advanced_config.ue_ip or ue_ip
        # NOTE this ip will later be taken from here and given as static_pod_ip to the ue component


def reconcile_ran(
        metamodel: MetaModel,
        deployment_model: DeploymentModel,
    ) -> None:
    """
    Ensure RAN is ready for deployment.

    - Resolve RAN component references to other components (slices, amf, ric, ru)
    - Resolve references between split RAN components
    - Derive implementation-specific radio configuration
    """

    ran_meta = metamodel.ran
    ran_deployment = deployment_model.ran

    core_meta = metamodel.core
    core_deployment = deployment_model.core

    ric_meta = metamodel.ric
    ric_deployment = deployment_model.ric

    rus_meta = metamodel.rus
    rus_provisioning = deployment_model.rus

    slices = metamodel.slices
    k8s_params = deployment_model.params.k8s

    grouped_meta = get_5g_components_by_type(ran_meta.components)
    cu_cps_meta = grouped_meta.get(RANComponentType.CU_CP, {})
    cu_ups_meta = grouped_meta.get(RANComponentType.CU_UP, {})
    cus_meta = grouped_meta.get(RANComponentType.CU, {})

    grouped_deployment = get_5g_components_by_type(ran_deployment.components)
    cu_cps_deployment = grouped_deployment.get(RANComponentType.CU_CP, {})
    cu_ups_deployment = grouped_deployment.get(RANComponentType.CU_UP, {})
    cus_deployment = grouped_deployment.get(RANComponentType.CU, {})

    amfs_meta = get_5g_components_by_type(core_meta.components, [CoreComponentType.AMF])
    amfs_deployment = get_5g_components_by_type(core_deployment.components, [CoreComponentType.AMF])

    rics_meta = get_5g_components_by_type(
        ric_meta.components, [RICComponentType.RIC, RICComponentType.E2TERM])
    rics_deployment = get_5g_components_by_type(
        ric_deployment.components, [RICComponentType.RIC, RICComponentType.E2TERM])

    # run standard component reconciliation on cu/cu_cp/cu_cp components first
    # because cu_up and cu_cp's e1, cu/cu_cp's f1c, and cu/cu_up's f1u interfaces
    # need to assigned a static ip before resolving cross-references
    reconcile_5g_components(
        components_meta=cus_meta | cu_cps_meta | cu_ups_meta,
        components_deployment=cus_deployment | cu_cps_deployment | cu_ups_deployment,
        k8s_params=k8s_params,
    )

    for component_name, component_meta in ran_meta.components.items():
        component_deployment = ran_deployment.components[component_name]

        args = {"component_name": component_name, "component_meta": component_meta}

        ## resolve references in ran components

        # resolve slice references in plmnList
        resolve_plmn_list(
            **args,
            slices=slices,
        )

        # resolve amf reference in cu_cp/cu/gnb components
        if component_meta.type in [RANComponentType.GNB, RANComponentType.CU, RANComponentType.CU_CP]:
            resolve_amf_ref(
                **args,
                amfs_meta=amfs_meta,
                amfs_deployment=amfs_deployment,
            )

        # resolve ric reference
        resolve_ric_ref(
            **args,
            rics_meta=rics_meta,
            rics_deployment=rics_deployment,
        )

        if component_meta.type in [RANComponentType.GNB, RANComponentType.DU]:
            # resolve ru reference for gnbs and dus
            resolve_ru_reference(
                 **args,
                rus_meta=rus_meta,
                rus_provisioning=rus_provisioning,
            )

            # NOTE gnbs and dus need ru reference to resolved first to select a default image based on ru type
            reconcile_5g_component(
                **args,
                component_deployment=component_deployment,
                k8s_params=k8s_params,
            )

            # derive implementation-specific radio parameters for gnb and du after ru name reference resolution
            derive_ran_radio_config(
                component_meta=component_meta,
                component_deployment=component_deployment,
                )

            # ocudu zmq specific case
            resolve_ocudu_zmq_ran(
                component_meta=component_meta,
                component_deployment=component_deployment,
                k8s_params=k8s_params,
            )

        # resolve references between split ran components
        # NOTE static ip assignment needs to be done before this
        if component_meta.type is RANComponentType.CU_UP:
            # resolve cu_cp reference in cu_cp with cu_cp's e1 ip address
            resolve_component_reference(
                **args,
                ref_attribute="cu_cp",
                registry=cu_cps_meta,
                value_attribute="config.e1.ipv4EndPointAddress",
            )
        elif component_meta.type is RANComponentType.DU:
            # resolve cu/cu_cp reference in du with cu/cu_cp's f1c ip address
            resolve_component_reference(
                **args,
                ref_attribute="cu_cp",
                registry=cu_cps_meta | cus_meta,
                value_attribute="config.f1c.ipv4EndPointAddress",
            )

            # resolve cu/cu_up reference in du with cu/cu_up's f1u ip address
            resolve_component_reference(
                **args,
                ref_attribute="cu_up",
                registry=cu_ups_meta | cus_meta,
                value_attribute="config.f1u.ipv4EndPointAddress",
            )
