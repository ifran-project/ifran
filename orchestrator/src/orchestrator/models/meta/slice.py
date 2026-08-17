"""Slice meta models."""

import re
from enum import StrEnum, auto
from ipaddress import IPv4Network

from pydantic import Field, IPvAnyNetwork, field_serializer, field_validator

from orchestrator.models.common import (
    BlueprintBaseModel,
    parse_hex_int,
    serialize_hex_int,
)


class PreemptionCapability(StrEnum):
    """
    Allocation and Retention Priority (ARP) pre-emption capability.

    Indicates whether a QoS Flow may trigger pre-emption of another
    QoS Flow with lower priority.

    3GPP References:
        - 3GPP TS 23.501 clause 5.7.2.2
        - 3GPP TS 23.503
    """

    NOT_PREEMPT = "NOT_PREEMPT"
    """The QoS Flow shall not trigger pre-emption of another QoS Flow."""

    MAY_PREEMPT = "MAY_PREEMPT"
    """The QoS Flow may trigger pre-emption of another QoS Flow."""


class PreemptionVulnerability(StrEnum):
    """
    Allocation and Retention Priority (ARP) pre-emption vulnerability.

    Indicates whether a QoS Flow may be pre-empted by another QoS Flow
    with higher priority.

    3GPP References:
        - 3GPP TS 23.501 clause 5.7.2.2
        - 3GPP TS 23.503
    """

    NOT_PREEMPTABLE = "NOT_PREEMPTABLE"
    """The QoS Flow shall not be pre-empted."""

    PREEMPTABLE = "PREEMPTABLE"
    """The QoS Flow may be pre-empted."""


class PDUSessionType(StrEnum):
    """
    PDU Session Type.

    Defines the type of PDU Session established between the UE
    and the Data Network.

    3GPP References:
        - 3GPP TS 23.501 clause 5.6.10
        - 3GPP TS 24.501
    """

    IPV4 = auto()
    """IPv4 PDU Session Type."""

    IPV6 = auto()
    """IPv6 PDU Session Type."""

    IPV4V6 = auto()
    """IPv4v6 PDU Session Type."""

    ETHERNET = auto()
    """Ethernet PDU Session Type."""

    UNSTRUCTURED = auto()
    """Unstructured PDU Session Type."""


class BitRate(BlueprintBaseModel):
    """
    Bit Rate values.

    Represents uplink and downlink bit rates used in QoS profiles.

    3GPP References:
        - 3GPP TS 23.501 clause 5.7
        - 3GPP TS 23.503
    """

    uplink: int = Field(ge=0, default=200_000_000)
    """Uplink bitrate in bits per second."""

    downlink: int = Field(ge=0, default=200_000_000)
    """Downlink bitrate in bits per second."""


    @field_validator("uplink", "downlink", mode="before")
    @classmethod
    def parse_bitrate(cls, value: int | str) -> int:
        """Convert a bitrate string to integer bits per second."""

        if isinstance(value, int):
            return value

        if not isinstance(value, str):
            raise TypeError("Bitrate must be an integer or a string with a unit.")

        value = value.strip()

        match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(bps|Kbps|Mbps|Gbps)", value)

        if not match:
            raise ValueError("Invalid bitrate. Expected a value like: '500Kbps', '100Mbps', or '1Gbps'.")

        number = float(match.group(1))
        unit = match.group(2)

        multiplier = {
            "bps": 1,
            "Kbps": 1_000,
            "Mbps": 1_000_000,
            "Gbps": 1_000_000_000,
        }[unit]

        return int(number * multiplier)


    @field_serializer("uplink", "downlink")
    def serialize_bitrate(self, value: int) -> str:
        """Serialize integer bits per second to a human-readable bitrate."""

        if value % 1_000_000_000 == 0:
            return f"{value // 1_000_000_000}Gbps"

        if value % 1_000_000 == 0:
            return f"{value // 1_000_000}Mbps"

        if value % 1_000 == 0:
            return f"{value // 1_000}Kbps"

        return f"{value}bps"


