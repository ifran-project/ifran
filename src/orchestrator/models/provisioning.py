"""Provisioning models."""

import re
from datetime import datetime, timedelta
from enum import StrEnum, auto
from pathlib import Path
from typing import Annotated, Any, Literal, Self, override
from zoneinfo import ZoneInfo

from metamodel.models.base import (
    StrictBaseModel,
    TolerantBaseModel,
)
from metamodel.models.common import Category5G
from metamodel.models.core import CoreComponentType
from metamodel.models.ran import RANComponentType
from metamodel.models.ric import RICComponentType
from metamodel.models.ru import RU
from metamodel.models.ue import UEType
from metamodel.utils import URL
from pydantic import (
    Field,
    IPvAnyAddress,
    TypeAdapter,
    computed_field,
    field_validator,
    model_validator,
)

from orchestrator.models.k8s import K8SStatus
from orchestrator.utils.utils import ResolvedPath


def _get_default_ssh_keys() -> list[str]:
    """Get the list of absolute paths for all public SSH keys from ~/.ssh."""

    ssh_dir = Path.home() / ".ssh"
    if ssh_dir.exists():
        return [str(p) for p in ssh_dir.glob("*.pub")]
    return []


class SSHInfo(StrictBaseModel):
    """SSH information about a host."""

    hostname: str | None = Field(default=None)
    """Hostname or IP address."""

    port: int = Field(default=22)
    """SSH port."""

    user: str = Field(default="root")
    """SSH username."""

    private_key_file: ResolvedPath | None = Field(default=None)
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

    ssh_pipelining: bool = Field(default=True)
    """If True, use SSH pipelining """

    # auto-generated
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
        if self.ssh_pipelining:
            args.append("-o ServerAliveInterval=30 -o ServerAliveCountMax=3 -o ControlMaster=auto")
            args.append("-o ControlPersist=7200s -o ControlPath=/tmp/cm-%C") # 2 hours
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
    """User Equipment provisioning."""


class ProvisioningType(StrEnum):
    """Supported provisioning types."""

    POS = auto()
    """Plain Orchestration Service provisioner."""

    LEGACY_POS = auto()
    """Legacy Plain Orchestration Service provisioner."""

    BI = auto()
    """Basic Infrastructure provisioner."""

    UNIFIED_RADIO = auto()
    """Unified radio management API provisioner."""

    R2LAB = auto()
    """R2Lab provisioner."""


# NOTE model needs to tolerate extra fields from deployment model's params.provisioning
class GenericProvisionerParams(TolerantBaseModel):
    """Base class for provisioner params."""

    extra_path: ResolvedPath | None = Field(default=None)
    """Extra Ansible environment path added to PATH used in the provisioner role."""


class GenericReservationParams(TolerantBaseModel):
    """Base class for provisioner's reservation params."""


class ReservableProvisionerParams(GenericProvisionerParams):
    """Params base class for provisioners where resource reservation is supported."""

    attempt_reservation: bool = Field(default=False)
    """If True, provisioner will try to reserve resources before provisioning."""

    reservation_period: int | None = Field(default=None)
    """Attempted reservation period in minutes if 'attempt_reservation' is True."""

    reservation_params: GenericReservationParams | None = Field(default=None)
    """Attempted reservation parameters if 'attempt_reservation' is True."""

    timezone: str = Field(default="Europe/Paris")
    """Reservation timezone."""

    start_time: datetime | None = Field(default=None)
    """The start datetime of the reservation. If None, defaults to current time in given timezone."""

    @computed_field
    @property
    def end_time(self) -> datetime | None:
        """The end datetime computed from the start time and reservation period."""

        if self.reservation_period is None:
            return self.start_time
        return self.start_time + timedelta(minutes=self.reservation_period) # type: ignore


    @field_validator("reservation_period", mode="before")
    @classmethod
    def parse_duration_to_minutes(cls, value) -> int | float | Any:
        """Parses duration strings (e.g., '120s', '1m', '3h', '2d', '1y') into total minutes."""

        if value is None or isinstance(value, (int, float)):
            return value

        if not isinstance(value, str):
            raise TypeError("'reservation_period' must be an integer (minutes) or a duration string.")

        v_str = value.strip().lower()
        match = re.match(r"^(\d+)([smhdyw])$", v_str)

        if not match:
            raise ValueError(f"Invalid duration format: {value!r}. "
                             "Use formats like: '120s', '30m', '3h', '2d', '1w', '1y'.")

        amount = int(match.group(1))
        unit = match.group(2)
        multipliers = {
            's': 1 / 60,          # seconds to minutes
            'm': 1,               # minutes
            'h': 60,              # hours to minutes
            'd': 24 * 60,         # days to minutes
            'w': 7 * 24 * 60,     # weeks to minutes
            'y': 365 * 24 * 60,   # years to minutes
        }
        return amount * multipliers[unit]


    def _populate_reservation(self, default_params_model = GenericReservationParams) -> None:
        """Ensures reservation fields are present when 'attempt_reservation' is True."""

        if self.reservation_period is None:
            self.reservation_period = 120 # default to 2 hours

        if self.reservation_params is None:
            if default_params_model is None:
                raise ValueError("Required reservation parameters are missing.")
            self.reservation_params = default_params_model()


    def _populate_start_time(self) -> Self:
        """Set 'start_time' if not provided using given timezone."""

        tzinfo = ZoneInfo(self.timezone)

        if self.start_time is None:
            self.start_time = datetime.now(tzinfo)
        elif self.start_time.tzinfo is None:
            # if the user passed a naive datetime, make it timezone aware
            self.start_time = self.start_time.replace(tzinfo=tzinfo)

        return self


    @model_validator(mode="after")
    def validate_reservation(self) -> Self:
        """Populate reservation reservation fields."""

        if self.attempt_reservation:
            self._populate_reservation()
        self._populate_start_time()
        return self


