"""Kubernetes setup lifecycle management."""

from typing import Literal

from ifran.deployment.base import BaseManagement
from ifran.models.k8s import K8SStatus
from ifran.utils.k8s import run_parallel_k8s_setup_action, run_single_k8s_setup_action


class K8SManagement(BaseManagement):
    """Kubernetes setup lifecycle management class."""

    def _get_master_node(self, master_node: str | None = None) -> str:
        """Helper to get the Kubernetes master node."""

        k8s_params = self.deployment_model.params.k8s
        if master_node:
            if master_node in self.deployment_model.nodes:
                k8s_params.master_node = master_node
            else:
                raise RuntimeError(f"Chosen master node {master_node!r} is not defined.")
        elif k8s_params.master_node is None:
            raise RuntimeError("No master node chosen.")

        return k8s_params.master_node

    async def run_action(  # noqa: PLR0917
        self,
        action: Literal["prepare", "create", "join", "remove"],
        nodes: list[str] | None = None,
        force: bool = False,
        ignore_invalid_states: bool = True,
        ignore_failures: bool = False,
        quiet: bool = False,
        retries: int = 5,
    ) -> None:
        """Run Kubernetes setup action on all nodes or a given subset."""

        target_nodes = (
            self.deployment_model.nodes
            if nodes is None
            else {k: v for k, v in self.deployment_model.nodes.items() if k in nodes}
        )

        await run_parallel_k8s_setup_action(
            nodes=target_nodes,
            action=action,
            k8s_params=self.deployment_model.params.k8s,
            ansible_params=self.deployment_model.params.ansible,
            ssh_params=self.deployment_model.params.ssh,
            force=force,
            ignore_invalid_states=ignore_invalid_states,
            ignore_failures=ignore_failures,
            quiet=quiet,
            retries=retries,
        )

    async def prepare(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Prepare nodes for Kubernetes setup."""
        await self.run_action(action="prepare", nodes=nodes, **kwargs)

    async def create(self, master_node: str | None = None, **kwargs) -> None:
        """
        Create Kubernetes control plane on the master node.

        The master node is taken from 'k8s_params' by default or a the one given as argument.
        """

        master_node = self._get_master_node(master_node)

        # NOTE 'run_single_k8s_setup_action' takes care of updating 'k8s_params.join_command' on success
        await self.run_action(action="create", nodes=[master_node], **kwargs)

    async def join(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Join worker nodes to the Kubernetes cluster."""
        await self.run_action(action="join", nodes=nodes, **kwargs)

    async def wait(self, **kwargs) -> None:
        """
        Wait until all Kubernetes system pods are ready on all nodes.

        This runs only once from the master node.
        """

        master_node = self._get_master_node()

        await run_single_k8s_setup_action(
            node_name=master_node,
            node_data=self.deployment_model.nodes[master_node],
            action="wait",
            k8s_params=self.deployment_model.params.k8s,
            ansible_params=self.deployment_model.params.ansible,
            ssh_params=self.deployment_model.params.ssh,
            force=kwargs.get("force", False),
            quiet=kwargs.get("quiet", False),
            retries=kwargs.get("retries", 5),
        )

    async def deploy(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Orchestrate full Kubernetes cluster setup on target nodes (prepare + create + join + wait)."""

        # run prepare in parallel on target nodes
        await self.prepare(nodes=nodes, **kwargs)

        # get ALL successfully prepared nodes
        prepared_nodes = {
            k: v for k, v in self.deployment_model.nodes.items() if v.k8s_status is not K8SStatus.NOT_CONFIGURED
        }

        if not prepared_nodes:
            raise RuntimeError("No nodes were successfully prepared for Kubernetes setup.")

        # resolve master node
        k8s_params = self.deployment_model.params.k8s
        if k8s_params.master_node is None:
            # pick first prepared node as master if not yet defined
            k8s_params.master_node = next(iter(prepared_nodes))

        master_node_name = k8s_params.master_node

        if master_node_name not in prepared_nodes:
            raise RuntimeError(f"Master node {master_node_name!r} was not successfully prepared.")

        # create k8s cluster on the master node
        await self.create(**kwargs)

        # if ignore_errors is False, we need to handle this before continuing
        if not k8s_params.join_command:
            raise RuntimeError(f"Failed to retrieve join command after cluster creation on {master_node_name!r}.")

        # join remaining prepared worker nodes in parallel
        worker_nodes = [name for name in prepared_nodes if name != master_node_name]
        await self.join(nodes=worker_nodes, **kwargs)

        # wait until k8s system pods are ready
        await self.wait(**kwargs)

    async def remove(self, nodes: list[str] | None = None, **kwargs) -> None:
        """Tear down/remove Kubernetes setup from nodes."""
        await self.run_action(action="remove", nodes=nodes, **kwargs)
