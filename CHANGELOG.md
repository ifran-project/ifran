# Changelog

## [0.0.5]
- Moved hardware-specific RU information (`vendor` and `model`) from the metamodel to the deployment model.
- Added explicit `name` field to provisionable resources (nodes, UEs, and RUs).
- Renamed `Miscellaneous` to `MiscellaneousManagement` for naming consistency.
- Added automatic detection of file-based `plain_text_config` inputs.
- Updated default versions of Free5GC, OAI RAN, and OAI Core.
- Enhanced resource provisioning, SSH configuration handling, and deployment robustness.
- Improved component installation and lifecycle management.

## [0.0.4]
- Added support for custom Helm charts, environment variables, entrypoint commands, and rendered files.
- Added file and directory copy support between resources and components.
- Improved resource provisioning and management.
- Added API reference documentation and expanded tutorials and examples.
- Improved documentation for LLM compatibility.

## [0.0.3]
- Added OAI and OCUDU RAN deployment support, including split CU/DU architectures.
- Added advanced RAN configuration parameters and radio configuration options.
- Added support for OAI NR UE and srsUE deployments.
- Improved RAN configuration, reconciliation, and deployment reliability.

## [0.0.2]
- Added advanced configuration support for OAI RAN components.
- Improved component creation and configuration options.
- Added remote command execution and improved component log retrieval.
- Improved UE networking and deployment management.
- Enhanced provisioning, SSH handling, and deployment reliability.
- Froze Python dependencies.

## [0.0.1]
- Introduced the initial 5G network orchestration framework.
- Added support for deploying and managing 5G core, RAN, UE, and RIC components.
- Introduced resource provisioning and reservation mechanisms.
- Added support for multiple RAN and core implementations.
- Introduced component lifecycle management and deployment reconciliation.
