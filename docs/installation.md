# Installation

## Status

**Work in progress.**

These instructions document the current Version 9.1.2 installation process and will be refined as the permanent controller is assembled and commissioned.

The procedures in this repository should be treated as the current confirmed installation method unless superseded by a later release.

## Overview

This guide covers installation of the Hydroponics Monitor software on a prepared Raspberry Pi, from the initial Raspberry Pi OS setup through to the point where the system is ready for commissioning.

The established Raspberry Pi identity for this project is:

| Item | Value |
|---|---|
| Username | `hydroponics` |
| Hostname | `hydro-monitor` |
| SSH address | `hydroponics@hydro-monitor.local` |
| Installation directory | `/opt/hydro-monitor` |
| Dashboard address | `http://hydro-monitor.local:8080/` |

The Version 9.1.2 installer checks the username and hostname before making system changes.

The monitor and dashboard services are deliberately left stopped and disabled during installation. They are enabled only after the two DS18B20 probes have been assigned and the hardware self-test has passed.

Hardware assembly and electrical connections are documented separately in [Wiring](wiring.md). Functional testing after installation is covered in [Commissioning](commissioning.md).
## Requirements

The final installation guide will include:

* supported Raspberry Pi model
* recommended Raspberry Pi OS version
* required network connection
* required Python version
* required Python packages
* required system packages
* expected hardware connections before first startup

## Prepare the Raspberry Pi

This section will document:

* Raspberry Pi OS installation
* first boot
* hostname and network configuration
* system updates
* enabling any required interfaces
* timezone and locale settings

## Install Project Software

This section will document:

* cloning or downloading the repository
* creating the project directory
* installing Python dependencies
* configuring file permissions
* installing any required services

## Configure Sensors

This section will document:

* DS18B20 sensor identification
* sensor ID assignment
* ambient sensor configuration
* water-level sensor configuration
* low-level float-switch configuration

## Configure Notifications

This section will document any required remote-notification settings and credentials.

Sensitive credentials must not be committed to the public repository.

Example configuration files will be provided where appropriate.

## Configure the Dashboard

This section will document:

* dashboard settings
* network access
* port configuration
* startup behaviour
* accessing the dashboard from another device

## Automatic Startup

This section will document how to configure the Hydroponics Monitor to start automatically when the Raspberry Pi boots.

## First Startup

Before commissioning, confirm that:

* all hardware connections have been checked
* sensor polarity is correct
* no exposed conductors can short against adjacent terminals
* the Raspberry Pi power supply is suitable
* all required configuration values have been entered

The first startup and functional testing procedure will be documented in the commissioning guide.

## Updating an Existing Installation

A tested update procedure will be added once the software release process has been finalised.
