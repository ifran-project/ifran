"""Common 5G meta models."""

from enum import StrEnum, auto
from ipaddress import IPv4Address
from typing import Any, Literal, Self

from pydantic import (
    BaseModel,
    Field,
    IPvAnyAddress,
    model_validator,
)

from orchestrator.models.common import BlueprintBaseModel


class Category5G(StrEnum):
    """Supported 5G network categories."""

    CORE = auto()
    """Core 5G network."""

    RAN = auto()
    """Radio Acess Network."""

    UE = auto()
    """User Equipment."""

    RIC = auto()
    """RAN Intelligent Controller."""


class DuplexMode(StrEnum):
    """Supported duplexing modes."""

    FDD = auto()
    """Frequency Division Duplex."""

    TDD = auto()
    """Time Division Duplex."""


class CipheringAlgorithm(StrEnum):
    """Supported New Radio Encryption Algorithms (NEA). TS 33.501."""

    NEA0 = auto()
    """Null ciphering."""

    NEA1 = auto()
    """128-bit SNOW 3G ciphering."""

    NEA2 = auto()
    """128-bit AES ciphering."""

    NEA3 = auto()
    """128-bit ZUC ciphering."""


class IntegrityAlgorithm(StrEnum):
    """Supported New Radio Integrity Algorithms (NIA). TS 33.501."""

    NIA0 = auto()
    """Null integrity protection."""

    NIA1 = auto()
    """128-bit SNOW 3G integrity."""

    NIA2 = auto()
    """128-bit AES integrity."""

    NIA3 = auto()
    """128-bit ZUC integrity."""


class SecurityAlgorithmConfiguration(BlueprintBaseModel):
    """Security algorithm preference configuration.

    Defines the ordered preference of integrity protection and
    ciphering algorithms advertised by the AMF.

    3GPP References:
        - 3GPP TS 33.501
        - 3GPP TS 24.501
    """

    integrityOrder: list[IntegrityAlgorithm] = Field(
        default_factory=lambda: [
            IntegrityAlgorithm.NIA2,
            IntegrityAlgorithm.NIA1,
            IntegrityAlgorithm.NIA0,
        ])
    """Preferred integrity protection algorithms."""

    cipheringOrder: list[CipheringAlgorithm] = Field(
        default_factory=lambda: [
            CipheringAlgorithm.NEA0,
            CipheringAlgorithm.NEA1,
            CipheringAlgorithm.NEA2,
        ])
    """Preferred ciphering algorithms."""


class TLS(BlueprintBaseModel):
    """
    Transport Layer Security (TLS) configuration.

    Defines the TLS parameters used to secure Service-Based Interface (SBI)
    communications over HTTPS.

    3GPP References:
        - 3GPP TS 29.500
        - 3GPP TS 33.501
    """

    enabled: bool = Field(default=False)
    """Enable Transport Layer Security (TLS)."""

    certificate: str | None = Field(default=None)
    """Path to the local X.509 certificate."""

    privateKey: str | None = Field( default=None)
    """Path to the local private key associated with the X.509 certificate."""


class TransportEndpoint(BlueprintBaseModel):
    """
    Transport endpoint configuration.

    Generic transport endpoint used for 5GC reference points and interfaces.

    3GPP References:
        - 3GPP TS 29.500
        - 3GPP TS 29.244
        - 3GPP TS 38.413
    """

    interfaceName: str = Field(default="eth0")
    """Network interface used to bind the transport endpoint."""

    ipv4EndPointAddress: IPvAnyAddress = Field(default=IPv4Address("0.0.0.0"))
    """IPv4 endpoint address."""

    ipv6EndPointAddress: IPvAnyAddress | None = Field(default=None)
    """IPv6 endpoint address."""

    port: int = Field(ge=1,le=65535)
    """Transport layer port number."""

    protocol: str | None = Field(default=None)
    """Protocol."""


