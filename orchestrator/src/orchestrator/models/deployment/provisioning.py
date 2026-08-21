"""Provisioning models."""

from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from orchestrator.models.common import (
    BlueprintBaseModel,
    BlueprintTolerantBaseModel,
)
from orchestrator.models.deployment.k8s import K8SStatus
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType
from orchestrator.models.meta.ran import RANComponentType


class SSHInfo(BlueprintBaseModel):
    """SSH information about a host."""

    hostname: str | None = Field(default=None)
    """Hostname or IP address."""

    port: int = Field(default=22)
    """SSH port."""

    user: str = Field(default="root")
    """SSH username."""

    private_key_file: str | None = Field(default=None)
    """Path to SSH private key."""

    password: str | None = Field(default=None)
    """SSH password."""

    sudo_password: str | None = Field(default=None)
    """SSH sudo password."""

    extra_args: str | None = Field(default=None)
    """Additional SSH arguments."""

    jumphost: Self | None = Field(default=None)
    """Direct jump host to reach this target."""

    no_host_key_checking: bool = Field(default=True)
    """If True, flags will be added to disable host key checkin."""

    # auto generated
    common_args: str | None = Field(default=None)
    """Auto-generated SSH flags."""


    def _build_proxy_command(self) -> str | None:
        """Recursively build nested SSH ProxyCommand string for jump hosts."""

        if not self.jumphost:
            return None
        jump = self.jumphost

        # build command to reach target with jump host and disable host key checking and known hosts file if desired
        opts = []
        if jump.no_host_key_checking:
            opts.append("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null")
        if jump.extra_args:
            opts.append(jump.extra_args)

        jump_opts = f"{' '.join(opts)} " if opts else ""
        proxy_cmd = f"ssh {jump_opts} -W %h:%p {jump.user}@{jump.hostname} -p {jump.port}"

        # if jump host itself has a jump host, nest the proxy command
        if jump.jumphost:
            nested_proxy = jump._build_proxy_command()
            proxy_cmd += f" -o ProxyCommand=\"{nested_proxy}\""

        return proxy_cmd


    @model_validator(mode="after")
    def compute_common_args(self) -> Self:
        """Combine explicit extra_args with generated ones and ProxyCommand to construct common_args."""

        args = []
        if self.no_host_key_checking:
            args.append("-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null")
        if self.extra_args:
            args.append(self.extra_args)

        proxy_cmd = self._build_proxy_command()
        if proxy_cmd:
            args.append(f'-o ProxyCommand="{proxy_cmd}"')

        self.common_args = " ".join(args) if args else None
        return self


class ProvisioningCategory(StrEnum):
    """Supported provisioning categories."""

    NODE = auto()
    """Node (VM or baremetal) provisioning."""

    RU = auto()
    """Radio Unit provisioning."""

    UE = auto()
    """UE provisioning."""


class NodeProvisioningType(StrEnum):
    """Supported node provisioning types."""

    POS = auto()
    """Plain Orchestration Service provisioner."""

    LEGACY_POS = auto()
    """Legacy Plain Orchestration Service provisioner."""

    BI = auto()
    """Basic Infrastructure provisioner."""


class RUProvisioningType(StrEnum):
    """Supported Radio Unit provisioning types."""

    R2LAB = auto()
    """R2Lab RU provisioner."""


class UEProvisioningType(StrEnum):
    """Supported UE provisioning types."""

    R2LAB = auto()
    """R2Lab UE provisioner."""


# union type
type ProvisioningType = NodeProvisioningType | RUProvisioningType | UEProvisioningType


# NOTE model needs to tolerate extra fields from deployment model's params.provisioning
class GenericProvisionerParams(BlueprintTolerantBaseModel):
    """Base class for provisioner params."""

    extra_path: str | None = Field(default=None)
    """Extra Ansible environment path added to PATH used in the provisioner role."""


