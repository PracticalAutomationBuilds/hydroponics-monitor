#!/usr/bin/env python3
"""Safely configure or test Pushover for Hydro Monitor."""

from __future__ import annotations

import argparse
import getpass
import grp
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

from hydro_version import VERSION

VALIDATE_URL = "https://api.pushover.net/1/users/validate.json"
MESSAGE_URL = "https://api.pushover.net/1/messages.json"
DEFAULT_CONFIG = Path("/opt/hydro-monitor/config.json")
DEFAULT_SECRETS = Path("/etc/hydro-monitor/pushover.json")
SECRETS_GROUP = "hydro-monitor-secrets"


def post_json(url: str, payload: dict, timeout: float = 10.0) -> dict:
    data = urllib_parse.urlencode(payload).encode("utf-8")
    request = urllib_request.Request(
        url,
        data=data,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib_request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            result = json.loads(body)
            errors = result.get("errors") or []
            raise RuntimeError("; ".join(str(x) for x in errors) or str(exc))
        except json.JSONDecodeError:
            raise RuntimeError(str(exc)) from exc
    except (urllib_error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"Network error: {exc}") from exc
    try:
        result = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Pushover returned invalid JSON") from exc
    if int(result.get("status", 0)) != 1:
        errors = result.get("errors") or ["Pushover rejected the request"]
        raise RuntimeError("; ".join(str(x) for x in errors))
    return result


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} does not contain a JSON object")
    return value


def atomic_write_json(path: Path, value: dict, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temp.replace(path)
    if mode is not None:
        os.chmod(path, mode)


def set_enabled(config_path: Path, enabled: bool) -> None:
    config = load_json(config_path)
    notifications = config.setdefault("notifications", {})
    notifications["enabled"] = enabled
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"{config_path.name}.pre-pushover-{stamp}")
    shutil.copy2(config_path, backup)
    atomic_write_json(config_path, config)
    print(f"Configuration backup: {backup}")


def restart_services(no_restart: bool) -> None:
    if no_restart:
        print("Services not restarted. Restart them later with:")
        print("  sudo systemctl restart hydro-monitor.service hydro-dashboard.service")
        return
    subprocess.run(
        ["systemctl", "restart", "hydro-monitor.service", "hydro-dashboard.service"],
        check=True,
    )
    print("Hydro monitor and dashboard services restarted.")


def send_test(secrets: dict, title_prefix: str = "Strawberry Hydroponics") -> None:
    payload = {
        "token": secrets["api_token"],
        "user": secrets["user_key"],
        "title": f"{title_prefix}: Pushover test",
        "message": (
            f"Hydro Monitor v{VERSION} can send phone notifications.\n\n"
            "This is a setup test; no hydroponic alarm is active."
        ),
        "priority": 0,
        "sound": "pushover",
    }
    device = str(secrets.get("device", "")).strip()
    if device:
        payload["device"] = device
    result = post_json(MESSAGE_URL, payload)
    print(f"Test notification queued. Request ID: {result.get('request', 'not supplied')}")


def require_root() -> None:
    if os.geteuid() != 0:
        raise SystemExit("Run with sudo: sudo /opt/hydro-monitor/configure_pushover.py")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--secrets", type=Path, default=DEFAULT_SECRETS)
    parser.add_argument("--test-only", action="store_true")
    parser.add_argument("--disable", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    require_root()
    config = load_json(args.config)
    notification_cfg = config.get("notifications", {})

    if args.status:
        secrets = {}
        if args.secrets.exists():
            try:
                secrets = load_json(args.secrets)
            except Exception:
                pass
        print(f"Enabled: {bool(notification_cfg.get('enabled', False))}")
        print(f"Credentials file: {args.secrets}")
        print(f"Credentials present: {bool(secrets.get('user_key') and secrets.get('api_token'))}")
        print("Credentials are not displayed.")
        return 0

    if args.disable:
        set_enabled(args.config, False)
        restart_services(args.no_restart)
        print("Pushover disabled. Local LED and buzzer alarms remain active.")
        return 0

    if args.test_only:
        secrets = load_json(args.secrets)
        send_test(secrets, str(notification_cfg.get("title_prefix", "Strawberry Hydroponics")))
        return 0

    print("Pushover Hydro Monitor setup")
    print("Keys are entered invisibly and are not stored in shell history.")
    user_key = getpass.getpass("Pushover User Key: ").strip()
    api_token = getpass.getpass("Hydro Monitor Application API Token: ").strip()
    device = input("Optional Pushover device name (Enter for all devices): ").strip()

    if len(user_key) != 30 or not user_key.isalnum():
        raise SystemExit("User Key should be a 30-character, case-sensitive alphanumeric value.")
    if len(api_token) != 30 or not api_token.isalnum():
        raise SystemExit("Application API Token should be a 30-character alphanumeric value.")

    validate_payload = {"token": api_token, "user": user_key}
    if device:
        validate_payload["device"] = device
    result = post_json(VALIDATE_URL, validate_payload)
    print("Pushover account/device validation passed.")
    devices = result.get("devices") or []
    if devices:
        print("Active devices: " + ", ".join(str(x) for x in devices))

    secrets = {
        "user_key": user_key,
        "api_token": api_token,
        "device": device,
    }
    atomic_write_json(args.secrets, secrets, mode=0o640)
    try:
        group = grp.getgrnam(SECRETS_GROUP)
        os.chown(args.secrets, 0, group.gr_gid)
    except KeyError:
        raise SystemExit(
            f"Required group {SECRETS_GROUP!r} is missing. Re-run the Hydro Monitor installer."
        )

    set_enabled(args.config, True)
    send_test(secrets, str(notification_cfg.get("title_prefix", "Strawberry Hydroponics")))
    restart_services(args.no_restart)
    print("Pushover is enabled. The local alarms remain independent.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
