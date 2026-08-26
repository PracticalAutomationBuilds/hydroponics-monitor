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

## Return-Water Sensor Reading Incorrect

The DFRobot SEN0368 detects whether return water is present. Its signal passes through Q1 before reaching GPIO24, so the Raspberry Pi input is intentionally **active-low**.

The expected logic is:

| Physical Condition | GPIO24 Raw Value | Interpretation |
|---|---:|---|
| Water present | `0` | Wet |
| Water absent | `1` | Dry |

Do not reverse the software logic merely to make an incorrectly wired sensor appear correct.

### Check the Current Reading

Stop the continuous monitor before running the hardware self-test:

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

With water present, the result should include:

```text
Return sensor raw value: 0
Return interpreted as wet: True
```

With no water detected:

```text
Return sensor raw value: 1
Return interpreted as wet: False
```

### Check the SEN0368 Adaptor

Power the Raspberry Pi down and disconnect power before changing any wiring.

The SEN0368 adaptor should be configured with:

- top selector set to **VIN**
- IO1 jumper **UP**
- IO2 jumper **DOWN**

The blue IO1 conductor is not used by this project and should be insulated so that it cannot contact other circuitry.

### Check TB3

The SEN0368 adaptor connects through TB3:

| TB3 Terminal | Connection |
|---:|---|
| 1 | 5 V |
| 2 | GND |
| 3 | IO2 to Q1 interface |

Confirm that:

- the adaptor receives 5 V
- ground is secure
- IO2 is connected to the Q1 interface
- IO1 has not accidentally been connected
- terminal-block screws are secure
- no loose conductor or solder bridge is present

### Check Q1

Q1 is a BC337 NPN transistor and the project wiring assumes the documented **C-B-E** lead arrangement.

The interface is:

```text
SEN0368 IO2 ── 10 kΩ ── Base Q1
                         │
                       100 kΩ
                         │
                        GND

Q1 Emitter ───────────── GND

Q1 Collector ─────────── GPIO24
                         │
                        10 kΩ
                         │
                        3.3 V
```

Confirm that:

- the BC337 is installed in the documented C-B-E orientation
- emitter is connected to ground
- collector is connected to GPIO24
- the 10 kΩ GPIO24 pull-up is connected to 3.3 V
- the 10 kΩ base resistor is present
- the 100 kΩ base-to-ground resistor is present

The transistor interface both protects the Raspberry Pi from the adaptor's 5 V signal and inverts the logic.

For the complete circuit, see [Wiring](wiring.md).

### Sensor Does Not Change State

If the reported state never changes:

1. confirm the SEN0368 physically changes between wet and dry conditions
2. check that the adaptor has power
3. check IO2 and Q1 wiring
4. inspect the sensor and cable for damage
5. confirm GPIO24 is not shorted permanently to ground or 3.3 V

Do not probe or alter the circuit while powered unless you are deliberately performing an appropriate voltage measurement.

### After Correcting the Fault

Repeat the hardware self-test in both wet and dry conditions.

If the system has already been commissioned, restart the monitor:

```bash
sudo systemctl restart hydro-monitor.service
```

Confirm that the dashboard correctly follows the physical return-water condition and repeat the applicable alarm test from [Commissioning](commissioning.md).

## Low Reservoir Alarm Does Not Operate

The reservoir float switch is connected to GPIO17 and uses a deliberately **fail-safe** arrangement.

The expected logic is:

| Physical / Electrical Condition | GPIO17 Raw Value | Interpretation |
|---|---:|---|
| Acceptable water level, switch closed to GND | `0` | Reservoir level acceptable |
| Low water, switch open | `1` | Low reservoir |
| Broken or disconnected float circuit | `1` | Low reservoir |

A disconnected wire is therefore treated as a fault rather than as a safe condition.

### Check the Current Input State

Stop the continuous monitor before running the hardware self-test:

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

With the float in its normal-water position, the result should include:

```text
Low-level input electrical value: 0
Reservoir level interpreted as acceptable: True
```

With the float in the low-water position:

```text
Low-level input electrical value: 1
Reservoir level interpreted as acceptable: False
```

