"""Utility functions to derive radio configuration based on the implementation."""

from collections.abc import Callable
from typing import Any

from orchestrator.models.meta.common import DuplexMode
from orchestrator.models.meta.ran import (
    CommonGNBComponent,
    RadioConfiguration,
    RANImplementation,
    SSBPeriodicity,
    SubcarrierSpacing,
    TDDPeriodicity,
)
from orchestrator.models.meta.ru import RUModel, RUType, USRPModel
from orchestrator.models.meta.ue import UE, UEImplementation, UEType

NUMEROLOGY: dict[SubcarrierSpacing, int] = {
    SubcarrierSpacing.SCS_15KHZ: 0,
    SubcarrierSpacing.SCS_30KHZ: 1,
    SubcarrierSpacing.SCS_60KHZ: 2,
    SubcarrierSpacing.SCS_120KHZ: 3,
    SubcarrierSpacing.SCS_240KHZ: 4,
}

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
    TDDPeriodicity.MS_0_5: 0,
    TDDPeriodicity.MS_0_625: 1,
    TDDPeriodicity.MS_1: 2,
    TDDPeriodicity.MS_1_25: 3,
    TDDPeriodicity.MS_2: 4,
    TDDPeriodicity.MS_2_5: 5,
    TDDPeriodicity.MS_5: 6,
    TDDPeriodicity.MS_10: 7,
}


OAI_SSB_PERIODICITY: dict[SSBPeriodicity, int] = {
    SSBPeriodicity.MS_5: 0,
    SSBPeriodicity.MS_10: 1,
    SSBPeriodicity.MS_20: 2,
    SSBPeriodicity.MS_40: 3,
    SSBPeriodicity.MS_80: 4,
    SSBPeriodicity.MS_160: 5,
}


OAI_RADIO_BY_RU: dict[RUType, dict[RUModel | None, str]] = {
    RUType.SIMULATED: {
        None: "rfsim", # model is None for simulatd rus
    },
    RUType.USRP: {
        USRPModel.B210: "b2xx",
        USRPModel.B205: "b2xx",
        USRPModel.N300: "n3xx",
        USRPModel.N320: "n3xx",
    },
}


def nr_arfcn_to_frequency_hz(arfcn: int) -> int:
    """Convert an NR-ARFCN to its reference frequency in Hz as per 3GPP TS 38.104 chapter 5.4.2.1."""

    # 0 to 599_999 => 0 to 3000 MHz
    if arfcn < 600_000:
        return arfcn * 5_000

    # 600000 to 2_016_666 => 3000 to 24250.08 MHz
    if arfcn < 2_016_667:
        return 3_000_000_000 + (arfcn - 600_000) * 15_000

    # 2_016_667 to 3_279_165 => 24_250.08 to 100_000 MHz
    return 24_250_080_000 + (arfcn - 2_016_667) * 60_000


# RAN radio parameter derivation
def derive_oai_ran_config(component: CommonGNBComponent) -> dict[str, Any]:
    """Derive radio parameters specific to OAI RAN to put in derived configuration."""

    radio_config: RadioConfiguration = component.config.radioConfiguration

    bandwidth_rb = NRB.get(radio_config.subcarrierSpacingKhz, {}).get(radio_config.channelBandwidthMhz)
    if bandwidth_rb is None and radio_config.implementation is RANImplementation.OAI:
        raise ValueError(
            "Cannot derive number of resource blocks from given SCS "
            f"'{radio_config.subcarrierSpacingKhz.value}Khz' and bandwidth '{radio_config.channelBandwidthMhz}Mhz'."
        )

    if radio_config.duplexMode == DuplexMode.FDD:
        # compute uplink point a based on the shift between dl and ul arfcn
        arfcn_shift = radio_config.uplinkArfcn - radio_config.downlinkArfcn
        ul_point_a_arfcn = radio_config.pointAFrequencyArfcn + arfcn_shift

        oai_tdd_periodicity = None

    elif radio_config.duplexMode == DuplexMode.TDD:
        ul_point_a_arfcn = None
        oai_tdd_periodicity = OAI_TDD_PERIODICITY.get(radio_config.tddConfiguration.periodicityMilliseconds)


    ru = component.config.ru
    radio = OAI_RADIO_BY_RU.get(ru.type, {}).get(ru.model, "")

    # additional flags for rfsim
    if ru.type is RUType.SIMULATED and (
        component.advanced_config is None or component.advanced_config.useAdditionalOptions is None):
        additional_flags = "-E --rfsim" # -E enables continuous synchronization/transmission optimizations
    else:
        additional_flags = "-E"

    derived = {
        "bandwidth_rb": bandwidth_rb,
        "ul_point_a_arfcn": ul_point_a_arfcn,
        "numerology": NUMEROLOGY[radio_config.subcarrierSpacingKhz],
        "ssb_numerology": NUMEROLOGY[radio_config.ssbSubcarrierSpacing],
        "oai_tdd_periodicity": oai_tdd_periodicity,
        "oai_ssb_periodicity": OAI_SSB_PERIODICITY.get(radio_config.ssbPeriodicityMs, 2),
        "radio": radio,
        "additional_flags": additional_flags,
    }

    return derived


