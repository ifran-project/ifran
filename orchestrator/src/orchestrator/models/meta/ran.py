"""5G RAN meta models."""

from enum import IntEnum, StrEnum, auto
from typing import Annotated, Any, Literal

from pydantic import Field, IPvAnyAddress, model_validator

from orchestrator.models.common import (
    BlueprintBaseModel,
)
from orchestrator.models.deployment.k8s import MultusNetworkStatus
from orchestrator.models.meta.common import (
    E1,
    E2,
    F1C,
    F1U,
    NGAP,
    Category5G,
    Component5G,
    DuplexMode,
    GTPUEndpoint,
    Network5G,
    SecurityAlgorithmConfiguration,
)
from orchestrator.models.meta.core import PLMNSupportItem
from orchestrator.models.meta.ru import RU


class RANType(StrEnum):
    """Supported open-source 5G RAN types/implementations."""

    OAI = auto()
    """OpenAirInterface RAN."""

    SRSRAN = auto()
    """SRS RAN."""

    UERANSIM = auto()
    """UERANSIM."""


class RANComponentType(StrEnum):
    """Supported 5G RAN components."""

    GNB = auto()
    """Monolithic gNodeB."""

    CU = auto()
    """Central Unit (F1 split)."""

    DU = auto()
    """Distributed Unit (F1 split)."""

    CU_CP = "cu-cp"
    """CU Control Plane (E1 split)."""

    CU_UP = "cu-up"
    """CU User Plane (E1 split)."""


SUPPORTED_RAN_COMPONENTS: dict[RANType, list[RANComponentType]] = {
    RANType.OAI: [
        RANComponentType.CU,
        RANComponentType.CU_CP,
        RANComponentType.CU_UP,
        RANComponentType.DU,
        RANComponentType.GNB,
    ],
    RANType.SRSRAN: [], # TODO to be added later
    RANType.UERANSIM: [], # same
}


class FrequencyRange(StrEnum):
    """3GPP TS 38.104 Clause 5.1: Frequency Ranges."""

    FR1 = auto() 
    """Sub-6 GHz (410 MHz - 7125 MHz)"""

    FR2 = auto() 
    """mmWave (24250 MHz - 71000 MHz)"""


class SubcarrierSpacing(IntEnum):
    """3GPP TS 38.211 Table 4.2-1: Subcarrier Spacing (SCS) Numerologies."""

    SCS_15KHZ = 15
    """mu = 0 (FR1 only)"""

    SCS_30KHZ = 30
    """mu = 1 (FR1 only)"""

    SCS_60KHZ = 60
    """mu = 2 (FR1 and FR2)"""

    SCS_120KHZ = 120
    """mu = 3 (FR2 only)"""

    SCS_240KHZ = 240
    """mu = 4 (FR2 only)"""


NUMEROLOGY: dict[SubcarrierSpacing, int] = {
    SubcarrierSpacing.SCS_15KHZ: 0,
    SubcarrierSpacing.SCS_30KHZ: 1,
    SubcarrierSpacing.SCS_60KHZ: 2,
    SubcarrierSpacing.SCS_120KHZ: 3,
    SubcarrierSpacing.SCS_240KHZ: 4,
}

# Common FR1 operating bands. An explicit radio.duplex_mode remains available
# for bands not yet included in this prototype catalogue.
TDD_BANDS: set[int] = {38, 40, 41, 46, 47, 48, 50, 51, 53, 77, 78, 79, 90, 96, 101, 102, 104}
FDD_BANDS: set[int] = {1, 2, 3, 5, 7, 8, 12, 13, 14, 18, 20, 24, 25, 26, 28, 30, 31, 65, 66, 70, 71, 74, 85, 91, 92, 93, 94, 95, 97, 98, 99, 100}


class SCTPConfiguration(BlueprintBaseModel):
    """
    Stream Control Transmission Protocol (SCTP) configuration.

    3GPP References:
        - 3GPP TS 38.401
        - 3GPP TS 38.410
    """

    inStreams: int = Field(default=2, ge=1)
    """Number of inbound SCTP streams."""

    outStreams: int = Field(default=2, ge=1)
    """Number of outbound SCTP streams."""


