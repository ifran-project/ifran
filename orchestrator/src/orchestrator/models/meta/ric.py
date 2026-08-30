"""RIC meta models."""

from enum import StrEnum, auto
from typing import Annotated, Any, Literal

from pydantic import Field, model_validator

from orchestrator.models.meta.common import (
    E2,
    BlueprintBaseModel,
    Category5G,
    Component5G,
    Network5G,
    Self,
)


class RICImplementation(StrEnum):
    """Supported RAN Intelligent Controller implementations."""

    OAI = auto()
    """OpenAireInterface's Flexible RAN Intelligent Controller (FlexRIC) and E2 Agent."""

    ORAN_SC = auto() # TODO https://docs.o-ran-sc.org/projects/o-ran-sc-ric-plt-ric-dep/en/latest/installation-guides.html#installing-near-realtime-ric-in-ric-cluster
    """O-RAN Software Community (SC) Near-Real-time RIC."""


class RICComponentType(StrEnum):
    """Supported RIC component types."""

    RIC = auto()
    DBAAS = auto()
    E2MGR = auto()
    E2TERM = auto()
    RTMGR = auto()
    SUBMGR = auto()
    APPMGR = auto()
    CHARTMUSEUM = auto()
    XAPP_ONBOARDER = auto()
    A1MEDIATOR = auto()


SUPPORTED_RIC_COMPONENTS: dict[RICImplementation, set[RICComponentType]] = {
    RICImplementation.OAI: {RICComponentType.RIC},
    RICImplementation.ORAN_SC: {
        RICComponentType.DBAAS,
        RICComponentType.E2MGR,
        RICComponentType.E2TERM,
        RICComponentType.RTMGR,
        RICComponentType.SUBMGR,
        RICComponentType.APPMGR,
        RICComponentType.CHARTMUSEUM,
        RICComponentType.XAPP_ONBOARDER,
        RICComponentType.A1MEDIATOR,
    },
}


class RICComponentConfig(BlueprintBaseModel):
    """Generic RIC component configuration."""


class RICConfig(BlueprintBaseModel):
    """Configuration for a RIC component exposing E2."""

    e2: E2 = Field(default_factory=E2)
    """E2 endpoint used to reach the RAN."""


class GenericAdvancedRICConfig(BlueprintBaseModel):
    """Generic RIC advanced configuration (implementation-specific)."""


class OAIAdvancedRICConfig(GenericAdvancedRICConfig):
   """Advanced configuration for OAI FLEXRIC."""

   DB_DIR: str | None = Field(default=None)
   DB_NAME: str | None = Field(default=None)


class ORANSCAdvancedRICConfig(GenericAdvancedRICConfig):
    """Advanced configuration for O-RAN SC Near-RT RIC."""


ADVANCED_RIC_CONFIG_MAPPING: dict[RICImplementation, dict[RICComponentType, type[GenericAdvancedRICConfig]]] = {
    RICImplementation.OAI: {
        RICComponentType.RIC: OAIAdvancedRICConfig,
    },
    RICImplementation.ORAN_SC: {
        RICComponentType.DBAAS: ORANSCAdvancedRICConfig,
        RICComponentType.E2MGR: ORANSCAdvancedRICConfig,
        RICComponentType.E2TERM: ORANSCAdvancedRICConfig,
        RICComponentType.RTMGR: ORANSCAdvancedRICConfig,
        RICComponentType.SUBMGR: ORANSCAdvancedRICConfig,
        RICComponentType.APPMGR: ORANSCAdvancedRICConfig,
        RICComponentType.CHARTMUSEUM: ORANSCAdvancedRICConfig,
        RICComponentType.XAPP_ONBOARDER: ORANSCAdvancedRICConfig,
        RICComponentType.A1MEDIATOR: ORANSCAdvancedRICConfig,
    },
}


class RICComponent(Component5G):
    """Generic RIC component."""

    category: Literal[Category5G.RIC] = Field(default=Category5G.RIC, frozen=True)

    type: RICComponentType = Field()
    """RIC component type."""

    implementation: RICImplementation | None = Field(default=None)
    """RIC component implementation."""

    config: RICComponentConfig = Field(default_factory=RICComponentConfig)
    """RIC component configuration."""

    advanced_config: dict[str, Any] | None = Field(default=None)
    """Implementation-specific RIC component configuration."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(ADVANCED_RIC_CONFIG_MAPPING)


class FlexRICComponent(RICComponent):
    """OAI FlexRIC component."""

    type: Literal[RICComponentType.RIC] = Field(frozen=True)
    config: RICConfig = Field(default_factory=RICConfig)


class E2TermComponent(RICComponent):
    """O-RAN SC E2 Termination component."""

    type: Literal[RICComponentType.E2TERM] = Field(frozen=True)
    # Match the SCTP port used by OAI's bundled FlexRIC E2 agent.
    config: RICConfig = Field(default_factory=lambda: RICConfig(e2=E2(port=36421)))


type ValidatedRICComponent = Annotated[
    FlexRICComponent | E2TermComponent,
    Field(discriminator="type"),
]


class RIC(Network5G):
    """5G RAN Intelligent Controller network."""

    implementation: RICImplementation = Field(default=RICImplementation.OAI)
    """RIC implementation."""

    components: dict[str, ValidatedRICComponent | RICComponent] = Field(default_factory=dict)
    """RIC components."""

    @model_validator(mode="after")
    def validate_supported_ric_component_types(self) -> Self:
        """Validate component support for the selected RIC implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_RIC_COMPONENTS)
        return self
