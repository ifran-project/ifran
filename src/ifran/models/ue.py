"""UE deployment models."""

from enum import StrEnum, auto
from typing import Any, Literal, Self

from metamodel_3gpp.models.base import StrictBaseModel
from metamodel_3gpp.models.ue import UEType
from pydantic import Field, model_validator

from ifran.models.common import Deployed5GComponent
from ifran.utils.utils import (
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
    gdbstack: int = Field(default=1)
    thread_pool: str | None = Field(default=None)
    tune_offset: float | None = Field(default=0.0)
    if_freq: int | None = Field(default=0)
    if_offset: int | None = Field(default=0)


class UERANSIMAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for UERANSIM UE."""

    protectionScheme: int | None = Field(default=0)
    homeNetworkPublicKey: str | None = Field(default="5a8d38864820197c3394b92613b20b91633cbd897119273bf8e4a6f4eec0a650")
    homeNetworkPublicKeyId: int | None = Field(default=1)
    routingIndicator: str | None = Field(default="0000")
    imeiSv: str | None = Field(default="4370816125816151")
    tunNetmask: str | None = Field(default="255.255.255.0")
    useNamespace: bool | None = Field(default=False)
    nsNamePrefix: str | None = Field(default="ueransim")
    uacAic: dict[str, Any] | None = Field(default=None)
    uacAcc: dict[str, Any] | None = Field(default=None)
    integrity: dict[str, Any] | None = Field(default=None)
    ciphering: dict[str, Any] | None = Field(default=None)
    integrityMaxRate: dict[str, Any] | None = Field(default=None)


class SRSUEAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for SRSUE."""

    freq_offset: float | None = Field(default=0)
    srate: str | float | None = Field(default="61.44e6")
    device_args: str | None = Field(default=None)
    nof_carriers: int | None = Field(default=1)
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
    master_clock_rate: str | float | None = Field(default=None)


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
            default_model=GenericAdvancedUEConfig,  # type: ignore
        )
