# Hydro Monitor v1.0.0 Release Candidate 1

Canonical Semantic Version: `1.0.0-rc.1`

This is the first formal public-release candidate for the Hydro Monitor project. Earlier numbered builds were internal development milestones and are not part of the public Semantic Versioning sequence.

## Release goals

RC1 freezes the intended v1.0.0 hardware allocation and monitoring behaviour while adding the release-management and recovery features required for a reproducible public installation.

## Added for RC1

- authoritative root `VERSION` file using Semantic Versioning
- runtime version loading from that single source of truth
- installer copies `VERSION` into `/opt/hydro-monitor`
- explicit fresh-install versus upgrade detection
- fallback detection of development-era installations that lacked an installed `VERSION` file
- timestamped configuration backup before upgrades
- safe configuration merge that preserves user settings and DS18B20 assignments while enforcing the fixed permanent-board GPIO map
- preservation of Pushover secrets, historical readings, event logs and runtime state during upgrades
- clean virtual-environment rebuild during installation
- `uninstall.sh` with data-preserving default behaviour
- explicit `--purge` uninstall mode for complete project-data removal
- power-loss-resilient CSV appends using flush and fsync
- startup recovery of a single interrupted final CSV record
- startup validation and regeneration of malformed disposable current-status JSON
- tests covering release-version consistency, upgrade merging, uninstall policy and power-loss recovery

## Deliberately unchanged

RC1 does not change the established monitoring behaviour, GPIO assignments, alarm thresholds, alarm timing, local dashboard behaviour, RTC arrangement or optional Pushover alarm policy.

## Promotion to v1.0.0

RC1 should be promoted to final v1.0.0 only after physical commissioning on the permanent Raspberry Pi controller, including an observed recovery after an unexpected power interruption.
