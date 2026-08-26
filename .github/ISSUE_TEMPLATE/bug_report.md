---
name: Bug report
about: Report a reproducible Hydroponics Monitor problem
title: "[Bug] "
labels: bug
assignees: ""
---

## Installed Version

Run:

`cat /opt/hydro-monitor/VERSION`

Version:

## Problem

Describe what happened and what you expected to happen.

## Steps to Reproduce

1.
2.
3.

## Dashboard State

Describe the relevant sensor, alarm or connection state shown on the dashboard.

## Hardware Self-Test

Has the hardware self-test passed?

- [ ] Yes
- [ ] No
- [ ] Not applicable / not tested

If relevant, describe any failed output or unexpected sensor reading.

## Relevant Logs

Include only the relevant portion of the service log.

Monitor:

`journalctl -u hydro-monitor.service -n 100 --no-pager`

Dashboard:

`journalctl -u hydro-dashboard.service -n 100 --no-pager`

## Hardware Changes

Have any wiring, sensors, components or GPIO connections been changed since the system last worked correctly?

- [ ] No
- [ ] Yes

If yes, describe the change.

## Restart Behaviour

Does the problem remain after a controlled restart?

- [ ] Yes
- [ ] No
- [ ] Not tested

## Additional Information

Add any other useful details, photographs or screenshots.

Do **not** include passwords, Pushover User Keys, API tokens or other private credentials.
