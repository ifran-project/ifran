"""5G RAN meta models."""

from enum import Enum, IntEnum, StrEnum, auto
from typing import Annotated, Any, Literal, Self

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


class RANImplementation(StrEnum):
    """Supported open-source 5G RAN implementations."""

    OAI = auto()
    """OpenAirInterface RAN."""

    OCUDU = auto()
    """OCUDU RAN."""

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

    CU_CP = auto()
    """CU Control Plane (E1 split)."""

    CU_UP = auto()
    """CU User Plane (E1 split)."""


SUPPORTED_RAN_COMPONENTS: dict[RANImplementation, list[RANComponentType]] = {
    RANImplementation.OAI: [
        RANComponentType.CU,
        RANComponentType.CU_CP,
        RANComponentType.CU_UP,
        RANComponentType.DU,
        RANComponentType.GNB,
    ],
    RANImplementation.OCUDU: [
        RANComponentType.CU,
        RANComponentType.CU_CP,
        RANComponentType.CU_UP,
        RANComponentType.DU,
        RANComponentType.GNB,
    ],
    RANImplementation.UERANSIM: [
        RANComponentType.GNB,
    ],
}


class FrequencyRange(StrEnum):
    """3GPP TS 38.104 Clause 5.1: Frequency Ranges."""

    FR1 = auto() 
    """Sub-6 GHz (410 MHz - 7125 MHz)"""

    FR2 = auto() 
    """mmWave (24250 MHz - 71000 MHz)"""


class TDDPeriodicity(float, Enum):
    """
    NR TDD UL/DL configuration periodicity.

    3GPP References:
        - 3GPP TS 38.331, IE TDD-UL-DL-ConfigCommon / TDD-UL-DL-ConfigDedicated
        - 3GPP TS 38.213, TDD UL/DL timing and slot configuration

    The periodicity values correspond to the standardized values of the
    `dl-UL-TransmissionPeriodicity` field in TS 38.331, expressed in milliseconds.
    """

    MS_0_5 = 0.5
    """0.5 ms TDD periodicity."""

    MS_0_625 = 0.625
    """0.625 ms TDD periodicity."""

    MS_1 = 1.0
    """1 ms TDD periodicity."""

    MS_1_25 = 1.25
    """1.25 ms TDD periodicity."""

    MS_2 = 2.0
    """2 ms TDD periodicity."""

    MS_2_5 = 2.5
    """2.5 ms TDD periodicity."""

    MS_3 = 3.0
    """3 ms TDD periodicity."""

    MS_4 = 4.0
    """4 ms TDD periodicity."""

    MS_5 = 5.0
    """5 ms TDD periodicity."""

    MS_10 = 10.0
    """10 ms TDD periodicity."""


class SSBPeriodicity(IntEnum):
    """3GPP TS 38.331: ssb-PeriodicityServingCell IE (in milliseconds)."""

    MS_5 = 5
    """5 ms periodicity."""

    MS_10 = 10
    """10 ms periodicity."""

    MS_20 = 20
    """20 ms periodicity."""

    MS_40 = 40
    """40 ms periodicity."""

    MS_80 = 80
    """80 ms periodicity."""

    MS_160 = 160
    """160 ms periodicity."""


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


FR1_SCS = {
    SubcarrierSpacing.SCS_15KHZ,
    SubcarrierSpacing.SCS_30KHZ,
    SubcarrierSpacing.SCS_60KHZ,
}

FR2_SCS = {
    SubcarrierSpacing.SCS_60KHZ,
    SubcarrierSpacing.SCS_120KHZ,
    SubcarrierSpacing.SCS_240KHZ,
}

# Common FR1 operating bands. An explicit radio.duplex_mode remains available
# for bands not yet included in this prototype catalogue.
TDD_BANDS: frozenset[int] = frozenset({38, 40, 41, 46, 47, 48, 50, 51, 53, 77, 78, 79, 90, 96, 101, 102, 104})
FDD_BANDS: frozenset[int] = frozenset({1, 2, 3, 5, 7, 8, 12, 13, 14, 18, 20, 24, 25, 26, 28, 30, 31, 65, 66, 70, 71, 74, 85, 91, 92, 93, 94, 95, 97, 98, 99, 100})


