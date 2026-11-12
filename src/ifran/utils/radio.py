"""Utility functions to derive radio configuration based on the implementation."""

from collections.abc import Callable
from typing import Any

from metamodel_3gpp.models.common import DuplexMode
from metamodel_3gpp.models.ran import (
    DUComponent,
    GNBComponent,
    RadioConfiguration,
    SSBPeriodicity,
    SubcarrierSpacing,
    TDDPeriodicity,
)
from metamodel_3gpp.models.ru import RUType
from metamodel_3gpp.models.ue import UE, UEType

from ifran.models.provisioning import AW2SModel, RUModel, RUVendor, USRPModel
from ifran.models.ran import ADVANCED_RAN_CONFIG_MAPPING, DeployedRANComponent, RANImplementation
from ifran.models.ue import DeployedUE, UEImplementation

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
    },
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


RADIO_TYPE_BY_RU: dict[RUVendor | None, dict[RUModel | None, str]] = {
    None: {
        None: "simulated",
    },
    RUVendor.USRP: {
        USRPModel.B210: "b2xx",
        USRPModel.B205: "b2xx",
        USRPModel.N300: "n3xx",
        USRPModel.N320: "n3xx",
    },
    RUVendor.AW2S: {
        AW2SModel.JAGUAR: "aw2s",
        AW2SModel.PANTHER: "aw2s",
    },
}


def nr_arfcn_to_frequency_hz(arfcn: int) -> int:
    """Convert an NR-ARFCN to its reference frequency in Hz as per 3GPP TS 38.104 chapter 5.4.2.1."""

    # 0 to 599_999 => 0 to 3000 MHz
    if arfcn < 600_000:  # noqa: PLR2004
        return arfcn * 5_000

    # 600000 to 2_016_666 => 3000 to 24250.08 MHz
    if arfcn < 2_016_667:  # noqa: PLR2004
        return 3_000_000_000 + (arfcn - 600_000) * 15_000

    # 2_016_667 to 3_279_165 => 24_250.08 to 100_000 MHz
    return 24_250_080_000 + (arfcn - 2_016_667) * 60_000


def get_rbs(subcarrierSpacingKhz: SubcarrierSpacing, channelBandwidthMhz: int):
    """Derive number of resource blocks from given SCS and channel bandwidth."""

    bandwidth_rb = NRB.get(subcarrierSpacingKhz, {}).get(channelBandwidthMhz)
    if bandwidth_rb is None:
        raise ValueError(
            "Cannot derive number of resource blocks from given SCS "
            f"'{subcarrierSpacingKhz.value}Khz' and bandwidth '{channelBandwidthMhz}Mhz'."
        )

    return bandwidth_rb


def get_oai_bwp_location_and_bandwidth(bandwidth_rb: int) -> int:
    """
    Calculate OAI initial BWP locationAndBandwidth.

    Assumes the initial BWP spans the entire carrier, starting at CRB 0.
    """

    n_rb = 275
    bwp_start = 0
    bwp_size = bandwidth_rb

    if bwp_size <= 0 or bwp_size > n_rb:
        raise ValueError(f"Cannot derive initial BWP locationAndBandwidth from BWP size: {bwp_size}")

    if bwp_size - 1 <= n_rb // 2:
        return n_rb * (bwp_size - 1) + bwp_start

    return n_rb * (n_rb - bwp_size + 1) + (n_rb - 1 - bwp_start)


## RAN radio parameter derivation