class NGAP(TransportEndpoint):
    """
    NG Application Protocol (NGAP) transport endpoint.

    Represents the N2/NG-C control-plane endpoint between the
    NG-RAN and the AMF. NGAP is transported over SCTP.

    3GPP References:
        - 3GPP TS 38.413, "NG-RAN; NG Application Protocol (NGAP)"
        - 3GPP TS 23.501, "System architecture for the 5G System (5GS)"
        - 3GPP TS 38.401, "NG-RAN; Architecture description"
    """

    protocol: Literal["SCTP"] = Field(default="SCTP", frozen=True)

    port: int = Field(default=38412, ge=1, le=65535)
    """NGAP SCTP port.

    The IANA-registered/default SCTP port for NGAP is 38412.
    """


class PFCP(TransportEndpoint):
    """
    Packet Forwarding Control Protocol (PFCP) transport endpoint.

    Represents a PFCP endpoint used for control-plane communication
    between a control-plane network function and a user-plane
    function.

    3GPP References:
        - 3GPP TS 29.244, "Interface between the Control Plane and the User Plane Nodes"
        - 3GPP TS 23.501, "System architecture for the 5G System (5GS)"
    """
    protocol: Literal["UDP"] = Field(default="UDP", frozen=True)

    port: int = Field(default=8805, ge=1, le=65535)
    """PFCP UDP port.

    The IANA-registered/default PFCP port is 8805.
    """


class GTPUEndpoint(TransportEndpoint):
    """
    GPRS Tunnelling Protocol User Plane (GTP-U) endpoint.

    Represents a GTP-U endpoint used for user-plane tunnelling.

    3GPP References:
        - 3GPP TS 29.281, "General Packet Radio System (GPRS) Tunnelling Protocol User Plane (GTPv1-U)"
        - 3GPP TS 23.501, "System architecture for the 5G System (5GS)"
    """

    protocol: Literal["UDP"] = Field(default="UDP", frozen=True)

    port: int = Field(default=2152, ge=1, le=65535)
    """GTP-U UDP port.

    The standard GTP-U UDP port is 2152.
    """


class N6Endpoint(TransportEndpoint):
    """
    N6 reference point transport endpoint.

    Represents the IP connectivity between the UPF and a Data Network
    (DN). N6 is an IP-based reference point and does not define a
    single standardized transport protocol or port number.

    3GPP References:
        - 3GPP TS 23.501, "System architecture for the 5G System (5GS)"
        - 3GPP TS 23.502, "Procedures for the 5G System (5GS)"
    """
    protocol: None = Field(default=None, frozen=True)

    port: None = Field(default=None)
    """No standardized transport-layer port is defined for N6."""


class F1C(TransportEndpoint):
    """
    F1-C transport endpoint.

    Represents the control-plane endpoint of the F1 interface between
    a gNB-CU and a gNB-DU. F1-C uses the F1 Application Protocol
    (F1AP), transported over SCTP.

    3GPP References:
        - 3GPP TS 38.470, "NG-RAN; F1 general aspects and principles"
        - 3GPP TS 38.473, "NG-RAN; F1 Application Protocol (F1AP)"
        - 3GPP TS 38.401, "NG-RAN; Architecture description"
    """

    protocol: Literal["SCTP"] = Field(default="SCTP", frozen=True)

    port: int = Field(default=38472, ge=1, le=65535)
    """F1AP SCTP port.

    The IANA-registered/default SCTP port for F1AP is 38472.
    """


class F1U(GTPUEndpoint):
    """
    F1-U user-plane transport endpoint.

    Represents the user-plane endpoint of the F1 interface between
    a gNB-CU-UP and a gNB-DU. F1-U uses GTP-U.

    3GPP References:
        - 3GPP TS 38.470, "NG-RAN; F1 general aspects and principles"
        - 3GPP TS 38.474, "NG-RAN; F1 data transport"
        - 3GPP TS 29.281, "General Packet Radio System (GPRS) Tunnelling Protocol User Plane (GTPv1-U)"
    """

    protocol: Literal["UDP"] = Field(default="UDP", frozen=True)

    port: int = Field(default=2153, ge=1, le=65535)
    """GTP-U UDP port used for F1-U."""


