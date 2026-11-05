"""Common 5G utilities and helpers."""

from collections import defaultdict
from ipaddress import IPv4Address
from typing import Any

from metamodel.models.common import (
    Category5G,
    Component5G,
    TransportEndpoint,
)
from metamodel.models.core import (
    CoreComponentType,
)
from metamodel.models.ran import RANComponentType
from metamodel.models.ric import RICComponentType
from metamodel.models.ru import RU, RUType
from metamodel.models.slice import Slice
from metamodel.models.ue import UEType

from orchestrator.models.common import (
    ComponentDependencyGraph,
    ComponentType,
    Deployed5GComponent,
)
from orchestrator.models.k8s import (
    ExposedPort,
    K8SParams,
)
from orchestrator.models.provisioning import MergedRU, ProvisionableRU
from orchestrator.utils.defaults import (
    DEFAULT_POD_IMAGES,
    POD_PRIVILEGES,
)
from orchestrator.utils.k8s import (
    build_k8s_safe,
    generate_random_ip,
)
from orchestrator.utils.utils import (
    InvalidResourceStateError,
    ReferenceNotFoundError,
)

EXPOSED_CORE_INTERFACES = ["sbi", "n2", "n3", "n4", "n9"]
EXPOSED_RAN_INTERFACES = ["e1", "e2", "f1c", "f1u", "n2", "n3"]
EXPOSED_RIC_INTERFACES = ["e2"]

EXPOSED_COMPONENT_INTERFACES = {
    Category5G.CORE: EXPOSED_CORE_INTERFACES,
    Category5G.RAN: EXPOSED_RAN_INTERFACES,
    Category5G.RIC: EXPOSED_RIC_INTERFACES,
}

# component types that require a static pod ip for configuration purposes
STATIC_POD_IP_TYPES = [
    # upf ip (assigned to n4) needs to be known by the smf before deployment (open5gs + free5gc)
    CoreComponentType.UPF,
    # cu_cp, cu_up and cu components reference each other and are reference by du
    RANComponentType.CU_CP, RANComponentType.CU_UP, RANComponentType.CU,
    # cu_up, cu and gnb ip (assigned to n3) needs to be known before deployment => advertised to core from config (oai)
    # gnb and du need a static ip given to simulated ues to reach it
    RANComponentType.DU, RANComponentType.GNB,
]

# uniion type
type Type5G = CoreComponentType | RANComponentType | RICComponentType | UEType

def get_5g_components_by_type(
        components: dict[str, Component5G],
        filter: list[Type5G] | None = None,
    ) -> dict[Type5G, dict[str, Component5G]]:
    """Get 5G components (core, ran, ric, ues) by their type."""

    groups = defaultdict(dict)
    for c_name, c_data  in components.items():
        groups[c_data.type][c_name] = c_data

    # filter by types if given
    if filter:
        filtered = {}

        for type in filter:
            filtered = filtered | groups.get(type, {})

        return filtered

    # else return all type groups
    return groups


def get_nested_attribute(object: Any, attribute: str) -> Any:
    """Get a nested attribute's value from a given object."""

    for part in attribute.split("."):
        object = getattr(object, part)

    return object


def resolve_component_reference(  # noqa: PLR0917
        component_name: str,
        component_meta: Component5G,
        ref_attribute: str,
        registry: dict[str, Any],
        ready_attribute: str | None = None,
        value_attribute: str | None = None,
    ) -> None:
    """
    Resolve a single string reference in a 5G component config.

    - 'ref_attribute' contains a reference name and is looked up in 'registry'
    - The reference is replaced with either the target object or the value of its 'value_attribute'
    - 'value_attribute' can be a nested attribute (e.g. config.n2.ipv4EndPointAddress)
    - Optionally, 'ready_attribute' can be used to require the referenced target to be ready before resolving the ref
    - Missing or invalid references raise a 'ReferenceNotFoundError' exception
    - Already-resolved values and missing attributes are left unchanged
    """

    # skip if component doesn't have 'ref_attribute' or is None
    if not hasattr(component_meta.config, ref_attribute) or getattr(component_meta.config, ref_attribute) is None:
        return

    reference = getattr(component_meta.config, ref_attribute)
    if not isinstance(reference, str): # reference already resolved
        return

    # get actual referenced target with 'ref_attribute' from the 'registry' if it exists
    target = registry.get(reference)

    if target is None:
        raise ReferenceNotFoundError(f"{component_meta.category.value.upper()} component {component_name!r} "
                                    f"references undefined {ref_attribute!r} {reference!r}.")

    # optionally verify that the referenced target is ready via 'ready_attribute' if it is True
    if ready_attribute and not getattr(target, ready_attribute):
        raise InvalidResourceStateError(f"{reference!r} referenced by {component_meta.category.value} component "
                                        f"{component_name!r} is not ready ({ready_attribute}=False).")

    # replace the string reference with the target's 'value_attribute' or the target itself if 'value_attribute' is None
    value = target if value_attribute is None else get_nested_attribute(target, value_attribute)
    setattr(component_meta.config, ref_attribute, value)


