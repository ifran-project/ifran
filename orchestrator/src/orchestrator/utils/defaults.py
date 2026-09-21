"""Defaults mainly for 5G core and RAN images."""

from orchestrator.models.deployment.k8s import (
    Capabilities,
    ContainerImage,
    SecurityContext,
)
from orchestrator.models.meta.common import Category5G
from orchestrator.models.meta.core import CoreComponentType, CoreImplementation
from orchestrator.models.meta.ran import RANComponentType, RANImplementation
from orchestrator.models.meta.ric import RICComponentType, RICImplementation
from orchestrator.models.meta.ru import RUType
from orchestrator.models.meta.ue import UEImplementation, UEType

DEFAULT_CORE_IMAGES: dict[CoreImplementation, dict[CoreComponentType, ContainerImage]] = {
    CoreImplementation.OAI: {
        CoreComponentType.AMF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-amf", image_tag="v2.2.0"),
        CoreComponentType.AUSF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-ausf", image_tag="v2.2.0"),
        CoreComponentType.LMF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-lmf", image_tag="v2.2.0"),
        CoreComponentType.NRF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nrf", image_tag="v2.2.0"),
        CoreComponentType.NSSF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nssf", image_tag="v2.2.0"),
        CoreComponentType.PCF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-pcf", image_tag="v2.2.0"),
        CoreComponentType.SMF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-smf", image_tag="v2.2.0"),
        CoreComponentType.UDM: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-udm", image_tag="v2.2.0"),
        CoreComponentType.UDR: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-udr", image_tag="v2.2.0"),
        CoreComponentType.UPF: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-upf", image_tag="v2.2.0"),
    },
    CoreImplementation.OPEN5GS: {
        CoreComponentType.AMF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.AUSF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.BSF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.NRF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.NSSF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.PCF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.SCP: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.SMF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.UDM: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.UDR: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
        CoreComponentType.UPF: ContainerImage(repository="docker.io/gradiant/open5gs", image_tag="2.8.0"),
    },
    CoreImplementation.FREE5GC: {
        CoreComponentType.AMF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-amf", image_tag="v4.2.3"),
        CoreComponentType.AUSF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-ausf", image_tag="v4.2.3"),
        CoreComponentType.BSF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-bsf", image_tag="v4.2.3"),
        CoreComponentType.CHF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-chf", image_tag="v4.2.3"),
        CoreComponentType.NEF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-nef", image_tag="v4.2.3"),
        CoreComponentType.NRF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-nrf", image_tag="v4.2.3"),
        CoreComponentType.NSSF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-nssf", image_tag="v4.2.3"),
        CoreComponentType.PCF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-pcf", image_tag="v4.2.3"),
        CoreComponentType.SMF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-smf", image_tag="v4.2.3"),
        CoreComponentType.UDM: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-udm", image_tag="v4.2.3"),
        CoreComponentType.UDR: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-udr", image_tag="v4.2.3"),
        CoreComponentType.UPF: ContainerImage(repository="ghcr.io/ziyad-mabrouk/free5gc-upf", image_tag="v4.2.3"),
    },
}


