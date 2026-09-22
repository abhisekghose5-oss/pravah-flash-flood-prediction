"""
PRAVAH — Database Migration Runner & Version Tracking System.
Provides safe, additive schema migrations and reversible down-migrations
for local SQLite persistence.
"""

from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Dict, List
import sqlite3

from src.data.db import get_connection

logger = logging.getLogger("pravah.data.migrations")
REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations"


def init_migration_table(conn: sqlite3.Connection) -> None:
    """Ensure migration tracking table exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT UNIQUE NOT NULL,
            description TEXT NOT NULL,
            applied_at TEXT NOT NULL
        );
    """)
    conn.commit()


def get_applied_migrations(conn: sqlite3.Connection) -> List[str]:
    """Retrieve list of already applied migration versions."""
    init_migration_table(conn)
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations ORDER BY id ASC;")
    return [row[0] for row in cursor.fetchall()]


def apply_migrations() -> List[str]:
    """
    Apply any pending SQL migrations in alphabetical order.
    Returns list of newly applied migration versions.
    """
    applied = []
    with get_connection() as conn:
        init_migration_table(conn)
        already_applied = set(get_applied_migrations(conn))

        if not MIGRATIONS_DIR.exists():
            logger.warning("Migrations directory not found at %s", MIGRATIONS_DIR)
            return applied

        migration_files = sorted(
            [f for f in MIGRATIONS_DIR.glob("*.sql") if not f.name.endswith("_rollback.sql")]
        )

        for m_file in migration_files:
            version = m_file.stem
            if version in already_applied:
                continue

            logger.info("Applying migration: %s", m_file.name)
            with open(m_file, "r", encoding="utf-8") as f:
                sql_content = f.read()

            conn.executescript(sql_content)
            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO schema_migrations (version, description, applied_at) VALUES (?, ?, ?);",
                (version, f"Migration {m_file.name}", now),
            )
            conn.commit()
            applied.append(version)
            logger.info("Successfully applied migration %s", version)

    return applied


def rollback_migration(version: str) -> bool:
    """
    Roll back a specific migration version if a rollback script exists.
    """
    rollback_file = MIGRATIONS_DIR / f"{version}_rollback.sql"
    if not rollback_file.exists():
        logger.error("No rollback script found for version %s", version)
        return False

    with get_connection() as conn:
        with open(rollback_file, "r", encoding="utf-8") as f:
            sql_content = f.read()

        conn.executescript(sql_content)
        conn.execute("DELETE FROM schema_migrations WHERE version = ?;", (version,))
        conn.commit()
        logger.info("Successfully rolled back migration %s", version)

    return True


def get_migration_status() -> Dict[str, Any]:
    """Retrieve full diagnostic status of all schema migrations."""
    with get_connection() as conn:
        applied = get_applied_migrations(conn)

    available = []
    if MIGRATIONS_DIR.exists():
        available = [
            f.stem for f in sorted(MIGRATIONS_DIR.glob("*.sql"))
            if not f.name.endswith("_rollback.sql")
        ]

    return {
        "applied_count": len(applied),
        "applied_versions": applied,
        "available_versions": available,
        "pending_versions": [v for v in available if v not in applied],
        "status": "UP_TO_DATE" if len(applied) == len(available) else "PENDING_MIGRATIONS",
    }
