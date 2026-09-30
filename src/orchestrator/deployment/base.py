"""Base deployment management class."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Literal

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

    def __init__(  # noqa: PLR0917
            self,
            preceding: BaseManagement | None = None,
            metamodel: MetaModel | None = None,
            deployment_model: DeploymentModel | None = None,
            merged: dict[str, Any] | None = None,
            metamodel_file: str | None = None,
            metamodel_file_type: Literal["json", "yaml"] = "yaml",
            deployment_model_file: str | None = None,
            deployment_model_file_type: Literal["json", "yaml"] = "yaml",
            merged_file: str | None = None,
            merged_file_type: Literal["json", "yaml"] = "yaml",
        ) -> None:

        if preceding:
            self.metamodel = preceding.metamodel.model_copy(deep=True)
            self.deployment_model = preceding.deployment_model.model_copy(deep=True)

        elif metamodel and deployment_model:
            # original metamodel should not be mutated to maintain consistency
            self.metamodel = metamodel.model_copy(deep=True)
             # deployment model is allowed to mutate to store deployment state
            self.deployment_model = deployment_model.model_copy(deep=True)

        elif metamodel_file and deployment_model_file:
            if metamodel_file_type == "json":
                self.metamodel = MetaModel.from_json_file(metamodel_file)
            elif merged_file_type == "yaml":
                self.metamodel = MetaModel.from_yaml_file(metamodel_file)

            if deployment_model_file_type == "json":
                self.deployment_model = DeploymentModel.from_json_file(deployment_model_file)
            elif merged_file_type == "yaml":
                self.deployment_model = DeploymentModel.from_yaml_file(deployment_model_file)

        elif merged:
            self.metamodel, self.deployment_model = self._from_merged(merged)

        elif merged_file:
            with Path(merged_file).open("r", encoding="utf-8") as f:
                merged_input = json.load(f) if merged_file_type == "json" else yaml.safe_load(f)

            self.metamodel, self.deployment_model = self._from_merged(merged_input)

        else:
            raise ValueError("No input was provided.")

        # use a mutable metamodel copy that will be used to resolve references and prepare for deployment
        self.mutable_metamodel = self.metamodel.model_copy(deep=True)

        # reconcile meta model and deployment model on init
        self.reconcile()


    def _from_merged(self, merged: dict[str, Any]) -> tuple[MetaModel, DeploymentModel]:
        """Return deployment model and meta model from single merged input."""

        metamodel = MetaModel.model_validate(merged, extra="allow")
        deployment_model = DeploymentModel.model_validate(merged, extra="allow")
        return metamodel, deployment_model


    def output(
            self,
            metamodel_file: str | None = None,
            metamodel_file_type: Literal["json", "yaml"] = "yaml",
            deployment_model_file: str | None = None,
            deployment_model_file_type: Literal["json", "yaml"] = "yaml",
        ) -> tuple[MetaModel, DeploymentModel]:
        """Output metamodel and potentially modified deployment model."""

        if metamodel_file:
            with Path(metamodel_file).open("w", encoding="utf-8") as f:
                f.write(
                    self.metamodel.to_yaml() if metamodel_file_type == "yaml"
                    else self.metamodel.model_dump_json()
                )

        if deployment_model_file:
            with Path(deployment_model_file).open("w", encoding="utf-8") as f:
                f.write(
                    self.deployment_model.to_yaml() if deployment_model_file_type == "yaml"
                    else self.deployment_model.model_dump_json()
                )

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

        if path:
            with Path(path).open("w", encoding="utf-8") as f:
                f.write(str(merged))
        else:
            return merged
        return None


    def reconcile(self) -> None:
        """
        Reconcile the metamodel and deployment model before deployment.

        This function should be ovewriten by inheriting classes to add their
        reconciliation logic on top of the default synchronization.
        """
        self.synchronize()


    def synchronize(self) -> None:
        """
        Synchronize the deployment model based on metamodel data.

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

        # NOTE the deployment model should retrigger its validation functions for the newly added components
        # this is mainly important to populate the implementation for the added core, ric and ran components
        self.deployment_model = DeploymentModel.model_validate(self.deployment_model.model_dump())


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
