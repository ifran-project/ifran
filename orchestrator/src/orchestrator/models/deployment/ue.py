"""UE deployment models."""

from orchestrator.models.deployment.k8s import K8SComponent


class UEDeployment(K8SComponent):
    """UE deployment."""
