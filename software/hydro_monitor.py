#!/usr/bin/env python3
"""
Hydroponic reservoir monitor for Raspberry Pi 3B and compatible 40-pin models.

This release preserves the trusted monitoring and alarm behaviour and final permanent-board
GPIO allocation while adding power-loss resilience for persistent runtime data. Both DS18B20
probes remain on the standard GPIO4 1-Wire bus.

Monitors:
- DS18B20 reservoir-temperature probe on GPIO4 (shared 1-Wire bus)
- DS18B20 grow-pipe airspace probe on GPIO4 (shared 1-Wire bus)
- DFRobot SEN0368 non-contact return-water sensor on GPIO24
- Jaycar SF0920 reservoir low-level float switch on GPIO17
- Maintained alarm-inhibit switch on GPIO18
- 5 V active buzzer through an NPN transistor on GPIO12
- Amber override LED on GPIO20
- Red alarm LED on GPIO26
- DHT22 ambient temperature/humidity module on GPIO22
- Green system-status LED on GPIO21

The DHT22 and grow-pipe DS18B20 are deliberately data-only by default. They cannot
activate the buzzer or alarm LEDs. Reservoir-temperature protection remains exactly as
in the established baseline. Pushover is optional and disabled by default; local alarms never depend
on it.

GPIO numbers are BCM numbering, not physical header numbers.
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import queue
import threading
import signal
import shutil
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from hydro_version import VERSION

from gpiozero import Button, DigitalInputDevice, DigitalOutputDevice

try:
    import board
    import adafruit_dht
except ImportError:
    board = None
    adafruit_dht = None


RUNNING = True

READINGS_FIELDNAMES = [
    "timestamp",
    "water_temp_c",
    "reservoir_temp_c",
    "grow_pipe_temp_c",
    "grow_pipe_minus_reservoir_c",
    "reservoir_temp_sensor_fault",
    "grow_pipe_temp_sensor_fault",
    "ambient_temp_c",
    "ambient_rh_percent",
    "air_minus_water_c",
    "ambient_last_attempt_ok",
    "ambient_sample_age_s",
    "ambient_data_stale",
    "ambient_consecutive_failures",
    "return_sensor_raw",
    "return_wet",
    "low_level_sensor_enabled",
    "low_level_sensor_raw",
    "reservoir_level_ok",
    "low_level_alarm",
    "override_active",
    "flow_alarm",
    "temp_state",
    "temp_sensor_fault",
    "active_alarm",
    "system_status",
    "green_status_led_on",
    "pi_cpu_temp_c",
]


@dataclass
class AmbientState:
    """Last known DHT22 state. This state never participates in alarm selection."""

    sensor: Any = None
    last_temp_c: Optional[float] = None
    last_rh_percent: Optional[float] = None
    last_valid_monotonic: Optional[float] = None
    last_attempt_ok: bool = False
    consecutive_failures: int = 0
    fault_logged: bool = False



PUSHOVER_MESSAGES_URL = "https://api.pushover.net/1/messages.json"


class PermanentNotificationError(RuntimeError):
    """Pushover rejected a request that should not be retried unchanged."""


class TransientNotificationError(RuntimeError):
    """A temporary network or server error prevented message delivery."""


@dataclass
class NotificationRuntimeState:
    enabled: bool = False
    configured: bool = False
    worker_running: bool = False
    queued_messages: int = 0
    sent_this_session: int = 0
    failed_this_session: int = 0
    last_event: Optional[str] = None
    last_attempt_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_error_at: Optional[str] = None
    last_error: Optional[str] = None
    last_request_id: Optional[str] = None


def load_optional_json(path: Path) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def send_pushover_request(
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    """Send one HTTPS POST to Pushover and return its JSON response."""
    encoded = urllib_parse.urlencode(payload).encode("utf-8")
    request = urllib_request.Request(
        PUSHOVER_MESSAGES_URL,
        data=encoded,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": f"HydroMonitor/{VERSION}",
        },
    )

    try:
        with urllib_request.urlopen(request, timeout=timeout_seconds) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib_error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
            detail = json.loads(body)
            errors = detail.get("errors") or []
            message = "; ".join(str(item) for item in errors) or str(exc)
        except Exception:
            message = str(exc)
        if 400 <= exc.code < 500:
            raise PermanentNotificationError(message) from exc
        raise TransientNotificationError(message) from exc
    except (urllib_error.URLError, TimeoutError, OSError) as exc:
        raise TransientNotificationError(str(exc)) from exc

    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise TransientNotificationError("Pushover returned invalid JSON") from exc

    if int(result.get("status", 0)) != 1:
        errors = result.get("errors") or ["Pushover rejected the message"]
        raise PermanentNotificationError("; ".join(str(item) for item in errors))
    return result


def temperature_notification_mode(
    temp_state: str,
    temp_sensor_fault: bool,
) -> str:
    if temp_sensor_fault:
        return "SENSOR_FAULT"
    if temp_state == "CRITICAL":
        return "CRITICAL"
    if temp_state == "WARNING":
        return "WARNING"
    return "NORMAL"


def temperature_transition_events(previous: str, current: str) -> list[str]:
    """Return concise, non-contradictory notification events for a transition."""
    if previous == current:
        return []
    if current == "SENSOR_FAULT":
        return ["TEMP_SENSOR_FAULT"]
    if previous == "SENSOR_FAULT":
        events = ["TEMP_SENSOR_RESTORED"]
        if current == "CRITICAL":
            events.append("TEMP_CRITICAL_ACTIVE")
        elif current == "WARNING":
            events.append("TEMP_WARNING_ACTIVE")
        return events
    if current == "CRITICAL":
        return ["TEMP_CRITICAL_ACTIVE"]
    if previous == "CRITICAL" and current == "WARNING":
        return ["TEMP_CRITICAL_EASED"]
    if current == "WARNING":
        return ["TEMP_WARNING_ACTIVE"]
    if current == "NORMAL" and previous in {"WARNING", "CRITICAL"}:
        return ["TEMP_NORMAL"]
    return []


def build_notification_message(
    event: str,
    now_wall: datetime,
    water_temp_c: Optional[float],
    return_wet: bool,
    reservoir_level_ok: Optional[bool],
    warning_c: float,
    critical_c: float,
    dry_delay: float,
    low_level_delay: float,
    temp_failures: int,
    title_prefix: str,
) -> tuple[str, str]:
    titles = {
        "LOW_WATER_ACTIVE": "Reservoir level LOW",
        "LOW_WATER_CLEARED": "Reservoir level restored",
        "LOW_WATER_REMINDER": "Reservoir level still LOW",
        "FLOW_LOSS_ACTIVE": "Return flow LOST",
        "FLOW_RESTORED": "Return flow restored",
        "FLOW_LOSS_REMINDER": "Return flow still absent",
        "TEMP_WARNING_ACTIVE": "Reservoir temperature warning",
        "TEMP_CRITICAL_ACTIVE": "Reservoir temperature CRITICAL",
        "TEMP_CRITICAL_EASED": "Temperature below critical",
        "TEMP_NORMAL": "Reservoir temperature normal",
        "TEMP_CRITICAL_REMINDER": "Temperature still CRITICAL",
        "TEMP_SENSOR_FAULT": "Water-temperature sensor fault",
        "TEMP_SENSOR_RESTORED": "Water-temperature sensor restored",
        "TEMP_SENSOR_FAULT_REMINDER": "Temperature sensor still offline",
    }
    descriptions = {
        "LOW_WATER_ACTIVE": (
            f"The reservoir float switch has remained low for {low_level_delay:.0f} seconds. "
            "Refill the reservoir and confirm the pump remains safely submerged."
        ),
        "LOW_WATER_CLEARED": "The float switch now reports an acceptable reservoir level.",
        "LOW_WATER_REMINDER": "The low-reservoir condition remains active and needs attention.",
        "FLOW_LOSS_ACTIVE": (
            f"No return water has been detected for {dry_delay:.0f} seconds. "
            "Check pump power, blockages, feed lines and the return pipe."
        ),
        "FLOW_RESTORED": "Return water is being detected again.",
        "FLOW_LOSS_REMINDER": "The return-flow alarm remains active and needs attention.",
        "TEMP_WARNING_ACTIVE": (
            f"Reservoir water has reached the {warning_c:.1f}°C warning range. "
            "Check shade, aeration and cooling measures."
        ),
        "TEMP_CRITICAL_ACTIVE": (
            f"Reservoir water has reached the {critical_c:.1f}°C critical range. "
            "Inspect the system promptly and add cooling/aeration as appropriate."
        ),
        "TEMP_CRITICAL_EASED": (
            "Water temperature is below the critical threshold but remains in the warning range."
        ),
        "TEMP_NORMAL": "Reservoir water temperature has returned to the normal range.",
        "TEMP_CRITICAL_REMINDER": "The critical-temperature condition remains active.",
        "TEMP_SENSOR_FAULT": (
            f"The DS18B20 has failed {temp_failures} consecutive readings. "
            "Water-temperature protection is currently unavailable."
        ),
        "TEMP_SENSOR_RESTORED": "The DS18B20 is reporting valid water temperature again.",
        "TEMP_SENSOR_FAULT_REMINDER": "The DS18B20 remains unavailable.",
    }

    temp_text = "Unavailable" if water_temp_c is None else f"{water_temp_c:.1f}°C"
    level_text = (
        "Unknown" if reservoir_level_ok is None
        else "Normal" if reservoir_level_ok
        else "LOW"
    )
    return_text = "Detected" if return_wet else "NOT DETECTED"
    time_text = now_wall.strftime("%d %b %Y %H:%M:%S %Z")
    title = f"{title_prefix}: {titles.get(event, event)}"
    message = "\n".join([
        descriptions.get(event, event),
        "",
        f"Time: {time_text}",
        f"Reservoir temperature: {temp_text}",
        f"Return water: {return_text}",
        f"Reservoir level: {level_text}",
    ])
    return title, message


class PushoverNotifier:
    """Non-blocking Pushover sender. GPIO monitoring never waits for the network."""

    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.enabled = bool(cfg.get("enabled", False))
        self.secrets_path = Path(
            cfg.get("secrets_path", "/etc/hydro-monitor/pushover.json")
        )
        self.secrets = load_optional_json(self.secrets_path)
        self.user_key = str(self.secrets.get("user_key", "")).strip()
        self.api_token = str(self.secrets.get("api_token", "")).strip()
        self.device = str(self.secrets.get("device", "")).strip()
        self.configured = bool(self.user_key and self.api_token)
        self.timeout = float(cfg.get("request_timeout_seconds", 8))
        self.attempts = max(1, int(cfg.get("local_retry_attempts", 3)))
        self.retry_delay = max(5.0, float(cfg.get("local_retry_delay_seconds", 5)))
        self._queue: queue.Queue[Optional[dict[str, Any]]] = queue.Queue(
            maxsize=max(1, int(cfg.get("queue_max_messages", 100)))
        )
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self.state = NotificationRuntimeState(
            enabled=self.enabled,
            configured=self.configured,
        )

    @property
    def ready(self) -> bool:
        return self.enabled and self.configured

    def start(self) -> None:
        if not self.enabled:
            logging.info("Pushover notifications disabled in config")
            return
        if not self.configured:
            logging.error(
                "Pushover is enabled but credentials are missing from %s; "
                "local alarms continue normally",
                self.secrets_path,
            )
            return
        self._thread = threading.Thread(
            target=self._worker,
            name="pushover-notifier",
            daemon=True,
        )
        self._thread.start()
        with self._lock:
            self.state.worker_running = True
        logging.info("Pushover notification worker started")

    def stop(self) -> None:
        self._stop.set()
        try:
            self._queue.put_nowait(None)
        except queue.Full:
            pass
        if self._thread is not None:
            self._thread.join(timeout=3.0)
        with self._lock:
            self.state.worker_running = False

    def notify(self, event: str, title: str, message: str) -> bool:
        if not self.ready:
            return False
        profile = self.cfg.get("events", {}).get(event, {})
        if not bool(profile.get("enabled", True)):
            return False
        item: dict[str, Any] = {
            "event": event,
            "title": title,
            "message": message,
            "priority": int(profile.get("priority", 0)),
            "sound": str(profile.get("sound", "")).strip(),
            "timestamp": int(time.time()),
        }
        try:
            self._queue.put_nowait(item)
        except queue.Full:
            self._record_failure(event, "notification queue is full")
            logging.error("Pushover queue full; dropped event %s", event)
            return False
        with self._lock:
            self.state.queued_messages = self._queue.qsize()
            self.state.last_event = event
        return True

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            self.state.queued_messages = self._queue.qsize()
            return {
                "provider": "pushover",
                "enabled": self.state.enabled,
                "configured": self.state.configured,
                "ready": self.ready,
                "worker_running": self.state.worker_running,
                "queued_messages": self.state.queued_messages,
                "sent_this_session": self.state.sent_this_session,
                "failed_this_session": self.state.failed_this_session,
                "last_event": self.state.last_event,
                "last_attempt_at": self.state.last_attempt_at,
                "last_success_at": self.state.last_success_at,
                "last_error_at": self.state.last_error_at,
                "last_error": self.state.last_error,
                "last_request_id": self.state.last_request_id,
                "credentials_exposed": False,
            }

    def _record_failure(self, event: str, error: str) -> None:
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._lock:
            self.state.failed_this_session += 1
            self.state.last_event = event
            self.state.last_error_at = now
            self.state.last_error = error[:500]

    def _worker(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            if item is None:
                self._queue.task_done()
                break
            try:
                self._send_with_retries(item)
            finally:
                self._queue.task_done()
                with self._lock:
                    self.state.queued_messages = self._queue.qsize()
        with self._lock:
            self.state.worker_running = False

    def _send_with_retries(self, item: dict[str, Any]) -> None:
        payload: dict[str, Any] = {
            "token": self.api_token,
            "user": self.user_key,
            "title": item["title"],
            "message": item["message"],
            "priority": item["priority"],
            "timestamp": item["timestamp"],
        }
        if item.get("sound"):
            payload["sound"] = item["sound"]
        if self.device:
            payload["device"] = self.device

        event = str(item["event"])
        for attempt in range(1, self.attempts + 1):
            now = datetime.now().astimezone().isoformat(timespec="seconds")
            with self._lock:
                self.state.last_attempt_at = now
                self.state.last_event = event
            try:
                result = send_pushover_request(payload, self.timeout)
            except PermanentNotificationError as exc:
                self._record_failure(event, str(exc))
                logging.error("Pushover permanently rejected %s: %s", event, exc)
                return
            except TransientNotificationError as exc:
                if attempt >= self.attempts:
                    self._record_failure(event, str(exc))
                    logging.error(
                        "Pushover failed after %d attempts for %s: %s",
                        attempt,
                        event,
                        exc,
                    )
                    return
                logging.warning(
                    "Temporary Pushover failure for %s (attempt %d/%d): %s",
                    event,
                    attempt,
                    self.attempts,
                    exc,
                )
                if self._stop.wait(self.retry_delay):
                    return
                continue

            success_at = datetime.now().astimezone().isoformat(timespec="seconds")
            with self._lock:
                self.state.sent_this_session += 1
                self.state.last_success_at = success_at
                self.state.last_error = None
                self.state.last_request_id = result.get("request")
            logging.info("Pushover sent: %s", event)
            return


def handle_signal(signum, frame) -> None:
    global RUNNING
    RUNNING = False


def load_config(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def configure_logging(event_log_path: Path) -> None:
    event_log_path.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(event_log_path, encoding="utf-8"),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
    )


DS18B20_ROOT = Path("/sys/bus/w1/devices")


def normalise_ds18b20_id(value: Any) -> str:
    """Return a clean 28-... sensor ID, or an empty string for unconfigured."""
    text = str(value or "").strip()
    if not text:
        return ""
    if not text.startswith("28-") or "/" in text or "\\" in text:
        raise ValueError(f"Invalid DS18B20 sensor ID: {text!r}")
    return text


def list_ds18b20_ids(root: Path = DS18B20_ROOT) -> list[str]:
    """List discovered DS18B20 hardware IDs in stable lexical order."""
    try:
        return sorted(path.name for path in root.glob("28-*") if path.is_dir())
    except OSError:
        return []


def find_ds18b20(
    sensor_id: Optional[str] = None,
    root: Path = DS18B20_ROOT,
) -> Optional[Path]:
    """
    Resolve a DS18B20 data file.

    A configured hardware ID is always resolved exactly. The empty-ID fallback is
    retained only for isolated offline tests and maintenance utilities; normal
    service startup requires assigned role IDs. It deliberately refuses to guess when
    two or more probes are connected because filesystem ordering does not identify
    their location.
    """
    cleaned = normalise_ds18b20_id(sensor_id)
    if cleaned:
        path = root / cleaned / "w1_slave"
        return path if path.exists() else None

    devices = list_ds18b20_ids(root)
    if len(devices) == 1:
        return root / devices[0] / "w1_slave"
    return None


def validate_temperature_probe_config(temp_cfg: dict) -> tuple[str, str, bool]:
    """Validate and return reservoir ID, grow-pipe ID and grow-pipe enabled flag."""
    reservoir_id = normalise_ds18b20_id(temp_cfg.get("reservoir_sensor_id", ""))
    grow_enabled = bool(temp_cfg.get("grow_pipe_enabled", True))
    grow_id = normalise_ds18b20_id(temp_cfg.get("grow_pipe_sensor_id", ""))
    if bool(temp_cfg.get("grow_pipe_alarm_enabled", False)):
        raise ValueError(
            "Grow-pipe alarms are intentionally disabled in this design; "
            "set temperature.grow_pipe_alarm_enabled to false"
        )
    if not reservoir_id:
        raise ValueError(
            "temperature.reservoir_sensor_id is not assigned; run "
            "/opt/hydro-monitor/configure_temperature_probes.py before starting the service"
        )
    if grow_enabled and not grow_id:
        raise ValueError(
            "temperature.grow_pipe_sensor_id is not assigned while grow-pipe monitoring "
            "is enabled; assign it or disable grow-pipe monitoring with "
            "/opt/hydro-monitor/configure_temperature_probes.py --disable-grow-pipe"
        )
    if grow_enabled and reservoir_id == grow_id:
        raise ValueError(
            "temperature.reservoir_sensor_id and grow_pipe_sensor_id must be different"
        )
    return reservoir_id, grow_id, grow_enabled


def read_ds18b20(sensor_file: Optional[Path]) -> Optional[float]:
    if sensor_file is None or not sensor_file.exists():
        return None

    try:
        lines = sensor_file.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return None

    if len(lines) < 2 or not lines[0].strip().endswith("YES"):
        return None

    marker = "t="
    index = lines[1].find(marker)
    if index == -1:
        return None

    try:
        value = float(lines[1][index + len(marker):]) / 1000.0
    except ValueError:
        return None

    # Reject obviously impossible values for this application.
    if not -10.0 <= value <= 60.0:
        return None
    return value


def read_cpu_temp() -> Optional[float]:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    try:
        return float(path.read_text(encoding="utf-8").strip()) / 1000.0
    except (OSError, ValueError):
        return None


def fsync_directory(path: Path) -> None:
    """Best-effort directory sync after replacing or creating a persistent file."""
    try:
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def fsync_file(path: Path) -> None:
    """Best-effort sync of an already closed file."""
    try:
        with path.open("rb+") as handle:
            os.fsync(handle.fileno())
    except OSError:
        pass


def validate_csv_header(header: list[str]) -> None:
    """Reject an unusable or unknown readings schema without guessing at repairs."""
    if not header or any(not name for name in header):
        raise ValueError("readings CSV header is empty or contains a blank column name")
    if len(set(header)) != len(header):
        raise ValueError("readings CSV header contains duplicate column names")
    if "timestamp" not in header:
        raise ValueError("readings CSV header does not contain the timestamp column")
    unexpected = [name for name in header if name not in READINGS_FIELDNAMES]
    if unexpected:
        raise ValueError(
            "readings CSV header contains unexpected columns: "
            + ", ".join(unexpected)
        )


def recover_csv_tail_after_power_loss(path: Path) -> bool:
    """
    Validate the readings CSV tail and remove only an interrupted final record.

    Only the header and final physical record are read, so startup time and memory use do
    not grow with years of retained history. A missing trailing newline, malformed final
    CSV record, wrong final field count, or invalid final timestamp is treated as evidence
    that power was lost during the final append. Before recovery, a timestamped copy of
    the original file is preserved. Earlier records are left byte-for-byte untouched.

    Header corruption is not repaired automatically because doing so would require guessing
    the historical schema. In that case ValueError is raised and normal monitoring stops.
    """
    if not path.exists() or path.stat().st_size == 0:
        return False

    with path.open("rb") as handle:
        header_raw = handle.readline()
        try:
            header_text = header_raw.decode("utf-8").rstrip("\r\n")
        except UnicodeDecodeError as exc:
            raise ValueError("readings CSV header is not valid UTF-8") from exc
        if not header_raw.endswith(b"\n"):
            raise ValueError("readings CSV header appears truncated")
        try:
            header = next(csv.reader([header_text], strict=True))
        except (csv.Error, StopIteration) as exc:
            raise ValueError("readings CSV header cannot be parsed") from exc
        validate_csv_header(header)

        handle.seek(0, os.SEEK_END)
        file_size = handle.tell()
        if file_size == len(header_raw):
            return False

        handle.seek(file_size - 1)
        trailing_newline = handle.read(1) == b"\n"
        search_position = file_size - 2 if trailing_newline else file_size - 1

        record_start: Optional[int] = None
        while search_position >= 0:
            block_start = max(0, search_position - 4095)
            handle.seek(block_start)
            block = handle.read(search_position - block_start + 1)
            index = block.rfind(b"\n")
            if index != -1:
                record_start = block_start + index + 1
                break
            search_position = block_start - 1

        if record_start is None or record_start < len(header_raw):
            raise ValueError("readings CSV does not contain a complete data record boundary")

        handle.seek(record_start)
        final_raw = handle.read(file_size - record_start)

    damaged = not trailing_newline
    final_row: list[str] = []
    try:
        final_text = final_raw.decode("utf-8").rstrip("\r\n")
        final_row = next(csv.reader([final_text], strict=True))
    except (UnicodeDecodeError, csv.Error, StopIteration):
        damaged = True

    if len(final_row) != len(header):
        damaged = True
    elif final_row:
        try:
            timestamp_value = final_row[header.index("timestamp")]
            datetime.fromisoformat(timestamp_value)
        except (ValueError, IndexError):
            damaged = True

    if not damaged:
        return False

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S-%f")
    backup = path.with_name(
        f"{path.stem}.powerloss-recovery-{stamp}{path.suffix}"
    )
    shutil.copy2(path, backup)
    fsync_file(backup)
    fsync_directory(path.parent)

    with path.open("r+b") as handle:
        handle.truncate(record_start)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_directory(path.parent)
    logging.warning(
        "Recovered interrupted final readings CSV record after power loss; "
        "preserved original at %s",
        backup,
    )
    return True


def discard_invalid_current_status(path: Path) -> bool:
    """Discard disposable live-status JSON if an interrupted write left it invalid."""
    if not path.exists():
        return False
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("current status JSON root is not an object")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        try:
            path.unlink()
            fsync_directory(path.parent)
        except OSError as unlink_exc:
            raise OSError(
                f"invalid current-status file could not be removed: {unlink_exc}"
            ) from unlink_exc
        logging.warning(
            "Discarded invalid current-status JSON after unclean shutdown: %s",
            exc,
        )
        return True
    return False


def ensure_csv_schema(path: Path, fieldnames: list[str]) -> None:
    """
    Extend a supported legacy readings CSV safely when the current schema adds columns.

    Existing rows are preserved and a timestamped copy of the original file is made.
    No history is automatically deleted.
    """
    if not path.exists() or path.stat().st_size == 0:
        return
    try:
        with path.open("r", newline="", encoding="utf-8", errors="replace") as handle:
            reader = csv.DictReader(handle)
            existing = list(reader.fieldnames or [])
            if existing == fieldnames:
                return
            if not set(existing).issubset(set(fieldnames)):
                raise ValueError(
                    "Existing readings CSV contains unexpected columns; refusing automatic migration"
                )
            rows = list(reader)
    except OSError:
        raise

    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup = path.with_name(f"{path.stem}.pre-schema-upgrade-{stamp}{path.suffix}")
    shutil.copy2(path, backup)
    temporary = path.with_suffix(path.suffix + ".migrate.tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for old_row in rows:
            migrated = {name: old_row.get(name, "") for name in fieldnames}
            # A legacy schema called the reservoir field water_temp_c.
            if "reservoir_temp_c" in fieldnames and not migrated.get("reservoir_temp_c"):
                migrated["reservoir_temp_c"] = old_row.get("water_temp_c", "")
            if (
                "reservoir_temp_sensor_fault" in fieldnames
                and not migrated.get("reservoir_temp_sensor_fault")
            ):
                migrated["reservoir_temp_sensor_fault"] = old_row.get(
                    "temp_sensor_fault", ""
                )
            writer.writerow(migrated)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)
    logging.info("Extended readings CSV schema; preserved original at %s", backup)


def append_csv(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(row.keys())
    ensure_csv_schema(path, fieldnames)
    exists = path.exists() and path.stat().st_size > 0
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
        handle.flush()
        os.fsync(handle.fileno())


def write_json_atomic(path: Path, payload: dict) -> None:
    """Write JSON atomically so dashboard readers never see a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fsync_directory(path.parent)


