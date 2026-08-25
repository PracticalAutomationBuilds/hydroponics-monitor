# Bill of Materials

## Status

**Work in progress.**

This bill of materials reflects the current prototype build and may change before the first stable release.

## Main Controller

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 1 | Single-board computer | Raspberry Pi 3 Model B | Core Electronics | Main controller |
| 1 | Prototyping board | Makerverse Protoboard for Raspberry Pi | Core Electronics | Permanent soldered controller board; mounts directly on the Raspberry Pi GPIO header |
| 1 | Real-time clock | DS3231 RTC module, XC9044 | Jaycar | Battery-backed clock; uses GPIO2/GPIO3 for I²C |

## Sensors

| Qty | Component | Part / Model | Supplier | Notes |
|---:|---|---|---|---|
| 2 | Waterproof digital temperature probe | DS18B20 | Core Electronics | Reservoir and grow-pipe probes; share the GPIO4 1-Wire bus |
| 1 | Ambient temperature and humidity module | DHT22 | Core Electronics | 3.3 V; data on GPIO22 |
| 1 | Non-contact return-water sensor | DFRobot SEN0368 | Core Electronics | Powered from 5 V; IO2 interfaces to GPIO24 through Q1; IO1 is unused |
| 1 | Reservoir low-water float switch | SF0920 | Jaycar | Passive contact; fail-safe input to GPIO17 using an external 10 kΩ pull-up |

## Indicators and Alarms

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

## Interface and Protection Components

| Qty | Component | Part / Model | Supplier | Notes |
| --: | --------- | ------------ | -------- | ----- |
|     |           |              |          |       |

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
