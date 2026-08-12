"""RIC deployment models."""


from orchestrator.models.deployment.k8s import K8SComponent


# TODO later
class RICDeployment(K8SComponent):
    """5G RAN Intelligent Controller deployment."""
