"""Core deployment models."""

from enum import StrEnum, auto
from typing import Any, Self

from metamodel.models.base import StrictBaseModel
from metamodel.models.core import AMFComponent, CoreComponentType
from pydantic import Field, IPvAnyAddress, model_validator

from orchestrator.models.common import Deployed5GComponent, Deployed5GNetwork
from orchestrator.models.k8s import ContainerImage


class CoreImplementation(StrEnum):
    """Supported open-source 5G core implementations."""

    OAI = auto()
    """OpenAirInterface core."""

    OPEN5GS = auto()
    """Open5GS core."""

    FREE5GC = auto()
    """Free5GC core."""


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

class GenericAdvancedCoreConfig(StrictBaseModel):
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


class DeployedCoreComponent(Deployed5GComponent):
    """5G core component deployment."""

    type: CoreComponentType = Field()
    """5G core component type."""

    implementation: CoreImplementation | None = Field(default=None)
    """5G core component implementation."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_CORE_CONFIG_MAPPING,
            default_model=GenericAdvancedCoreConfig,
        )


class CoreDatabaseParams(StrictBaseModel):
    """5G core database deployment parameters."""

    image: ContainerImage | None = Field(default=None)
    """5G core database container image."""

    is_installed: bool = Field(default=False)
    """If 5G core database is deployed or not."""

    ip: IPvAnyAddress | None = Field(default=None)
    """5G core database IP address."""

    force_database_scheduling: bool = Field(default=False)
    """If True, label will be added to ensure scheduling only on nodes with 'database' label AND 'core' label."""


class CoreDeployment(Deployed5GNetwork):
    """5G core deployment."""

    implementation: CoreImplementation = Field(default=CoreImplementation.OPEN5GS)
    """5G ore implementation."""

    components: dict[str, DeployedCoreComponent] = Field(default_factory=dict)
    """5G core Kubernetes components."""

    database_params: CoreDatabaseParams = Field(default_factory=CoreDatabaseParams)
    """5G core database parameters."""

    @model_validator(mode="after")
    def validate_supported_core_component_types(self) -> Self:
        """Validate if requested 5G core component types are available for given implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_CORE_COMPONENTS)
        return self


# model used to resolve amf references in ran components
class MergedAMF(AMFComponent, DeployedCoreComponent):
    """Merged AMF model."""
