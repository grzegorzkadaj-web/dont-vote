import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.config import settings


def get_db_path(custom_path: str | Path | None = None) -> Path:
    target_path = Path(custom_path) if custom_path else Path(settings.contact_db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    return target_path


def init_db(custom_path: str | Path | None = None) -> None:
    db_file = get_db_path(custom_path)
    conn = sqlite3.connect(db_file)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS contact_submissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    email TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    rodo_consent INTEGER NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT
                )
                """)
    finally:
        conn.close()


def save_contact_submission(
    email: str,
    category: str,
    message: str,
    rodo_consent: bool,
    ip_address: str | None = None,
    user_agent: str | None = None,
    custom_path: str | Path | None = None,
) -> int:
    init_db(custom_path)
    db_file = get_db_path(custom_path)
    created_at = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(db_file)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO contact_submissions (
                    created_at, email, category, message, rodo_consent, ip_address, user_agent
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    email.strip(),
                    category.strip(),
                    message.strip(),
                    1 if rodo_consent else 0,
                    ip_address,
                    user_agent,
                ),
            )
            return int(cursor.lastrowid)
    finally:
        conn.close()


def get_contact_submissions(
    limit: int = 50, custom_path: str | Path | None = None
) -> list[dict[str, Any]]:
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    conn = sqlite3.connect(db_file)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, created_at, email, category, message, rodo_consent, ip_address, user_agent
            FROM contact_submissions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
