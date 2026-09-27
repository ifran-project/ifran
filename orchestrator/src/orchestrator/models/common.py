"""Common deployment-related models."""

from typing import Any, Self

from metamodel.models.base import StrictBaseModel
from metamodel.models.core import CoreComponentType
from metamodel.models.ran import RANComponentType
from metamodel.models.ric import RICComponentType
from pydantic import BaseModel, Field, model_validator

from orchestrator.models.k8s import K8SComponent


class Deployed5GComponent(K8SComponent):
    """Base class for generic 5G network component."""

    type: str = Field()
    """Component type in the 5G category it's in (e.g. amf, upf, gnb, ... etc)."""

    # populated by parent metamodel validator before validation
    implementation: str | None = Field(default=None)
    """Component 5G category's implementation (e.g. oai, open5gs, srsran, ... etc)."""

    # incoming 'advanced_config' is validated into concrete model afterwards
    advanced_config: Any = Field(default=None)
    """Component configuration specific to the implementation."""

    plain_text_config: str | None = Field(default=None)
    """Raw configuration file content."""


    def validate_advanced_config(self, mapping: dict, default_model: BaseModel) -> Self:
        """Validate component advanced configuration's raw dict based on what is supported in the mapping."""

        # advanced config can be none
        if self.advanced_config is None:
            return self

        if isinstance(self.advanced_config, BaseModel):
            return self

        advanced_config_model: BaseModel = mapping.get(self.implementation, {}).get(self.type)
        if advanced_config_model:
            # use type-specific advanced config model if found
            self.advanced_config = advanced_config_model.model_validate(self.advanced_config)
        else:
            # use default advanced config model
            self.advanced_config = default_model.model_validate(self.advanced_config)

        return self


class Deployed5GNetwork(StrictBaseModel):
    """Base class for 5G network deployment."""

    implementation: str | None = Field(default=None)
    """5G network implementation."""

    components: dict[str, Deployed5GComponent] = Field(default_factory=dict)
    """5G network components."""


    @model_validator(mode="after")
    def populate_component_implementation(self) -> Self:
        """Populate 5G network component implementation after validation."""

        # if network implementation is None, each component should define its implementation
        if self.implementation:
            for component in self.components.values():
                if component.implementation is None:
                    component.implementation = self.implementation
        return self


    def validate_supported_component_types(self, supported: dict) -> Self:
        """Validate if requested 5G network component types are available for given implementation."""

        for name, component in self.components.items():
            if component.type not in supported[self.implementation]:
                raise ValueError(f"Requested component {name!r} of type {component.type!r} "
                                 f"is not supported in {self.implementation!r} implementation.")
        return self


type ComponentType = CoreComponentType | RANComponentType | RICComponentType

type ComponentDependencyGraph = dict[ComponentType, frozenset[ComponentType]]
