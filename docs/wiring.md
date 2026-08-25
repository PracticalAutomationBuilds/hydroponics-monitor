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

Two waterproof DS18B20 temperature probes share a single Raspberry Pi 1-Wire bus on GPIO4.

Each probe has its own 3-way terminal block so that either sensor can be disconnected or replaced independently.

#### Reservoir DS18B20 — TB4

| Terminal | Connection | Probe Wire |
|---:|---|---|
| 1 | 3.3 V | Red |
| 2 | DATA / GPIO4 shared bus | White |
| 3 | GND | Black |

#### Grow-Pipe DS18B20 — TB5

| Terminal | Connection | Probe Wire |
|---:|---|---|
| 1 | 3.3 V | Red |
| 2 | DATA / GPIO4 shared bus | White |
| 3 | GND | Black |

#### Shared 1-Wire Bus

The two probes are connected in parallel:

- both red wires connect to 3.3 V
- both white DATA wires connect to the common GPIO4 bus
- both black wires connect to GND
- one shared 4.7 kΩ pull-up resistor connects the DATA/GPIO4 bus to 3.3 V

Only **one 4.7 kΩ pull-up resistor** is used for the complete 1-Wire bus.

The two sensors are distinguished in software by their unique DS18B20 hardware IDs, which are assigned permanently as the reservoir and grow-pipe probes during commissioning.

### Ambient Temperature and Humidity Sensor

The ambient sensor is a Core Electronics DHT22 module connected through the 3-way TB2 terminal block.

#### DHT22 — TB2

| Terminal | Connection |
|---:|---|
| 1 | 3.3 V |
| 2 | DATA / GPIO22 |
| 3 | GND |

The DHT22 module used for this project already includes its required support components, so **no additional DHT22 pull-up resistor is fitted on the Makerverse Protoboard**.

The DHT22 provides ambient temperature and relative-humidity data for the dashboard and historical logging. It is informational only and does not directly trigger the system alarms.

### Return Water-Level Sensor

The return-water sensor is a DFRobot SEN0368 non-contact liquid-level sensor operating through its supplied 5 V adaptor.

The adaptor connects to the controller through the 3-way TB3 terminal block.

#### SEN0368 — TB3

| Terminal | Connection |
|---:|---|
| 1 | 5 V / VIN |
| 2 | GND |
| 3 | IO2 signal to Q1 interface |

The adaptor settings are:

- top switch: VIN
- IO1 jumper: UP
- IO2 jumper: DOWN

The blue IO1 lead is not used in this installation. Insulate it and secure it out of the way.

#### Q1 Level-Shifting Interface

Because the SEN0368 adaptor operates at 5 V, its IO2 signal must not be connected directly to a Raspberry Pi GPIO.

A BC337 NPN transistor provides the interface:

```text
SEN0368 IO2 ---- 10 kΩ ---- Q1 base
Q1 base -------- 100 kΩ --- GND
Q1 emitter ---------------- GND
Q1 collector -------------- GPIO24
GPIO24 --------- 10 kΩ ---- 3.3 V
```

The resulting Raspberry Pi logic is:

- water present: SEN0368 IO2 HIGH → Q1 ON → GPIO24 LOW
- no water: SEN0368 IO2 LOW → Q1 OFF → GPIO24 HIGH

The software therefore treats the return-water input as active-low, with `wet_level: 0`.

The 100 kΩ base pull-down and 10 kΩ GPIO24 pull-up perform separate functions and both are required.

### Low Reservoir Float Switch

The reservoir low-water detector is a passive float switch connected through the 4-way TB1 terminal block.

TB1 is shared with the maintained alarm-inhibit switch.

#### Reservoir Float — TB1

| Terminal | Connection |
|---:|---|
| 3 | Reservoir float signal / GPIO17 |
| 4 | GND |

The float-switch input uses an external **10 kΩ pull-up resistor to 3.3 V**.

The circuit is:

```text
3.3 V
  |
10 kΩ
  |
GPIO17 -------- float switch -------- GND
```

The switch is arranged so that:

- acceptable reservoir level = switch closed to GND = GPIO17 LOW
- low reservoir level = switch open = GPIO17 HIGH
- broken or disconnected float-switch wiring = open circuit = GPIO17 HIGH

This provides fail-safe behaviour: a disconnected or broken float-switch circuit produces the same fault state as a genuinely low reservoir level.

The software therefore treats GPIO17 HIGH as the reservoir low-level alarm condition.

