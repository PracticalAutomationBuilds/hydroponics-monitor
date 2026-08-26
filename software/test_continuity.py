#!/usr/bin/env python3
"""Continuity assertions for fixed Hydro Monitor project identity and behaviour."""

from __future__ import annotations

import json
from pathlib import Path

from hydro_version import VERSION

ROOT = Path(__file__).resolve().parent
EXPECTED_USER = "hydroponics"
EXPECTED_HOSTNAME = "hydro-monitor"
EXPECTED_SSH = "ssh hydroponics@hydro-monitor.local"
EXPECTED_DASHBOARD = "http://hydro-monitor.local:8080/"


def read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


# Release identity is single-source and Semantic Versioned.
assert VERSION == read("VERSION").strip()
assert "from hydro_version import VERSION" in read("hydro_monitor.py")
assert "from hydro_version import VERSION" in read("hydro_dashboard.py")

# Fixed Raspberry Pi identity and network conventions.
installer = read("install.sh")
assert f'EXPECTED_USER="{EXPECTED_USER}"' in installer
assert f'EXPECTED_HOSTNAME="{EXPECTED_HOSTNAME}"' in installer
assert EXPECTED_SSH in installer
assert EXPECTED_DASHBOARD in installer
assert "systemctl enable --now avahi-daemon.service" in installer

readme = read("README.md")
for value in (EXPECTED_USER, EXPECTED_HOSTNAME, EXPECTED_SSH, EXPECTED_DASHBOARD):
    assert value in readme, value

# Service paths and privilege boundaries must remain stable.
for unit_name in ("hydro-monitor.service", "hydro-dashboard.service"):
    unit = read(unit_name)
    assert "User=REPLACE_WITH_YOUR_USERNAME" in unit
    assert "WorkingDirectory=/opt/hydro-monitor" in unit
    assert "/opt/hydro-monitor/config.json" in unit

monitor_unit = read("hydro-monitor.service")
assert "RestartPreventExitStatus=2" in monitor_unit
assert "SupplementaryGroups=gpio hydro-monitor-secrets" in monitor_unit

dashboard_unit = read("hydro-dashboard.service")
assert "Requires=hydro-monitor.service" in dashboard_unit
assert "After=network-online.target hydro-monitor.service" in dashboard_unit

# Stable configuration source of truth.
config = json.loads(read("config.json"))
assert config["gpio"] == {
    "return_sensor": 24,
    "override_switch": 18,
    "buzzer": 12,
    "override_led": 20,
    "alarm_led": 26,
    "status_led": 21,
    "low_level_sensor": 17,
}
assert config["ambient"]["gpio"] == 22
assert config["rtc"]["sda_gpio"] == 2
assert config["rtc"]["scl_gpio"] == 3
assert config["return_sensor"] == {
    "wet_level": 0,
    "dry_delay_seconds": 15,
    "startup_grace_seconds": 60,
}
assert config["temperature"]["warning_c"] == 24.0
assert config["temperature"]["critical_c"] == 25.0
assert config["temperature"]["clear_c"] == 23.5
assert config["temperature"]["sensor_failures_before_alarm"] == 3
assert config["temperature"]["grow_pipe_enabled"] is True
assert config["temperature"]["grow_pipe_alarm_enabled"] is False
assert config["dashboard"] == {
    "enabled": True,
    "bind_address": "0.0.0.0",
    "port": 8080,
    "current_status_path": "/var/lib/hydro-monitor/current_status.json",
    "max_points_per_series": 1200,
    "status_stale_after_seconds": 15,
    "default_history_hours": 24,
    "system_info_refresh_seconds": 30,
}
assert config["logging"] == {
    "csv_path": "/var/log/hydro-monitor/readings.csv",
    "event_log_path": "/var/log/hydro-monitor/events.log",
    "csv_interval_seconds": 60,
}
assert config["rtc"]["model"] == "DS3231"
assert config["rtc"]["i2c_address"] == "0x68"
assert config["low_level_sensor"]["external_pullup_ohms"] == 10000
assert config["low_level_sensor"]["normal_contact_closed_to_ground"] is True
assert config["low_level_sensor"]["fail_safe_open_circuit_is_low"] is True
assert config["notifications"]["provider"] == "pushover"
assert config["notifications"]["enabled"] is False
assert config["notifications"]["secrets_path"] == "/etc/hydro-monitor/pushover.json"

# Established persistent paths and service names must not drift silently.
for required in (
    "/opt/hydro-monitor",
    "/var/lib/hydro-monitor/current_status.json",
    "/var/log/hydro-monitor/readings.csv",
    "/var/log/hydro-monitor/events.log",
    "/etc/hydro-monitor/pushover.json",
    "hydro-monitor.service",
    "hydro-dashboard.service",
):
    assert required in readme or required in installer or required in read("config.json"), required

# Known identity drift remains forbidden in current-facing source.
forbidden = (
    "strawberrypi",
    "peter@",
    "http://<Pi-hostname>.local:8080/",
    "http://<hostname>.local:8080/",
    ":5000",
)
scan_names = (
    "README.md",
    "install.sh",
    "config.json",
    "hydro_monitor.py",
    "hydro_dashboard.py",
    "dashboard.html",
    "dashboard.js",
)
for name in scan_names:
    text = read(name)
    for token in forbidden:
        assert token not in text, f"{token!r} found in {name}"

monitor = read("hydro_monitor.py")
for required in (
    "recover_csv_tail_after_power_loss",
    "discard_invalid_current_status",
    "os.fsync(handle.fileno())",
    "powerloss-recovery",
):
    assert required in monitor, required

print(f"Hydro Monitor {VERSION} continuity checks passed.")
