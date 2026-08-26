# Hardware

This directory contains hardware-specific reference material for the Hydroponics Monitor.

The main written hardware documentation is maintained in:

- [Wiring](../docs/wiring.md) — GPIO allocation, circuit connections, terminal blocks and construction details
- [Bill of Materials](../docs/bill-of-materials.md) — selected components and reproducible sourcing information
- [Commissioning](../docs/commissioning.md) — verification and functional testing of the completed controller

## Permanent Controller

The controller is assembled on a **Makerverse Protoboard for Raspberry Pi** mounted above a Raspberry Pi 3 Model B.

The current design includes:

- DS3231 RTC mounted on the exposed extra-long GPIO header
- two DS18B20 temperature probes sharing the GPIO4 1-Wire bus
- DHT22 ambient temperature and humidity sensor
- DFRobot SEN0368 return-water sensor with BC337 interface
- fail-safe reservoir float switch
- red, amber and green status LEDs
- 5 V active buzzer with BC337 driver
- maintained alarm-inhibit switch

## Board Layout

A final pad-by-pad protoboard layout will be added here after the permanent board has been physically assembled, continuity-tested and commissioned.

The final published layout will represent the **verified as-built controller**, rather than an untested planning drawing.

Until then, the connection tables and circuit descriptions in [Wiring](../docs/wiring.md) are the authoritative hardware reference.

## Images

Construction photographs and other useful hardware reference images may also be added here as the permanent controller is completed.

Where possible, photographs should be taken before wiring or enclosure assembly hides important connections.