### Check Float Orientation

The float must be installed so that its contact is **closed at an acceptable reservoir level** and opens when the water level falls.

If the logic is reversed, first check the physical orientation of the float rather than changing the software.

The Jaycar Electronics SF0920 float can be mechanically reoriented by reversing the float body on its stem if necessary.

### Check TB1 Wiring

The reservoir float uses TB1 terminals 3 and 4:

| TB1 Terminal | Connection |
|---:|---|
| 3 | GPIO17 |
| 4 | GND |

Confirm that:

- the float switch is connected between GPIO17 and GND
- the external 10 kΩ pull-up resistor connects GPIO17 to 3.3 V
- terminal-block screws are secure
- no conductor is loose or broken
- GPIO17 is not shorted permanently to ground

Power the Raspberry Pi down before changing any wiring.

### Test the Fail-Safe Behaviour

With power removed, disconnect one float-switch conductor.

Restore power and run the hardware self-test again.

The reservoir should now be interpreted as **low**, because the open circuit allows the 10 kΩ pull-up resistor to pull GPIO17 HIGH.

If a disconnected float circuit is interpreted as acceptable, stop troubleshooting and re-check the wiring against [Wiring](wiring.md).

### Alarm Does Not Appear Immediately

The software applies a confirmation delay before declaring the low-reservoir alarm.

If the raw input changes correctly but the alarm is not immediately active, allow the configured confirmation period to expire before judging the result.

Do not shorten or bypass the confirmation period merely to compensate for a wiring fault.

### After Correcting the Fault

Repeat the hardware self-test with the float in both positions.

If the system has already been commissioned, restart the monitor:

```bash
sudo systemctl restart hydro-monitor.service
```

Then confirm that:

- the dashboard follows the physical float position
- the low-reservoir alarm appears after the expected confirmation period
- the red LED and buzzer operate correctly
- the alarm clears after restoring the float to the normal-water position

Repeat the applicable alarm test from [Commissioning](commissioning.md).

## Alarm-Inhibit Switch Does Not Work

The maintained alarm-inhibit switch is connected to GPIO18 and uses the Raspberry Pi's internal pull-up resistor.

The expected logic is:

| Switch Condition | GPIO18 State | Interpretation |
|---|---:|---|
| Switch open | HIGH | Alarms enabled |
| Switch closed to GND | LOW | Alarm inhibit active |

The switch does not disable monitoring. It suppresses the local alarm outputs while leaving the underlying sensor condition visible to the software and dashboard.

### Check the Current Input State

Stop the continuous monitor before running the hardware self-test:

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

With the switch in its normal **alarms enabled** position, the result should report:

```text
Override switch active: False
```

With the switch set to inhibit alarms:

```text
Override switch active: True
```

### Check TB1 Wiring

The alarm-inhibit switch uses TB1 terminals 1 and 2:

| TB1 Terminal | Connection |
|---:|---|
| 1 | GPIO18 |
| 2 | GND |

Confirm that:

- the maintained SPST switch connects GPIO18 directly to GND when closed
- no external pull-up resistor has been added
- terminal-block screws are secure
- GPIO18 is not permanently shorted to ground
- the switch opens and closes electrically as expected

Power the Raspberry Pi down before changing any wiring.

### Check the Switch Itself

With the Raspberry Pi powered down and the switch disconnected from TB1 if necessary, use a multimeter continuity test to confirm that:

- one switch position is open circuit
- the other switch position has continuity between its two terminals

If both positions show the same result, the switch or its connections may be faulty.

### Amber LED Does Not Follow the Switch

If the self-test reports the correct inhibit state but the amber LED does not respond correctly, the fault is likely in the LED/output circuit rather than the switch input.

Check:

- GPIO20 connection
- 330 Ω series resistor
- LED polarity
- LED ground connection
- solder joints and terminal connections

The hardware self-test can be used to confirm whether the amber LED can be operated independently.

### Buzzer Still Sounds While Inhibited

If the dashboard shows the alarm-inhibit switch as active but the buzzer continues operating:

1. confirm the monitor service is running the expected software version
2. confirm the dashboard and monitor agree that inhibit is active
3. inspect the recent monitor log
4. repeat the alarm-inhibit commissioning test

