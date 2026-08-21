"""Common 5G utilities and helpers."""

from collections import defaultdict
from typing import Any

from orchestrator.models.deployment.k8s import (
    ExposedPort,
    K8SComponent,
)
from orchestrator.models.deployment.provisioning import ProvisionableRU
from orchestrator.models.deployment.ric import RICType
from orchestrator.models.meta.common import (
    EXPOSED_COMPONENT_INTERFACES,
    Category5G,
    Component5G,
    TransportEndpoint,
)
from orchestrator.models.meta.core import (
    CoreComponent,
    CoreComponentType,
    NSSFConfig,
)
from orchestrator.models.meta.ran import (
    RANComponent,
    RANComponentType,
)
from orchestrator.models.meta.ru import RU, RUType
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE, UEType
from orchestrator.utils.common import (
    InvalidResourceStateError,
    ReferenceNotFounError,
)
from orchestrator.utils.defaults import (
    DEFAULT_CORE_IMAGES,
    DEFAULT_RAN_IMAGES,
    DEFAULT_UE_IMAGES,
    POD_PRIVELEGES,
)


def resolve_component_reference(
        component_name: str,
        component_meta: RANComponent,
        ref_attribute: str,
        registry: dict[str, Any],
        ready_attribute: str | None = None,
        value_attribute: str | None = None,
    ) -> None:
    """Resolve a single string reference on a component config."""

    # skip if component doesn't have 'ref_attribute' or is None
    if not hasattr(component_meta.config, ref_attribute) or getattr(component_meta.config, ref_attribute) is None:
        return

    reference = getattr(component_meta.config, ref_attribute)
    if not isinstance(reference, str): # reference already resolved
        return

    # get actual referenced target with 'ref_attribute' from the 'registry' if it exists
    target = registry.get(reference)

    if target is None:
        raise ReferenceNotFounError(f"{component_meta.category.value.upper()} component {component_name!r} "
                                    f"refrences undefined {ref_attribute.upper()} {reference!r}.")

    # optionally verify that the referenced target is ready via 'ready_attribute' if it is True
    if ready_attribute and not getattr(target, ready_attribute):
        raise InvalidResourceStateError(f"{reference!r} referenced by {component_meta.category.value} component "
                                        f"{component_name!r} is not ready ({ready_attribute}=False).")

    # replace the string reference with the target's 'value_attribute' or the target itself if value_attribute is None
    value = target if value_attribute is None else getattr(target, value_attribute)
    setattr(component_meta.config, ref_attribute, value)


class _TempMergedRU(ProvisionableRU):
    """RU merged model to temporarily resolve the RU reference."""
    resolved_reference: RU


def resolve_ru_reference(
        component_name: str,
        component_meta: K8SComponent,
        rus_meta: dict[str, RU],
        rus_provisioning: dict[str, ProvisionableRU],
    ) -> None:
    """Resolve RU name reference in a 5G component."""

    # merge rus (we need the meta for ran config parameters and provisioning for readiness state)
    rus: dict[str, _TempMergedRU] = {}
    for ru_name, ru_meta in rus_meta.items():
        if ru_meta.type is RUType.SIMULATED:
            ru_prov = {"is_provisioned": True} # simulated rus are not part of deployment model, so we just consider them as "provisioned"
        else:
            ru_prov = rus_provisioning[ru_name].model_dump(mode="json") # ru_meta and rus_provisioning are supposed to be synchronized by this point
        rus[ru_name] = _TempMergedRU.model_validate({**ru_prov, "resolved_reference": ru_meta})

    resolve_component_reference(
        component_name=component_name,
        component_meta=component_meta,
        ref_attribute="ru",
        registry=rus,
        ready_attribute="is_provisioned",
        value_attribute="resolved_reference",
    )


def resolve_snssai_reference(
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
        value: Slice | str,
        field_name: str,
    ) -> Slice:
    """Resolve a single slice reference by name."""

    if isinstance(value, Slice):
        return value

    if value in slices:
        return slices[value]

    raise ReferenceNotFounError(
        f"{component_meta.category.value.capitalize()} component "
        f"{component_name!r} references undefined slice {value!r} "
        f"in {field_name!r}."
    )