def update_temperature_state(
    current_state: str,
    temp_c: Optional[float],
    warning_c: float,
    critical_c: float,
    clear_c: float,
) -> str:
    if temp_c is None:
        return current_state

    if current_state == "NORMAL":
        if temp_c >= critical_c:
            return "CRITICAL"
        if temp_c >= warning_c:
            return "WARNING"
        return "NORMAL"

    if current_state == "WARNING":
        if temp_c >= critical_c:
            return "CRITICAL"
        if temp_c < clear_c:
            return "NORMAL"
        return "WARNING"

    if current_state == "CRITICAL":
        if temp_c < clear_c:
            return "NORMAL"
        if temp_c < critical_c:
            return "WARNING"
        return "CRITICAL"

    return "NORMAL"



def read_low_level_state(
    level_sensor: Optional[DigitalInputDevice],
    normal_contact_closed_to_ground: bool,
) -> tuple[Optional[int], Optional[bool]]:
    """
    Return electrical pin level and interpreted reservoir-level state.

    The permanent circuit uses an external 10 kΩ pull-up to 3.3 V. The float
    switch closes GPIO17 to ground when the reservoir is at an acceptable level.
    Therefore:

    - electrical 0 / contact closed = level OK;
    - electrical 1 / contact open = low water or broken/disconnected wiring.

    The interpretation can be inverted in config for a differently oriented
    switch, but the fail-safe closed-at-normal arrangement is recommended.
    """
    if level_sensor is None:
        return None, None

    contact_closed_to_ground = bool(level_sensor.is_active)
    electrical_level = 0 if contact_closed_to_ground else 1
    level_ok = (
        contact_closed_to_ground
        if normal_contact_closed_to_ground
        else not contact_closed_to_ground
    )
    return electrical_level, level_ok