class TDDConfiguration(BlueprintBaseModel):
    """
    NR TDD UL/DL slot pattern configuration.
    
    Maps directly to 3GPP TS 38.331 'TDD-UL-DL-ConfigCommon' / 'Pattern'.
    """

    periodicityMilliseconds: float = Field(default=5.0, gt=0)
    """TDD periodicity."""

    nrofDownlinkSlots: int = Field(default=7,ge=0,le=320)
    """Number of complete downlink slots."""

    nrofDownlinkSymbols: int = Field(default=6,ge=0,le=14)
    """Number of additional downlink symbols."""

    nrofUplinkSlots: int = Field(default=2,ge=0,le=320)
    """Number of complete uplink slots."""

    nrofUplinkSymbols: int = Field(default=4,ge=0,le=14)
    """Number of additional uplink symbols."""


class RadioConfiguration(BlueprintBaseModel):
    """
    NR Radio Configuration.

    3GPP References:
        - 3GPP TS 38.104 (BS Radio Transmission and Reception)
        - 3GPP TS 38.211 (Physical Channels and Modulation)
        - 3GPP TS 38.331 (RRC Protocol Information Elements)
    """

    frType: FrequencyRange = Field(default=FrequencyRange.FR1)
    """Frequency Range Type (FR1 or FR2). Determines structural bandwidth limits."""

    nrBand: int = Field(default=78, ge=1, le=303)
    """NR Operating Band (e.g. 78 for n78). Covers FR1 and FR2 boundaries."""

    duplexMode: DuplexMode | None = Field(default=None)
    """NR Duplex Mode. None means derive the duplex mode from the NR band."""

    downlinkArfcn: int = Field(default=640000, ge=0, le=3279165)
    """NR Downlink Absolute Radio Frequency Channel Number (NR-ARFCN). Max bound per TS 38.104."""

    ssbArfcn: int = Field(default=621312, ge=0, le=3279165)
    """Synchronization Signal Block (SSB) NR-ARFCN positioning."""

    pointAFrequencyArfcn: int = Field(default=620040, ge=0, le=3279165)
    """Absolute Frequency of Resource Element Point A."""

    channelBandwidthMhz: int = Field(default=40, ge=5, le=400)
    """NR Transmission Channel Bandwidth in MHz."""

    subcarrierSpacingKhz: SubcarrierSpacing = Field(default=SubcarrierSpacing.SCS_30KHZ)
    """NR Subcarrier Spacing configuration."""

    tddConfiguration: TDDConfiguration | None = Field(default_factory=TDDConfiguration)
    """TDD configuration if duplex mode is TDD."""

    # NOTE don't use @property to avoid having to tolerate extra input fields for serialized output
    numerology: int | None = Field(default=None)
    """NR numerology corresponding to the configured SCS."""

    @model_validator(mode="after")
    def populate_numerlogy(self):
        """Populate the NR numerology corresponding to the configured SCS."""

        if self.numerology is None:
            self.numerology = NUMEROLOGY[self.subcarrierSpacingKhz]
        return self


    def _derive_duplex_mode(self) -> None:
        """Derive duplex mode if not defined from the configured NR band."""

        if self.duplexMode is None:
            # band can be support both -> tdd takes precedednce
            if self.nrBand in FDD_BANDS:
                self.duplexMode = DuplexMode.FDD
            elif self.nrBand in TDD_BANDS:
                self.duplexMode = DuplexMode.TDD
            else:
                raise ValueError(f"Cannot derive duplex mode for given NR band 'n{self.nrBand}'.")


    def _validate_tdd(self) -> None:
        """Ensure 'tddConfiguration' is set when duplex mode is TDD."""

        if self.duplexMode == DuplexMode.TDD and self.tddConfiguration is None:
            raise ValueError("'tddConfiguration' is required when duplex mode is TDD.")


    @model_validator(mode="after")
    def validate_configuration(self):
        """Validate provided radion configuration."""

        self._derive_duplex_mode()
        self._validate_tdd()
        return self


class RANComponentConfig(BlueprintBaseModel):
    """Generic RAN configuration."""

    timeZone: str = Field(default="Europe/Paris")
    """Timezone."""

    gnbId: int = Field(default=0, ge=0, le=4294967295)
    """gNB identity."""

    tac: int = Field(default=1, ge=0, le=65535)
    """Tracking Area Code (16 bits)."""

    plmnList: list[PLMNSupportItem] = Field(default_factory=lambda: [PLMNSupportItem()])
    """List of supported PLMN identities and associated S-NSSAIs."""

    sctpConfiguration: SCTPConfiguration = Field(default_factory=SCTPConfiguration)
    """SCTP configuration."""

    e2: E2 | None = Field(default=None)
    """E2 endpoint used to reach the RIC."""

    ric: IPvAnyAddress | str | None = Field(default=None)
    """RIC component to connect to (can be a reference to a defined RIC)."""


