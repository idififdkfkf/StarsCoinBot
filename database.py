"""
Thin synchronous SQLite wrapper. Kept simple on purpose: this app is expected
to run as a single process on Railway, so a lock-protected sqlite3 connection
is enough and avoids adding an external database dependency.
"""
import sqlite3
import threading
import time
from contextlib import contextmanager

from config import DB_PATH

_lock = threading.Lock()


def _connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


_conn = _connect()


@contextmanager
def cursor():
    with _lock:
        cur = _conn.cursor()
        try:
            yield cur
            _conn.commit()
        finally:
            cur.close()


def init_db():
    with cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            joined_at INTEGER,
            is_premium INTEGER DEFAULT 0,
            premium_until INTEGER DEFAULT 0,
            referred_by INTEGER,
            captcha_passed INTEGER DEFAULT 0,
            bonus_slots INTEGER DEFAULT 0
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS child_bots (
            bot_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            token TEXT NOT NULL UNIQUE,
            username TEXT,
            force_join_channel TEXT DEFAULT '',
            reactions_enabled INTEGER DEFAULT 1,
            welcome_text TEXT DEFAULT 'سلام! خوش اومدی 👋',
            welcome_photo TEXT DEFAULT '',
            keyboard_style TEXT DEFAULT 'inline',
            unlock_price_stars INTEGER DEFAULT 0,
            unlock_text TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            created_at INTEGER
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            reply_text TEXT NOT NULL,
            color TEXT DEFAULT '#2AABEE',
            FOREIGN KEY(bot_id) REFERENCES child_bots(bot_id) ON DELETE CASCADE
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS bot_subscribers (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at INTEGER,
            PRIMARY KEY (bot_id, user_id)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS reactions (
            bot_id INTEGER NOT NULL,
            chat_id INTEGER NOT NULL,
            message_id INTEGER NOT NULL,
            emoji TEXT NOT NULL,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (bot_id, chat_id, message_id, emoji)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS blocked_users (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            PRIMARY KEY (bot_id, user_id)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS unlocked_users (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            unlocked_at INTEGER,
            PRIMARY KEY (bot_id, user_id)
        )""")
        cur.execute("""
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )""")
    _migrate_add_columns()


def _migrate_add_columns():
    """Best-effort ALTER TABLE for people upgrading an existing database
    created by an earlier version of this project. Safe to run every start."""
    additions = [
        ("child_bots", "welcome_photo", "TEXT DEFAULT ''"),
        ("child_bots", "keyboard_style", "TEXT DEFAULT 'inline'"),
        ("child_bots", "unlock_price_stars", "INTEGER DEFAULT 0"),
        ("child_bots", "unlock_text", "TEXT DEFAULT ''"),
        ("users", "bonus_slots", "INTEGER DEFAULT 0"),
        ("bot_buttons", "color", "TEXT DEFAULT '#2AABEE'"),
    ]
    with cursor() as cur:
        for table, col, decl in additions:
            try:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
            except sqlite3.OperationalError:
                pass  # column already exists


# ---------- users ----------
def upsert_user(user_id: int, username: str, referred_by: int = None) -> bool:
    """Returns True if this user is brand new (first /start ever)."""
    with cursor() as cur:
        cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if cur.fetchone():
            cur.execute("UPDATE users SET username=? WHERE user_id=?", (username, user_id))
            return False
        cur.execute(
            "INSERT INTO users (user_id, username, joined_at, referred_by) VALUES (?,?,?,?)",
            (user_id, username, int(time.time()), referred_by),
        )
        return True


def get_user(user_id: int):
    with cursor() as cur:
        cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
        return cur.fetchone()


def set_captcha_passed(user_id: int):
    with cursor() as cur:
        cur.execute("UPDATE users SET captcha_passed=1 WHERE user_id=?", (user_id,))


def set_premium(user_id: int, until_ts: int):
    with cursor() as cur:
        cur.execute(
            "UPDATE users SET is_premium=1, premium_until=? WHERE user_id=?",
            (until_ts, user_id),
        )


def is_premium(user_id: int) -> bool:
    row = get_user(user_id)
    if not row:
        return False
    return bool(row["is_premium"]) and row["premium_until"] > time.time()


def all_user_ids():
    with cursor() as cur:
        cur.execute("SELECT user_id FROM users")
        return [r["user_id"] for r in cur.fetchall()]


def add_bonus_slot(user_id: int, amount: int = 1):
    with cursor() as cur:
        cur.execute("UPDATE users SET bonus_slots = bonus_slots + ? WHERE user_id=?", (amount, user_id))


def get_bonus_slots(user_id: int) -> int:
    row = get_user(user_id)
    return row["bonus_slots"] if row else 0


def count_referrals(user_id: int) -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM users WHERE referred_by=?", (user_id,))
        return cur.fetchone()["c"]


# ---------- child bots ----------
def count_user_bots(owner_id: int) -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM child_bots WHERE owner_id=?", (owner_id,))
        return cur.fetchone()["c"]


def create_child_bot(owner_id: int, token: str, username: str) -> int:
    with cursor() as cur:
        cur.execute(
            "INSERT INTO child_bots (owner_id, token, username, created_at) VALUES (?,?,?,?)",
            (owner_id, token, username, int(time.time())),
        )
        return cur.lastrowid


def get_user_bots(owner_id: int):
    with cursor() as cur:
        cur.execute("SELECT * FROM child_bots WHERE owner_id=?", (owner_id,))
        return cur.fetchall()


def get_bot(bot_id: int):
    with cursor() as cur:
        cur.execute("SELECT * FROM child_bots WHERE bot_id=?", (bot_id,))
        return cur.fetchone()


def get_bot_by_token(token: str):
    with cursor() as cur:
        cur.execute("SELECT * FROM child_bots WHERE token=?", (token,))
        return cur.fetchone()


def get_all_active_bots():
    with cursor() as cur:
        cur.execute("SELECT * FROM child_bots WHERE is_active=1")
        return cur.fetchall()


def set_bot_active(bot_id: int, active: bool):
    with cursor() as cur:
        cur.execute("UPDATE child_bots SET is_active=? WHERE bot_id=?", (int(active), bot_id))


def delete_bot(bot_id: int):
    with cursor() as cur:
        cur.execute("DELETE FROM child_bots WHERE bot_id=?", (bot_id,))
        cur.execute("DELETE FROM bot_buttons WHERE bot_id=?", (bot_id,))
        cur.execute("DELETE FROM bot_subscribers WHERE bot_id=?", (bot_id,))
        cur.execute("DELETE FROM blocked_users WHERE bot_id=?", (bot_id,))
        cur.execute("DELETE FROM unlocked_users WHERE bot_id=?", (bot_id,))
        cur.execute("DELETE FROM reactions WHERE bot_id=?", (bot_id,))


def set_force_join(bot_id: int, channel: str):
    with cursor() as cur:
        cur.execute("UPDATE child_bots SET force_join_channel=? WHERE bot_id=?", (channel, bot_id))


def toggle_reactions(bot_id: int) -> bool:
    with cursor() as cur:
        cur.execute("SELECT reactions_enabled FROM child_bots WHERE bot_id=?", (bot_id,))
        cur_val = cur.fetchone()["reactions_enabled"]
        new_val = 0 if cur_val else 1
        cur.execute("UPDATE child_bots SET reactions_enabled=? WHERE bot_id=?", (new_val, bot_id))
        return bool(new_val)


def set_welcome_text(bot_id: int, text: str):
    with cursor() as cur:
        cur.execute("UPDATE child_bots SET welcome_text=? WHERE bot_id=?", (text, bot_id))


def set_welcome_photo(bot_id: int, file_id: str):
    with cursor() as cur:
        cur.execute("UPDATE child_bots SET welcome_photo=? WHERE bot_id=?", (file_id, bot_id))


def set_keyboard_style(bot_id: int, style: str):
    """style is one of 'inline', 'reply', 'menu', 'webapp'."""
    with cursor() as cur:
        cur.execute("UPDATE child_bots SET keyboard_style=? WHERE bot_id=?", (style, bot_id))


def set_unlock(bot_id: int, price_stars: int, text: str):
    with cursor() as cur:
        cur.execute(
            "UPDATE child_bots SET unlock_price_stars=?, unlock_text=? WHERE bot_id=?",
            (price_stars, text, bot_id),
        )


def mark_unlocked(bot_id: int, user_id: int):
    with cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO unlocked_users (bot_id, user_id, unlocked_at) VALUES (?,?,?)",
            (bot_id, user_id, int(time.time())),
        )


def has_unlocked(bot_id: int, user_id: int) -> bool:
    with cursor() as cur:
        cur.execute("SELECT 1 FROM unlocked_users WHERE bot_id=? AND user_id=?", (bot_id, user_id))
        return cur.fetchone() is not None


def block_user(bot_id: int, user_id: int):
    with cursor() as cur:
        cur.execute("INSERT OR IGNORE INTO blocked_users (bot_id, user_id) VALUES (?,?)", (bot_id, user_id))


def unblock_user(bot_id: int, user_id: int):
    with cursor() as cur:
        cur.execute("DELETE FROM blocked_users WHERE bot_id=? AND user_id=?", (bot_id, user_id))


def is_blocked(bot_id: int, user_id: int) -> bool:
    with cursor() as cur:
        cur.execute("SELECT 1 FROM blocked_users WHERE bot_id=? AND user_id=?", (bot_id, user_id))
        return cur.fetchone() is not None


# ---------- buttons ----------
def add_button(bot_id: int, text: str, reply_text: str, color: str = "#2AABEE"):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO bot_buttons (bot_id, text, reply_text, color) VALUES (?,?,?,?)",
            (bot_id, text, reply_text, color),
        )


def get_buttons(bot_id: int):
    with cursor() as cur:
        cur.execute("SELECT * FROM bot_buttons WHERE bot_id=?", (bot_id,))
        return cur.fetchall()


def delete_button(button_id: int):
    with cursor() as cur:
        cur.execute("DELETE FROM bot_buttons WHERE id=?", (button_id,))


# ---------- child bot subscribers (for broadcast) ----------
def add_bot_subscriber(bot_id: int, user_id: int):
    with cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO bot_subscribers (bot_id, user_id, joined_at) VALUES (?,?,?)",
            (bot_id, user_id, int(time.time())),
        )


def get_bot_subscribers(bot_id: int):
    with cursor() as cur:
        cur.execute("SELECT user_id FROM bot_subscribers WHERE bot_id=?", (bot_id,))
        return [r["user_id"] for r in cur.fetchall()]


def count_bot_subscribers(bot_id: int) -> int:
    with cursor() as cur:
        cur.execute("SELECT COUNT(*) c FROM bot_subscribers WHERE bot_id=?", (bot_id,))
        return cur.fetchone()["c"]


# ---------- app settings (key/value) ----------
def get_setting(key: str):
    with cursor() as cur:
        cur.execute("SELECT value FROM app_settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else None


def set_setting(key: str, value: str):
    with cursor() as cur:
        cur.execute(
            "INSERT INTO app_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


# ---------- reactions ----------
def bump_reaction(bot_id: int, chat_id: int, message_id: int, emoji: str) -> int:
    with cursor() as cur:
        cur.execute(
            "SELECT count FROM reactions WHERE bot_id=? AND chat_id=? AND message_id=? AND emoji=?",
            (bot_id, chat_id, message_id, emoji),
        )
        row = cur.fetchone()
        if row:
            new_count = row["count"] + 1
            cur.execute(
                "UPDATE reactions SET count=? WHERE bot_id=? AND chat_id=? AND message_id=? AND emoji=?",
                (new_count, bot_id, chat_id, message_id, emoji),
            )
        else:
            new_count = 1
            cur.execute(
                "INSERT INTO reactions (bot_id, chat_id, message_id, emoji, count) VALUES (?,?,?,?,1)",
                (bot_id, chat_id, message_id, emoji),
            )
        return new_count
