# Contributing

Contributions to the Hydroponics Monitor are welcome where they improve reliability, documentation, reproducibility or maintainability.

This project combines Raspberry Pi software with physical electronics, so changes should be approached carefully.

## Before Making Changes

Please:

- review the existing documentation before changing hardware behaviour
- avoid changing established GPIO assignments without a clear technical reason
- preserve compatibility with the documented wiring wherever practical
- do not commit installation-specific configuration, passwords or Pushover credentials
- keep changes focused and easy to review

## Software Changes

Software changes should:

- retain the root `VERSION` file as the authoritative version source
- preserve existing configuration and user data during supported upgrades
- avoid silently changing alarm thresholds or sensor logic
- include or update automated tests where appropriate
- pass the release-test suite before being considered ready for release

Run:

`./software/run_release_tests.sh`

from the repository root where applicable.

## Hardware Changes

Any change affecting:

- GPIO allocation
- power distribution
- sensor interfaces
- transistor circuits
- terminal-block allocation
- LEDs or buzzer
- RTC connections

should also update the relevant documentation in:

- `docs/wiring.md`
- `docs/bill-of-materials.md`
- `docs/commissioning.md`

Hardware changes should not be presented as final construction instructions until they have been physically assembled and tested.

## Documentation Changes

Documentation should describe the current confirmed design.

Working ideas, untested layouts and proposed changes should not replace verified instructions until they have been tested.

Where possible, use version-neutral wording such as **latest release** or **current release** rather than embedding a specific version number into general procedures.

## Reporting Problems

Use the repository's **Bug report** issue template for reproducible problems.

Useful information includes:

- installed software version
- steps to reproduce the problem
- relevant dashboard state
- hardware self-test result
- relevant service-log messages
- details of any recent wiring or hardware changes

The installed software version can be checked with:

`cat /opt/hydro-monitor/VERSION`

## Private Information

Never include:

- passwords
- Pushover User Keys
- Pushover Application API Tokens
- private network credentials
- other installation-specific secrets

in commits, issues, screenshots or logs posted publicly.
