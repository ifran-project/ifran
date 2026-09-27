"""Base deployment management class."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal, Self

import yaml
from metamodel.models.metamodel import MetaModel
from metamodel.models.ru import RUType
from metamodel.models.ue import UEType

from orchestrator.models.core import DeployedCoreComponent
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.provisioning import (
    ProvisionableResource,
    ProvisionableRU,
    ProvisionableUE,
    ProvisioningCategory,
)
from orchestrator.models.ran import DeployedRANComponent
from orchestrator.models.ric import DeployedRICComponent
from orchestrator.models.ue import DeployedUE
from orchestrator.utils.ansible import get_ansible_inventory_line
from orchestrator.utils.utils import deep_merge, sync_dict_keys


class BaseManagement:
    """Base class for all the Post-5G blueprint's deployment lifecycle management classes."""

    def __init__(self, metamodel: MetaModel, deployment_model: DeploymentModel) -> None:
        self.metamodel = metamodel.model_copy(deep=True)

        # original metamodel should not be mutated to maintain consistency
        # use a mutable metamodel copy that will be used to resolve references and prepare for deployment
        self.mutable_metamodel = metamodel.model_copy(deep=True)

        # deployment model is allowed to mutate to store changes (resolved references)
        self.deployment_model = deployment_model.model_copy(deep=True)

        # reconcile meta model and deployment model on init
        self.reconcile()


    @classmethod
    def from_merged(
            cls,
            merged_model: dict[str, Any] | None = None,
            input_file: Literal["json", "yaml"] = "yaml",
            path: str | None = None,
        ) -> Self:
        """Initialize deployment management class from single merged models input."""

        if merged_model is None and path is None:
            raise ValueError("No input was provided.")

        if path:
            with Path(path).open("r", encoding="utf-8") as f:
                merged_model = json.load(f) if input_file == "json" else yaml.safe_load(f)

        metamodel = MetaModel.model_validate(merged_model, extra="allow")
        deployment_model = DeploymentModel.model_validate(merged_model, extra="allow")

        return cls(metamodel, deployment_model)


    def output(self) -> tuple[MetaModel, DeploymentModel]:
        """Output metamodel and potentially modified deployment model."""

        return self.metamodel, self.deployment_model


    def output_merged(
            self,
            output: Literal["dict", "json", "yaml"] = "dict",
            path: str | None = None,
        ) -> dict[str, Any] | str | None:
        """Output merged dictionary from deployment and meta model."""

        merged = self.deployment_model.model_dump(
            mode="json",
            include={"params", "nodes", "miscellaneous"}
            ) | {
            "core": deep_merge(self.metamodel.core, self.deployment_model.core),
            "ran": deep_merge(self.metamodel.ran, self.deployment_model.ran),
            "rus": deep_merge(self.metamodel.rus, self.deployment_model.rus),
            "ues": deep_merge(self.metamodel.ues, self.deployment_model.ues),
            "ric": deep_merge(self.metamodel.ric, self.deployment_model.ric),
        }

        if output == "json":
            merged = json.dumps(merged)
        elif output == "yaml":
            merged = yaml.safe_dump(merged)
        else:
            merged = str(merged)

        if path:
            with Path(path).open("w", encoding="utf-8") as f:
                f.write(merged)
        else:
            return merged
        return None


    def reconcile(self) -> None:
        """
        Reconcile deployment model based on metamodel data.

        This guarantees that all subsequent actions can safely assume that both models are fully synchronized.
        """

        # core components
        sync_dict_keys(
            target_dict=self.deployment_model.core.components,
            source_dict=self.metamodel.core.components,
            default_factory=DeployedCoreComponent,
            populate_type=True,
        )
        # ran components
        sync_dict_keys(
            target_dict=self.deployment_model.ran.components,
            source_dict=self.metamodel.ran.components,
            default_factory=DeployedRANComponent,
            populate_type=True,
        )
        # rus (only real rus are provisionable)
        sync_dict_keys(
            target_dict=self.deployment_model.rus,
            source_dict={k: ru for k, ru in self.metamodel.rus.items() if ru.type is not RUType.SIMULATED},
            default_factory=lambda: ProvisionableRU(category=ProvisioningCategory.RU),
        )
        # ues (only cots ues are provisionable, others are deployed)
        sync_dict_keys(
            target_dict=self.deployment_model.ues,
            source_dict=self.metamodel.ues,
            default_factory=(
                lambda type:
                    ProvisionableUE(category=ProvisioningCategory.UE, type=type) if type is UEType.COTS
                    else DeployedUE(type=type)
            ),
            populate_type=True,
        )
        # ric components
        sync_dict_keys(
            target_dict=self.deployment_model.ric.components,
            source_dict=self.metamodel.ric.components,
            default_factory=DeployedRICComponent,
            populate_type=True,
        )

    def get_ansible_inventory(self, path: str | None = None) -> str | None:
        """Generate an Ansible .ini inventory from nodes and ues."""

        # get groups based on node roles => {role: nodes with that role}
        groups: dict[str, dict[str, ProvisionableResource]] = defaultdict(dict)

        for node_name, node_data in self.deployment_model.nodes.items():
            for role in node_data.roles:
                groups[f"{role.value}_nodes"][node_name] = node_data

        # add ues as their own group (only cots ues are provisionable)
        ues = {
            ue_name: ue_data
            for ue_name, ue_data in self.deployment_model.ues.items()
            if ue_data.type is UEType.COTS
        }
        if ues:
            groups["ues"] = ues # type: ignore

        lines: list[str] = []
        for role, role_resources in groups.items():
            lines.append(f"[{role}]")
            for name, resource in role_resources.items():
                lines.append(get_ansible_inventory_line(
                    resource_name=name,
                    resource_data=resource, # type: ignore
                ))
            lines.append("") # new line between sections

        inventory = "\n".join(lines)
        if path:
            with Path(path).open("w", encoding="utf-8") as f:
                f.write(inventory)
        else:
            return inventory
        return None
