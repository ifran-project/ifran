"""RICs lifecycle management."""

from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.helm import run_parallel_helm_action
from orchestrator.utils.ric import (
    RIC_COMPONENT_DEPENDENCIES,
    create_ric_namespaces,
    get_ric_helm_components,
    get_ric_helm_inputs,
    reconcile_rics,
)


class RICManagement(HelmManagement):
    """RICs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the RICs are ready to be managed."""

        super().reconcile()

        reconcile_rics(
            rics_meta=self.mutatable_metamodel.rics,
            rics_k8s=self.deployment_model.rics,
        )


    async def run_action(
            self,
            action: Literal["prepare", "install", "uninstall"],
            components: list[str] | None = None,
            node: str | None = None,
            **kwargs,
        ) -> None:
        """Deploy RIC components through the standard Helm roles."""
        node_name, node_data = self._get_master_node(node)
        all_meta, all_k8s = get_ric_helm_components(
            self.mutatable_metamodel.rics, self.deployment_model.rics,
        )
        if components is not None:
            all_meta = {key: value for key, value in all_meta.items() if key in components}
            all_k8s = {key: value for key, value in all_k8s.items() if key in components}
        if action == "install":
            await create_ric_namespaces(all_meta, node_name, node_data, self.deployment_model.params.ansible)
        await run_parallel_helm_action(
            components_meta=all_meta,
            components_k8s=all_k8s,
            action=action,
            node_name=node_name,
            node_data=node_data,
            ansible_params=self.deployment_model.params.ansible,
            component_role_inputs={
                name: get_ric_helm_inputs(meta)
                for name, meta in all_meta.items()
            },
            **kwargs,
        )


    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)


    async def install(
            self,
            components: list[str] | None = None,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Install RIC components in dependency order."""
        await super().install(components=components, order=order, **kwargs)


    async def uninstall(
            self,
            components: list[str] | None = None,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Uninstall RIC components in reverse dependency order."""
        await super().uninstall(components=components, order=order, **kwargs)