class CommonPOSParams(ReservableProvisionerParams):
    """Common parameters between legacy and new POS provisioner."""

    image: str = Field(default="ubuntu-noble")
    """POS image name."""

    is_staged_image: bool = Field(default=False)
    """If the POS image is staged or not."""

    boot_params: str | None = Field(default=None)
    """POS boot parameters (https://man7.org/linux/man-pages/man7/bootparam.7.html)."""

    only_bootstrap: bool = Field(default=False)
    """If True, POS will not reset node and only bootstrap it."""


class POSParams(CommonPOSParams):
    """POS provisioner parameters."""

    testbed: str = Field(default="sophia")
    """POS testbed."""

    use_slices: bool = Field(default=True)
    """If True, 'slices-pos' CLI will be used, else, 'pos' CLI will be used."""


class LegacyPOSParams(CommonPOSParams):
    """Legacy POS provisioner parameters."""

    central_pos_ssh_info: SSHInfo = Field(default_factory=lambda: SSHInfo(
        hostname="duckburg.net.cit.tum.de",
        port=10022,
    ))
    """SSH information to access the central POS server."""

    public_key_files: list[ResolvedPath] = Field(default=_get_default_ssh_keys())
    """
    Paths to public key files.
    Will be added to 'authorized_keys' of provisioned nodes to allow subsequent SSH access.
    """


class BIParams(GenericProvisionerParams):
    """BI provisioner parameters."""

    infra: str = Field(default="fr-sophia2-bi-vm1")
    """BI infrastructure."""

    image: str = Field(default="Ubuntu 24.04.3")
    """BI image name."""

    flavor: str = Field(default="large")
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

    allow_created: bool = Field(default=True)
    """Allow the BI nodes creation to fail, and only try to get the SSH info if the node is already created."""


class UnifiedRadioTokenParams(StrictBaseModel):
    """Parameters/fields to generate a valid token for the unified radio management API."""

    infra: str = Field(default="r2lab")
    """Radio infrastructure to generate the token for."""

    input_body: dict[str, Any] = Field(default_factory=dict)
    """Dictionary given as POST request input to the '/token/{infra}' endpoint."""


class UnifiedRadioParams(GenericProvisionerParams):
    """Provisioning parameters for the unified radio management API."""

    base_url: URL = Field(default=TypeAdapter(URL).validate_python("https://bi.theblueprintfactory.org/devices/api/v1"))
    """Base URL of the unified radio management API."""

    token: str | None = Field(default=None)
    """Valid API token. If None, a token will be generated from the given 'token_params'."""

    token_params: UnifiedRadioTokenParams | None = Field(default_factory=UnifiedRadioTokenParams)
    """Parameters used to generate a token when None is given."""


    @model_validator(mode="after")
    def validate_token(self) -> Self:
        """Ensure that 'token' and 'token_params' are not both None."""

        if self.token is None and self.token_params is None:
            raise ValueError("At least one of 'token' or 'token_params' must be provided.")
        return self