def select_alarm(
    override_active: bool,
    low_level_alarm: bool,
    flow_alarm: bool,
    temp_state: str,
    temp_sensor_fault: bool,
) -> Optional[str]:
    """
    Select the highest-priority active alarm.

    LOW_WATER is prioritised ahead of FLOW_LOSS because it threatens pump
    submersion and may also explain deteriorating return flow. Ambient DHT22
    values are intentionally absent from this function.
    """
    if override_active:
        return None
    if low_level_alarm:
        return "LOW_WATER"
    if flow_alarm:
        return "FLOW_LOSS"
    if temp_state == "CRITICAL":
        return "TEMP_CRITICAL"
    if temp_sensor_fault:
        return "TEMP_SENSOR_FAULT"
    if temp_state == "WARNING":
        return "TEMP_WARNING"
    return None


def buzzer_pattern(alarm: Optional[str], elapsed: float) -> bool:
    """Return True when the buzzer should be energised."""
    if alarm is None:
        return False

    if alarm == "LOW_WATER":
        # One deliberate 0.8-second warning every 3 seconds.
        return (elapsed % 3.0) < 0.8

    if alarm == "FLOW_LOSS":
        # Two 0.4-second beeps every 4 seconds.
        phase = elapsed % 4.0
        return phase < 0.4 or 0.8 <= phase < 1.2

    if alarm == "TEMP_CRITICAL":
        # One second on, one second off.
        return (elapsed % 2.0) < 1.0

    if alarm == "TEMP_SENSOR_FAULT":
        # Three short beeps every 6 seconds.
        phase = elapsed % 6.0
        return (
            phase < 0.2
            or 0.5 <= phase < 0.7
            or 1.0 <= phase < 1.2
        )

    if alarm == "TEMP_WARNING":
        # One short reminder every 10 seconds.
        return (elapsed % 10.0) < 0.4

    return False


