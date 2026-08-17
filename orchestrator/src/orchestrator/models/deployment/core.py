"""Core deployment models."""

from pydantic import Field, IPvAnyAddress

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.k8s import K8SComponent


class K8SCoreComponent(K8SComponent):
    """5G core component deployment."""


class CoreDeployment(BlueprintBaseModel):
    """5G core deployment."""

    components: dict[str, K8SCoreComponent] = Field(default_factory=dict)
    """5G core Kubernetes components."""

    is_database_present: bool = Field(default=False)
    """If 5G core databse is deployed or not."""

    database_ip: IPvAnyAddress | None = Field(default=None)
    """5G core databse IP address."""