def derive_oai_ran_config(  # noqa: C901, PLR0912
    component_meta: GNBComponent | DUComponent,
    component_deployment: DeployedRANComponent,
) -> dict[str, Any]:
    """Derive radio parameters specific to OAI RAN to put in derived configuration."""

    ru = component_meta.config.ru
    radio_config: RadioConfiguration = component_meta.config.radioConfiguration

    if radio_config.duplexMode == DuplexMode.FDD:
        # compute uplink point a based on the shift between dl and ul arfcn
        arfcn_shift = radio_config.uplinkArfcn - radio_config.downlinkArfcn  # type: ignore
        ul_point_a_arfcn = radio_config.pointAFrequencyArfcn + arfcn_shift

        oai_tdd_periodicity = None

    elif radio_config.duplexMode == DuplexMode.TDD:
        ul_point_a_arfcn = None
        oai_tdd_periodicity = OAI_TDD_PERIODICITY.get(radio_config.tddConfiguration.periodicityMilliseconds)  # type: ignore

    # additional flags for rfsim
    # -E enables continuous synchronization/transmission optimizations
    # NOTE don't use -E with real RUs, except for USRP B210/B205
    # for some reason the gNB can't see radio signals anymore (tested on N300 and N320)
    if component_deployment.advanced_config and component_deployment.advanced_config.useAdditionalOptions:
        additional_flags = component_deployment.advanced_config.useAdditionalOptions
    elif ru.type is RUType.SIMULATED:  # type: ignore
        additional_flags = "-E --rfsim"
    elif ru.model in [USRPModel.B210, USRPModel.B205]:  # type: ignore
        additional_flags = "-E --continuous-tx"
    else:
        additional_flags = ""

    # aw2s specific configuration
    if ru.type is RUType.REAL and ru.vendor is RUVendor.AW2S:  # type: ignore
        if not component_deployment.advanced_config:
            component_deployment.advanced_config = ADVANCED_RAN_CONFIG_MAPPING[RANImplementation.OAI][
                component_meta.type
            ]()

        adv_conf = component_deployment.advanced_config

        adv_conf.local_rf = adv_conf.local_rf or "no"
        adv_conf.local_portc = adv_conf.local_portc or 50000
        adv_conf.remote_portc = adv_conf.remote_portc or 55444
        adv_conf.local_portd = adv_conf.local_portd or 52001
        adv_conf.remote_portd = adv_conf.remote_portd or 52183
        adv_conf.tr_preference = adv_conf.tr_preference or "udp_ecpri_if5"
        adv_conf.nr_flag = adv_conf.nr_flag or 1
        adv_conf.sl_ahead = adv_conf.sl_ahead or 5

        if ru.ips:  # type: ignore
            adv_conf.remote_address = adv_conf.remote_address or ru.ips[0]  # type: ignore

        if component_deployment.multus.enabled:
            ru_iface = None
            for iface in component_deployment.multus.interfaces:
                if iface.enabled and iface.name.startswith("ru"):
                    ru_iface = iface

            if ru_iface:
                adv_conf.local_if_name = adv_conf.local_if_name or ru_iface.name
                adv_conf.local_address = adv_conf.local_address or ru_iface.ip_address

    bandwidth_rb = get_rbs(radio_config.subcarrierSpacingKhz, radio_config.channelBandwidthMhz)

    return {
        "bandwidth_rb": bandwidth_rb,
        "ul_point_a_arfcn": ul_point_a_arfcn,
        "numerology": NUMEROLOGY[radio_config.subcarrierSpacingKhz],
        "ssb_numerology": NUMEROLOGY[radio_config.ssbSubcarrierSpacing],
        "oai_tdd_periodicity": oai_tdd_periodicity,
        "oai_ssb_periodicity": OAI_SSB_PERIODICITY.get(radio_config.ssbPeriodicityMs, 2),
        "radio": RADIO_TYPE_BY_RU.get(getattr(ru, "vendor", None), {}).get(getattr(ru, "model", None), ""),  # type: ignore
        "additional_flags": additional_flags,
        "sdr_addrs": (
            f"addr={ru.ips[0]},clock_source={ru.clockSource},time_source={ru.timeSource}"  # type: ignore
            if ru.type is RUType.REAL and ru.ips and ru.vendor is not RUVendor.AW2S  # type: ignore
            else None
        ),
        "bwp_location_and_bandwidth": get_oai_bwp_location_and_bandwidth(bandwidth_rb),
    }


