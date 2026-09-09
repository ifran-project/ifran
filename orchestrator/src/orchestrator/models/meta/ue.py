"""UE provisioning models."""

from enum import StrEnum, auto
from ipaddress import IPv4Address, IPv6Address
from typing import Any, Literal, Self

from pydantic import (
    Field,
    IPvAnyAddress,
    field_serializer,
    field_validator,
    model_validator,
)

from orchestrator.models.common import (
    BlueprintBaseModel,
    SerializableLibconfigDict,
    parse_hex_int,
    serialize_hex_int,
)
from orchestrator.models.meta.common import (
    Category5G,
    Component5G,
)
from orchestrator.models.meta.ran import RU, CommonGNBComponent
from orchestrator.models.meta.slice import DNN, BitRate, Slice


class UEType(StrEnum):
    """Supported UE types."""

    CONTAINERIZED = auto()
    """Software-based UE stack deployed as Kubernetes pod (can be simulated or real RF)."""

    COTS = auto()
    """Physical Commercial Off-The-Shelf (COTS) UE."""


class UEImplementation(StrEnum):
    """Supported implementations for conatainerized UES."""

    OAI = auto()
    """OpenAireInterface NR UE."""

    UERANSIM = auto()
    """UERANSIM UE."""

    SRS = auto()
    """Software Radio Systems (SRS) UE."""


class SSCMode(StrEnum):
    """
    Session and Service Continuity (SSC) mode.

    3GPP References:
        - 3GPP TS 23.501 clause 5.6.9
    """

    SSC_MODE_1 = auto()
    """SSC mode 1: The core network maintains the established user plane connectivity."""

    SSC_MODE_2 = auto()
    """SSC mode 2: User plane connectivity is released before establishing new connectivity."""

    SSC_MODE_3 = auto()
    """SSC mode 3: Make-before-break; new connectivity is established before releasing old."""


class AuthenticationMethod(StrEnum):
    """
    Authentication method used for 5GS access.

    3GPP References:
        - 3GPP TS 23.501 clause 5.16.2
        - 3GPP TS 33.501 clause 6
        - 3GPP TS 24.501
    """

    FIVE_G_AKA = "5G_AKA"
    """5G Authentication and Key Agreement."""

    EAP_AKA_PRIME = "EAP_AKA_PRIME"
    """Extensible Authentication Protocol-AKA'."""

    EAP_TLS = "EAP_TLS"
    """Extensible Authentication Protocol-Transport Layer Security."""


class UESubscriptionData(BlueprintBaseModel):
    """
    UE subscription data.

    Represents subscription information associated with a UE/SUPI,
    independent of an individual PDU Session.

    3GPP References:
        - 3GPP TS 23.501 clause 5.15
        - 3GPP TS 23.502
        - 3GPP TS 29.503
    """

    snssai: Slice | str = Field(default="internet")
    """S-NSSAI associated with this PDU Session (can be a reference to a defined slice)."""

    dnn: DNN | str = Field(default="internet")
    """DNN associated with this PDU Session (can be a reference to a defined DNN)."""


class UEAuthenticationData(BlueprintBaseModel):
    """
    UE authentication subscription data.

    Contains authentication parameters required for 5G Authentication
    and Key Agreement (5G-AKA) and related authentication methods.

    3GPP References:
        - 3GPP TS 33.501 clause 6
        - 3GPP TS 31.102
        - 3GPP TS 35.206
        - 3GPP TS 29.503
    """

    k: bytes = Field(default=bytes.fromhex("fec86ba6eb707ed08905757b1bb44b8f"), min_length=16, max_length=16)
    """Subscriber permanent key (K). 128-bit value."""

    opc: bytes = Field(default=bytes.fromhex("C42449363BBAD02B66D16BC975D77CC1"), min_length=16, max_length=16)
    """Operator Variant Algorithm Configuration Field (OPc). 128-bit value."""

    op: bytes | None = Field(default=None, min_length=16, max_length=16)
    """Operator Code (OP). 128-bit value."""

    amf: int = Field(default=0x8000, ge=0, le=0xFFFF)
    """Authentication Management Field (AMF). 16-bit value."""

    sqn: int = Field(default=0, ge=0, le=0xFFFFFFFFFFFF)
    """Sequence Number (SQN). 48-bit value."""

    authenticationMethod: AuthenticationMethod = Field(default=AuthenticationMethod.FIVE_G_AKA)
    """Authentication method used for 5GS access."""

    @field_validator("amf", "sqn", mode="before")
    @classmethod
    def normalize_hex_int(cls, value) -> int | Any:
        """Convert hexadecimal strings to integers."""

        return parse_hex_int(value)

    @field_serializer("amf")
    def serialize_amf(self, value: int | None) -> str | None:
        """Serialize AMF as a four-digit hexadecimal string."""

        return serialize_hex_int(value, 4)

    @field_serializer("sqn")
    def serialize_sqn(self, value: int) -> str:
        """Serialize SQN as a twelve-digit hexadecimal string."""

        return serialize_hex_int(value, 12)

    @field_validator("k", "opc", "op", mode="before")
    @classmethod
    def normalize_hex_bytes(cls, value) -> bytes | Any:
        """Convert hexadecimal strings to bytes."""

        if isinstance(value, str):
            return bytes.fromhex(value)

        return value

    @field_serializer("k", "opc", "op")
    def serialize_hex_bytes(self, value: bytes | None) -> str | None:
        """Serialize bytes as an uppercase hexadecimal string."""

        if value is None:
            return None

        return value.hex().upper()


