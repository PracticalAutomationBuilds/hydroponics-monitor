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

Check:

* project files are present
* Python dependencies are installed
* configuration files exist
* required permissions are correct
* any automatic-start service is enabled and running

Relevant diagnostic commands will be added once the final installation method is established.

## Dashboard Cannot Be Reached

Check:

* the Raspberry Pi is running
* the monitoring software is running
* the Raspberry Pi is connected to the network
* the correct IP address or hostname is being used
* the configured dashboard port is correct
* another device on the same network can reach the Raspberry Pi

## DS18B20 Temperature Sensor Missing

Check:

* 1-Wire support is enabled
* sensor power, ground and data connections
* the shared data-bus connection
* the pull-up resistor
* sensor identification in the configuration
* terminal-block connections

If multiple DS18B20 sensors are fitted, confirm that the expected sensor IDs have not been accidentally swapped.

## Incorrect Temperature Sensor Assignment

If the nutrient-solution and grow-pipe temperature readings appear reversed:

* identify the physical sensors
* confirm their unique DS18B20 IDs
* check the sensor assignments in the configuration
* restart the monitoring software after making changes

## Ambient Temperature or Humidity Reading Missing

Check:

* sensor wiring
* supply voltage
* GPIO assignment
* sensor communication
* software configuration

Intermittent readings should be investigated before replacing the sensor, as some ambient temperature/humidity sensors may occasionally fail to return a valid reading.

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
