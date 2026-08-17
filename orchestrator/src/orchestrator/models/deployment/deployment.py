"""Deployment model."""


from typing import Any

from pydantic import Field

from orchestrator.models.common import BlueprintBaseModel
from orchestrator.models.deployment.ansible import AnsibleParams
from orchestrator.models.deployment.core import CoreDeployment
from orchestrator.models.deployment.k8s import K8SParams
from orchestrator.models.deployment.provisioning import (
    BIProvisioner,
    NodeProvisioningType,
    POSProvisioner,
    ProvisionableNode,
    ProvisionableRU,
    ProvisionableUE,
    Provisioner,
    ProvisioningCategory,
)
from orchestrator.models.deployment.ran import RANDeployment
from orchestrator.models.deployment.ric import RICDeployment
from orchestrator.models.deployment.ue import UEDeployment


class DeploymentParams(BlueprintBaseModel):
    """Global deployment parameters."""

    ansible: AnsibleParams = Field(default_factory=AnsibleParams)
    """Ansible global parameters."""

    k8s: K8SParams = Field(default_factory=K8SParams)
    """Kubernetes global default parameters."""

    provisioning: dict[str, Any] | None = Field(default=None)
    """Global default provisioning parameters."""


class DeploymentModel(BlueprintBaseModel):
    """Model for 5G blueprint deployement parameters and status."""

    params: DeploymentParams = Field(default_factory=DeploymentParams)
    """Global deployment parameters."""

    provisioners: dict[str, Provisioner] = Field(default_factory=lambda: {
        "bi": BIProvisioner(category=ProvisioningCategory.NODE, type=NodeProvisioningType.BI),
        "pos": POSProvisioner(category=ProvisioningCategory.NODE, type=NodeProvisioningType.POS),
    })
    """Provisioners."""

    nodes: dict[str, ProvisionableNode] = Field(default_factory=lambda: {
        "node1": ProvisionableNode(category=ProvisioningCategory.NODE),
        "node2": ProvisionableNode(category=ProvisioningCategory.NODE),
        "node3": ProvisionableNode(category=ProvisioningCategory.NODE),
    })
    """Nodes provisioning."""

    core_deployment: CoreDeployment = Field(default_factory=CoreDeployment)
    """5G core deployment."""

    ran_deployment: RANDeployment = Field(default_factory=RANDeployment)
    """5G RAN deployment."""

    rus: dict[str, ProvisionableRU] = Field(default_factory=dict)
    """RU provisioning."""

    ues: dict[str, ProvisionableUE] = Field(default_factory=dict)
    """UEs provisioning."""

    simulated_ues: dict[str, UEDeployment] = Field(default_factory=dict)
    """UEs deployment."""

    rics: dict[str, RICDeployment] = Field(default_factory=dict)
    """RICs deployment."""

    miscellaneous: dict[str, Any] | None = Field(default=None)
    """Miscellaneous data for pipelining purposes."""