class UEPDUSession(BlueprintBaseModel):
    """
    UE PDU Session configuration.

    Defines a UE-associated PDU Session towards a Data Network.

    3GPP References:
        - 3GPP TS 23.501 clause 5.6
        - 3GPP TS 24.501
    """

    subscriptionIndex: int = Field(ge=0, default=0)
    """
    Index of the UE subscription data used by this PDU Session.
    The referenced subscription provides the S-NSSAI and DNN.
    """

    sscMode: SSCMode = Field(default=SSCMode.SSC_MODE_1)
    """SSC mode for this PDU Session."""

    ueIPv4Address: IPv4Address | None = Field(default=None)
    """UE IPv4 address allocated to this PDU Session."""

    ueIPv6Address: IPv6Address | None = Field(default=None)
    """UE IPv6 address allocated to this PDU Session."""

    ipAllocationMethod: Literal["DYNAMIC", "STATIC"] = Field(default="DYNAMIC")
    """UE IP address allocation method."""

    sessionAmbr: BitRate | None = Field(default=None)
    """
    Session-AMBR applicable to this PDU Session.
    If omitted, the applicable value may be inherited from subscription/DNN configuration.
    """


class UEConfiguration(BlueprintBaseModel):
    """
    User Equipment (UE) configuration.

    Represents a 5G subscriber equipment profile.

    3GPP References:
        - 3GPP TS 23.003
        - 3GPP TS 23.501
        - 3GPP TS 24.501
    """

    timeZone: str = Field(default="Europe/Paris")
    """UE timezone."""

    supi: str = Field(default="001010000000100", pattern=r"^[0-9]{15}$")
    """UE Subscription Permanent Identifier (SUPI). For IMSI-based SUPI, this contains the IMSI digits."""

    pei: str | None = Field(default=None, pattern=r"^[0-9]{14,16}$")
    """Permanent Equipment Identifier (PEI). For an IMEI/IMEISV-based PEI, this contains the corresponding decimal identifier."""

    authenticationData: UEAuthenticationData = Field(default_factory=UEAuthenticationData)
    """UE authentication subscription data."""

    subscriptions: list[UESubscriptionData] = Field(default_factory=lambda: [UESubscriptionData()])
    """S-NSSAI/DNN subscription data available to the UE."""

    pduSessions: list[UEPDUSession] = Field(default_factory=lambda: [UEPDUSession()])
    """List of UE PDU Sessions."""

    ueAmbr: BitRate = Field(default=BitRate(uplink="1Gbps", downlink="1Gbps"))
    """UE AMBR."""

    gnb: tuple[IPvAnyAddress, CommonGNBComponent] | str | None = Field(default="gnb")
    """GNB/DU component to connect the UE to. Only relevant for containerized UEs."""

    ru: RU | str | None = Field(default="sim_ru")
    """RU to be used by the UE. Only relevant for containerized UEs."""


    @model_validator(mode="after")
    def validate_pdu_session_subscription_indexes(self) -> Self:
        """Ensure that PDU sessions 'subscriptionIndex' reference valid subscriptions."""

        if self.pduSessions:
            max_index = max(session.subscriptionIndex for session in self.pduSessions)

            if max_index >= len(self.subscriptions):
                raise ValueError(
                    f"UE 'pduSessions' references out of range 'subscriptionIndex' ({max_index} > {len(self.subscriptions) - 1})."
                    )

        return self


class GenericAdvancedUEConfig(BlueprintBaseModel):
    """Generic UE advanced configuration (implementation-specific)."""


class OAIAdvancedUEConfig(GenericAdvancedUEConfig):
    """Advanced configuration for OAI NR UE."""

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
    tunNetmask: str | None = Field(default=None)
    useNamespace: bool | None = Field(default=None)
    nsNamePrefix: str | None = Field(default=None)
    gnbSearchList: dict[str, Any] | None = Field(default=None)
    uacAic: dict[str, Any] | None = Field(default=None)
    uacAcc: dict[str, Any] | None = Field(default=None)
    integrity: dict[str, Any] | None = Field(default=None)
    ciphering: dict[str, Any] | None = Field(default=None)
    integrityMaxRate: dict[str, Any] | None = Field(default=None)


ADVANCED_UE_CONFIG_MAPPING: dict[UEImplementation, dict[UEType, type[GenericAdvancedUEConfig]]] = {
    UEImplementation.OAI: {
        UEType.CONTAINERIZED: OAIAdvancedUEConfig,
    },
    UEImplementation.UERANSIM: {
        UEType.CONTAINERIZED: UERANSIMAdvancedUEConfig,
    },
}


class UE(Component5G):
    """User Equipment."""

    category: Literal[Category5G.UE] = Field(default=Category5G.UE, frozen=True)

    type: UEType = Field(default=UEType.CONTAINERIZED)
    """UE type."""

    implementation: UEImplementation | None = Field(default=UEImplementation.OAI)
    """UE implementation. Only relevant for simulated UEs."""

    config: UEConfiguration = Field(default_factory=UEConfiguration)
    """UE configuration."""

    advanced_config: dict[str, Any] | None = Field(default=None)
    """RAN component configuration specific to the implementation."""

    derived_radio_config: dict[str, Any] | None = Field(default=None)
    """Automatically derived implementation-specific radio parameters. Only relevant for containerized UEs."""


    @model_validator(mode="after")
    def validate_gnb_and_ru(self) -> Self:
        """Ensure that 'gnb' and 'ru' are set for containerized UEs."""

        if self.type is UEType.CONTAINERIZED:
            if self.config.gnb is None:
                raise ValueError("'gnb' is required for containerized UE.")
            if self.config.ru is None:
                raise ValueError("'ru' is required for containerized UE.")

        return self


    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_UE_CONFIG_MAPPING,
            default_model=GenericAdvancedUEConfig,
        )
