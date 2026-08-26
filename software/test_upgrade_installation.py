#!/usr/bin/env python3
"""Offline tests for upgrade preservation and release-version handling."""

from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

from hydro_version import VERSION
from merge_config import AUTHORITATIVE_GPIO, build_merged_config

ROOT = Path(__file__).resolve().parent

with tempfile.TemporaryDirectory() as temp_dir:
    temp = Path(temp_dir)
    defaults_path = ROOT / "config.json"
    existing_path = temp / "existing.json"
    output_path = temp / "merged.json"

    existing = json.loads(defaults_path.read_text(encoding="utf-8"))
    existing["temperature"]["reservoir_sensor_id"] = "28-000000000001"
    existing["temperature"]["grow_pipe_sensor_id"] = "28-000000000002"
    existing["temperature"]["warning_c"] = 23.8
    existing["notifications"]["enabled"] = True
    existing["dashboard"]["default_history_hours"] = 48
    existing["gpio"] = {
        "return_sensor": 99,
        "override_switch": 98,
        "buzzer": 97,
        "override_led": 96,
        "alarm_led": 95,
        "status_led": 94,
        "low_level_sensor": 93,
    }
    existing["ambient"]["gpio"] = 91
    existing["rtc"]["sda_gpio"] = 90
    existing["rtc"]["scl_gpio"] = 89
    existing["user_note_for_future_compatibility"] = "preserve me"
    existing_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")

    merged = build_merged_config(defaults_path, existing_path)

    # User-specific configuration survives the upgrade.
    assert merged["temperature"]["reservoir_sensor_id"] == "28-000000000001"
    assert merged["temperature"]["grow_pipe_sensor_id"] == "28-000000000002"
    assert merged["temperature"]["warning_c"] == 23.8
    assert merged["notifications"]["enabled"] is True
    assert merged["dashboard"]["default_history_hours"] == 48
    assert merged["user_note_for_future_compatibility"] == "preserve me"

    # Hardware-critical permanent-board assignments remain authoritative.
    assert merged["gpio"] == AUTHORITATIVE_GPIO
    assert merged["ambient"]["gpio"] == 22
    assert merged["rtc"]["sda_gpio"] == 2
    assert merged["rtc"]["scl_gpio"] == 3

    # Exercise the same command-line path used by install.sh.
    subprocess.run(
        [
            "python3",
            str(ROOT / "merge_config.py"),
            "--defaults",
            str(defaults_path),
            "--existing",
            str(existing_path),
            "--output",
            str(output_path),
        ],
        check=True,
    )
    cli_merged = json.loads(output_path.read_text(encoding="utf-8"))
    assert cli_merged == merged

    # A malformed existing config must fail without overwriting a pre-existing output.
    malformed = temp / "malformed.json"
    malformed.write_text('{"temperature": ', encoding="utf-8")
    sentinel = temp / "sentinel.json"
    sentinel.write_text('{"sentinel": true}\n', encoding="utf-8")
    failed = subprocess.run(
        [
            "python3",
            str(ROOT / "merge_config.py"),
            "--defaults",
            str(defaults_path),
            "--existing",
            str(malformed),
            "--output",
            str(sentinel),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert failed.returncode != 0
    assert json.loads(sentinel.read_text(encoding="utf-8")) == {"sentinel": True}

installer = (ROOT / "install.sh").read_text(encoding="utf-8")
assert 'if [[ -f "${INSTALL_DIR}/VERSION" ]]' in installer
assert 'elif [[ -f "${INSTALL_DIR}/hydro_monitor.py" ]]' in installer
assert 'INSTALLED_VERSION="${INSTALLED_VERSION:-legacy/unknown}"' in installer
assert 'Existing configuration, history, logs and Pushover secrets will be preserved.' in installer
assert 'rm -rf "${INSTALL_DIR}/venv"' in installer
assert 'install -m 0644 "${PROJECT_DIR}/VERSION" "${INSTALL_DIR}/VERSION"' in installer

print(f"Hydro Monitor {VERSION} upgrade-preservation tests passed.")