Check the installed version:

```bash
cat /opt/hydro-monitor/VERSION
```

Check recent monitor messages:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager
```

Do not change GPIO logic in the configuration to compensate for an incorrectly wired switch.

### After Correcting the Fault

If the system has already been commissioned, restart the monitor:

```bash
sudo systemctl restart hydro-monitor.service
```

Confirm that:

- alarms are enabled with the switch open
- the amber LED is off in normal operation
- inhibit becomes active when the switch is closed
- the amber LED illuminates while inhibited
- the red LED and buzzer are suppressed during a test alarm
- the underlying alarm condition remains visible on the dashboard

Return the switch to **alarms enabled** after testing and repeat the applicable section of [Commissioning](commissioning.md).

## Indicator or Buzzer Does Not Operate

The hardware self-test operates each alarm output independently, making it the best first check when an LED or the buzzer does not behave as expected.

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

The self-test briefly operates:

1. amber LED
2. red LED
3. green LED
4. buzzer

Observe each output and note which one fails.

### LED Does Not Illuminate

The three panel-mounted LEDs are connected through TB6:

| TB6 Terminal | Connection |
|---:|---|
| 1 | Red LED anode from GPIO26 through 330 Ω |
| 2 | Red LED cathode / GND |
| 3 | Amber LED anode from GPIO20 through 330 Ω |
| 4 | Amber LED cathode / GND |
| 5 | Green LED anode from GPIO21 through 330 Ω |
| 6 | Green LED cathode / GND |

Each LED circuit is:

```text
GPIO ── 330 Ω ── LED anode (+)
                    LED cathode (−) ── GND
```

If one LED fails while the others work, power the Raspberry Pi down and check:

- LED polarity
- the 330 Ω series resistor
- the corresponding GPIO connection
- the LED ground connection
- TB6 terminal connections
- solder joints
- the panel wiring between TB6 and the LED

For a conventional through-hole LED, the longer lead is normally the anode and the shorter lead is normally the cathode. The flat edge of the LED body normally identifies the cathode.

Verify the actual component before relying solely on lead length.

### All LEDs Fail

If none of the LEDs operate during the hardware self-test, check the shared ground connections and protoboard wiring before assuming that three LEDs have failed independently.

Also confirm that the self-test itself is running without GPIO initialisation errors.

### Buzzer Does Not Sound

The 5 V active buzzer is switched by Q2, a BC337 NPN transistor.

The project wiring assumes the documented **C-B-E** transistor lead arrangement.

The buzzer circuit is:

```text
GPIO12 ── 1 kΩ ── Base Q2
                   │
                  10 kΩ
                   │
                  GND

Q2 Emitter ─────── GND

Q2 Collector ───── Buzzer negative
                    Buzzer positive ── 5 V
```

Power the Raspberry Pi down before changing any wiring.

Confirm that:

- the buzzer positive terminal is connected to 5 V
- the buzzer negative terminal is connected to Q2 collector
- Q2 emitter is connected to GND
- GPIO12 reaches Q2 base through the 1 kΩ resistor
- the 10 kΩ base-to-ground resistor is fitted
- Q2 is installed in the documented C-B-E orientation
- the buzzer polarity is correct
- solder joints are sound

The 10 kΩ base-to-ground resistor keeps Q2 off while the Raspberry Pi is booting or GPIO12 is otherwise not being actively driven.

### Output Works in Self-Test but Not During an Alarm

If an LED or buzzer works during the hardware self-test but does not operate during normal monitoring, the physical output circuit is probably functional.

Check instead:

- whether the expected alarm is actually active
- whether the alarm-inhibit switch is active
- whether the alarm confirmation or startup grace period has elapsed
- whether the dashboard reports the same alarm state
- recent monitor service messages

Check the monitor log:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager
```

Do not alter GPIO assignments merely because an expected alarm output did not activate. First determine whether the software actually declared the relevant alarm condition.

### After Correcting the Fault

Repeat the hardware self-test and confirm that all three LEDs and the buzzer operate individually.

If the system has already been commissioned, restart the monitor:

