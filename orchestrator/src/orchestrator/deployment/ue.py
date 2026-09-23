"""UEs lifecycle management."""

from typing import Literal

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ue import UEType
from orchestrator.utils.common_5g import RANComponentType, get_5g_components_by_type
from orchestrator.utils.ue import reconcile_ues, run_parallel_ue_action


class UEManagement(HelmManagement):
    """UEs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the UEs are ready to be managed."""

        super().reconcile()

        # get gnbs and dus from metamodel
        grouped = get_5g_components_by_type(self.mutable_metamodel.ran.components)
        gnbs = grouped.get(RANComponentType.GNB, {})
        dus = grouped.get(RANComponentType.DU, {})
        gnb_components_meta = gnbs | dus # gnbs + dus

        # get gnbs and dus from deployment model (keys of meta and deployment models should be in sync by this point)
        gnb_components_k8s = {k: self.deployment_model.ran_deployment.components[k] for k, v in gnb_components_meta.items()}

        reconcile_ues(
            ues_meta=self.mutable_metamodel.ues,
            ues_k8s=self.deployment_model.containerized_ues,
            slices=self.mutable_metamodel.slices,
            gnb_components_meta=gnb_components_meta,
            gnb_components_k8s=gnb_components_k8s,
            rus_meta=self.mutable_metamodel.rus,
            rus_provisioning=self.deployment_model.rus,
        )


    async def run_action(
            self,
            action: Literal["prepare", "install", "uninstall", "connect", "disconnect"],
            ues: list[str] | None = None,
            node: str | None = None,
            force: bool = False,
            ignore_invalid_states: bool = True,
            ignore_failures: bool = False,
        ) -> None:
        """Run Helm action on containerized UEs."""

        containarized_actions = ["prepare", "install", "uninstall"]
        cots_actions = ["connect", "disconnect"]

        all_ues = self.mutable_metamodel.ues

        if action in containarized_actions:
            all_meta = {k: v for k, v in all_ues.items() if v.type is UEType.CONTAINERIZED}
        else:
            all_meta = {k: v for k, v in all_meta.items() if v.type is UEType.COTS}

        # filter for specific components if requested
        target_meta = all_meta if ues is None else {k: v for k, v in all_meta.items() if k in ues}

        # validate action by ue type
        for ue_name, ue_meta in target_meta.items():
            if (
                (ue_meta.type is UEType.CONTAINERIZED and action not in containarized_actions) or
                (ue_meta.type is UEType.COTS and action not in cots_actions)
                ):
                    raise RuntimeError(f"Unsupported action {action!r} for UE {ue_name!r} of type {ue_meta.type.value.upper()!r}.")

        if action in containarized_actions:
            await super().run_action(
                category=Category5G.UE,
                action=action,
                components=ues,
                node=node,
                force=force,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
                )
        else:
            await run_parallel_ue_action(
                ues_meta=target_meta,
                ues_prov={ue_name: self.deployment_model.ues[ue_name] for ue_name in target_meta},
                action=action,
                provisioners=self.deployment_model.provisioners,
                provisioning_params=self.deployment_model.params.provisioning,
                ansible_params=self.deployment_model.params.ansible,
                force=force,
                ignore_invalid_states=ignore_invalid_states,
                ignore_failures=ignore_failures,
            )


    async def prepare(self, ues: list[str] | None = None, **kwargs) -> None:
        """Prepare  containarized UEs Helm charts."""
        await self.run_action(action="prepare", ues=ues, **kwargs)


    async def install(self, ues: list[str] | None = None, **kwargs) -> None:
        """Install containarized UEs via Helm."""
        await self.run_action(action="install", ues=ues, **kwargs)


    async def uninstall(self, ues: list[str] | None = None, **kwargs) -> None:
        """Uninstall containarized UEs via Helm."""
        await self.run_action(action="uninstall", ues=ues, **kwargs)


    async def deploy(self, **kwargs) -> None:
        """Prepare and install containarized UEs via Helm."""
        await self.prepare(**kwargs)
        await self.install(**kwargs)


    async def connect(self, ues: list[str] | None = None, **kwargs) -> None:
        """Connect COTS UEs via provisioner."""
        await self.run_action(action="connect", ues=ues, **kwargs)


    async def disconnect(self, ues: list[str] | None = None, **kwargs) -> None:
        """Disconnect COTS UEs via provisioner."""
        await self.run_action(action="dicconnect", ues=ues, **kwargs)
