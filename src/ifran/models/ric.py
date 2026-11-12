"""RIC deployment models."""

from enum import StrEnum, auto
from typing import Self

from metamodel_3gpp.models.base import StrictBaseModel
from metamodel_3gpp.models.ric import RICComponentType, SingleRICComponent
from pydantic import Field, model_validator

from ifran.models.common import Deployed5GComponent, Deployed5GNetwork


class RICImplementation(StrEnum):
    """Supported RAN Intelligent Controller implementations."""

    OAI = auto()
    """OpenAireInterface's Flexible RAN Intelligent Controller (FlexRIC) and E2 Agent."""

    ORAN_SC = auto()
    """O-RAN Software Community (SC) Near-Real-time RIC."""


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


class GenericAdvancedRICConfig(StrictBaseModel):
    """Generic RIC advanced configuration (implementation-specific)."""


class OAIAdvancedRICConfig(GenericAdvancedRICConfig):
    """Advanced configuration for OAI FLEXRIC."""

    DB_DIR: str | None = Field(default=None)
    DB_NAME: str | None = Field(default=None)


class ORANSCAdvancedRICConfig(GenericAdvancedRICConfig):
    """Advanced configuration for O-RAN SC Near-RT RIC."""

    service_name: str | None = Field(default=None)
    """Kubernetes service name for this component."""

    ric_type_services: dict[str, str] | None = Field(default=None)
    """Unique sibling component types mapped to their Kubernetes services."""


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


class DeployedRICComponent(Deployed5GComponent):
    """5G RIC component deployment."""

    type: RICComponentType = Field()
    """RIC component type."""

    implementation: RICImplementation | None = Field(default=None)
    """RIC component implementation."""

    @model_validator(mode="after")
    def validate_advanced_config(self) -> Self:
        """Validate advanced configuration based on what is supported."""
        return super().validate_advanced_config(
            mapping=ADVANCED_RIC_CONFIG_MAPPING,
            default_model=GenericAdvancedRICConfig,  # type: ignore
        )


class RICDeployment(Deployed5GNetwork):
    """Deployment state for one RIC network."""

    implementation: RICImplementation = Field(default=RICImplementation.OAI)
    """RIC implementation."""

    components: dict[str, DeployedRICComponent] = Field(default_factory=dict)
    """RIC Kubernetes components."""

    @model_validator(mode="after")
    def validate_supported_ric_component_types(self) -> Self:
        """Validate component support for the selected RIC implementation."""

        self.validate_supported_component_types(supported=SUPPORTED_RIC_COMPONENTS)
        return self


# model used to resolve ric references in ran components
class MergedRIC(SingleRICComponent, DeployedRICComponent):
    """Merged single RIC/E2Term model (they both have the needed 'e2' in their config)."""

    # override type since SingleRICComponent expects 'type' to be literal 'ric'
    type: RICComponentType = Field()
    """RIC component type."""
