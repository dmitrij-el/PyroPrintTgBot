# app/db/state.py
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Optional, Literal, Any, Dict

_DB: Optional[Path] = None

def _conn() -> sqlite3.Connection:
    if _DB is None:
        raise RuntimeError("state DB is not initialized. Call state_db.init(path) first.")
    conn = sqlite3.connect(_DB.as_posix(), timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init(db_path: str) -> None:
    """Инициализация файла и таблицы состояния пользователей."""
    global _DB
    _DB = Path(db_path)
    _DB.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
        CREATE TABLE IF NOT EXISTS user_state (
            user_id INTEGER PRIMARY KEY,
            brightness REAL NOT NULL DEFAULT 1.0,
            contrast   REAL NOT NULL DEFAULT 1.0,
            gamma      REAL NOT NULL DEFAULT 1.0,
            sharpness  REAL NOT NULL DEFAULT 1.0,
            invert     INTEGER NOT NULL DEFAULT 0,
            dither     TEXT NOT NULL DEFAULT 'fs',
            dpi        INTEGER NOT NULL DEFAULT 300,
            denoise_size INTEGER NOT NULL DEFAULT 0,
            blur_radius REAL NOT NULL DEFAULT 0.0,
            last_image_bytes BLOB
        );
        """)
        # мягкая миграция новых полей
        try:
            c.execute("ALTER TABLE user_state ADD COLUMN out_format TEXT NOT NULL DEFAULT 'bmp';")
        except sqlite3.OperationalError:
            # колонка уже добавлена ранее
            pass
        c.commit()

def ensure_user(user_id: int) -> None:
    with _conn() as c:
        c.execute("""
            INSERT INTO user_state (user_id) VALUES (?)
            ON CONFLICT(user_id) DO NOTHING;
        """, (user_id,))
        c.commit()

def get_state(user_id: int) -> Dict[str, Any]:
    """Возвращает все поля состояния пользователя (создаёт запись при отсутствии)."""
    with _conn() as c:
        ensure_user(user_id)
        cur = c.execute("""
            SELECT brightness, contrast, gamma, sharpness, invert, dither, dpi,
                   denoise_size, blur_radius, last_image_bytes, out_format
            FROM user_state WHERE user_id = ?;
        """, (user_id,))
        row = cur.fetchone()
        # row гарантированно есть после ensure_user
        return {
            "brightness": float(row[0]),
            "contrast": float(row[1]),
            "gamma": float(row[2]),
            "sharpness": float(row[3]),
            "invert": bool(row[4]),
            "dither": str(row[5]),
            "dpi": int(row[6]),
            "denoise_size": int(row[7]),
            "blur_radius": float(row[8]),
            "last_image_bytes": row[9],
            "out_format": (row[10] or "bmp"),
        }

def save_state(
    user_id: int,
    *,
    brightness: float,
    contrast: float,
    gamma: float,
    sharpness: float,
    invert: bool,
    dither: Literal["fs","ordered","none"],
    dpi: int,
    denoise_size: int,
    blur_radius: float,
    last_image_bytes: Optional[bytes],
    out_format: str = "bmp",
) -> None:
    with _conn() as c:
        c.execute("""
            UPDATE user_state
               SET brightness = ?, contrast = ?, gamma = ?, sharpness = ?,
                   invert = ?, dither = ?, dpi = ?, denoise_size = ?,
                   blur_radius = ?, last_image_bytes = ?, out_format = ?
             WHERE user_id = ?;
        """, (
            brightness, contrast, gamma, sharpness,
            1 if invert else 0, dither, dpi, denoise_size,
            blur_radius, last_image_bytes, out_format, user_id
        ))
        c.commit()

def update_fields(user_id: int, **fields) -> None:
    """Частичное обновление произвольных полей (без SELECT)."""
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields.keys())
    vals = list(fields.values()) + [user_id]
    with _conn() as c:
        ensure_user(user_id)
        c.execute(f"UPDATE user_state SET {cols} WHERE user_id = ?;", vals)
        c.commit()