class CommonCUConfig(RANComponentConfig):
    """Common configuration between CU, CU-UP and CU-CP."""

    du: IPvAnyAddress | str | list[MultusNetworkStatus] = Field()
    """DU component to connect to (can be a reference to a defined DU)."""


class CUCPConfig(CommonCUConfig):
    """Generic CU-CP configuration."""

    nrCellId: int = Field(default=0, ge=0)
    """NR Cell Identity."""

    securityAlgorithmConfiguration: SecurityAlgorithmConfiguration = Field(default_factory=SecurityAlgorithmConfiguration)
    """Security algorithm preference configuration."""

    e1: E1 = Field(default_factory=E1)
    """E1 endpoint used to reach CU-CP."""

    f1c: F1C = Field(default_factory=F1C)
    """F1-C endpoint used to reach DU."""

    n2: NGAP = Field(default_factory=NGAP)
    """N2 reference point endpoint. Used for NGAP signalling between AMF and NG-RAN."""

    cu_up: IPvAnyAddress | str | list[MultusNetworkStatus] = Field()
    """CU-UP component to connect to (can be a reference to a defined CU-UP or CU)."""

    amf: IPvAnyAddress | str = Field(default="amf")
    """AMF component to connect to (can be a reference to a defined AMF)."""


class CUUPConfig(CommonCUConfig):
    """Generic CU-UP configuration."""

    gnbCuUpId: int = Field(default=0, ge=0, le=4294967295)
    """gNB CU-UP identity."""

    e1: E1 = Field(default_factory=E1)
    """E1 endpoint used to reach CU-CP."""

    f1u: F1U = Field(default_factory=F1U)
    """F1-U endpoint used to reach DU."""

    n3: GTPUEndpoint = Field(default_factory=GTPUEndpoint)
    """N3 reference point endpoint. GTP-U user-plane tunnel endpoint towards NG-RAN."""

    cu_cp: IPvAnyAddress | str | list[MultusNetworkStatus] = Field()
    """CU-CP component to connect to (can be a reference to a defined CU-CP or CU)."""


class CUConfig(CommonCUConfig):
    """Generic CU configuration."""

    nrCellId: int = Field(default=0, ge=0)
    """NR Cell Identity."""

    f1c: F1C = Field(default_factory=F1C)
    """F1-C endpoint used to reach DU."""

    f1u: F1U = Field(default_factory=F1U)
    """F1-U endpoint used to reach DU."""

    n2: NGAP = Field(default_factory=NGAP)
    """N2 reference point endpoint. Used for NGAP signalling between AMF and NG-RAN."""

    n3: GTPUEndpoint = Field(default_factory=GTPUEndpoint)
    """N3 reference point endpoint. GTP-U user-plane tunnel endpoint towards NG-RAN."""

    securityAlgorithmConfiguration: SecurityAlgorithmConfiguration = Field(default_factory=SecurityAlgorithmConfiguration)
    """Security algorithm preference configuration."""

    amf: IPvAnyAddress | str = Field(default="amf")
    """AMF component to connect to (can be a reference to a defined AMF)."""


class CommonGNBConfig(RANComponentConfig):
    """Common configuration between gNB and DU."""

    nrCellId: int = Field(default=1, ge=0)
    """NR Cell Identity."""

    physicalCellId: int = Field(default=0, ge=0, le=4294967295)
    """Physical cell identity."""

    radioConfiguration: RadioConfiguration = Field(default_factory=RadioConfiguration)
    """Radio configuration."""

    ru: RU | str = Field(default="sim_ru")
    """Reference to a defined RU."""


class DUConfig(CommonGNBConfig):
    """Generic DU configuration."""

    gnbDuId: int = Field(default=0, ge=0, le=4294967295)
    """gNB DU identity."""

    f1u: F1U = Field(default_factory=F1U)
    """F1-U endpoint."""

    f1c: F1C = Field(default_factory=F1C)
    """F1-C endpoint."""

    cu_cp: IPvAnyAddress | str | list[MultusNetworkStatus] = Field()
    """CU-CP component to connect to (can be a reference to a defined CU or CU-CP)."""

    cu_up: IPvAnyAddress | str | list[MultusNetworkStatus] = Field()
    """CU-UP component to connect to (can be a reference to a defined CU or CU-CUP)."""


