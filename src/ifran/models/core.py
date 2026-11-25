"""Core deployment models."""

from enum import StrEnum, auto
from typing import Any, Self

from metamodel_3gpp.models.base import StrictBaseModel
from metamodel_3gpp.models.core import AMFComponent, CoreComponentType
from pydantic import Field, IPvAnyAddress, model_validator

from ifran.models.common import Deployed5GComponent, Deployed5GNetwork
from ifran.models.k8s import ContainerImage


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
    http_version: int = Field(default=2)
    nfs: dict[str, Any] | None = Field(default=None)


class GenericOpen5GSAdvancedCoreConfig(GenericAdvancedCoreConfig):
    """Generic advanced configuration for Open5GS core."""

    logger: dict[str, Any] | None = Field(default=None)
    global_config: dict[str, Any] | None = Field(default=None)
    sslkeylogfile: str = Field(default="/var/log/open5gs/tls/amf-server-sslkeylog.log")
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
    relative_capacity: int = Field(default=30)
    statistics_timer_interval: int = Field(default=20)
    emergency_support: bool = Field(default=False)


class OAIAdvancedSMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI SMF."""

    support_features: dict[str, str] | None = Field(default=None)
    ue_mtu: int = Field(default=1500)
    upfs: dict[str, Any] | None = Field(default=None)
    ue_dns: dict[str, Any] | None = Field(default=None)


class OAIAdvancedUPFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UPF."""

    support_features: dict[str, str] | None = Field(default=None)
    remote_n6_gw: str = Field(default="127.0.0.1")


class OAIAdvancedPCFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI PCF."""

    database: dict[str, Any] | None = Field(default=None)
    local_policy: dict[str, str] | None = Field(default=None)
    enable_policy_provisioning_api: str = Field(default="no")


class OAIAdvancedNSSFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI NSSF."""

    slice_config_path: str = Field(default="/openair-nssf/etc/nssf_slice_config.yaml")


class OAIAdvancedLMFConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI LMF."""

    http_threads_count: int = Field(default=8)
    gnb_id_bits_count: int = Field(default=28)
    num_gnb: int = Field(default=1)
    trp_info_wait_ms: int = Field(default=10000)
    positioning_wait_ms: int = Field(default=10000)
    measurement_wait_ms: int = Field(default=10000)
    support_features: dict[str, str] | None = Field(default=None)


class OAIAdvancedUDRConfig(GenericOAIAdvancedCoreConfig):
    """Advanced configuration for OAI UDR."""

    database: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedAMFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS AMF."""

    metrics: dict[str, Any] | None = Field(default=None)
    time: dict[str, Any] | None = Field(default=None)
    access_control: dict[str, Any] | None = Field(default=None)
    relative_capacity: int = Field(default=30)


class Open5GSAdvancedNRFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS NRF."""

    db_uri: str = Field(default="mongodb://test:test@open5gs-database/open5gs?authSource=admin")


class Open5GSAdvancedSCPConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS SCP."""

    db_uri: str = Field(default="mongodb://test:test@open5gs-database/open5gs?authSource=admin")
    info: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedSMFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS SMF."""

    metrics: dict[str, Any] | None = Field(default=None)
    info: dict[str, Any] | None = Field(default=None)
    pfcp_client: dict[str, Any] | None = Field(default=None)
    gtpc: dict[str, Any] | None = Field(default=None)
    gtpu: dict[str, Any] | None = Field(default=None)
    dns: dict[str, Any] | None = Field(default=None)
    mtu: int = Field(default=1400)
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

    db_uri: str = Field(default="mongodb://test:test@open5gs-database/open5gs?authSource=admin")
    qos_profiles: dict[str, Any] | None = Field(default=None)
    policy: dict[str, Any] | None = Field(default=None)


class Open5GSAdvancedUDRConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS UDR."""

    db_uri: str = Field(default="mongodb://test:test@open5gs-database/open5gs?authSource=admin")


class Open5GSAdvancedUPFConfig(GenericOpen5GSAdvancedCoreConfig):
    """Advanced configuration for Open5GS UPF."""

    metrics: dict[str, Any] | None = Field(default=None)
    pfcp_client: dict[str, Any] | None = Field(default=None)
    gtpu_client: dict[str, Any] | None = Field(default=None)
    teid_range_indication: int | None = Field(default=None)
    teid_range: int | None = Field(default=None)
    network_instance: str | None = Field(default=None)
    source_interface: int | None = Field(default=None)


class Free5GCAdvancedAMFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC AMF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    ngapIE: dict[str, Any] | None = Field(default=None)
    nasIE: dict[str, Any] | None = Field(default=None)
    t3502Value: int = Field(default=720)
    t3512Value: int = Field(default=3600)
    non3gppDeregTimerValue: int = Field(default=3240)
    t3513: dict[str, Any] | None = Field(default=None)
    t3522: dict[str, Any] | None = Field(default=None)
    t3550: dict[str, Any] | None = Field(default=None)
    t3555: dict[str, Any] | None = Field(default=None)
    t3560: dict[str, Any] | None = Field(default=None)
    t3565: dict[str, Any] | None = Field(default=None)
    t3570: dict[str, Any] | None = Field(default=None)
    locality: str = Field(default="area1")
    sctp: dict[str, Any] | None = Field(default=None)
    defaultUECtxReq: bool = Field(default=False)
    ngapWorkerPoolSize: int = Field(default=0)
    ngapTaskBufferSize: int = Field(default=4096)


