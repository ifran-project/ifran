"""Meta Model."""

from typing import Any

from pydantic import Field, field_validator

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.meta.core import Core
from orchestrator.models.meta.ran import RAN
from orchestrator.models.meta.ric import RIC
from orchestrator.models.meta.ru import RU
from orchestrator.models.meta.slice import Slice
from orchestrator.models.meta.ue import UE, UEType


class MetaModel(BlueprintBaseModel):
    """Meta Model describing the 5G network to be deployed."""

    core: Core = Field(default_factory=Core)
    """5G core configuration."""

    ran: RAN = Field(default_factory=RAN)
    """5G RAN configuration."""

    rus: dict[str, RU] = Field(default_factory=lambda: {"sim_ru": RU()})
    """Radio Units."""

    ues: dict[str, UE] = Field(default_factory=lambda: {"sim_ue": UE()})
    """User Equipments."""

    slices: dict[str, Slice] = Field(default_factory=lambda: {"internet": Slice()})
    """Slices."""

    ric: RIC = Field(default_factory=RIC)
    """RIC."""


    @field_validator("slices", mode="after")
    @classmethod
    def populate_slice_names(cls, value: dict[str, Slice]) -> dict[str, Slice]:
        """Populate slice names with slices dict keys after validation."""

        for slice_name, slice_data in value.items():
            if slice_data.name is None:
                slice_data.name = slice_name

        return value


    @field_validator("ues", mode="before")
    @classmethod
    def default_ue_type(cls, value) -> dict[str, UE] | Any:
        """Make default UE type a simulated one."""

        if not isinstance(value, dict):
            return value

        for ue_data in value.values():
            if isinstance(ue_data, dict) and "type" not in ue_data:
                ue_data["type"] = UEType.CONTAINERIZED

        return value
