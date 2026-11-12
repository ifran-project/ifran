# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Migrated the codebase to GitHub as `ifran`.

## [0.0.5] - 2026-11-04

### Added
- Explicit `name` field on provisionable resources (nodes, UEs and RUs).
- Automatic detection of file-based `plain_text_config` inputs.

### Changed
- **Breaking:** Hardware-specific RU information (`vendor` and `model`) moved from the metamodel to the deployment model.
- **Breaking:** Renamed `Miscellaneous` to `MiscellaneousManagement` for naming consistency.
- Updated default versions of Free5GC, OAI RAN and OAI Core.
- Improved resource provisioning, SSH configuration handling and deployment robustness.
- Improved component installation and lifecycle management.

## [0.0.4] - 2026-10-30

### Added
- Support for custom Helm charts, environment variables, entrypoint commands and rendered files.
- File and directory copy between resources and components.
- API reference documentation, plus expanded tutorials and examples.

### Changed
- Improved resource provisioning and management.
- Improved documentation for LLM compatibility.

## [0.0.3] - 2026-10-11

### Added
- OAI and OCUDU RAN deployment support, including split CU/DU architectures.
- Advanced RAN configuration parameters and radio configuration options.
- OAI NR UE and srsUE deployments.

### Changed
- Improved RAN configuration, reconciliation and deployment reliability.

## [0.0.2] - 2026-10-02

### Added
- Advanced configuration support for OAI RAN components.
- Remote command execution on components.

### Changed
- Improved component creation and configuration options.
- Improved component log retrieval.
- Improved UE networking and deployment management.
- Enhanced provisioning, SSH handling and deployment reliability.
- Froze Python dependency versions.

## [0.0.1] - 2026-10-01

### Added
- Initial 5G network orchestration framework.
- Deployment and management of 5G core, RAN, UE and RIC components.
- Resource provisioning and reservation mechanisms.
- Support for multiple RAN and core implementations.
- Component lifecycle management and deployment reconciliation.

[Unreleased]: https://github.com/ifran-project/ifran/compare/v0.0.5...HEAD
[0.0.5]: https://github.com/ifran-project/ifran/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/ifran-project/ifran/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/ifran-project/ifran/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/ifran-project/ifran/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/ifran-project/ifran/releases/tag/v0.0.1
