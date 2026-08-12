"""Kubernetes 5G components Helm lifecycle management."""

from typing import Literal

from orchestrator.deployment.common import BaseBlueprintManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ue import UEType
from orchestrator.utils.helm import ComponentDependencyGraph, run_parallel_helm_action


class HelmManagement(BaseBlueprintManagement):
    """Kubernetes 5G components Helm lifecycle management class."""

    async def run_action(
        self,
        category: Category5G,
        action: Literal["prepare", "install", "uninstall"],
        components: list[str] | None = None,
        node: str | None = None,
        order: ComponentDependencyGraph | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
    ):
        """Run Helm action on 5G components of a specific category."""
        
        # k8s master node is the deployment entry point by default
        target_node_name = node or self.deployment_model.params.k8s.master_node
        if not target_node_name:
            raise ValueError("Target node for Helm action is undefined. Provide a node or set the master node.")

        target_node_data = self.deployment_model.nodes.get(target_node_name)
        if target_node_data is None:
            raise ValueError("Target node for Helm action is not defined in deployment model.")

        # resolve dictionaries based on category
        match category:
            case Category5G.CORE:
                all_meta = self.mutatable_metamodel.core.components
                all_k8s = self.deployment_model.core_deployment.components

            case Category5G.RAN:
                all_meta = self.mutatable_metamodel.ran.components
                all_k8s = self.deployment_model.ran_deployment.components

            case Category5G.UE:
                all_meta = {ue for ue in self.mutatable_metamodel.ues if ue.type == UEType.SIMULATED}
                all_k8s = self.deployment_model.deployed_ues

            case Category5G.RIC:
                all_meta = self.mutatable_metamodel.rics
                all_k8s = self.deployment_model.rics

        # filter for specific components if requested
        if components is None:
            target_meta = all_meta
            target_k8s = all_k8s
        else:
            target_meta = {k: v for k, v in all_meta.items() if k in components}
            target_k8s = {k: v for k, v in all_k8s.items() if k in components}

        await run_parallel_helm_action(
            components_meta=target_meta,
            components_k8s=target_k8s,
            action=action,
            node_name=target_node_name,
            node_data=target_node_data,
            ansible_params=self.deployment_model.params.ansible,
            order=order,
            force=force,
            ignore_invalid_states=ignore_invalid_states,
            ignore_failures=ignore_failures,
        )
