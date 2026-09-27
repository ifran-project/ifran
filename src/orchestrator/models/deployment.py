"""Deployment model."""

from typing import Annotated, Any

from metamodel.models.base import StrictBaseModel
from pydantic import Field

from orchestrator.models.ansible import AnsibleParams
from orchestrator.models.core import CoreDeployment
from orchestrator.models.k8s import K8SParams
from orchestrator.models.provisioning import (
    BIProvisioner,
    POSProvisioner,
    ProvisionableNode,
    ProvisionableRU,
    ProvisionableUE,
    Provisioner,
    ProvisioningCategory,
    ProvisioningType,
)
from orchestrator.models.ran import RANDeployment
from orchestrator.models.ric import RICDeployment
from orchestrator.models.ue import DeployedUE


class DeploymentParams(StrictBaseModel):
    """Global deployment parameters."""

    ansible: AnsibleParams = Field(default_factory=AnsibleParams)
    """Ansible global parameters."""

    k8s: K8SParams = Field(default_factory=K8SParams)
    """Kubernetes global default parameters."""

    provisioning: dict[str, Any] = Field(default_factory=dict)
    """Global default provisioning parameters."""


class DeploymentModel(StrictBaseModel):
    """Model for the 5G deployment parameters and status."""

    params: DeploymentParams = Field(default_factory=DeploymentParams)
    """Global deployment parameters."""

    provisioners: dict[str, Provisioner] = Field(default_factory=lambda: {
        "bi": BIProvisioner(type=ProvisioningType.BI),
        "pos": POSProvisioner(type=ProvisioningType.POS),
    })
    """Provisioners."""

    nodes: dict[str, ProvisionableNode] = Field(default_factory=lambda: {
        "node1": ProvisionableNode(category=ProvisioningCategory.NODE),
        "node2": ProvisionableNode(category=ProvisioningCategory.NODE),
        "node3": ProvisionableNode(category=ProvisioningCategory.NODE),
        "node4": ProvisionableNode(category=ProvisioningCategory.NODE),
    })
    """Deployment nodes (node names should correspond to their actual hostname)."""

    core: CoreDeployment = Field(default_factory=CoreDeployment)
    """5G core deployment."""

    ran: RANDeployment = Field(default_factory=RANDeployment)
    """5G RAN deployment."""

    rus: dict[str, ProvisionableRU] = Field(default_factory=dict)
    """RUs."""

    ues: dict[str, Annotated[ProvisionableUE | DeployedUE, Field(discriminator="type")]] = Field(default_factory=dict)
    """UEs."""

    ric: RICDeployment = Field(default_factory=RICDeployment)
    """RIC deployment."""

    miscellaneous: dict[str, Any] | None = Field(default=None)
    """Miscellaneous data for pipelining purposes."""
