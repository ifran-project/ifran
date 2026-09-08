"""5G core meta models."""

from enum import StrEnum, auto
from typing import Annotated, Any, Literal, Self

from pydantic import (
    Field,
    IPvAnyAddress,
    TypeAdapter,
    computed_field,
    field_serializer,
    field_validator,
    model_validator,
)

from orchestrator.models.common import (
    URL,
    BlueprintBaseModel,
    BlueprintTolerantBaseModel,
    parse_hex_int,
    serialize_hex_int,
)
from orchestrator.models.meta.common import (
    NGAP,
    PFCP,
    TLS,
    Category5G,
    Component5G,
    GTPUEndpoint,
    N6Endpoint,
    Network5G,
    SecurityAlgorithmConfiguration,
    TransportEndpoint,
)
from orchestrator.models.meta.slice import Slice


class CoreImplementation(StrEnum):
    """Supported open-source 5G core implementations."""

    OAI = auto()
    """OpenAirInterface core."""

    OPEN5GS = auto()
    """Open5GS core."""

    FREE5GC = auto()
    """Free5GC core."""


class CoreComponentType(StrEnum): # 16 of them
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

    LMF = auto()
    """Location Management Function."""


SUPPORTED_CORE_COMPONENTS: dict[CoreImplementation, list[CoreComponentType]] = {
    # OAI NEF, UDSF, SCP and AF are planned in OAI's roadmap
    # OAI NWDAF is not included in the official OAI Helm charts
    CoreImplementation.OAI: [
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
    CoreImplementation.OPEN5GS: [
        CoreComponentType.AMF,
        CoreComponentType.AUSF,
        CoreComponentType.BSF,
        CoreComponentType.NRF,
        CoreComponentType.NSSF,
        CoreComponentType.PCF,
        CoreComponentType.SCP,
        CoreComponentType.SMF,
        CoreComponentType.UDM,
        CoreComponentType.UDR,
        CoreComponentType.UPF,
    ],
    CoreImplementation.FREE5GC: [
        CoreComponentType.AMF,
        CoreComponentType.AUSF,
        CoreComponentType.BSF,
        CoreComponentType.CHF,
        CoreComponentType.NEF,
        CoreComponentType.NRF,
        CoreComponentType.NSSF,
        CoreComponentType.PCF,
        CoreComponentType.SMF,
        CoreComponentType.UDM,
        CoreComponentType.UDR,
        CoreComponentType.UPF,
    ],
}


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

    mcc: int = Field(default=1, ge=0, le=999)
    """Mobile Country Code (MCC) (3 digits)."""

    mnc: int = Field(default=1, ge=0, le=999)
    """Mobile Network Code (MNC) (2 to 3 digits)."""

    @computed_field
    @property
    def mncLength(self) -> int:
        """Length of the MNC field (2 or 3)."""

        return 2 if self.mnc < 100 else 3

    @computed_field
    @property
    def plmnId(self) -> str:
        """PLMN identity (MCC + MNC)."""

        return f"{self.mcc:03d}{self.mnc:02d}" if self.mnc < 100 else f"{self.mcc:03d}{self.mnc:03d}"


    @field_validator("mcc", "mnc", mode="before")
    @classmethod
    def parse_code(cls, value) -> int | Any:
        """Convert string MCC and MNC values to integers."""

        if isinstance(value, str):
            if not value.isdigit():
                raise ValueError("MCC and MNC must contain only digits.")
            return int(value)
        return value


    @field_serializer("mcc")
    def serialize_mcc(self, value: int) -> str:
        """Serialize MCC as a three-digit string."""

        return f"{value:03d}"


    @field_serializer("mnc")
    def serialize_mnc(self, value: int) -> str:
        """Serialize MNC as a two or three-digit string."""

        return f"{value:02d}" if value < 100 else f"{value:03d}"


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


# NOTE after serialization and deserialization, the computed amfId be given as input but should be tolerated
class GUAMI(BlueprintTolerantBaseModel):
    """
    Globally Unique AMF Identifier (GUAMI).

    3GPP References:
        - 3GPP TS 23.003, clause 2.10
        - 3GPP TS 23.501
        - 3GPP TS 38.413
    """

    plmnId: PLMN = Field(default_factory=PLMN)
    """PLMN Identity."""

    amfRegionId: int = Field(default=0x02, ge=0, le=0xFF)
    """AMF Region Identifier (8 bits)."""

    amfSetId: int = Field(default=0x001, ge=0, le=0x3FF)
    """AMF Set Identifier (10 bits)."""

    amfPointer: int = Field(default=0x00, ge=0, le=0x3F)
    """AMF Pointer (6 bits)."""

    @computed_field
    @property
    def amfId(self) -> int:
        """
        AMF Identifier (24-bit integer).
        
        Concatenates the fields into a single 24-bit value:
        [ Region ID (8 bits) ] [ Set ID (10 bits) ] [ Pointer (6 bits) ]
        
        - Region ID shifts left by 16 bits (10 + 6) to occupy bits 16-23.
        - Set ID shifts left by 6 bits to occupy bits 6-15.
        - Pointer occupies the lowest 6 bits (bits 0-5).
        """
        return (self.amfRegionId << 16) | (self.amfSetId << 6) | self.amfPointer

    @field_validator("amfRegionId", "amfSetId", "amfPointer", mode="before")
    @classmethod
    def normalize_hex_values(cls, value) -> int | Any:
        """Convert hexadecimal strings to integers."""

        return parse_hex_int(value)

    @field_serializer("amfRegionId")
    def serialize_amf_region_id(self, value: int) -> str:
        """Serialize AMF Region ID as hexadecimal."""

        return serialize_hex_int(value, 2)

    @field_serializer("amfSetId")
    def serialize_amf_set_id(self, value: int) -> str:
        """Serialize AMF Set ID as hexadecimal."""

        return serialize_hex_int(value, 3)

    @field_serializer("amfPointer")
    def serialize_amf_pointer(self, value: int) -> str:
        """Serialize AMF Pointer as hexadecimal."""

        return serialize_hex_int(value, 2)

    @field_serializer("amfId")
    def serialize_amf_id(self, value: int) -> str:
        """Serialize AMF ID as hexadecimal."""

        return serialize_hex_int(value, 6)


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


class NSIInformation(BlueprintBaseModel):
    """
    Network Slice Instance information.

    3GPP References:
        - 3GPP TS 29.531
        - 3GPP TS 29.571
    """

    nrfId: URL = Field(default=TypeAdapter(URL).validate_python("http://cn5g-nrf:8080/nnrf-disc/v1/nf-instances"))
    """NRF discovery URI used to discover Network Functions."""

    nsiId: int = Field(default=1)
    """Network Slice Instance identifier."""

    nrfNfMgtUri: URL | None = Field(default=TypeAdapter(URL).validate_python("http://cn5g-nrf:8080/nnrf-nfm/v1/nf-instances"))
    """NRF NF management URI."""


class NSIInfo(BlueprintBaseModel):
    """
    Network Slice Instance information associated with an S-NSSAI.

    3GPP References:
        - 3GPP TS 29.531
    """

    snssai: Slice | str = Field(default="internet")
    """S-NSSAI associated with the Network Slice Instance."""

    nsiInformationList: list[NSIInformation] = Field(default_factory=lambda: [NSIInformation()])
    """Network Slice Instance information."""


class RestrictedSNSSAIList(BlueprintBaseModel):
    """
    Restricted S-NSSAI list associated with a home PLMN.

    3GPP References:
        - 3GPP TS 29.531
    """

    homePlmnId: PLMN = Field(default_factory=PLMN)
    """Home PLMN identity for which the S-NSSAI restriction applies."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of restricted S-NSSAIs."""


class SupportedTAIItem(BlueprintBaseModel):
    """
    S-NSSAI information supported by a Tracking Area.

    3GPP References:
        - 3GPP TS 29.531
    """

    tai: TAI = Field(default_factory=TAI)
    """Tracking Area Identity."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of supported S-NSSAIs."""


class ExtendedSupportedTAIItem(SupportedTAIItem):
    """
    S-NSSAI information supported by a Tracking Area.

    3GPP References:
        - 3GPP TS 29.531
    """

    restrictedSnssaiList: list[RestrictedSNSSAIList] = Field(default_factory=list)
    """List of restricted S-NSSAIs."""


class SupportedNSSAIAvailabilityData(BlueprintBaseModel):
    """
    Supported S-NSSAI availability information for an AMF.

    3GPP References:
        - 3GPP TS 29.531
    """

    tai: TAI = Field(default_factory=TAI)
    """Tracking Area Identity for the supported S-NSSAI availability information."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of S-NSSAIs supported in the Tracking Area."""

    taiList: list[SupportedTAIItem] | None = Field(default=None)
    """Additional list of TAIs supported by the AMF."""


class AMFInfo(BlueprintBaseModel):
    """
    AMF information associated with an AMF Set.

    3GPP References:
        - 3GPP TS 29.531
        - 3GPP TS 29.571
    """

    nfId: str = Field(default="405e8251-cc5a-45dd-a494-efb9eaf1cd58")
    """NF Instance ID of the AMF."""

    supportedNssaiAvailabilityData: SupportedNSSAIAvailabilityData = Field(default_factory=SupportedNSSAIAvailabilityData)
    """Supported S-NSSAI availability information advertised by the AMF."""


class AMFInfoSet(BlueprintBaseModel):
    """
    AMF Set information used by the NSSF.

    3GPP References:
        - 3GPP TS 29.531
    """

    targetAmfSet: int = Field(default=0x001, ge=0, le=0x3FF)
    """Target AMF Set identifier."""

    nrfAmfSet: URL = Field(default=TypeAdapter(URL).validate_python("http://nrf/nnrf-nfm/v1/nf-instances"))
    """NRF discovery URI for the AMF Set."""

    nrfAmfSetNfMgtUri: URL = Field(default=TypeAdapter(URL).validate_python("http://nrf/nnrf-nfm/v1/nf-instances"))
    """NRF NF management URI for the AMF Set."""

    amfList: list[AMFInfo] = Field(default_factory=lambda: [AMFInfo()])
    """List of AMFs belonging to the AMF Set."""


    @field_validator("targetAmfSet", mode="before")
    @classmethod
    def normalize_hex_values(cls, value) -> int | Any:
        """Convert hexadecimal strings to integers."""

        return parse_hex_int(value)


    @field_serializer("targetAmfSet")
    def serialize_target_amf_set_id(self, value: int) -> str:
        """Serialize target AMF Set ID as hexadecimal."""

        return serialize_hex_int(value, 3)


class PLMNInfo(BlueprintBaseModel):
    """
    PLMN information configured in the NSSF.

    3GPP References:
        - 3GPP TS 29.531
        - 3GPP TS 29.571
    """

    operatorName: str = Field(default="")
    """Operator name."""

    homePlmnId: PLMN = Field(default_factory=PLMN)
    """Home PLMN identity."""


class CoreComponentConfig(BlueprintBaseModel):
    """
    Generic 5G Core Network Function configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.500
    """

    sbi: SBI = Field(default_factory=SBI)
    """Service-Based Interface configuration."""

    nrfUri: URL | None = Field(default=None)
    """URI of the NRF."""


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


class AUSFConfig(CoreComponentConfig):
    """
    Authentication Server Function (AUSF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.510
    """

    plmnList: list[PLMN] = Field(default_factory=lambda: [PLMN()])
    """List of PLMN identities (MCC/MNC) served by this AUSF instance for authentication."""


class SMFConfig(CoreComponentConfig):
    """
    Session Management Function (SMF) configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 23.502
        - 3GPP TS 29.510
        - 3GPP TS 29.502
        - 3GPP TS 29.244
    """

    n4: PFCP = Field(default_factory=PFCP)
    """N4 reference point endpoint. Used for PFCP signalling between SMF and UPF."""

    snssaiList: list[Slice | str] = Field(default_factory=lambda: ["internet"])
    """List of references to defined slices."""

    plmnList: list[PLMN] = Field(default_factory=lambda: [PLMN()])
    """List of PLMN identities (MCC/MNC) served by this SMF instance."""

    upfs: list[tuple[IPvAnyAddress, "UPFComponent"] | str] = Field(default_factory=lambda: ["upf"])
    """List of UPFs to connect to."""


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


class NSSFConfig(CoreComponentConfig):
    """
    Network Slice Selection Function configuration.

    3GPP References:
        - 3GPP TS 23.501
        - 3GPP TS 29.531
        - 3GPP TS 29.571
    """

    nsiInfoList: list[NSIInfo] = Field(default_factory=lambda: [NSIInfo()])
    """List of Network Slice Instance information."""

    taInfoList: list[ExtendedSupportedTAIItem] = Field(default_factory=lambda: [ExtendedSupportedTAIItem()])
    """List of Tracking Area and S-NSSAI information."""

    amfInfoList: list[AMFInfoSet] = Field(default_factory=lambda: [AMFInfoSet()])
    """List of AMF Set information."""

    plmnInfoList: list[PLMNInfo] = Field(default_factory=lambda: [PLMNInfo()])
    """List of PLMN information."""


class GenericAdvancedCoreConfig(BlueprintBaseModel):
    """Generic 5G core advanced configuration (implementation-specific)."""


class GenericOAIAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for OAI core."""

    log_level: dict[str, str] | None = Field(default=None)
    register_nf: dict[str, str] | None = Field(default=None)
    http_version: int | None = Field(default=None)
    nfs: dict[str, Any] | None = Field(default=None)


class GenericOpen5GSAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for Open5GS core."""

    logger: dict[str, Any] | None = Field(default=None)
    global_config: dict[str, Any] | None = Field(default=None)
    sslkeylogfile: str | None = Field(default=None)
    tls_client: dict[str, Any] | None = Field(default=None)
    sbi_client: dict[str, Any] | None = Field(default=None)


class GenericFree5GCAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for Free5GC core."""

    info: dict[str, Any] | None = Field(default=None)
    logger: dict[str, Any] | None = Field(default=None)
    nrfCertPem: str | None = Field(default=None)


class OAIAdvancedAMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI AMF."""

    database: dict[str, Any] | None = Field(default=None)
    support_features_options: dict[str, str] | None = Field(default=None)
    relative_capacity: int | None = Field(default=None)
    statistics_timer_interval: int | None = Field(default=None)
    emergency_support: bool | None = Field(default=None)


class OAIAdvancedSMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI SMF."""

    support_features: dict[str, str] | None = Field(default=None)
    ue_mtu: int | None = Field(default=None)
    upfs: dict[str, Any] | None = Field(default=None)
    ue_dns: dict[str, Any] | None = Field(default=None)


class OAIAdvancedUPFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UPF."""

    support_features: dict[str, str] | None = Field(default=None)
    remote_n6_gw: str | None = Field(default=None)


class OAIAdvancedPCFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI PCF."""

    database: dict[str, Any] | None = Field(default=None)
    local_policy: dict[str, str] | None = Field(default=None)
    enable_policy_provisioning_api: str | None = Field(default=None)


class OAIAdvancedNSSFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI NSSF."""

    slice_config_path: dict[str, str] | None = Field(default=None)


class OAIAdvancedLMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI LMF."""

    http_threads_count: int | None = Field(default=None)
    gnb_id_bits_count: int | None = Field(default=None)
    num_gnb: int | None = Field(default=None)
    trp_info_wait_ms: int | None = Field(default=None)
    positioning_wait_ms: int | None = Field(default=None)
    measurement_wait_ms: int | None = Field(default=None)
    support_features: dict[str, str] | None = Field(default=None)


class OAIAdvancedUDRConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UDR."""

    database: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedAMFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS AMF."""

    metrics: dict[str, Any] | None = Field(default=None)
    time: dict[str, Any] | None = Field(default=None)
    access_control: dict[str, Any] | None = Field(default=None)
    relative_capacity: int | None = Field(default=None)


class Open5GSAdvancedNRFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS NRF."""

    db_uri: str | None = Field(default=None)


class Open5GSAdvancedSCPConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS SCP."""

    db_uri: str | None = Field(default=None)
    info: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedSMFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS SMF."""

    metrics: dict[str, Any] | None = Field(default=None)
    info: dict[str, Any] | None = Field(default=None)
    pfcp_client: dict[str, Any] | None = Field(default=None)
    gtpc: dict[str, Any] | None = Field(default=None)
    gtpu: dict[str, Any] | None = Field(default=None)
    dns: dict[str, Any] | None = Field(default=None)
    mtu: int | None = Field(default=None)
    p_cscf: dict[str, Any] | None = Field(default=None)
    ctf: dict[str, Any] | None = Field(default=None)
    freeDiameter: str | None = Field(default=None)
    security_indication: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedUDMConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS UDM."""

    hnet: dict[str, Any] | None = Field(default=None)
    discovery: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedPCFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS PCF."""

    db_uri: str | None = Field(default=None)
    qos_profiles: dict[str, Any] | None = Field(default=None)
    policy: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedUDRConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS UDR."""

    db_uri: str | None = Field(default=None)


class Open5GSAdvancedUPFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS UPF."""

    metrics: dict[str, Any] | None = Field(default=None)
    pfcp_client: dict[str, Any] | None = Field(default=None)
    teid_range_indication: int
    teid_range: int | None = Field(default=None)
    network_instance: str | None = Field(default=None)
    source_interface: int | None = Field(default=None)


class Free5GCAdvancedAMFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC AMF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    ngapIE: dict[str, Any] | None = Field(default=None)
    nasIE: dict[str, Any] | None = Field(default=None)
    t3502Value: int | None = Field(default=None)
    t3512Value: int | None = Field(default=None)
    non3gppDeregTimerValue: int | None = Field(default=None)
    t3513: dict[str, Any] | None = Field(default=None)
    t3522: dict[str, Any] | None = Field(default=None)
    t3550: dict[str, Any] | None = Field(default=None)
    t3555: dict[str, Any] | None = Field(default=None)
    t3560: dict[str, Any] | None = Field(default=None)
    t3565: dict[str, Any] | None = Field(default=None)
    t3570: dict[str, Any] | None = Field(default=None)
    locality: str | None = Field(default=None)
    sctp: dict[str, Any] | None = Field(default=None)
    defaultUECtxReq: bool | None = Field(default=None)
    ngapWorkerPoolSize: int | None = Field(default=None)
    ngapTaskBufferSize: int | None = Field(default=None)


class Free5GCAdvancedAUSFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC AUSF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    groupId: str | None = Field(default=None)
    eapAkaSupiImsiPrefix: bool | None = Field(default=None)


class Free5GCAdvancedBSFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC BSF."""

    mongodb_name: str | None = Field(default=None)
    mongodb_url: str | None = Field(default=None)


class Free5GCAdvancedCHFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC CHF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    mongodb_name: str | None = Field(default=None)
    mongodb_url: str | None = Field(default=None)
    quotaValidityTime: int | None = Field(default=None)
    volumeLimit: int | None = Field(default=None)
    volumeLimitPDU: int | None = Field(default=None)
    volumeThresholdRate: float | None = Field(default=None)
    cgf: dict[str, Any] | None = Field(default=None)
    abmfDiameter: dict[str, Any] | None = Field(default=None)
    rfDiameter: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedNEFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC NEF."""

    serviceList: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedNRFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC NRF."""

    MongoDBName: str | None = Field(default=None)
    MongoDBUrl: str | None = Field(default=None)
    rootcert: dict[str, Any] | None = Field(default=None)
    oauth: bool | None = Field(default=None)
    serviceNameList: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedPCFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC PCF."""

    timeFormat: str | None = Field(default=None)
    defaultBdtRefId: str | None = Field(default=None)
    bsf_enable: bool | None = Field(default=None)
    serviceList: dict[str, Any] | None = Field(default=None)
    mongodb_name: str | None = Field(default=None)
    mongodb_url: str | None = Field(default=None)
    locality: str | None = Field(default=None)


class Free5GCAdvancedSMFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC SMF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    dns: dict[str, Any] | None = Field(default=None)
    locality: str | None = Field(default=None)
    assocFailAlertInterval: str | None = Field(default=None)
    assocFailRetryInterval: str | None = Field(default=None)
    heartbeatInterval: str | None = Field(default=None)
    userplaneInformation: dict[str, Any] | None = Field(default=None)
    links: dict[str, Any] | None = Field(default=None)
    t3591: dict[str, Any] | None = Field(default=None)
    t3592: dict[str, Any] | None = Field(default=None)
    urrPeriod: int | None = Field(default=None)
    urrThreshold: int | None = Field(default=None)
    requestedUnit: int | None = Field(default=None)


class Free5GCAdvancedUDMConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UDM."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    SuciProfile: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedUDRConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UDR."""

    mongodb_name: str | None = Field(default=None)
    mongodb_url: str | None = Field(default=None)
    dbConnectorType: str | None = Field(default=None)


class Free5GCAdvancedUPFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UPF."""

    version: str | None = Field(default=None)
    description: str | None = Field(default=None)
    retransTimeout: str | None = Field(default=None)
    maxRetrans: int | None = Field(default=None)
    gtpu: dict[str, Any] | None = Field(default=None)


ADVANCED_CORE_CONFIG_MAPPING: dict[CoreImplementation, dict[CoreComponentType, type[GenericAdvancedCoreConfig]]] = {
    CoreImplementation.OAI: {
        CoreComponentType.AMF: OAIAdvancedAMFConfig,
        CoreComponentType.SMF: OAIAdvancedSMFConfig,
        CoreComponentType.UPF: OAIAdvancedUPFConfig,
        CoreComponentType.PCF: OAIAdvancedPCFConfig,
        CoreComponentType.NSSF: OAIAdvancedNSSFConfig,
        CoreComponentType.LMF: OAIAdvancedLMFConfig,
        CoreComponentType.UDR: OAIAdvancedLMFConfig,
    },
    CoreImplementation.OPEN5GS: {
        CoreComponentType.AMF: Open5GSAdvancedAMFConfig,
        CoreComponentType.NRF: Open5GSAdvancedNRFConfig,
        CoreComponentType.PCF: Open5GSAdvancedPCFConfig,
        CoreComponentType.SCP: Open5GSAdvancedSCPConfig,
        CoreComponentType.SMF: Open5GSAdvancedSMFConfig,
        CoreComponentType.UDM: Open5GSAdvancedUDMConfig,
        CoreComponentType.UDR: Open5GSAdvancedUDRConfig,
        CoreComponentType.UPF: Open5GSAdvancedUPFConfig,
    },
    CoreImplementation.FREE5GC: {
        CoreComponentType.AMF: Free5GCAdvancedAMFConfig,
        CoreComponentType.AUSF: Free5GCAdvancedAUSFConfig,
        CoreComponentType.BSF: Free5GCAdvancedBSFConfig,
        CoreComponentType.CHF: Free5GCAdvancedCHFConfig,
        CoreComponentType.NEF: Free5GCAdvancedNEFConfig,
        CoreComponentType.NRF: Free5GCAdvancedNRFConfig,
        CoreComponentType.PCF: Free5GCAdvancedPCFConfig,
        CoreComponentType.SMF: Free5GCAdvancedSMFConfig,
        CoreComponentType.UDM: Free5GCAdvancedUDMConfig,
        CoreComponentType.UDR: Free5GCAdvancedUDRConfig,
        CoreComponentType.UPF: Free5GCAdvancedUPFConfig,
    },
}


class CoreComponent(Component5G):
    """Base class for 5G core component."""

    category: Literal[Category5G.CORE] = Field(default=Category5G.CORE, frozen=True)

    implementation: CoreImplementation | None = Field(default=None)
    """Core component implementation."""

    type: CoreComponentType = Field()
    """Core component type."""

    config: CoreComponentConfig = Field(default_factory=CoreComponentConfig)
    """Core component configuration."""

    advanced_config: dict[str, Any] | None = Field(default=None)
    """Core component configuration specific to the implementation."""


    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_CORE_CONFIG_MAPPING,
            default_model=GenericAdvancedCoreConfig,
        )


class AMFComponent(CoreComponent):
    """AMF component."""

    type: Literal[CoreComponentType.AMF] = Field(frozen=True)
    config: AMFConfig = Field(default_factory=AMFConfig)


class AUSFComponent(CoreComponent):
    """AUSF component."""

    type: Literal[CoreComponentType.AUSF] = Field(frozen=True)
    config: AUSFConfig = Field(default_factory=AUSFConfig)


class SMFComponent(CoreComponent):
    """SMF component."""

    type: Literal[CoreComponentType.SMF] = Field(frozen=True)
    config: SMFConfig = Field(default_factory=SMFConfig)


class UPFComponent(CoreComponent):
    """UPF component."""

    type: Literal[CoreComponentType.UPF] = Field(frozen=True)
    config: UPFConfig = Field(default_factory=UPFConfig)


class NRFComponent(CoreComponent):
    """NRF component."""

    type: Literal[CoreComponentType.NRF] = Field(frozen=True)
    config: NRFConfig = Field(default_factory=NRFConfig)


class NSSFComponent(CoreComponent):
    """NSSF component."""

    type: Literal[CoreComponentType.NSSF] = Field(frozen=True)
    config: NSSFConfig = Field(default_factory=NSSFConfig)


# components with their specific validated config
type ValidatedCoreComponent = Annotated[
    AMFComponent |
    AUSFComponent |
    SMFComponent |
    UPFComponent |
    NRFComponent |
    NSSFComponent,
    Field(discriminator="type")
]


class Core(Network5G):
    """5G core."""

    implementation: CoreImplementation = Field(default=CoreImplementation.OPEN5GS)
    """Core implementation."""

    components: dict[str, ValidatedCoreComponent | CoreComponent] = Field(default_factory=lambda: {
        "amf": AMFComponent(type=CoreComponentType.AMF),
        "ausf": AUSFComponent(type=CoreComponentType.AUSF),
        "bsf": CoreComponent(type=CoreComponentType.BSF),
        "nssf": NSSFComponent(type=CoreComponentType.NSSF),
        "nrf": NRFComponent(type=CoreComponentType.NRF),
        "pcf": CoreComponent(type=CoreComponentType.PCF),
        "smf": SMFComponent(type=CoreComponentType.SMF),
        "upf": UPFComponent(type=CoreComponentType.UPF),
        "udm": CoreComponent(type=CoreComponentType.UDM),
        "udr": CoreComponent(type=CoreComponentType.UDR),
    })
    """Core components."""


    @model_validator(mode="after")
    def validate_supported_core_component_types(self) -> Self:
        """Validate if requested 5G core component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_CORE_COMPONENTS)
        return self
