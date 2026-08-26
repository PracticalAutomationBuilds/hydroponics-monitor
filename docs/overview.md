# Hydroponics Monitor Overview

## Purpose

The Hydroponics Monitor is a Raspberry Pi-based monitoring and alert system developed for a home hydroponic strawberry installation.

The project is intended to provide continuous monitoring of important system conditions without requiring frequent manual checks, while also providing clear local alarms and a browser-based dashboard.

## What It Monitors

The system is designed to monitor:

- reservoir nutrient-solution temperature
- grow-pipe airspace temperature
- ambient temperature and relative humidity
- return-water presence
- critically low reservoir water level

## Alerts and Outputs

The completed system is designed to provide:

* browser-based status dashboard
* historical sensor information
* visual LED warnings
* audible alarm
* remote notifications for selected fault conditions

## Hardware Platform

The project is based around a Raspberry Pi 3 Model B and combines commercially available sensors with a permanent controller assembled on a Makerverse Protoboard for Raspberry Pi.

The hardware has been designed so that sensors and field wiring can be disconnected using terminal blocks rather than being permanently soldered to the controller.

## Design Goals

The main goals of the project are:

* reliable unattended monitoring
* straightforward construction from readily available components
* clearly documented wiring and assembly
* easy replacement of sensors and other field components
* useful fault reporting rather than unnecessary complexity
* maintainability by the person who built it

## Project Status

**Work in progress.**

The hardware, software and documentation are still being developed and tested. Information in this repository may change until the first stable release is published.
