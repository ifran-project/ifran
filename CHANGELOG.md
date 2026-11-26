# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.0.7] - 2026-11-26

### Added
- A separate `configure` action for COTS UEs, so configuration can be performed independently of connecting to the network (#4).
- SSH access and remote command execution on radio units (RUs), with shared SSH defaults and per-resource overrides (#5).
- A public Kubernetes `wait` action, kubelet CPU and topology manager settings, and containerd registry mirror configuration (#25).
- Support for rendering `rendered_files` and `custom_rendered_files` together.

### Changed
- **Breaking:** COTS UE setup now requires calling `configure()` before `connect()` (#4).
- **Breaking:** `ProvisionableUE.is_connected` is replaced by `connection_status`, with `not_configured`, `configured` and `connected` states.
- **Breaking:** Rename the SSH pipelining setting from `ssh_pipelining` to `pipelining`; SSH common arguments are generated from the connection settings.
- Core deployment no longer applies a fixed default component order.
- Advanced configuration defaults are defined and validated by the Pydantic models across core, RAN and UE components. The schemas now cover additional OAI and OCUDU settings (#20, #23, #24).
- Ansible actions retry failures with exponential backoff, include detailed failure output, and stop cleanly when cancelled.
- Free5GC components use the official Docker Hub images by default.

### Fixed
- Preserve explicitly supplied advanced configuration values, including `0` and values equal to model defaults, and correct missing fields and defaults across supported components (#20, #23, #24).
- SSH connections through multiple jumphosts issue (#28).
- OAI PCF start-up failures caused by unsupported database-backed policies: mount default local policy files in the chart and use them by default (#18).
- Handle Kubernetes readiness waits when a Kubernetes or Calico system pod is removed, and make Kubernetes deployment actions idempotent.
- Helm installations using relative chart paths.
- Free5GC and Open5GS NSSF chart configuration issues.

## [0.0.6] - 2026-11-13

### Changed
- Migrated the codebase to GitHub as `ifran`.

### Fixed
- OCUDU and srsUE deployments failing when `advanced_config` is not set.
- String `plain_text_config` values failing with a "OSError: filename too long" error.

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

[Unreleased]: https://github.com/ifran-project/ifran/compare/v0.0.7...HEAD
[0.0.7]: https://github.com/ifran-project/ifran/compare/v0.0.6...v0.0.7
[0.0.6]: https://github.com/ifran-project/ifran/compare/v0.0.5...v0.0.6
[0.0.5]: https://github.com/ifran-project/ifran/compare/v0.0.4...v0.0.5
[0.0.4]: https://github.com/ifran-project/ifran/compare/v0.0.3...v0.0.4
[0.0.3]: https://github.com/ifran-project/ifran/compare/v0.0.2...v0.0.3
[0.0.2]: https://github.com/ifran-project/ifran/compare/v0.0.1...v0.0.2
[0.0.1]: https://github.com/ifran-project/ifran/releases/tag/v0.0.1
