# Hydroponics Monitor

A Raspberry Pi-based monitoring and alert system for a home hydroponic installation.

The project is being developed around a Raspberry Pi 3B to provide continuous monitoring of important system conditions, local alarms, historical information and a browser-based dashboard.

## Project Status

> **Work in progress**
>
> The prototype hardware and software are currently being built and tested. Wiring, components and software may change before the first stable release.

## Monitored Conditions

The system is designed to monitor:

* nutrient-solution temperature
* grow-pipe water temperature
* ambient temperature and relative humidity
* return water level
* critically low reservoir water level

## Outputs and Alerts

Planned system functions include:

* browser-based dashboard
* historical sensor information
* visual status and warning LEDs
* audible alarm
* remote notifications for selected fault conditions

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
