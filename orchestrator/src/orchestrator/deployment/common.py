"""Common deployment management classes and utilities."""

import json
from collections import defaultdict
from typing import Any, Literal

import yaml

from orchestrator.models.deployment.core import K8SCoreComponent
from orchestrator.models.deployment.deployment import DeploymentModel
from orchestrator.models.deployment.provisioning import (
    ProvisionableResource,
    ProvisionableRU,
    ProvisionableUE,
)
from orchestrator.models.deployment.ran import K8SRANComponent
from orchestrator.models.deployment.ric import RICDeployment
from orchestrator.models.deployment.ue import UEDeployment
from orchestrator.models.meta.metamodel import MetaModel
from orchestrator.models.meta.ru import RUType
from orchestrator.models.meta.ue import UEType
from orchestrator.utils.ansible import get_ansible_inventory_line
from orchestrator.utils.common import deep_merge, sync_dict_keys


class BaseBlueprintManagement:
    """Base class for the 5G blueprint deployment lifecycle management classes."""

    def __init__(self, metamodel: MetaModel, deployment_model: DeploymentModel):
        self.metamodel = metamodel.model_copy(deep=True)

        # original metamodel should not be mutated to maintain integrity
        # use a mutable one that will be used to resolve references and prepare for deployment
        self.mutatable_metamodel = metamodel.model_copy(deep=True)

        # deployment model is allowed to mutate to keep track of changes
        self.deployment_model = deployment_model.model_copy(deep=True)

        # reconcile models on init
        self.reconcile()


    def reconcile(self):
        """
        Reconcile deployment model based on metamodel data.
        This is meant to synchronize both models at the start if it's not the case.
        """

        # core components
        sync_dict_keys(
            target_dict=self.deployment_model.core_deployment.components,
            source_dict=self.metamodel.core.components,
            default_factory=K8SCoreComponent,
        )
        # ran components
        sync_dict_keys(
            target_dict=self.deployment_model.ran_deployment.components,
            source_dict=self.metamodel.ran.components,
            default_factory=K8SRANComponent,
        )
        # rus
        sync_dict_keys(
            target_dict=self.deployment_model.rus,
            source_dict={k: ru for k, ru in self.metamodel.rus.items() if ru.type != RUType.SIMULATED}, # only real rus are provisionable
            default_factory=ProvisionableRU,
        )
        # ues
        sync_dict_keys(
            target_dict=self.deployment_model.ues,
            source_dict={k: ue for k, ue in self.metamodel.ues.items() if ue.type == UEType.REAL}, # only real ues are provisionable
            default_factory=ProvisionableUE,
        )
        sync_dict_keys(
            target_dict=self.deployment_model.simulated_ues,
            source_dict={k: ue for k, ue in self.metamodel.ues.items() if ue.type == UEType.SIMULATED},
            default_factory=UEDeployment,
        )
        # rics
        sync_dict_keys(
            target_dict=self.deployment_model.rics,
            source_dict=self.metamodel.rics,
            default_factory=RICDeployment,
        )


    def get_ansible_inventory(self, path: str | None = None) -> str | None:
        """Generate an Ansible .ini inventory from nodes, rus and ues."""

        model = self.deployment_model

        # get groups based on node roles: role -> nodes with that role
        groups: dict[str, dict[str, ProvisionableResource]] = defaultdict(dict)
        for name, node in model.nodes.items():
            for role in node.roles:
                groups[f"{role.value}_nodes"][name] = node

        # add rus and ues as their own groups
        groups["ru"].update(model.rus)
        groups["ue"].update(model.ues)

        lines: list[str] = []
        for role, role_resources in groups.items():
            lines.append(f"[{role}]")
            for name, resource in role_resources.items():
                lines.append(get_ansible_inventory_line(
                    resource_name=name,
                    resource_data=resource
                ))
            lines.append("") # new line between sections

        inventory = "\n".join(lines)
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(inventory)
        else:
            return inventory


    def get_merged(
            self,
            output: Literal["dict", "json", "yaml"] = "dict",
            path: str | None = None
        ) -> dict[str, Any] | str | None:
        """Get merged dictionary from deployment and meta model."""

        merged = self.deployment_model.model_dump(
            mode="json",
            include={"params", "nodes", "miscellaneous"}
            ) | {
            "core": deep_merge(
                        self.metamodel.core,
                        self.deployment_model.core_deployment,
            ),
            "ran": deep_merge(
                    self.metamodel.ran,
                    self.deployment_model.ran_deployment,
            ),
            "rus": deep_merge(
                    self.metamodel.rus,
                    self.deployment_model.rus,
            ),
            "ues": deep_merge(
                        self.metamodel.ues,
                        deep_merge(
                            self.deployment_model.ues,
                            self.deployment_model.simulated_ues,
                        ),
            ),
            "rics": deep_merge(
                        self.metamodel.rics,
                        self.deployment_model.rics,
            ),
        }

        if output == "json":
            merged = json.dumps(merged)
        if output == "yaml":
            merged = yaml.safe_dump(merged)

        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(merged)
        else:
            return merged


    def output(self) -> tuple[MetaModel, DeploymentModel]:
        """Output potentially modified input models."""

        return self.metamodel, self.deployment_model
