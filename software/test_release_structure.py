#!/usr/bin/env python3
"""Static release checks for Hydro Monitor package consistency."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hydro_version import VERSION, read_version

ROOT = Path(__file__).resolve().parent
assert VERSION == (ROOT / "VERSION").read_text(encoding="utf-8").strip()
assert read_version(ROOT) == VERSION
assert re.fullmatch(
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?",
    VERSION,
)

required_files = {
    "README.md",
    "RELEASE-NOTES.md",
    "VERSION",
    "MANIFEST.txt",
    "SHA256SUMS",
    "hydro_version.py",
    "hydro_monitor.py",
    "hydro_dashboard.py",
    "dashboard.html",
    "dashboard.css",
    "dashboard.js",
    "config.json",
    "install.sh",
    "uninstall.sh",
    "merge_config.py",
    "configure_rtc.sh",
    "verify_rtc.sh",
    "configure_pushover.py",
    "configure_temperature_probes.py",
    "pushover_secrets.example.json",
    "requirements.txt",
    "hydro-monitor.service",
    "hydro-dashboard.service",
    "run_release_tests.sh",
    "test_logic.py",
    "test_dashboard.py",
    "test_notifications.py",
    "test_temperature_configuration.py",
    "test_power_loss_recovery.py",
    "test_upgrade_installation.py",
    "test_release_structure.py",
    "test_continuity.py",
}
missing = sorted(name for name in required_files if not (ROOT / name).is_file())
assert not missing, f"Missing required files: {missing}"

config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
assert config["dashboard"]["bind_address"] == "0.0.0.0"
assert config["dashboard"]["port"] == 8080
assert config["temperature"]["grow_pipe_alarm_enabled"] is False
assert config["low_level_sensor"]["external_pullup_ohms"] == 10000
assert config["return_sensor"]["wet_level"] == 0
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

monitor = (ROOT / "hydro_monitor.py").read_text(encoding="utf-8")
dashboard = (ROOT / "hydro_dashboard.py").read_text(encoding="utf-8")
for text, name in ((monitor, "hydro_monitor.py"), (dashboard, "hydro_dashboard.py")):
    assert "from hydro_version import VERSION" in text, name
    assert not re.search(r'^VERSION\s*=\s*["\']', text, flags=re.MULTILINE), name

assert "grow_pipe_minus_reservoir_c" in monitor
assert "pull_up=None" in monitor
assert "active_state=True" in monitor
assert "temperature.reservoir_sensor_id is not assigned" in monitor
assert "temperature.grow_pipe_sensor_id is not assigned" in monitor
assert "recover_csv_tail_after_power_loss" in monitor
assert "os.fsync(handle.fileno())" in monitor
assert "discard_invalid_current_status" in monitor
assert "pre-schema-upgrade" in monitor

html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
js = (ROOT / "dashboard.js").read_text(encoding="utf-8")
assert "<title>Strawberry Hydroponics Monitor</title>" in html
for element_id in ("growPipeTemp", "growPipeDelta", "growPipeProbe"):
    assert f'id="{element_id}"' in html
    assert f'$("{element_id}")' in js

installer = (ROOT / "install.sh").read_text(encoding="utf-8")
for required in (
    'EXPECTED_USER="hydroponics"',
    'EXPECTED_HOSTNAME="hydro-monitor"',
    'VERSION_FILE="${PROJECT_DIR}/VERSION"',
    'Mode: upgrade',
    'Existing configuration, history, logs and Pushover secrets will be preserved.',
    'install -m 0644 "${PROJECT_DIR}/VERSION" "${INSTALL_DIR}/VERSION"',
    'install -m 0644 "${PROJECT_DIR}/hydro_version.py" "${INSTALL_DIR}/hydro_version.py"',
    'python3 "${PROJECT_DIR}/merge_config.py"',
    'config.json.pre-${RELEASE_VERSION}-${STAMP}',
    'systemctl disable --now hydro-dashboard.service hydro-monitor.service',
    'systemctl enable --now hydro-monitor.service hydro-dashboard.service',
):
    assert required in installer, required

uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")
for required in (
    "--purge",
    "Type PURGE to continue",
    'rm -rf "${INSTALL_DIR}" "${LOG_DIR}" "${STATE_DIR}" "${SECRETS_DIR}"',
    "Software removed. Preserved data remains in:",
    "shared/system facilities were deliberately left unchanged",
):
    assert required in uninstaller, required
assert "apt-get remove" not in uninstaller
assert "apt-get purge" not in uninstaller
assert "raspi-config" not in uninstaller

monitor_unit = (ROOT / "hydro-monitor.service").read_text(encoding="utf-8")
assert "RestartPreventExitStatus=2" in monitor_unit
assert "WorkingDirectory=/opt/hydro-monitor" in monitor_unit

dashboard_unit = (ROOT / "hydro-dashboard.service").read_text(encoding="utf-8")
assert "Requires=hydro-monitor.service" in dashboard_unit
assert "v9." not in dashboard_unit

# Public RC runtime/package-facing files must not carry the internal development numbering.
current_facing = (
    "README.md",
    "RELEASE-NOTES.md",
    "hydro_monitor.py",
    "hydro_dashboard.py",
    "hydro_version.py",
    "configure_pushover.py",
    "configure_temperature_probes.py",
    "install.sh",
    "uninstall.sh",
    "merge_config.py",
    "dashboard.html",
    "hydro-monitor.service",
    "hydro-dashboard.service",
)
for name in current_facing:
    text = (ROOT / name).read_text(encoding="utf-8")
    assert "9.1.2" not in text, name
    assert "9.1.3" not in text, name

print(f"Hydro Monitor {VERSION} release-structure checks passed.")
