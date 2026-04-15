"""
Version bump utility for Stdytime.

Increments the patch segment of the VERSION file (xx.xx.xx -> xx.xx.(xx+1)),
preserving zero-padding width of each segment.

Usage:
  python scripts/version_bump.py [optional_path_to_VERSION]
"""
from __future__ import annotations
import os
import re
import sys

DEFAULT_VERSION = "00.00.01"

def find_version_path(arg_path: str | None = None) -> str:
    if arg_path:
        return os.path.abspath(arg_path)
    # VERSION is at project root (parent of scripts/)
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    return os.path.join(root, "VERSION")


def read_version(vpath: str) -> tuple[str, list[str]]:
    if not os.path.exists(vpath):
        return DEFAULT_VERSION, DEFAULT_VERSION.split('.')
    try:
        with open(vpath, 'r', encoding='utf-8') as f:
            raw = (f.read().strip() or DEFAULT_VERSION)
    except Exception:
        return DEFAULT_VERSION, DEFAULT_VERSION.split('.')

    # Expect pattern like 06.07.08 (digits with dots)
    if not re.match(r"^\d+\.\d+\.\d+$", raw):
        return DEFAULT_VERSION, DEFAULT_VERSION.split('.')
    return raw, raw.split('.')


def bump_patch(parts: list[str]) -> list[str]:
    # Preserve zero-padding widths per segment
    widths = [len(p) for p in parts]
    try:
        major = int(parts[0])
        minor = int(parts[1])
        patch = int(parts[2]) + 1
    except ValueError:
        major, minor, patch = 0, 0, 1

    return [
        str(major).zfill(widths[0]),
        str(minor).zfill(widths[1]),
        str(patch).zfill(widths[2]),
    ]


def write_version(vpath: str, new_version: str) -> None:
    with open(vpath, 'w', encoding='utf-8') as f:
        f.write(new_version)


def main(argv: list[str]) -> int:
    vpath = find_version_path(argv[1] if len(argv) > 1 else None)
    old_raw, parts = read_version(vpath)
    new_parts = bump_patch(parts)
    new_raw = '.'.join(new_parts)
    write_version(vpath, new_raw)
    print(f"Version bumped: {old_raw} -> {new_raw}\nPath: {vpath}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
