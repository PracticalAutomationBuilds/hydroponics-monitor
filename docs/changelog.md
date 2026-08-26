# Changelog

All notable changes to the Hydroponics Monitor project will be documented in this file.

The public release history begins with Version 1.0.0.

Earlier versions through the v9.x development line were internal development builds used while the hardware, software and documentation were being designed. They are not treated as public releases.

## Unreleased

No changes recorded yet.

## 1.0.0-rc.1 - 2026-08-26

First public release candidate of the Hydroponics Monitor.

### Added

- Raspberry Pi 3 Model B monitoring application
- local web dashboard
- reservoir and grow-pipe DS18B20 temperature monitoring
- DHT22 ambient temperature and relative-humidity monitoring
- SEN0368 return-water detection
- fail-safe reservoir low-level float monitoring
- red, amber and green status indicators
- active buzzer alarm output
- maintained alarm-inhibit switch
- DS3231 real-time clock support
- historical CSV logging and event logging
- optional Pushover remote notifications
- interactive DS18B20 probe assignment utility
- hardware self-test mode
- RTC configuration and verification utilities
- installation and upgrade support
- safe uninstall utility with optional purge mode
- root `VERSION` file as the authoritative installed software version
- release-structure and regression tests
- power-loss resilience for persistent monitoring data
- automatic recovery of an interrupted final `readings.csv` record
- automatic regeneration of malformed disposable live-status data
- complete wiring, installation, commissioning and troubleshooting documentation

### Changed

- public version numbering reset to Semantic Versioning, beginning with `1.0.0`
- installer now distinguishes fresh installations from upgrades
- installer preserves existing configuration, history, logs and Pushover secrets during upgrades
- Python virtual environment is rebuilt during upgrades
- installed software now carries its authoritative `VERSION` file
- current-facing documentation uses version-neutral wording where practical

### Fixed

- historical CSV writes are explicitly flushed and synchronised to storage
- interrupted final CSV records are detected and safely recovered on startup
- malformed `current_status.json` files caused by unclean shutdowns are discarded and regenerated
- invalid or unrecognised historical CSV headers cause a safe startup failure rather than an attempted automatic repair
