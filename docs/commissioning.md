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
- confirming that the system recovers correctly after a reboot or unexpected loss of power

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

## Alarm and Indicator Behaviour

These tests are performed with the monitor and dashboard services running.

Before beginning, allow any startup grace periods to finish and confirm the normal state:

- green LED solid
- amber LED off
- red LED off
- buzzer silent
- dashboard showing no active alarm

Optional Pushover notifications should remain disabled until the local alarm behaviour has been verified.

### Low Reservoir Alarm

Manually move the reservoir float to simulate a low-water condition. There is no need to drain the reservoir.

While the low-water condition is being confirmed, the green LED should turn off.

After approximately 30 seconds, confirm that:

- the dashboard reports the reservoir level as low
- `LOW_WATER` becomes the active alarm
- the red LED illuminates
- the green LED remains off
- the buzzer gives one approximately 0.8-second beep every 3 seconds

Return the float to its normal-water position.

Confirm that:

- the low-water alarm clears
- the red LED turns off
- the buzzer stops
- the green LED returns to solid once all protected conditions are healthy

### Return-Water Alarm

Create a dry condition at the SEN0368 without unnecessarily interrupting circulation to the hydroponic system. For example, temporarily remove the sensor from the water being detected.

Once the configured confirmation period has elapsed, confirm that:

- the dashboard reports return water as absent
- `FLOW_LOSS` becomes the active alarm
- the red LED illuminates
- the green LED is off
- the buzzer gives two short beeps approximately every 4 seconds

Return the SEN0368 to its normal wet condition.

Confirm that the flow-loss alarm clears and normal indication is restored.

### Alarm-Inhibit Function

While a test alarm is active, operate the maintained alarm-inhibit switch.

Confirm that:

- the amber LED illuminates
- the red LED turns off
- the buzzer becomes silent
- the green LED remains off
- the dashboard shows that alarm override/inhibit is active
- the underlying sensor condition remains visible on the dashboard

Return the switch to its normal **alarms enabled** position.

The alarm may not immediately reappear if the test fault is still present because the applicable confirmation or grace timing is restarted. Allow the system to complete that timing before judging the result.

Restore the test condition to normal before continuing.

### Reservoir Temperature Alarms

The reservoir-temperature alarm can be tested without heating the hydroponic reservoir.

Temporarily place the reservoir DS18B20 probe in a small container of controlled warm water while leaving the grow-pipe probe undisturbed.

The established reservoir thresholds are:

| State | Temperature |
|---|---:|
| Warning begins | 24.0 °C |
| Critical begins | 25.0 °C |
| Returns to normal | below 23.5 °C |

Raise the probe temperature gradually and confirm that:

- at 24.0 °C or above, `TEMP_WARNING` is reported
- at 25.0 °C or above, `TEMP_CRITICAL` is reported
- the red LED is illuminated while an alarm is active
- the buzzer pattern changes appropriately between warning and critical states
- the dashboard displays the same reservoir-temperature state

Allow the probe to cool below 23.5 °C and confirm that the temperature alarm clears.

Return the reservoir probe to its normal installed position after testing.

Do not use boiling water, a heat gun or another uncontrolled heat source for this test.

### Reservoir Sensor-Fault Alarm

It is not necessary to disconnect live wiring merely to force a reservoir DS18B20 failure during commissioning.

The physical probe connection and valid-reading path have already been checked by the hardware self-test, while the sensor-fault alarm logic is covered by the software release tests.

Do not disturb powered terminal-block wiring solely to create this fault condition.

## Remote Notification Test

Pushover notifications are optional.

If Pushover will not be used, skip this section. The Hydroponics Monitor does not require Internet access for local sensing, logging, dashboard operation, LEDs or audible alarms.

Configure Pushover only after the local alarm and indicator tests have passed.

### Configure Pushover

Create a Pushover account and a dedicated Application/API Token for the Hydroponics Monitor.

You will need:

- the Pushover User Key
- the dedicated Application API Token
- optionally, the name of a specific Pushover device

Do not place these credentials in the GitHub repository, screenshots, documentation or other public files.

On the Raspberry Pi, run:

```bash
sudo /opt/hydro-monitor/configure_pushover.py
```

Enter the requested credentials when prompted.

Press Enter at the optional device-name prompt if notifications should be delivered to all active devices associated with the Pushover account.

The configuration utility validates the supplied credentials, stores them separately from the ordinary monitor configuration, enables phone notifications and sends a harmless setup-test message.

Confirm that the test notification is received.

### Check Notification Status

Run:

```bash
sudo /opt/hydro-monitor/configure_pushover.py --status
```

Then check the dashboard.

**Phone notifications** should report:

```text
Ready
```

The Pushover User Key and Application API Token must not be visible in the dashboard or downloadable configuration backups.

### Send Another Test Notification

A further harmless test message can be sent at any time with:

```bash
sudo /opt/hydro-monitor/configure_pushover.py --test-only
```

Confirm that the message arrives on the intended phone or device.

### Test Real Alarm Notifications

With the system supervised, repeat suitable alarm tests that were already verified locally.

At minimum, confirm that:

