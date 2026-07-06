from __future__ import annotations
import sqlite3
from config import DB_PATH, DEFAULT_RULES, DEFAULT_AI_PROMPT


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phrase TEXT NOT NULL,
            answer TEXT NOT NULL,
            match_type TEXT NOT NULL DEFAULT 'exact'
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS whitelist (
            user_id INTEGER PRIMARY KEY
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS blacklist (
            user_id INTEGER PRIMARY KEY
        )
    """)

    # Заполняем дефолтные настройки при первом запуске
    defaults = {
        "enabled": "true",
        "notifications": "true",
        "reply_mode": "all",
        "owner_name": "Владелец",
        "ai_prompt": DEFAULT_AI_PROMPT,
        "whitelist_users": "",
        "blacklist_users": "",
    }
    for key, value in defaults.items():
        c.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )

    # Заполняем дефолтные правила
    c.execute("SELECT COUNT(*) as cnt FROM rules")
    if c.fetchone()["cnt"] == 0:
        for phrase, answer, match_type in DEFAULT_RULES:
            c.execute(
                "INSERT INTO rules (phrase, answer, match_type) VALUES (?, ?, ?)",
                (phrase, answer, match_type),
            )

    conn.commit()
    conn.close()


def get_setting(key: str) -> str:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else ""


def set_setting(key: str, value: str):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


def add_rule(phrase: str, answer: str, match_type: str = "exact"):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "INSERT INTO rules (phrase, answer, match_type) VALUES (?, ?, ?)",
        (phrase, answer, match_type),
    )
    conn.commit()
    rule_id = c.lastrowid
    conn.close()
    return rule_id


def delete_rule(rule_id: int):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
    conn.commit()
    conn.close()


def get_all_rules() -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT id, phrase, answer, match_type FROM rules")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def match_rule(text: str) -> str | None:
    """Ищет совпадение правила: сначала точные, потом частичные"""
    conn = get_conn()
    c = conn.cursor()

    # Точное совпадение
    c.execute(
        "SELECT answer FROM rules WHERE match_type = 'exact' AND LOWER(phrase) = LOWER(?)",
        (text.strip(),),
    )
    row = c.fetchone()
    if row:
        conn.close()
        return row["answer"]

    # Частичное совпадение
    c.execute(
        "SELECT answer FROM rules WHERE match_type = 'partial' AND LOWER(?) LIKE '%' || LOWER(phrase) || '%'",
        (text.strip(),),
    )
    row = c.fetchone()
    conn.close()
    return row["answer"] if row else None


def get_whitelist() -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM whitelist")
    rows = c.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def set_whitelist(user_ids: list):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM whitelist")
    for uid in user_ids:
        c.execute("INSERT OR IGNORE INTO whitelist (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()


def get_blacklist() -> list:
    conn = get_conn()
    c = conn.cursor()
    c.execute("SELECT user_id FROM blacklist")
    rows = c.fetchall()
    conn.close()
    return [row["user_id"] for row in rows]


def set_blacklist(user_ids: list):
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM blacklist")
    for uid in user_ids:
        c.execute("INSERT OR IGNORE INTO blacklist (user_id) VALUES (?)", (uid,))
    conn.commit()
    conn.close()
