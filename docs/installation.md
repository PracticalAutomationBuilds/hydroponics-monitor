# Installation

## Status

**Work in progress.**

These instructions document the current installation process for the latest Hydroponics Monitor release, and will be refined as the permanent controller is assembled and commissioned.

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

The Hydroponics Monitor installer checks the username and hostname before making system changes.

The monitor and dashboard services are deliberately left stopped and disabled during installation. They are enabled only after the two DS18B20 probes have been assigned and the hardware self-test has passed.

Hardware assembly and electrical connections are documented separately in [Wiring](wiring.md). Functional testing after installation is covered in [Commissioning](commissioning.md).

### Administration Computer

The examples in this guide assume that the Raspberry Pi is being prepared and administered from a **Windows computer using PowerShell**.

Linux and macOS users can follow the same general procedure using their system terminal, although local file paths and some command syntax may differ.

## Requirements

Before beginning the software installation, the following should be available.

### Hardware

- Raspberry Pi 3 Model B
- SanDisk 64GB High Endurance microSDXC card
- suitable 5.1 V / 2.5 A Micro USB power supply
- completed or sufficiently assembled controller hardware
- DS3231 RTC module
- both DS18B20 temperature probes connected for commissioning

The remaining sensors and alarm outputs should also be connected before the final hardware self-test.

### Raspberry Pi Setup

Instructions for preparing the Raspberry Pi and installing Raspberry Pi OS are shown below.

Be sure to configure the Raspberry Pi with the established project identity:

| Setting | Value |
|---|---|
| Username | `hydroponics` |
| Hostname | `hydro-monitor` |

The installer checks both values and will stop without making system changes if they do not match.

### Network

The Raspberry Pi should be connected to the same local network as the computer used for installation.

The installation procedure assumes that the Pi can be reached as `hydro-monitor.local`.

Avahi/mDNS support is installed by the Hydroponics Monitor installer.

Internet access is useful during installation because the installer downloads required Raspberry Pi OS and Python packages.

After installation, an Internet connection is **not required** for:

- sensor monitoring
- local LED and buzzer alarms
- historical logging
- the local dashboard

Internet access is required only if optional Pushover notifications are enabled.

### Installation Package

Download the **latest Hydroponics Monitor release** and have the complete release ZIP available on the computer from which the installation will be performed.

For example, the current release at the time this documentation was prepared is:

`Hydro_Monitor_v9_1_2.zip`

Do not copy individual files from the release package or omit supporting files. The supplied installer expects the complete extracted release structure.

## Prepare the Raspberry Pi

This procedure assumes a fresh or otherwise suitable Raspberry Pi OS installation.

### Install Raspberry Pi OS

Use Raspberry Pi Imager to install a current Raspberry Pi OS release suitable for the Raspberry Pi 3 Model B.

A graphical desktop is not required by the Hydroponics Monitor; the software is installed and administered from the command line.

When preparing the microSD card, configure:

| Setting | Value |
|---|---|
| Hostname | `hydro-monitor` |
| Username | `hydroponics` |
| Network | Connect to the intended local network |
| SSH | Enabled |
| Timezone | Correct timezone for the installation location |
| Locale | Appropriate local locale |

Choose a secure password for the `hydroponics` account. The password is installation-specific and must not be committed to the repository.

### First Boot

Insert the prepared microSD card, connect the Raspberry Pi to the local network and apply power.

Allow the Raspberry Pi to complete its first boot before attempting to connect.

From another computer on the same network, connect by SSH:

```powershell
ssh hydroponics@hydro-monitor.local
```

On first connection, SSH may ask whether the host key should be trusted. Confirm the connection after verifying that you are connecting to the intended Raspberry Pi.

### Confirm the Raspberry Pi Identity

After logging in, check the username:

```bash
whoami
```

The result should be:

```text
hydroponics
```

Check the hostname:

```bash
hostname
```

The result should be:

```text
hydro-monitor
```

Both values must match before running the Hydroponics Monitor installer.

### Update Raspberry Pi OS

Before installing the project software, update the Raspberry Pi OS package information and installed packages:

```bash
sudo apt update
sudo apt full-upgrade -y
```

If the update installs a new kernel or otherwise indicates that a reboot is required, reboot:

```bash
sudo reboot
```

After the Raspberry Pi restarts, reconnect:

```powershell
ssh hydroponics@hydro-monitor.local
```

### Interfaces

Do not manually configure the DS3231 RTC overlay before running the Hydroponics Monitor installer. The installer performs the required RTC/I²C configuration.

The 1-Wire interface used by the two DS18B20 probes is enabled after the project software has been installed, before commissioning.

## Install Project Software

This procedure is for a **fresh installation** of the Hydroponics Monitor.

Download the latest release ZIP from the project releases and transfer the complete package to the Raspberry Pi.

The examples below use `Hydro_Monitor_v9_1_2.zip`. Replace that filename and the corresponding extracted directory name with those of the latest release.

### Transfer the Release

On the computer containing the downloaded release ZIP, open PowerShell in that directory.

Transfer the ZIP to the Raspberry Pi:

```powershell
scp .\Hydro_Monitor_v9_1_2.zip hydroponics@hydro-monitor.local:~
```

Then connect to the Raspberry Pi:

```powershell
ssh hydroponics@hydro-monitor.local
```

### Extract the Release

On the Raspberry Pi:

```bash
cd ~
unzip Hydro_Monitor_v9_1_2.zip
cd Hydro_Monitor_v9_1_2
```

Use Tab completion where useful to avoid mistyping the release filename or directory name.

Do not run the installer from inside the ZIP file or copy only selected files from the release package.

### Run the Installer

Make the installer executable:

```bash
chmod +x install.sh
```

Run it with administrator privileges:

```bash
sudo ./install.sh
```

Before making system changes, the installer verifies that:

- the user invoking `sudo` is `hydroponics`
- the Raspberry Pi hostname is `hydro-monitor`

If either value is incorrect, the installer stops.

The installer then:

- installs the required Raspberry Pi OS packages
- creates `/opt/hydro-monitor`
- creates the Python virtual environment
- installs the monitor, dashboard and configuration utilities
- creates the required log and state directories
- installs the monitor and dashboard systemd services
- configures the DS3231 RTC support
- keeps Pushover credentials separate from dashboard backups
- leaves the monitor and dashboard services stopped and disabled until commissioning is complete

The services are intentionally **not started at this stage**. The two DS18B20 probes must first be assigned to their reservoir and grow-pipe roles and the hardware self-test must pass.

### Enable 1-Wire

After the installer completes, open Raspberry Pi configuration:

```bash
sudo raspi-config
```

Enable the **1-Wire** interface, then exit `raspi-config`.

Reboot the Raspberry Pi:

```bash
sudo reboot
```

After the reboot, reconnect from the other computer:

```powershell
ssh hydroponics@hydro-monitor.local
```

### Verify the RTC

Run the RTC verification utility:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

Confirm that the Raspberry Pi has the correct time and that network time synchronisation is operating normally.

Then synchronise the RTC from the system clock:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh --sync-from-system
```

The verification utility will not overwrite the RTC unless network time synchronisation has been confirmed.
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
