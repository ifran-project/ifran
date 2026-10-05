"""Kubernetes models."""

import re
from enum import StrEnum, auto
from ipaddress import IPv4Network
from pathlib import Path
from typing import Any, Literal, Self

from metamodel.models.base import StrictBaseModel
from pydantic import (
    Field,
    IPvAnyAddress,
    IPvAnyNetwork,
    model_validator,
)


class K8SStatus(StrEnum):
    """Supported node Kubernetes status values."""

    NOT_CONFIGURED = auto()
    """Kubernetes is not configured on node."""

    CONFIGURED = auto()
    """Kubernetes is configured on node (necessary packages are present)."""

    IN_CLUSTER = auto()
    """Kubernetes is configured on node and node is part of a cluster."""


SEM_VER_PATTERN = r"^(?P<major>\d+)\.(?P<minor>\d+)(?:\.(?P<patch>\d+))?(?:-(?P<extension>.+))?$"

class Version(StrictBaseModel):
    """Conventional semantic version."""

    major: int = Field()
    """Major version."""

    minor: int = Field()
    """Minor version."""

    patch: int = Field()
    """Patch version."""

    extension: str | None = Field(default=None)
    """Version extension (anything after -)."""


    @model_validator(mode="before")
    @classmethod
    def parse_string_or_dict(cls, data) -> dict[str, Any] | Any:
        """Parse version string directly into initialisation dict before validation."""

        if isinstance(data, str):
            match = re.match(SEM_VER_PATTERN, data.strip())
            if not match:
                raise ValueError(f"Invalid version string {data!r}. Expected format: 'X.Y.Z' or 'X.Y.Z-extension'")

            data = match.groupdict()
            return {
                "major": int(data["major"]),
                "minor": int(data["minor"]),
                "patch": int(data["patch"]) if data["patch"] is not None else 0,
                "extension": data["extension"],
            }

        return data


class K8SParams(StrictBaseModel):
    """Kubernetes global parameters."""

    timezone: str = Field(default="Europe/Paris")
    """Timezone set across Kubernetes nodes."""

    k8s_version: Version = Field(default=Version(major=1, minor=36, patch=2, extension="2.1"))
    """Kubernetes version (the extension part is needed only for kubectl/kubeadm/kubelet packages)."""

    cluster_name: str = Field(default="5gbp")
    """Kubernetes cluster name."""

    master_node: str | None = Field(default=None)
    """Node that will act as the Kubernetes cluster master."""

    join_command: str | None = Field(default=None)
    """Kubernetes command to join workers to cluster."""

    pod_network_cidr: IPvAnyNetwork = Field(default=IPv4Network("10.244.0.0/16"))
    """Kubernetes pod network CIDR."""

    service_cidr: IPvAnyNetwork = Field(default=IPv4Network("10.96.0.0/12"))
    """Kubernetes service CIDR."""

    calico_version: str = Field(default="3.32.1", pattern=SEM_VER_PATTERN)
    """Calico CNI version."""

    # NOTE leave install_multus=False as default to avoid possible OOMKilled error
    # whene many pods are created in parallel. See this related issue:
    # https://github.com/k8snetworkplumbingwg/multus-cni/issues/1346
    install_multus: bool = Field(default=False)
    """If True, Multus CNI will be deployed on the cluster."""

    multus_version: str = Field(default="4.3.0")
    """Multus CNI version to be deployed if 'install_multus' is True."""

    helm_version: str = Field(default="4.2.3", pattern=SEM_VER_PATTERN)
    """Helm version."""

    k9s_install: bool = Field(default=True)
    """If True, K9S will be installed."""

    k9s_version: str = Field(default="0.51.0", pattern=SEM_VER_PATTERN)
    """k9S version."""

    containerd_snapshotter: str | None = Field(default=None)
    """Containerd snapshotter. If None, overlayfs is used by default or native on overlay/live nodes."""

    enable_cni_dhcp: bool = Field(default=True)
    """If True, CNI DHCP service will be installed."""

    copy_kubeconfig_to_workers: bool = Field(default=True)
    """If True, cluster admin credentials will be shared over all workers."""

    local_kubeconfig_path: str = Field(default=str(Path(__file__).resolve().parents[3] / ".k8s-admin.conf"))
    """
    Local path on Ansible controller where master's admin.conf is temporarily saved
    before distribution over workers if 'copy_kubeconfig_to_workers' is True.
    """

    label_selection_base: str = Field(default="node-type.5g.blueprint")
    """Label base used to enforce scheduling on nodes based on their roles."""

    used_ips: set[IPvAnyAddress] = Field(default_factory=set)
    """Set of IPs explicitly assigned to pods."""


    @model_validator(mode="after")
    def validate_k8s_version(self) -> Self:
        """Ensure Kubernetes version has extension needed to install packages."""

        if not self.k8s_version.extension:
            raise ValueError("k8s_version extension is required for kubectl/kubeadm/kubelet packages")
        return self


