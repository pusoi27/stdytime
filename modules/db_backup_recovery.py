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
from typing import Iterable, Iterator

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


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    if not rows:
        raise ValueError(f"Table not found: {table_name}")
    return [row[1] for row in rows]


def restore_tenant_rows(backup_path: str, owner_user_id: int, table_names: Iterable[str]) -> dict[str, int]:
    """Restore only one tenant's rows for the specified tables from a backup.

    This prevents one user's rollback from rewinding other users' data.
    Tables must contain an owner_user_id column.
    Returns a mapping of table name -> restored row count.
    """
    if not backup_path or not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup not found: {backup_path}")

    restored_counts: dict[str, int] = {}
    unique_tables = list(dict.fromkeys(table_names or []))
    if not unique_tables:
        return restored_counts

    with sqlite3.connect(DB_PATH) as live_conn, sqlite3.connect(backup_path) as backup_conn:
        live_conn.execute("PRAGMA foreign_keys = OFF")
        backup_conn.row_factory = sqlite3.Row
        try:
            live_conn.execute("BEGIN IMMEDIATE")
            for table_name in unique_tables:
                live_columns = _table_columns(live_conn, table_name)
                backup_columns = _table_columns(backup_conn, table_name)
                if "owner_user_id" not in live_columns or "owner_user_id" not in backup_columns:
                    raise ValueError(f"Table {table_name} does not support tenant-scoped restore")

                column_names = [col for col in live_columns if col in backup_columns]
                quoted_columns = ", ".join(column_names)
                placeholders = ", ".join("?" for _ in column_names)

                live_conn.execute(f"DELETE FROM {table_name} WHERE owner_user_id = ?", (owner_user_id,))
                rows = backup_conn.execute(
                    f"SELECT {quoted_columns} FROM {table_name} WHERE owner_user_id = ?",
                    (owner_user_id,),
                ).fetchall()

                if rows:
                    live_conn.executemany(
                        f"INSERT INTO {table_name} ({quoted_columns}) VALUES ({placeholders})",
                        [tuple(row[col] for col in column_names) for row in rows],
                    )
                restored_counts[table_name] = len(rows)
            live_conn.commit()
        except Exception:
            live_conn.rollback()
            raise
        finally:
            live_conn.execute("PRAGMA foreign_keys = ON")

    _logger.warning(
        "[backup] tenant restore from %s for owner_user_id=%s tables=%s",
        backup_path,
        owner_user_id,
        unique_tables,
    )
    return restored_counts


def restore_tenant_from_backup(backup_path: str, owner_user_id: int, *table_names: str) -> dict[str, int]:
    """Convenience wrapper for tenant-scoped restore using positional table names."""
    return restore_tenant_rows(backup_path, owner_user_id, table_names)


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