class R2LabReservationParams(GenericReservationParams):
    """R2Lab reservation parameters."""

    r2lab_api_url: URL = Field(default=TypeAdapter(URL).validate_python("https://r2labapi.inria.fr"))
    """R2Lab API base URL."""

    email: str = Field()
    """R2Lab user's email address."""

    password: str = Field()
    """R2Lab user's password address."""


class R2LabParams(UnifiedRadioParams, ReservableProvisionerParams):
    """R2Lab provisioner parameters."""

    r2lab_slice: str | None = Field(default=None)
    """R2Lab user's slice name."""

    reservation_params: R2LabReservationParams | None = Field(default=None)
    """R2Lab reservation parameters if 'attempt_reservation' is True."""

    @override
    def _populate_reservation(self) -> None:
        """Populate 'reservation_params' if missing from 'token_params.input_body' if given."""

        if self.attempt_reservation and self.token is None and self.reservation_params is None and self.token_params:
            try:
                self.reservation_params = R2LabReservationParams(
                    email=self.token_params.input_body.get("email"), # type: ignore
                    password=self.token_params.input_body.get("password"), # type: ignore
                )
            except Exception as e:
                raise ValueError(
                    "Failed to populate required 'reservation_params' from given 'token_params.input_body'."
                    ) from e

        super()._populate_reservation(default_params_model=None) # type: ignore


    @model_validator(mode="after")
    def populate_token_params(self) -> Self:
        """Populate 'token_params' from 'reservation_params' if given."""

        # ensure r2lab_slice is not None when attempt_reservation is True
        if self.attempt_reservation and self.r2lab_slice is None:
            raise ValueError("'r2lab_slice' cannot be left None when 'attempt_reservation' is True.")

        if not self.token and self.token_params:
            self.token_params.infra = "r2lab"

            if not self.token_params.input_body:
                if self.reservation_params:
                    self.token_params.input_body = {
                        "email": self.reservation_params.email,
                        "password": self.reservation_params.password,
                        "slice": self.r2lab_slice,
                    }
                else:
                    raise ValueError("Cannot populate required 'token_params.input_body'.")

        return self


class GenericProvisioner(StrictBaseModel):
    """Base class for provisioner."""

    supported_categories: set[ProvisioningCategory] = Field(default_factory=set)
    """Provisioning categories supported by this provisioner."""

    type: ProvisioningType = Field()
    """Provisioner type."""

    params: GenericProvisionerParams = Field(default_factory=GenericProvisionerParams)
    """Provisioner parameters."""


class POSProvisioner(GenericProvisioner):
    """POS provisioner."""

    supported_categories: set[Literal[ProvisioningCategory.NODE]] = Field(
        default_factory=lambda: {ProvisioningCategory.NODE}, frozen=True)

    type: Literal[ProvisioningType.POS] = Field(frozen=True)
    """Provisioning type for POS provisioner."""

    params: POSParams = Field(default_factory=POSParams)
    """POS provisioner parameters."""


class LegacyPOSProvisioner(GenericProvisioner):
    """Legacy POS provisioner."""

    supported_categories: set[Literal[ProvisioningCategory.NODE]] = Field(
        default_factory=lambda: {ProvisioningCategory.NODE}, frozen=True)

    type: Literal[ProvisioningType.LEGACY_POS] = Field(frozen=True)
    """Provisioning type for Legacy POS provisioner."""

    params: LegacyPOSParams = Field(default_factory=LegacyPOSParams)
    """Legacy POS provisioner parameters."""


class BIProvisioner(GenericProvisioner):
    """BI provisioner."""

    supported_categories: set[Literal[ProvisioningCategory.NODE]] = Field(
        default_factory=lambda: {ProvisioningCategory.NODE}, frozen=True)

    type: Literal[ProvisioningType.BI] = Field(frozen=True)
    """Provisioning type for BI provisioner."""

    params: BIParams = Field(default_factory=BIParams)
    """BI provisioner parameters."""


class UnifiedRadioProvisioner(GenericProvisioner):
    """Unified radio management API provisioner."""

    supported_categories: set[Literal[ProvisioningCategory.RU, ProvisioningCategory.UE]] = Field(
        default_factory=lambda: {ProvisioningCategory.RU, ProvisioningCategory.UE}, frozen=True)

    type: Literal[ProvisioningType.UNIFIED_RADIO] = Field(frozen=True)
    """Provisioning type for Unified Radio API RU provisioner."""

    params: UnifiedRadioParams = Field()
    """Unified Radio API RU provisioner parameters."""


