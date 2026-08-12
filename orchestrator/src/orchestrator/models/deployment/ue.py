"""UE deployment models."""


from pydantic import Field

from orchestrator.models.deployment.k8s import K8SComponent


# TODO later
class UEDeployment(K8SComponent):
    """UE deployment."""

    is_connected: bool = Field(default=False)
    """If this UE is connected or not."""