DEFAULT_RAN_IMAGES: dict[RANImplementation, dict[RUType, dict[RANComponentType, ContainerImage]]] = {
    RANImplementation.OAI: {
        RUType.USRP: {
            RANComponentType.GNB: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.DU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU_CP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU_UP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nr-cuup", image_tag="2026.w31"),
        },
        RUType.SIMULATED: {
            RANComponentType.GNB: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.DU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU_CP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb", image_tag="2026.w31"),
            RANComponentType.CU_UP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nr-cuup", image_tag="2026.w31"),
        },
        RUType.AW2S: {
            RANComponentType.GNB: ContainerImage(repository="docker.io/r2labuser/oai-gnb-aw2s-csi", image_tag="2026.w31"),
            RANComponentType.CU: ContainerImage(repository="docker.io/r2labuser/oai-gnb-aw2s-csi", image_tag="2026.w31"),
            RANComponentType.DU: ContainerImage(repository="docker.io/r2labuser/oai-gnb-aw2s-csi", image_tag="2026.w31"),
            RANComponentType.CU_CP: ContainerImage(repository="docker.io/r2labuser/oai-gnb-aw2s-csi", image_tag="2026.w31"),
            RANComponentType.CU_UP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nr-cuup", image_tag="2026.w31"),
        },
        RUType.BENETEL: {
            RANComponentType.GNB: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb-fhi72", image_tag="2026.w31"),
            RANComponentType.CU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb-fhi72", image_tag="2026.w31"),
            RANComponentType.DU: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb-fhi72", image_tag="2026.w31"),
            RANComponentType.CU_CP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-gnb-fhi72", image_tag="2026.w31"),
            RANComponentType.CU_UP: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nr-cuup", image_tag="2026.w31"),
        },
    },
    RANImplementation.OCUDU: {
        RUType.USRP: {
            RANComponentType.GNB: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-gnb-uhd", image_tag="release_26_04"),
            RANComponentType.CU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu", image_tag="release_26_04"),
            RANComponentType.DU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-du-uhd", image_tag="release_26_04"),
            RANComponentType.CU_CP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-cp", image_tag="release_26_04"),
            RANComponentType.CU_UP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-up", image_tag="release_26_04"),
        },
        RUType.BENETEL: {
            RANComponentType.GNB: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-gnb-dpdk", image_tag="release_26_04"),
            RANComponentType.CU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu", image_tag="release_26_04"),
            RANComponentType.DU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-du-dpdk", image_tag="release_26_04"),
            RANComponentType.CU_CP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-cp", image_tag="release_26_04"),
            RANComponentType.CU_UP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-up", image_tag="release_26_04"),
        },
        RUType.SIMULATED: {
            RANComponentType.GNB: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-gnb-zmq", image_tag="release_26_04"),
            RANComponentType.CU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu", image_tag="release_26_04"),
            RANComponentType.DU: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-du-zmq", image_tag="release_26_04"),
            RANComponentType.CU_CP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-cp", image_tag="release_26_04"),
            RANComponentType.CU_UP: ContainerImage(repository="ghcr.io/ziyad-mabrouk/ocudu-cu-up", image_tag="release_26_04"),
        },
    },
    RANImplementation.UERANSIM: {
        RUType.SIMULATED: {
            RANComponentType.GNB: ContainerImage(repository="docker.io/gradiant/ueransim", image_tag="3.3.0"),
        },
    },
}


DEFAULT_UE_IMAGES: dict[UEImplementation, dict[UEType, ContainerImage]] = {
    UEImplementation.OAI: {
        UEType.CONTAINERIZED: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-nr-ue", image_tag="2026.w31"),
    },
    UEImplementation.UERANSIM: {
        UEType.CONTAINERIZED: ContainerImage(repository="docker.io/gradiant/ueransim", image_tag="3.3.0"),
    },
    UEImplementation.SRSUE: {
        UEType.CONTAINERIZED: ContainerImage(repository="ghcr.io/ziyad-mabrouk/srsue", image_tag="release_25_10"), # TODO upload image with this tag
    },
}


DEFAULT_RIC_IMAGES: dict[RICImplementation, dict[RICComponentType, ContainerImage]] = {
    RICImplementation.OAI: {
        RICComponentType.RIC: ContainerImage(repository="docker.io/oaisoftwarealliance/oai-flexric", image_tag="develop"),
    },
    RICImplementation.ORAN_SC: {
        RICComponentType.DBAAS: ContainerImage(repository="docker.io/r2labuser/ric-plt-dbaas", image_tag="0.6.5"),
        RICComponentType.E2MGR: ContainerImage(repository="docker.io/r2labuser/ric-plt-e2mgr", image_tag="6.0.8"),
        RICComponentType.E2TERM: ContainerImage(repository="docker.io/r2labuser/ric-plt-e2", image_tag="6.0.8"),
        RICComponentType.RTMGR: ContainerImage(repository="docker.io/r2labuser/ric-plt-rtmgr", image_tag="0.9.7"),
        RICComponentType.SUBMGR: ContainerImage(repository="docker.io/r2labuser/ric-plt-submgr", image_tag="0.10.4"),
        RICComponentType.APPMGR: ContainerImage(repository="docker.io/r2labuser/ric-plt-appmgr", image_tag="0.5.9-helm3"),
        RICComponentType.CHARTMUSEUM: ContainerImage(repository="docker.io/chartmuseum/chartmuseum", image_tag="v0.8.2"),
        RICComponentType.XAPP_ONBOARDER: ContainerImage(repository="docker.io/r2labuser/xapp-onboarder", image_tag="1.0.8-helm3"),
        RICComponentType.A1MEDIATOR: ContainerImage(repository="docker.io/r2labuser/ric-plt-a1", image_tag="3.2.3"),
    },
}


