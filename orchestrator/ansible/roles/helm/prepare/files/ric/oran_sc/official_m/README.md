# O-RAN SC M-release charts

These charts are vendored from the official `o-ran-sc/ric-plt-ric-dep`
`m-release` branch at commit
`d9298b0865b69847c2ed0885f5077e703e5a6638`.

The orchestrator deploys the official DBaaS, Routing Manager, E2 Manager,
E2 Termination, Subscription Manager, and A1 Mediator charts. It supplies a
small `orchestrator-values.yaml` override containing only the target namespace,
the selected image coordinates, scheduling, and M-release recipe settings.
The official container images and their RMR route/configuration files are not
patched.

AppMgr and xApp Onboarder continue to use the orchestrator's Helm 3 compatible
charts because the upstream M-release lifecycle charts depend on the removed
Helm 2/Tiller API. The AppMgr chart exposes the official
`service-<namespace>-appmgr-http` alias so the official Routing Manager chart
can consume it without changing either image.
