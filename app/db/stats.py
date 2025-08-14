# app/db/stats.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Literal, Optional

_DB_PATH: Optional[Path] = None

def _connect() -> sqlite3.Connection:
    if _DB_PATH is None:
        raise RuntimeError("stats DB is not initialized. Call stats_db.init(db_path) first.")
    conn = sqlite3.connect(_DB_PATH.as_posix(), timeout=10, check_same_thread=False)
    # Бонус к устойчивости при параллельных апдейтах
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init(db_path: str) -> None:
    """Инициализирует файл БД и таблицу статистики."""
    global _DB_PATH
    _DB_PATH = Path(db_path)
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_stats (
                user_id INTEGER PRIMARY KEY,
                outputs_count INTEGER NOT NULL DEFAULT 0,
                settings_changes_count INTEGER NOT NULL DEFAULT 0,
                first_seen TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_seen  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

def _ensure_user_row(conn: sqlite3.Connection, user_id: int) -> None:
    conn.execute("""
        INSERT INTO user_stats (user_id) VALUES (?)
        ON CONFLICT(user_id) DO NOTHING;
    """, (user_id,))

def _incr(conn: sqlite3.Connection, user_id: int, column: Literal["outputs_count","settings_changes_count"], delta: int = 1) -> None:
    _ensure_user_row(conn, user_id)
    conn.execute(f"""
        UPDATE user_stats
           SET {column} = {column} + ?,
               last_seen = CURRENT_TIMESTAMP
         WHERE user_id = ?;
    """, (delta, user_id))

def record_output(user_id: int, delta: int = 1) -> None:
    """Вызывать после отправки финального файла (после выбора формата)."""
    with _connect() as conn:
        _incr(conn, user_id, "outputs_count", delta)
        conn.commit()

def record_setting_change(user_id: int, delta: int = 1) -> None:
    """Вызывать при любом изменении параметров/настройки."""
    with _connect() as conn:
        _incr(conn, user_id, "settings_changes_count", delta)
        conn.commit()

def get_user_stats(user_id: int) -> dict:
    with _connect() as conn:
        _ensure_user_row(conn, user_id)
        cur = conn.execute("""
            SELECT outputs_count, settings_changes_count, first_seen, last_seen
              FROM user_stats WHERE user_id = ?;
        """, (user_id,))
        row = cur.fetchone()
        return {
            "outputs_count": row[0],
            "settings_changes_count": row[1],
            "first_seen": row[2],
            "last_seen": row[3],
        }