def resolve_snssai_reference(
        component_name: str,
        component_meta: Component5G,
        reference: str,
        slices: dict[str, Slice],
        field_name: str,
    ) -> Slice:
    """Resolve a single slice reference."""

    if reference in slices:
        return slices[reference]

    raise ReferenceNotFoundError(
        f"{component_meta.category.value.upper()} component {component_name!r} references undefined slice {reference!r}"
        f" in {field_name!r}."
    )


def resolve_snssai_list(
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
        config: Any | None = None,
    ) -> None:
    """
    Resolve slice references in an 'snssaiList' field.

    The 'snssaiList' field in question is resolved in the given config.
    By default, the config is the 5G component's main config.
    """

    config = config or component_meta.config

    if hasattr(config, "snssaiList"):
        snssai_list: list[str] = config.snssaiList # type: ignore

        for i, snssai in enumerate(snssai_list):
            config.snssaiList[i] = resolve_snssai_reference( # type: ignore
                component_name=component_name,
                component_meta=component_meta,
                reference=snssai,
                slices=slices,
                field_name="snssaiList",
            )


def resolve_plmn_list(
        component_name: str,
        component_meta: Component5G,
        slices: dict[str, Slice],
    ) -> None:
    """Resolve slices references in 'plmnList' field of 5G components."""

    config = component_meta.config

    for plmn_item in config.plmnList: # type: ignore
        resolve_snssai_list(
            component_name=component_name,
            component_meta=component_meta,
            slices=slices,
            config=plmn_item,
        )


def resolve_ru_reference(
        component_name: str,
        component_meta: Component5G,
        rus_meta: dict[str, RU],
        rus_provisioning: dict[str, ProvisionableRU],
        check_is_porvisioned: bool = True,
    ) -> None:
    """Resolve RU name reference in a 5G component."""

    # merge rus (we need the meta for ran config parameters and provisioning for readiness state and IPs)
    rus: dict[str, RU | MergedRU] = {}
    for ru_name, ru_meta in rus_meta.items():
        if ru_meta.type is RUType.SIMULATED:
            # simulated rus are not part of deployment model
            rus[ru_name] = ru_meta
            check_is_porvisioned = False # simulated rus are not provisionable
        else:
            # ru_meta and rus_provisioning are supposed to be synchronized by this point
            ru_prov = rus_provisioning[ru_name].model_dump(mode="json")
            rus[ru_name] = MergedRU.model_validate({
                **ru_prov, **ru_meta.model_dump(mode="json")
                })

    resolve_component_reference(
        component_name=component_name,
        component_meta=component_meta,
        ref_attribute="ru",
        registry=rus,
        ready_attribute="is_provisioned" if check_is_porvisioned else None,
    )


