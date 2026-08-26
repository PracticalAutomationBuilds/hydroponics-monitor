# Hydroponics Monitor Software

This directory contains the source files, installation utilities and automated tests for the Hydroponics Monitor.

## Version

The authoritative software version is stored in:

`VERSION`

Installed systems retain this file at:

`/opt/hydro-monitor/VERSION`

The installed version can be checked with:

`cat /opt/hydro-monitor/VERSION`

## Installation

For a normal installation or upgrade, use the complete packaged release rather than downloading individual files from this directory.

See [Installation](../docs/installation.md) for the supported procedure.

The installer:

- supports both fresh installations and upgrades
- preserves existing configuration, historical readings, logs and Pushover secrets during upgrades
- rebuilds the Python virtual environment
- installs the systemd services
- leaves the monitor and dashboard services disabled until commissioning is completed

## Main Application Files

- `hydro_monitor.py` — sensor monitoring, alarm logic, logging and hardware control
- `hydro_dashboard.py` — local web-dashboard server
- `dashboard.html` — dashboard page
- `dashboard.css` — dashboard styling
- `dashboard.js` — dashboard behaviour
- `config.json` — default application configuration
- `hydro_version.py` — common VERSION handling

## Installation and Configuration Utilities

- `install.sh` — fresh installation and upgrade utility
- `uninstall.sh` — safe removal utility
- `merge_config.py` — preserves user configuration during upgrades
- `configure_temperature_probes.py` — DS18B20 identification and role assignment
- `configure_pushover.py` — optional Pushover configuration
- `configure_rtc.sh` — DS3231 RTC setup
- `verify_rtc.sh` — RTC verification and initialisation

## Tests

The release-test suite can be run with:

`./run_release_tests.sh`

The tests cover application logic, configuration, dashboard behaviour, notifications, DS18B20 assignment, release structure, upgrade preservation and power-loss recovery.

Passing the automated tests does not replace physical hardware commissioning.

See [Commissioning](../docs/commissioning.md).

## Private Data

Do not commit:

- `pushover_secrets.json`
- live `readings.csv`
- `events.log`
- `current_status.json`
- configuration backups containing installation-specific information

The repository `.gitignore` contains exclusions for these files.

`pushover_secrets.example.json` contains no real credentials and is provided only as a template.
