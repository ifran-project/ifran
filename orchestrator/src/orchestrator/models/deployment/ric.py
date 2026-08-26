"""RIC deployment models."""

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.k8s import K8SComponent


class K8SRICComponent(K8SComponent):
    """Kubernetes deployment state for one RIC component."""

    service_name: str = Field(default="")
    """Kubernetes service name for this component."""

    ric_services: dict[str, str] = Field(default_factory=dict)
    """Sibling component names mapped to their Kubernetes services."""

    ric_type_services: dict[str, str] = Field(default_factory=dict)
    """Unique sibling component types mapped to their Kubernetes services."""


class RICDeployment(BlueprintBaseModel):
    """Deployment state for one RIC network."""

    components: dict[str, K8SRICComponent] = Field(default_factory=dict)
