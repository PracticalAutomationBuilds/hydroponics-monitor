#!/usr/bin/env python3
import csv
import importlib.util
import tempfile
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

module_path = Path(__file__).with_name("hydro_dashboard.py")
spec = importlib.util.spec_from_file_location("hydro_dashboard", module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    csv_path = root / "readings.csv"
    now = datetime.now(timezone.utc)
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "timestamp", "water_temp_c", "reservoir_temp_c",
            "grow_pipe_temp_c", "grow_pipe_minus_reservoir_c",
            "reservoir_temp_sensor_fault", "grow_pipe_temp_sensor_fault",
            "ambient_temp_c", "ambient_rh_percent", "air_minus_water_c", "return_wet",
            "override_active", "active_alarm", "system_status",
            "pi_cpu_temp_c"
        ])
        writer.writeheader()
        for index in range(100):
            writer.writerow({
                "timestamp": (now - timedelta(minutes=99-index)).isoformat(),
                "water_temp_c": 10 + index / 100,
                "reservoir_temp_c": 10 + index / 100,
                "grow_pipe_temp_c": 11 + index / 100,
                "grow_pipe_minus_reservoir_c": 1,
                "reservoir_temp_sensor_fault": 0,
                "grow_pipe_temp_sensor_fault": 0,
                "ambient_temp_c": 12 + index / 100,
                "ambient_rh_percent": 70,
                "air_minus_water_c": 2,
                "return_wet": 1,
                "override_active": 0,
                "active_alarm": "",
                "system_status": "HEALTHY",
                "pi_cpu_temp_c": 40,
            })
    rows, total = module.read_history(
        csv_path,
        now - timedelta(hours=3),
        now + timedelta(minutes=1),
        20,
    )
    assert total == 100
    assert len(rows) <= 20
    assert rows[0]["water_temp_c"] is not None
    assert rows[0]["reservoir_temp_c"] is not None
    assert rows[0]["grow_pipe_temp_c"] is not None
    assert rows[0]["grow_pipe_minus_reservoir_c"] == 1.0

    log_path = root / "events.log"
    log_path.write_text(
        "2026-07-12 10:00:00,000 INFO Hydro monitor started\n"
        "2026-07-12 10:05:00,000 ERROR Alarm active: FLOW_LOSS\n",
        encoding="utf-8",
    )
    events = module.read_events(log_path, "flow", "ALL", 10)
    assert len(events) == 1
    assert events[0]["level"] == "ERROR"

print("History parsing and dashboard tests passed.")


system_info = module.build_system_info()
assert "hostname" in system_info
assert "memory" in system_info
assert "disk" in system_info
assert "wifi" in system_info
assert "dashboard_version" in system_info
print("System information tests passed.")


config_sample = {
    "gpio": {
        "return_sensor": 17,
        "override_switch": 27,
        "buzzer": 18,
        "override_led": 22,
        "alarm_led": 23,
        "status_led": 25,
        "low_level_sensor": 5,
    },
    "return_sensor": {
        "dry_delay_seconds": 15,
        "startup_grace_seconds": 60,
    },
    "low_level_sensor": {
        "enabled": True,
        "product": "Jaycar SF0920 float switch",
        "normal_contact_closed_to_ground": True,
        "external_pullup_ohms": 10000,
        "alarm_delay_seconds": 30,
        "startup_grace_seconds": 30,
        "fail_safe_open_circuit_is_low": True,
    },
    "temperature": {
        "reservoir_sensor_id": "28-reservoir",
        "grow_pipe_enabled": True,
        "grow_pipe_sensor_id": "28-growpipe",
        "grow_pipe_alarm_enabled": False,
        "warning_c": 24.0,
        "critical_c": 25.0,
        "clear_c": 23.5,
        "read_interval_seconds": 2,
        "sensor_failures_before_alarm": 3,
    },
    "ambient": {
        "gpio": 24,
        "read_interval_seconds": 10,
        "max_stale_seconds": 300,
    },
    "logging": {
        "csv_path": "/tmp/readings.csv",
        "event_log_path": "/tmp/events.log",
        "csv_interval_seconds": 60,
    },
    "dashboard": {
        "bind_address": "0.0.0.0",
        "port": 8080,
        "current_status_path": "/tmp/current.json",
        "max_points_per_series": 1200,
        "status_stale_after_seconds": 15,
        "default_history_hours": 24,
        "system_info_refresh_seconds": 30,
    },
    "notifications": {
        "enabled": False,
        "provider": "pushover",
        "secrets_path": "/etc/hydro-monitor/pushover.json",
        "title_prefix": "Strawberry Hydroponics",
        "send_clear_messages": True,
        "active_reminders_enabled": True,
        "reminder_minutes": {"FLOW_LOSS": 30},
        "events": {"FLOW_LOSS_ACTIVE": {"priority": 1, "sound": "siren"}},
    },
    "rtc": {
        "enabled": True,
        "model": "DS3231",
        "module": "Jaycar XC9044",
        "i2c_bus": 1,
        "i2c_address": "0x68",
        "sda_gpio": 2,
        "scl_gpio": 3,
        "device_tree_overlay": "i2c-rtc,ds3231",
        "device": "/dev/rtc0",
    },
}
summary = module.build_configuration_summary(config_sample)
assert summary["alarm_thresholds"]["reservoir_warning_c"] == 24.0
assert summary["alarm_thresholds"]["grow_pipe_alarm_enabled"] is False
assert summary["sampling_and_logging"]["reservoir_sensor_id"] == "28-reservoir"
assert summary["sampling_and_logging"]["grow_pipe_sensor_id"] == "28-growpipe"
assert summary["gpio"]["Green status LED"] == 25
assert summary["dashboard"]["read_only"] is True

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    cfg = root / "config.json"
    readings = root / "readings.csv"
    events = root / "events.log"
    cfg.write_text('{"test": true}\\n', encoding="utf-8")
    readings.write_text("timestamp,value\\n2026-01-01,1\\n", encoding="utf-8")
    events.write_text("test event\\n", encoding="utf-8")
    body, name = module.create_backup_archive(cfg, readings, events)
    assert name.startswith("hydro-monitor-backup_")
    archive_path = root / "backup.zip"
    archive_path.write_bytes(body)
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = set(archive.namelist())
        assert "config.json" in names
        assert "readings.csv" in names
        assert "events.log" in names
        assert "backup_manifest.json" in names

