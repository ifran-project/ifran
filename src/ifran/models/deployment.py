"""Deployment model."""

from typing import Annotated, Any

from metamodel_3gpp.models.base import StrictBaseModel
from pydantic import Field, model_validator

from ifran.models.ansible import AnsibleParams
from ifran.models.core import CoreDeployment
from ifran.models.k8s import K8SParams
from ifran.models.provisioning import (
    BIProvisioner,
    POSProvisioner,
    ProvisionableNode,
    ProvisionableRU,
    ProvisionableUE,
    Provisioner,
    ProvisioningCategory,
    ProvisioningType,
)
from ifran.models.ran import RANDeployment
from ifran.models.ric import RICDeployment
from ifran.models.ue import DeployedUE


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
        "node1": ProvisionableNode(name="node1", category=ProvisioningCategory.NODE),
        "node2": ProvisionableNode(name="node2", category=ProvisioningCategory.NODE),
        "node3": ProvisionableNode(name="node3", category=ProvisioningCategory.NODE),
        "node4": ProvisionableNode(name="node4", category=ProvisioningCategory.NODE),
    })
    """Deployment nodes."""

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


    @model_validator(mode="before")
    @classmethod
    def populate_resource_names(cls, data: Any) -> Any:
        """Populate resources (nodes, RUs, UEs) names from their dict keys if a name is not provided."""

        if not isinstance(data, dict):
            return data

        data = data.copy()

        # populate nodes names
        nodes = data.get("nodes")
        if nodes:
            data["nodes"] = {
                name: {**node, "name": node.get("name") if node.get("name") is not None else name}
                for name, node in nodes.items()
            }

        # populate rus names
        rus = data.get("rus")
        if rus:
            data["rus"] = {
                name: {**ru, "name": ru.get("name") if ru.get("name") is not None else name}
                for name, ru in rus.items()
            }

        # populate ues names
        # NOTE only cots ues have a name field
        ues = data.get("ues")
        if ues:
            data["ues"] = {
                name: (
                    {**ue, "name": ue.get("name") if ue.get("name") is not None else name}
                    if ue.get("type") == "cots"
                    else ue
                )
                for name, ue in ues.items()
            }

        return data
