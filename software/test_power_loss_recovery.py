#!/usr/bin/env python3
"""Offline power-loss resilience tests for Hydro Monitor."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

# Hardware stubs allow importing the monitor on a non-Raspberry-Pi test host.
gpiozero = types.ModuleType("gpiozero")
gpiozero.Button = type("Button", (), {})
gpiozero.DigitalInputDevice = type("DigitalInputDevice", (), {})
gpiozero.DigitalOutputDevice = type("DigitalOutputDevice", (), {})
sys.modules["gpiozero"] = gpiozero
sys.modules.setdefault("board", types.ModuleType("board"))
sys.modules.setdefault("adafruit_dht", types.ModuleType("adafruit_dht"))

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("hydro_monitor_v913_powerloss", ROOT / "hydro_monitor.py")
monitor = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = monitor
spec.loader.exec_module(monitor)


def backup_files(root: Path) -> list[Path]:
    return sorted(root.glob("readings.powerloss-recovery-*.csv"))


# A complete file is not altered.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    path = root / "readings.csv"
    original = (
        "timestamp,water_temp_c\r\n"
        "2026-08-25T12:00:00+10:00,1\r\n"
    )
    path.write_text(original, encoding="utf-8", newline="")
    assert monitor.recover_csv_tail_after_power_loss(path) is False
    assert path.read_text(encoding="utf-8", newline="") == original
    assert backup_files(root) == []


# An interrupted final append without its newline is backed up and removed only at the tail.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    path = root / "readings.csv"
    path.write_bytes(
        b"timestamp,water_temp_c\r\n"
        b"2026-08-25T12:00:00+10:00,1\r\n"
        b"2026-08-25T12:01:00+10:00,par"
    )
    original = path.read_bytes()
    assert monitor.recover_csv_tail_after_power_loss(path) is True
    assert path.read_bytes() == (
        b"timestamp,water_temp_c\r\n"
        b"2026-08-25T12:00:00+10:00,1\r\n"
    )
    backups = backup_files(root)
    assert len(backups) == 1
    assert backups[0].read_bytes() == original


# A malformed final row that did reach a newline is also treated as an interrupted tail record.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    path = root / "readings.csv"
    path.write_bytes(
        b"timestamp,water_temp_c,return_wet\n"
        b"2026-08-25T12:00:00+10:00,1,0\n"
        b"2026-08-25T12:01:00+10:00,2\n"
    )
    assert monitor.recover_csv_tail_after_power_loss(path) is True
    assert path.read_bytes().endswith(b"2026-08-25T12:00:00+10:00,1,0\n")
    assert b"12:01:00" not in path.read_bytes()


# Header damage is never guessed at or auto-repaired.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    path = root / "readings.csv"
    original = b"time,water_temp_c\n2026-08-25T12:00:00+10:00,1\n"
    path.write_bytes(original)
    try:
        monitor.recover_csv_tail_after_power_loss(path)
    except ValueError as exc:
        assert "timestamp" in str(exc)
    else:
        raise AssertionError("Corrupt/mismatched readings header was not rejected")
    assert path.read_bytes() == original
    assert backup_files(root) == []


# Disposable current-status state is retained when valid and removed when invalid.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    status = root / "current_status.json"
    status.write_text(json.dumps({"updated_at": "2026-08-25T12:00:00+10:00"}) + "\n", encoding="utf-8")
    assert monitor.discard_invalid_current_status(status) is False
    assert status.exists()

    status.write_text('{"updated_at": ', encoding="utf-8")
    assert monitor.discard_invalid_current_status(status) is True
    assert not status.exists()


# Every CSV append explicitly flushes through the OS cache with fsync().
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    path = root / "readings.csv"
    calls: list[int] = []
    real_fsync = monitor.os.fsync
    monitor.os.fsync = lambda descriptor: calls.append(descriptor)
    try:
        monitor.append_csv(
            path,
            {
                "timestamp": "2026-08-25T12:00:00+10:00",
                "water_temp_c": "1",
            },
        )
    finally:
        monitor.os.fsync = real_fsync
    assert calls, "append_csv did not call os.fsync"


# Atomic live-status writes fsync the file and leave valid JSON behind.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    status = root / "current_status.json"
    monitor.write_json_atomic(status, {"ok": True})
    assert json.loads(status.read_text(encoding="utf-8")) == {"ok": True}
    assert not status.with_suffix(status.suffix + ".tmp").exists()

print("Hydro Monitor power-loss resilience tests passed.")
