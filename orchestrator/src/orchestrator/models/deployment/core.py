"""Core deployment models."""

from pydantic import Field, IPvAnyAddress

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.k8s import K8SComponent


class K8SCoreComponent(K8SComponent):
    """5G core component deployment."""


class CoreDatabaseParams(BlueprintBaseModel):
    """5G core database deployment parameters."""

    is_installed: bool = Field(default=False)
    """If 5G core databse is deployed or not."""

    ip: IPvAnyAddress | None = Field(default=None)
    """5G core databse IP address."""

    force_database_scheduling: bool = Field(default=False)
    """If True, label will be added to ensure scheduling only on nodes with database label AND core label."""


class CoreDeployment(BlueprintBaseModel):
    """5G core deployment."""

    components: dict[str, K8SCoreComponent] = Field(default_factory=dict)
    """5G core Kubernetes components."""

    database: CoreDatabaseParams = Field(default_factory=CoreDatabaseParams)
    """5G core database parameters."""
