"""Kubernetes 5G components Helm lifecycle management."""

from typing import Literal

from orchestrator.deployment.common import BaseBlueprintManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ue import UEType
from orchestrator.utils.helm import ComponentDependencyGraph, run_parallel_helm_action


class HelmManagement(BaseBlueprintManagement):
    """Kubernetes 5G components Helm lifecycle management class."""

    def _get_master_node(self, node: str | None) -> tuple[str, str]:
        """Helper to get the master node."""

        node_name = node or self.deployment_model.params.k8s.master_node
        if not node_name or node_name not in self.deployment_model.nodes:
            raise RuntimeError(
                f"Target node {node_name!r} for database action is invalid or missing from deployment model."
            )

        node_data = self.deployment_model.nodes[node_name]

        return node_name, node_data


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
    ) -> None:
        """Run Helm action on 5G components of a specific category."""
        
        # k8s master node is the deployment entry point by default
        node_name, node_data = self._get_master_node(node)

        # resolve dictionaries based on category
        match category:
            case Category5G.CORE:
                all_meta = self.mutable_metamodel.core.components
                all_k8s = self.deployment_model.core_deployment.components

            case Category5G.RAN:
                all_meta = self.mutable_metamodel.ran.components
                all_k8s = self.deployment_model.ran_deployment.components

            case Category5G.UE:
                all_meta = {
                    ue_name: ue_meta
                    for ue_name, ue_meta in self.mutable_metamodel.ues.items()
                    if ue_meta.type is UEType.CONTAINERIZED
                } # only containerized UEs are k8s-deployable
                all_k8s = self.deployment_model.containerized_ues

            case Category5G.RIC:
                all_meta = self.mutable_metamodel.rics
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
            node_name=node_name,
            node_data=node_data,
            ansible_params=self.deployment_model.params.ansible,
            order=order,
            force=force,
            ignore_invalid_states=ignore_invalid_states,
            ignore_failures=ignore_failures,
        )


    async def prepare(self, components: list[str] | None = None, **kwargs) -> None:
        """Prepare components Helm charts."""
        await self.run_action(action="prepare", components=components, **kwargs)


    async def install(self, components: list[str] | None = None, **kwargs) -> None:
        """Install components via Helm."""
        await self.run_action(action="install", components=components, **kwargs)


    async def uninstall(self, components: list[str] | None = None, **kwargs) -> None:
        """Uninstall components via Helm."""
        await self.run_action(action="uninstall", components=components, **kwargs)


    async def deploy(self, order: ComponentDependencyGraph | None = None, **kwargs) -> None:
        """Prepare and install components via Helm."""
        await self.prepare(**kwargs)
        await self.install(order=order, **kwargs)


    # only for naming consistency
    async def remove(self, **kwargs) -> None:
        """Remove/uninstall components via Helm."""
        await self.uninstall(**kwargs)
