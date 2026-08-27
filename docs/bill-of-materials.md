# Bill of Materials

## Status

**Work in progress.**

This bill of materials reflects the current prototype build and may change before the first stable release.

## Main Controller

| Qty | Component | Part / Model | My Supplier | Notes |
|---:|---|---|---|---|
| 1 | Single-board computer | Raspberry Pi 3 Model B | Core Electronics | Main controller |
| 1 | Power supply | Official Raspberry Pi 12.5W Micro USB Power Supply | Core Electronics | 5.1 V, 2.5 A supply for the Raspberry Pi 3 Model B |
| 1 | High-endurance microSD card | SanDisk 64GB High Endurance microSDXC Card, XC5520 | Jaycar Electronics | System storage; high-endurance card selected for the repeated writes associated with continuous monitoring, logging and historical data |
| 1 | Extra-long GPIO header | GPIO Header for Raspberry Pi B+ (Extra-long 2x20 Female Header) | Core Electronics | Passes through the Makerverse Protoboard and leaves the GPIO pins accessible above the board for the RTC module |
| 1 | Prototyping board | Makerverse Protoboard for Raspberry Pi | Core Electronics | Permanent soldered controller board; mounts directly on the Raspberry Pi GPIO header |
| 1 | Real-time clock | DS3231 RTC module, XC9044 | Jaycar Electronics | Battery-backed clock; uses GPIO2/GPIO3 for I²C |

## Sensors

| Qty | Component | Part / Model | My Supplier | Notes |
|---:|---|---|---|---|
| 2 | Waterproof digital temperature probe | DS18B20 | Core Electronics | Reservoir and grow-pipe probes; share the GPIO4 1-Wire bus |
| 1 | Ambient temperature and humidity module | DHT22 | Core Electronics | 3.3 V; data on GPIO22 |
| 1 | Non-contact return-water sensor | DFRobot SEN0368 | Core Electronics | Powered from 5 V; IO2 interfaces to GPIO24 through Q1; IO1 is unused |
| 1 | Reservoir low-water float switch | SF0920 | Jaycar Electronics | Passive contact; fail-safe input to GPIO17 using an external 10 kΩ pull-up |

## Indicators and Alarms

| Qty | Component | Part / Model | My Supplier | Notes |
|---:|---|---|---|---|
| 1 | Red 10 mm diffused LED | SparkFun COM-10632 | Core Electronics | Alarm indicator; GPIO26; requires external 330 Ω series resistor |
| 1 | Yellow 10 mm diffused LED | SparkFun COM-10634 | Core Electronics | Used as amber alarm-inhibit indicator; GPIO20; requires external 330 Ω series resistor |
| 1 | Green 10 mm diffused LED | SparkFun COM-10633 | Core Electronics | Healthy/startup status indicator; GPIO21; requires external 330 Ω series resistor |
| 1 | 5 V active buzzer | CE09882 | Core Electronics | PCB-mounted audible alarm; driven from GPIO12 through Q2 |
| 1 | Maintained SPST rocker switch | Rocker Switch - SPST (round) | Core Electronics | Panel-mounted alarm-inhibit switch; connects GPIO18 to GND when active |

## Interface and Protection Components

| Qty | Component | Part / Model | My Supplier | Notes |
|---:|---|---|---|---|
| 2 | NPN transistor | Transistor - NPN (BC337) | Core Electronics | Q1 interfaces the 5 V SEN0368 output to the Raspberry Pi; Q2 is the 5 V buzzer low-side driver. Confirm collector, base and emitter orientation before soldering. |
| 1 pack | 1/4 W, 1% through-hole resistor assortment | CE05092 — 600 Pack of 1/4 Watt 1% Resistors | Core Electronics | Provides all resistor values required for the build: 330 Ω × 3, 1 kΩ × 1, 4.7 kΩ × 1, 10 kΩ × 4 and 100 kΩ × 1. |

## Connectors and Wiring

| Qty | Component | Part / Model | My Supplier | Notes |
|---:|---|---|---|---|
| 2 packs | 3-pin side-entry screw terminal block | Screw Terminal Block: 3-Pin, 0.1" Pitch, Side Entry (3-Pack) | Core Electronics | Four blocks used: DHT22, SEN0368, reservoir DS18B20 and grow-pipe DS18B20. |
| 1 pack | 4-pin side-entry screw terminal block | Screw Terminal Block: 4-Pin, 0.1" Pitch, Side Entry (2-Pack) | Core Electronics | One block used for the maintained alarm-inhibit switch and reservoir float switch. |
| 1 | 6-pin side-entry screw terminal block | Screw Terminal Block: 6-Pin, 0.1" Pitch, Side Entry | Core Electronics | One block provides separate anode and GND connections for the red, amber and green enclosure LEDs. |
| 1 kit | Stranded silicone hookup wire | Silicone Hookup Wire Kit, 22 AWG, 6 Colours | Core Electronics | Used for internal controller and enclosure wiring; multiple colours simplify identification of power, ground and signal connections. |

## Mechanical and Enclosure Components

The final enclosure has not yet been selected.

The enclosure requirements are currently:

- IP68-rated construction
- clear lid
- gasketed lid seal
- sufficient internal space for the assembled Raspberry Pi, RTC and Makerverse Protoboard stack
- sufficient panel area for the three 10 mm status LEDs and maintained rocker switch
- provision for suitable cable glands and strain relief

The exact enclosure model, size, supplier and cable-gland requirements will be added after the permanent controller board has been assembled and its required clearances can be measured.

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

## Optional Items

No optional hardware is currently specified for the current build.

Pushover remote notifications are optional and do not require additional project hardware. The local dashboard, LEDs, buzzer and monitoring functions operate without Pushover.

## Notes

- Supplier entries identify convenient sources for reproducing the project and do not necessarily indicate where the components used in the original build were purchased.
- Where practical, components have been consolidated around a small number of Australian suppliers.
- Equivalent components may be substituted only where their electrical characteristics, pinout, physical dimensions and mounting requirements are compatible with the documented design.
- Resistor quantities shown in the resistor-assortment entry refer to the values actually required by the completed controller.
- The final IP68 enclosure and associated cable glands have not yet been selected. These items will be added after the assembled Raspberry Pi, RTC and Makerverse Protoboard stack has been measured for the required enclosure clearances.
- The bill of materials will be updated if the physical prototype identifies any required changes before the first stable release.

Exact supplier links and substitutions will be added once the prototype hardware configuration has been finalised and tested.
