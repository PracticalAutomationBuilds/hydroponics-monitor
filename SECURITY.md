# Security Policy

## Supported Versions

Security fixes are applied to the **latest release** of the Hydroponics Monitor.

Pre-release and older development builds should not be assumed to receive separate security updates.

## Reporting a Security Issue

Do not publish passwords, Pushover credentials, network credentials or other private information in a public GitHub issue.

If a suspected security problem can be described safely without exposing sensitive information, open an issue with enough detail to identify the affected component and software version.

If sensitive information would be required to demonstrate the problem, do **not** post that information publicly. Provide only a minimal description initially so that an appropriate private reporting method can be arranged.

The installed Hydroponics Monitor version can be checked with:

`cat /opt/hydro-monitor/VERSION`

## Credentials

The repository must never contain real:

- Pushover User Keys
- Pushover Application API Tokens
- passwords
- Wi-Fi credentials
- SSH private keys
- other installation-specific secrets

The supplied `pushover_secrets.example.json` contains empty placeholder values only.

## Local Network Exposure

The Hydroponics Monitor dashboard is intended for use on a trusted local network.

It should not be exposed directly to the public Internet without additional access controls and appropriate network-security measures.

Pushover provides the optional remote-notification path and does not require the local dashboard to be Internet-accessible.
