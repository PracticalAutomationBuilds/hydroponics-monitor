# Troubleshooting

## Status

**Work in progress.**

This guide will be expanded as the prototype system is assembled, commissioned and operated.

## General Approach

When troubleshooting the Hydroponics Monitor:

1. identify the failed function
2. check the dashboard or log output for relevant errors
3. confirm the affected hardware connection
4. verify power and ground
5. test the individual sensor or output where practical
6. make only one change at a time
7. repeat the relevant commissioning test after correcting the fault

## Raspberry Pi Does Not Boot

Check:

* power supply and cable
* microSD card installation
* Raspberry Pi status LEDs
* attached hardware for possible shorts or incorrect connections

Disconnect external hardware if necessary and confirm that the Raspberry Pi can boot independently.

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