# 3GPP TS 38.104 Table 5.2-1: Complete FDD ARFCN Offsets (N_UL - N_DL)
# Formula: (f_UL_low - f_DL_low in MHz) * 200 ARFCNs/MHz
FDD_BAND_ARFCN_OFFSETS: dict[int, int] = {
    1: -38000,   # DL 2110-2170 MHz, UL 1920-1980 MHz (-190 MHz)
    2: -16000,   # DL 1930-1990 MHz, UL 1850-1910 MHz (-80 MHz)
    3: -19000,   # DL 1805-1880 MHz, UL 1710-1785 MHz (-95 MHz)
    5: -9000,    # DL 869-894 MHz,   UL 824-849 MHz   (-45 MHz)
    7: -24000,   # DL 2620-2690 MHz, UL 2500-2570 MHz (-120 MHz)
    8: -9000,    # DL 925-960 MHz,   UL 880-915 MHz   (-45 MHz)
    12: -6000,   # DL 729-746 MHz,   UL 699-716 MHz   (-30 MHz)
    13: 6200,    # DL 746-756 MHz,   UL 777-787 MHz   (+31 MHz)
    14: 6000,    # DL 758-768 MHz,   UL 788-798 MHz   (+30 MHz)
    18: -9000,   # DL 860-875 MHz,   UL 815-830 MHz   (-45 MHz)
    20: 8200,    # DL 791-821 MHz,   UL 832-862 MHz   (+41 MHz)
    24: 20300,   # DL 1525-1559 MHz, UL 1626.5-1660.5 MHz (+101.5 MHz)
    25: -16000,  # DL 1930-1995 MHz, UL 1850-1915 MHz (-80 MHz)
    26: -9000,   # DL 859-894 MHz,   UL 814-849 MHz   (-45 MHz)
    28: -11000,  # DL 758-803 MHz,   UL 703-748 MHz   (-55 MHz)
    30: -9000,   # DL 2350-2360 MHz, UL 2305-2315 MHz (-45 MHz)
    31: -2000,   # DL 462.5-467.5 MHz, UL 452.5-457.5 MHz (-10 MHz)
    65: -38000,  # DL 2110-2200 MHz, UL 1920-2010 MHz (-190 MHz)
    66: -20000,  # DL 2110-2200 MHz, UL 1710-1780 MHz (-100 MHz)
    70: -60000,  # DL 1995-2020 MHz, UL 1695-1710 MHz (-300 MHz)
    71: 9200,    # DL 617-652 MHz,   UL 663-698 MHz   (+46 MHz)
    74: -9600,   # DL 1475-1518 MHz, UL 1427-1470 MHz (-48 MHz)
    85: -6000,   # DL 728-746 MHz,   UL 698-716 MHz   (-30 MHz)
    91: -9000,   # DL 1427-1432 MHz, UL 880-915 MHz / variable per sub-band
    92: -9000,   # DL 1432-1517 MHz, UL 880-915 MHz
    93: -9000,   # DL 1427-1432 MHz, UL 1710-1785 MHz
    94: -9000,   # DL 1432-1517 MHz, UL 1710-1785 MHz
    95: -9000,   # DL 2010-2025 MHz, UL 1710-1785 MHz
    97: -9000,   # SUL / Variable Paired Offsets
    98: -9000,   # SUL / Variable Paired Offsets
    99: -9000,   # SUL / Variable Paired Offsets
    100: -9000,  # DL 925-960 MHz, UL 880-915 MHz
}


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

    The default configuration corresponds to the commonly used
    FR1 / 30 kHz / 5 ms TDD pattern:
        7 full DL slots + 6 DL symbols
        2 full UL slots + 4 UL symbols.
    """

    periodicityMilliseconds: TDDPeriodicity = Field(default=TDDPeriodicity.MS_5)
    """TDD periodicity in milliseconds."""

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
    """NR Duplex Mode. If None, it will be chosen from the NR band (TDD takes precedence)."""

    downlinkArfcn: int = Field(default=640000, ge=0, le=3279165)
    """NR Downlink Absolute Radio Frequency Channel Number (NR-ARFCN). Max bound per TS 38.104."""

    uplinkArfcn: int | None = Field(default=None, ge=0, le=3279165)
    """NR Uplink NR-ARFCN. Required for FDD per TS 38.104. If None, it will calculated automatically."""

    pointAFrequencyArfcn: int = Field(default=620040, ge=0, le=3279165)
    """Absolute Frequency of Resource Element Point A."""

    channelBandwidthMhz: int = Field(default=40, ge=5, le=400)
    """NR Transmission Channel Bandwidth in MHz (TS 38.104)."""

    subcarrierSpacingKhz: SubcarrierSpacing = Field(default=SubcarrierSpacing.SCS_30KHZ)
    """NR Subcarrier Spacing configuration."""

    ssbArfcn: int = Field(default=621312, ge=0, le=3279165)
    """Synchronization Signal Block (SSB) NR-ARFCN positioning."""

    ssbSubcarrierSpacing: SubcarrierSpacing = Field(default=SubcarrierSpacing.SCS_30KHZ)
    """SSB Subcarrier Spacing (subCarrierSpacingCommon in TS 38.331)."""

    ssbPeriodicityMs: SSBPeriodicity = Field(default=SSBPeriodicity.MS_20)
    """SSB burst set periodicity (ssb-PeriodicityServingCell in TS 38.331)."""

    ssbPbchBlockPowerDbm: int = Field(default=-25, ge=-60, le=50)
    """SSB/PBCH block transmit power in dBm (ssb-PBCH-BlockPower in TS 38.331)."""

    prachConfigurationIndex: int = Field(default=0, ge=0, le=255)
    """PRACH Configuration Index (TS 38.211 Table 6.3.3.2-1)."""

    msg1FrequencyStartPrb: int = Field(default=0, ge=0, le=274)
    """Offset of lowest PRACH transmission channel in PRBs relative to PRB 0."""

    tddConfiguration: TDDConfiguration | None = Field(default=None)
    """TDD configuration if duplex mode is TDD."""


    def _derive_duplex_mode(self) -> None:
        """Derive duplex mode if not defined from the configured NR band."""

        if self.duplexMode is None:
            # band can support both -> tdd takes precedence
            if self.nrBand in TDD_BANDS:
                self.duplexMode = DuplexMode.TDD
            elif self.nrBand in FDD_BANDS:
                self.duplexMode = DuplexMode.FDD
            else:
                raise ValueError(f"Cannot chose duplex mode for given NR band 'n{self.nrBand}'.")


    def _validate_tdd(self) -> None:
        """Ensure 'tddConfiguration' is set when duplex mode is TDD and is None for FDD."""

        if self.duplexMode is DuplexMode.TDD:
            if self.tddConfiguration is None:
                self.tddConfiguration = TDDConfiguration()
        elif self.duplexMode is DuplexMode.FDD:  # noqa: SIM102
            if self.tddConfiguration:
                raise ValueError("'tddConfiguration' must be 'None' when duplex mode is FDD.")


    def _validate_arfcn_for_duplex_mode(self) -> None:
        """Enforce 3GPP duplex paired/unpaired ARFCN constraints."""

        if self.duplexMode is DuplexMode.FDD:
            if self.uplinkArfcn is None:
                # calculate automatically from available 3GPP fdd band offsets
                offset = FDD_BAND_ARFCN_OFFSETS.get(self.nrBand)
                if offset is None:
                    raise ValueError(f"Cannot calculate 'uplinkArfcn' for FDD NR band 'n{self.nrBand}'.")
                else:
                    self.uplinkArfcn = self.downlinkArfcn + offset

            if self.uplinkArfcn == self.downlinkArfcn:
                raise ValueError("'uplinkArfcn' and 'downlinkArfcn' must be different when duplex mode is FDD.")

        elif self.duplexMode is DuplexMode.TDD:
            if self.uplinkArfcn is None:
                self.uplinkArfcn = self.downlinkArfcn


    def _validate_scs_for_frequency_range(self) -> None:
        """Validate if SCS is valid for the selected FR."""

        valid_scs = FR1_SCS if self.frType is FrequencyRange.FR1 else FR2_SCS

        if self.subcarrierSpacingKhz not in valid_scs:
            raise ValueError(f"{self.subcarrierSpacingKhz.value}kHz SCS is not valid for {self.frType.value.upper()!r}.")


    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        """Validate provided radio configuration."""

        self._derive_duplex_mode()
        self._validate_tdd()
        self._validate_scs_for_frequency_range()
        return self


class RANComponentConfig(BlueprintBaseModel):
    """Generic RAN configuration."""

    timeZone: str = Field(default="Europe/Paris")
    """Timezone."""

    gnbId: int = Field(default=1, ge=1, le=4294967295) # 2^32 - 1
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

    du: IPvAnyAddress | str | list[MultusNetworkStatus] = Field(default="du")
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

    cu_up: IPvAnyAddress | str | list[MultusNetworkStatus] = Field(default="cu_up")
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

    cu_cp: IPvAnyAddress | str | list[MultusNetworkStatus] = Field(default="cu_cp")
    """CU-CP component to connect to (can be a reference to a defined CU-CP or CU)."""


class CUConfig(CommonCUConfig):
    """Generic CU configuration."""

    gnbCuUpId: int = Field(default=0, ge=0, le=4294967295)
    """gNB CU-UP identity."""

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

    nrCellId: int = Field(default=1, ge=1, le=4294967295)
    """NR Cell Identity."""

    physicalCellId: int = Field(default=0, ge=0, le=1007)
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

    cu_cp: IPvAnyAddress | str | list[MultusNetworkStatus] = Field(default="cu_cp")
    """CU-CP component to connect to (can be a reference to a defined CU or CU-CP)."""

    cu_up: IPvAnyAddress | str | list[MultusNetworkStatus] = Field(default="cu_up")
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


class GenericOAIAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for OAI RAN."""

   useAdditionalOptions: str | None = Field(default=None)
   gdbstack: int | None = Field(default=None)
   Asn1_verbosity: Literal["none", "info", "annoying"] | None = Field(default=None)
   log_config: dict[str, str] | None = Field(default=None)


class GenericOCUDUAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for OCUDU RAN."""

   gnb_id_bit_length: int | None = Field(default=None)
   dryrun: bool | None = Field(default=None)
   e2: dict[str, Any] | None = Field(default=None)
   remote_control: dict[str, Any] | None = Field(default=None)
   log: dict[str, Any] | None = Field(default=None)
   pcap: dict[str, Any] | None = Field(default=None)
   metrics: dict[str, Any] | None = Field(default=None)


class GenericUERANSIMAdvancedRANConfig(GenericAdvancedRANConfig):
   """Generic advanced configuration for UERANSIM RAN."""

   ignoreStreamIds: bool | None = Field(default=None)
   cellAccessType: str | None = Field(default=None)


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
   prach_msg1_FDM: int | None = Field(default=None)
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
   dmrs_TypeA_Position: int | None = Field(default=None)
   pusch_TargetSNRx10: int | None = Field(default=None)
   pucch_TargetSNRx10: int | None = Field(default=None)
   prach_dtx_threshold: int | None = Field(default=None)
   pucch0_dtx_threshold: int | None = Field(default=None)
   ofdm_offset_divisor: int | None = Field(default=None)
   local_rf: str | None = Field(default=None)
   max_pdschReferenceSignalPower: int | None = Field(default=None)
   eNB_instances: list[int] | None = Field(default=None)
   sf_extension: int | None = Field(default=None)
   rfsimulator: dict[str, Any] | None = Field(default=None)
   fhi_72: dict[str, Any] | None = Field(default=None)
   thread_pool: str | None = Field(default=None)
   channelmod: dict[str, Any] | None = Field(default=None)


class OAIAdvancedDUConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI DU."""


class OAIAdvancedGNBConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI GNB."""

    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)
    sm_dir: str | None = Field(default=None)


class OCUDUAdvancedCUCPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-CP."""

    cu_cp: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCUUPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-UP."""

    cu_up: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCUConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    cu_up: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCommonGNBConfig(GenericOCUDUAdvancedRANConfig):
   """OCUDU advanced configuration common for gNB and DU."""

   cells: dict[str, Any] | None = Field(default=None)
   qos: dict[str, Any] | None = Field(default=None)
   srbs: dict[str, Any] | None = Field(default=None)
   du: dict[str, Any] | None = Field(default=None)
   cell_cfg: dict[str, Any] | None = Field(default=None)
   ntn: dict[str, Any] | None = Field(default=None)
   custom_freq_bands: dict[str, Any] | None = Field(default=None)
   ru_ofh: dict[str, Any] | None = Field(default=None)
   ru_sdr: dict[str, Any] | None = Field(default=None)
   ru_dummy: dict[str, Any] | None = Field(default=None)
   hal: dict[str, Any] | None = Field(default=None)
   buffer_pool: dict[str, Any] | None = Field(default=None)
   expert_phy: dict[str, Any] | None = Field(default=None)
   expert_execution: dict[str, Any] | None = Field(default=None)
   test_mode: dict[str, Any] | None = Field(default=None)
   trace: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedDUConfig(OCUDUAdvancedCommonGNBConfig):
    """Advanced configuration for OCUDU DU."""

    f1ap: dict[str, Any] | None = Field(default=None)
    f1u: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedGNBConfig(OCUDUAdvancedCommonGNBConfig):
    """Advanced configuration for OCUDU GNB."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    cu_up: dict[str, Any] | None = Field(default=None)


