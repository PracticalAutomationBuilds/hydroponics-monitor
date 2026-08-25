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

Release ZIP filenames follow this pattern. For example:

`Hydro_Monitor_v9_1_2.zip`

Use the filename of the latest release when following the commands below.

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

## Verify and Initialise the RTC

Before continuing, confirm that the DS3231 RTC module is physically fitted to the Raspberry Pi GPIO header.

The Makerverse Protoboard is mounted using the **GPIO Header for Raspberry Pi B+ (Extra-long 2x20 Female Header)**. The extended pins remain accessible above the protoboard, allowing the RTC module to be fitted normally across Raspberry Pi physical pins 1, 3, 5, 7 and 9.

**Power down the Raspberry Pi before fitting or removing the RTC module.**

The RTC connections are:

| RTC Position | Raspberry Pi Physical Pin | Function |
|---:|---:|---|
| 1 | 1 | 3.3 V |
| 2 | 3 | GPIO2 / SDA |
| 3 | 5 | GPIO3 / SCL |
| 4 | 7 | NC |
| 5 | 9 | GND |

The RTC position over physical pin 7 is not electrically connected, so GPIO4 remains available for the DS18B20 1-Wire bus.

For the complete physical wiring arrangement, see [Wiring](wiring.md).

With the RTC correctly fitted to the GPIO pins, run the RTC verification utility:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

Confirm that the Raspberry Pi has the correct time and that network time synchronisation is operating normally.

Then synchronise the RTC from the system clock:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh --sync-from-system
```

The verification utility will not overwrite the RTC unless network time synchronisation has been confirmed.

## Assign the Temperature Probes

The two DS18B20 probes share the same GPIO4 1-Wire bus. Each probe has a unique hardware ID, and the Hydroponics Monitor uses those IDs to distinguish the reservoir probe from the grow-pipe probe.

Do not rely on the order in which Linux discovers the sensors. That order may change after a reboot.

### List the Connected Probes

After 1-Wire has been enabled and the Raspberry Pi has rebooted, list the detected probes:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py --list
```

Two IDs beginning with `28-` should be displayed, together with their current temperature readings.

### Identify Each Probe

Gently hold one of the metal probes in your hand and watch the readings:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py --watch 30
```

The temperature of the probe being held should rise relative to the other probe.

Record which `28-...` ID belongs to:

- the reservoir probe
- the grow-pipe probe

Hand warmth is sufficient. Do not use hot water, a heat gun or another high-temperature source to identify the probes.

### Assign the Probe Roles

Run the interactive configuration utility:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py
```

Select the appropriate hardware ID for the reservoir probe and the grow-pipe probe.

The configuration utility:

- refuses to leave a required probe role unassigned
- refuses to assign the same hardware ID to both roles
- creates a timestamped backup of the existing configuration before writing changes
- leaves grow-pipe alarms disabled
- leaves the monitor and dashboard services stopped until commissioning is complete

### Verify the Saved Configuration

To inspect the saved configuration:

```bash
python3 -m json.tool /opt/hydro-monitor/config.json | less
```

The temperature section should contain two different DS18B20 hardware IDs, similar to:

```json
"temperature": {
  "reservoir_sensor_id": "28-...",
  "grow_pipe_enabled": true,
  "grow_pipe_sensor_id": "28-...",
  "grow_pipe_alarm_enabled": false
}
```

Press `q` to exit the configuration display.

Do not enable the continuous monitor and dashboard services yet. Complete the hardware checks and commissioning procedure first.

## Ready for Commissioning

At this point, the installation stage is complete.

The Raspberry Pi should now have:

- Raspberry Pi OS installed and updated
- the latest Hydroponics Monitor release installed in `/opt/hydro-monitor`
- 1-Wire enabled
- the DS3231 RTC fitted, verified and initialised
- both DS18B20 probes detected and assigned to their correct roles
- the monitor and dashboard services still stopped and disabled

Do not enable the services yet.

The next stage is to verify the completed hardware, test the sensors, indicators and alarm outputs, and then place the system into normal operation.

Continue with [Commissioning](commissioning.md).

## Updating an Existing Installation

The update procedure will be documented once the first upgrade between published releases has been tested.

Until then, follow the instructions provided with the relevant release rather than assuming that a fresh-install procedure is suitable for updating an existing system.
