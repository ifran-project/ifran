"""RICs lifecycle management."""

import json
import re
from pathlib import Path

from orchestrator.deployment.helm import HelmManagement
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.ric import RICComponentType, RICImplementation
from orchestrator.utils.ansible import get_ansible_inventory_line, run_ansible_role
from orchestrator.utils.common import build_safe_helm_name
from orchestrator.utils.common_5g import ComponentDependencyGraph
from orchestrator.utils.ric import reconcile_rics


RIC_COMPONENT_DEPENDENCIES: ComponentDependencyGraph = {
    RICComponentType.A1MEDIATOR: frozenset({
        RICComponentType.DBAAS,
    }),
    RICComponentType.XAPP_ONBOARDER: frozenset({
        RICComponentType.APPMGR,
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.APPMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.CHARTMUSEUM,
    }),
    RICComponentType.RTMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
        RICComponentType.SUBMGR,
    }),
    RICComponentType.E2MGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
    }),
    RICComponentType.E2TERM: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.RTMGR,
        RICComponentType.E2MGR,
    }),
    RICComponentType.SUBMGR: frozenset({
        RICComponentType.DBAAS,
        RICComponentType.APPMGR,
        RICComponentType.E2MGR,
    }),
}


class RICManagement(HelmManagement):
    """RICs lifecycle management class."""

    def reconcile(self) -> None:
        """Ensure the RICs are ready to be managed."""

        super().reconcile()

        reconcile_rics(
            rics_meta=self.mutatable_metamodel.rics,
            rics_k8s=self.deployment_model.rics,
        )


    async def run_action(self, **kwargs) -> None:
        """Run Helm action on RICs."""
        await super().run_action(category=Category5G.RIC, **kwargs)


    async def deploy(
            self,
            order: ComponentDependencyGraph | None = RIC_COMPONENT_DEPENDENCIES,
            **kwargs,
        ) -> None:
        """Orchestrate RIC component deployment."""
        await super().deploy(order=order, **kwargs)


    async def prepare(self, components: list[str] | None = None, **kwargs) -> None:
        """Prepare RIC component Helm charts."""
        await super().prepare(components=components, **kwargs)


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


    async def remove(self, **kwargs) -> None:
        """Remove/uninstall RIC components."""
        await self.uninstall(**kwargs)


    async def install_xapp(
            self,
            source_dir: str | Path,
            ric_name: str | None = None,
            node: str | None = None,
            xapp_namespace: str = "ricxapp",
            wait_for_e2: bool = True,
        ) -> None:
        """Onboard, install, register, and verify an OSC xApp."""

        source_path = Path(source_dir).resolve()
        config_path = source_path / "config-file.json"
        schema_path = source_path / "schema.json"
        if not config_path.is_file() or not schema_path.is_file():
            raise ValueError("xApp source directory must contain config-file.json and schema.json")

        descriptor = json.loads(config_path.read_text())
        xapp_name = descriptor.get("name")
        xapp_version = descriptor.get("version")
        if not isinstance(xapp_name, str) or not xapp_name or not isinstance(xapp_version, str) or not xapp_version:
            raise ValueError("xApp descriptor must define non-empty name and version fields")
        if build_safe_helm_name(xapp_name) != xapp_name or not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.+_-]*", xapp_version):
            raise ValueError("xApp name or version is not safe for Helm and shell arguments")

        if ric_name is None:
            if len(self.mutatable_metamodel.rics) != 1:
                raise ValueError("ric_name is required when the metamodel contains multiple RICs")
            ric_name = next(iter(self.mutatable_metamodel.rics))

        ric_meta = self.mutatable_metamodel.rics.get(ric_name)
        ric_k8s = self.deployment_model.rics.get(ric_name)
        if ric_meta is None or ric_k8s is None:
            raise ValueError(f"RIC {ric_name!r} is missing from the metamodel or deployment model")
        if ric_meta.implementation is not RICImplementation.ORAN_SC:
            raise ValueError("xApp lifecycle management is currently supported only for O-RAN SC RICs")

        required_types = {
            RICComponentType.APPMGR,
            RICComponentType.CHARTMUSEUM,
            RICComponentType.E2MGR,
            RICComponentType.RTMGR,
            RICComponentType.XAPP_ONBOARDER,
        }
        components_by_type = {component.type: name for name, component in ric_meta.components.items()}
        missing = required_types - components_by_type.keys()
        if missing:
            raise ValueError(f"RIC {ric_name!r} is missing required xApp components: {sorted(item.value for item in missing)}")

        node_name, node_data = self._get_master_node(node)
        component_services = {
            component_type: ric_k8s.components[components_by_type[component_type]].service_name
            for component_type in required_types
        }
        namespace = ric_k8s.components[components_by_type[RICComponentType.XAPP_ONBOARDER]].namespace

        await run_ansible_role(
            role="ric/xapp/install",
            runner_path=(
                f"{self.deployment_model.params.ansible.runner_path}/ric/{ric_name}/xapps/{xapp_name}/install"
            ),
            roles_path=self.deployment_model.params.ansible.roles_path,
            hosts=node_name,
            inventory=get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
            become=True,
            inputs={
                "xapp_name": xapp_name,
                "xapp_version": xapp_version,
                "xapp_config_file": str(config_path),
                "xapp_schema_file": str(schema_path),
                "xapp_namespace": xapp_namespace,
                "ric_namespace": namespace,
                "appmgr_service": component_services[RICComponentType.APPMGR],
                "e2mgr_service": component_services[RICComponentType.E2MGR],
                "rtmgr_service": component_services[RICComponentType.RTMGR],
                "xapp_onboarder_service": component_services[RICComponentType.XAPP_ONBOARDER],
                "wait_for_e2": wait_for_e2,
            },
        )

    async def audit_xapp(
            self,
            xapp_name: str,
            ric_name: str | None = None,
            node: str | None = None,
            xapp_namespace: str = "ricxapp",
            indication_timeout: int = 180,
        ) -> None:
        """Verify xApp deployment, registration, routing, E2, and indications."""

        if build_safe_helm_name(xapp_name) != xapp_name:
            raise ValueError("xApp name is not safe for Helm and shell arguments")
        if indication_timeout < 0:
            raise ValueError("indication_timeout must be non-negative")
        if ric_name is None:
            if len(self.mutatable_metamodel.rics) != 1:
                raise ValueError("ric_name is required when the metamodel contains multiple RICs")
            ric_name = next(iter(self.mutatable_metamodel.rics))

        ric_meta = self.mutatable_metamodel.rics.get(ric_name)
        ric_k8s = self.deployment_model.rics.get(ric_name)
        if ric_meta is None or ric_k8s is None:
            raise ValueError(f"RIC {ric_name!r} is missing from the metamodel or deployment model")
        components_by_type = {component.type: name for name, component in ric_meta.components.items()}
        required_types = {RICComponentType.APPMGR, RICComponentType.E2MGR, RICComponentType.RTMGR}
        missing = required_types - components_by_type.keys()
        if missing:
            raise ValueError(f"RIC {ric_name!r} is missing audit components: {sorted(item.value for item in missing)}")

        node_name, node_data = self._get_master_node(node)
        component_services = {
            component_type: ric_k8s.components[components_by_type[component_type]].service_name
            for component_type in required_types
        }
        namespace = ric_k8s.components[components_by_type[RICComponentType.APPMGR]].namespace
        await run_ansible_role(
            role="ric/xapp/audit",
            runner_path=(
                f"{self.deployment_model.params.ansible.runner_path}/ric/{ric_name}/xapps/{xapp_name}/audit"
            ),
            roles_path=self.deployment_model.params.ansible.roles_path,
            hosts=node_name,
            inventory=get_ansible_inventory_line(resource_name=node_name, resource_data=node_data),
            become=True,
            inputs={
                "xapp_name": xapp_name,
                "xapp_namespace": xapp_namespace,
                "ric_namespace": namespace,
                "appmgr_service": component_services[RICComponentType.APPMGR],
                "e2mgr_service": component_services[RICComponentType.E2MGR],
                "rtmgr_service": component_services[RICComponentType.RTMGR],
                "indication_timeout": indication_timeout,
            },
        )