DEFAULT_POD_IMAGES = {
    Category5G.CORE: DEFAULT_CORE_IMAGES,
    Category5G.RAN: DEFAULT_RAN_IMAGES,
    Category5G.UE: DEFAULT_UE_IMAGES,
    Category5G.RIC: DEFAULT_RIC_IMAGES,
}


CORE_POD_PRIVILEGES: dict[CoreImplementation, dict[CoreComponentType, SecurityContext]] = {
    CoreImplementation.OAI: {
        CoreComponentType.AMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.AUSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.LMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NRF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NSSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.PCF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.SMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDM: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDR: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UPF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN", "SYS_ADMIN"], drop=["ALL"])),
    },
    CoreImplementation.OPEN5GS: {
        CoreComponentType.AMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.AUSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.BSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NRF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NSSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.PCF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.SCP: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.SMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDM: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDR: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UPF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN", "SYS_ADMIN"], drop=["ALL"])),
    },
    CoreImplementation.FREE5GC: {
        CoreComponentType.AMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.AUSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.BSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.CHF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NEF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NRF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.NSSF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.PCF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.SMF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDM: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UDR: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
        CoreComponentType.UPF: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN", "SYS_ADMIN"], drop=["ALL"])),
    },
}


RAN_POD_PRIVILEGES: dict[RANImplementation, dict[RANComponentType, SecurityContext]] = {
    RANImplementation.OAI: {
        RANComponentType.CU_CP: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
        RANComponentType.CU_UP: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
        RANComponentType.CU: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
        RANComponentType.DU: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
        RANComponentType.GNB: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
    },
    RANImplementation.OCUDU: {
        RANComponentType.CU_CP: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK", "PERFMON"], drop=["ALL"])),
        RANComponentType.CU_UP: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK", "PERFMON"], drop=["ALL"])),
        RANComponentType.CU: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK", "PERFMON"], drop=["ALL"])),
        RANComponentType.DU: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK", "PERFMON"], drop=["ALL"])),
        RANComponentType.GNB: SecurityContext(capabilities=Capabilities(add=["SYS_NICE", "IPC_LOCK", "PERFMON"], drop=["ALL"])),
    },
    RANImplementation.UERANSIM: {
        RANComponentType.GNB: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
    },
}


UE_POD_PRIVILEGES: dict[UEImplementation, dict[UEType, SecurityContext]] = {
    UEImplementation.OAI: {
        UEType.CONTAINERIZED: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN", "NET_RAW", "SYS_NICE", "IPC_LOCK"], drop=["ALL"])),
    },
    UEImplementation.UERANSIM: {
        UEType.CONTAINERIZED: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
    },
    UEImplementation.SRSUE: {
        UEType.CONTAINERIZED: SecurityContext(capabilities=Capabilities(add=["NET_ADMIN"], drop=["ALL"])),
    }
}


# no particular privileges for now
RIC_POD_PRIVILEGES: dict[RICImplementation, dict[str, SecurityContext]] = {}


POD_PRIVILEGES = {
    Category5G.CORE: CORE_POD_PRIVILEGES,
    Category5G.RAN: RAN_POD_PRIVILEGES,
    Category5G.UE: UE_POD_PRIVILEGES,
    Category5G.RIC: RIC_POD_PRIVILEGES,
}
