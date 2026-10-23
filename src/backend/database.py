import json
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS politician_positions (
                    deputy_id INTEGER PRIMARY KEY,
                    first_last_name TEXT NOT NULL,
                    club TEXT NOT NULL,
                    club_display_name TEXT NOT NULL,
                    photo_url TEXT NOT NULL,
                    axis_x REAL NOT NULL,
                    axis_y REAL NOT NULL,
                    axis_label TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    economic_description TEXT NOT NULL,
                    worldview_description TEXT NOT NULL,
                    voting_details_json TEXT NOT NULL,
                    calculated_at TEXT NOT NULL
                )
                """)
    finally:
        conn.close()


def save_politician_positions(
    positions: list[dict[str, Any]], custom_path: str | Path | None = None
) -> None:
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    conn = sqlite3.connect(db_file)
    try:
        with conn:
            cursor = conn.cursor()
            cursor.executemany(
                """
                INSERT OR REPLACE INTO politician_positions (
                    deputy_id, first_last_name, club, club_display_name, photo_url,
                    axis_x, axis_y, axis_label, summary,
                    economic_description, worldview_description,
                    voting_details_json, calculated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        p["deputy_id"],
                        p["first_last_name"],
                        p["club"],
                        p["club_display_name"],
                        p["photo_url"],
                        float(p["axis_x"]),
                        float(p["axis_y"]),
                        p["axis_label"],
                        p["summary"],
                        p.get("economic_description", ""),
                        p.get("worldview_description", ""),
                        json.dumps(p.get("voting_details", []), ensure_ascii=False)
                        if isinstance(p.get("voting_details"), list)
                        else p.get("voting_details_json", "[]"),
                        p["calculated_at"],
                    )
                    for p in positions
                ],
            )
    finally:
        conn.close()


def get_all_politician_positions(
    custom_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    conn = sqlite3.connect(db_file)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT deputy_id, first_last_name, club, club_display_name, photo_url,
                   axis_x, axis_y, axis_label, summary,
                   economic_description, worldview_description,
                   voting_details_json, calculated_at
            FROM politician_positions
            ORDER BY first_last_name ASC
            """
        )
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d["voting_details"] = json.loads(d.pop("voting_details_json"))
            except Exception:
                d["voting_details"] = []
            result.append(d)
        return result
    finally:
        conn.close()


def get_politician_position_by_id(
    deputy_id: int, custom_path: str | Path | None = None
) -> dict[str, Any] | None:
    init_db(custom_path)
    db_file = get_db_path(custom_path)

    conn = sqlite3.connect(db_file)
    try:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT deputy_id, first_last_name, club, club_display_name, photo_url,
                   axis_x, axis_y, axis_label, summary,
                   economic_description, worldview_description,
                   voting_details_json, calculated_at
            FROM politician_positions
            WHERE deputy_id = ?
            """,
            (deputy_id,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["voting_details"] = json.loads(d.pop("voting_details_json"))
        except Exception:
            d["voting_details"] = []
        return d
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
