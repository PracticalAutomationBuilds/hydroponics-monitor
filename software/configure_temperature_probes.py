#!/usr/bin/env python3
"""Discover and assign the two DS18B20 probes used by Hydro Monitor."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG = Path("/opt/hydro-monitor/config.json")
DEFAULT_W1_ROOT = Path("/sys/bus/w1/devices")


def list_ids(root: Path) -> list[str]:
    return sorted(path.name for path in root.glob("28-*") if path.is_dir())


def read_temperature(root: Path, sensor_id: str) -> Optional[float]:
    sensor_file = root / sensor_id / "w1_slave"
    try:
        lines = sensor_file.read_text(encoding="utf-8").strip().splitlines()
    except OSError:
        return None
    if len(lines) < 2 or not lines[0].strip().endswith("YES"):
        return None
    marker = "t="
    index = lines[1].find(marker)
    if index < 0:
        return None
    try:
        value = float(lines[1][index + len(marker):]) / 1000.0
    except ValueError:
        return None
    return value if -10.0 <= value <= 60.0 else None


def print_devices(root: Path, ids: list[str]) -> None:
    if not ids:
        print("No DS18B20 devices were found.")
        print("Confirm 1-Wire is enabled, rebooted, and the probes are wired correctly.")
        return
    print("Discovered DS18B20 probes:")
    for index, sensor_id in enumerate(ids, start=1):
        value = read_temperature(root, sensor_id)
        shown = "no valid reading" if value is None else f"{value:.3f} °C"
        print(f"  {index}. {sensor_id}  ({shown})")


def select_id(label: str, ids: list[str], current: str) -> str:
    current_text = current or "not assigned"
    prompt = (
        f"Select {label} probe [1-{len(ids)}], Enter to keep {current_text}, "
        "or 0 to clear: "
    )
    while True:
        answer = input(prompt).strip()
        if not answer:
            return current
        if answer == "0":
            return ""
        try:
            choice = int(answer)
        except ValueError:
            print("Enter a listed number, 0, or press Enter.")
            continue
        if 1 <= choice <= len(ids):
            return ids[choice - 1]
        print("That number is not in the list.")


def write_config(config_path: Path, config: dict) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"{config_path.name}.before-probe-setup-{stamp}.bak")
    shutil.copy2(config_path, backup)
    temporary = config_path.with_suffix(config_path.suffix + ".tmp")
    temporary.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    temporary.replace(config_path)
    return backup


def restart_monitor() -> None:
    result = subprocess.run(
        ["systemctl", "restart", "hydro-monitor.service"],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(detail or "systemctl restart failed")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List DS18B20 hardware IDs and assign them to reservoir and grow-pipe roles."
        )
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--w1-root", type=Path, default=DEFAULT_W1_ROOT)
    parser.add_argument("--list", action="store_true", help="List probes and exit")
    parser.add_argument(
        "--watch",
        type=int,
        metavar="SECONDS",
        help="Show repeated readings to help identify a probe by warming it gently",
    )
    parser.add_argument("--reservoir", metavar="28-ID")
    parser.add_argument("--grow-pipe", metavar="28-ID")
    parser.add_argument("--disable-grow-pipe", action="store_true")
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()

    ids = list_ids(args.w1_root)
    print_devices(args.w1_root, ids)

    if args.watch:
        if not ids:
            return 1
        deadline = time.monotonic() + max(1, args.watch)
        print("\nWatching temperatures. Press Ctrl+C to stop early.")
        try:
            while time.monotonic() < deadline:
                parts = []
                for sensor_id in ids:
                    value = read_temperature(args.w1_root, sensor_id)
                    shown = "—" if value is None else f"{value:.3f} °C"
                    parts.append(f"{sensor_id}: {shown}")
                print(" | ".join(parts), flush=True)
                time.sleep(2)
        except KeyboardInterrupt:
            pass
        if args.list and not any(
            [args.reservoir, args.grow_pipe, args.disable_grow_pipe]
        ):
            return 0

    if args.list and not any(
        [args.reservoir, args.grow_pipe, args.disable_grow_pipe]
    ):
        return 0 if ids else 1

    if not args.config.exists():
        print(f"Configuration file not found: {args.config}", file=sys.stderr)
        return 1
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Unable to read configuration: {exc}", file=sys.stderr)
        return 1

    temperature = config.setdefault("temperature", {})
    current_reservoir = str(temperature.get("reservoir_sensor_id", "")).strip()
    current_grow = str(temperature.get("grow_pipe_sensor_id", "")).strip()

    if args.reservoir is not None:
        reservoir = args.reservoir.strip()
    elif ids:
        reservoir = select_id("reservoir", ids, current_reservoir)
    else:
        reservoir = current_reservoir

    if args.disable_grow_pipe:
        grow_enabled = False
        grow_pipe = ""
    else:
        grow_enabled = True
        if args.grow_pipe is not None:
            grow_pipe = args.grow_pipe.strip()
        elif ids:
            grow_pipe = select_id("grow-pipe", ids, current_grow)
        else:
            grow_pipe = current_grow

    if not reservoir:
        print("A reservoir probe ID must be assigned before the monitor can start.", file=sys.stderr)
        return 1
    if grow_enabled and not grow_pipe:
        print(
            "A grow-pipe probe ID must be assigned while grow-pipe monitoring is enabled.",
            file=sys.stderr,
        )
        return 1

    for label, sensor_id in (("reservoir", reservoir), ("grow-pipe", grow_pipe)):
        if sensor_id and (
            not sensor_id.startswith("28-") or "/" in sensor_id or "\\" in sensor_id
        ):
            print(f"Invalid {label} sensor ID: {sensor_id}", file=sys.stderr)
            return 1
        if sensor_id and sensor_id not in ids:
            print(
                f"Warning: {label} ID {sensor_id} is not currently discovered.",
                file=sys.stderr,
            )
    if grow_enabled and reservoir == grow_pipe:
        print("The reservoir and grow-pipe roles cannot use the same sensor ID.", file=sys.stderr)
        return 1

    temperature["reservoir_sensor_id"] = reservoir
    temperature["grow_pipe_enabled"] = grow_enabled
    temperature["grow_pipe_sensor_id"] = grow_pipe
    temperature["grow_pipe_alarm_enabled"] = False

    try:
        backup = write_config(args.config, config)
    except OSError as exc:
        print(f"Unable to update configuration: {exc}", file=sys.stderr)
        return 1

    print(f"\nUpdated: {args.config}")
    print(f"Backup:  {backup}")
    print(f"Reservoir probe: {reservoir or 'NOT ASSIGNED'}")
    print(
        "Grow-pipe probe: "
        + ("DISABLED" if not grow_enabled else (grow_pipe or "NOT ASSIGNED"))
    )
    print("Grow-pipe temperature remains display-and-log only; no alarm thresholds are enabled.")

    if args.restart:
        try:
            restart_monitor()
        except RuntimeError as exc:
            print(f"Configuration saved, but restart failed: {exc}", file=sys.stderr)
            return 1
        print("hydro-monitor.service restarted.")
    else:
        print("Run the hardware self-test before enabling the services:")
        print("  /opt/hydro-monitor/venv/bin/python /opt/hydro-monitor/hydro_monitor.py --config /opt/hydro-monitor/config.json --test")
        print("Then enable and start the monitor and dashboard:")
        print("  sudo systemctl enable --now hydro-monitor.service hydro-dashboard.service")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