```bash
sudo systemctl restart hydro-monitor.service
```

Then repeat the applicable alarm and indicator checks in [Commissioning](commissioning.md).

## RTC or System Time Incorrect

The DS3231 RTC provides time retention when the Raspberry Pi is powered down. During normal network-connected operation, Raspberry Pi OS synchronises the system clock from network time.

The RTC should therefore be treated as a backup time source rather than as a replacement for normal network time synchronisation.

### Run the RTC Verification Utility

Run:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

A working RTC should report:

- `/dev/rtc0` present
- an RTC driver
- the current Raspberry Pi system time
- the current RTC time
- the DS3231 on I2C bus 1

At I2C address `0x68`, the scan may show:

```text
UU
```

This is normally expected and means the kernel RTC driver has claimed the device.

### RTC Device Is Missing

If the utility reports:

```text
ERROR: /dev/rtc0 is missing.
```

shut the Raspberry Pi down and remove power before checking the RTC hardware.

Confirm that the DS3231 module is fitted in the documented position:

| RTC Position | Raspberry Pi Physical Pin | Function |
|---:|---:|---|
| 1 | 1 | 3.3 V |
| 2 | 3 | GPIO2 / SDA |
| 3 | 5 | GPIO3 / SCL |
| 4 | 7 | NC |
| 5 | 9 | GND |

The RTC position over physical pin 7 is not electrically connected. GPIO4 therefore remains available for the DS18B20 1-Wire bus.

Also confirm that:

- the RTC is fitted in the correct orientation
- the extra-long GPIO header is correctly aligned
- the module is fully seated
- no pin is offset by one position
- no bent pin or solder fault is present

Do not fit, remove or reposition the RTC while the Raspberry Pi is powered.

### Check the RTC Boot Configuration

The installer configures I2C and the DS3231 RTC overlay automatically.

If the RTC hardware is correctly fitted but `/dev/rtc0` is still missing, run:

```bash
sudo /opt/hydro-monitor/configure_rtc.sh
```

The utility checks the Raspberry Pi boot configuration, enables I2C where required and installs the DS3231 RTC overlay.

It also creates a timestamped backup of the boot configuration before making changes.

Reboot when instructed:

```bash
sudo reboot
```

Then reconnect and run:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

Do not manually add additional RTC overlays without first checking the existing configuration. The supplied configuration utility deliberately refuses to stack a conflicting I2C RTC overlay.

### System Time Is Correct but RTC Time Is Wrong

First confirm that network time synchronisation is active:

```bash
timedatectl status
```

The Raspberry Pi system clock should show the correct local date and time, and network time synchronisation should be active.

Once the system clock is known to be correct, initialise the RTC from it:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh --sync-from-system
```

The utility will **refuse to overwrite the RTC unless Raspberry Pi OS reports that network time is synchronised**.

This prevents an incorrect system clock from being written into the RTC.

### System Time Is Wrong After a Power Failure

Check the RTC first:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

If the RTC itself contains the correct time but the Raspberry Pi system clock is wrong, inspect the boot-time RTC configuration and system logs before rewriting the RTC.

If both the RTC and system time are wrong, reconnect the Raspberry Pi to the network and allow network time synchronisation to establish the correct system clock before using:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh --sync-from-system
```

### RTC Loses Time While the Raspberry Pi Is Off

If the RTC repeatedly loses its clock while the Raspberry Pi is powered down, check the RTC module's backup battery.

Replace the battery if necessary using the correct type specified for the RTC module.

After replacing the battery, allow the Raspberry Pi to obtain correct network time and initialise the RTC again.

### fake-hwclock

Some Raspberry Pi OS installations include `fake-hwclock`, which stores an approximate software clock during shutdown.

The RTC verification utility reports if `fake-hwclock.service` exists.

Once the physical DS3231 has been confirmed to operate correctly, it can be disabled with:

```bash
sudo systemctl disable --now fake-hwclock.service
```

Do not disable `fake-hwclock` until the DS3231 has been physically installed and verified.

### After Correcting an RTC Fault

Run:

```bash
sudo /opt/hydro-monitor/verify_rtc.sh
```