## Indicators and Alarm

The controller uses three panel-mounted 10 mm LEDs, one maintained alarm-inhibit rocker switch and one PCB-mounted 5 V active buzzer.

### Alarm-Inhibit Switch — TB1

TB1 is shared with the reservoir float switch.

| Terminal | Connection |
|---:|---|
| 1 | Alarm-inhibit input / GPIO18 |
| 2 | GND |

The maintained SPST rocker switch connects GPIO18 to GND when alarms are inhibited.

GPIO18 uses the Raspberry Pi internal pull-up, so:

- switch open = GPIO18 HIGH = alarms enabled
- switch closed = GPIO18 LOW = alarms inhibited

### Enclosure LEDs — TB6

The three panel-mounted LEDs connect through the 6-way TB6 terminal block.

| Terminal | Connection |
|---:|---|
| 1 | Red LED anode feed from GPIO26 through 330 Ω |
| 2 | Red LED cathode / GND |
| 3 | Amber LED anode feed from GPIO20 through 330 Ω |
| 4 | Amber LED cathode / GND |
| 5 | Green LED anode feed from GPIO21 through 330 Ω |
| 6 | Green LED cathode / GND |

Each LED requires its own external **330 Ω series resistor**.

The LED functions are:

- red = confirmed active alarm
- amber = alarms inhibited
- green = healthy/startup status

### Buzzer Driver — Q2

The 5 V active buzzer is mounted directly on the Makerverse Protoboard rather than connected through a terminal block.

A BC337 NPN transistor provides low-side switching from GPIO12:

```text
GPIO12 --------- 1 kΩ ----- Q2 base
Q2 base -------- 10 kΩ ---- GND
Q2 emitter ---------------- GND
Q2 collector -------------- buzzer negative
5 V ----------------------- buzzer positive
```

The 10 kΩ base pull-down keeps the buzzer off while GPIO12 is floating during boot or shutdown.

The selected active buzzer is treated as non-inductive, so no flyback diode is required.

## RTC Module

The real-time clock is a Jaycar Electronics XC9044 DS3231 module mounted directly on the Raspberry Pi GPIO header.

The Makerverse Protoboard for Raspberry Pi is fitted using a **GPIO Header for Raspberry Pi B+ (Extra-long 2x20 Female Header)** from Core Electronics. The extended upper pins pass through the Makerverse board and remain exposed above it, allowing the RTC module to be fitted to the Raspberry Pi header positions in the normal way.

The RTC occupies the odd-numbered header positions shown below:

| RTC Position | Raspberry Pi Physical Pin | Function |
|---:|---:|---|
| 1 | 1 | 3.3 V |
| 2 | 3 | GPIO2 / SDA |
| 3 | 5 | GPIO3 / SCL |
| 4 | 7 | NC on RTC module |
| 5 | 9 | GND |

The RTC communicates with the Raspberry Pi over I²C using GPIO2 and GPIO3.

The RTC position above physical pin 7 is **not connected internally on the RTC module**, so it does not electrically consume GPIO4. GPIO4 therefore remains available for the shared DS18B20 1-Wire bus.

The Raspberry Pi must be powered down before fitting or removing the Makerverse Protoboard or RTC module.

## Terminal Blocks

The permanent v9.1.2 controller uses six side-entry screw terminal blocks on the Makerverse Protoboard for Raspberry Pi.

The final allocation is:

| Terminal Block | Size | Function | Connections |
|---|---:|---|---|
| TB1 | 4-way | Alarm-inhibit switch and reservoir float switch | GPIO18, GND, GPIO17, GND |
| TB2 | 3-way | DHT22 ambient sensor | 3.3 V, GPIO22 DATA, GND |
| TB3 | 3-way | SEN0368 return-water sensor | 5 V, GND, IO2 to Q1 interface |
| TB4 | 3-way | Reservoir DS18B20 | 3.3 V, shared GPIO4 DATA, GND |
| TB5 | 3-way | Grow-pipe DS18B20 | 3.3 V, shared GPIO4 DATA, GND |
| TB6 | 6-way | Red, amber and green enclosure LEDs | Individual anode feeds and GND returns for each LED |

### TB1 — Alarm-Inhibit Switch and Reservoir Float

| Terminal | Connection |
|---:|---|
| 1 | Alarm-inhibit input / GPIO18 |
| 2 | GND |
| 3 | Reservoir float input / GPIO17 |
| 4 | GND |

### TB2 — DHT22

