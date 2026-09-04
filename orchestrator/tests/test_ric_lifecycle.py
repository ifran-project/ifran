"""Regression checks for RIC-owned naming and Ansible role dispatch."""
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from orchestrator.deployment import RICManagement
from orchestrator.models import DeploymentModel, MetaModel
from orchestrator.utils.ric import build_ric_component_name, get_ric_helm_components, get_ric_helm_inputs
from orchestrator.utils.helm import run_single_helm_action


def manager_for(implementation="oran_sc"):
    components = {"e2_manager": {"type": "e2mgr"}} if implementation == "oran_sc" else {"ric": {"type": "ric"}}
    model = MetaModel.model_validate({"rics": {"sample": {
        "implementation": implementation, "components": components,
    }}})
    return RICManagement(metamodel=model, deployment_model=DeploymentModel())


class RICLifecycleTests(unittest.IsolatedAsyncioTestCase):
    def test_standard_rendering_defaults(self):
        from orchestrator.models.deployment.k8s import HelmParams
        params = HelmParams(chart_name="test", helm_build_dir="/tmp/test")
        self.assertEqual(params.rendered_files, ["values.yaml", "config.yaml"])
        self.assertEqual(HelmParams(chart_name="test", helm_build_dir="/tmp/test", rendered_files=[]).rendered_files, [])

    def test_m_charts_use_standard_paths(self):
        from orchestrator.utils.ric import OFFICIAL_ORAN_SC_M_TYPES
        root = Path(__file__).resolve().parents[1] / "ansible/roles/helm/prepare"
        for component_type in OFFICIAL_ORAN_SC_M_TYPES:
            path = Path("ric/oran_sc") / f"oran_sc-{component_type.value}"
            self.assertTrue((root / "files" / path / "Chart.yaml").is_file())
            self.assertTrue((root / "templates" / path / "values.yaml.j2").is_file())
        manager = manager_for()
        meta, deployed = get_ric_helm_components(manager.mutatable_metamodel.rics, manager.deployment_model.rics)
        inputs = get_ric_helm_inputs(meta["sample-e2_manager"])
        for key in ("helm_chart_source", "helm_values_template", "helm_config_template"):
            self.assertNotIn(key, inputs)

    def test_component_selection_keys_are_unchanged(self):
        self.assertEqual(build_ric_component_name("sample", "e2_manager"), "sample-e2_manager")
        manager = manager_for()
        meta, deployed = get_ric_helm_components(manager.mutatable_metamodel.rics, manager.deployment_model.rics)
        self.assertEqual(list(meta), ["sample-e2_manager"])
        self.assertEqual(list(meta), list(deployed))

    async def test_ric_dispatches_shared_lifecycle_roles(self):
        for implementation in ("oran_sc", "oai"):
            for action in ("prepare", "install", "uninstall"):
                manager = manager_for(implementation)
                with patch.object(manager, "_get_master_node", return_value=("node1", object())), patch(
                    "orchestrator.deployment.ric.run_parallel_helm_action", new_callable=AsyncMock
                ) as execute, patch(
                    "orchestrator.utils.ric.run_ansible_playbook", new_callable=AsyncMock
                ) as namespaces, patch("orchestrator.utils.ric.get_ansible_inventory_line", return_value="node1"):
                    async def install_after_namespace(**kwargs):
                        if implementation == "oran_sc" and action == "install":
                            namespaces.assert_awaited_once()
                    execute.side_effect = install_after_namespace
                    await getattr(manager, action)()
                if implementation == "oran_sc" and action == "install":
                    namespaces.assert_awaited_once()
                else:
                    namespaces.assert_not_awaited()
                self.assertNotIn("role_prefix", execute.call_args.kwargs)
                inputs = execute.call_args.kwargs["component_role_inputs"]
                if implementation == "oai":
                    self.assertEqual(list(inputs.values()), [{}])
                else:
                    self.assertEqual(inputs["sample-e2_manager"]["rendered_files"], ["values.yaml"])
                self.assertEqual(execute.call_args.kwargs["action"], action)

    async def test_namespace_creation_uses_existing_remote_runner(self):
        from orchestrator.utils.ric import create_ric_namespaces
        manager = manager_for()
        meta, _ = get_ric_helm_components(manager.mutatable_metamodel.rics, manager.deployment_model.rics)
        with patch("orchestrator.utils.ric.get_ansible_inventory_line", return_value="node1"), patch(
            "orchestrator.utils.ric.run_ansible_playbook", new_callable=AsyncMock
        ) as execute:
            await create_ric_namespaces(meta, "node1", None, manager.deployment_model.params.ansible)
        play = execute.call_args.kwargs["playbook"][0]
        self.assertEqual(play["hosts"], "node1")
        self.assertNotIn("roles", play)
        self.assertEqual(play["tasks"][0]["kubernetes.core.k8s"], {
            "api_version": "v1", "kind": "Namespace", "name": "ricxapp", "state": "present",
        })

    def test_unused_service_map_is_not_serialized(self):
        manager = manager_for()
        component = manager.deployment_model.rics["sample"].components["e2_manager"]
        self.assertNotIn("ric_services", component.model_dump())
        self.assertEqual(component.service_name, "service-ricplt-e2mgr-http")
        self.assertEqual(component.ric_type_services["e2mgr"], component.service_name)

    async def test_inherited_remove_preserves_uninstall_defaults(self):
        from orchestrator.utils.ric import RIC_COMPONENT_DEPENDENCIES
        manager = manager_for()
        self.assertNotIn("remove", RICManagement.__dict__)
        with patch.object(manager, "run_action", new_callable=AsyncMock) as execute:
            await manager.remove(components=["sample-e2_manager"])
        self.assertEqual(execute.call_args.kwargs["action"], "uninstall")
        self.assertEqual(execute.call_args.kwargs["order"], RIC_COMPONENT_DEPENDENCIES)
        self.assertEqual(execute.call_args.kwargs["components"], ["sample-e2_manager"])

    async def test_executor_preserves_release_name_and_uses_requested_role(self):
        manager = manager_for()
        meta, deployed = get_ric_helm_components(manager.mutatable_metamodel.rics, manager.deployment_model.rics)
        with patch("orchestrator.utils.helm.get_ansible_inventory_line", return_value="node1"), patch(
            "orchestrator.utils.helm.run_ansible_role", new_callable=AsyncMock
        ) as execute:
            await run_single_helm_action(
                component_name="sample-e2_manager", component_meta=meta["sample-e2_manager"],
                component_k8s=deployed["sample-e2_manager"], action="prepare",
                node_name="node1", node_data=None, ansible_params=manager.deployment_model.params.ansible,
                role_inputs=get_ric_helm_inputs(meta["sample-e2_manager"]),
            )
        self.assertEqual(execute.call_args.kwargs["role"], "helm/prepare")
        self.assertEqual(execute.call_args.kwargs["inputs"]["chart_name"], "oran-sc-sample-e2-manager")


if __name__ == "__main__":
    unittest.main()
