"""RAN deployment models."""

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.k8s import K8SComponent


class K8SRANComponent(K8SComponent):
    """5G RAN component deployment."""


class RANDeployment(BlueprintBaseModel):
    """5G RAN deployment."""

    components: dict[str, K8SRANComponent] = Field(default_factory=dict)
    """5G RAN Kubernetes components."""