def derive_ocudu_ran_config(
    component_meta: GNBComponent | DUComponent,
    component_deployment: DeployedRANComponent,  # noqa: ARG001
) -> dict[str, Any]:
    """Derive radio parameters specific to OCUDU RAN to put in derived configuration."""

    ru = component_meta.config.ru
    radio_config: RadioConfiguration = component_meta.config.radioConfiguration

    if ru.type is RUType.SIMULATED:  # type: ignore
        device_driver = "zmq"
        device_args = (
            f"tx_port=tcp://{component_deployment.static_pod_ip}:2000,"
            f"rx_port=tcp://{component_deployment.advanced_config.ue_ip}:2001"
        )
        if component_deployment.advanced_config and component_deployment.advanced_config.base_srate:
            device_args += f",base_srate={component_deployment.advanced_config.base_srate}"

    elif ru.vendor is RUVendor.USRP:  # type: ignore
        device_driver = "uhd"
        if ru.model in [USRPModel.B210, USRPModel.B205]:  # type: ignore
            device_args = "type=b200,num_recv_frames=64,num_send_frames=64"
        elif ru.ips:  # type: ignore
            device_args = (
                f"addr={ru.ips[0]},"  # type: ignore
                f"clock_source={ru.clockSource},time_source={ru.timeSource}"  # type: ignore
            )
            if component_deployment.advanced_config and component_deployment.advanced_config.master_clock_rate:
                device_args += f",master_clock_rate={component_deployment.advanced_config.master_clock_rate}"
    else:
        device_driver = None
        device_args = None

    derived = {
        "device_driver": device_driver,
        "device_args": component_deployment.advanced_config.device_args or device_args,
        "radio": RADIO_TYPE_BY_RU.get(getattr(ru, "vendor", None), {}).get(getattr(ru, "model", None), ""),  # type: ignore
    }
    if radio_config.duplexMode is DuplexMode.TDD:
        tdd = radio_config.tddConfiguration
        period = tdd.periodicityMilliseconds.value  # type: ignore
        period_slots = round(period / (15.0 / radio_config.subcarrierSpacingKhz.value))
        derived["tdd_period_slots"] = period_slots

    return derived


def derive_ueransim_config(
    component_meta: GNBComponent | DUComponent,  # noqa: ARG001
    component_deployment: DeployedRANComponent,  # noqa: ARG001
) -> dict[str, Any]:
    """Derive radio parameters specific to UERANSIM to put in derived configuration."""
    return {}


# mapping of RAN implementation and callable radio config derive function
RAN_CONFIG_DERIVATOR: dict[RANImplementation, Callable] = {
    RANImplementation.OAI: derive_oai_ran_config,
    RANImplementation.OCUDU: derive_ocudu_ran_config,
    RANImplementation.UERANSIM: derive_ueransim_config,
}


def derive_ran_radio_config(
    component_meta: GNBComponent | DUComponent,
    component_deployment: DeployedRANComponent,
) -> dict[str, Any]:  # type: ignore
    """Derive gNB or DU's component's implementation-specific radio parameters."""

    component_deployment.derived_radio_config = RAN_CONFIG_DERIVATOR[component_deployment.implementation](  # type: ignore
        component_meta=component_meta,
        component_deployment=component_deployment,
    )


## UE radio parameter derivation


