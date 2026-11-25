"""RAN deployment models."""

from enum import StrEnum, auto
from ipaddress import IPv4Address
from typing import Any, Literal, Self

from metamodel_3gpp.models.base import StrictBaseModel
from metamodel_3gpp.models.ran import DUComponent, GNBComponent, RANComponentType
from pydantic import Field, IPvAnyAddress, model_validator

from ifran.models.common import Deployed5GComponent, Deployed5GNetwork


class RANImplementation(StrEnum):
    """Supported open-source 5G RAN implementations."""

    OAI = auto()
    """OpenAirInterface RAN."""

    OCUDU = auto()
    """OCUDU RAN."""

    UERANSIM = auto()
    """UERANSIM."""


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


class GenericAdvancedRANConfig(StrictBaseModel):
    """Generic 5G RAN advanced configuration (implementation-specific)."""


class GenericOAIAdvancedRANConfig(GenericAdvancedRANConfig):
    """Generic advanced configuration for OAI RAN."""

    useAdditionalOptions: str | None = Field(default=None)
    gdbstack: int = Field(default=1)
    Asn1_verbosity: Literal["none", "info", "annoying"] = Field(default="none")
    log_config: dict[str, str] | None = Field(default=None)
    sm_dir: str = Field(default="/usr/local/lib/flexric/")


class GenericOCUDUAdvancedRANConfig(GenericAdvancedRANConfig):
    """Generic advanced configuration for OCUDU RAN."""

    gnb_id_bit_length: int = Field(default=32)
    dryrun: bool = Field(default=False)
    e2: dict[str, Any] | None = Field(default=None)
    remote_control: dict[str, Any] | None = Field(default=None)
    log: dict[str, Any] | None = Field(default=None)
    pcap: dict[str, Any] | None = Field(default=None)
    metrics: dict[str, Any] | None = Field(default=None)


class GenericUERANSIMAdvancedRANConfig(GenericAdvancedRANConfig):
    """Generic advanced configuration for UERANSIM RAN."""

    ignoreStreamIds: bool = Field(default=True)
    cellAccessType: str = Field(default="nr")


class OAIAdvancedCUCPConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU-CP."""

    cu_up_ip: IPvAnyAddress = Field(default=IPv4Address("0.0.0.0"))
    du_ip: IPvAnyAddress = Field(default=IPv4Address("0.0.0.0"))
    Num_Threads_PUSCH: int = Field(default=8)
    sa: int = Field(default=1)
    drb_ciphering: str = Field(default="yes")
    drb_integrity: str = Field(default="no")


class OAIAdvancedCUUPConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU-UP."""

    du_ip: IPvAnyAddress = Field(default=IPv4Address("0.0.0.0"))


class OAIAdvancedCUConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU."""

    du_ip: IPvAnyAddress = Field(default=IPv4Address("0.0.0.0"))
    drb_ciphering: str = Field(default="yes")
    drb_integrity: str = Field(default="no")


class OAIAdvancedCommonGNBConfig(GenericOAIAdvancedRANConfig):
    """OAI advanced configuration common for gNB and DU."""

    min_rxtxtime: int = Field(default=6)
    dl_offstToCarrier: int = Field(default=0)
    initialDLBWPlocationAndBandwidth: int | None = Field(default=None)
    initialDLBWPsubcarrierSpacing: int = Field(default=1)
    initialDLBWPcontrolResourceSetZero: int = Field(default=11)
    initialDLBWPsearchSpaceZero: int = Field(default=0)
    ul_offstToCarrier: int = Field(default=0)
    pMax: int = Field(default=20)
    initialULBWPlocationAndBandwidth: int | None = Field(default=None)
    prach_msg1_FDM: int = Field(default=0)
    zeroCorrelationZoneConfig: int = Field(default=12)
    preambleReceivedTargetPower: int = Field(default=-104)
    preambleTransMax: int = Field(default=6)
    powerRampingStep: int = Field(default=1)
    ssb_perRACH_OccasionAndCB_PreamblesPerSSB_PR: int = Field(default=4)
    ssb_perRACH_OccasionAndCB_PreamblesPerSSB: int = Field(default=15)
    ra_ContentionResolutionTimer: int = Field(default=7)
    rsrp_ThresholdSSB: int = Field(default=19)
    prach_RootSequenceIndex_PR: int = Field(default=2)
    prach_RootSequenceIndex: int = Field(default=1)
    restrictedSetConfig: int = Field(default=0)
    msg3_DeltaPreamble: int = Field(default=1)
    p0_NominalWithGrant: int = Field(default=-90)
    pucchGroupHopping: int = Field(default=0)
    hoppingId: int = Field(default=40)
    p0_nominal: int = Field(default=-90)
    ssb_PositionsInBurst_Bitmap: int = Field(default=1)
    dmrs_TypeA_Position: int = Field(default=0)
    pusch_TargetSNRx10: int = Field(default=200)
    pucch_TargetSNRx10: int = Field(default=200)
    prach_dtx_threshold: int = Field(default=200)
    pucch0_dtx_threshold: int = Field(default=150)
    ofdm_offset_divisor: int = Field(default=8)
    local_rf: str = Field(default="yes")
    max_pdschReferenceSignalPower: int = Field(default=-27)
    eNB_instances: list[int] = Field(default_factory=lambda: [0])
    sf_extension: int = Field(default=0)
    tr_preference: str | None = Field(default=None)
    num_tp_cores: int | None = Field(default=None)
    rxfh_core_id: int | None = Field(default=None)
    txfh_core_id: int | None = Field(default=None)
    tp_cores: list[int] | None = Field(default=None)
    nr_flag: int | None = Field(default=None)
    sl_ahead: int | None = Field(default=None)
    local_if_name: str | None = Field(default=None)
    remote_address: IPvAnyAddress | None = Field(default=None)
    local_address: IPvAnyAddress | None = Field(default=None)
    local_portc: int | None = Field(default=None)
    remote_portc: int | None = Field(default=None)
    local_portd: int | None = Field(default=None)
    remote_portd: int | None = Field(default=None)
    rfsimulator: dict[str, Any] | None = Field(default=None)
    fhi_72: dict[str, Any] | None = Field(default=None)
    thread_pool: str | None = Field(default=None)
    channelmod: dict[str, Any] | None = Field(default=None)

class OAIAdvancedDUConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI DU."""