class Free5GCAdvancedAUSFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC AUSF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    groupId: str = Field(default="ausfGroup001")
    eapAkaSupiImsiPrefix: bool = Field(default=False)


class Free5GCAdvancedBSFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC BSF."""

    mongodb_name: str = Field(default="free5gc")
    mongodb_url: str = Field(default="mongodb://test:test@free5gc-database/?authSource=admin")
    metrics: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedCHFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC CHF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    mongodb_name: str = Field(default="free5gc")
    mongodb_url: str = Field(default="mongodb://test:test@free5gc-database/?authSource=admin")
    quotaValidityTime: int = Field(default=10000)
    volumeLimit: int = Field(default=50000)
    volumeLimitPDU: int = Field(default=10000)
    volumeThresholdRate: float = Field(default=0.8)
    cgf: dict[str, Any] | None = Field(default=None)
    abmfDiameter: dict[str, Any] | None = Field(default=None)
    rfDiameter: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedNEFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC NEF."""

    serviceList: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedNRFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC NRF."""

    MongoDBName: str = Field(default="free5gc")
    MongoDBUrl: str = Field(default="mongodb://test:test@free5gc-database/?authSource=admin")
    rootcert: dict[str, Any] | None = Field(default=None)
    oauth: bool = Field(default=False)
    serviceNameList: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedNSSFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC NSSF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedPCFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC PCF."""

    timeFormat: str = Field(default="2019-01-02 15:04:05")
    defaultBdtRefId: str = Field(default="BdtPolicyId-")
    bsf_enable: bool = Field(default=True)
    serviceList: dict[str, Any] | None = Field(default=None)
    mongodb_name: str = Field(default="free5gc")
    mongodb_url: str = Field(default="mongodb://test:test@free5gc-database/?authSource=admin")
    locality: str = Field(default="area1")


class Free5GCAdvancedSMFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC SMF."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    dns: dict[str, Any] | None = Field(default=None)
    locality: str = Field(default="area1")
    assocFailAlertInterval: str = Field(default="10s")
    assocFailRetryInterval: str = Field(default="30s")
    heartbeatInterval: str = Field(default="10s")
    userplaneInformation: dict[str, Any] | None = Field(default=None)
    links: dict[str, Any] | None = Field(default=None)
    t3591: dict[str, Any] | None = Field(default=None)
    t3592: dict[str, Any] | None = Field(default=None)
    urrPeriod: int = Field(default=30)
    urrThreshold: int = Field(default=500000)
    requestedUnit: int = Field(default=1000)


class Free5GCAdvancedUDMConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UDM."""

    serviceNameList: dict[str, Any] | None = Field(default=None)
    SuciProfile: dict[str, Any] | None = Field(default=None)


class Free5GCAdvancedUDRConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UDR."""

    mongodb_name: str = Field(default="free5gc")
    mongodb_url: str = Field(default="mongodb://test:test@free5gc-database/?authSource=admin")
    dbConnectorType: str = Field(default="mongodb")


class Free5GCAdvancedUPFConfig(GenericFree5GCAdvancedCoreConfig):
    """Advanced configuration for Free5GC UPF."""

    version: str = Field(default="1.0.3")
    description: str = Field(default="UPF initial local configuration")
    retransTimeout: str = Field(default="1s")
    maxRetrans: int = Field(default=3)
    gtpu: dict[str, Any] | None = Field(default=None)


GENERIC_ADVANCED_CORE_CONFIGS: dict[CoreImplementation, type[GenericAdvancedCoreConfig]] = {
    CoreImplementation.OAI: GenericOAIAdvancedCoreConfig,
    CoreImplementation.OPEN5GS: GenericOpen5GSAdvancedCoreConfig,
    CoreImplementation.FREE5GC: GenericFree5GCAdvancedCoreConfig,
}

VALIDATED_ADVANCED_CORE_CONFIGS: dict[CoreImplementation, dict[CoreComponentType, type[GenericAdvancedCoreConfig]]] = {
    CoreImplementation.OAI: {
        CoreComponentType.AMF: OAIAdvancedAMFConfig,
        CoreComponentType.SMF: OAIAdvancedSMFConfig,
        CoreComponentType.UPF: OAIAdvancedUPFConfig,
        CoreComponentType.PCF: OAIAdvancedPCFConfig,
        CoreComponentType.NSSF: OAIAdvancedNSSFConfig,
        CoreComponentType.LMF: OAIAdvancedLMFConfig,
        CoreComponentType.UDR: OAIAdvancedUDRConfig,
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
        CoreComponentType.NSSF: Free5GCAdvancedNSSFConfig,
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
            validated=VALIDATED_ADVANCED_CORE_CONFIGS,
            generic=GENERIC_ADVANCED_CORE_CONFIGS,
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
    """5G core implementation."""

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
