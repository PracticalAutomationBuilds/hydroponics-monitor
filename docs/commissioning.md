# Commissioning

## Status

**Work in progress.**

This procedure documents commissioning of the completed Hydroponics Monitor after the software installation and initial configuration described in [Installation](installation.md).

The procedure will be refined as the permanent controller is assembled and tested.

## Purpose

Commissioning verifies that the completed Hydroponics Monitor hardware and software are operating correctly before the system is placed into normal unattended service.

The process includes:

- checking the completed wiring before power is applied
- running the supplied hardware self-test
- verifying each sensor and alarm input
- testing the LEDs and buzzer
- enabling and starting the monitor and dashboard services
- checking the local dashboard
- testing optional remote notifications, where configured
- confirming that the system recovers correctly after a reboot

The system should not be relied upon for unattended monitoring until the applicable commissioning checks have passed.

## Before Applying Power

Complete these checks with the Raspberry Pi power supply disconnected.

### Visual Inspection

Confirm that:

- all wiring matches the current [Wiring](wiring.md) documentation
- the Makerverse Protoboard is fully seated on the Raspberry Pi GPIO header
- the DS3231 RTC is fitted in the correct position on the exposed extra-long GPIO header
- terminal blocks are in their documented TB1–TB6 positions and their connections have not been transposed
- the DS18B20, DHT22 and SEN0368 power connections have the correct polarity
- the three LEDs have the correct polarity and each has its 330 Ω series resistor
- Q1 and Q2 are fitted in the documented C-B-E orientation
- the required pull-up and pull-down resistors are fitted in the correct locations
- no solder bridges, loose wire strands or unintended connections are visible
- terminal-block screws are secure
- unused conductors, including the SEN0368 IO1 wire, are insulated so that they cannot contact other circuitry

### Protoboard Inspection

Inspect both sides of the permanent board before fitting it into the enclosure.

Pay particular attention to:

- solder joints between adjacent protoboard pads
- underside links and bent component leads
- the areas around the 3.3 V, 5 V and ground connections
- clearance between solder joints or component leads and the Raspberry Pi below

A standard Raspberry Pi 3 Model B should not normally create a clearance problem. If a large aftermarket heatsink is fitted, confirm that no component lead, solder joint or underside link can contact it.

### Basic Electrical Checks

Before connecting power, use a multimeter to check for obvious unintended shorts between:

- 3.3 V and ground
- 5 V and ground
- 3.3 V and 5 V

Also confirm continuity through any underside links or connections that will no longer be easily accessible once the controller is enclosed.

Do not continue to power-up if an unexpected short or uncertain connection is found.

### Final Check

Confirm that all external sensor and control cables are connected to the intended terminal blocks before applying power.

If any wiring is changed during these checks, repeat the inspection before continuing.

## Commissioning Power-Up

After completing the pre-power checks, connect the Raspberry Pi power supply and allow the system to boot normally.

The Hydroponics Monitor and dashboard services should still be **stopped and disabled**. They are not started until the hardware self-test and the remaining commissioning checks have been completed successfully.

Connect to the Raspberry Pi by SSH:

```powershell
ssh hydroponics@hydro-monitor.local
```

Confirm that the monitor service is disabled:

```bash
systemctl is-enabled hydro-monitor.service
```

The expected result is:

```text
disabled
```

Confirm that the dashboard service is also disabled:

```bash
systemctl is-enabled hydro-dashboard.service
```

The expected result is:

```text
disabled
```

Check the Raspberry Pi system time:

```bash
date
```

Confirm that the displayed date, time and timezone are correct.

If either Hydroponics Monitor service is unexpectedly enabled or running, stop and disable both before continuing:

```bash
sudo systemctl disable --now hydro-monitor.service hydro-dashboard.service
```

Do not enable the services yet.

## Hardware Self-Test

With the Hydroponics Monitor and dashboard services still stopped, run the supplied hardware self-test:

```bash
/opt/hydro-monitor/venv/bin/python \
  /opt/hydro-monitor/hydro_monitor.py \
  --config /opt/hydro-monitor/config.json \
  --test
```

The self-test briefly operates the outputs in this order:

1. amber alarm-inhibit LED
2. red alarm LED
3. green status LED
4. buzzer

Each output is activated for approximately half a second.

Watch and listen during the test and confirm that all three LEDs illuminate individually and that the buzzer sounds.

The test then reports the current state or reading for:

- SEN0368 return-water sensor
- reservoir low-level float switch
- alarm-inhibit switch
- reservoir DS18B20 temperature probe
- grow-pipe DS18B20 temperature probe
- DHT22 ambient temperature and relative humidity
- Raspberry Pi CPU temperature

Check that the reported input interpretations make sense for the physical state of the system.

For example:

- with water detected at the SEN0368, the return sensor should be interpreted as wet
- with the reservoir float in its normal-water position, the reservoir level should be interpreted as acceptable
- with the alarm-inhibit switch in its normal position, the override/inhibit input should report inactive

### Self-Test Result

The automated pass/fail result specifically requires valid readings from both assigned DS18B20 temperature probes.

A successful test finishes with:

```text
SELF-TEST RESULT: REQUIRED TEMPERATURE PROBES PASSED.
```

The program then reminds the installer to confirm the LEDs, buzzer and input interpretations manually.

If either required DS18B20 probe fails to produce a valid reading after three attempts, the self-test fails and the services must not be enabled.

A successful automated result does **not** by itself prove that every sensor, switch or alarm output is wired correctly. The reported states and physical outputs must also be checked manually before commissioning continues.

Do not enable the Hydroponics Monitor services yet.

## Sensor and Input Tests

The hardware self-test can be repeated as necessary while checking the individual sensors and inputs:

