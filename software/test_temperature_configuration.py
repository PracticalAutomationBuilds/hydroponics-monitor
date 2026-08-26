#!/usr/bin/env python3
"""Offline tests for the DS18B20 role-assignment utility."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

project = Path(__file__).resolve().parent
script = project / "configure_temperature_probes.py"

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    w1_root = root / "w1"
    w1_root.mkdir()
    for sensor_id, value in (("28-res", 18000), ("28-pipe", 19500)):
        device = w1_root / sensor_id
        device.mkdir()
        (device / "w1_slave").write_text(
            f"aa bb cc YES\naa bb t={value}\n", encoding="utf-8"
        )

    config_path = root / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "temperature": {
                    "reservoir_sensor_id": "",
                    "grow_pipe_enabled": True,
                    "grow_pipe_sensor_id": "",
                    "grow_pipe_alarm_enabled": False,
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_path),
            "--w1-root",
            str(w1_root),
            "--reservoir",
            "28-res",
            "--grow-pipe",
            "28-pipe",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    updated = json.loads(config_path.read_text(encoding="utf-8"))
    temp_cfg = updated["temperature"]
    assert temp_cfg["reservoir_sensor_id"] == "28-res"
    assert temp_cfg["grow_pipe_sensor_id"] == "28-pipe"
    assert temp_cfg["grow_pipe_enabled"] is True
    assert temp_cfg["grow_pipe_alarm_enabled"] is False
    assert len(list(root.glob("config.json.before-probe-setup-*.bak"))) == 1

    missing = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_path),
            "--w1-root",
            str(w1_root),
            "--reservoir",
            "",
            "--grow-pipe",
            "28-pipe",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert missing.returncode != 0
    assert "reservoir probe ID must be assigned" in missing.stderr

    duplicate = subprocess.run(
        [
            sys.executable,
            str(script),
            "--config",
            str(config_path),
            "--w1-root",
            str(w1_root),
            "--reservoir",
            "28-res",
            "--grow-pipe",
            "28-res",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    assert duplicate.returncode != 0
    assert "cannot use the same" in duplicate.stderr

print("Temperature-probe configuration tests passed.")
