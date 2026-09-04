# O-RAN SC M-release charts

All active O-RAN SC charts are located here at `oran_sc-<component>`,
following the shared Helm role's standard layout. M-release is the supported
O-RAN SC release; there is no separate release-specific chart directory.

The six upstream platform charts are vendored from `o-ran-sc/ric-plt-ric-dep`
`m-release` branch at commit
`d9298b0865b69847c2ed0885f5077e703e5a6638`.

The orchestrator deploys the official DBaaS, Routing Manager, E2 Manager,
E2 Termination, Subscription Manager, and A1 Mediator charts. It supplies a
rendered `values.yaml` merging upstream defaults with the target namespace,
selected image coordinates, scheduling, and M-release recipe settings. The
shared upstream prepare role renders chart metadata and only `values.yaml`
for these six components, using its `rendered_files` input.
The official container images and their RMR route/configuration files are not
patched.

AppMgr and xApp Onboarder continue to use the orchestrator's Helm 3 compatible
charts because the upstream M-release lifecycle charts depend on the removed
Helm 2/Tiller API. The AppMgr chart exposes the official
`service-<namespace>-appmgr-http` alias so the official Routing Manager chart
can consume it without changing either image.
