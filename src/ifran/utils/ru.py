"""Radio Unit (RU) configuration utils (O-RAN 7.2 Benetel RUs)."""

import asyncio

from metamodel_3gpp.models.common import DuplexMode
from metamodel_3gpp.models.ran import DUComponent, GNBComponent, RadioConfiguration

from ifran.models.ansible import AnsibleParams
from ifran.models.provisioning import BenetelRUParams, MergedRU, ProvisionableNode
from ifran.utils.ansible import get_ansible_inventory_line, handle_ansible_result_exception, run_ansible_role
from ifran.utils.radio import get_rbs, nr_arfcn_to_frequency_hz

# Benetel 'mimo_mode' from the RU (Tx, Rx) ports, for the 4-port RANx50 RUs
BENETEL_MIMO_MODES: dict[tuple[int, int], str] = {
    (4, 4): "1_2_3_4_4x4",
    (4, 2): "1_2_3_4_4x2",
}

# number of symbols in a slot (normal cyclic prefix)
SYMBOLS_PER_SLOT = 14

# Benetel TDD patterns: at most 10 slots for both patterns together
BENETEL_MAX_TDD_SLOTS = 10


def get_benetel_tdd_config(radio_config: RadioConfiguration) -> dict[str, str]:
    """Derive the Benetel TDD pattern (e.g. DDDSU) and special slot symbols (e.g. DDDDDDGGGGUUUU)."""

    tdd = radio_config.tddConfiguration

    if radio_config.duplexMode is not DuplexMode.TDD or tdd is None:
        raise ValueError("Benetel RU configuration: only TDD is supported.")

    slots = round(float(tdd.periodicityMilliseconds) * int(radio_config.subcarrierSpacingKhz) / 15)
    special = tdd.nrofDownlinkSymbols > 0 or tdd.nrofUplinkSymbols > 0
    pattern = "D" * tdd.nrofDownlinkSlots + ("S" if special else "") + "U" * tdd.nrofUplinkSlots

    if len(pattern) != slots:
        raise ValueError(f"Benetel RU configuration: TDD pattern {pattern!r} does not fill the {slots} slots period.")

    # the same pattern is repeated in both Benetel patterns, which hold at most 10 slots together
    if 2 * slots > BENETEL_MAX_TDD_SLOTS:
        raise ValueError(f"Benetel RU configuration: TDD period of {slots} slots is not supported (5 slots at most).")

    guard = SYMBOLS_PER_SLOT - tdd.nrofDownlinkSymbols - tdd.nrofUplinkSymbols
    if guard < 0:
        raise ValueError("Benetel RU configuration: more than 14 downlink and uplink symbols in the special slot.")

    return {
        "tdd_pattern_1": pattern,
        "tdd_pattern_2": pattern,
        "special_slots_symbols": "D" * tdd.nrofDownlinkSymbols + "G" * guard + "U" * tdd.nrofUplinkSymbols,
    }


def build_benetel_ru_config(
    component_name: str,
    component_meta: GNBComponent | DUComponent,
    node_name: str,
    node_data: ProvisionableNode,
) -> dict[str, str]:
    """
    Build the values of the Benetel /etc/ru_config.cfg for the RU of a gNB or DU.

    - DU C-plane and U-plane MAC addresses and VLAN: VFs of the 'fhi72' parameters of the gNB or DU node
    - centre frequency, bandwidth and TDD pattern: gNB or DU radio configuration
    - MIMO mode: RU Tx and Rx ports
    - other values: RU 'benetel' parameters
    """

    ru: MergedRU = component_meta.config.ru  # type: ignore
    radio_config: RadioConfiguration = component_meta.config.radioConfiguration
    params = ru.benetel or BenetelRUParams()

    if node_data.fhi72 is None:
        raise ValueError(
            f"RAN component {component_name!r} uses a Benetel RU: its node {node_name!r} needs 'fhi72' parameters."
        )

    mimo_mode = BENETEL_MIMO_MODES.get((ru.numberOfTxPorts, ru.numberOfRxPorts))
    if mimo_mode is None:
        raise ValueError(
            f"Benetel RU configuration: {ru.numberOfTxPorts}T{ru.numberOfRxPorts}R is not supported "
            f"(supported: {', '.join(f'{tx}T{rx}R' for tx, rx in BENETEL_MIMO_MODES)})."
        )

    # the RU centre frequency is the middle of the carrier, from point A
    bandwidth_rb = get_rbs(radio_config.subcarrierSpacingKhz, radio_config.channelBandwidthMhz)
    centre_frequency_hz = nr_arfcn_to_frequency_hz(radio_config.pointAFrequencyArfcn) + (
        bandwidth_rb * 12 * int(radio_config.subcarrierSpacingKhz) * 1000 // 2
    )

    vlan = f"{node_data.fhi72.vf('U').vlan:x}"  # hexadecimal, without prefix (e.g. 321 for VLAN 801)

    config = {
        "mimo_mode": mimo_mode,
        "downlink_scaling": str(params.downlink_scaling),
        "prach_format": params.prach_format,
        "compression": params.compression,
        "c_plane_du_mac": node_data.fhi72.vf("C").mac.lower(),
        "u_plane_du_mac": node_data.fhi72.vf("U").mac.lower(),
        "u_plane_du_vlan_uplink": vlan,
        "u_plane_du_vlan_downlink": vlan,
        "c_plane_du_vlan": vlan,
        "bandwidth_hz": str(radio_config.channelBandwidthMhz * 1_000_000),
        "centre_frequency_hz": str(centre_frequency_hz),
        "tx_power_dbm": f"{params.tx_power_dbm:.6f}",
        **get_benetel_tdd_config(radio_config),
    }

    return config | params.extra


async def run_single_ru_configuration(  # noqa: PLR0917
    component_name: str,
    ru_name: str,
    ru_config: dict[str, str],
    ru_ip: str,
    node_name: str,
    node_data: ProvisionableNode,
    ansible_params: AnsibleParams,
    force: bool = False,
    quiet: bool = False,
) -> None:
    """Load the configuration of a Benetel RU from the node of its gNB or DU and reboot the RU if it changed."""

    args = {
        "role": "ru/benetel/configure",
        "inputs": {
            "ru_name": ru_name,
            "ru_ip": ru_ip,
            "ru_config": ru_config,
            "force_reboot": force,
        },
        "runner_path": f"{ansible_params.runner_path}/ru/{ru_name}/configure",
        "roles_paths": ansible_params.roles_paths,
        "hosts": node_name,
        "inventory": get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
        "become": True,
        "quiet": quiet,
    }

    try:
        await run_ansible_role(**args)
    except Exception as e:
        raise RuntimeError(
            f"RU {ru_name!r} configuration from node {node_name!r} (component {component_name!r}) not successful."
        ) from e


async def run_parallel_ru_configuration(
    configurations: list[dict],
    ansible_params: AnsibleParams,
    force: bool = False,
    ignore_failures: bool = False,
    quiet: bool = False,
) -> None:
    """Run RU configurations in parallel (each item holds run_single_ru_configuration arguments)."""

    tasks = [
        asyncio.create_task(
            run_single_ru_configuration(**configuration, ansible_params=ansible_params, force=force, quiet=quiet)
        )
        for configuration in configurations
    ]

    for result in await asyncio.gather(*tasks, return_exceptions=True):
        if isinstance(result, Exception):
            handle_ansible_result_exception(result=result, ignore_invalid_states=False, ignore_failures=ignore_failures)
