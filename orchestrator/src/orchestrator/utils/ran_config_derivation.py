"""Utility functions to derive RAN radio configuration based on the implementation."""

from collections.abc import Callable
from typing import Any

from orchestrator.models.meta.common import DuplexMode
from orchestrator.models.meta.ran import (
    CommonGNBComponent,
    RadioConfiguration,
    RANComponent,
    RANType,
    SubcarrierSpacing,
)
from orchestrator.models.meta.ru import RUModel, RUType, USRPModel

# FR1 NRB values for the combinations supported by this prototype based on 3GPP TS 38.104
NRB: dict[SubcarrierSpacing, dict[int, int]] = {
    SubcarrierSpacing.SCS_15KHZ: {
        5: 25,
        10: 52,
        15: 79,
        20: 106,
        25: 133,
        30: 160,
        35: 188,
        40: 216,
        45: 242,
        50: 270,
    },
    SubcarrierSpacing.SCS_30KHZ: {
        5: 11,
        10: 24,
        15: 38,
        20: 51,
        25: 65,
        30: 78,
        35: 92,
        40: 106,
        45: 119,
        50: 133,
        60: 162,
        70: 189,
        80: 217,
        90: 245,
        100: 273,
    },
    SubcarrierSpacing.SCS_60KHZ: {
        10: 11,
        15: 18,
        20: 24,
        25: 31,
        30: 38,
        35: 44,
        40: 51,
        45: 58,
        50: 65,
        60: 79,
        70: 93,
        80: 107,
        90: 121,
        100: 135,
    }
}


OAI_TDD_PERIODICITY: dict[float, int] = {
    0.5: 0,
    0.625: 1,
    1.0: 2,
    1.25: 3,
    2.0: 4,
    2.5: 5,
    5.0: 6,
    10.0: 7,
}


OAI_RADIO_BY_RU: dict[RUType, dict[RUModel | None, str]] = {
    RUType.SIMULATED: {
        None: "rfsim"
    },
    RUType.USRP: {
        USRPModel.B210: "b2xx",
        USRPModel.B205: "b2xx",
        USRPModel.N300: "n3xx",
        USRPModel.N320: "n3xx",
    },
}


def derive_oai_ran_config(component: RANComponent) -> dict:
    """Derive radio parameters specific to OAI RAN to put in advanced configuration."""

    # TODO

    radio_config: RadioConfiguration = component.config.radioConfiguration

    bandwidth_rb = NRB.get(radio_config.subcarrierSpacingKhz, {}).get(radio_config.channelBandwidthMhz)
    if bandwidth_rb is None and radio_config.implementation is RANType.OAI:
        raise ValueError(
            "Cannot derive number of resource blocks from given SCS "
            f"'{radio_config.subcarrierSpacingKhz.value}Khz' and bandwidth '{radio_config.channelBandwidthMhz}Mhz'."
        )

    ru = component.config.ru
    radio = OAI_RADIO_BY_RU.get(ru.type, {}).get(ru.model, "")

    # additional flags for rfsim
    if ru.type is RUType.SIMULATED and (
        component.advanced_config is None or component.advanced_config.useAdditionalOptions is None):
        additional_flags = "-E --rfsim"
    else:
        additional_flags = ""

    derived = {
        "bandwidth_rb": bandwidth_rb,
        "radio": radio,
        "additional_flags": additional_flags,
    }

    if radio_config.duplexMode is DuplexMode.TDD:
        tdd = radio_config.tddConfiguration
        period = tdd.periodicityMilliseconds.value

        oai_tdd_periodicity = OAI_TDD_PERIODICITY.get(period)
        if oai_tdd_periodicity is None:
            raise ValueError(f"Cannot derive OAI TDD periodicity for given value {period!r}.")

        derived["oai_tdd_periodicity"] = oai_tdd_periodicity

    return derived


def derive_srs_ran_config(component: RANComponent) -> dict[str, Any]:
    """Derive radio parameters specific to SRSRAN to put in advanced configuration."""

    # TODO

    radio_config: RadioConfiguration = component.config.radioConfiguration

    derived = {}
    if radio_config.duplexMode is DuplexMode.TDD:
        tdd = radio_config.tddConfiguration
        period = tdd.periodicityMilliseconds.value
        period_slots = round(period / (15.0 / radio_config.subcarrierSpacingKhz.value))
        derived["tdd_period_slots"] = period_slots

    return derived


def derive_ueransim_config(component: RANComponent) -> dict[str, Any]:
    """Derive radio parameters specific to UERANSIM to put in advanced configuration."""

    # TODO

    return {}


# mapping of RAN implementation and callable radio config derive funtion
RAN_CONFIG_DERIVATOR: dict[RANType, Callable] = {
    RANType.OAI: derive_oai_ran_config,
    RANType.SRSRAN: derive_srs_ran_config,
    RANType.UERANSIM: derive_ueransim_config,
}


def derive_radio_config(component: CommonGNBComponent) -> dict[str, Any]:
    """Derive gNB or DU's component's implementation-specific radio parameters."""

    component.derived_radio_config =  RAN_CONFIG_DERIVATOR[component.implementation](component)