```bash
/opt/hydro-monitor/venv/bin/python \
  /opt/hydro-monitor/hydro_monitor.py \
  --config /opt/hydro-monitor/config.json \
  --test
```

The monitor and dashboard services should remain disabled during these checks.

### Reservoir Temperature Probe

Confirm that:

- a valid reservoir temperature is reported
- the temperature is plausible for the probe's surroundings
- the reading belongs to the probe previously assigned as the reservoir sensor

If necessary, gently warm the probe by hand and repeat the self-test to confirm its identity.

### Grow-Pipe Temperature Probe

Confirm that:

- a separate valid grow-pipe temperature is reported
- the temperature is plausible for the probe's surroundings
- the reading belongs to the probe previously assigned as the grow-pipe sensor

The two DS18B20 probes must remain distinguishable by their unique hardware IDs even though they share the same GPIO4 1-Wire bus.

### Ambient Temperature and Humidity Sensor

Confirm that the DHT22 reports:

- a plausible ambient temperature
- a plausible relative-humidity reading

A failed DHT22 reading does not cause the DS18B20 hardware self-test itself to fail, so its output must be checked manually.

### Return-Water Sensor

Test the SEN0368 in both water-present and water-absent conditions.

With water detected, the self-test should report:

```text
Return sensor raw value: 0
Return interpreted as wet: True
```

With no water detected, it should report:

```text
Return sensor raw value: 1
Return interpreted as wet: False
```

The inverted GPIO logic is intentional because the SEN0368 signal passes through Q1 before reaching GPIO24.

If the interpretation is reversed, check the SEN0368 adaptor settings and Q1 wiring rather than changing the software configuration to compensate for a wiring fault.

### Reservoir Float Switch

Manually operate the float through both positions.

In the intended normal-water position, the self-test should report:

```text
Low-level input electrical value: 0
Reservoir level interpreted as acceptable: True
```

In the low-water position, it should report:

```text
Low-level input electrical value: 1
Reservoir level interpreted as acceptable: False
```

The float must be oriented so that the contact is **closed to ground at an acceptable water level** and open at low water.

This arrangement is deliberately fail-safe: an open circuit caused by a disconnected or broken float-switch cable is interpreted in the same way as low water.

### Alarm-Inhibit Switch

Test the maintained alarm-inhibit switch in both positions.

With alarms operating normally, the self-test should report:

```text
Override switch active: False
```

With the switch set to inhibit alarms:

```text
Override switch active: True
```

Return the switch to its normal **alarms enabled** position before continuing commissioning.

## Start and Check Services

Once the hardware self-test and individual sensor/input checks have passed, the continuous monitor and dashboard services can be enabled.

Before continuing, return the alarm-inhibit switch to its normal **alarms enabled** position.

Enable and start both services:

```bash
sudo systemctl enable --now hydro-monitor.service hydro-dashboard.service
```

Check the monitor service:

```bash
systemctl status hydro-monitor.service
```

It should show:

```text
active (running)
```

Check the dashboard service:

```bash
systemctl status hydro-dashboard.service
```

It should also show:

```text
active (running)
```

Press `q` to exit either status display.

If a service does not start successfully, inspect its recent log messages:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager
```

or:

```bash
journalctl -u hydro-dashboard.service -n 100 --no-pager
```

Do not continue commissioning until both services remain running without unexpected errors.

The services are now enabled to start automatically whenever the Raspberry Pi boots.

## Dashboard Test

From another computer or device on the same local network, open:

`http://hydro-monitor.local:8080/`

The dashboard should load and show a **Live** connection state rather than stale or unavailable monitor data.

### Monitor Page

Confirm that the displayed values are plausible and agree with the physical state of the system:

- Return water
- Reservoir level
- Reservoir temperature
- Grow-pipe airspace temperature
- Pipe − reservoir temperature difference
- Grow-pipe probe status
- Ambient temperature
- Relative humidity
- Alarm override
- Active alarm
- Phone notification status
- Monitor uptime
- Raspberry Pi temperature

With the system in its normal commissioning state:

- Return water should match the actual SEN0368 condition
- Reservoir level should match the float-switch position
- Alarm override should show that alarms are enabled
- no unexpected active alarm should be present
- the reservoir and grow-pipe temperatures should correspond to the probes assigned during installation

The dashboard refreshes current monitor information automatically. Leave it open for several update cycles and confirm that readings continue to update without requiring a manual page refresh.

### History

Confirm that the temperature-history display contains separate series for:

- reservoir temperature
- grow-pipe airspace temperature
- ambient temperature

Also confirm that the relative-humidity history is available.

A newly commissioned installation will naturally contain only a small amount of historical data. Longer time ranges will populate as the monitor continues operating.

### System Information

Open the **System information** tab and confirm that system information is displayed without errors, including the Raspberry Pi and RTC status.

### Configuration and Downloads

Open the **Configuration & backups** tab and confirm that it loads successfully.

At minimum, verify that the available read-only downloads can be accessed, including:

- readings CSV
- event log

Do not alter configuration merely to complete this dashboard check.

If the dashboard cannot be reached, reports stale monitor data, or displays values inconsistent with the physical sensor states, resolve the problem before continuing commissioning.

## Remote Notification Test

Where remote notifications are enabled, trigger an appropriate test condition and confirm that:

* the notification is received
* the message identifies the correct condition
* repeated notifications behave as intended

## Restart Test

Restart the Raspberry Pi and confirm that:

* the system boots normally
* monitoring software starts automatically
* sensors are detected again
* the dashboard becomes available
* normal monitoring resumes without manual intervention

## Final Acceptance

The system should not be considered commissioned until all applicable tests above have passed.

Any failed test should be corrected and repeated before the monitor is relied upon for unattended operation.