print("Configuration and backup tests passed.")


rtc_summary = module.build_configuration_summary(config_sample)
assert rtc_summary["gpio"]["RTC I2C SDA"] == 2
assert rtc_summary["gpio"]["RTC I2C SCL"] == 3
assert rtc_summary["rtc"]["model"] == "DS3231"
assert rtc_summary["rtc"]["i2c_address"] == "0x68"

rtc_info = module.read_rtc_info()
assert "available" in rtc_info
assert rtc_info["expected_model"] == "DS3231"
assert rtc_info["expected_i2c_address"] == "0x68"

print("RTC configuration tests passed.")


v7_summary = module.build_configuration_summary(config_sample)
assert v7_summary["gpio"]["Reservoir low-level float switch"] == 5
assert v7_summary["low_level_sensor"]["external_pullup_ohms"] == 10000
assert v7_summary["alarm_thresholds"]["low_water_alarm_delay_seconds"] == 30

print("Dashboard configuration tests passed.")


v8_summary = module.build_configuration_summary(config_sample)
assert v8_summary["software"]["monitor_version"] == module.VERSION
assert v8_summary["notifications"]["provider"] == "pushover"
assert v8_summary["notifications"]["credentials_in_dashboard_or_backup"] is False

print("Notification dashboard tests passed.")


# Legacy CSV rows are preserved while adding the current probe columns.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    csv_path = root / "readings.csv"
    csv_path.write_text(
        "timestamp,water_temp_c,ambient_temp_c\n"
        "2026-01-01T00:00:00+00:00,18.0,20.0\n",
        encoding="utf-8",
    )
    # Import monitor with hardware stubs to exercise its schema migration.
    import sys, types
    gpiozero = types.ModuleType("gpiozero")
    gpiozero.Button = type("Button", (), {})
    gpiozero.DigitalInputDevice = type("DigitalInputDevice", (), {})
    gpiozero.DigitalOutputDevice = type("DigitalOutputDevice", (), {})
    sys.modules["gpiozero"] = gpiozero
    sys.modules.setdefault("board", types.ModuleType("board"))
    sys.modules.setdefault("adafruit_dht", types.ModuleType("adafruit_dht"))
    monitor_path = Path(__file__).with_name("hydro_monitor.py")
    monitor_spec = importlib.util.spec_from_file_location("hydro_monitor_v91_csv", monitor_path)
    monitor = importlib.util.module_from_spec(monitor_spec)
    sys.modules[monitor_spec.name] = monitor
    monitor_spec.loader.exec_module(monitor)
    row = {
        "timestamp": "2026-01-01T00:01:00+00:00",
        "water_temp_c": "18.1",
        "reservoir_temp_c": "18.1",
        "grow_pipe_temp_c": "19.0",
        "grow_pipe_minus_reservoir_c": "0.9",
        "ambient_temp_c": "20.1",
    }
    monitor.append_csv(csv_path, row)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        migrated = list(csv.DictReader(handle))
    assert len(migrated) == 2
    assert migrated[0]["water_temp_c"] == "18.0"
    assert migrated[0]["reservoir_temp_c"] == "18.0"
    assert migrated[0]["grow_pipe_temp_c"] == ""
    assert migrated[1]["grow_pipe_temp_c"] == "19.0"
    backups = list(root.glob("readings.pre-schema-upgrade-*.csv"))
    assert len(backups) == 1

print("Legacy CSV migration test passed.")