class ARP(BlueprintBaseModel):
    """
    Allocation and Retention Priority (ARP).

    Defines QoS resource allocation priority and pre-emption
    behaviour.

    3GPP References:
        - 3GPP TS 23.501 clause 5.7.2.2
        - 3GPP TS 23.503
    """

    priorityLevel: int = Field(default=1, ge=1, le=15)
    """ARP priority level (1 to 15)."""

    preemptionCapability: PreemptionCapability = Field(default=PreemptionCapability.NOT_PREEMPT)
    """ARP pre-emption capability."""

    preemptionVulnerability: PreemptionVulnerability = Field(default=PreemptionVulnerability.PREEMPTABLE)
    """ARP pre-emption vulnerability."""


class QoSFlow(BlueprintBaseModel):
    """
    QoS Flow profile.

    Defines QoS parameters associated with a QoS Flow.

    3GPP References:
        - 3GPP TS 23.501 clause 5.7
        - 3GPP TS 24.501
    """

    qfi: int = Field(default=1, ge=1, le=63)
    """QoS Flow Identifier (QFI)."""

    fiveQI: int = Field(default=9, ge=1, le=255)
    """5G QoS Identifier (5QI)."""

    arp: ARP = Field(default_factory=ARP)
    """Allocation and Retention Priority."""

    guaranteedBitRate: BitRate | None = Field(default=None)
    """Guaranteed Bit Rate (GBR)."""

    maximumBitRate: BitRate | None = Field(default=None)
    """Maximum Bit Rate (MBR)."""


class DNN(BlueprintBaseModel):
    """
    Data Network Name (DNN).

    Identifies a Data Network accessed through a PDU Session.

    3GPP References:
        - 3GPP TS 23.003 clause 9
        - 3GPP TS 23.501 clause 5.6
    """

    name: str | None = Field(default="internet")
    """Data Network Name."""

    pduSessionType: PDUSessionType = Field(default=PDUSessionType.IPV4)
    """PDU Session Type."""

    ipv4Network: IPvAnyNetwork = Field(default=IPv4Network("11.1.1.0/24"))
    """IPv4 address pool associated with the DNN."""

    ipv6Network: IPvAnyNetwork | None = Field(default=None)
    """IPv6 address pool associated with the DNN."""

    aggregateMaximumBitRate: BitRate = Field(default_factory=BitRate)
    """Aggregate Maximum Bit Rate (AMBR)."""

    qosFlows: list[QoSFlow] = Field(default_factory=lambda: [QoSFlow()])
    """QoS Flows configured for this DNN."""


class SNSSAI(BlueprintBaseModel):
    """
    Single Network Slice Selection Assistance Information (S-NSSAI).

    S-NSSAI identifies a Network Slice.

    3GPP References:
        - 3GPP TS 23.003 clause 28.4
        - 3GPP TS 23.501 clause 5.15
    """

    sst: int = Field(default=1, ge=0, le=255)
    """Slice/Service Type (SST) (0 to 255)."""

    sd: int | None = Field(default=None, ge=0, le=0xFFFFFF)
    """Slice Differentiator (SD) in hex format (000001 to FFFFFF)."""


    @field_validator("sd", mode="before")
    @classmethod
    def normalize_sd(cls, value):
        """Convert SD hexadecimal strings to integers."""

        return parse_hex_int(value)

    @field_serializer("sd")
    def serialize_sd(self, value: int | None) -> str | None:
        """Serialize SD as a six-digit hexadecimal string."""

        return serialize_hex_int(value, 6)


class Slice(SNSSAI):
    """
    Network Slice deployment configuration.

    Extends S-NSSAI with deployment-specific Data Network
    configuration.
    """

    # populated by parent model (metamodel)
    name: str | None = Field(default="internet")
    """Slice name."""

    dnns: dict[str, DNN] = Field(default_factory=lambda: {"internet": DNN()})
    """DNNs associated with this Slice."""


    @field_validator("dnns", mode="before")
    @classmethod
    def populate_dnn_names(cls, value):
        """Populate dnn names with dnns dict keys before validation."""

        if isinstance(value, dict):
            for dnn_name, dnn_data in value.items():
                if isinstance(dnn_data, dict):
                    dnn_data["name"] = dnn_name
                value[dnn_name] = dnn_data

        return value
