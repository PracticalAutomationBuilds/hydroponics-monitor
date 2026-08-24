# Installation

## Status

**Work in progress.**

These instructions are being developed alongside the prototype system and may change before the first stable release.

## Overview

This document will describe the complete software installation process, starting with a prepared Raspberry Pi and ending with the Hydroponics Monitor running as intended.

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
