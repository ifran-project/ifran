"""5G core meta models."""

from enum import StrEnum, auto
from typing import Annotated, Literal

from pydantic import (
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from orchestrator.models.common import (
    BlueprintBaseModel,
    BlueprintTolerantBaseModel,
)
from orchestrator.models.meta.common import (
    NGAP,
    PFCP,
    Category5G,
    Component5G,
    GTPUEndpoint,
    N6Endpoint,
    Network5G,
    SecurityAlgorithmConfiguration,
    TransportEndpoint,
)
from orchestrator.models.meta.slice import Slice


class CoreType(StrEnum):
    """Supported open-source 5G core types/implementations."""

    OAI = auto()
    """OpenAirInterface core."""

    OPEN5GS = auto()
    """Open5GS core."""

    FREE5GC = auto()
    """Free5GC core."""


class CoreComponentType(StrEnum): # 23 of them
    """Supported 5G core components."""

    AMF = auto()
    """Access and Mobility Management Function."""

    SMF = auto()
    """Session Management Function."""

    UPF = auto()
    """User Plane Function."""

    AUSF = auto()
    """Authentication Server Function."""

    UDM = auto()
    """Unified Data Management."""

    UDR = auto()
    """Unified Data Repository."""

    PCF = auto()
    """Policy Control Function."""

    CHF = auto()
    """Charging Function."""

    NRF = auto()
    """Network Repository Function."""

    NSSF = auto()
    """Network Slice Selection Function."""

    NEF = auto()
    """Network Exposure Function."""

    NWDAF = auto()
    """Network Data Analytics Function."""

    BSF = auto()
    """Binding Support Function."""

    SEPP = auto()
    """Security Edge Protection Proxy."""

    SCP = auto()
    """Service Communication Proxy."""

    SGWC = auto()
    """Serving Gateway Control Plane."""

    SGWU = auto()
    """Serving Gateway User Plane."""

    HSS = auto()
    """Home Subscriber Server."""

    MME = auto()
    """Mobility Management Entity."""

    PCRF = auto()
    """Policy and Charging Rules Function."""

    LMF = auto()
    """Location Management Function."""

    N3IWF = auto()
    """Non-3GPP Interworking Function."""

    TNGF = auto()
    """Trusted Non-3GPP Gateway Function."""


SUPPORTED_CORE_COMPONENTS: dict[CoreType, list[CoreComponentType]] = {
    CoreType.OAI: [
        CoreComponentType.AMF,
        CoreComponentType.AUSF,
        CoreComponentType.LMF,
        CoreComponentType.NRF,
        CoreComponentType.NSSF,
        CoreComponentType.PCF,
        CoreComponentType.SMF,
        CoreComponentType.UDM,
        CoreComponentType.UDR,
        CoreComponentType.UPF,
    ],
    CoreType.OPEN5GS: [], # TODO to be added later
    CoreType.FREE5GC: [], # same
}


class TLS(BlueprintBaseModel):
    """
    Transport Layer Security (TLS) configuration.

    Defines the TLS parameters used to secure Service-Based Interface (SBI)
    communications over HTTPS.

    3GPP References:
        - 3GPP TS 29.500
        - 3GPP TS 33.501
    """

    enabled: bool = Field(default=False)
    """Enable Transport Layer Security (TLS)."""

    certificate: str | None = Field(default=None)
    """Path to the local X.509 certificate."""

    privateKey: str | None = Field( default=None)
    """Path to the local private key associated with the X.509 certificate."""


class SBI(TransportEndpoint):
    """
    Service-Based Interface (SBI) configuration.

    Defines the transport endpoint used by a Network Function (NF)
    to expose SBI services.

    3GPP References:
        - 3GPP TS 29.500
        - 3GPP TS 29.501
        - 3GPP TS 29.510
    """

    protocol: Literal["TCP"] = Field(default="TCP")

    scheme: Literal["http", "https"] = Field(default="http")
    """URI scheme used for the SBI endpoint."""

    port: int = Field(default=80, ge=1,le=65535)
    """TCP port of the SBI endpoint."""

    apiVersion: str = Field(default="v1", pattern=r"^v\d+$")
    """Service API version."""

    tls: TLS = Field(default_factory=TLS)
    """Transport Layer Security (TLS) configuration."""


# NOTE after serialization and deserialization, the mncLength and plmnId might be given as input but should be tolerated
class PLMN(BlueprintTolerantBaseModel):
    """
    Public Land Mobile Network (PLMN) Identity.

    3GPP References:
        - 3GPP TS 23.003, clause 2.2 (PLMN Identity)
        - 3GPP TS 24.501
        - 3GPP TS 29.571
    """

    mcc: str = Field(pattern=r"^\d{3}$", default="001")
    """Mobile Country Code (MCC) (3 digits string)."""

    mnc: str = Field(pattern=r"^\d{2,3}$", default="01")
    """Mobile Network Code (MNC) (2 to 3 digits string)."""

    @computed_field
    @property
    def mncLength(self) -> int:
        """Length of the MNC field (2 or 3)."""
        return len(self.mnc)

    @computed_field
    @property
    def plmnId(self) -> str:
        """PLMN identity (mcc + mnc)."""
        return f"{self.mcc}{self.mnc}"

    @field_validator("mcc", "mnc", mode="before")
    @classmethod
    def normalize_codes(cls, value):
        """Convert integer MCC/MNC values to strings before validation."""

        if isinstance(value, int):
            return str(value)
        return value


class PLMNSupportItem(BlueprintBaseModel):
    """
    Association between a PLMN Identity and supported S-NSSAIs.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.510
        - 3GPP TS 29.571
    """

    plmnId: PLMN = Field(default_factory=PLMN)
    """PLMN Identity."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of references to defined slices."""


class TAI(BlueprintBaseModel):
    """
    Tracking Area Identity (TAI).

    3GPP References:
        - 3GPP TS 23.003, clause 19.4
        - 3GPP TS 24.501
        - 3GPP TS 38.413
    """

    plmnId: PLMN = Field(default_factory=PLMN)
    """PLMN Identity."""

    tac: int = Field(default=1, ge=0, le=65535)
    """Tracking Area Code (16 bits)."""


class GUAMI(BlueprintBaseModel):
    """
    Globally Unique AMF Identifier (GUAMI).

    3GPP References:
        - 3GPP TS 23.003, clause 2.10
        - 3GPP TS 23.501
        - 3GPP TS 38.413
    """

    plmnId: PLMN = Field(default_factory=PLMN)
    """PLMN Identity."""

    amfRegionId: str = Field(default="02", pattern=r"^[A-Fa-f0-9]{2}$")
    """AMF Region Identifier (8 bits in hexadecimal)."""

    amfSetId: str = Field(default="001", pattern=r"^[A-Fa-f0-9]{3}$")
    """AMF Set Identifier (10 bits represented as 3 hexadecimal digits)."""

    amfPointer: str = Field(default="00", pattern=r"^[0-3][A-Fa-f0-9]$")
    """AMF Pointer (6 bits represented as a hexadecimal digit)."""


class NetworkName(BlueprintBaseModel):
    """
    Network Name.

    Broadcast network names provided by the AMF.

    3GPP References:
        - 3GPP TS 23.003
        - 3GPP TS 24.501
    """

    fullNetworkName: str = Field(default="5G_network")
    """Full Network Name."""

    shortNetworkName: str | None = Field(default=None)
    """Short Network Name."""


class CoreComponentConfig(BlueprintBaseModel):
    """
    Generic 5G Core Network Function configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.500
    """

    sbi: SBI = Field(default_factory=SBI)
    """Service-Based Interface configuration."""


class AMFConfig(CoreComponentConfig):
    """
    Access and Mobility Management Function (AMF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 23.502
        - 3GPP TS 24.501
        - 3GPP TS 29.518
        - 3GPP TS 38.413
    """

    n2: NGAP = Field(default_factory=NGAP)
    """N2 reference point endpoint. Used for NGAP signalling between AMF and NG-RAN."""

    guamiList: list[GUAMI] = Field(default_factory=lambda: [GUAMI()])
    """List of Globally Unique AMF Identifiers (GUAMI) supported by this AMF."""

    taiList: list[TAI] = Field(default_factory=lambda: [TAI()])
    """List of Tracking Area Identities (TAI) served by this AMF."""

    plmnList: list[PLMNSupportItem] = Field(default_factory=lambda: [PLMNSupportItem()])
    """List of supported PLMN identities and associated S-NSSAIs."""

    securityAlgorithmConfiguration: SecurityAlgorithmConfiguration = Field(default_factory=SecurityAlgorithmConfiguration)
    """Security algorithm preference configuration."""

    networkName: NetworkName = Field(default_factory=NetworkName)
    """Network Name broadcast by the AMF."""


class SMFConfig(CoreComponentConfig):
    """
    Session Management Function (SMF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 23.502
        - 3GPP TS 29.502
        - 3GPP TS 29.244
    """

    n4: PFCP = Field(default_factory=PFCP)
    """N4 reference point endpoint. Used for PFCP signalling between SMF and UPF."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of references to defined slices."""


class UPFConfig(CoreComponentConfig):
    """
    User Plane Function (UPF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.244
        - 3GPP TS 29.281
    """

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of references to defined slices."""

    n3: GTPUEndpoint = Field(default_factory=GTPUEndpoint)
    """N3 reference point endpoint. GTP-U user-plane tunnel endpoint towards NG-RAN."""

    n4: PFCP = Field(default_factory=PFCP)
    """N4 reference point endpoint. PFCP endpoint towards SMF."""

    n6: N6Endpoint = Field(default_factory=N6Endpoint)
    """N6 reference point endpoint. User-plane connection towards the Data Network (DN)."""

    n9: GTPUEndpoint = Field(default_factory=lambda: GTPUEndpoint(port=2153)) # chose port 2153 and keep default 2152 to n3 interface
    """N9 reference point endpoint. GTP-U endpoint used between UPFs."""


class NRFConfig(CoreComponentConfig):
    """
    Network Repository Function (NRF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.500
        - 3GPP TS 29.510
    """

    plmnList: list[PLMNSupportItem] = Field(default_factory=lambda: [PLMNSupportItem()])
    """List of supported PLMN identities and S-NSSAIs."""


class GenericAdvancedCoreConfig(BlueprintBaseModel):
    """Generic 5G core advanced configuration (implementation-specific)."""

    implementation: CoreType | None = Field(default=None)
    """5G core implementation."""

    type: CoreComponentType | None = Field(default=None)
    """5G core component type."""


class GenericOAIAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for OAI core."""

    implementation: Literal[CoreType.OAI] = Field(default=Literal[CoreType.OAI], frozen=True)
    log_level: dict[str, str] | None = Field(default=None)
    register_nf: dict[str, str] | None = Field(default=None)
    http_version: int | None = Field(default=None)
    nfs: dict | None = Field(default=None)


class GenericOpen5GSAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for Open5GS core."""

    implementation: Literal[CoreType.OPEN5GS] = Field(default=Literal[CoreType.OPEN5GS], frozen=True)


class GenericFree5GCAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for Free5GC core."""

    implementation: Literal[CoreType.FREE5GC] = Field(default=Literal[CoreType.OAI], frozen=True)


type AdvancedCoreConfig = Annotated[GenericOAIAdvancedCoreConfig | GenericOpen5GSAdvancedCoreConfig | GenericFree5GCAdvancedCoreConfig, Field(discriminator="implementation")]


class OAIAdvancedAMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI AMF."""

    type: Literal[CoreComponentType.AMF] = Field(default=Literal[CoreComponentType.AMF], frozen=True)
    database: dict | None = Field(default=None)
    support_features_options: dict[str, str] | None = Field(default=None)
    relative_capacity: int | None = Field(default=None)
    statistics_timer_interval: int | None = Field(default=None)
    emergency_support: bool | None = Field(default=None)


class OAIAdvancedSMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI SMF."""

    type: Literal[CoreComponentType.SMF] = Field(default=Literal[CoreComponentType.SMF], frozen=True)
    support_features: dict[str, str] | None = Field(default=None)
    ue_mtu: int | None = Field(default=None)
    upfs: dict | None = Field(default=None)
    ue_dns: dict | None = Field(default=None)


class OAIAdvancedUPFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UPF."""

    type: Literal[CoreComponentType.UPF] = Field(default=Literal[CoreComponentType.UPF], frozen=True)
    support_features: dict[str, str] | None = Field(default=None)
    remote_n6_gw: str | None = Field(default=None)


class OAIAdvancedPCFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI PCF."""

    type: Literal[CoreComponentType.PCF] = Field(default=Literal[CoreComponentType.PCF], frozen=True)
    local_policy: dict[str, str] | None = Field(default=None)


class OAIAdvancedNSSFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI NSSF."""

    type: Literal[CoreComponentType.NSSF] = Field(default=Literal[CoreComponentType.NSSF], frozen=True)
    slice_config_path: dict[str, str] | None = Field(default=None)


class OAIAdvancedLMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI LMF."""

    type: Literal[CoreComponentType.LMF] = Field(default=Literal[CoreComponentType.LMF], frozen=True)
    http_threads_count: int | None = Field(default=None)
    gnb_id_bits_count: int | None = Field(default=None)
    num_gnb: int | None = Field(default=None)
    trp_info_wait_ms: int | None = Field(default=None)
    positioning_wait_ms: int | None = Field(default=None)
    measurement_wait_ms: int | None = Field(default=None)
    support_features: dict[str, str] | None = Field(default=None)


class OAIAdvancedUDRConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UDR."""

    type: Literal[CoreComponentType.UDR] = Field(default=Literal[CoreComponentType.UDR], frozen=True)
    database: dict | None = Field(default=None)


ADVANCED_CORE_CONFIG_MAPPING: dict[CoreType, CoreComponentType] = {
    CoreType.OAI: {
        CoreComponentType.AMF: OAIAdvancedAMFConfig,
        CoreComponentType.SMF: OAIAdvancedSMFConfig,
        CoreComponentType.UPF: OAIAdvancedUPFConfig,
        CoreComponentType.PCF: OAIAdvancedPCFConfig,
        CoreComponentType.NSSF: OAIAdvancedNSSFConfig,
        CoreComponentType.LMF: OAIAdvancedLMFConfig,
        CoreComponentType.UDR: OAIAdvancedLMFConfig,
    }
}


class CoreComponent(Component5G):
    """Base class for 5G core component."""

    category: Literal[Category5G.CORE] = Field(default=Category5G.CORE, frozen=True)

    implementation: CoreType | None = Field(default=None)
    """Core component implementation."""

    type: CoreComponentType = Field()
    """Core component type."""

    config: CoreComponentConfig = Field(default_factory=CoreComponentConfig)
    """Core component configuration."""

    advanced_config: AdvancedCoreConfig | dict | None = Field(default=None)
    """Core component configuration specific to the implementation."""


    @model_validator(mode="after")
    def validate_advanced_config(self):
        """Validate advanced configuration based on what is supported."""

        if not isinstance(self.advanced_config, dict):
            return self

        model = ADVANCED_CORE_CONFIG_MAPPING.get(self.implementation, {}).get(self.type)
        if model:
            self.advanced_config = model(**self.advanced_config)
        return self


class AMFComponent(CoreComponent):
    """AMF component."""

    type: Literal[CoreComponentType.AMF] = Field(default=CoreComponentType.AMF, frozen=True)
    config: AMFConfig = Field(default_factory=AMFConfig)


class SMFComponent(CoreComponent):
    """SMF component."""

    type: Literal[CoreComponentType.SMF] = Field(default=CoreComponentType.SMF, frozen=True)
    config: SMFConfig = Field(default_factory=SMFConfig)


class UPFComponent(CoreComponent):
    """UPF component."""

    type: Literal[CoreComponentType.UPF] = Field(default=CoreComponentType.UPF, frozen=True)
    config: UPFConfig = Field(default_factory=UPFConfig)


class NRFComponent(CoreComponent):
    """NRF component."""

    type: Literal[CoreComponentType.NRF] = Field(default=CoreComponentType.NRF, frozen=True)
    config: NRFConfig = Field(default_factory=NRFConfig)


# components with their specific validated config
type ValidatedCoreComponent = Annotated[AMFComponent | SMFComponent | UPFComponent | NRFComponent, Field(discriminator="type")]


class Core(Network5G):
    """5G core."""

    type: CoreType | None = Field(default=CoreType.OAI)
    """Core type."""

    components: dict[str, ValidatedCoreComponent | CoreComponent] = Field(default_factory=lambda: {
        "amf": AMFComponent(),
        "smf": SMFComponent(),
        "upf": UPFComponent(),
        "nrf": NRFComponent(),
    })
    """Core components."""


    @model_validator(mode="after")
    def validate_supported_core_component_types(self):
        """Validate if requested 5G core component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_CORE_COMPONENTS)
        return self