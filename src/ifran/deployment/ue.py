"""UEs lifecycle management."""

from typing import Any, Literal, override

from metamodel_3gpp.models.common import Category5G
from metamodel_3gpp.models.ue import UE, UEType

from ifran.deployment.helm import HelmManagement
from ifran.models.ue import DeployedUE
from ifran.utils.ue import reconcile_ues, run_parallel_ue_action


class UEManagement(HelmManagement):
    """UEs lifecycle management class."""

    @override
    def reconcile(self) -> None:
        """Ensure the UEs are ready to be managed."""

        super().reconcile()

        reconcile_ues(
            metamodel=self.mutable_metamodel,
            deployment_model=self.deployment_model,
        )

    @override
    async def run_action(  # noqa: PLR0917
        self,
        action: Literal["prepare", "install", "uninstall", "get_logs", "run_cmd", "copy", "connect", "disconnect"],
        components: list[str] | None = None,
        **kwargs,
    ) -> dict[str, str] | None:
        """Run Helm action on containerized UEs."""

        containarized_actions = ["prepare", "install", "uninstall", "get_logs", "run_cmd", "copy"]
        cots_actions = ["connect", "disconnect"]

        all_ues = self.mutable_metamodel.ues

        if action in containarized_actions:
            all_meta = {k: v for k, v in all_ues.items() if v.type is UEType.CONTAINERIZED}
        else:
            all_meta = {k: v for k, v in all_ues.items() if v.type is UEType.COTS}

        # filter for specific components if requested
        target_meta = all_meta if components is None else {k: v for k, v in all_meta.items() if k in components}

        # validate action by ue type
        for ue_name, ue_meta in target_meta.items():
            if (ue_meta.type is UEType.CONTAINERIZED and action not in containarized_actions) or (
                ue_meta.type is UEType.COTS and action not in cots_actions
            ):
                raise RuntimeError(
                    f"Unsupported action {action!r} for UE {ue_name!r} of type {ue_meta.type.value.upper()!r}."
                )

        if action in containarized_actions:
            return await super().run_action(
                category=Category5G.UE,
                action=action,  # type: ignore
                components=components,
                **kwargs,
            )
        if action in cots_actions:
            await run_parallel_ue_action(
                ues_meta=target_meta,
                ues_prov={ue_name: self.deployment_model.ues[ue_name] for ue_name in target_meta},  # type: ignore
                action=action,  # type: ignore
                provisioners=self.deployment_model.provisioners,
                provisioning_params=self.deployment_model.params.provisioning,
                ansible_params=self.deployment_model.params.ansible,
                **kwargs,
            )

        return None

    # NOTE don't use kwargs to expose the function signature
    @override
    def add_component(
        self,
        name: str,
        component_meta: UE | None = None,
        component_deployment: DeployedUE | None = None,
        merged: dict[str, Any] | None = None,
    ) -> None:
        """Add or update a UE if it exists."""
        super().add_component(
            name=name,
            category=Category5G.UE,
            component_meta=component_meta,
            component_deployment=component_deployment,
            merged=merged,
        )

    @override
    def remove_component(self, name: str) -> None:
        """Remove a containarized UE."""
        super().remove_component(category=Category5G.UE, name=name)

    # connect action wrapper
    async def connect(self, ues: list[str] | None = None, **kwargs) -> None:
        """Connect COTS UEs via provisioner."""
        await self.run_action(action="connect", components=ues, **kwargs)

    # disconnect action wrapper
    async def disconnect(self, ues: list[str] | None = None, **kwargs) -> None:
        """Disconnect COTS UEs via provisioner."""
        await self.run_action(action="disconnect", components=ues, **kwargs)