class OAIAdvancedGNBConfig(OAIAdvancedCommonGNBConfig):
    """Advanced configuration for OAI GNB."""

    drb_ciphering: str = Field(default="yes")
    drb_integrity: str = Field(default="no")


class OCUDUAdvancedCUCPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-CP."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    inactivity_timer: int = Field(default=120)


class OCUDUAdvancedCUUPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-UP."""

    cu_up: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCUConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    inactivity_timer: int = Field(default=120)
    cu_up: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCommonGNBConfig(GenericOCUDUAdvancedRANConfig):
    """OCUDU advanced configuration common for gNB and DU."""

    cells: dict[str, Any] | None = Field(default=None)
    qos: dict[str, Any] | None = Field(default=None)
    srbs: dict[str, Any] | None = Field(default=None)
    du: dict[str, Any] | None = Field(default=None)
    cell_cfg: dict[str, Any] | None = Field(default=None)
    pdcch: dict[str, Any] | None = Field(default=None)
    pdsch: dict[str, Any] | None = Field(default=None)
    pusch: dict[str, Any] | None = Field(default=None)
    pucch: dict[str, Any] | None = Field(default=None)
    prach: dict[str, Any] | None = Field(default=None)
    csi: dict[str, Any] | None = Field(default=None)
    ntn: dict[str, Any] | None = Field(default=None)
    custom_freq_bands: dict[str, Any] | None = Field(default=None)
    ru_ofh: dict[str, Any] | None = Field(default=None)
    ru_sdr: dict[str, Any] | None = Field(default=None)
    device_args: str | None = Field(default=None)
    ue_ip: IPvAnyAddress | None = Field(default=None)
    srate: float = Field(default=61.44)
    base_srate: str | float | None = Field(default=None)
    master_clock_rate: str | float | None = Field(default=None)
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
    inactivity_timer: int = Field(default=120)
    cu_up: dict[str, Any] | None = Field(default=None)


GENERIC_ADVANCED_CORE_CONFIGS: dict[RANImplementation, type[GenericAdvancedRANConfig]] = {
    RANImplementation.OAI: GenericOAIAdvancedRANConfig,
    RANImplementation.OCUDU: GenericOCUDUAdvancedRANConfig,
    RANImplementation.UERANSIM: GenericUERANSIMAdvancedRANConfig,
}

VALIDATED_ADVANCED_RAN_CONFIGS: dict[RANImplementation, dict[RANComponentType, type[GenericAdvancedRANConfig]]] = {
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


class DeployedRANComponent(Deployed5GComponent):
    """5G RAN component deployment."""

    type: RANComponentType = Field()
    """RAN component type."""

    implementation: RANImplementation | None = Field(default=None)
    """RAN component implementation."""

    derived_radio_config: dict[str, Any] | None = Field(default=None)
    """Automatically derived implementation-specific radio parameters."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            validated=VALIDATED_ADVANCED_RAN_CONFIGS,
            generic=GENERIC_ADVANCED_CORE_CONFIGS,
        )


class RANDeployment(Deployed5GNetwork):
    """5G RAN deployment."""

    implementation: RANImplementation = Field(default=RANImplementation.OAI)
    """RAN implementation."""

    components: dict[str, DeployedRANComponent] = Field(default_factory=dict)
    """5G RAN Kubernetes components."""

    @model_validator(mode="after")
    def validate_supported_ran_component_types(self) -> Self:
        """Validate if requested 5G RAN component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_RAN_COMPONENTS)
        return self


class UEReferencedGNB(GNBComponent, DeployedRANComponent):
    """Model for gNB components referenced by a UE in simulated RAN."""

    gnb_ip: IPvAnyAddress | None = Field(default=None)
    """IP of referenced gNB/DU component."""


class UEReferencedDU(DUComponent, DeployedRANComponent):
    """Model for DU components referenced by a UE in simulated RAN."""

    gnb_ip: IPvAnyAddress | None = Field(default=None)
    """IP of referenced gNB/DU component."""