class CommonPOSParams(GenericProvisionerParams):
    """Common parameters between legacy and new POS provisioner."""

    image: str = Field(default="ubuntu-noble")
    """POS image name."""

    is_staged_image: bool = Field(default=False)
    """If the POS image is staged or not."""

    boot_params: str | None = Field(default=None)
    """POS boot parameters (https://man7.org/linux/man-pages/man7/bootparam.7.html)."""

    attempt_reservation: bool = Field(default=False)
    """If True, POS will try to reserve before allocating."""

    reservation_period: int = Field(default=120)
    """Attempted POS reservation period in minutes if 'attempt_reservation' is True."""

    only_bootstrap: bool = Field(default=False)
    """If True, POS will not reset node and only bootstrap it."""


class POSParams(CommonPOSParams):
    """POS provisioner parameters."""

    testbed: str = Field(default="sophia")
    """POS testbed."""


class LegacyPOSParams(CommonPOSParams):
    """Legacy POS provisioner parameters."""

    central_pos_ssh_info: SSHInfo = Field(default_factory=lambda: SSHInfo(
        hostname="duckburg.net.cit.tum.de",
        port=10022,
    ))
    """SSH information to access the central POS server."""

    public_key_file: str = Field(default=str(Path.home() / ".ssh/id_rsa.pub"))
    """Path to public key file that will be added to authorized_keys of provisioned nodes to allow subsequent SSH access."""


class BIParams(GenericProvisionerParams):
    """BI provisioner parameters."""

    infra: str = Field(default="fr-sophia2-bi-vm1")
    """BI infrastructure."""

    image: str = Field(default="Ubuntu 24.04.3")
    """BI image name."""

    flavor: str = Field(default="medium")
    """BI flavor name."""

    project: str = Field(default="post5g-beta")
    """SLICES project for BI."""

    experiment: str = Field(default="5gbp_exp")
    """SLICES experiment for BI."""

    create_experiment: bool = Field(default=False)
    """If True, will create SLICES experiment and delete a previous one if it exists."""

    experiment_duration: str = Field(default="24h", pattern=r"^\d+[mhdwy]$")
    """SLICES experiment duration set if 'create_experiment' is True."""

    node_duration: str = Field(default="3h", pattern=r"^\d+[mhdwy]$")
    """BI node lifetime duration."""


class R2LabParams(GenericProvisionerParams):
    """R2Lab provisioner parameters."""

    r2lab_gateway: str = Field(default="faraday.inria.fr")
    """R2Lab SSH-able gateway."""

    r2lab_slice: str = Field()
    """R2Lab user's slice name used to reserve and access testbed."""

    attempt_reservation: bool = Field(default=False)
    """If True, R2Lab provisioner will try to reserve before provisioning."""

    reservation_period: int = Field(default=120)
    """Attempted R2Lab reservation period in minutes if 'attempt_reservation' is True."""

    email: str | None = Field()
    """R2Lab user's email address used if 'attempt_reservation' is True."""

    passowrd: str | None = Field()
    """R2Lab user's password address used if 'attempt_reservation' is True."""


class GenericProvisioner(BlueprintBaseModel):
    """Base class for provisioner."""

    category: ProvisioningCategory = Field()
    """Provisioner category."""

    type: ProvisioningType = Field()
    """Provisioner type."""

    params: GenericProvisionerParams = Field(default_factory=GenericProvisionerParams)
    """Provisioner parameters."""


class POSProvisioner(GenericProvisioner):
    """POS provisioner."""

    category: Literal[ProvisioningCategory.NODE] = Field(frozen=True)
    """Provisioning category for POS provisioner."""

    type: Literal[NodeProvisioningType.POS] = Field(frozen=True)
    """Provisioning type for POS provisioner."""

    params: POSParams = Field(default_factory=POSParams)
    """POS provisioner parameters."""


class LegacyPOSProvisioner(GenericProvisioner):
    """Legacy POS provisioner."""

    category: Literal[ProvisioningCategory.NODE] = Field(frozen=True)
    """Provisioning category for Legacy POS provisioner."""

    type: Literal[NodeProvisioningType.LEGACY_POS] = Field(frozen=True)
    """Provisioning type for Legacy POS provisioner."""

    params: LegacyPOSParams = Field(default_factory=LegacyPOSParams)
    """Legacy POS provisioner parameters."""