class HelmParams(StrictBaseModel):
    """Parameters for prepare/install/uninstall Helm ansible role."""

    chart_name: str = Field()
    """Helm chart name."""

    helm_build_dir: str = Field()
    """Directory where the chart will be built/rendered before install."""

    clean_helm_build_dir: bool = Field(default=False)
    """If True, 'helm_build_dir' will be cleaned after chart is installed."""

    output_with_multus: bool = Field(default=False)
    """If True, install role will output list of MultusNetworkStatus, else output pod IP string."""


class ImagePullSecret(StrictBaseModel):
    """Kubernetes image pull secret."""

    name: str = Field()
    """Name of the image pull secret."""


class ContainerImage(StrictBaseModel):
    """Container image."""

    repository: str = Field()
    """Container image name for the component."""

    image_tag: str = Field(default="latest")
    "Container image tag or version."

    image_pull_policy: Literal["IfNotPresent", "Always", "Never"] = Field(default="IfNotPresent")
    """Container image pull policy."""

    image_pull_secrets: list[ImagePullSecret] | None = Field(default=None)
    """List of Kubernetes image pull secrets."""


class ComputeResources(StrictBaseModel):
    """CPU and memory resources for a container."""

    cpu: str | int | float | None = Field(default=None)
    """CPU resource value (e.g. 1500m)."""

    memory: str | int | float | None = Field(default=None)
    """Memory resource value (e.g. 1Gi)."""


class ContainerResources(StrictBaseModel):
    """Resources assigned to a specific container."""

    nf: ComputeResources | None = Field(default=None)
    """Main network function container resources."""

    tcpdump: ComputeResources | None = Field(default=None)
    """Tcpdump sidecar resources."""


class ResourceRequirements(StrictBaseModel):
    """Pod/container resource requirements."""

    define: bool = Field(default=False)
    """Whether resource constraints are explicitly defined."""

    requests: ContainerResources | None = Field(default=None)
    """Requested compute resources."""

    limits: ContainerResources | None = Field(default=None)
    """Maximum compute resources."""


class MultusInterface(StrictBaseModel):
    """Multus network attachment configuration."""

    enabled: bool = Field(default=True)
    """Whether this network attachment is enabled."""

    name: str = Field()
    """Name of the interface inside the pod."""

    network: str | None = Field(default=None)
    """Name of the Multus NetworkAttachmentDefinition."""

    namespace: str | None = Field(default=None)
    """Namespace containing the NetworkAttachmentDefinition."""

    type: Literal["macvlan", "ipvlan", "bridge", "sriov"] = Field(default="macvlan")
    """Underlying CNI network type."""

    mode: str = Field(default="bridge")
    """Network mode (implementation dependent)."""

    host_interface: str = Field(default="eth0")
    """Host network interface used by the CNI plugin."""

    ip_address: IPvAnyAddress | None = Field(default=None)
    """Static IP address assigned to the interface."""

    netmask: int = Field(default=24, ge=0, le=128)
    """Network prefix length."""

    gateway: IPvAnyAddress | None = Field(default=None)
    """Default gateway for this interface."""

    default_route: bool = Field(default=False)
    """Whether this interface provides the pod default route."""

    dns_servers: list[IPvAnyAddress] = Field(default_factory=list)
    """DNS servers reachable through this interface."""

    mtu: int | None = Field(default=None, ge=576)
    """Maximum Transmission Unit (MTU)."""


class Multus(StrictBaseModel):
    """Multus CNI configuration."""

    enabled: bool = Field(default=False)
    """Enable Multus networking."""

    interfaces: list[MultusInterface] = Field(default_factory=list)
    """Secondary network interfaces attached to the pod."""


class MultusNetworkStatus(StrictBaseModel):
    """One entry of the Multus network-status annotation (k8s.v1.cni.cncf.io/network-status)."""

    name: str = Field()
    """Network name."""

    interface: str = Field()
    """Interface name inside the pod."""

    ips: list[IPvAnyAddress] = Field(default_factory=list)
    """List of IP addresses assigned to the interface."""

    mac: str | None = None
    """MAC address of the interface."""

    default: bool = False
    """Whether this interface provides the pod default route."""

    dns: dict[str, Any] = Field(default_factory=dict)
    """DNS configuration for this interface."""

    gateway: list[IPvAnyAddress] = Field(default_factory=list)
    """List of default gateways for this interface."""


