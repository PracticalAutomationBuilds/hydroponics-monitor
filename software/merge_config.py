#!/usr/bin/env python3
"""Merge an existing Hydro Monitor config onto current release defaults safely."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import tempfile
from typing import Any


AUTHORITATIVE_GPIO = {
    "return_sensor": 24,
    "override_switch": 18,
    "buzzer": 12,
    "override_led": 20,
    "alarm_led": 26,
    "status_led": 21,
    "low_level_sensor": 17,
}


def recursive_merge(base: Any, overlay: Any) -> Any:
    """Overlay user configuration while retaining new default keys."""
    if isinstance(base, dict) and isinstance(overlay, dict):
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            if key in result:
                result[key] = recursive_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
    return copy.deepcopy(overlay)


def enforce_hardware_assignments(config: dict[str, Any]) -> dict[str, Any]:
    """Keep fixed permanent-board GPIO assignments authoritative across upgrades."""
    config["gpio"] = copy.deepcopy(AUTHORITATIVE_GPIO)
    config.setdefault("ambient", {})["gpio"] = 22
    config.setdefault("rtc", {})["sda_gpio"] = 2
    config.setdefault("rtc", {})["scl_gpio"] = 3
    return config


def load_json_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Configuration root must be a JSON object: {path}")
    return payload


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def build_merged_config(defaults_path: Path, existing_path: Path | None) -> dict[str, Any]:
    defaults = load_json_object(defaults_path)
    merged = defaults
    if existing_path is not None:
        existing = load_json_object(existing_path)
        merged = recursive_merge(defaults, existing)
    return enforce_hardware_assignments(merged)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--defaults", type=Path, required=True)
    parser.add_argument("--existing", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    merged = build_merged_config(args.defaults, args.existing)
    write_json_atomic(args.output, merged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
