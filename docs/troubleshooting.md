# Troubleshooting

## Status

**Work in progress.**

This guide documents troubleshooting procedures for the Hydroponics Monitor and will be expanded as additional faults and real-world operating experience are encountered.

Where a fault is corrected, repeat the relevant checks in [Commissioning](commissioning.md) before returning the controller to unattended operation.

## General Approach

When troubleshooting the Hydroponics Monitor:

1. identify the failed function or incorrect reading
2. check the dashboard for the current system state
3. check the relevant service logs for errors
4. confirm the affected hardware connection against [Wiring](wiring.md)
5. verify the relevant power, ground and signal connections
6. test the individual sensor, input or output where practical
7. make only one change at a time
8. repeat the relevant commissioning test after correcting the fault

Avoid changing software settings simply to make an unexpected electrical state appear correct. Where a sensor or input reports reversed or implausible logic, confirm the physical wiring and documented interface circuit first.

When requesting troubleshooting assistance, do not publish Pushover credentials, passwords or other private configuration values.

## Raspberry Pi Does Not Boot

If the Raspberry Pi does not appear to boot, first disconnect its power supply before inspecting or changing any hardware.

### Check the Basics

Confirm that:

- the Micro USB power supply is connected securely
- the microSD card is fully inserted
- the power supply is suitable for the Raspberry Pi 3 Model B
- no loose wire, component lead or solder joint is shorting against another connection
- the Makerverse Protoboard and GPIO header are correctly aligned
- the DS3231 RTC, if fitted, is positioned on the correct GPIO pins

Do not remove or refit GPIO-connected hardware while the Raspberry Pi is powered.

### Observe the Raspberry Pi LEDs

On the Raspberry Pi itself:

- the red **PWR** LED should indicate that power is present
- the green **ACT** LED should normally show activity while the microSD card is being accessed during boot

No power indication suggests a power-supply or power-connection problem.

Power indication with no apparent boot activity may indicate a microSD card, Raspberry Pi OS or attached-hardware problem.

### Isolate the Controller Hardware

If the cause is not obvious, power the Raspberry Pi off and temporarily disconnect the Hydroponics Monitor hardware.

Where practical, test the Raspberry Pi with only:

- the microSD card
- the Raspberry Pi power supply
- the required network connection

Then apply power again.

If the Raspberry Pi boots normally with the controller hardware removed, the fault is likely associated with the GPIO-connected hardware, protoboard or external wiring.

Reconnect hardware progressively, with power removed between changes, until the fault is identified.

Pay particular attention to:

- shorts between 3.3 V and ground
- shorts between 5 V and ground
- shorts between 3.3 V and 5 V
- incorrect GPIO-header alignment
- misplaced RTC connection
- underside protoboard links or solder joints
- clearance against any large aftermarket Raspberry Pi heatsink

### If the Raspberry Pi Still Does Not Boot

If the Raspberry Pi will not boot with the Hydroponics Monitor hardware disconnected, investigate the Raspberry Pi, power supply and microSD card independently of this project.

Do not immediately re-image the existing microSD card if the controller has already been commissioned and contains historical readings or configuration that should be preserved.

If possible, preserve or copy the existing card before undertaking destructive recovery steps such as re-imaging it.

After correcting the fault, reconnect the controller hardware and repeat the relevant [Commissioning](commissioning.md) checks before returning the system to unattended operation.

## Monitoring Software Does Not Start

If the monitor service is not running, first check its current state:

```bash
systemctl status hydro-monitor.service
```

Press `q` to exit the status display.

### Check Whether the Service Is Enabled

```bash
systemctl is-enabled hydro-monitor.service
```

For a commissioned system, the expected result is:

```text
enabled
```

If it is disabled after commissioning, enable and start it:

```bash
sudo systemctl enable --now hydro-monitor.service
```

### Check the Installed Version

Confirm that the installed release is the expected version:

```bash
cat /opt/hydro-monitor/VERSION
```

