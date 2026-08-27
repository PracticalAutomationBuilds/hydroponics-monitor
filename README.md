# Hydroponics Monitor

A Raspberry Pi-based monitoring and alert system for a home hydroponic installation.

The project is being developed around a Raspberry Pi 3B to provide continuous monitoring of important system conditions, local alarms, historical information and a browser-based dashboard.

## Project Status

> **Work in progress**
>
> The permanent controller hardware is currently being assembled and commissioned. The software has reached its first public release-candidate stage, while hardware verification and documentation are being completed before the first stable release.

## Releases and Downloads

Installable packages are published through the project's [GitHub Releases](https://github.com/PracticalAutomationBuilds/hydroponics-monitor/releases) page.

Use the **latest release or pre-release package** rather than downloading individual files from the repository.

Each packaged release includes:

- the complete installation package
- release notes
- a SHA-256 checksum for integrity verification

The current public release candidate is:

**v1.0.0-rc.1**

Stable release **v1.0.0** will follow once permanent-hardware commissioning has been completed successfully.

For installation instructions, see [Installation](docs/installation.md).

## Monitored Conditions

The system monitors:

- reservoir nutrient-solution temperature
- grow-pipe airspace temperature
- ambient temperature and relative humidity
- return-water presence (Pump Working indication)
- critically low reservoir water level

## Outputs and Alerts

System functions include:

- browser-based local dashboard
- historical sensor logging
- visual status and warning LEDs
- audible alarm
- maintained alarm-inhibit control
- optional Pushover notifications for selected fault conditions

## Documentation

* [Project Overview](docs/overview.md)
* [Bill of Materials](docs/bill-of-materials.md)
* [Wiring](docs/wiring.md)
* [Installation](docs/installation.md)
* [Commissioning](docs/commissioning.md)
* [Troubleshooting](docs/troubleshooting.md)
* [Changelog](docs/changelog.md)

## Repository Structure

* `docs/` — project documentation
* `hardware/` — board layouts, wiring diagrams and mechanical design files
* `images/` — photographs and documentation images
* `software/` — Raspberry Pi application and configuration files

## Licence

This project is released under the [MIT License](LICENSE).

## Practical Automation Builds

Hydroponics Monitor is the first project from **Practical Automation Builds**, a collection of practical electronics and automation projects designed for real-world use.