| Terminal | Connection |
|---:|---|
| 1 | 3.3 V |
| 2 | DATA / GPIO22 |
| 3 | GND |

### TB3 — SEN0368

| Terminal | Connection |
|---:|---|
| 1 | 5 V / VIN |
| 2 | GND |
| 3 | IO2 signal to Q1 interface |

### TB4 — Reservoir DS18B20

| Terminal | Connection |
|---:|---|
| 1 | 3.3 V |
| 2 | DATA / shared GPIO4 1-Wire bus |
| 3 | GND |

### TB5 — Grow-Pipe DS18B20

| Terminal | Connection |
|---:|---|
| 1 | 3.3 V |
| 2 | DATA / shared GPIO4 1-Wire bus |
| 3 | GND |

### TB6 — Enclosure LEDs

| Terminal | Connection |
|---:|---|
| 1 | Red LED anode feed from GPIO26 through 330 Ω |
| 2 | Red LED cathode / GND |
| 3 | Amber LED anode feed from GPIO20 through 330 Ω |
| 4 | Amber LED cathode / GND |
| 5 | Green LED anode feed from GPIO21 through 330 Ω |
| 6 | Green LED cathode / GND |

The active buzzer is mounted directly on the Makerverse Protoboard and therefore does not require a terminal-block connection.

All terminal blocks are 0.1-inch / 2.54 mm pitch side-entry screw terminals.

## Prototype Board Layout

The permanent controller is assembled on a Makerverse Protoboard for Raspberry Pi using the extra-long 2×20 GPIO header.

The final board includes:

- TB1 — 4-way terminal block for the alarm-inhibit switch and reservoir float
- TB2 — 3-way terminal block for the DHT22
- TB3 — 3-way terminal block for the SEN0368 adaptor
- TB4 — 3-way terminal block for the reservoir DS18B20
- TB5 — 3-way terminal block for the grow-pipe DS18B20
- TB6 — 6-way terminal block for the three enclosure LEDs
- Q1 — BC337 interface for the SEN0368
- Q2 — BC337 low-side driver for the active buzzer
- BZ1 — PCB-mounted 5 V active buzzer
- the required pull-up, pull-down, base and LED series resistors
- underside soldered links where required

### Raspberry Pi Heatsink Keepout

A standard Raspberry Pi 3 Model B does not normally create a clearance problem beneath the Makerverse Protoboard.

If an aftermarket heatsink has been fitted, particularly a large or tall model, check the available clearance before finalising the protoboard layout.

A heatsink may occupy space beneath part of the Makerverse board and prevent some protoboard holes from being used for component leads, solder joints or underside links.

Where this occurs:

- components may still extend over the affected area if there is adequate vertical clearance
- do not use any blocked protoboard holes for component leads
- do not place solder joints or underside links where they could contact the heatsink
- verify clearance before powering the assembled board

This is not normally an issue with an unmodified Raspberry Pi.

### RTC Clearance

The extra-long GPIO header passes through the Makerverse Protoboard and leaves the upper GPIO pins exposed.

The DS3231 RTC module is fitted above the protoboard on these exposed pins, so component placement must also preserve sufficient clearance around the RTC.

### Final Pad-by-Pad Layout

The exact pad-by-pad component-placement diagram and underside-link map will be added to the `hardware/` directory after the permanent controller has been assembled, continuity-tested and confirmed against the Version 9.1.2 wiring.

The verified hardware drawing, rather than an earlier working layout, will be treated as the authoritative physical-board reference.

## Wiring Diagram

A final schematic-style wiring diagram will be added to the `hardware/` directory after the permanent controller board has been assembled and verified.

The diagram will show:

- Raspberry Pi GPIO assignments
- 3.3 V, 5 V and GND distribution
- both DS18B20 probes on the shared GPIO4 1-Wire bus
- DHT22 connection
- SEN0368 adaptor and Q1 interface
- reservoir float-switch fail-safe circuit
- alarm-inhibit switch
- red, amber and green LED circuits
- Q2 buzzer-driver circuit
- DS3231 RTC connection
- terminal-block assignments

Until that diagram is added, the tables and circuit descriptions in this document are the authoritative wiring reference for Version 9.1.2.

Any future wiring diagram added to the repository must be checked against the verified physical build before it is treated as authoritative.

## Safety and Construction Notes

Final construction notes will include:

* polarity checks
* voltage-level considerations
* sensor lead identification
* soldering and insulation requirements
* strain relief
* enclosure considerations