class BIProvisioner(GenericProvisioner):
    """BI provisioner."""

    category: Literal[ProvisioningCategory.NODE] = Field(frozen=True)
    """Provisioning category for BI provisioner."""

    type: Literal[NodeProvisioningType.BI] = Field(frozen=True)
    """Provisioning type for BI provisioner."""

    params: BIParams = Field(default_factory=BIParams)
    """BI provisioner parameters."""


class R2LabRUProvisioner(GenericProvisioner):
    """R2lab RU provisioner."""

    category: Literal[ProvisioningCategory.RU] = Field(frozen=True)
    """Provisioning category for R2lab RU provisioner."""

    type: Literal[RUProvisioningType.R2LAB] = Field(frozen=True)
    """Provisioning type for R2lab RU provisioner."""

    params: R2LabParams = Field(default_factory=R2LabParams)
    """R2lab RU provisioner parameters."""


class R2LabUEProvisioner(GenericProvisioner):
    """R2lab UE provisioner."""

    category: Literal[ProvisioningCategory.UE] = Field(frozen=True)
    """Provisioning category for R2lab UE provisioner."""

    type: Literal[UEProvisioningType.R2LAB] = Field(frozen=True)
    """Provisioning type for R2lab UE provisioner."""

    params: R2LabParams = Field(default_factory=R2LabParams)
    """R2lab UE provisioner parameters."""


# types used to tell pydantic to validate the correct provisioner model based on its type
type NodeProvisioner = Annotated[POSProvisioner | LegacyPOSProvisioner | BIProvisioner, Field(discriminator="type")]
type RUProvisioner = Annotated[R2LabRUProvisioner, Field(discriminator="type")]
type UEProvisioner = Annotated[R2LabUEProvisioner, Field(discriminator="type")]

# type used to tell pydantic to validate the correct provisioner model based on the category
type Provisioner = Annotated[NodeProvisioner | RUProvisioner | UEProvisioner, Field(discriminator="category")]


class ProvisionableResource(BlueprintBaseModel):
    """Base class for provisionable resource (Node, RU, UE)."""

    category: ProvisioningCategory = Field()
    """Provisioning category."""

    is_provisioned: bool = Field(default=False)
    """If True, resource will not be provisioned."""

    provisioner: str | None = Field(default=None)
    """Provisioner's name."""

    provisioning_params: dict[str, Any] = Field(default_factory=dict)
    """Provisioner parameter overrides."""

    ssh_info: SSHInfo = Field(default_factory=SSHInfo)
    """Resource SSH configuration."""


    @model_validator(mode="after")
    def validate_provisioning(self):
        """Ensure provisioner is defined when 'is_provisioned' is False."""

        if not self.is_provisioned and self.provisioner is None:
            raise ValueError("Provisioner is required for when is_provisioned=False")

        return self


class ProvisionableNode(ProvisionableResource):
    """Node provisioning."""

    category: Literal[ProvisioningCategory.NODE] = Field(default=ProvisioningCategory.NODE, frozen=True)

    provisioner: str = Field(default="bi")
    """Node provisioner's name."""

    roles: list[Category5G | CoreComponentType | RANComponentType] = Field(default_factory=lambda: list(Category5G))
    """Node roles. Can be either a 5G catefory (e.g. core) or 5G component type (e.g. upf)."""

    k8s_status: K8SStatus = Field(default=K8SStatus.NOT_CONFIGURED)
    """Kubernetes status on node."""

    k8s_params: dict[str, Any] = Field(default_factory=dict)
    """Kubernetes parameter overrides."""


class ProvisionableRU(ProvisionableResource):
    """Radio Unit (RU) provisionig."""

    category: Literal[ProvisioningCategory.RU] = Field(default=ProvisioningCategory.RU, frozen=True)

    provisioner: str = Field(default="r2lab")
    """RU provisioner's name."""


class ProvisionableUE(ProvisionableResource):
    """User Equipment (UE) provisionig."""

    category: Literal[ProvisioningCategory.UE] = Field(default=ProvisioningCategory.UE, frozen=True)

    provisioner: str = Field(default="r2lab")
    """UE provisioner's name."""

    is_connected: bool = Field(default=False)
    """If this UE is connected or not."""
