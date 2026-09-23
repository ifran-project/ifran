"""Radio Unit provisioning models."""

from enum import StrEnum, auto
from typing import Literal

from pydantic import Field, model_validator

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.meta.common import DuplexMode


class RUType(StrEnum):
    """Supported Radio Unit vendor types."""

    SIMULATED = auto()
    """Simulated Radio Unit."""

    USRP = auto()
    """Ettus/USRP Radio Unit."""

    AW2S = auto()
    """AW2S Radio Unit."""

    BENETEL = auto()
    """Benetel Radio Unit."""

    LITEON = auto()
    """Liteon Radio Unit."""


class USRPModel(StrEnum):
    """Supported Ettus/USRP models."""

    B210 = auto()
    """USRP B210 model."""

    B205 = auto()
    """USRP B205 model."""

    N300 = auto()
    """USRP N300 model."""

    N320 = auto()
    """USRP N320 model."""


class AW2SModel(StrEnum):
    """Supported AW2S models."""

    JAGUAR = auto()
    """AW2S Jaguar model."""

    PANTHER = auto()
    """AW2S Panther model."""


class BenetelModel(StrEnum):
    """Supported Benetel models."""

    RAN550 = auto()
    """Benetel RAN550 model."""

    RAN650 = auto()
    """Benetel RAN650 model."""


class LiteonModel(StrEnum):
    """Supported Liteon models."""

    FLEXFI = auto()
    """Liteon FlexFi model."""


# types used to tell pydantic to validate the correct RU model based on its type
type RUModel = USRPModel | AW2SModel | BenetelModel | LiteonModel


class RUCapabilities(BlueprintBaseModel):
    """Radio Unit hardware capabilities."""

    max_bw_mhz: float = Field(gt=0)
    """Maximum supported bandwidth per channel (MHz)."""

    min_freq_mhz: float = Field(gt=0)
    """Minimum supported RF frequency (MHz)."""

    max_freq_mhz: float = Field(gt=0)
    """Maximum supported RF frequency (MHz)."""

    num_tx_antennas: int = Field(ge=1)
    """Number of transmit antenna ports."""

    num_rx_antennas: int = Field(ge=1)
    """Number of receive antenna ports."""

    duplex_modes: list[DuplexMode] = Field()
    """Supported duplexing modes."""


# Radio Unit catalogs
USRP_CATALOG: dict[USRPModel, RUCapabilities] = {
    USRPModel.B205: RUCapabilities(
        max_bw_mhz=56,
        min_freq_mhz=70,
        max_freq_mhz=6000,
        num_tx_antennas=1,
        num_rx_antennas=1,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
    USRPModel.B210: RUCapabilities(
        max_bw_mhz=56,
        min_freq_mhz=70,
        max_freq_mhz=6000,
        num_tx_antennas=2,
        num_rx_antennas=2,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
    USRPModel.N300: RUCapabilities(
        max_bw_mhz=100,
        min_freq_mhz=10,
        max_freq_mhz=6000,
        num_tx_antennas=2,
        num_rx_antennas=2,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
    USRPModel.N320: RUCapabilities(
        max_bw_mhz=200,
        min_freq_mhz=3,
        max_freq_mhz=6000,
        num_tx_antennas=2,
        num_rx_antennas=2,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
}

AW2S_CATALOG: dict[AW2SModel, RUCapabilities] = {
    AW2SModel.JAGUAR: RUCapabilities(
        max_bw_mhz=50,
        min_freq_mhz=600,
        max_freq_mhz=3800,
        num_tx_antennas=2,
        num_rx_antennas=2,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
    AW2SModel.PANTHER: RUCapabilities(
        max_bw_mhz=100,
        min_freq_mhz=600,
        max_freq_mhz=4000,
        num_tx_antennas=4,
        num_rx_antennas=4,
        duplex_modes=[DuplexMode.FDD, DuplexMode.TDD],
    ),
}

BENETEL_CATALOG: dict[BenetelModel, RUCapabilities] = {
    BenetelModel.RAN550: RUCapabilities(
        max_bw_mhz=100,
        min_freq_mhz=3300,
        max_freq_mhz=3800,
        num_tx_antennas=4,
        num_rx_antennas=4,
        duplex_modes=[DuplexMode.TDD],
    ),
    BenetelModel.RAN650: RUCapabilities(
        max_bw_mhz=100,
        min_freq_mhz=3300,
        max_freq_mhz=3800,
        num_tx_antennas=4,
        num_rx_antennas=4,
        duplex_modes=[DuplexMode.TDD],
    ),
}

LITEON_CATALOG: dict[LiteonModel, RUCapabilities] = {
    LiteonModel.FLEXFI: RUCapabilities(
        max_bw_mhz=100,
        min_freq_mhz=3300,
        max_freq_mhz=29500,
        num_tx_antennas=4,
        num_rx_antennas=4,
        duplex_modes=[DuplexMode.TDD],
    ),
}

CATALOGS = {
    RUType.USRP: (USRPModel, USRP_CATALOG),
    RUType.AW2S: (AW2SModel, AW2S_CATALOG),
    RUType.BENETEL: (BenetelModel, BENETEL_CATALOG),
    RUType.LITEON: (LiteonModel, LITEON_CATALOG),
}


class RU(BlueprintBaseModel):
    """Radio Unit."""

    type: RUType = Field(default=RUType.SIMULATED)
    """RU type/vendor."""

    model: RUModel | None = Field(default=None)
    """RU model name."""

    capabilities: RUCapabilities | None = Field(default=None)
    """RU capabilities."""

    clockSource: Literal["internal", "external"] = Field(default="internal")
    """Clock synchronization source."""

    timeSource: Literal["internal", "external"] = Field(default="internal")
    """Time synchronization source."""

    numberOfTxPorts: int = Field(default=1, ge=1)
    """Number of transmit antenna ports."""

    numberOfRxPorts: int = Field(default=1, ge=1)
    """Number of receive antenna ports."""

    txAttenuationDB: int = Field(default=0, ge=0)
    """Transmit attenuation in dB."""

    rxAttenuationDB: int = Field(default=0, ge=0)
    """Receive attenuation in dB."""

    txGainDB: int = Field(default=35)
    """Transmit gain in dB."""

    rxGainDB: int = Field(default=75)
    """Receive gain in dB."""


    @model_validator(mode="after")
    def populate_capabilities(self):
        """Populate the capabilities field if empty based on known specs."""

        if self.capabilities is None and CATALOGS.get(self.type):
                model_enum, catalog = CATALOGS[self.type]
                self.capabilities = catalog[model_enum(self.model)]
        return self


    @model_validator(mode="after")
    def validate_configuration(self):
        """Validate RU configuration against its capabilities."""

        if self.capabilities is None:
            return self

        capabilities = self.capabilities

        if self.numberOfTxPorts > capabilities.num_tx_antennas:
            raise ValueError(
                f"RU {self.name!r} configures {self.numberOfTxPorts} TX ports, "
                f"but only {capabilities.num_tx_antennas} are supported."
            )

        if self.numberOfRxPorts > capabilities.num_rx_antennas:
            raise ValueError(
                f"RU {self.name!r} configures {self.numberOfRxPorts} RX ports, "
                f"but only {capabilities.num_rx_antennas} are supported."
            )

        return self