If the VERSION file is missing or reports an unexpected release, stop and verify that the correct software package was installed.

### Check Recent Monitor Logs

View the most recent service messages:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager
```

For messages from the current boot only:

```bash
journalctl -u hydro-monitor.service -b --no-pager
```

Look for errors involving:

- missing or invalid configuration
- unassigned DS18B20 probe IDs
- missing required temperature probes
- malformed historical-data files
- GPIO initialisation
- missing Python packages
- file permissions
- unexpected shutdown or power-loss recovery

### Run the Monitor Manually

If the service log does not make the problem clear, first stop the service:

```bash
sudo systemctl stop hydro-monitor.service
```

Then run the monitor directly:

```bash
sudo /opt/hydro-monitor/venv/bin/python \
  /opt/hydro-monitor/hydro_monitor.py \
  --config /opt/hydro-monitor/config.json
```

Running the program interactively can make startup errors easier to see.

Stop the manual run with `Ctrl+C` when finished.

Do not run the manual monitor and the systemd monitor service at the same time.

### Check the Configuration

Confirm that the main configuration file is valid JSON:

```bash
python3 -m json.tool /opt/hydro-monitor/config.json > /dev/null
```

No output indicates that the JSON syntax is valid.

If the command reports an error, do not manually guess at repairs. Check for a timestamped configuration backup and compare it with the damaged file.

### Check the Temperature-Probe Assignments

List the detected DS18B20 probes:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py --list
```

Both required probes should be detected.

If the probes are present but their roles have not yet been assigned, run:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py
```

The continuous monitor will not start normally until the required reservoir and grow-pipe probe roles contain valid, different hardware IDs.

### Restart the Service

After correcting the cause:

```bash
sudo systemctl restart hydro-monitor.service
```

Then check:

```bash
systemctl is-active hydro-monitor.service
```

The expected result is:

```text
active
```

Repeat the relevant [Commissioning](commissioning.md) checks before returning the controller to unattended operation.

## Dashboard Does Not Load

If the dashboard cannot be opened at:

`http://hydro-monitor.local:8080/`

first confirm that the Raspberry Pi itself is reachable.

From another computer on the same network:

```powershell
ssh hydroponics@hydro-monitor.local
```

If SSH also fails, investigate the Raspberry Pi network connection or hostname resolution before troubleshooting the dashboard service.

### Check the Dashboard Service

On the Raspberry Pi:

```bash
systemctl status hydro-dashboard.service
```

Press `q` to exit the status display.

For a commissioned system, the service should report:

```text
active (running)
```

Check whether it is enabled:

```bash
systemctl is-enabled hydro-dashboard.service
```

The expected result is:

```text
enabled
```

If it is disabled after commissioning, enable and start it:

```bash
sudo systemctl enable --now hydro-dashboard.service
```

### Check Recent Dashboard Logs

View the most recent service messages:

```bash
journalctl -u hydro-dashboard.service -n 100 --no-pager
```

For messages from the current boot only:

```bash
journalctl -u hydro-dashboard.service -b --no-pager
```

Look for errors involving:

- failure to bind to port 8080
- missing files
- Python errors
- file permissions
- invalid configuration
- inability to read monitor status or history data

### Try the Raspberry Pi IP Address

If the dashboard service is running but `hydro-monitor.local` does not work, determine the Raspberry Pi's IP address:

```bash
hostname -I
```

Then open:

`http://<Pi-IP-address>:8080/`

For example:

`http://192.168.1.50:8080/`

If the dashboard works by IP address but not by `hydro-monitor.local`, the dashboard itself is operating and the problem is with local hostname resolution or mDNS.

### Check Whether Port 8080 Is Listening

On the Raspberry Pi:

```bash
ss -ltn | grep ':8080'
```

A listening entry should be shown if the dashboard service has successfully bound to port 8080.

If nothing is returned, inspect the dashboard service logs for the reason it failed to start or bind.