def resolve_snssai_list(
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
        config: Any,
    ) -> None:
    """Resolve slice references by name in an S-NSSAI list."""

    if hasattr(config, "snssaiList"):
        snssai_list: list[Slice | str] = config.snssaiList

        for i, snssai in enumerate(snssai_list):
            config.snssaiList[i] = resolve_snssai_reference(
                component_name=component_name,
                component_meta=component_meta,
                slices=slices,
                value=snssai,
                field_name="snssaiList",
            )


def resolve_plmn_list(        
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve slices references by name in 'plmnList' field of 5G components."""

    config = component_meta.config

    for plmn_item in config.plmnList:
        resolve_snssai_list(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            config=plmn_item,
        )


def resolve_nssf_slices(
        component_name: str,
        component_meta: CoreComponent,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve slice references in an NSSF component configuration."""

    config = component_meta.config

    if not isinstance(config, NSSFConfig):
        return

    # nsiInfoList[*].snssai
    for nsi_info in config.nsiInfoList:
        nsi_info.snssai = resolve_snssai_reference(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            value=nsi_info.snssai,
            field_name="nsiInfoList.snssai",
        )

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


def resolve_ue_slices_dnns(
        component_name: str,
        component_meta: UE,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve UE slices and DNNs."""

    ue_config = component_meta.config

    for subscription in ue_config.subscriptions:
        subscription.snssai = resolve_snssai_reference(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            value=subscription.snssai,
            field_name="subscription.snssai",
        )

        if isinstance(subscription.dnn, str):
            subscription_dnn = subscription.snssai.dnns.get(subscription.dnn)
            if subscription_dnn is None:
                raise ReferenceNotFounError(f"UE {component_name!r} references undefined DNN {subscription.dnn!r}.")

            subscription.dnn = subscription_dnn


def resolve_component_slices(        
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve slice references in 5G components."""

    args = {"component_name": component_name, "component_meta": component_meta, "slices": slices}
    if component_meta.type is CoreComponentType.NSSF:
        resolve_nssf_slices(**args)
    if component_meta.type in [CoreComponentType.SMF, CoreComponentType.UPF]:
        resolve_snssai_list(**args, config=component_meta.config)
    if component_meta.type in [CoreComponentType.AMF, CoreComponentType.NRF] or component_meta.category is Category5G.RAN:
        resolve_plmn_list(**args)
    if component_meta.category is Category5G.UE:
        resolve_ue_slices_dnns(**args)


def populate_default_images(
        component_name: str,
        component_meta: Component5G,
        component_k8s: K8SComponent,
    ) -> None:
    """Populate 5G component image from default images."""

    # if not implementation is defined raise an error
    if component_meta.implementation is None:
        raise ValueError(
            f"{component_meta.category.value.capitalize()} component {component_name!r} "
            f"has no defined {component_meta.category.value} implementation."
        )

    match component_meta.category:
        case Category5G.CORE:
            if component_k8s.image is None and DEFAULT_CORE_IMAGES.get(component_meta.implementation):
                component_k8s.image = DEFAULT_CORE_IMAGES.get(component_meta.implementation, {}
                                                              ).get(component_meta.type)

        case Category5G.RAN:
            # for RAN components, RU is supposed to be resolved before this
            config = component_meta.config
            if hasattr(config, "ru") and isinstance(config.ru, RU):
                ru_type = config.ru.type
            else:
                # NOTE CUs, CU-CPs and CU-UPs dont have and ru field, so give them simulated one for simplicity
                ru_type = RUType.SIMULATED

                component_k8s.image = DEFAULT_RAN_IMAGES.get(component_meta.implementation, {}
                                                            ).get(ru_type, {}).get(component_meta.type)

        case Category5G.UE:
            if component_k8s.image is None and DEFAULT_UE_IMAGES.get(component_meta.implementation):
                component_k8s.image = DEFAULT_UE_IMAGES.get(component_meta.implementation, {}
                                                              ).get(component_meta.type)

        case Category5G.RIC:
            # TODO
            pass

    # if not default image is available, it stays None but is required
    if component_k8s.image is None:
        raise ValueError(f"{component_meta.category.value.capitalize()} component {component_name!r} has no container image.")


def reconcile_5g_component(
        component_name: str,
        component_meta: Component5G,
        component_k8s: K8SComponent,
        slices: dict[str, Slice],
    ) -> None:
    """
    Ensure the 5G component Kubernetes deployment model is ready for deployment.
    Is slices is None, slices name references are not resolved.
    """

    resolve_component_slices(
        component_name=component_name,
        component_meta=component_meta,
        slices=slices,
    )

    populate_default_images(
        component_name=component_name,
        component_meta=component_meta,
        component_k8s=component_k8s,
    )

    # add namespace
    component_k8s.namespace = f"{component_meta.implementation}-{component_meta.category}"

    # add corresponding labels
    label_base = "node-type.5g.blueprint"

    selector = dict(component_k8s.node_selector or {})
    selector[f"{label_base}/{component_meta.category}"] = "true"

    if component_k8s.force_type_scheduling:
        selector[f"{label_base}/{component_meta.type}"] = "true"

    component_k8s.node_selector = selector

    # add exposed interfaces (used only to document k8s pod for now but might be useful later)
    for iface in EXPOSED_COMPONENT_INTERFACES.get(component_meta.category, []):
        if hasattr(component_meta.config, iface) and getattr(component_meta.config, iface) is not None: # some might be None
            iface_meta: TransportEndpoint = getattr(component_meta.config, iface)
            component_k8s.exposed_ports.setdefault(iface, ExposedPort(port=iface_meta.port, protocol=iface_meta.protocol))

    # add necessary priveleges if defined
    if component_k8s.security_context is None:
        # not defined => stays at None
        component_k8s.security_context = POD_PRIVELEGES.get(component_meta.category, {}
                                                            ).get(component_meta.implementation, {}
                                                                  ).get(component_meta.type)


def get_5g_components_by_type(
        components: dict[str, Component5G]
    ) -> dict[CoreComponentType | RANComponentType | UEType | RICType, dict[str, Component5G]]:
    """Get 5G components (core, ran, ues, rics) by their type."""

    groups = defaultdict(dict)
    for c_name, c_data  in components.items():
        groups[c_data.type][c_name] = c_data

    return groups


type ComponentDependencyGraph = dict[CoreComponentType | RANComponentType, frozenset[CoreComponentType | RANComponentType]]


def resolve_component_dependency_levels(
    components: dict[str, Component5G],
    dependencies: ComponentDependencyGraph | None = None,
    ) -> list[list[str]]:
    """
    Resolve component instances into dependency execution levels.

    Every instance of a component type depends on every instance of each dependency type.
    (e.g. components/instances 'upf1' and 'upf2' of type UPF depend on 'smf3', 'smf4' and 'smf5' of type SMF)

    Components within the same level can be actioned-on concurrently while levels are actioned sequentially.
    """

    if not components:
        return []

    if dependencies is None:
        # no dependencies
        return [list(components)] # all components in one single level

    
    available_types = {component.type for component in components.values()}

    remaining = dict(components) # components still to be resolved (be grouped in an execution level)
    completed_types: set[CoreComponentType | RANComponentType] = set() # resolved types 
    levels: list[list[str]] = [] # levels / groups of independent components in order

    while remaining:
        # components that have resolved dependencies
        # => the components of the types they depend on (if any) were already handeled in the previous levels and are considered as completed
        ready = {
            name: component for name, component in remaining.items()
            if (dependencies.get(component.type, frozenset()) & available_types) <= completed_types
        }
        # a dependency is enforced only when at least one instance of that dependency type is present in the given components

        if not ready: # we cannot proceed
            unresolved = ", ".join(remaining)
            raise ValueError(f"Dependency cycle or unresolved dependency for: {unresolved}.")

        # add ready components to execution level
        levels.append(list(ready))

        remaining = {
            name: component for name, component in remaining.items()
            if name not in ready
        }

        # resolved component types
        completed_types.update(component.type for component in ready.values())

    return levels