def derive_oai_ue_config(  # noqa: C901, PLR0912
    ue_meta: UE,
    ue_deployment: DeployedUE,
) -> dict[str, Any]:
    """Derive radio parameters specific to OAI NR UE to put in derived configuration."""

    derived = {}

    if ue_meta.type is UEType.CONTAINERIZED:
        ru = ue_meta.config.ru
        gnb = ue_meta.config.gnbs[0]
        radio_config: RadioConfiguration = gnb.config.radioConfiguration  # type: ignore

        # calculate the ue parameters
        # https://gitlab.eurecom.fr/oai/openairinterface5g/-/blob/develop/doc/runmodem-nrue.md

        # -r : bandwidth in terms of RBs
        bandwidth_rb = get_rbs(radio_config.subcarrierSpacingKhz, radio_config.channelBandwidthMhz)

        # -C : downlink carrier frequency in Hz
        # SSB and Point A frequencies are distinct from the carrier center.
        ssb_freq_hz = nr_arfcn_to_frequency_hz(radio_config.ssbArfcn)
        scs_hz = int(radio_config.subcarrierSpacingKhz.value) * 1000
        dl_point_a_hz = nr_arfcn_to_frequency_hz(radio_config.pointAFrequencyArfcn)

        if gnb.implementation is RANImplementation.OCUDU:  # type: ignore
            # Point A is at the lowest subcarrier of the resource grid.
            # The carrier center is halfway across the occupied RB grid.
            occupied_bandwidth_hz = bandwidth_rb * 12 * scs_hz

            dl_carrier_freq_hz = dl_point_a_hz + occupied_bandwidth_hz // 2
        else:
            dl_carrier_freq_hz = ssb_freq_hz

        # --CO : uplink frequency offset for FDD in Hz
        if radio_config.duplexMode == DuplexMode.FDD:
            ul_carrier_freq_hz = nr_arfcn_to_frequency_hz(radio_config.uplinkArfcn)  # type: ignore
            offset_hz = ul_carrier_freq_hz - dl_carrier_freq_hz
        else:
            # set to 0 for tdd
            offset_hz = 0

        # --numerology : numerology index
        numerology = NUMEROLOGY[radio_config.subcarrierSpacingKhz]

        # --ssb : SSB start subcarrier
        # delta_f_SSB in hz
        scs_ssb_hz = radio_config.ssbSubcarrierSpacing.value * 1000

        # 3GPP TS 38.211: SSB center is subcarrier #120 of the 240 subcarriers (20 RBs)
        # SSB lowest subcarrier = f_SSB - 120 * SCS_SSB
        ssb_start_freq_hz = ssb_freq_hz - (120 * scs_ssb_hz)
        ssb_offset_hz = ssb_start_freq_hz - dl_point_a_hz

        if ssb_offset_hz < 0:
            raise ValueError(f"Invalid 'ssbArfcn' ({radio_config.ssbArfcn}): SSB start frequency lies below Point A.")

        ssb_start = int(ssb_offset_hz // scs_ssb_hz)

        # additional flags
        if ue_deployment.advanced_config and ue_deployment.advanced_config.useAdditionalOptions:
            additional_flags = ue_deployment.advanced_config.useAdditionalOptions

        elif ru.type is RUType.SIMULATED:  # type: ignore
            if gnb.implementation is RANImplementation.OAI:  # type: ignore
                additional_flags = "-E --rfsim"
            elif gnb.implementation is RANImplementation.OCUDU:  # type: ignore
                additional_flags = (
                    "-E --ue-scan-carrier --thread-pool -1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1,-1 "
                    "--uecap_file /opt/oai-nr-ue/etc/uecap_ports1.xml"
                )

        elif ru.model in [USRPModel.B210, USRPModel.B205]:  # type: ignore
            additional_flags = "-E --ue-fo-compensation --ue-scan-carrier"

        else:
            additional_flags = ""

        # sdr_addrs
        sdr_addrs = None
        if ru.type is RUType.REAL:  # type: ignore
            if ru.model in [USRPModel.B210, USRPModel.B205]:  # type: ignore
                sdr_addrs = "type=b200,num_recv_frames=64,num_send_frames=64"
            elif ru.ips:  # type: ignore
                sdr_addrs = f"addr={ru.ips[0]},clock_source={ru.clockSource},time_source={ru.timeSource}"  # type: ignore

        derived = {
            "dl_carrier_freq_hz": dl_carrier_freq_hz,  # rf_freq
            "offset_hz": offset_hz,  # rf_offset
            "numerology": numerology,  # numerology
            "bandwidth_rb": bandwidth_rb,  # N_RB_DL
            "ssb_start": ssb_start,  # ssb_start
            "radio": RADIO_TYPE_BY_RU.get(getattr(ru, "vendor", None), {}).get(getattr(ru, "model", None), ""),  # type: ignore
            "additional_flags": additional_flags,
            "sdr_addrs": sdr_addrs,
        }

    return derived


def derive_ueransim_ue_config(
    ue_meta: UE,  # noqa: ARG001
    ue_deployment: DeployedUE,  # noqa: ARG001
) -> dict[str, Any]:
    """Derive radio parameters specific to USERANSIM UE to put in derived configuration."""
    return {}


def derive_srsue_ue_config(
    ue_meta: UE,
    ue_deployment: DeployedUE,  # noqa: ARG001
) -> dict[str, Any]:
    """Derive radio parameters specific to SRSRUE UE to put in derived configuration."""

    derived = {}

    if ue_meta.type is UEType.CONTAINERIZED:
        # gnb references must be resolved by now
        radio_config: RadioConfiguration = ue_meta.config.gnbs[0].config.radioConfiguration  # type: ignore

        ru = ue_meta.config.ru  # must be resolved by now

        if ru.type is RUType.SIMULATED:  # type: ignore
            device_driver = "zmq"
            device_args = (
                f"tx_port=tcp://{ue_deployment.static_pod_ip}:2001,"
                f"rx_port=tcp://{ue_meta.config.gnbs[0].gnb_ip}:2000"  # type: ignore
            )
            if ue_deployment.advanced_config and ue_deployment.advanced_config.srate:
                device_args += f",base_srate={ue_deployment.advanced_config.srate}"

        elif ru.vendor is RUVendor.USRP:  # type: ignore
            device_driver = "uhd"
            if ru.model in [USRPModel.B210, USRPModel.B205]:  # type: ignore
                device_args = "type=b200,num_recv_frames=64,num_send_frames=64"
            elif ru.ips:  # type: ignore
                device_args = (
                    f"addr={ru.ips[0]},"  # type: ignore
                    f"clock_source={ru.clockSource},time_source={ru.timeSource}"  # type: ignore
                )
                if ue_deployment.advanced_config and ue_deployment.advanced_config.master_clock_rate:
                    device_args += f",master_clock_rate={ue_deployment.advanced_config.master_clock_rate}"
        else:
            device_driver = None
            device_args = None

        derived = {
            "device_driver": device_driver,
            "device_args": ue_deployment.advanced_config.device_args or device_args,
            "radio": RADIO_TYPE_BY_RU.get(getattr(ru, "vendor", None), {}).get(getattr(ru, "model", None), ""),  # type: ignore
            "nof_prb": get_rbs(radio_config.subcarrierSpacingKhz, radio_config.channelBandwidthMhz),
        }

    return derived


# mapping of UE implementation and callable radio config derive function
UE_CONFIG_DERIVATOR: dict[UEImplementation, Callable] = {
    UEImplementation.OAI: derive_oai_ue_config,
    UEImplementation.UERANSIM: derive_ueransim_ue_config,
    UEImplementation.SRSUE: derive_srsue_ue_config,
}


def derive_ue_radio_config(
    ue_meta: UE,
    ue_deployment: DeployedUE,
) -> dict[str, Any]:  # type: ignore
    """Derive UE's implementation-specific radio parameters."""

    ue_deployment.derived_radio_config = UE_CONFIG_DERIVATOR[ue_deployment.implementation](
        ue_meta=ue_meta,
        ue_deployment=ue_deployment,
    )