### Dashboard Loads but Shows Stale or Unavailable Data

The dashboard service and monitoring service are separate.

A working web page does not necessarily mean that the monitor service is running.

Check the monitor:

```bash
systemctl is-active hydro-monitor.service
```

The expected result is:

```text
active
```

If the dashboard loads but reports stale, unavailable or implausible live data, troubleshoot the monitor service using the [Monitoring Software Does Not Start](#monitoring-software-does-not-start) section.

### Restart the Dashboard Service

After correcting the cause:

```bash
sudo systemctl restart hydro-dashboard.service
```

Then confirm:

```bash
systemctl is-active hydro-dashboard.service
```

The expected result is:

```text
active
```

Reload the dashboard from another device and confirm that the connection returns to **Live**.

Repeat the relevant [Commissioning](commissioning.md) checks before returning the controller to unattended operation.

## DS18B20 Temperature Probe Problems

The reservoir and grow-pipe DS18B20 probes share the same GPIO4 1-Wire bus but are identified individually by their unique `28-...` hardware IDs.

Both probes must be detected and correctly assigned for normal monitoring.

### Check Which Probes Are Detected

Run:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py --list
```

Two different DS18B20 hardware IDs should be detected.

You can also check the Linux 1-Wire devices directly:

```bash
ls -1 /sys/bus/w1/devices/28-* 2>/dev/null
```

### Neither Probe Is Detected

If no DS18B20 probes are detected, check that 1-Wire support is enabled:

```bash
sudo raspi-config
```

Confirm that **1-Wire** is enabled, then reboot if a change was made.

If 1-Wire is already enabled, power the Raspberry Pi down before checking the wiring.

Both probes use:

| Wire | Connection |
|---|---|
| Red | 3.3 V |
| White | GPIO4 / DATA |
| Black | GND |

Also confirm that:

- both probes share GPIO4
- the 4.7 kΩ pull-up resistor is connected between GPIO4 / DATA and 3.3 V
- TB4 and TB5 are wired according to [Wiring](wiring.md)
- terminal-block screws are secure
- no conductor is connected to 5 V
- GPIO4 has not accidentally been connected to the NC position of the RTC module

Do not alter DS18B20 wiring while the Raspberry Pi is powered.

### Only One Probe Is Detected

If only one `28-...` device appears, first check the terminal-block connection for the missing probe.

Because both probes share the same bus, a fault in one probe or its wiring can also interfere with the other.

If necessary, isolate the probes one at a time:

1. shut the Raspberry Pi down and remove power
2. disconnect one DS18B20 probe
3. power the Raspberry Pi and check the remaining probe
4. shut down and remove power again before changing connections
5. repeat with the other probe

This can distinguish an individual probe fault from a shared GPIO4 bus or pull-up problem.

### Temperature Readings Are Assigned to the Wrong Locations

If the reservoir and grow-pipe temperatures appear to be reversed, do not swap wiring at the terminal blocks.

Identify the probes by their unique hardware IDs.

Watch both readings:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py --watch 30
```

Gently warm one physical probe by hand and observe which `28-...` reading rises.

Record which ID belongs to:

- reservoir
- grow-pipe

Then stop the continuous monitor before changing the assignments:

```bash
sudo systemctl stop hydro-monitor.service
```

Run the assignment utility:

```bash
sudo /opt/hydro-monitor/configure_temperature_probes.py
```

Assign the correct hardware ID to each role.

Do not manually edit the IDs in `config.json` unless specifically recovering a damaged configuration.

### After Correcting a Probe Problem

Run the hardware self-test:

```bash
/opt/hydro-monitor/venv/bin/python \
  /opt/hydro-monitor/hydro_monitor.py \
  --config /opt/hydro-monitor/config.json \
  --test
```

Both required DS18B20 probes must produce valid readings.

If the system has already been commissioned, restart the monitor afterwards:

```bash
sudo systemctl restart hydro-monitor.service
```

Then confirm that the dashboard shows the reservoir and grow-pipe temperatures in their correct locations.

## Ambient Temperature or Humidity Reading Missing

The DHT22 provides ambient temperature and relative-humidity data only. A missing DHT22 reading does **not** activate an alarm or prevent the Hydroponics Monitor from continuing to operate.

The dashboard may show the ambient data as unavailable or stale while the remaining sensors continue normally.

### Run the Hardware Self-Test

Stop the continuous monitor before running the self-test:

```bash
sudo systemctl stop hydro-monitor.service
```

Then run:

```bash
/opt/hydro-monitor/venv/bin/python \
  /opt/hydro-monitor/hydro_monitor.py \
  --config /opt/hydro-monitor/config.json \
  --test
```

The self-test makes up to three attempts to obtain a DHT22 reading.

A successful result should show plausible:

- ambient temperature
- relative humidity

If all three attempts fail, continue with the checks below.

### Check the Wiring

Power the Raspberry Pi down and disconnect its power supply before changing any wiring.

The DHT22 is connected through TB2:

| TB2 Terminal | Connection |
|---:|---|
| 1 | 3.3 V |
| 2 | GPIO22 / DATA |
| 3 | GND |

Confirm that:

- the DHT22 is powered from **3.3 V**, not 5 V
- DATA is connected to GPIO22
- ground is secure
- the terminal-block screws are secure
- the cable conductors have not been transposed
- no loose strand or solder bridge is present

The selected DHT22 module includes the required support components, so **no additional DHT22 pull-up resistor is fitted on the protoboard**.

For the complete connection details, see [Wiring](wiring.md).

### Check the Monitor Log

After restarting the monitor:

```bash
sudo systemctl restart hydro-monitor.service
```

check recent DHT22-related messages:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager | grep -i dht
```

Occasional DHT22 timing or checksum errors can occur and do not necessarily indicate a hardware fault. The software ignores an unsuccessful sample and tries again at the next reading interval.

Investigate further if readings remain unavailable or failures continue repeatedly.

### Intermittent Readings

If the DHT22 works only intermittently, check:

- terminal-block and cable connections
- cable damage
- electrical noise or poor ground continuity
- whether moving the cable changes the behaviour
- whether the sensor operates reliably with a shorter temporary connection

Do not replace the sensor solely because of an isolated failed sample.

### After Correcting the Fault

Confirm that the dashboard again shows plausible ambient temperature and relative humidity values and that they continue updating normally.

If the controller has already been commissioned, repeat the relevant [Commissioning](commissioning.md) checks before returning it to unattended operation.

## Return Water-Level Reading Incorrect

Check:

* sensor supply
* signal connection
* grounding
* physical sensor installation
* expected operating range
* software calibration or threshold values

## Low Reservoir Alarm Does Not Operate

Check:

* float-switch wiring
* mechanical movement of the float
* GPIO assignment
* expected normal-open or normal-closed behaviour
* software alarm logic

Manually operate the float switch while watching the dashboard or diagnostic output.

## LED Does Not Illuminate

Check:

* LED polarity
* current-limiting resistor
* GPIO assignment
* ground connection
* solder joints
* software output state

## Buzzer Does Not Operate

Check:

* buzzer polarity
* supply voltage
* transistor/interface wiring
* GPIO control signal
* associated resistor connections
* ground continuity

## Remote Notification Not Received

Check:

* internet connectivity
* notification configuration
* credentials or API values
* whether the triggering condition is configured for remote notification
* rate limiting or repeated-alert suppression

Credentials should never be posted publicly when requesting troubleshooting assistance.

## After a Wiring Change

After any wiring repair or modification:

* inspect the modified area
* check for solder bridges
* confirm polarity
* verify continuity where appropriate
* repeat the relevant commissioning tests before returning the system to unattended operation

## Known Issues

Confirmed software or hardware issues will be listed here as they are identified.