- a sustained low-reservoir condition produces a `Reservoir level LOW` notification
- restoring the reservoir float produces the corresponding cleared notification
- sustained loss of return water produces a `Return flow LOST` notification
- restoring return-water detection produces the corresponding restored notification

Confirm that the notification identifies the same condition shown by the dashboard and local indicators.

### Test Alarm Inhibit

Create a test alarm condition while the alarm-inhibit switch is active.

Confirm that:

- the dashboard still shows the underlying sensor condition
- no red LED alarm is produced
- the buzzer remains silent
- no Pushover alarm notification is sent

Return the switch to **alarms enabled** and restore the test condition to normal when finished.

### Internet Independence

If practical, temporarily disconnect the Raspberry Pi from Internet access while leaving the local network and controller operating.

Trigger a suitable test alarm and confirm that:

- the local dashboard continues operating
- the local LEDs and buzzer continue operating normally
- loss of Internet access does not interfere with sensor monitoring

Restore Internet access after the test.

Pushover is an additional remote warning path and should not be treated as a replacement for the local alarm system.

## Restart and Power-Loss Recovery Test

After all applicable commissioning tests have passed, verify that the controller recovers correctly after both a normal reboot and an unexpected loss of power.

### Controlled Reboot

Before rebooting, confirm that:

- all temporary test conditions have been removed
- the reservoir float is in its normal-water position
- the SEN0368 is detecting return water normally
- the alarm-inhibit switch is set to **alarms enabled**
- no unexpected alarm is active

Reboot the Raspberry Pi:

```bash
sudo reboot
```

Allow the Raspberry Pi to restart normally.

After approximately one to two minutes, reconnect by SSH:

```powershell
ssh hydroponics@hydro-monitor.local
```

### Check Automatic Service Startup

Confirm that the monitor service restarted automatically:

```bash
systemctl is-active hydro-monitor.service
```

The expected result is:

```text
active
```

Confirm the dashboard service:

```bash
systemctl is-active hydro-dashboard.service
```

The expected result is:

```text
active
```

Also confirm that both services remain enabled for future boots:

```bash
systemctl is-enabled hydro-monitor.service
systemctl is-enabled hydro-dashboard.service
```

Each should report:

```text
enabled
```

### Check RTC and System Time

Check the current system time:

```bash
date
```

Confirm that the date, time and timezone are correct.

Run the RTC verification utility:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

Confirm that the RTC is detected and operating normally.

### Check Normal Monitoring

Open:

`http://hydro-monitor.local:8080/`

Confirm that:

- the dashboard becomes available without manual intervention
- the connection state returns to **Live**
- both DS18B20 probes are detected
- the DHT22 is reporting
- the return-water and reservoir-level states are correct
- no unexpected alarm is active
- the green LED returns to its normal operating state after any startup grace period
- historical logging resumes

If Pushover is configured, confirm that the dashboard again reports phone notifications as ready.

The system should recover from the reboot without requiring any manual software restart, sensor reassignment or configuration change.

### Unexpected Power-Loss Test

The current release includes protection against an interrupted write to persistent monitoring data.

Perform this test only after the controlled reboot test has passed and while the controller is supervised.

Do not perform the test while Raspberry Pi OS packages, configuration files or other system-level changes are being installed.

With the monitor and dashboard operating normally, disconnect power from the Raspberry Pi without first issuing a shutdown command.

Wait several seconds, then reconnect power and allow the Raspberry Pi to boot normally.

Reconnect by SSH and confirm that both services have returned to the active state:

```bash
systemctl is-active hydro-monitor.service
systemctl is-active hydro-dashboard.service
```

Both should report:

```text
active
```

Open the dashboard and confirm that normal monitoring resumes without manual intervention.

### Check Persistent-Data Recovery

Inspect the monitor log from the current boot:

```bash
journalctl -u hydro-monitor.service -b -n 100 --no-pager
```

An unexpected power interruption will not necessarily damage an application data file.

If no interrupted application write occurred, the monitor should simply start normally.

If the final `readings.csv` record was interrupted, the monitor should automatically:

- preserve the original CSV as a timestamped `readings.powerloss-recovery-*.csv` file
- remove only the incomplete final record
- preserve all earlier historical readings
- log that automatic recovery occurred
- continue normal monitoring

If `current_status.json` was left malformed by the interruption, it should be discarded automatically and regenerated from live monitor data.

A damaged or unrecognised `readings.csv` header is **not** repaired automatically. The monitor will stop rather than guess at the historical data structure.

The software release tests separately simulate an interrupted final CSV record and malformed live-status file. The physical power-loss test verifies that the complete Raspberry Pi installation can recover from an actual unclean shutdown.

After restart, confirm that:

- the dashboard returns to **Live**
- historical logging continues
- existing historical readings remain available
- the sensors retain their assigned roles
- no configuration has been lost
- no unexpected alarm remains active

The controller should now be capable of returning to normal unattended monitoring after either a controlled reboot or an unexpected loss of power.

## Final Acceptance

The system should not be considered commissioned until all applicable tests above have passed.

Any failed test should be corrected and repeated before the monitor is relied upon for unattended operation.
