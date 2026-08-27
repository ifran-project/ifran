"""RIC meta models."""

from enum import StrEnum, auto
from typing import Literal

from pydantic import Field, model_validator

from orchestrator.models.meta.common import (
    E2,
    BlueprintBaseModel,
    Category5G,
    Component5G,
    Self,
)


class RICImplementation(StrEnum):
    """Supported RAN Intelligent Controller implementations."""

    OAI = auto()
    """OpenAireInterface's Flexible RAN Intelligent Controller (FlexRIC) and E2 Agent."""

    ORAN_SC = auto() # TODO https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-ric-dep/en/latest/installation-guides.html#installing-near-realtime-ric-in-ric-cluster
    """O-RAN Software Community (SC) Near-Real-time RIC."""


class RICConfig(BlueprintBaseModel):
    """RIC configuration."""

    e2: E2 = Field(default_factory=E2)
    """E2 endpoint used to reach the RAN."""


class GenericAdvancedRICConfig(BlueprintBaseModel):
    """Generic RIC advanced configuration (implementation-specific)."""


class OAIAdvancedRICConfig(GenericAdvancedRICConfig):
   """Advanced configuration for OAI FLEXRIC."""

   DB_DIR: str | None = Field(default=None)
   DB_NAME: str | None = Field(default=None)


ADVANCED_RIC_CONFIG_MAPPING: dict[RICImplementation, dict[str, type[GenericAdvancedRICConfig]]] = {
    RICImplementation.OAI: {
        "ric": OAIAdvancedRICConfig,
    },
}


class RIC(Component5G):
    """5G RAN Intelligent Controller."""

    category: Literal[Category5G.RIC] = Field(default=Category5G.RIC, frozen=True)

    type: Literal["ric"] = Field(default="ric", frozen=True) # type still needed for deployment consistency with other 5g components

    implementation: RICImplementation = Field(default=RICImplementation.OAI)
    """RIC implementation."""

    config: RICConfig = Field(default_factory=RICConfig)
    """RIC configuration."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_RIC_CONFIG_MAPPING,
            default_model=GenericAdvancedRICConfig,
        )