ADVANCED_RAN_CONFIG_MAPPING: dict[RANImplementation, dict[RANComponentType, type[GenericAdvancedRANConfig]]] = {
    RANImplementation.OAI: {
        RANComponentType.CU_CP: OAIAdvancedCUCPConfig,
        RANComponentType.CU_UP: OAIAdvancedCUUPConfig,
        RANComponentType.CU: OAIAdvancedCUConfig,
        RANComponentType.DU: OAIAdvancedDUConfig,
        RANComponentType.GNB: OAIAdvancedGNBConfig,
    },
    RANImplementation.OCUDU: {
        RANComponentType.CU_CP: OCUDUAdvancedCUCPConfig,
        RANComponentType.CU_UP: OCUDUAdvancedCUUPConfig,
        RANComponentType.CU: OCUDUAdvancedCUConfig,
        RANComponentType.DU: OCUDUAdvancedDUConfig,
        RANComponentType.GNB: OCUDUAdvancedGNBConfig,
    },
    RANImplementation.UERANSIM: {
        RANComponentType.GNB: GenericUERANSIMAdvancedRANConfig,
    },
}


class GenericRANComponent(Component5G):
    """Generic RAN component."""

    category: Literal[Category5G.RAN] = Field(default=Category5G.RAN, frozen=True)

    implementation: RANImplementation | None = Field(default=None)
    """RAN component implementation."""

    type: RANComponentType = Field()
    """Core component type."""

    config: RANComponentConfig = Field(default_factory=RANComponentConfig)
    """Core component configuration."""

    advanced_config: dict[str, Any] | None = Field(default=None)
    """RAN component configuration specific to the implementation."""


    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_RAN_CONFIG_MAPPING,
            default_model=GenericAdvancedRANConfig,
        )


class CUCPComponent(GenericRANComponent):
    """Generic CU-CP component."""

    type: Literal[RANComponentType.CU_CP] = Field(frozen=True)
    config: CUCPConfig = Field(default_factory=CUCPConfig)
    """CU-CP component configuration."""


class CUUPComponent(GenericRANComponent):
    """Generic CU-UP component."""

    type: Literal[RANComponentType.CU_UP] = Field(frozen=True)
    config: CUUPConfig = Field(default_factory=CUUPConfig)
    """CU-UP component configuration."""


class CUComponent(GenericRANComponent):
    """Generic CU component."""

    type: Literal[RANComponentType.CU] = Field(frozen=True)
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
    """Generic DU component."""

    type: Literal[RANComponentType.DU] = Field(frozen=True)
    config: DUConfig = Field(default_factory=DUConfig)
    """DU component configuration."""


class GNBComponent(CommonGNBComponent):
    """Generic gNB component."""

    type: Literal[RANComponentType.GNB] = Field(frozen=True)
    config: GNBConfig = Field(default_factory=GNBConfig)
    """gNB component configuration."""


# type used to tell pydantic which ran component to chose for validation based on the type
type RANComponent = Annotated[CUCPComponent | CUUPComponent | CUComponent | DUComponent | GNBComponent, Field(discriminator="type")]


class RAN(Network5G):
    """5G Radio Access Network."""

    implementation: RANImplementation | None = Field(default=RANImplementation.OAI)
    """RAN implementation."""

    components: dict[str, RANComponent] = Field(default_factory=lambda: {"gnb": GNBComponent(type=RANComponentType.GNB)})
    """RAN components."""


    @model_validator(mode="after")
    def validate_supported_ran_component_types(self) -> Self:
        """Validate if requested 5G RAN component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_RAN_COMPONENTS)
        return self