Confirm that both the Raspberry Pi system time and RTC time are sensible.

Then repeat the restart portion of [Commissioning](commissioning.md) to verify that correct timekeeping survives a reboot.

## Remote Notification Not Received

Pushover notifications are optional and depend on Internet access.

A Pushover failure does **not** stop local monitoring, the dashboard, LEDs, buzzer or historical logging.

### Check Pushover Status

Run:

```bash
sudo /opt/hydro-monitor/configure_pushover.py --status
```

Confirm that Pushover is enabled and that the required credentials are present.

The User Key and Application API Token should never be displayed in full.

### Send a Test Notification

Run:

```bash
sudo /opt/hydro-monitor/configure_pushover.py --test-only
```

If the test message arrives, the Pushover account, credentials and Internet connection are working.

If it does not arrive, continue with the checks below.

### Check Internet Connectivity

Confirm that the Raspberry Pi has network connectivity:

```bash
ping -c 3 1.1.1.1
```

Then confirm DNS resolution:

```bash
ping -c 3 pushover.net
```

If the first command succeeds but the second fails, investigate DNS configuration.

If neither succeeds, investigate the Raspberry Pi network connection before troubleshooting Pushover itself.

### Check the Monitor Log

View recent monitor messages:

```bash
journalctl -u hydro-monitor.service -n 100 --no-pager
```

To show likely Pushover-related entries only:

```bash
journalctl -u hydro-monitor.service -n 200 --no-pager | grep -i pushover
```

Look for messages involving:

- authentication failure
- invalid User Key
- invalid Application API Token
- network or DNS failure
- HTTP errors
- notification suppression
- alarm inhibit

### Reconfigure Pushover

If the credentials may be incorrect, rerun:

```bash
sudo /opt/hydro-monitor/configure_pushover.py
```

Enter:

- the Pushover User Key
- the dedicated Application API Token
- an optional device name, if notifications should be limited to one device

The configuration utility validates the credentials and sends a harmless setup-test notification.

Do not manually place Pushover credentials in `config.json`.

### Test the Pushover Account Independently

If the configuration utility reports success but no notification appears:

- check that notifications from Pushover are permitted on the phone
- confirm that the intended device is active in the Pushover account
- check whether a specific device name was configured
- confirm that Do Not Disturb, Focus or similar phone settings are not suppressing the alert
- inspect the Pushover application for the received message even if no audible phone alert occurred

### Test a Real Alarm

A successful `--test-only` message proves the communication path, but not necessarily the complete Hydroponics Monitor alarm path.

With the controller supervised, create a suitable commissioning alarm such as a low-reservoir condition.

Confirm that:

- the dashboard reports the alarm
- local LED and buzzer behaviour is correct
- the corresponding Pushover notification arrives

Restore the test condition afterwards.

### Alarm Is Visible Locally but No Pushover Message Is Sent

Check whether the alarm-inhibit switch is active.

When alarm inhibit is active, the underlying sensor condition remains visible on the dashboard while alarm outputs, including Pushover notifications, are suppressed as designed.

Also confirm that:

- Pushover is enabled
- the alarm confirmation period has elapsed
- the monitor service is running
- Internet access is available

### Duplicate or Unexpected Notifications

Check the monitor log to determine which alarm transition generated each notification.

Do not assume that repeated messages necessarily indicate a software fault. A condition that clears and then reappears can legitimately generate new notifications.

If notification behaviour does not match the documented alarm state transitions, record:

- the approximate time
- the alarm shown on the dashboard
- the notification text
- relevant monitor log entries

Do not include Pushover credentials when sharing logs or screenshots.

### After Correcting the Fault

Send another harmless test notification:

```bash
sudo /opt/hydro-monitor/configure_pushover.py --test-only
```

Then repeat one supervised real-alarm notification test before returning the controller to unattended operation.

## After a Wiring Change

After any wiring repair or modification:

* inspect the modified area
* check for solder bridges
* confirm polarity
* verify continuity where appropriate
* repeat the relevant commissioning tests before returning the system to unattended operation

## Known Issues

Confirmed software or hardware issues will be listed here as they are identified.