class PodSecurityContext(StrictBaseModel):
    """Kubernetes pod-level security context."""

    run_as_user: int = Field(default=0, ge=0)
    """Default UID for all containers in the pod."""

    run_as_group: int = Field(default=0, ge=0)
    """Default GID for all containers in the pod."""

    run_as_non_root: bool = Field(default=False)
    """Require containers to run as a non-root user."""

    fs_group: int | None = Field(default=None, ge=0)
    """Filesystem group applied to mounted volumes."""


class Capabilities(StrictBaseModel):
    """Linux capability configuration."""

    add: list[str] = Field(default_factory=list)
    """Capabilities to add."""

    drop: list[str] = Field(default_factory=list)
    """Capabilities to drop."""


class SecurityContext(StrictBaseModel):
    """Kubernetes container security context."""

    privileged: bool = Field(default=True)
    """Run the container in privileged mode."""

    capabilities: Capabilities = Field(default_factory=Capabilities)
    """Linux capabilities to add or drop."""


class ExposedPort(StrictBaseModel):
    """Kubernetes container exposed port."""

    port: int = Field()
    """Exposed port number."""

    protocol: str | None = Field(default=None)
    """Protocol going through exposed port."""


class LogFetchParams(StrictBaseModel):
    """Kubernetes log fetching parameters."""

    kind: Literal["Pod", "Deployment", "StatefulSet"] = Field(default="Deployment")
    """Kubernetes workload kind for which to retrieve logs."""

    since_seconds: int = Field(default=3600) # last hour
    """Time in seconds before the current time from which to show logs."""

    all_containers: bool = Field(default=False)
    """If set to True, retrieve all containers' logs in the pod(s)."""


class K8SComponent(StrictBaseModel):
    """Generic Kubernetes component."""

    is_installed: bool = Field(default=False)
    """If this component is installed or not."""

    static_pod_ip: IPvAnyAddress | None = Field(default=None)
    """Optional static primary pod IP address set with Calico."""

    network_info: IPvAnyAddress | list[MultusNetworkStatus] | None = Field(default=None)
    """
    Component pod network information (populated only after installation).
    - Can be either the IP of the pod if Multus was not used,
    - or a list of Multus network status otherwise.
    """

    force_type_scheduling: bool = Field(default=False)
    """If True, label will be added to ensure scheduling only on nodes with matching type AND category label."""

    image: ContainerImage | None = Field(default=None)
    """Pod main container image."""

    exposed_ports: dict[str, ExposedPort] = Field(default_factory=dict)
    """Exposed ports."""

    resources: ResourceRequirements = Field(default_factory=ResourceRequirements)
    """CPU and memory resource requirements."""

    # populated later on if none
    namespace: str | None = Field(default=None)
    """
    Kubernetes namespace where the component will be deployed.
    If None, '<implementation>-<type>' is used by default.
    """

    pod_security_context: PodSecurityContext = Field(default_factory=PodSecurityContext)
    """Pod-level security context."""

    security_context: SecurityContext | None = Field(default=None)
    """Container security context."""

    node_name: str | None = Field(default=None)
    """Pin workload to a specific node."""

    node_selector: dict[str, str] | None = Field(default=None)
    """Node selection labels."""

    affinity: dict[str, Any] | None = Field(default=None)
    """Kubernetes affinity rules."""

    tolerations: list[dict[str, Any]] = Field(default_factory=list)
    """Node taints tolerations."""

    multus: Multus = Field(default_factory=Multus)
    """Multus secondary network configuration."""

    labels: dict[str, str] = Field(default_factory=dict)
    """Kubernetes pod labels."""

    annotations: dict[str, str] = Field(default_factory=dict)
    """Kubernetes pod annotations."""

    liveness_probe: bool = Field(default=True)
    """Liveness health check."""

    readiness_probe: bool = Field(default=True)
    """Readiness health check."""

    start: bool = Field(default=True)
    """If False, container sleeps."""

    include_tcp_dump_container: bool = Field(default=False)
    """Add a tcpdump sidecar container."""

    tcp_dump_image: ContainerImage | None = Field(default_factory=lambda: ContainerImage(
        repository="docker.io/oaisoftwarealliance/oai-tcpdump-init",
        image_tag="alpine-3.20",
        ))
    """TCP dump sidecar image."""

    tcp_dump_share_volume: bool = Field(default=False)
    """If True, TCP dump will use a shared volume."""

    rendered_files: list[str] = Field(default_factory=lambda: ["values.yaml", "config.yaml"])
    """List of Helm chart template files to be rendered."""

    log_fetch_params: LogFetchParams = Field(default_factory=LogFetchParams)
    """Kubernetes log fetching parameters for this component."""

    logs: str | None = Field(default=None)
    """Where the latest fetched logs for this component are stored."""


    @model_validator(mode="after")
    def ensure_network_info(self) -> Self:
        """Ensure installed component has network info."""

        if self.is_installed and self.network_info is None:
            raise ValueError("Component is installed but has no 'network_info'.")
        return self