# NOTE all deployed 5g components are supposed to have a defined implementation
def populate_default_images(
        component_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """Populate 5G component image from default images."""

    # look for default image if not image was explicitly given
    if component_deployment.image is None:
        if component_meta.category is Category5G.RAN:
            # for RAN components, RU is supposed to be resolved before this
            ru_vendor = component_meta.config.model_dump(serialize_as_any=True).get("ru", {}).get("vendor") # type: ignore

            component_deployment.image = DEFAULT_POD_IMAGES.get(component_meta.category, {}
                                                            ).get(component_deployment.implementation, {}
                                                                ).get(ru_vendor, {}
                                                                        ).get(component_meta.type)
        else:
            component_deployment.image = DEFAULT_POD_IMAGES.get(component_meta.category, {}
                                                        ).get(component_deployment.implementation, {}
                                                            ).get(component_meta.type)


    # if not default image is available, it stays None but is required => raise ValueError
    if component_deployment.image is None:
        raise ValueError(
            f"{component_meta.category.value.upper()} component "
            f"{component_name!r} has no container image."
        )


def add_node_selection_labels(
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
        k8s_params: K8SParams,
    ) -> None:
    """Add node selection labels for component scheduling on Kubernetes cluster."""

    selector = dict(component_deployment.node_selector or {})

    # add category-based label
    selector[f"{k8s_params.label_selection_base}/{component_meta.category}"] = "true"

    # add type-based label
    if component_deployment.force_type_scheduling:
        selector[f"{k8s_params.label_selection_base}/{component_meta.type}"] = "true"

    component_deployment.node_selector = selector


# NOTE this should not be used on undeployed components, otherwise the interface's endpoint will be ovewirtten to None
def populate_iface_for_deployed(
        iface_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """Populate component interface endpoint for a deployed 5G component from its network info."""

    iface_meta: TransportEndpoint = getattr(component_meta.config, iface_name)

    # multus case => list if multus interfaces
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


def populate_iface_for_undeployed(
        iface_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """Populate component interface endpoint for undeployed 5G component from its static IPs."""

    iface_meta: TransportEndpoint = getattr(component_meta.config, iface_name)

    # use static pod ip (can be undefined)
    iface_meta.ipv4EndPointAddress = component_deployment.static_pod_ip or iface_meta.ipv4EndPointAddress

    # multus case => takes precedence over simple static pod ip
    if component_deployment.multus.enabled:
        # look for interface ip with same name
        for multus_iface in component_deployment.multus.interfaces:
            if multus_iface.name == iface_name:
                # multus interface holding the same name can still have an undefined static ip
                iface_meta.ipv4EndPointAddress = multus_iface.ip_address or iface_meta.ipv4EndPointAddress
                break


def populate_iface(
        iface_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """
    Populate component interface endpoint for a 5G component if not explicitly set.

    The interface endpoint is populated from the component's network info if it has one,
    meaning it is deployed, otherwise, its static IPs are used when it is not yet deployed.
    If no defined IP was found, the existing default value (0.0.0.0) is kept.
    """

    iface_meta: TransportEndpoint = getattr(component_meta.config, iface_name)

    # populate interface ip if not explicitly set
    if iface_meta.ipv4EndPointAddress == IPv4Address("0.0.0.0"):

        # if component is already deployed
        if component_deployment.network_info:
            populate_iface_for_deployed(
                iface_name=iface_name,
                component_meta=component_meta,
                component_deployment=component_deployment,
            )

        # component hasn't been deployed yet => look for predefined static ips
        else:
            populate_iface_for_undeployed(
                iface_name=iface_name,
                component_meta=component_meta,
                component_deployment=component_deployment,
            )


def populate_exposed_endpoints(
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
    ) -> None:
    """Populate the 5G components's exposed interface endpoints with relevant IPs and add it to for Kubernetes."""

    for iface_name in EXPOSED_COMPONENT_INTERFACES.get(component_meta.category, []):

        # some interfaces can be None
        if hasattr(component_meta.config, iface_name) and getattr(component_meta.config, iface_name) is not None:
            iface_meta: TransportEndpoint = getattr(component_meta.config, iface_name)

            # mark interface port as exposed in k8s
            component_deployment.exposed_ports.setdefault(
                iface_name,
                ExposedPort(port=iface_meta.port, protocol=iface_meta.protocol)
            )

            # populate interface ip
            populate_iface(
                iface_name=iface_name,
                component_meta=component_meta,
                component_deployment=component_deployment,
            )


def reconcile_5g_component(
        component_name: str,
        component_meta: Component5G,
        component_deployment: Deployed5GComponent,
        k8s_params: K8SParams,
    ) -> None:
    """
    Ensure the 5G component Kubernetes deployment model is ready for deployment.

    - Populate component image from known defaults (based on implementation and type + ru type if it's a RAN component)
    - Add namespace if missing
    - Add node selection labels
    - Add pod privileges if defined
    - Assign static pod IP to components that require it for configuration purposes
    - Populate component's exposed interfaces with static IPs if given
    """

    # populate component image
    populate_default_images(
        component_name=component_name,
        component_meta=component_meta,
        component_deployment=component_deployment,
    )

    # add namespace
    component_deployment.namespace = (
        component_deployment.namespace or
        build_k8s_safe(f"{component_deployment.implementation}-{component_meta.category}")
    )

    # add node selection labels
    add_node_selection_labels(
        component_meta=component_meta,
        component_deployment=component_deployment,
        k8s_params=k8s_params,
    )

    # add necessary privileges if defined
    if component_deployment.security_context is None:
        # not defined => stays None
        component_deployment.security_context = POD_PRIVILEGES.get(component_meta.category, {}
                                                             ).get(component_deployment.implementation, {}
                                                             ).get(component_meta.type)

    # assign static pod ip when needed
    if component_meta.type in STATIC_POD_IP_TYPES:
        component_deployment.static_pod_ip = component_deployment.static_pod_ip or generate_random_ip(k8s_params)

    # populate exposed interfaces
    populate_exposed_endpoints(
        component_meta=component_meta,
        component_deployment=component_deployment,
    )


def reconcile_5g_components(
        components_meta: dict[str, Component5G],
        components_deployment: dict[str, Deployed5GComponent],
        k8s_params: K8SParams,
    ) -> None:
    """Run 'reconcile_5g_component' on all provided components."""

    for component_name, component_meta in components_meta.items():
        reconcile_5g_component(
            component_name=component_name,
            component_meta=component_meta,
            component_deployment=components_deployment[component_name],
            k8s_params=k8s_params,
        )


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
    completed_types: set[ComponentType] = set() # resolved types
    levels: list[list[str]] = [] # levels / groups of independent components in order

    while remaining:
        # components that have resolved dependencies
        # => the components of the types they depend on (if any)
        # were already handled in the previous levels and are considered as completed
        ready = {
            name: component for name, component in remaining.items()
            if (dependencies.get(component.type, frozenset()) & available_types) <= completed_types # type: ignore
        }
        # a dependency is enforced only when at least one instance of that dependency type
        # is present in the given components

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
        completed_types.update(component.type for component in ready.values()) # type: ignore

    return levels