def select_system_status(
    override_active: bool,
    grace_active: bool,
    alarm: Optional[str],
    return_wet: bool,
    reservoir_level_ok: Optional[bool],
    water_temp_valid: bool,
    temp_state: str,
    temp_sensor_fault: bool,
) -> str:
    """
    Select the externally visible system status.

    The DHT22 is intentionally absent. Ambient-data failure never changes the
    green LED or any alarm.

    Precedence:
    - INHIBITED: maintenance/refill switch is active.
    - ALARM: an active low-water, flow, temperature or sensor alarm exists.
    - STARTING: startup/refill grace period is active.
    - CHECKING_LEVEL: reservoir float is low but its confirmation delay has not
      yet expired.
    - CHECKING_RETURN: return sensor is dry but its flow-loss delay has not yet
      expired.
    - CHECKING_WATER_TEMP: no current valid DS18B20 sample is available.
    - UNHEALTHY_TEMP: temperature state is not NORMAL.
    - HEALTHY: all monitored alarm conditions are normal.
    """
    if override_active:
        return "INHIBITED"
    if alarm is not None:
        return "ALARM"
    if grace_active:
        return "STARTING"
    if reservoir_level_ok is False:
        return "CHECKING_LEVEL"
    if not return_wet:
        return "CHECKING_RETURN"
    if temp_sensor_fault or not water_temp_valid:
        return "CHECKING_WATER_TEMP"
    if temp_state != "NORMAL":
        return "UNHEALTHY_TEMP"
    return "HEALTHY"


def status_led_pattern(status: str, elapsed: float) -> bool:
    """Return True when the green status LED should be illuminated."""
    if status == "HEALTHY":
        return True
    if status == "STARTING":
        # Calm one-hertz blink: 0.5 seconds on, 0.5 seconds off.
        return (elapsed % 1.0) < 0.5
    return False


def initialise_ambient_sensor(ambient_cfg: dict) -> AmbientState:
    state = AmbientState()

    if not bool(ambient_cfg.get("enabled", True)):
        logging.info("DHT22 ambient monitoring disabled in config")
        return state

    if board is None or adafruit_dht is None:
        logging.warning(
            "DHT22 library unavailable. Ambient data will be blank. "
            "Install adafruit-circuitpython-dht in the project virtual environment."
        )
        return state

    gpio_number = int(ambient_cfg["gpio"])
    board_pin_name = f"D{gpio_number}"

    try:
        board_pin = getattr(board, board_pin_name)
    except AttributeError:
        logging.error("Blinka has no board pin named %s", board_pin_name)
        return state

    try:
        state.sensor = adafruit_dht.DHT22(
            board_pin,
            use_pulseio=bool(ambient_cfg.get("use_pulseio", False)),
        )
    except Exception as exc:
        logging.exception("Unable to initialise DHT22 on GPIO%d: %s", gpio_number, exc)
        state.sensor = None
        return state

    logging.info(
        "DHT22 ambient sensor initialised on GPIO%d (%s); data logging only",
        gpio_number,
        board_pin_name,
    )
    return state


