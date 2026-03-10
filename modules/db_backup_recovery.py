"""SQLite backup + recovery helpers for high-risk write operations.

This module creates point-in-time SQLite backups before bulk/sync writes,
and can restore from that backup if an operation fails.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

from modules.database import DB_PATH

_logger = logging.getLogger("db_backup_recovery")
BACKUP_DIR = os.path.join("data", "backups")


def _sanitize_label(label: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in (label or "operation"))
    return cleaned.strip("_") or "operation"


def create_backup(label: str) -> str:
    """Create a full SQLite backup and return the backup file path."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    safe_label = _sanitize_label(label)
    backup_path = os.path.join(BACKUP_DIR, f"{safe_label}_{ts}.db")

    with sqlite3.connect(DB_PATH) as src, sqlite3.connect(backup_path) as dst:
        src.backup(dst)

    _logger.info("[backup] created %s", backup_path)
    return backup_path


def restore_backup(backup_path: str) -> None:
    """Restore the main database from a backup file."""
    if not backup_path or not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    with sqlite3.connect(backup_path) as src, sqlite3.connect(DB_PATH) as dst:
        src.backup(dst)

    _logger.warning("[backup] restored from %s", backup_path)


@contextmanager
def backup_guard(label: str) -> Iterator[str]:
    """Context manager: create backup, auto-restore on exception.

    Usage:
        with backup_guard("students_import") as backup_path:
            ... risky writes ...
    """
    backup_path = create_backup(label)
    try:
        yield backup_path
    except Exception:
        restore_backup(backup_path)
        raise
