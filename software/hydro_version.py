#!/usr/bin/env python3
"""Single source of truth for the installed Hydro Monitor release version."""

from __future__ import annotations

from pathlib import Path
import re

_VERSION_PATTERN = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?"
    r"(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)


def read_version(base_dir: Path | None = None) -> str:
    """Read and validate VERSION beside the installed/project source files."""
    root = base_dir if base_dir is not None else Path(__file__).resolve().parent
    path = root / "VERSION"
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise RuntimeError(f"Unable to read release version from {path}: {exc}") from exc
    if not _VERSION_PATTERN.fullmatch(value):
        raise RuntimeError(f"Invalid Semantic Version in {path}: {value!r}")
    return value


VERSION = read_version()
