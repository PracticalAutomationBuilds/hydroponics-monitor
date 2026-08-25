# Wiring

## Status

**Work in progress.**

The wiring shown in this repository reflects the current prototype design and may change before the first stable release.

## Raspberry Pi GPIO Assignments

GPIO numbers use BCM numbering.

| Function | BCM GPIO | Physical Pin | Interface / Notes |
|---|---:|---:|---|
| RTC SDA | GPIO2 | 3 | I²C |
| RTC SCL | GPIO3 | 5 | I²C |
| Reservoir DS18B20 DATA | GPIO4 | 7 | Shared 1-Wire bus |
| Grow-pipe DS18B20 DATA | GPIO4 | 7 | Shared 1-Wire bus |
| Reservoir low-level float | GPIO17 | 11 | External 10 kΩ pull-up to 3.3 V; fail-safe active-high fault |
| Alarm-inhibit switch | GPIO18 | 12 | Maintained SPST switch to GND; internal pull-up |
| DHT22 DATA | GPIO22 | 15 | Digital data |
| SEN0368 return-water signal | GPIO24 | 18 | Q1 BC337 interface; water present = GPIO LOW |
| Buzzer control | GPIO12 | 32 | Q2 BC337 low-side driver |
| Red alarm LED | GPIO26 | 37 | External 330 Ω series resistor |
| Amber inhibit LED | GPIO20 | 38 | External 330 Ω series resistor |
| Green status LED | GPIO21 | 40 | External 330 Ω series resistor |

## Power Distribution

The Raspberry Pi is powered through its normal Micro USB power input. The Makerverse Protoboard for Raspberry Pi then uses the Raspberry Pi GPIO header supplies for the project circuitry.

### Raspberry Pi Header Supplies

| Supply | Raspberry Pi Physical Pin | Use |
|---|---:|---|
| 3.3 V | 1 or 17 | Sensors and pull-up circuits |
| 5 V | 2 or 4 | SEN0368 adaptor and active buzzer |
| GND | Any suitable GND pin | Common circuit ground |

Suitable ground pins include physical pins 6, 9, 14 and 20.

### 3.3 V Loads

The 3.3 V rail supplies:

- both DS18B20 temperature probes
- the DHT22 module
- the shared 4.7 kΩ DS18B20 1-Wire pull-up
- the 10 kΩ Q1 collector pull-up
- the 10 kΩ reservoir-float pull-up
- the DS3231 RTC through the Raspberry Pi header

### 5 V Loads

The 5 V rail supplies:

- the SEN0368 adaptor
- the active 5 V buzzer

### Grounding

All sensors, interface circuitry, indicators and the Raspberry Pi use a common ground.

The external sensor and switch ground connections are returned to the appropriate terminal blocks on the Makerverse Protoboard.

### Voltage-Level Warning

**Never connect a 5 V signal directly to a Raspberry Pi GPIO input.**

The SEN0368 adaptor operates from 5 V, so its IO2 signal is interfaced to GPIO24 through the Q1 BC337 transistor circuit rather than being connected directly to the Raspberry Pi.

## Sensors

### DS18B20 Temperature Sensors

Connection details for the shared 1-Wire temperature-sensor bus will be documented here.

### Ambient Temperature and Humidity Sensor

Connection details will be added once the final hardware layout is confirmed.

### Return Water-Level Sensor

Connection details will be added once the final hardware layout is confirmed.

### Low Reservoir Float Switch

Connection details will be added once the final hardware layout is confirmed.

## Indicators and Alarm

This section will document:

* status LEDs
* current-limiting resistors
* buzzer
* transistor/interface circuitry
* pull-up or pull-down resistors where required

## RTC Module

The real-time clock connection and GPIO/header arrangement will be documented here.

## Terminal Blocks

Terminal-block assignments will be documented after the prototype board layout has been finalised.

## Prototype Board Layout

A final component-placement diagram and underside wiring plan will be added after the physical board has been assembled and tested.

## Wiring Diagram

A complete wiring diagram will be included here before the first stable release.

## Safety and Construction Notes

Final construction notes will include:

* polarity checks
* voltage-level considerations
* sensor lead identification
* soldering and insulation requirements
* strain relief
* enclosure considerations
