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

Confirm that:

* all wiring matches the final wiring documentation
* power and ground connections are correct
* sensor polarity has been checked
* no solder bridges or unintended connections are present
* terminal-block screws are secure
* exposed conductors cannot short against adjacent terminals or hardware
* the Raspberry Pi and connected devices are receiving the correct supply voltage

## Initial Power-Up

The final procedure will include checks for:

* successful Raspberry Pi boot
* automatic startup of the monitoring software
* dashboard availability
* absence of unexpected error messages
* correct system date and time

## Sensor Tests

### Nutrient-Solution Temperature Sensor

Verify that the sensor:

* is detected
* reports a plausible temperature
* responds appropriately to a controlled temperature change

### Grow-Pipe Temperature Sensor

Verify that the sensor:

* is detected
* reports a plausible temperature
* can be distinguished from the nutrient-solution sensor

### Ambient Temperature and Humidity Sensor

Verify that:

* temperature readings are plausible
* relative-humidity readings are plausible
* loss of sensor communication is detected correctly

### Return Water-Level Sensor

Verify normal operation across the expected water-level range.

### Low Reservoir Float Switch

Manually operate the float switch and confirm that both normal and low-water states are detected correctly.

## Indicator Tests

Test each visual indicator individually and confirm that:

* the correct LED activates
* the indicated condition matches the dashboard
* normal status is restored when the test condition is removed

## Audible Alarm Test

Trigger an alarm condition and confirm that:

* the buzzer operates
* the correct fault is displayed
* the alarm clears or resets as designed

## Remote Notification Test

Where remote notifications are enabled, trigger an appropriate test condition and confirm that:

* the notification is received
* the message identifies the correct condition
* repeated notifications behave as intended

## Dashboard Test

Confirm that the dashboard:

* loads correctly from another device on the local network
* displays all expected sensor readings
* displays system and alarm status correctly
* updates readings as expected
* records historical information where applicable

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
