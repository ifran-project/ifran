"""Common 5G utilities and helpers."""

from collections import defaultdict
from typing import Any

from orchestrator.models.deployment.k8s import (
    ExposedPort,
    K8SComponent,
)
from orchestrator.models.meta.common import (
    EXPOSED_COMPONENT_INTERFACES,
    Category5G,
    Component5G,
    TransportEndpoint,
)
from orchestrator.models.meta.core import (
    Core,
    CoreComponent,
    CoreComponentConfig,
    CoreComponentType,
    PLMNSupportItem,
)
from orchestrator.models.meta.ran import (
    RAN,
    RANComponent,
    RANComponentConfig,
    RANComponentType,
)
from orchestrator.models.meta.ru import RU, RUType
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE
from orchestrator.utils.common import (
    InvalidResourceStateError,
    ReferenceNotFounError,
)
from orchestrator.utils.defaults import (
    DEFAULT_CORE_IMAGES,
    DEFAULT_RAN_IMAGES,
    POD_PRIVELEGES,
)


def resolve_component_reference(
        component_name: str,
        component_meta: RANComponent,
        ref_attribute: str,
        registry: dict[str, Any],
        ready_attribute: str | None = None,
        value_attribute: str | None = None,
        ):
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
        raise ReferenceNotFounError(f"{component_meta.category.value.capitalize()} component {component_name!r} "
                                    f"refrences undefined {ref_attribute.upper()} {reference!r}.")

    # optionally verify that the referenced target is ready via 'ready_attribute' if it is True
    if ready_attribute and not getattr(target, ready_attribute):
        raise InvalidResourceStateError(f"{reference!r} referenced by {component_meta.category.value} component "
                                        f"{component_name!r} is not ready ({ready_attribute}=False).")

    # replace the string reference with the target's 'value_attribute' or the target itself if value_attribute is None
    value = target if value_attribute is None else getattr(target, value_attribute)
    setattr(component_meta.config, ref_attribute, value)


def resolve_snssai_list(
        component_name: str,
        component_meta: CoreComponent | RANComponent,
        slices: dict[str, Slice],
        config: CoreComponentConfig | RANComponentConfig | PLMNSupportItem | None = None,
        ):
    """Resolve slices references by name in 'snssai_list' field of 5G components."""

    if config is None:
        config = component_meta.config
    if hasattr(config, "snssaiList"):
        snssai_list: list[Slice | str] = config.snssaiList
        for i in range(len(snssai_list)):
            slice_name = snssai_list[i]
            if isinstance(slice_name, str):
                if slices.get(slice_name):
                    config.snssaiList[i] = slices[slice_name]
                else:
                    raise ReferenceNotFounError(f"{component_meta.category.value.capitalize()} component "
                                                f"{component_name!r} refrences undefined slice {slice_name!r} in 'snssaiList'.")


def resolve_plmn_list(        
        component_name: str,
        component_meta: CoreComponent | RANComponent,
        slices: dict[str, Slice],
        ):
    """Resolve slices references by name in 'plmn_list' field of 5G components."""

    config = component_meta.config
    if hasattr(config, "plmnList"):
        plmn_list: list[PLMNSupportItem] = config.plmnList
        for plmn_item in plmn_list:
            resolve_snssai_list(
                component_name=component_name,
                component_meta=component_meta,
                slices=slices,
                config=plmn_item,
            )


def resolve_component_slices(        
        component_name: str,
        component_meta: CoreComponent | RANComponent,
        slices: dict[str, Slice],
        ):
    """Resolve slice references in 5G components."""

    args = {"component_name": component_name, "component_meta": component_meta, "slices": slices}
    resolve_snssai_list(**args)
    resolve_plmn_list(**args)


def populate_default_images(
        component_name: str,
        component_meta: Component5G,
        component_k8s: K8SComponent,
    ):
    """Populate 5G component image from default images."""

    # if not implementation is defined raise an error
    if component_meta.implementation is None:
        raise ValueError(
            f"{component_meta.category.value.capitalize()} component {component_name!r} "
            f"has no defined {component_meta.category.value} implementation."
        )

    if (
        component_meta.category is Category5G.CORE and
        component_k8s.image is None and
        DEFAULT_CORE_IMAGES.get(component_meta.implementation)
        ):
            component_k8s.image = DEFAULT_CORE_IMAGES.get(component_meta.implementation, {}
                                                          ).get(component_meta.type)


    if component_meta.category is Category5G.RAN:
        # for RAN components, RU is supposed to be resolved before this
        # NOTE CUs, CU-CPs and CU-UPs dont have and ru field, so give them simulated one instead
        config = component_meta.config
        if hasattr(config, "ru") and isinstance(config.ru, RU):
            ru_type = config.ru.type
        else:
            ru_type = RUType.SIMULATED

            component_k8s.image = DEFAULT_RAN_IMAGES.get(component_meta.implementation, {}
                                                         ).get(ru_type, {}).get(component_meta.type)

    # if not default image is available, it stays None but is required
    if component_k8s.image is None:
        raise ValueError(f"{component_meta.category.value.capitalize()} component {component_name!r} has no container image.")


def reconcile_5g_component(
        component_name: str,
        component_meta: Component5G,
        component_k8s: K8SComponent,
        slices: dict[str, Slice],
    ):
    """Ensure the 5G component Kubernetes deployment model is ready for deployment."""

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

    # add exposed interfaces (unecessary for now but might be useful later)
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


def resolve_ue_slices_dnns(
        ue_name: str,
        ue_meta: UE,
        slices: dict[str, Slice],
        ):
    """Resolve UE slices and DNNs."""

    ue_config = ue_meta.config
    for subscription in ue_config.subscriptions:
        if isinstance(subscription.snssai, str):
            subscription_slice = slices.get(subscription.snssai)
            if subscription_slice is None:
                raise ReferenceNotFounError(f"UE {ue_name!r} references undefined slice {subscription.slice!r}.")

            subscription.snssai = subscription_slice

        if isinstance(subscription.dnn, str):
            subscription_dnn = subscription.snssai.dnns.get(subscription.dnn)
            if subscription_dnn is None:
                raise ReferenceNotFounError(f"UE {ue_name!r} references undefined DNN {subscription.dnn!r}.")

            subscription.dnn = subscription_dnn


def get_5g_components_by_type(network5g: Core | RAN) -> dict[CoreComponentType | RANComponentType, dict[str, CoreComponent | RANComponent]]:
    """Get 5G components by their type from core or ran."""

    groups = defaultdict(dict)
    for c_name, c_data  in network5g.components.items():
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