class E1(TransportEndpoint):
    """
    E1 Application Protocol (E1AP) transport endpoint.

    Represents the E1 control-plane transport endpoint between the
    gNB-CU-CP and gNB-CU-UP. E1AP is transported over SCTP.

    3GPP References:
        - 3GPP TS 38.460, "NG-RAN; E1 general aspects and principles"
        - 3GPP TS 38.463, "NG-RAN; E1 Application Protocol (E1AP)"
        - 3GPP TS 38.401, "NG-RAN; Architecture description"
    """

    protocol: Literal["SCTP"] = Field(default="SCTP", frozen=True)

    port: int = Field(default=38462, ge=1, le=65535)
    """E1AP SCTP port.

    The IANA-registered/default SCTP port for E1AP is 38462.
    """


class E2(TransportEndpoint):
    """
    E2 Application Protocol (E2AP) transport endpoint.

    Represents the E2 interface transport endpoint between a
    Near-Real-Time RAN Intelligent Controller (Near-RT RIC) and an
    E2 Node, such as a gNB.

    E2AP is transported over SCTP.

    E2 is specified by the O-RAN Alliance rather than by 3GPP.
    It is therefore intentionally not described as a 3GPP reference
    point.

    References:
        - O-RAN.WG3.E2AP, "E2 Application Protocol"
        - O-RAN.WG3.E2GAP, "E2 General Aspects and Principles"
        - 3GPP TS 38.401, "NG-RAN; Architecture description"
    """

    protocol: Literal["SCTP"] = Field(default="SCTP", frozen=True)

    port: int = Field(default=36421, ge=1, le=65535)
    """E2AP SCTP port.

    The commonly used/registered E2AP SCTP port is 36421.
    """


EXPOSED_CORE_INTERFACES = ["sbi", "n2", "n3", "n4", "n9"]
EXPOSED_RAN_INTERFACES = ["e1", "e2", "f1c", "f1u", "n2", "n3"]
EXPOSED_RIC_INTERFACES = ["e2"]

EXPOSED_COMPONENT_INTERFACES = {
    Category5G.CORE: EXPOSED_CORE_INTERFACES,
    Category5G.RAN: EXPOSED_RAN_INTERFACES,
    Category5G.RIC: EXPOSED_RIC_INTERFACES,
}


class Component5G(BlueprintBaseModel):
    """Base class for generic 5G network component."""

    category: Category5G = Field()
    """Component category relative to the 5G network."""

    type: str = Field()
    """Component type in the 5G category it's in (e.g. amf, upf, gnb, ... etc)."""

    # populated by parent metamodel validator before validation if its a core or ran component
    implementation: str | None = Field(default=None)
    """Component 5G category's implementation (e.g. oai, open5gs, srsran, ... etc)."""

    config: dict[str, Any] = Field(default_factory=dict)
    """Component configuration."""

    advanced_config: dict[str, Any] | None = Field(default=None)
    """Component configuration specific to the implementation."""

    plain_text_config: str | None = Field(default=None)
    """Raw configuration file content."""


    def validate_advanced_config(self, mapping: dict, default_model: BaseModel) -> Self:
        """Validate component advanced configuration's raw dict based on what is supported in the mapping."""

        # advanced config can be none
        if not isinstance(self.advanced_config, dict):
            return self

        advanced_config_model: BaseModel = mapping.get(self.implementation, {}).get(self.type)
        if advanced_config_model:
            # use type-specific advanced config model
            self.advanced_config = advanced_config_model.model_validate(self.advanced_config)
        else:
            # use implementation advanced config model
            self.advanced_config = default_model.model_validate(self.advanced_config)

        return self


class Network5G(BlueprintBaseModel):
    """Base class for 5G network core and RAN."""

    implementation: str | None = Field(default=None)
    """5G network implementation."""

    components: dict[str, Component5G] = Field(default_factory=dict)
    """5G network components."""


    @model_validator(mode="after")
    def populate_component_implementation(self) -> Self:
        """Populate 5G network component implementation after validation."""

        if self.implementation: # if network implementation is None, each component should define its implementation
            for component in self.components.values():
                if component.implementation is None:
                    component.implementation = self.implementation
        return self


    def validate_supported_component_types(self, supported: dict) -> Self:
        """Validate if requested 5G network component types are available for given implementation."""

        for name, component in self.components.items():
            if component.type not in supported[self.implementation]:
                raise ValueError(f"Requested component {name!r} of type {component.type!r} is not supported in {self.implementation!r} implementation.")
        return self

