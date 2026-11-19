"""RAN deployment lifecycle management."""

from typing import Any, override

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.ran import RANComponent, RANComponentType

from ifran.deployment.helm import HelmManagement
from ifran.models.provisioning import MergedRU, RUVendor
from ifran.models.ran import DeployedRANComponent
from ifran.utils.common_5g import (
    ComponentDependencyGraph,
)
from ifran.utils.ran import reconcile_ran
from ifran.utils.ru import build_benetel_ru_config, run_parallel_ru_configuration

RAN_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RANComponentType.DU: frozenset(
        {
            RANComponentType.CU,
            RANComponentType.CU_CP,
            RANComponentType.CU_UP,
        }
    ),
    RANComponentType.CU_UP: frozenset({RANComponentType.CU_CP}),
}


class RANManagement(HelmManagement):
    """RAN deployment lifecycle management class."""

    @override
    def reconcile(self) -> None:
        """Ensure the 5G RAN is ready for deployment by resolving its components' configs."""

        super().reconcile()

        reconcile_ran(
            metamodel=self.mutable_metamodel,
            deployment_model=self.deployment_model,
        )

    # override category
    @override
    async def run_action(self, **kwargs) -> dict[str, str] | None:
        """Run Helm action on RAN components."""
        return await super().run_action(category=Category5G.RAN, **kwargs)

    # NOTE don't use kwargs to expose the function signature
    @override
    def add_component(
        self,
        name: str,
        component_meta: RANComponent | None = None,
        component_deployment: DeployedRANComponent | None = None,
        merged: dict[str, Any] | None = None,
    ) -> None:
        """Add or update a RAN component if it exists."""
        super().add_component(
            name=name,
            category=Category5G.RAN,
            component_meta=component_meta,
            component_deployment=component_deployment,
            merged=merged,
        )

    @override
    def remove_component(self, name: str) -> None:
        """Remove a RAN component."""
        super().remove_component(category=Category5G.RAN, name=name)

    # override dependency graph
    @override
    async def install(
        self,
        order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
        **kwargs,
    ) -> None:
        """Install RAN components."""
        await super().install(order=order, **kwargs)

    # override dependency graph
    @override
    async def deploy(
        self,
        order: ComponentDependencyGraph | None = RAN_COMPONENT_DEPENDENCIES,
        **kwargs,
    ) -> None:
        """Orchestrate full RAN deployment."""
        await super().deploy(order=order, **kwargs)

    async def configure_rus(
        self,
        components: list[str] | None = None,
        force: bool = False,
        ignore_failures: bool = False,
        quiet: bool = False,
    ) -> None:
        """
        Load the configuration of the Benetel RUs of gNBs and DUs (all of them or a given subset), then reboot them.

        The RU /etc/ru_config.cfg is generated from the models and pushed from the gNB or DU node, which must reach
        the RU management IP (first RU 'ips' entry). The RU is only rebooted when its configuration changes, or
        always with 'force'. It then waits for the radio initialization of each RU, and fails if it did not succeed.
        """

        configurations = []
        for name, component_meta in self.mutable_metamodel.ran.components.items():
            if (components is not None and name not in components) or component_meta.type not in [
                RANComponentType.GNB,
                RANComponentType.DU,
            ]:
                continue

            # resolved RU reference (MergedRU), or a simulated RU without vendor
            ru: MergedRU = component_meta.config.ru  # type: ignore
            if getattr(ru, "vendor", None) is not RUVendor.BENETEL:
                continue

            # the reference is resolved in the mutable metamodel, the RU name is in the original one
            ru_name = self.metamodel.ran.components[name].config.ru  # type: ignore
            node_name = self.deployment_model.ran.components[name].node_name

            if node_name is None or node_name not in self.deployment_model.nodes:
                raise ValueError(f"RAN component {name!r} with Benetel RU {ru_name!r} needs a deployment 'node_name'.")

            if not ru.ips:
                raise ValueError(f"Benetel RU {ru_name!r} has no IP: set its management IP in the RU 'ips'.")

            node_data = self.deployment_model.nodes[node_name]
            configurations.append(
                {
                    "component_name": name,
                    "ru_name": ru_name,
                    "ru_config": build_benetel_ru_config(
                        component_name=name,
                        component_meta=component_meta,  # type: ignore
                        node_name=node_name,
                        node_data=node_data,
                    ),
                    "ru_ip": str(ru.ips[0]),
                    "node_name": node_name,
                    "node_data": node_data,
                }
            )

        if not configurations:
            raise RuntimeError("No target gNB or DU uses a Benetel RU.")

        await run_parallel_ru_configuration(
            configurations=configurations,
            ansible_params=self.deployment_model.params.ansible,
            force=force,
            ignore_failures=ignore_failures,
            quiet=quiet,
        )
