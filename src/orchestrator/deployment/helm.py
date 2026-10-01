"""Kubernetes 5G components Helm lifecycle management."""

from typing import Any, Literal

from metamodel.models.common import Category5G, Component5G
from metamodel.models.metamodel import MetaModel
from metamodel.models.ue import UEType

from orchestrator.deployment.base import BaseManagement
from orchestrator.models.common import Deployed5GComponent
from orchestrator.models.deployment import DeploymentModel
from orchestrator.models.provisioning import ProvisionableNode
from orchestrator.utils.helm import ComponentDependencyGraph, run_parallel_helm_action
from orchestrator.utils.utils import ReferenceNotFoundError


class HelmManagement(BaseManagement):
    """Kubernetes 5G components Helm lifecycle management class."""

    def _get_deployment_node(self, node: str | None) -> tuple[str, ProvisionableNode]:
        """Helper to get the deployment node information."""

        # chose provided node name if given or the k8s master node in the deployment_model
        if node:
            if node not in self.deployment_model.nodes:
                raise ReferenceNotFoundError(
                    f"Target node {node!r} for Helm action was not found in deployment model nodes."
                )
        else:
            master_node = self.deployment_model.params.k8s.master_node
            if master_node is None:
                raise RuntimeError(
                    f"Target node {node!r} for Helm action was not provided "
                    "and Kubernetes master node does not exist."
                )
            node = master_node

        return node, self.deployment_model.nodes[node]


    def add_component(
            self,
            name: str,
            category: Category5G,
            component_meta: Component5G | None = None,
            component_deployment: Deployed5GComponent | None = None,
            merged: dict[str, Any] | None = None,
        ) -> None:
        """Add or update a 5G component if it exists."""

        # NOTE merged always takes precedence
        if merged:

            # if merged dict is provided, let metamodel and deployment model chose
            # the right pydantic model to validate the added component's meta and deployment
            metamodel = self.metamodel.model_dump(mode="json")
            deployment_model = self.deployment_model.model_dump(mode="json")

            if category is Category5G.UE:
                metamodel["ues"][name] = merged
                deployment_model["ues"][name] = merged

            else:
                metamodel[category.value]["components"][name] = merged
                deployment_model[category.value]["components"][name] = merged

            self.metamodel = MetaModel.model_validate(metamodel, extra="allow")
            self.deployment_model = DeploymentModel.model_validate(deployment_model, extra="allow")

        elif component_meta:

            if category is Category5G.UE:
                self.metamodel.ues[name] = component_meta.model_copy(deep=True) # type: ignore

                if component_deployment:
                    self.deployment_model.ues[name] = component_meta.model_copy(deep=True) # type: ignore
            else:
                getattr(
                    self.metamodel, category.value
                ).components[name] = component_meta.model_copy(deep=True)

                if component_deployment:
                    getattr(
                        self.metamodel, category.value
                    ).components[name] = component_meta.model_copy(deep=True)

        else:
            raise ValueError("No valid input was given.")

        # NOTE make sure the mutable metamodel is reset (resolved references are removed)
        # so the reconciliation can redo it again
        self.mutable_metamodel = self.metamodel.model_copy(deep=True)
        self.reconcile()


    def remove_component(self, name: str, category: Category5G) -> None:
        """Remove a 5G component."""

        match category:
            case Category5G.CORE:
                self.metamodel.core.components.pop(name, None)
                self.mutable_metamodel.core.components.pop(name, None)
            case Category5G.RIC:
                self.metamodel.ric.components.pop(name, None)
                self.mutable_metamodel.ric.components.pop(name, None)
            case Category5G.RAN:
                self.metamodel.ran.components.pop(name, None)
                self.mutable_metamodel.ran.components.pop(name, None)
            case Category5G.UE:
                self.metamodel.ues.pop(name, None)
                self.mutable_metamodel.ues.pop(name, None)

        self.synchronize()


    # NOTE child classes need to override this method with their 5G category
    async def run_action(  # noqa: PLR0917
        self,
        category: Category5G,
        action: Literal["prepare", "install", "uninstall", "get_logs"],
        components: list[str] | None = None,
        node: str | None = None,
        order: ComponentDependencyGraph | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
        """Run Helm action on 5G components of a specific category."""

        # get the node from which the helm action will be executed
        # by default, it is the k8s master node
        node_name, node_data = self._get_deployment_node(node)

        # resolve dictionaries based on category
        match category:
            case Category5G.CORE:
                all_meta = self.mutable_metamodel.core.components
                all_deployment = self.deployment_model.core.components

            case Category5G.RIC:
                all_meta = self.mutable_metamodel.ric.components
                all_deployment = self.deployment_model.ric.components

            case Category5G.RAN:
                all_meta = self.mutable_metamodel.ran.components
                all_deployment = self.deployment_model.ran.components

            case Category5G.UE:
                # only containerized UEs are k8s-deployable
                all_meta = {
                    ue_name: ue_meta
                    for ue_name, ue_meta in self.mutable_metamodel.ues.items()
                    if ue_meta.type is UEType.CONTAINERIZED
                }
                all_deployment = {
                    ue_name: ue_data
                    for ue_name, ue_data in self.deployment_model.ues.items()
                    if ue_data.type is UEType.CONTAINERIZED
                }

        # filter for specific components if requested
        if components is None:
            target_meta = all_meta
            target_deployment = all_deployment
        else:
            target_meta = {k: v for k, v in all_meta.items() if k in components}
            target_deployment = {k: v for k, v in all_deployment.items() if k in components}

        await run_parallel_helm_action(
            components_meta=target_meta, # type: ignore
            components_deployment=target_deployment, # type: ignore
            action=action,
            node_name=node_name,
            node_data=node_data,
            ansible_params=self.deployment_model.params.ansible,
            order=order,
            force=force,
            ignore_invalid_states=ignore_invalid_states,
            ignore_failures=ignore_failures,
            quiet=quiet,
        )


    # wrapper functions for usage convenience
    async def prepare(self, components: list[str] | None = None, **kwargs) -> None:
        """Prepare components Helm charts."""
        await self.run_action(action="prepare", components=components, **kwargs)


    async def install(self, components: list[str] | None = None, **kwargs) -> None:
        """Install components via Helm."""
        await self.run_action(action="install", components=components, **kwargs)


    async def uninstall(self, components: list[str] | None = None, **kwargs) -> None:
        """Uninstall components via Helm."""
        await self.run_action(action="uninstall", components=components, **kwargs)


    async def get_logs(self, components: list[str] | None = None, **kwargs) -> None:
        """Get components logs."""
        await self.run_action(action="get_logs", components=components, **kwargs)


    async def deploy(self, order: ComponentDependencyGraph | None = None, **kwargs) -> None:
        """Prepare and install components via Helm."""
        await self.prepare(**kwargs)
        await self.install(order=order, **kwargs)


    # only for naming consistency with deploy function
    async def remove(self, **kwargs) -> None:
        """Remove/uninstall components via Helm."""
        await self.uninstall(**kwargs)
