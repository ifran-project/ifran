"""RIC deployment models."""

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.k8s import K8SComponent


class K8SRICComponent(K8SComponent):
    """5G RAN Intelligent Controller component deployment."""


class RICDeployment(BlueprintBaseModel):
    """Deployment state for one RIC network."""

    components: dict[str, K8SRICComponent] = Field(default_factory=dict)