def read_ambient_sensor(
    state: AmbientState,
    ambient_cfg: dict,
    now_monotonic: float,
) -> bool:
    """
    Attempt one DHT22 reading.

    Returns True for a valid reading. Failures are expected occasionally and are
    retained as data-quality information only; they never create an alarm.
    """
    state.last_attempt_ok = False

    if state.sensor is None:
        state.consecutive_failures += 1
        return False

    try:
        temp_c = state.sensor.temperature
        rh_percent = state.sensor.humidity
    except RuntimeError:
        # DHT timing/checksum errors occur occasionally. Retry next interval.
        state.consecutive_failures += 1
        return False
    except Exception as exc:
        state.consecutive_failures += 1
        if not state.fault_logged:
            logging.exception("Unexpected DHT22 read error: %s", exc)
            state.fault_logged = True
        return False

    if temp_c is None or rh_percent is None:
        state.consecutive_failures += 1
        return False

    try:
        temp_c = float(temp_c)
        rh_percent = float(rh_percent)
    except (TypeError, ValueError):
        state.consecutive_failures += 1
        return False

    min_temp = float(ambient_cfg.get("valid_min_temp_c", -40.0))
    max_temp = float(ambient_cfg.get("valid_max_temp_c", 80.0))
    if not min_temp <= temp_c <= max_temp or not 0.0 <= rh_percent <= 100.0:
        state.consecutive_failures += 1
        return False

    had_fault = state.fault_logged
    state.last_temp_c = temp_c
    state.last_rh_percent = rh_percent
    state.last_valid_monotonic = now_monotonic
    state.last_attempt_ok = True
    state.consecutive_failures = 0
    state.fault_logged = False

    if had_fault:
        logging.info("DHT22 ambient readings recovered")

    return True


def update_ambient_fault_logging(state: AmbientState, ambient_cfg: dict) -> None:
    threshold = int(ambient_cfg.get("log_fault_after_failures", 6))
    if (
        state.sensor is not None
        and state.consecutive_failures >= threshold
        and not state.fault_logged
    ):
        logging.warning(
            "DHT22 has failed %d consecutive reads; monitoring continues without an alarm",
            state.consecutive_failures,
        )
        state.fault_logged = True


def ambient_values_for_log(
    state: AmbientState,
    now_monotonic: float,
    max_stale_seconds: float,
) -> tuple[Optional[float], Optional[float], Optional[float], bool]:
    """
    Return ambient temp, RH, sample age, and stale flag.

    Values older than max_stale_seconds are not repeated in the CSV; blank fields
    are preferable to silently presenting old measurements as current.
    """
    if state.last_valid_monotonic is None:
        return None, None, None, True

    age = max(0.0, now_monotonic - state.last_valid_monotonic)
    stale = age > max_stale_seconds
    if stale:
        return None, None, age, True

    return state.last_temp_c, state.last_rh_percent, age, False


def run_self_test(
    return_sensor: DigitalInputDevice,
    level_sensor: Optional[DigitalInputDevice],
    normal_level_contact_closed: bool,
    override_switch: Button,
    buzzer: DigitalOutputDevice,
    override_led: DigitalOutputDevice,
    alarm_led: DigitalOutputDevice,
    status_led: DigitalOutputDevice,
    reservoir_sensor_file: Optional[Path],
    grow_pipe_sensor_file: Optional[Path],
    grow_pipe_required: bool,
    wet_level: int,
    ambient_state: AmbientState,
    ambient_cfg: dict,
) -> bool:
    print(f"Starting hydro monitor v{VERSION} hardware self-test...")
    override_led.on()
    time.sleep(0.5)
    override_led.off()
    alarm_led.on()
    time.sleep(0.5)
    alarm_led.off()
    status_led.on()
    time.sleep(0.5)
    status_led.off()
    buzzer.on()
    time.sleep(0.5)
    buzzer.off()

    raw = int(return_sensor.value)
    print(f"Return sensor raw value: {raw}")
    print(f"Return interpreted as wet: {raw == wet_level}")

    level_raw, level_ok = read_low_level_state(
        level_sensor,
        normal_level_contact_closed,
    )
    if level_sensor is None:
        print("Reservoir low-level switch: DISABLED")
    else:
        print(f"Low-level input electrical value: {level_raw}")
        print(f"Reservoir level interpreted as acceptable: {level_ok}")

    print(f"Override switch active: {override_switch.is_pressed}")

    def test_probe(label: str, sensor_file: Optional[Path]) -> Optional[float]:
        value: Optional[float] = None
        for attempt in range(1, 4):
            value = read_ds18b20(sensor_file)
            if value is not None:
                break
            if attempt < 3:
                time.sleep(0.25)
        print(f"{label}: {value if value is not None else 'NO VALID READING'}")
        return value

    reservoir_test_temp = test_probe(
        "Reservoir temperature (°C)", reservoir_sensor_file
    )
    grow_pipe_test_temp = (
        test_probe("Grow-pipe airspace temperature (°C)", grow_pipe_sensor_file)
        if grow_pipe_required
        else None
    )
    if not grow_pipe_required:
        print("Grow-pipe airspace temperature: DISABLED")

    if ambient_state.sensor is None:
        print("DHT22 ambient sensor: NOT AVAILABLE")
    else:
        ambient_ok = False
        for attempt in range(1, 4):
            if read_ambient_sensor(ambient_state, ambient_cfg, time.monotonic()):
                ambient_ok = True
                break
            if attempt < 3:
                time.sleep(2.1)
        if ambient_ok:
            print(f"Ambient temperature: {ambient_state.last_temp_c} °C")
            print(f"Ambient relative humidity: {ambient_state.last_rh_percent} %")
        else:
            print("DHT22 ambient reading failed after 3 attempts")

    print(f"Pi CPU temperature: {read_cpu_temp()} °C")

    required_probe_failure = reservoir_test_temp is None or (
        grow_pipe_required and grow_pipe_test_temp is None
    )
    if required_probe_failure:
        print(
            "SELF-TEST RESULT: FAILED — each enabled DS18B20 role must produce "
            "a valid reading before the services are enabled.",
            file=sys.stderr,
        )
        return False

    print("SELF-TEST RESULT: REQUIRED TEMPERATURE PROBES PASSED.")
    print("Confirm the LEDs, buzzer and input interpretations manually above.")
    return True