class GNBConfig(CommonGNBConfig):
    """Generic gNB configuration."""

    securityAlgorithmConfiguration: SecurityAlgorithmConfiguration = Field(default_factory=SecurityAlgorithmConfiguration)
    """Security algorithm preference configuration."""

    n2: NGAP = Field(default_factory=NGAP)
    """N2 reference point endpoint. Used for NGAP signalling between AMF and NG-RAN."""

    n3: GTPUEndpoint = Field(default_factory=GTPUEndpoint)
    """N3 reference point endpoint. GTP-U user-plane tunnel endpoint towards NG-RAN."""

    amf: IPvAnyAddress | str = Field(default="amf")
    """AMF component to connect to (can be a reference to a defined AMF)."""


class GenericAdvancedRANConfig(BlueprintBaseModel):
    """Generic 5G RAN advanced configuration (implementation-specific)."""

    implementation: RANType | None = Field(default=None)
    """5G RAN implementation."""

    type: RANComponentType | None = Field(default=None)
    """5G RAN component type."""


class GenericOAIAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for OAI RAN."""

   implementation: Literal[RANType.OAI] = Field(default=RANType.OAI, frozen=True)
   useAdditionalOptions: str | None = Field(default=None)
   gdbstack: int | None = Field(default=None)
   Asn1_verbosity: Literal["none", "info", "annoying"] | None = Field(default=None)
   log_config: dict[str, str] | None = Field(default=None)


class GenericSRSRANAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for SRSRAN RAN."""

   implementation: Literal[RANType.SRSRAN] = Field(default=RANType.SRSRAN, frozen=True)


class GenericUERANSIMAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for UERANSIM RAN."""

   implementation: Literal[RANType.UERANSIM] = Field(default=RANType.UERANSIM, frozen=True)


type AdvancedRANConfig = Annotated[GenericOAIAdvancedRANConfig | GenericSRSRANAdvancedRANConfig | GenericUERANSIMAdvancedRANConfig, Field(discriminator="implementation")]


class OAIAdvancedCUCPConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU-CP."""

    Num_Threads_PUSCH: int | None = Field(default=None)
    sa: int | None = Field(default=None)
    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)


class OAIAdvancedCUUPConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU-UP."""


class OAIAdvancedCUConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU."""

    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)
    sm_dir: str | None = Field(default=None)


class OAIAdvancedCommonGNBConfig(GenericOAIAdvancedRANConfig):
   """OAI advanced configuration common for gNB and DU."""

   min_rxtxtime: int | None = Field(default=None)
   dl_offstToCarrier: int | None = Field(default=None)
   initialDLBWPlocationAndBandwidth: int | None = Field(default=None)
   initialDLBWPcontrolResourceSetZero: int | None = Field(default=None)
   initialDLBWPsearchSpaceZero: int | None = Field(default=None)
   ul_offstToCarrier: int | None = Field(default=None)
   pMax: int | None = Field(default=None)
   initialULBWPlocationAndBandwidth: int | None = Field(default=None)
   prach_ConfigurationIndex: int | None = Field(default=None)
   prach_msg1_FDM: int | None = Field(default=None)
   prach_msg1_FrequencyStart: int | None = Field(default=None)
   zeroCorrelationZoneConfig: int | None = Field(default=None)
   preambleTransMax: int | None = Field(default=None)
   powerRampingStep: int | None = Field(default=None)
   ssb_perRACH_OccasionAndCB_PreamblesPerSSB_PR: int | None = Field(default=None)
   ssb_perRACH_OccasionAndCB_PreamblesPerSSB: int | None = Field(default=None)
   ra_ContentionResolutionTimer: int | None = Field(default=None)
   rsrp_ThresholdSSB: int | None = Field(default=None)
   prach_RootSequenceIndex_PR: int | None = Field(default=None)
   prach_RootSequenceIndex: int | None = Field(default=None)
   restrictedSetConfig: int | None = Field(default=None)
   msg3_DeltaPreamble: int | None = Field(default=None)
   p0_NominalWithGrant: int | None = Field(default=None)
   pucchGroupHopping: int | None = Field(default=None)
   hoppingId: int | None = Field(default=None)
   p0_nominal: int | None = Field(default=None)
   ssb_PositionsInBurst_Bitmap: int | None = Field(default=None)
   ssb_periodicityServingCell: int | None = Field(default=None)
   dmrs_TypeA_Position: int | None = Field(default=None)
   ssPBCH_BlockPower: int | None = Field(default=None)
   pusch_TargetSNRx10: int | None = Field(default=None)
   pucch_TargetSNRx10: int | None = Field(default=None)
   prach_dtx_threshold: int | None = Field(default=None)
   pucch0_dtx_threshold: int | None = Field(default=None)
   ofdm_offset_divisor: int | None = Field(default=None)
   local_rf: str | None = Field(default=None)
   max_pdschReferenceSignalPower: int | None = Field(default=None)
   eNB_instances: list[int] | None = Field(default=None)
   sf_extension: int | None = Field(default=None)
   rfsimulator: dict | None = Field(default=None)


class OAIAdvancedDUConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI DU."""


class OAIAdvancedGNBConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI GNB."""

    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)
    sm_dir: str | None = Field(default=None)


ADVANCED_RAN_CONFIG_MAPPING: dict[RANType, dict[RANComponentType, AdvancedRANConfig]] = {
    RANType.OAI: {
        RANComponentType.CU_CP: OAIAdvancedCUCPConfig,
        RANComponentType.CU_UP: OAIAdvancedCUUPConfig,
        RANComponentType.DU: OAIAdvancedDUConfig,
        RANComponentType.GNB: OAIAdvancedGNBConfig,
    }
}


class GenericRANComponent(Component5G):
    """Generic RAN component."""

    category: Literal[Category5G.RAN] = Field(default=Category5G.RAN, frozen=True)

    implementation: RANType | None = Field(default=None)
    """RAN component implementation."""

    type: RANComponentType = Field()
    """Core component type."""

    config: RANComponentConfig = Field(default_factory=RANComponentConfig)
    """Core component configuration."""

    advanced_config: AdvancedRANConfig | dict | None = Field(default=None)
    """RAN component configuration specific to the implementation."""


    @model_validator(mode="after")
    def validate_advanced_config(self):
        """Validate advanced configuration based on what is supported."""

        if not isinstance(self.advanced_config, dict):
            return self

        model = ADVANCED_RAN_CONFIG_MAPPING.get(self.implementation, {}).get(self.type)
        if model:
            self.advanced_config = model(**self.advanced_config)
        return self


class CUCPComponent(GenericRANComponent):
    """Generic CU-CP component config."""

    type: Literal[RANComponentType.CU_CP] = Field(default=RANComponentType.CU_CP, frozen=True)
    config: CUCPConfig = Field(default_factory=CUCPConfig)
    """CU-CP component configuration."""


class CUUPComponent(GenericRANComponent):
    """Generic CU=UP component config."""

    type: Literal[RANComponentType.CU_UP] = Field(default=RANComponentType.CU_UP, frozen=True)
    config: CUUPConfig = Field(default_factory=CUUPConfig)
    """CU-UP component configuration."""


class CUComponent(GenericRANComponent):
    """Generic CU component config."""

    type: Literal[RANComponentType.CU] = Field(default=RANComponentType.CU, frozen=True)
    config: CUConfig = Field(default_factory=CUConfig)
    """CU component configuration."""


class CommonGNBComponent(GenericRANComponent):
    """
    Common component for gNB and DU.
    Used mainly to add derived radio configuration
    for implementation specific parameters translation.
    """

    config: CommonGNBConfig = Field(default_factory=CommonGNBConfig)
    derived_radio_config: dict[str, Any] | None = Field(default=None)
    """Automatically derived implementation-specific radio parameters."""


class DUComponent(CommonGNBComponent):
    """Generic DU component config."""

    type: Literal[RANComponentType.DU] = Field(default=RANComponentType.DU, frozen=True)
    config: DUConfig = Field(default_factory=DUConfig)
    """DU component configuration."""


class GNBComponent(CommonGNBComponent):
    """Generic gNB component config."""

    type: Literal[RANComponentType.GNB] = Field(default=RANComponentType.GNB, frozen=True)
    config: GNBConfig = Field(default_factory=GNBConfig)
    """gNB component configuration."""


# type used to tell pydantic which ran component to chose for validation based on the type
type RANComponent = Annotated[CUCPComponent | CUUPComponent | CUComponent | DUComponent | GNBComponent, Field(discriminator="type")]


class RAN(Network5G):
    """5G Radio Access Network."""

    type: RANType | None = Field(default=RANType.OAI)
    """RAN type."""

    components: dict[str, RANComponent] = Field(default_factory=lambda: {"gnb": GNBComponent()})
    """RAN components."""


    @model_validator(mode="after")
    def validate_supported_ran_component_types(self):
        """Validate if requested 5G RAN component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_RAN_COMPONENTS)
        return self
