# Bill of Materials

## Status

**Work in progress.**

This bill of materials reflects the current prototype build and may change before the first stable release.

## Main Controller

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 1 | Single-board computer | Raspberry Pi 3 Model B | Core Electronics | Main controller |
| 1 | Prototyping board | Makerverse Protoboard for Raspberry Pi | Core Electronics | Permanent soldered controller board; mounts directly on the Raspberry Pi GPIO header |
| 1 | Real-time clock | DS3231 RTC module, XC9044 | Jaycar Electronics | Battery-backed clock; uses GPIO2/GPIO3 for I²C |

## Sensors

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 2 | Waterproof digital temperature probe | DS18B20 | Core Electronics | Reservoir and grow-pipe probes; share the GPIO4 1-Wire bus |
| 1 | Ambient temperature and humidity module | DHT22 | Core Electronics | 3.3 V; data on GPIO22 |
| 1 | Non-contact return-water sensor | DFRobot SEN0368 | Core Electronics | Powered from 5 V; IO2 interfaces to GPIO24 through Q1; IO1 is unused |
| 1 | Reservoir low-water float switch | SF0920 | Jaycar Electronics | Passive contact; fail-safe input to GPIO17 using an external 10 kΩ pull-up |

## Indicators and Alarms

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 1 | Red 10 mm diffused LED | SparkFun COM-10632 | Core Electronics | Alarm indicator; GPIO26; requires external 330 Ω series resistor |
| 1 | Yellow 10 mm diffused LED | SparkFun COM-10634 | Core Electronics | Used as amber alarm-inhibit indicator; GPIO20; requires external 330 Ω series resistor |
| 1 | Green 10 mm diffused LED | SparkFun COM-10633 | Core Electronics | Healthy/startup status indicator; GPIO21; requires external 330 Ω series resistor |
| 1 | 5 V active buzzer | CE09882 | Core Electronics | PCB-mounted audible alarm; driven from GPIO12 through Q2 |
| 1 | Maintained SPST rocker switch | Rocker Switch - SPST (round) | Core Electronics | Panel-mounted alarm-inhibit switch; connects GPIO18 to GND when active |

## Interface and Protection Components

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 2 | NPN transistor | Transistor - NPN (BC337) | Core Electronics | Q1 interfaces the 5 V SEN0368 output to the Raspberry Pi; Q2 is the 5 V buzzer low-side driver. Confirm collector, base and emitter orientation before soldering. |
| 1 pack | 1/4 W, 1% through-hole resistor assortment | CE05092 — 600 Pack of 1/4 Watt 1% Resistors | Core Electronics | Provides all resistor values required for the build: 330 Ω × 3, 1 kΩ × 1, 4.7 kΩ × 1, 10 kΩ × 4 and 100 kΩ × 1. |

## Connectors and Wiring

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

## Mechanical and Enclosure Components

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

## Optional Items

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

## Notes

Exact supplier links and substitutions will be added once the prototype hardware configuration has been finalised and tested.