def close_ambient_sensor(state: AmbientState) -> None:
    if state.sensor is None:
        return
    try:
        state.sensor.exit()
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hydroponic dual-temperature, return-water, reservoir-level and ambient-data monitor"
    )
    parser.add_argument(
        "--config",
        default=str(Path(__file__).with_name("config.json")),
        help="Path to config.json",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run a short hardware self-test and exit",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
    )
    args = parser.parse_args()

    config = load_config(Path(args.config))
    gpio = config["gpio"]
    return_cfg = config["return_sensor"]
    level_cfg = config.get("low_level_sensor", {"enabled": False})
    temp_cfg = config["temperature"]
    ambient_cfg = config["ambient"]
    log_cfg = config["logging"]
    dashboard_cfg = config.get("dashboard", {})
    notification_cfg = config.get("notifications", {"enabled": False})

    try:
        reservoir_sensor_id, grow_pipe_sensor_id, grow_pipe_enabled = (
            validate_temperature_probe_config(temp_cfg)
        )
    except ValueError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    event_log_path = Path(log_cfg["event_log_path"])
    csv_path = Path(log_cfg["csv_path"])
    current_status_path = Path(
        dashboard_cfg.get(
            "current_status_path",
            "/var/lib/hydro-monitor/current_status.json",
        )
    )
    configure_logging(event_log_path)
    if not args.test:
        try:
            recover_csv_tail_after_power_loss(csv_path)
            discard_invalid_current_status(current_status_path)
        except (OSError, ValueError) as exc:
            logging.error("Persistent-data integrity check failed: %s", exc)
            print(
                f"Persistent-data integrity check failed: {exc}",
                file=sys.stderr,
            )
            return 2

    notifier = PushoverNotifier(notification_cfg)
    notifier.start()

    # The SEN0368 output is translated through an NPN transistor.
    # An external 10 kΩ resistor pulls GPIO24 up to 3.3 V.
    return_sensor = DigitalInputDevice(
        gpio["return_sensor"],
        pull_up=None,
        active_state=True,
        bounce_time=0.1,
    )
    level_sensor: Optional[DigitalInputDevice] = None
    if bool(level_cfg.get("enabled", False)):
        level_gpio = gpio.get("low_level_sensor")
        if level_gpio is None:
            raise ValueError(
                "low_level_sensor is enabled but gpio.low_level_sensor is missing"
            )
        # External 10 kΩ pull-up to 3.3 V; switch closes the input to ground.
        level_sensor = DigitalInputDevice(
            int(level_gpio),
            pull_up=None,
            active_state=False,
            bounce_time=float(level_cfg.get("bounce_time_seconds", 0.2)),
        )
    override_switch = Button(
        gpio["override_switch"],
        pull_up=True,
        bounce_time=0.1,
    )
    buzzer = DigitalOutputDevice(
        gpio["buzzer"],
        active_high=True,
        initial_value=False,
    )
    override_led = DigitalOutputDevice(
        gpio["override_led"],
        active_high=True,
        initial_value=False,
    )
    alarm_led = DigitalOutputDevice(
        gpio["alarm_led"],
        active_high=True,
        initial_value=False,
    )
    status_led = DigitalOutputDevice(
        gpio["status_led"],
        active_high=True,
        initial_value=False,
    )

    reservoir_sensor_file = find_ds18b20(reservoir_sensor_id)
    grow_pipe_sensor_file = (
        find_ds18b20(grow_pipe_sensor_id) if grow_pipe_enabled else None
    )
    wet_level = int(return_cfg["wet_level"])
    normal_level_contact_closed = bool(
        level_cfg.get("normal_contact_closed_to_ground", True)
    )
    ambient_state = initialise_ambient_sensor(ambient_cfg)

    if args.test:
        self_test_ok = False
        try:
            self_test_ok = run_self_test(
                return_sensor,
                level_sensor,
                normal_level_contact_closed,
                override_switch,
                buzzer,
                override_led,
                alarm_led,
                status_led,
                reservoir_sensor_file,
                grow_pipe_sensor_file,
                grow_pipe_enabled,
                wet_level,
                ambient_state,
                ambient_cfg,
            )
        finally:
            buzzer.off()
            override_led.off()
            alarm_led.off()
            status_led.off()
            close_ambient_sensor(ambient_state)
            return_sensor.close()
            if level_sensor is not None:
                level_sensor.close()
            override_switch.close()
            buzzer.close()
            override_led.close()
            alarm_led.close()
            status_led.close()
            notifier.stop()
        return 0 if self_test_ok else 1

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    sample_interval = float(temp_cfg["read_interval_seconds"])
    log_interval = float(log_cfg["csv_interval_seconds"])
    dry_delay = float(return_cfg["dry_delay_seconds"])
    startup_grace = float(return_cfg["startup_grace_seconds"])
    low_level_delay = float(level_cfg.get("alarm_delay_seconds", 30))
    low_level_startup_grace = float(
        level_cfg.get("startup_grace_seconds", 30)
    )
    warning_c = float(temp_cfg["warning_c"])
    critical_c = float(temp_cfg["critical_c"])
    clear_c = float(temp_cfg["clear_c"])
    max_temp_failures = int(temp_cfg["sensor_failures_before_alarm"])

    ambient_read_interval = float(ambient_cfg.get("read_interval_seconds", 10))
    ambient_max_stale = float(ambient_cfg.get("max_stale_seconds", 300))

    process_started_at = datetime.now().astimezone()
    process_started_monotonic = time.monotonic()
    grace_until = process_started_monotonic + startup_grace
    level_grace_until = (
        process_started_monotonic + low_level_startup_grace
    )
    dry_since: Optional[float] = None
    level_low_since: Optional[float] = None
    temp_failures = 0
    grow_pipe_temp_failures = 0
    previous_grow_pipe_fault = False
    temp_state = "NORMAL"
    flow_alarm = False
    low_level_alarm = False
    previous_override = override_switch.is_pressed
    previous_alarm: Optional[str] = None
    alarm_started_at = time.monotonic()
    previous_system_status: Optional[str] = None
    status_started_at = time.monotonic()
    previous_wet: Optional[bool] = None
    previous_level_ok: Optional[bool] = None
    last_csv = 0.0
    next_ambient_read = 0.0
    previous_low_notification = False
    previous_flow_notification = False
    previous_temp_notification_mode = "NORMAL"
    last_notification_reminder: dict[str, float] = {}

    logging.info("Hydro monitor v%s started", VERSION)
    discovered_ids = list_ds18b20_ids()
    logging.info("Discovered DS18B20 IDs: %s", discovered_ids or "NONE")
    logging.info(
        "Reservoir DS18B20: configured=%s file=%s",
        reservoir_sensor_id or "UNASSIGNED",
        reservoir_sensor_file if reservoir_sensor_file else "NOT FOUND/AMBIGUOUS",
    )
    logging.info(
        "Grow-pipe DS18B20: enabled=%s configured=%s file=%s (data-only)",
        grow_pipe_enabled,
        grow_pipe_sensor_id or "UNASSIGNED",
        grow_pipe_sensor_file if grow_pipe_sensor_file else "NOT FOUND/UNASSIGNED",
    )
    logging.info(
        "Water thresholds: warning %.1f°C, critical %.1f°C, clear below %.1f°C",
        warning_c,
        critical_c,
        clear_c,
    )
    logging.info(
        "DHT22 ambient readings are data-only and cannot activate alarms"
    )
    logging.info(
        "Phone notifications: enabled=%s configured=%s provider=pushover",
        notifier.enabled,
        notifier.configured,
    )
    if level_sensor is None:
        logging.info("Reservoir low-level monitoring is disabled")
    else:
        logging.info(
            "Reservoir low-level switch enabled on GPIO%d: %.0f-second delay, "
            "%.0f-second startup grace, normal contact %s",
            int(gpio["low_level_sensor"]),
            low_level_delay,
            low_level_startup_grace,
            "closed-to-ground" if normal_level_contact_closed else "open",
        )

    try:
        while RUNNING:
            loop_started = time.monotonic()
            override_active = override_switch.is_pressed
            override_led.value = override_active

            if previous_override and not override_active:
                grace_until = loop_started + startup_grace
                dry_since = None
                flow_alarm = False
                level_low_since = None
                low_level_alarm = False
                logging.info(
                    "Alarm override disabled; %.0f-second flow grace period started",
                    startup_grace,
                )
            elif not previous_override and override_active:
                dry_since = None
                flow_alarm = False
                level_low_since = None
                low_level_alarm = False
                logging.info("Alarm override enabled")
            previous_override = override_active

            raw_return = int(return_sensor.value)
            return_wet = raw_return == wet_level

            if previous_wet is None or return_wet != previous_wet:
                logging.info(
                    "Return sensor changed: raw=%d interpreted=%s",
                    raw_return,
                    "WET" if return_wet else "DRY",
                )
                previous_wet = return_wet

            if override_active:
                dry_since = None
                flow_alarm = False
            elif loop_started < grace_until:
                dry_since = None
                flow_alarm = False
            elif return_wet:
                dry_since = None
                flow_alarm = False
            else:
                if dry_since is None:
                    dry_since = loop_started
                flow_alarm = (loop_started - dry_since) >= dry_delay

            level_raw, reservoir_level_ok = read_low_level_state(
                level_sensor,
                normal_level_contact_closed,
            )

            if (
                reservoir_level_ok is not None
                and (
                    previous_level_ok is None
                    or reservoir_level_ok != previous_level_ok
                )
            ):
                logging.info(
                    "Reservoir level switch changed: electrical=%s interpreted=%s",
                    level_raw,
                    "OK" if reservoir_level_ok else "LOW",
                )
                previous_level_ok = reservoir_level_ok

            if level_sensor is None:
                level_low_since = None
                low_level_alarm = False
            elif override_active:
                level_low_since = None
                low_level_alarm = False
            elif loop_started < level_grace_until:
                level_low_since = None
                low_level_alarm = False
            elif reservoir_level_ok:
                level_low_since = None
                low_level_alarm = False
            else:
                if level_low_since is None:
                    level_low_since = loop_started
                low_level_alarm = (
                    loop_started - level_low_since
                ) >= low_level_delay

            reservoir_temp_c = read_ds18b20(reservoir_sensor_file)
            if reservoir_temp_c is None:
                temp_failures += 1
                if (
                    reservoir_sensor_file is None
                    or not reservoir_sensor_file.exists()
                ):
                    reservoir_sensor_file = find_ds18b20(reservoir_sensor_id)
            else:
                temp_failures = 0

            grow_pipe_temp_c: Optional[float] = None
            grow_pipe_configured = grow_pipe_enabled and bool(grow_pipe_sensor_id)
            if grow_pipe_configured:
                grow_pipe_temp_c = read_ds18b20(grow_pipe_sensor_file)
                if grow_pipe_temp_c is None:
                    grow_pipe_temp_failures += 1
                    if (
                        grow_pipe_sensor_file is None
                        or not grow_pipe_sensor_file.exists()
                    ):
                        grow_pipe_sensor_file = find_ds18b20(grow_pipe_sensor_id)
                else:
                    grow_pipe_temp_failures = 0
            else:
                grow_pipe_temp_failures = 0

            temp_sensor_fault = temp_failures >= max_temp_failures
            grow_pipe_temp_sensor_fault = (
                grow_pipe_configured
                and grow_pipe_temp_failures >= max_temp_failures
            )
            if grow_pipe_temp_sensor_fault != previous_grow_pipe_fault:
                if grow_pipe_temp_sensor_fault:
                    logging.warning(
                        "Grow-pipe DS18B20 has failed %d consecutive readings; "
                        "reservoir protection continues normally",
                        grow_pipe_temp_failures,
                    )
                else:
                    logging.info("Grow-pipe DS18B20 readings restored")
                previous_grow_pipe_fault = grow_pipe_temp_sensor_fault

            # Preserve the established reservoir alarm logic exactly.
            water_temp_c = reservoir_temp_c
            temp_state = update_temperature_state(
                temp_state,
                reservoir_temp_c,
                warning_c,
                critical_c,
                clear_c,
            )

            # Ambient DHT22 data collection is independent of all alarm logic.
            if loop_started >= next_ambient_read:
                read_ambient_sensor(ambient_state, ambient_cfg, loop_started)
                update_ambient_fault_logging(ambient_state, ambient_cfg)
                next_ambient_read = loop_started + ambient_read_interval

            alarm = select_alarm(
                override_active,
                low_level_alarm,
                flow_alarm,
                temp_state,
                temp_sensor_fault,
            )

            if alarm != previous_alarm:
                alarm_started_at = loop_started
                if alarm is None:
                    logging.info("Alarm cleared or inhibited")
                else:
                    logging.error("Alarm active: %s", alarm)
                previous_alarm = alarm

            flow_grace_active = (
                not override_active and loop_started < grace_until
            )
            level_grace_active = (
                level_sensor is not None
                and not override_active
                and loop_started < level_grace_until
            )
            grace_active = flow_grace_active or level_grace_active
            system_status = select_system_status(
                override_active=override_active,
                grace_active=grace_active,
                alarm=alarm,
                return_wet=return_wet,
                reservoir_level_ok=reservoir_level_ok,
                water_temp_valid=water_temp_c is not None,
                temp_state=temp_state,
                temp_sensor_fault=temp_sensor_fault,
            )

            if system_status != previous_system_status:
                status_started_at = loop_started
                logging.info("System status: %s", system_status)
                previous_system_status = system_status

            alarm_led.value = alarm is not None
            buzzer.value = buzzer_pattern(alarm, loop_started - alarm_started_at)
            status_led.value = status_led_pattern(
                system_status,
                loop_started - status_started_at,
            )

            (
                live_ambient_temp_c,
                live_ambient_rh,
                live_ambient_age_s,
                live_ambient_stale,
            ) = ambient_values_for_log(
                ambient_state,
                loop_started,
                ambient_max_stale,
            )
            live_delta_c: Optional[float] = None
            if reservoir_temp_c is not None and live_ambient_temp_c is not None:
                live_delta_c = live_ambient_temp_c - reservoir_temp_c
            live_grow_pipe_delta_c: Optional[float] = None
            if reservoir_temp_c is not None and grow_pipe_temp_c is not None:
                live_grow_pipe_delta_c = grow_pipe_temp_c - reservoir_temp_c

            now_wall = datetime.now().astimezone()

            # Pushover is an additional output only. The local LED/buzzer logic
            # above remains authoritative and continues if Internet access fails.
            if override_active:
                # Maintenance/refill override suppresses phone alerts and avoids
                # generating misleading "cleared" messages when alarms are hidden.
                previous_low_notification = False
                previous_flow_notification = False
                previous_temp_notification_mode = "NORMAL"
                last_notification_reminder.clear()
            else:
                title_prefix = str(
                    notification_cfg.get("title_prefix", "Strawberry Hydroponics")
                )

                def queue_event(event_name: str) -> None:
                    title, message = build_notification_message(
                        event_name,
                        now_wall,
                        water_temp_c,
                        return_wet,
                        reservoir_level_ok,
                        warning_c,
                        critical_c,
                        dry_delay,
                        low_level_delay,
                        temp_failures,
                        title_prefix,
                    )
                    if notifier.notify(event_name, title, message):
                        last_notification_reminder[event_name] = loop_started

                current_low_notification = bool(low_level_alarm)
                if current_low_notification and not previous_low_notification:
                    queue_event("LOW_WATER_ACTIVE")
                elif (
                    not current_low_notification
                    and previous_low_notification
                    and bool(notification_cfg.get("send_clear_messages", True))
                ):
                    queue_event("LOW_WATER_CLEARED")
                previous_low_notification = current_low_notification

                current_flow_notification = bool(flow_alarm)
                if current_flow_notification and not previous_flow_notification:
                    queue_event("FLOW_LOSS_ACTIVE")
                elif (
                    not current_flow_notification
                    and previous_flow_notification
                    and bool(notification_cfg.get("send_clear_messages", True))
                ):
                    queue_event("FLOW_RESTORED")
                previous_flow_notification = current_flow_notification

                current_temp_mode = temperature_notification_mode(
                    temp_state,
                    temp_sensor_fault,
                )
                temp_events = temperature_transition_events(
                    previous_temp_notification_mode,
                    current_temp_mode,
                )
                for event_name in temp_events:
                    if (
                        event_name in {
                            "TEMP_CRITICAL_EASED",
                            "TEMP_NORMAL",
                            "TEMP_SENSOR_RESTORED",
                        }
                        and not bool(notification_cfg.get("send_clear_messages", True))
                    ):
                        continue
                    queue_event(event_name)
                previous_temp_notification_mode = current_temp_mode

                if bool(notification_cfg.get("active_reminders_enabled", True)):
                    reminder_cfg = notification_cfg.get("reminder_minutes", {})
                    reminder_states = {
                        "LOW_WATER": current_low_notification,
                        "FLOW_LOSS": current_flow_notification,
                        "TEMP_CRITICAL": current_temp_mode == "CRITICAL",
                        "TEMP_SENSOR_FAULT": current_temp_mode == "SENSOR_FAULT",
                    }
                    reminder_events = {
                        "LOW_WATER": "LOW_WATER_REMINDER",
                        "FLOW_LOSS": "FLOW_LOSS_REMINDER",
                        "TEMP_CRITICAL": "TEMP_CRITICAL_REMINDER",
                        "TEMP_SENSOR_FAULT": "TEMP_SENSOR_FAULT_REMINDER",
                    }
                    active_events = {
                        "LOW_WATER": "LOW_WATER_ACTIVE",
                        "FLOW_LOSS": "FLOW_LOSS_ACTIVE",
                        "TEMP_CRITICAL": "TEMP_CRITICAL_ACTIVE",
                        "TEMP_SENSOR_FAULT": "TEMP_SENSOR_FAULT",
                    }
                    for condition, active in reminder_states.items():
                        if not active:
                            continue
                        minutes = float(reminder_cfg.get(condition, 0) or 0)
                        if minutes <= 0:
                            continue
                        initial_key = active_events[condition]
                        last_sent = max(
                            last_notification_reminder.get(initial_key, 0.0),
                            last_notification_reminder.get(
                                reminder_events[condition], 0.0
                            ),
                        )
                        if last_sent and loop_started - last_sent >= minutes * 60.0:
                            queue_event(reminder_events[condition])

            notification_snapshot = notifier.snapshot()
            write_json_atomic(
                current_status_path,
                {
                    "schema_version": 2,
                    "monitor_version": VERSION,
                    "updated_at": now_wall.isoformat(timespec="seconds"),
                    "monitor_started_at": process_started_at.isoformat(
                        timespec="seconds"
                    ),
                    "monitor_uptime_seconds": round(
                        loop_started - process_started_monotonic,
                        1,
                    ),
                    "system_status": system_status,
                    "status_message": (
                        {
                            "LOW_WATER": "Reservoir water level is low",
                            "FLOW_LOSS": "Return water has stopped",
                            "TEMP_CRITICAL": "Reservoir temperature is critical",
                            "TEMP_SENSOR_FAULT": "Reservoir temperature sensor fault",
                            "TEMP_WARNING": "Reservoir temperature warning",
                        }.get(alarm, "Active alarm")
                        if system_status == "ALARM"
                        else {
                            "HEALTHY": "System healthy",
                            "STARTING": "Startup or refill grace period",
                            "INHIBITED": "Alarms inhibited locally",
                            "CHECKING_LEVEL": (
                                "Reservoir level is low; confirmation delay active"
                            ),
                            "CHECKING_RETURN": (
                                "Return water not currently detected"
                            ),
                            "CHECKING_WATER_TEMP": (
                                "Waiting for reservoir temperature"
                            ),
                            "UNHEALTHY_TEMP": (
                                "Reservoir temperature outside normal state"
                            ),
                        }.get(system_status, system_status)
                    ),
                    "active_alarm": alarm,
                    "override_active": override_active,
                    "grace_active": grace_active,
                    "return_wet": return_wet,
                    "return_sensor_raw": raw_return,
                    "flow_alarm": flow_alarm,
                    "low_level_sensor_enabled": level_sensor is not None,
                    "low_level_sensor_raw": level_raw,
                    "reservoir_level_ok": reservoir_level_ok,
                    "reservoir_low": (
                        None
                        if reservoir_level_ok is None
                        else not reservoir_level_ok
                    ),
                    "low_level_alarm": low_level_alarm,
                    "low_level_grace_active": level_grace_active,
                    # water_temp_c remains as a compatibility alias for reservoir_temp_c.
                    "water_temp_c": reservoir_temp_c,
                    "reservoir_temp_c": reservoir_temp_c,
                    "reservoir_sensor_id": reservoir_sensor_id or None,
                    "reservoir_temperature_state": temp_state,
                    "temperature_state": temp_state,
                    "reservoir_temperature_sensor_fault": temp_sensor_fault,
                    "temperature_sensor_fault": temp_sensor_fault,
                    "reservoir_temperature_failures": temp_failures,
                    "grow_pipe_enabled": grow_pipe_enabled,
                    "grow_pipe_configured": grow_pipe_configured,
                    "grow_pipe_temp_c": grow_pipe_temp_c,
                    "grow_pipe_sensor_id": grow_pipe_sensor_id or None,
                    "grow_pipe_temperature_sensor_fault": grow_pipe_temp_sensor_fault,
                    "grow_pipe_temperature_failures": grow_pipe_temp_failures,
                    "grow_pipe_minus_reservoir_c": live_grow_pipe_delta_c,
                    "grow_pipe_alarm_enabled": False,
                    "ambient_temp_c": live_ambient_temp_c,
                    "ambient_rh_percent": live_ambient_rh,
                    "ambient_sample_age_seconds": live_ambient_age_s,
                    "ambient_data_stale": live_ambient_stale,
                    "ambient_last_attempt_ok": ambient_state.last_attempt_ok,
                    "ambient_consecutive_failures": (
                        ambient_state.consecutive_failures
                    ),
                    "air_minus_water_c": live_delta_c,
                    "pi_cpu_temp_c": read_cpu_temp(),
                    "notifications": notification_snapshot,
                    "outputs": {
                        "green_led_on": bool(status_led.value),
                        "amber_led_on": bool(override_led.value),
                        "red_led_on": bool(alarm_led.value),
                        "buzzer_on": bool(buzzer.value),
                    },
                },
            )

            if loop_started - last_csv >= log_interval:
                (
                    ambient_temp_c,
                    ambient_rh,
                    ambient_age_s,
                    ambient_stale,
                ) = ambient_values_for_log(
                    ambient_state,
                    loop_started,
                    ambient_max_stale,
                )

                delta_c: Optional[float] = None
                if reservoir_temp_c is not None and ambient_temp_c is not None:
                    delta_c = ambient_temp_c - reservoir_temp_c
                grow_pipe_delta_c: Optional[float] = None
                if reservoir_temp_c is not None and grow_pipe_temp_c is not None:
                    grow_pipe_delta_c = grow_pipe_temp_c - reservoir_temp_c

                cpu_temp = read_cpu_temp()

                append_csv(
                    csv_path,
                    {
                        "timestamp": datetime.now().astimezone().isoformat(
                            timespec="seconds"
                        ),
                        # Preserve the legacy water_temp_c compatibility column as the reservoir value.
                        "water_temp_c": (
                            "" if reservoir_temp_c is None else f"{reservoir_temp_c:.3f}"
                        ),
                        "reservoir_temp_c": (
                            "" if reservoir_temp_c is None else f"{reservoir_temp_c:.3f}"
                        ),
                        "grow_pipe_temp_c": (
                            "" if grow_pipe_temp_c is None else f"{grow_pipe_temp_c:.3f}"
                        ),
                        "grow_pipe_minus_reservoir_c": (
                            "" if grow_pipe_delta_c is None else f"{grow_pipe_delta_c:.3f}"
                        ),
                        "reservoir_temp_sensor_fault": int(temp_sensor_fault),
                        "grow_pipe_temp_sensor_fault": int(
                            grow_pipe_temp_sensor_fault
                        ),
                        "ambient_temp_c": (
                            "" if ambient_temp_c is None else f"{ambient_temp_c:.2f}"
                        ),
                        "ambient_rh_percent": (
                            "" if ambient_rh is None else f"{ambient_rh:.2f}"
                        ),
                        "air_minus_water_c": (
                            "" if delta_c is None else f"{delta_c:.2f}"
                        ),
                        "ambient_last_attempt_ok": int(
                            ambient_state.last_attempt_ok
                        ),
                        "ambient_sample_age_s": (
                            "" if ambient_age_s is None else f"{ambient_age_s:.1f}"
                        ),
                        "ambient_data_stale": int(ambient_stale),
                        "ambient_consecutive_failures": (
                            ambient_state.consecutive_failures
                        ),
                        "return_sensor_raw": raw_return,
                        "return_wet": int(return_wet),
                        "low_level_sensor_enabled": int(
                            level_sensor is not None
                        ),
                        "low_level_sensor_raw": (
                            "" if level_raw is None else level_raw
                        ),
                        "reservoir_level_ok": (
                            ""
                            if reservoir_level_ok is None
                            else int(reservoir_level_ok)
                        ),
                        "low_level_alarm": int(low_level_alarm),
                        "override_active": int(override_active),
                        "flow_alarm": int(flow_alarm),
                        "temp_state": temp_state,
                        "temp_sensor_fault": int(temp_sensor_fault),
                        "active_alarm": alarm or "",
                        "system_status": system_status,
                        "green_status_led_on": int(status_led.value),
                        "pi_cpu_temp_c": (
                            "" if cpu_temp is None else f"{cpu_temp:.1f}"
                        ),
                    },
                )
                last_csv = loop_started

            elapsed = time.monotonic() - loop_started
            time.sleep(max(0.05, sample_interval - elapsed))

    finally:
        buzzer.off()
        override_led.off()
        alarm_led.off()
        status_led.off()
        close_ambient_sensor(ambient_state)
        return_sensor.close()
        if level_sensor is not None:
            level_sensor.close()
        override_switch.close()
        buzzer.close()
        override_led.close()
        alarm_led.close()
        status_led.close()
        notifier.stop()
        logging.info("Hydro monitor stopped")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
