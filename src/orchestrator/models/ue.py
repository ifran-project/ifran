"""UE deployment models."""

from enum import StrEnum, auto
from typing import Any, Literal, Self

from metamodel.models.base import StrictBaseModel
from metamodel.models.ue import UEType
from pydantic import Field, model_validator

from orchestrator.models.common import Deployed5GComponent
from orchestrator.utils.utils import (
    SerializableINIConfigDict,
    SerializableLibconfigDict,
)


class UEImplementation(StrEnum):
    """Supported implementations for conatainerized UES."""

    OAI = auto()
    """OpenAireInterface NR UE."""

    UERANSIM = auto()
    """UERANSIM UE."""

    SRSUE = auto()
    """Software Radio Systems (SRS) UE."""


class GenericAdvancedUEConfig(StrictBaseModel):
    """Generic UE advanced configuration (implementation-specific)."""


class OAIAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for OAI NR UE."""

    useAdditionalOptions: str | None = Field(default=None)
    rf_freq: int | None = Field(default=None)
    rf_offset: int | None = Field(default=None)
    ssb_start: int | None = Field(default=None)
    position0: SerializableLibconfigDict | None = Field(default=None)
    channelmod: SerializableLibconfigDict | None = Field(default=None)
    gdbstack: int | None = Field(default=None)
    thread_pool: str | None = Field(default=None)
    tune_offset: float | None = Field(default=None)
    if_freq: int | None = Field(default=None)
    if_offset: int | None = Field(default=None)


class UERANSIMAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for UERANSIM UE."""

    protectionScheme: int | None = Field(default=None)
    homeNetworkPublicKey: str | None = Field(default=None)
    homeNetworkPublicKeyId: str | None = Field(default=None)
    routingIndicator: str | None = Field(default=None)
    imeiSv: str | None = Field(default=None)
    tunNetmask: str | None = Field(default=None)
    useNamespace: bool | None = Field(default=None)
    nsNamePrefix: str | None = Field(default=None)
    uacAic: dict[str, Any] | None = Field(default=None)
    uacAcc: dict[str, Any] | None = Field(default=None)
    integrity: dict[str, Any] | None = Field(default=None)
    ciphering: dict[str, Any] | None = Field(default=None)
    integrityMaxRate: dict[str, Any] | None = Field(default=None)


class SRSUEAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for SRSUE."""

    freq_offset: float | None = Field(default=None)
    srate: str | float | None = Field(default=None)
    device_args: str | None = Field(default=None)
    nof_carriers: int | None = Field(default=None)
    max_nof_prb: int | None = Field(default=None)
    nof_prb: int | None = Field(default=None)
    rf: SerializableINIConfigDict | None = Field(default=None)
    rat_eutra: SerializableINIConfigDict | None = Field(default=None)
    pcap: SerializableINIConfigDict | None = Field(default=None)
    log: SerializableINIConfigDict | None = Field(default=None)
    usim: SerializableINIConfigDict | None = Field(default=None)
    rrc: SerializableINIConfigDict | None = Field(default=None)
    nas: SerializableINIConfigDict | None = Field(default=None)
    slicing: SerializableINIConfigDict | None = Field(default=None)
    gw: SerializableINIConfigDict | None = Field(default=None)
    gui: SerializableINIConfigDict | None = Field(default=None)
    channel_dl: SerializableINIConfigDict | None = Field(default=None)
    channel_dl_awgn: SerializableINIConfigDict | None = Field(default=None)
    channel_dl_fading: SerializableINIConfigDict | None = Field(default=None)
    channel_dl_delay: SerializableINIConfigDict | None = Field(default=None)
    channel_dl_rlf: SerializableINIConfigDict | None = Field(default=None)
    channel_dl_hst: SerializableINIConfigDict | None = Field(default=None)
    channel_ul: SerializableINIConfigDict | None = Field(default=None)
    channel_ul_awgn: SerializableINIConfigDict | None = Field(default=None)
    channel_ul_fading: SerializableINIConfigDict | None = Field(default=None)
    channel_ul_delay: SerializableINIConfigDict | None = Field(default=None)
    channel_ul_rlf: SerializableINIConfigDict | None = Field(default=None)
    channel_ul_hst: SerializableINIConfigDict | None = Field(default=None)
    phy: SerializableINIConfigDict | None = Field(default=None)
    phy_nr: SerializableINIConfigDict | None = Field(default=None)
    cfr: SerializableINIConfigDict | None = Field(default=None)
    sim: SerializableINIConfigDict | None = Field(default=None)
    general: SerializableINIConfigDict | None = Field(default=None)


ADVANCED_UE_CONFIG_MAPPING: dict[UEImplementation, dict[UEType, type[GenericAdvancedUEConfig]]] = {
    UEImplementation.OAI: {
        UEType.CONTAINERIZED: OAIAdvancedUEConfig,
    },
    UEImplementation.UERANSIM: {
        UEType.CONTAINERIZED: UERANSIMAdvancedUEConfig,
    },
    UEImplementation.SRSUE: {
        UEType.CONTAINERIZED: SRSUEAdvancedUEConfig,
    },
}


class DeployedUE(Deployed5GComponent):
    """UE deployment."""

    type: Literal[UEType.CONTAINERIZED] = Field(frozen=True)
    """UE type."""

    implementation: UEImplementation = Field(default=UEImplementation.OAI)
    """UE implementation."""

    derived_radio_config: dict[str, Any] | None = Field(default=None)
    """Automatically derived implementation-specific radio parameters."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_UE_CONFIG_MAPPING,
            default_model=GenericAdvancedUEConfig, # type: ignore
        )
