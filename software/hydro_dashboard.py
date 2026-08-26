#!/usr/bin/env python3
"""Read-only local web dashboard for the hydroponic monitor, including system information."""

from __future__ import annotations

import argparse
import csv
import io
import json
import mimetypes
import os
import platform
import re
import socket
import subprocess
import shutil
import sys
import time
import zipfile
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import parse_qs, unquote, urlparse

from hydro_version import VERSION
INSTALL_DIR = Path(__file__).resolve().parent
SAFE_ASSETS = {
    "/": "dashboard.html",
    "/index.html": "dashboard.html",
    "/dashboard.css": "dashboard.css",
    "/dashboard.js": "dashboard.js",
}
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
    r"(?P<level>[A-Z]+) (?P<message>.*)$"
)


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def parse_iso(value: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def parse_range(query: dict[str, list[str]], default_hours: float) -> tuple[datetime, datetime]:
    now = datetime.now().astimezone()
    start = parse_iso(query.get("start", [""])[0])
    end = parse_iso(query.get("end", [""])[0])
    if end is None:
        end = now
    if start is None:
        hours_raw = query.get("hours", [str(default_hours)])[0]
        try:
            hours = min(max(float(hours_raw), 0.25), 24 * 366 * 5)
        except ValueError:
            hours = default_hours
        start = end - timedelta(hours=hours)
    if start > end:
        start, end = end, start
    return start, end


def float_or_none(value: str) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_none(value: str) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def evenly_sample(rows: list[dict[str, Any]], maximum: int) -> list[dict[str, Any]]:
    if maximum <= 0 or len(rows) <= maximum:
        return rows
    if maximum == 1:
        return [rows[-1]]
    step = (len(rows) - 1) / (maximum - 1)
    indices = sorted({round(index * step) for index in range(maximum)})
    return [rows[index] for index in indices]


def read_history(
    csv_path: Path,
    start: datetime,
    end: datetime,
    maximum: int,
) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    if not csv_path.exists():
        return rows, 0

    with csv_path.open("r", newline="", encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            timestamp = parse_iso(row.get("timestamp", ""))
            if timestamp is None or timestamp < start or timestamp > end:
                continue
            rows.append(
                {
                    "timestamp": timestamp.isoformat(timespec="seconds"),
                    "water_temp_c": float_or_none(row.get("water_temp_c", "")),
                    "reservoir_temp_c": float_or_none(
                        row.get("reservoir_temp_c", "")
                        or row.get("water_temp_c", "")
                    ),
                    "grow_pipe_temp_c": float_or_none(
                        row.get("grow_pipe_temp_c", "")
                    ),
                    "grow_pipe_minus_reservoir_c": float_or_none(
                        row.get("grow_pipe_minus_reservoir_c", "")
                    ),
                    "reservoir_temp_sensor_fault": int_or_none(
                        row.get("reservoir_temp_sensor_fault", "")
                    ),
                    "grow_pipe_temp_sensor_fault": int_or_none(
                        row.get("grow_pipe_temp_sensor_fault", "")
                    ),
                    "ambient_temp_c": float_or_none(row.get("ambient_temp_c", "")),
                    "ambient_rh_percent": float_or_none(
                        row.get("ambient_rh_percent", "")
                    ),
                    "air_minus_water_c": float_or_none(
                        row.get("air_minus_water_c", "")
                    ),
                    "return_wet": int_or_none(row.get("return_wet", "")),
                    "reservoir_level_ok": int_or_none(
                        row.get("reservoir_level_ok", "")
                    ),
                    "low_level_alarm": int_or_none(
                        row.get("low_level_alarm", "")
                    ),
                    "override_active": int_or_none(
                        row.get("override_active", "")
                    ),
                    "active_alarm": row.get("active_alarm", ""),
                    "system_status": row.get("system_status", ""),
                    "pi_cpu_temp_c": float_or_none(
                        row.get("pi_cpu_temp_c", "")
                    ),
                }
            )

    total = len(rows)
    return evenly_sample(rows, maximum), total


def read_events(
    log_path: Path,
    query_text: str,
    level: str,
    limit: int,
) -> list[dict[str, str]]:
    if not log_path.exists():
        return []

    query_lower = query_text.strip().lower()
    level = level.strip().upper()
    matches: list[dict[str, str]] = []

    with log_path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            match = LOG_PATTERN.match(line)
            if match:
                item = match.groupdict()
            else:
                item = {"timestamp": "", "level": "", "message": line}

            if level and level != "ALL" and item["level"] != level:
                continue
            searchable = f'{item["timestamp"]} {item["level"]} {item["message"]}'.lower()
            if query_lower and query_lower not in searchable:
                continue
            matches.append(item)
            if len(matches) > limit:
                matches.pop(0)

    matches.reverse()
    return matches


def read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None


def read_cpu_percent(sample_seconds: float = 0.15) -> Optional[float]:
    """Estimate total CPU utilisation from /proc/stat without extra packages."""
    def snapshot() -> Optional[tuple[int, int]]:
        line = read_text(Path("/proc/stat"))
        if not line:
            return None
        first = line.splitlines()[0].split()
        if not first or first[0] != "cpu":
            return None
        try:
            values = [int(value) for value in first[1:]]
        except ValueError:
            return None
        if len(values) < 4:
            return None
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        total = sum(values)
        return idle, total

    before = snapshot()
    if before is None:
        return None
    time.sleep(sample_seconds)
    after = snapshot()
    if after is None:
        return None

    idle_delta = after[0] - before[0]
    total_delta = after[1] - before[1]
    if total_delta <= 0:
        return None
    return round(100.0 * (1.0 - idle_delta / total_delta), 1)


def read_memory_info() -> dict[str, Optional[float]]:
    text = read_text(Path("/proc/meminfo"))
    if not text:
        return {
            "total_mb": None,
            "available_mb": None,
            "used_mb": None,
            "used_percent": None,
        }

    values: dict[str, int] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, raw = line.split(":", 1)
        parts = raw.strip().split()
        if not parts:
            continue
        try:
            values[key] = int(parts[0])  # kB
        except ValueError:
            continue

    total_kb = values.get("MemTotal")
    available_kb = values.get("MemAvailable")
    if total_kb is None or available_kb is None or total_kb <= 0:
        return {
            "total_mb": None,
            "available_mb": None,
            "used_mb": None,
            "used_percent": None,
        }

    used_kb = total_kb - available_kb
    return {
        "total_mb": round(total_kb / 1024, 1),
        "available_mb": round(available_kb / 1024, 1),
        "used_mb": round(used_kb / 1024, 1),
        "used_percent": round(100.0 * used_kb / total_kb, 1),
    }


def read_disk_info(path: Path = Path("/")) -> dict[str, Optional[float]]:
    try:
        usage = shutil.disk_usage(path)
    except OSError:
        return {
            "total_gb": None,
            "used_gb": None,
            "free_gb": None,
            "used_percent": None,
        }
    total = usage.total
    used = usage.used
    free = usage.free
    return {
        "total_gb": round(total / (1024 ** 3), 2),
        "used_gb": round(used / (1024 ** 3), 2),
        "free_gb": round(free / (1024 ** 3), 2),
        "used_percent": round(100.0 * used / total, 1) if total else None,
    }


def read_uptime() -> Optional[float]:
    text = read_text(Path("/proc/uptime"))
    if not text:
        return None
    try:
        return round(float(text.split()[0]), 1)
    except (ValueError, IndexError):
        return None


def read_boot_time() -> Optional[str]:
    uptime = read_uptime()
    if uptime is None:
        return None
    boot = datetime.now().astimezone() - timedelta(seconds=uptime)
    return boot.isoformat(timespec="seconds")


def read_pi_model() -> Optional[str]:
    return read_text(Path("/proc/device-tree/model"))


def read_os_release() -> dict[str, Optional[str]]:
    text = read_text(Path("/etc/os-release"))
    if not text:
        return {"name": None, "version": None, "pretty_name": None}
    result: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key] = value.strip().strip('"')
    return {
        "name": result.get("NAME"),
        "version": result.get("VERSION"),
        "pretty_name": result.get("PRETTY_NAME"),
    }


def run_command(command: list[str], timeout: float = 2.0) -> Optional[str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    output = completed.stdout.strip()
    return output or None


def read_ipv4_addresses() -> list[str]:
    output = run_command(["hostname", "-I"])
    if not output:
        return []
    addresses = []
    for token in output.split():
        if ":" in token:
            continue
        addresses.append(token)
    return addresses


def read_wifi_info() -> dict[str, Optional[object]]:
    # Prefer iw for current association details.
    iw_output = run_command(["iw", "dev"])
    interface = None
    if iw_output:
        for line in iw_output.splitlines():
            line = line.strip()
            if line.startswith("Interface "):
                interface = line.split(maxsplit=1)[1].strip()
                break

    ssid = None
    signal_dbm = None
    link_quality_percent = None

    if interface:
        link_output = run_command(["iw", "dev", interface, "link"])
        if link_output:
            for line in link_output.splitlines():
                stripped = line.strip()
                if stripped.startswith("SSID:"):
                    ssid = stripped.split(":", 1)[1].strip()
                elif stripped.startswith("signal:"):
                    parts = stripped.split()
                    if len(parts) >= 2:
                        try:
                            signal_dbm = float(parts[1])
                        except ValueError:
                            pass

    # Fallback for systems where iw is unavailable.
    wireless = read_text(Path("/proc/net/wireless"))
    if wireless:
        lines = [line for line in wireless.splitlines() if ":" in line]
        if lines:
            parts = lines[0].replace(":", " ").split()
            if not interface and parts:
                interface = parts[0]
            if len(parts) >= 4:
                try:
                    quality = float(parts[2].rstrip("."))
                    link_quality_percent = round(min(max(quality / 70.0 * 100.0, 0.0), 100.0), 1)
                except ValueError:
                    pass

    if signal_dbm is not None and link_quality_percent is None:
        # Common practical approximation: -100 dBm = 0%, -50 dBm = 100%.
        link_quality_percent = round(
            min(max(2.0 * (signal_dbm + 100.0), 0.0), 100.0),
            1,
        )

    return {
        "interface": interface,
        "ssid": ssid,
        "signal_dbm": signal_dbm,
        "quality_percent": link_quality_percent,
    }


def read_cpu_temperature() -> Optional[float]:
    text = read_text(Path("/sys/class/thermal/thermal_zone0/temp"))
    if not text:
        return None
    try:
        return round(float(text) / 1000.0, 1)
    except ValueError:
        return None



def read_rtc_info() -> dict[str, Any]:
    """Return external RTC status without changing the hardware clock."""
    device = Path("/dev/rtc0")
    name = read_text(Path("/sys/class/rtc/rtc0/name"))
    since_epoch = read_text(Path("/sys/class/rtc/rtc0/since_epoch"))
    hardware_time = run_command(["hwclock", "--show", "--utc"], timeout=2.0)

    return {
        "available": device.exists(),
        "device": str(device),
        "driver_name": name,
        "hardware_time_utc": hardware_time,
        "seconds_since_epoch": int(since_epoch) if since_epoch and since_epoch.isdigit() else None,
        "expected_model": "DS3231",
        "expected_i2c_address": "0x68",
    }


def build_system_info() -> dict[str, Any]:
    hostname = socket.gethostname()
    memory = read_memory_info()
    disk = read_disk_info()
    wifi = read_wifi_info()
    os_release = read_os_release()

    return {
        "dashboard_version": VERSION,
        "hostname": hostname,
        "pi_model": read_pi_model(),
        "architecture": platform.machine(),
        "kernel": platform.release(),
        "python_version": platform.python_version(),
        "os": os_release,
        "cpu_percent": read_cpu_percent(),
        "cpu_temperature_c": read_cpu_temperature(),
        "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
        "memory": memory,
        "disk": disk,
        "uptime_seconds": read_uptime(),
        "boot_time": read_boot_time(),
        "ipv4_addresses": read_ipv4_addresses(),
        "wifi": wifi,
        "rtc": read_rtc_info(),
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }


def build_configuration_summary(config: dict) -> dict[str, Any]:
    gpio = config.get("gpio", {})
    return_cfg = config.get("return_sensor", {})
    level_cfg = config.get("low_level_sensor", {})
    temperature = config.get("temperature", {})
    ambient = config.get("ambient", {})
    rtc = config.get("rtc", {})
    logging_cfg = config.get("logging", {})
    dashboard = config.get("dashboard", {})
    notifications = config.get("notifications", {})

    return {
        "software": {
            "dashboard_version": VERSION,
            "monitor_version": VERSION,
        },
        "alarm_thresholds": {
            "reservoir_warning_c": temperature.get("warning_c"),
            "reservoir_critical_c": temperature.get("critical_c"),
            "reservoir_clear_c": temperature.get("clear_c"),
            "temperature_sensor_failures_before_alarm": (
                temperature.get("sensor_failures_before_alarm")
            ),
            "grow_pipe_alarm_enabled": temperature.get(
                "grow_pipe_alarm_enabled", False
            ),
            "grow_pipe_default_role": "Display and logging only",
            "return_dry_delay_seconds": return_cfg.get("dry_delay_seconds"),
            "return_startup_grace_seconds": return_cfg.get(
                "startup_grace_seconds"
            ),
            "low_water_alarm_delay_seconds": level_cfg.get(
                "alarm_delay_seconds"
            ),
            "low_water_startup_grace_seconds": level_cfg.get(
                "startup_grace_seconds"
            ),
        },
        "sampling_and_logging": {
            "dual_DS18B20_read_interval_seconds": (
                temperature.get("read_interval_seconds")
            ),
            "reservoir_sensor_id": temperature.get("reservoir_sensor_id") or "Not assigned",
            "grow_pipe_enabled": temperature.get("grow_pipe_enabled", True),
            "grow_pipe_sensor_id": temperature.get("grow_pipe_sensor_id") or "Not assigned",
            "ambient_read_interval_seconds": ambient.get(
                "read_interval_seconds"
            ),
            "ambient_max_stale_seconds": ambient.get("max_stale_seconds"),
            "csv_logging_interval_seconds": logging_cfg.get(
                "csv_interval_seconds"
            ),
            "dashboard_status_stale_after_seconds": dashboard.get(
                "status_stale_after_seconds"
            ),
            "dashboard_system_info_refresh_seconds": dashboard.get(
                "system_info_refresh_seconds"
            ),
            "dashboard_frontend_status_refresh_seconds": 5,
            "dashboard_frontend_graph_refresh_seconds": 60,
        },
        "dashboard": {
            "bind_address": dashboard.get("bind_address"),
            "port": dashboard.get("port"),
            "default_history_hours": dashboard.get(
                "default_history_hours"
            ),
            "max_points_per_series": dashboard.get(
                "max_points_per_series"
            ),
            "read_only": True,
            "remote_access_configured": False,
        },
        "notifications": {
            "enabled": notifications.get("enabled"),
            "provider": notifications.get("provider", "pushover"),
            "title_prefix": notifications.get("title_prefix"),
            "credentials_file": notifications.get("secrets_path"),
            "credentials_in_dashboard_or_backup": False,
            "send_clear_messages": notifications.get("send_clear_messages"),
            "active_reminders_enabled": notifications.get(
                "active_reminders_enabled"
            ),
            "reminder_minutes": notifications.get("reminder_minutes"),
            "critical_priority": "High (1); bypasses Pushover quiet hours",
            "warning_priority": "Normal (0)",
            "clear_priority": "Low (-1); silent",
            "emergency_priority_used": False,
            "network_required_for_phone_delivery": True,
            "local_led_and_buzzer_independent": True,
        },
        "low_level_sensor": {
            "enabled": level_cfg.get("enabled"),
            "product": level_cfg.get("product"),
            "normal_contact_closed_to_ground": level_cfg.get(
                "normal_contact_closed_to_ground"
            ),
            "external_pullup_ohms": level_cfg.get(
                "external_pullup_ohms"
            ),
            "fail_safe_open_circuit_is_low": level_cfg.get(
                "fail_safe_open_circuit_is_low"
            ),
            "alarm_delay_seconds": level_cfg.get("alarm_delay_seconds"),
            "startup_grace_seconds": level_cfg.get(
                "startup_grace_seconds"
            ),
        },
        "rtc": {
            "enabled": rtc.get("enabled"),
            "model": rtc.get("model"),
            "module": rtc.get("module"),
            "i2c_bus": rtc.get("i2c_bus"),
            "i2c_address": rtc.get("i2c_address"),
            "device_tree_overlay": rtc.get("device_tree_overlay"),
            "device": rtc.get("device"),
        },
        "gpio": {
            "RTC I2C SDA": rtc.get("sda_gpio", 2),
            "RTC I2C SCL": rtc.get("scl_gpio", 3),
            "DS18B20 reservoir temperature (shared 1-Wire bus)": 4,
            "DS18B20 grow-pipe temperature (shared 1-Wire bus)": 4,
            "Reservoir low-level float switch": gpio.get(
                "low_level_sensor"
            ),
            "Return-water sensor": gpio.get("return_sensor"),
            "Alarm-inhibit switch": gpio.get("override_switch"),
            "Buzzer": gpio.get("buzzer"),
            "Amber override LED": gpio.get("override_led"),
            "Red alarm LED": gpio.get("alarm_led"),
            "DHT22 ambient sensor": ambient.get("gpio"),
            "Green status LED": gpio.get("status_led"),
        },
        "paths": {
            "configuration": "/opt/hydro-monitor/config.json",
            "readings_csv": logging_cfg.get("csv_path"),
            "event_log": logging_cfg.get("event_log_path"),
            "current_status": dashboard.get("current_status_path"),
            "rtc_device": rtc.get("device"),
            "temperature_terminal_1": "Reservoir: 3.3V, DATA, GND, NC",
            "temperature_terminal_2": "Grow pipe: 3.3V, DATA, GND, NC",
            "switch_terminal": "4-way block: inhibit GPIO18, GND, float GPIO17, GND",
            "dht22_terminal": "3-way block: 3.3V, DATA GPIO22, GND",
            "sen0368_terminal": "3-way block: 5V, GND, IO2 to Q1/GPIO24",
            "led_terminal": "6-way block: red, amber and green LED pairs",
        },
    }


def create_backup_archive(
    config_path: Path,
    csv_path: Path,
    event_log_path: Path,
) -> tuple[bytes, str]:
    timestamp = datetime.now().astimezone()
    stamp = timestamp.strftime("%Y-%m-%d_%H%M%S")
    archive_name = f"hydro-monitor-backup_{stamp}.zip"

    manifest = {
        "created_at": timestamp.isoformat(timespec="seconds"),
        "dashboard_version": VERSION,
        "contents": [
            "config.json",
            "readings.csv",
            "events.log",
        ],
        "note": (
            "Read-only dashboard backup. Missing runtime files are represented "
            "by explanatory text files."
        ),
    }

    buffer = io.BytesIO()
    with zipfile.ZipFile(
        buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:
        archive.writestr(
            "backup_manifest.json",
            json.dumps(manifest, indent=2) + "\n",
        )

        sources = [
            (config_path, "config.json"),
            (csv_path, "readings.csv"),
            (event_log_path, "events.log"),
        ]
        for path, archive_name_inside in sources:
            if path.exists() and path.is_file():
                archive.write(path, archive_name_inside)
            else:
                archive.writestr(
                    f"{archive_name_inside}.MISSING.txt",
                    f"{path} did not exist when this backup was created.\n",
                )

    return buffer.getvalue(), archive_name


class DashboardServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, handler, config: dict):
        super().__init__(address, handler)
        self.config = config


class Handler(BaseHTTPRequestHandler):
    server_version = "HydroDashboard/8"

    @property
    def config(self) -> dict:
        return self.server.config  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        sys.stdout.write(
            f'{self.address_string()} - [{self.log_date_time_string()}] '
            f'{format % args}\n'
        )
        sys.stdout.flush()

    def send_json(self, payload: Any, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_bytes(
        self,
        body: bytes,
        content_type: str,
        download_name: str,
    ) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Content-Disposition",
            f'attachment; filename="{download_name}"',
        )
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, download_name: Optional[str] = None) -> None:
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        stat = path.stat()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(stat.st_size))
        self.send_header("X-Content-Type-Options", "nosniff")
        if download_name:
            self.send_header(
                "Content-Disposition",
                f'attachment; filename="{download_name}"',
            )
        else:
            self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        with path.open("rb") as handle:
            while chunk := handle.read(64 * 1024):
                self.wfile.write(chunk)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query, keep_blank_values=True)

        if parsed.path in SAFE_ASSETS:
            self.send_file(INSTALL_DIR / SAFE_ASSETS[parsed.path])
            return

        log_cfg = self.config["logging"]
        dashboard_cfg = self.config.get("dashboard", {})
        status_path = Path(
            dashboard_cfg.get(
                "current_status_path",
                "/var/lib/hydro-monitor/current_status.json",
            )
        )
        csv_path = Path(log_cfg["csv_path"])
        event_log_path = Path(log_cfg["event_log_path"])

        if parsed.path == "/api/status":
            if not status_path.exists():
                self.send_json(
                    {
                        "available": False,
                        "error": "Current status has not yet been written.",
                    },
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return
            try:
                payload = json.loads(status_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.send_json(
                    {"available": False, "error": str(exc)},
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return

            updated = parse_iso(str(payload.get("updated_at", "")))
            stale_after = float(
                dashboard_cfg.get("status_stale_after_seconds", 15)
            )
            age = None
            stale = True
            if updated is not None:
                age = max(
                    0.0,
                    (datetime.now().astimezone() - updated).total_seconds(),
                )
                stale = age > stale_after
            payload["available"] = True
            payload["dashboard_status_age_seconds"] = age
            payload["dashboard_status_stale"] = stale
            self.send_json(payload)
            return

        if parsed.path == "/api/history":
            default_hours = float(
                dashboard_cfg.get("default_history_hours", 24)
            )
            start, end = parse_range(query, default_hours)
            maximum = int(
                dashboard_cfg.get("max_points_per_series", 1200)
            )
            try:
                requested_max = int(query.get("max_points", [str(maximum)])[0])
                maximum = min(max(requested_max, 50), 5000)
            except ValueError:
                pass
            rows, total = read_history(csv_path, start, end, maximum)
            self.send_json(
                {
                    "start": start.isoformat(timespec="seconds"),
                    "end": end.isoformat(timespec="seconds"),
                    "returned_points": len(rows),
                    "matching_points": total,
                    "sampled": total > len(rows),
                    "rows": rows,
                }
            )
            return

        if parsed.path == "/api/events":
            search = query.get("q", [""])[0]
            level = query.get("level", ["ALL"])[0]
            try:
                limit = min(max(int(query.get("limit", ["250"])[0]), 1), 2000)
            except ValueError:
                limit = 250
            self.send_json(
                {
                    "query": search,
                    "level": level,
                    "events": read_events(
                        event_log_path,
                        search,
                        level,
                        limit,
                    ),
                }
            )
            return

        if parsed.path == "/download/readings.csv":
            self.send_file(csv_path, "hydro-readings.csv")
            return

        if parsed.path == "/download/events.log":
            self.send_file(event_log_path, "hydro-events.log")
            return

        if parsed.path == "/api/system":
            self.send_json(build_system_info())
            return

        if parsed.path == "/api/configuration":
            self.send_json(build_configuration_summary(self.config))
            return

        if parsed.path == "/download/config.json":
            self.send_file(
                Path("/opt/hydro-monitor/config.json"),
                "hydro-monitor-config.json",
            )
            return

        if parsed.path == "/download/backup.zip":
            backup_body, backup_name = create_backup_archive(
                Path("/opt/hydro-monitor/config.json"),
                csv_path,
                event_log_path,
            )
            self.send_bytes(
                backup_body,
                "application/zip",
                backup_name,
            )
            return

        if parsed.path == "/api/health":
            self.send_json({"ok": True, "version": VERSION})
            return

        self.send_error(HTTPStatus.NOT_FOUND)


def main() -> int:
    parser = argparse.ArgumentParser(description="Local hydroponics dashboard")
    parser.add_argument(
        "--config",
        default=str(INSTALL_DIR / "config.json"),
    )
    parser.add_argument("--bind")
    parser.add_argument("--port", type=int)
    args = parser.parse_args()

    config = load_config(Path(args.config))
    dashboard_cfg = config.get("dashboard", {})
    bind = args.bind or dashboard_cfg.get("bind_address", "0.0.0.0")
    port = args.port or int(dashboard_cfg.get("port", 8080))

    server = DashboardServer((bind, port), Handler, config)
    print(
        f"Hydro dashboard v{VERSION} listening on http://{bind}:{port}/",
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