def derive_srs_ran_config(component: CommonGNBComponent) -> dict[str, Any]:
    """Derive radio parameters specific to SRSRAN to put in derived configuration."""

    # TODO

    radio_config: RadioConfiguration = component.config.radioConfiguration

    derived = {}
    if radio_config.duplexMode is DuplexMode.TDD:
        tdd = radio_config.tddConfiguration
        period = tdd.periodicityMilliseconds.value
        period_slots = round(period / (15.0 / radio_config.subcarrierSpacingKhz.value))
        derived["tdd_period_slots"] = period_slots

    return derived


def derive_ueransim_config(component: CommonGNBComponent) -> dict[str, Any]:
    """Derive radio parameters specific to UERANSIM to put in derived configuration."""

    # TODO

    return {}


# mapping of RAN implementation and callable radio config derive funtion
RAN_CONFIG_DERIVATOR: dict[RANImplementation, Callable] = {
    RANImplementation.OAI: derive_oai_ran_config,
    RANImplementation.SRSRAN: derive_srs_ran_config,
    RANImplementation.UERANSIM: derive_ueransim_config,
}


def derive_ran_radio_config(component: CommonGNBComponent) -> dict[str, Any]:
    """Derive gNB or DU's component's implementation-specific radio parameters."""

    component.derived_radio_config = RAN_CONFIG_DERIVATOR[component.implementation](component)


# UE radio parameter derivation
def derive_oai_ue_config(ue: UE) -> dict[str, Any]:
    """Derive radio parameters specific to OAI NR UE to put in derived configuration."""

    derived = {}

    if ue.type is UEType.CONTAINERIZED:
        # gnb reference must be resolved by now and its derived config must be present
        radio_config: RadioConfiguration = ue.config.gnb[1].config.radioConfiguration

        # calculate the ue parameters
        # https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/runmodem-nrue.md

        # -C : downlink carrier frequency in Hz
        dl_carrier_freq_hz = nr_arfcn_to_frequency_hz(radio_config.ssbArfcn)

        # --CO : uplink frequency offset for FDD in Hz
        if radio_config.duplexMode == DuplexMode.FDD:
            ul_carrier_freq_hz = nr_arfcn_to_frequency_hz(radio_config.uplinkArfcn)
            offset_hz = ul_carrier_freq_hz - dl_carrier_freq_hz
        else:
            # set to 0 for tdd
            offset_hz = 0

        # --numerology : numerology index   
        numerology = NUMEROLOGY[radio_config.subcarrierSpacingKhz]

        # -r : bandwidth in terms of RBs
        bandwidth_rb = NRB.get(radio_config.subcarrierSpacingKhz, {}).get(radio_config.channelBandwidthMhz)
        if bandwidth_rb is None:
            raise ValueError(
                "Cannot derive number of resource blocks from given SCS "
                f"'{radio_config.subcarrierSpacingKhz.value}Khz' and bandwidth '{radio_config.channelBandwidthMhz}Mhz'."
            )

        # --ssb : SSB start subcarrier
        # delta_f_SSB in hz
        scs_ssb_hz = radio_config.ssbSubcarrierSpacing.value * 1000
        ssb_freq_hz = nr_arfcn_to_frequency_hz(radio_config.ssbArfcn)

        # 3GPP TS 38.211: SSB center is subcarrier #120 of the 240 subcarriers (20 RBs)
        # SSB lowest subcarrier = f_SSB - 120 * SCS_SSB
        dl_point_a_hz = nr_arfcn_to_frequency_hz(radio_config.pointAFrequencyArfcn)
        ssb_start_freq_hz = ssb_freq_hz - (120 * scs_ssb_hz)
        ssb_offset_hz = ssb_start_freq_hz - dl_point_a_hz

        if ssb_offset_hz < 0:
            raise ValueError(
                f"Invalid 'ssbArfcn' ({radio_config.ssbArfcn}): SSB start frequency lies below Point A."
            )

        ssb_start = int(ssb_offset_hz // scs_ssb_hz)

        # additional flags
        ru = ue.config.ru # must be resolved by now
        radio = OAI_RADIO_BY_RU.get(ru.type, {}).get(ru.model, "") if ru else ""

        # additional flags for ru
        if ru.type is RUType.SIMULATED and (
            ue.advanced_config is None or ue.advanced_config.useAdditionalOptions is None):
            additional_flags = "-E --rfsim" # -E enables continuous synchronization/transmission optimizations
        else:
            additional_flags = "-E"

        derived = {
            "dl_carrier_freq_hz": dl_carrier_freq_hz, # rf_freq
            "offset_hz": offset_hz, # rf_offset
            "numerology": numerology, # numerology
            "bandwidth_rb": bandwidth_rb, # N_RB_DL
            "ssb_start": ssb_start, # ssb_start
            "radio": radio,
            "additional_flags": additional_flags,
        }

    return derived


# mapping of UE implementation and callable radio config derive funtion
UE_CONFIG_DERIVATOR: dict[UEImplementation, Callable] = {
    UEImplementation.OAI: derive_oai_ue_config,
}


def derive_ue_radio_config(ue: UE) -> dict[str, Any]:
    """Derive UE's implementation-specific radio parameters."""

    ue.derived_radio_config = UE_CONFIG_DERIVATOR[ue.implementation](ue)
