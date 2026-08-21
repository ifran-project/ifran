"""Common utilities and helpers."""

import ipaddress
import random
from typing import Any

from pydantic import BaseModel, IPvAnyAddress, IPvAnyNetwork


class InvalidResourceStateError(Exception):
    """Exception when a resource's state/status contradicts the desired action to be done."""


class ReferenceNotFounError(Exception):
    """Exception when a resource references an undefined resource."""


def generate_random_ip(network: IPvAnyNetwork, used: set[IPvAnyAddress] | None = None) -> IPvAnyAddress:
    """Generate a random IP address inside a network."""

    used = used or set()

    first = int(network.network_address) + 1
    last = int(network.broadcast_address) - 1

    if first > last:
        raise ValueError(f"Network {network!r} has no usable host addresses to pick from.")

    retries = 100
    for i in range(retries):
        address = ipaddress.ip_address(random.randint(first, last))
        if address not in used:
            return address


def sync_dict_keys(target_dict: dict, source_dict: dict, default_factory) -> None:
    """Synchronize target_dict keys with source_dict keys."""

    missing_keys = source_dict.keys() - target_dict.keys()
    extra_keys = target_dict.keys() - source_dict.keys()

    # add missing keys
    for key in missing_keys:
        target_dict[key] = default_factory()

    # remove exra keys
    for key in extra_keys:
        del target_dict[key]


def _to_jsonable(value: Any) -> Any:
    """Helper to recursively convert Pydantic models to JSON-compatible values."""

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return {k: _to_jsonable(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_to_jsonable(item) for item in value)

    return value


def deep_merge(left: dict[str, Any] | BaseModel, right: dict[str, Any] | BaseModel) -> dict[str, Any]:
    """
    Recursively merge two dictionaries or pydantic models (converted to dictionaries).
    Values from 'right' dict take precedence when the same leaf field exists in both dicts.
    """

    left = _to_jsonable(left)
    right = _to_jsonable(right)

    result = dict(left)

    for key, right_value in right.items():
        left_value = result.get(key)
        if (isinstance(left_value, dict) and isinstance(right_value, dict)):
            result[key] = deep_merge(left=left_value, right=right_value)
        else:
            result[key] = right_value

    return result
