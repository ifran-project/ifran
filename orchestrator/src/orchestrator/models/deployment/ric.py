"""RIC deployment models."""

from enum import StrEnum

from orchestrator.models.deployment.k8s import K8SComponent


class RICType(StrEnum):
    """Supported RAN Intelligent Controller types."""

    # TODO


# TODO later
class RICDeployment(K8SComponent):
    """5G RAN Intelligent Controller deployment."""
