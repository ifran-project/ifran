"""RAN deployment models."""

from enum import StrEnum, auto
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

    cu_up_ip: IPvAnyAddress | None = Field(default=None)
    du_ip: IPvAnyAddress | None = Field(default=None)
    Num_Threads_PUSCH: int | None = Field(default=None)
    sa: int | None = Field(default=None)
    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)


class OAIAdvancedCUUPConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU-UP."""

    du_ip: IPvAnyAddress | None = Field(default=None)


class OAIAdvancedCUConfig(GenericOAIAdvancedRANConfig):
    """Advanced configuration for OAI CU."""

    du_ip: IPvAnyAddress | None = Field(default=None)
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
    preambleReceivedTargetPower: int | None = Field(default=None)
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

    drb_ciphering: str | None = Field(default=None)
    drb_integrity: str | None = Field(default=None)
    sm_dir: str | None = Field(default=None)


class OCUDUAdvancedCUCPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-CP."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    inactivity_timer: int | None = Field(default=None)


class OCUDUAdvancedCUUPConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU-UP."""

    cu_up: dict[str, Any] | None = Field(default=None)


class OCUDUAdvancedCUConfig(GenericOCUDUAdvancedRANConfig):
    """Advanced configuration for OCUDU CU."""

    cu_cp: dict[str, Any] | None = Field(default=None)
    inactivity_timer: int | None = Field(default=None)
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
    srate: float | None = Field(default=None)
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
    inactivity_timer: int | None = Field(default=None)
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
            mapping=ADVANCED_RAN_CONFIG_MAPPING,
            default_model=GenericAdvancedRANConfig,  # type: ignore
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
