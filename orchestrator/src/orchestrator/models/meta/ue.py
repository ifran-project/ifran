"""User Equipment provisioning models."""

from enum import StrEnum, auto
from ipaddress import IPv6Network
from typing import Annotated, Literal

from pydantic import Field, IPvAnyAddress

from orchestrator.models.common import (
    BlueprintBaseModel,
    parse_hex_int,
    serialize_hex_int,
)
from orchestrator.models.meta.common import Category5G, Component5G
from orchestrator.models.meta.slice import DNN, BitRate, Slice


class UEType(StrEnum):
    """Supported UE types."""

    SIMULATED = auto()
    """Simulated UE."""

    REAL = auto()
    """Real UE."""


class UEImplementation(StrEnum):
    """Supported UE implementations."""

    OAI = auto()
    """OAI NR UE."""

    UERANSIM = auto()
    """UERANSIM UE."""

    SRS = auto()
    """SRS UE."""


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

    snssai: Slice | str = Field()
    """S-NSSAI associated with this PDU Session (can be a reference to a defined slice)."""

    dnn: DNN | str = Field()
    """DNN associated with this PDU Session (can be a reference to a defined DNN)."""


from pydantic import Field, field_serializer, field_validator


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

    amf: int | None = Field(efault=None, ge=0, le=0xFFFF)
    """Authentication Management Field (AMF). 16-bit value."""

    sqn: int = Field(default=0, ge=0, le=0xFFFFFFFFFFFF)
    """Sequence Number (SQN). 48-bit value."""

    authenticationMethod: AuthenticationMethod = Field(default=AuthenticationMethod.FIVE_G_AKA)
    """Authentication method used for 5GS access."""

    @field_validator("amf", "sqn", mode="before")
    @classmethod
    def normalize_hex_int(cls, value):
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
    def normalize_hex_bytes(cls, value):
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

    subscriptionIndex: int | UESubscriptionData = Field(ge=0)
    """
    Index of the UE subscription data used by this PDU Session.
    The referenced subscription provides the S-NSSAI and DNN.
    """

    ueIPv4Address: IPvAnyAddress | None = Field(default=None)
    """UE IPv4 address allocated to this PDU Session."""

    ueIPv6Prefix: IPv6Network | None = Field(default=None)
    """UE IPv6 prefix associated with this PDU Session."""

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

    supi: str = Field(pattern=r"^[0-9]{15}$")
    """UE Subscription Permanent Identifier (SUPI). For IMSI-based SUPI, this contains the IMSI digits."""

    pei: str | None = Field(default=None, pattern=r"^[0-9]{14,16}$")
    """Permanent Equipment Identifier (PEI). For an IMEI/IMEISV-based PEI, this contains the corresponding decimal identifier."""

    authenticationData: UEAuthenticationData = Field(default_factory=UEAuthenticationData)
    """UE authentication subscription data."""

    subscriptions: list[UESubscriptionData] = Field(default_factory=list)
    """S-NSSAI/DNN subscription data available to the UE."""

    pduSessions: list[UEPDUSession] = Field(default_factory=list)
    """List of UE PDU Sessions."""


class GenericUE(Component5G):
    """Base class for real and simulated UEs."""

    category: Literal[Category5G.UE] = Field(frozen=True)

    config: UEConfiguration = Field(default_factory=UEConfiguration)
    """UE configuration."""


class RealUE(GenericUE):
    """Real UE."""

    type: Literal[UEType.REAL] = Field(frozen=True)

    implementation: None = Field(default=None, frozen=True)
    """Real UE doesn't have an implementation."""


class SimulatedUE(GenericUE):
    """Simulated UE."""

    type: Literal[UEType.SIMULATED] = Field(frozen=True)

    implementation: UEImplementation = Field(default=UEImplementation.OAI)
    """Simulated UE implementation."""


type UE = Annotated[RealUE | SimulatedUE, Field(discriminator="type")]