class R2LabProvisioner(GenericProvisioner):
    """R2lab provisioner."""

    supported_categories: set[Literal[ProvisioningCategory.RU, ProvisioningCategory.UE]] = Field(
        default_factory=lambda: {ProvisioningCategory.RU, ProvisioningCategory.UE}, frozen=True)

    type: Literal[ProvisioningType.R2LAB] = Field(frozen=True)
    """Provisioning type for R2lab provisioner."""

    params: R2LabParams = Field()
    """R2lab provisioner parameters."""


# type used to tell pydantic to validate the correct provisioner model based on the type
type Provisioner = Annotated[
    POSProvisioner |
    LegacyPOSProvisioner |
    BIProvisioner |
    UnifiedRadioProvisioner |
    R2LabProvisioner,
    Field(discriminator="type")]


class GenericProvisionableResource(StrictBaseModel):
    """Base class for provisionable resource."""

    category: ProvisioningCategory = Field()
    """Provisioning category."""

    is_provisioned: bool = Field(default=False)
    """If True, resource will not be provisioned."""

    provisioner: str | None = Field(default=None)
    """Provisioner's name."""

    provisioning_params: dict[str, Any] = Field(default_factory=dict)
    """Provisioner parameter overrides."""


    @model_validator(mode="after")
    def validate_provisioning(self):
        """Ensure provisioner is defined when 'is_provisioned' is False."""

        if not self.is_provisioned and self.provisioner is None:
            raise ValueError("Provisioner is required for when is_provisioned=False")

        return self


class SSHableResource(GenericProvisionableResource):
    """Base class for provisionable resource (Node, RU, UE) that can be SSH-ed into."""

    ssh_info: SSHInfo = Field(default_factory=SSHInfo)
    """Resource SSH configuration."""


class DatabaseRole(StrEnum):
    """Node database role."""

    DATABASE = auto()

# union type
type NodeRole = Category5G | CoreComponentType | RANComponentType | RICComponentType | DatabaseRole

class ProvisionableNode(SSHableResource):
    """Node provisioning."""

    category: Literal[ProvisioningCategory.NODE] = Field(default=ProvisioningCategory.NODE, frozen=True)

    provisioner: str | None = Field(default="bi")
    """Node provisioner's name."""

    roles: list[NodeRole] = Field(default_factory=lambda: list(Category5G))
    """
    Node roles. Can be either a 5G category (e.g. core) or 5G component type (e.g. upf).
    Roles are added as "node-type.5g.blueprint/{role} = true" Kubernetes label for the node.
    """

    k8s_status: K8SStatus = Field(default=K8SStatus.NOT_CONFIGURED)
    """Kubernetes status on node."""

    k8s_params: dict[str, Any] = Field(default_factory=dict)
    """Kubernetes parameter overrides."""


class ProvisionableUE(SSHableResource):
    """User Equipment (UE) provisioning."""

    category: Literal[ProvisioningCategory.UE] = Field(default=ProvisioningCategory.UE, frozen=True)

    # NOTE ue type is used to distinguish between deployed and provisionable ues in deployment model
    type: Literal[UEType.COTS] = Field(frozen=True)
    """UE type."""

    provisioner: str | None = Field(default="r2lab")
    """UE provisioner's name."""

    is_connected: bool = Field(default=False)
    """If this UE is connected or not."""


# NOTE radio units are not ssh-able resources
class ProvisionableRU(GenericProvisionableResource):
    """Radio Unit (RU) provisioning."""

    category: Literal[ProvisioningCategory.RU] = Field(default=ProvisioningCategory.RU, frozen=True)

    provisioner: str | None = Field(default="r2lab")
    """RU provisioner's name."""

    ips: list[IPvAnyAddress] = Field(default_factory=list)
    """List of RU IP addresses."""


# type used to tell pydantic to validate the correct provisionable resource model based on the category
type ProvisionableResource = Annotated[
    ProvisionableNode |
    ProvisionableRU |
    ProvisionableUE,
    Field(discriminator="category")
]

# model used to resolve ru references in gnb/du/ue components
class MergedRU(RU, ProvisionableRU):
    """RU merged model."""
