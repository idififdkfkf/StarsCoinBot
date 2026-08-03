# -*- coding: utf-8 -*-
"""
LIBER Telegram Bot — main.py
================================================================
اقتصاد، بازار، بانک، صندوق، اشتراک استارز، برداشت TON، رفرال،
ماموریت روزانه‌ی اجباری، رقابت آنلاین رنک‌بندی‌شده.
پنل مدیریت جداست: admin_panel.py را کنار همین فایل بگذارید.

نصب:  pip install python-telegram-bot==21.*
اجرا:  python main.py
قبل از اجرا BOT_TOKEN و ADMIN_IDS را در SECTION 1 تنظیم کنید.
"""
# SECTION 1: CONFIG — تنظیمات، تعرفه‌ها، رنک‌ها
BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"          # توکن ربات از BotFather
ADMIN_IDS = [6188951798]                    # آیدی عددی ادمین (فقط همین آیدی دسترسی داره)
DB_PATH = "liber.db"
ADMIN_SECRET_COMMAND = "/admin"

FORCE_JOIN_CHANNELS = [
    {"id": "@Libercoin1", "title": "کانال LIBER", "url": "https://t.me/Libercoin1"},
    {"id": "@Libercoin2", "title": "گروه LIBER", "url": "https://t.me/Libercoin2"},
]
# کانال سفارشات: لاگ خودکار هر سفارش/آپدیت وضعیت؛ کاربرها نیازی به عضویت ندارن.
ORDERS_CHANNEL_ID = "@Libercoin23"

MARKET_BASE_PRICE = 100
BUY_FEE_PERCENT = 2
SELL_FEE_PERCENT = 2
MARKET_FLUCTUATION_RANGE = (-0.07, 0.07)
MARKET_UPDATE_INTERVAL_SECONDS = 3600

BANK_INTEREST_PERCENT = 1.5
LOAN_INTEREST_PERCENT = 5
MAX_LOAN_MULTIPLIER = 3
LOAN_BASE_PER_LEVEL = 100

XP_PER_LEVEL = 100
DAILY_MISSION_XP = 20
DAILY_MISSION_LIBER = 8

CHEST_TABLE = {
    "free":    {"cost": {},               "rewards": [("coin", 40, 120), ("liber", 1, 3)]},
    "bronze":  {"cost": {"coin": 350},     "rewards": [("coin", 90, 350), ("liber", 2, 7), ("xp", 8, 18)]},
    "silver":  {"cost": {"coin": 900},     "rewards": [("liber", 6, 20), ("diamond", 1, 2), ("xp", 15, 35)]},
    "gold":    {"cost": {"liber": 130},    "rewards": [("liber", 18, 55), ("diamond", 2, 4), ("medal", 1, 2)]},
    "diamond": {"cost": {"diamond": 25},   "rewards": [("liber", 50, 140), ("diamond", 4, 8), ("medal", 1, 4)]},
}

VIP_TIERS = {
    "silver":  {"cost_diamond": 50,   "xp_bonus": 1.10, "income_bonus": 1.10},
    "gold":    {"cost_diamond": 150,  "xp_bonus": 1.25, "income_bonus": 1.25},
    "diamond": {"cost_diamond": 400,  "xp_bonus": 1.50, "income_bonus": 1.50},
    "titan":   {"cost_diamond": 1000, "xp_bonus": 2.00, "income_bonus": 2.00},
}

SUBSCRIPTION_TIERS = {
    "normal": {
        "title": "🎫 اشتراک عادی", "badge": "🎫",
        "daily_bonus_percent": 10, "market_fee_discount_percent": 20, "withdraw_fee_discount_percent": 0,
        "perks": ["۱۰٪ افزایش پاداش ماموریت روزانه", "۲۰٪ تخفیف کارمزد خرید/فروش بازار", "دسترسی به صندوق‌های ویژه"],
        "options": {3: 30, 6: 50},
    },
    "dragon": {
        "title": "🐉 اشتراک اژدها", "badge": "🐉",
        "daily_bonus_percent": 25, "market_fee_discount_percent": 50, "withdraw_fee_discount_percent": 25,
        "perks": ["۲۵٪ افزایش پاداش ماموریت روزانه", "۵۰٪ تخفیف کارمزد خرید/فروش بازار (نصف)",
                  "۲۵٪ تخفیف کارمزد برداشت TON", "بج ویژه‌ی اژدها 🐉 کنار نامت"],
        "options": {3: 50, 6: 80},
    },
    "liberi": {
        "title": "👑 اشتراک لیبری (VIP برتر)", "badge": "👑",
        "daily_bonus_percent": 50, "market_fee_discount_percent": 100, "withdraw_fee_discount_percent": 50,
        "perks": ["۵۰٪ افزایش پاداش ماموریت روزانه", "بدون کارمزد بازار (۱۰۰٪ تخفیف)",
                  "۵۰٪ تخفیف کارمزد برداشت TON + اولویت در صف تایید", "بج طلایی اختصاصی 👑 + دسترسی زودهنگام به رویدادها"],
        "options": {3: 100, 6: 135},
    },
}

MONTH_END_DISCOUNT_PERCENT = {"normal": 5, "dragon": 10, "liberi": 15}

REFERRAL_BONUS_NORMAL = 100
REFERRAL_BONUS_PREMIUM = 150

MIN_WITHDRAW_LIBER = 2000
WITHDRAW_FEE_PERCENT = 5
WITHDRAW_PENDING_TEXT = (
    "✅ درخواست برداشت شما با موفقیت ثبت شد و برای بررسی ادمین ارسال گردید.\n"
    "⏳ وضعیت: در حال بررسی — به محض تایید و انجام تراکنش، پیام موفقیت برایتان ارسال می‌شود."
)

SPAM_WINDOW_SECONDS = 8
SPAM_MAX_ACTIONS = 10
SPAM_WARN_LIMIT = 3

RANKS = [
    "🔰 سواپ وان", "🔰 سواپ تو", "🔰 سواپ لجند", "🐉 دراگون", "🐉 دراگون لجند",
    "🔷 لیبر", "🔷 لیبر لجند", "💎 الماس", "💎 الماسی فول لجند",
]
MAX_RANK_INDEX = len(RANKS) - 1

MATCH_ENTRY_FEE = 15
MATCH_BASE_REWARD = 30
MATCH_QUEUE_CHECK_SECONDS = 120
MATCH_BOT_FALLBACK_SECONDS = 300
MATCH_MIN_SECONDS_BETWEEN_STARTS = 10

TOURNAMENT_INTERVAL_SECONDS = 30 * 86400
TOURNAMENT_REWARDS = {1: 2000, 2: 1500, 3: 1000}

COMPETITION_DAILY_MISSION_WINS = 1
COMPETITION_DAILY_MISSION_REWARD = 40


def wins_required_for_rank(rank_index: int) -> int:
    return 10 + rank_index * 5


def medals_per_win_for_rank(rank_index: int) -> float:
    return max(5.0, 10 - rank_index * 0.5)


def reward_for_rank(rank_index: int) -> int:
    return MATCH_BASE_REWARD * (2 ** rank_index)


# SECTION 2: DATABASE — لایه‌ی دیتابیس (SQLite)
import sqlite3
from contextlib import contextmanager


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            coin INTEGER NOT NULL DEFAULT 200,
            liber REAL NOT NULL DEFAULT 0,
            diamond INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            bank_balance REAL NOT NULL DEFAULT 0,
            bank_last_interest INTEGER NOT NULL DEFAULT 0,
            loan_balance REAL NOT NULL DEFAULT 0,
            vip_tier TEXT,
            subscription_tier TEXT,
            subscription_expires INTEGER,
            referred_by INTEGER,
            warnings INTEGER NOT NULL DEFAULT 0,
            is_banned INTEGER NOT NULL DEFAULT 0,
            joined_at INTEGER NOT NULL,
            last_daily INTEGER NOT NULL DEFAULT 0
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS market_state (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            price REAL NOT NULL,
            updated_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS withdrawal_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            liber_amount REAL NOT NULL,
            fee REAL NOT NULL,
            ton_amount REAL NOT NULL,
            wallet_address TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER,
            resolved_by INTEGER
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            tx_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            detail TEXT,
            created_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            inviter_id INTEGER NOT NULL,
            invitee_id INTEGER NOT NULL UNIQUE,
            bonus_liber REAL NOT NULL,
            created_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS star_payments (
            payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tier TEXT NOT NULL,
            months INTEGER NOT NULL,
            stars_amount INTEGER NOT NULL,
            telegram_payment_charge_id TEXT,
            created_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS comp_profile (
            user_id INTEGER PRIMARY KEY,
            rank_index INTEGER NOT NULL DEFAULT 0,
            medals REAL NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0,
            draws INTEGER NOT NULL DEFAULT 0,
            season_medals REAL NOT NULL DEFAULT 0
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS comp_queue (
            user_id INTEGER PRIMARY KEY,
            rank_index INTEGER NOT NULL,
            joined_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS comp_season (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            season_number INTEGER NOT NULL DEFAULT 1,
            started_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS comp_daily_mission (
            user_id INTEGER,
            mission_date TEXT,
            wins_needed INTEGER NOT NULL DEFAULT 1,
            wins_done INTEGER NOT NULL DEFAULT 0,
            claimed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, mission_date)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            country_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER UNIQUE,
            name TEXT,
            flag TEXT DEFAULT '🏳',
            population INTEGER DEFAULT 1000,
            satisfaction INTEGER DEFAULT 70,
            created_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            building_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            level INTEGER NOT NULL DEFAULT 1
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS alliances (
            alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            leader_id INTEGER,
            treasury REAL NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS alliance_members (
            user_id INTEGER PRIMARY KEY,
            alliance_id INTEGER NOT NULL,
            joined_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            auction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            current_price REAL NOT NULL DEFAULT 50,
            current_winner INTEGER,
            active INTEGER NOT NULL DEFAULT 1,
            created_at INTEGER NOT NULL,
            ends_at INTEGER NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            pred_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            direction TEXT NOT NULL,
            start_price REAL NOT NULL,
            bet_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            created_at INTEGER NOT NULL
        )
        """)

        for ddl in (
            "ALTER TABLE users ADD COLUMN research_level INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN personal_defense_level INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN job_key TEXT",
            "ALTER TABLE users ADD COLUMN job_title TEXT NOT NULL DEFAULT 'بیکار'",
            "ALTER TABLE users ADD COLUMN last_work INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN last_explore INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE users ADD COLUMN country_id INTEGER",
        ):
            try:
                c.execute(ddl)
            except sqlite3.OperationalError:
                pass

        row = c.execute("SELECT 1 FROM comp_season WHERE id = 1").fetchone()
        if not row:
            c.execute(
                "INSERT INTO comp_season (id, season_number, started_at) VALUES (1, 1, ?)",
                (int(time.time()),),
            )

        row = c.execute("SELECT 1 FROM market_state WHERE id = 1").fetchone()
        if not row:
            c.execute(
                "INSERT INTO market_state (id, price, updated_at) VALUES (1, ?, ?)",
                (MARKET_BASE_PRICE, int(time.time())),
            )


def get_user(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def ensure_user(user_id, username, first_name, referred_by=None):
    with get_conn() as conn:
        existing = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if existing:
            conn.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username, first_name, user_id),
            )
            return False
        conn.execute(
            """INSERT INTO users (user_id, username, first_name, referred_by, joined_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, referred_by, int(time.time())),
        )
        return True


def update_balance(user_id, coin=0, liber=0, diamond=0, xp=0):
    with get_conn() as conn:
        conn.execute(
            """UPDATE users
               SET coin = coin + ?, liber = liber + ?, diamond = diamond + ?, xp = xp + ?
               WHERE user_id = ?""",
            (coin, liber, diamond, xp, user_id),
        )
        row = conn.execute("SELECT xp, level FROM users WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            new_level = 1 + row["xp"] // XP_PER_LEVEL
            if new_level != row["level"]:
                conn.execute("UPDATE users SET level = ? WHERE user_id = ?", (new_level, user_id))


def log_transaction(user_id, kind, detail=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO transactions (user_id, kind, detail, created_at) VALUES (?, ?, ?, ?)",
            (user_id, kind, detail, int(time.time())),
        )


def add_warning(user_id):
    with get_conn() as conn:
        conn.execute("UPDATE users SET warnings = warnings + 1 WHERE user_id = ?", (user_id,))
        row = conn.execute("SELECT warnings FROM users WHERE user_id = ?", (user_id,)).fetchone()
        warnings = row["warnings"] if row else 0
        banned = False
        if warnings >= SPAM_WARN_LIMIT:
            conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))
            banned = True
        return warnings, banned


def is_banned(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,)).fetchone()
        return bool(row and row["is_banned"])


def set_ban(user_id, banned: bool):
    with get_conn() as conn:
        conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (1 if banned else 0, user_id))


def get_market_price():
    with get_conn() as conn:
        row = conn.execute("SELECT price FROM market_state WHERE id = 1").fetchone()
        return row["price"] if row else MARKET_BASE_PRICE


def fluctuate_market(low, high):
    with get_conn() as conn:
        row = conn.execute("SELECT price FROM market_state WHERE id = 1").fetchone()
        price = row["price"] if row else MARKET_BASE_PRICE
        change_pct = random.uniform(low, high)
        new_price = max(1.0, round(price * (1 + change_pct), 2))
        conn.execute(
            "UPDATE market_state SET price = ?, updated_at = ? WHERE id = 1",
            (new_price, int(time.time())),
        )
        return price, new_price, change_pct


def bank_deposit(user_id, amount):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET coin = coin - ?, bank_balance = bank_balance + ? WHERE user_id = ?",
            (amount, amount, user_id),
        )


def bank_withdraw_all(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT bank_balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
        total = row["bank_balance"] if row else 0
        if total > 0:
            conn.execute(
                "UPDATE users SET coin = coin + ?, bank_balance = 0 WHERE user_id = ?",
                (total, user_id),
            )
        return total


def take_loan(user_id, amount, interest_percent):
    owed = round(amount * (1 + interest_percent / 100), 2)
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET liber = liber + ?, loan_balance = loan_balance + ? WHERE user_id = ?",
            (amount, owed, user_id),
        )
    return owed


def repay_loan(user_id, amount):
    with get_conn() as conn:
        row = conn.execute("SELECT loan_balance, liber FROM users WHERE user_id = ?", (user_id,)).fetchone()
        actual = min(amount, row["loan_balance"], row["liber"])
        actual = round(actual, 2)
        if actual > 0:
            conn.execute(
                "UPDATE users SET liber = liber - ?, loan_balance = loan_balance - ? WHERE user_id = ?",
                (actual, actual, user_id),
            )
        return actual


def max_loan_for_level(level, base_per_level, multiplier):
    return level * base_per_level * multiplier


def apply_daily_interest(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT bank_balance, bank_last_interest FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or row["bank_balance"] <= 0:
            return 0
        now = int(time.time())
        if now - row["bank_last_interest"] < 86400:
            return 0
        interest = round(row["bank_balance"] * BANK_INTEREST_PERCENT / 100, 2)
        conn.execute(
            "UPDATE users SET bank_balance = bank_balance + ?, bank_last_interest = ? WHERE user_id = ?",
            (interest, now, user_id),
        )
        return interest


def has_done_daily_mission(user_id) -> bool:
    with get_conn() as conn:
        row = conn.execute("SELECT last_daily FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row or not row["last_daily"]:
        return False
    today_start = int(time.time() // 86400) * 86400
    return row["last_daily"] >= today_start


def get_active_subscription_tier(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT subscription_tier, subscription_expires FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    if not row or not row["subscription_tier"] or not row["subscription_expires"]:
        return None
    if row["subscription_expires"] <= int(time.time()):
        return None
    return row["subscription_tier"]


def create_withdraw_request(user_id, liber_amount, fee, ton_amount, wallet_address):
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO withdrawal_requests
               (user_id, liber_amount, fee, ton_amount, wallet_address, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, liber_amount, fee, ton_amount, wallet_address, int(time.time())),
        )
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?",
            (liber_amount, user_id),
        )
        return cur.lastrowid


def list_pending_withdrawals(limit=20):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM withdrawal_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT ?",
            (limit,),
        ).fetchall()


def get_withdraw_request(request_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM withdrawal_requests WHERE request_id = ?", (request_id,)
        ).fetchone()


def approve_withdraw_request(request_id, admin_id):
    with get_conn() as conn:
        conn.execute(
            """UPDATE withdrawal_requests
               SET status = 'approved', resolved_at = ?, resolved_by = ?
               WHERE request_id = ?""",
            (int(time.time()), admin_id, request_id),
        )


def reject_withdraw_request(request_id, admin_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT user_id, liber_amount FROM withdrawal_requests WHERE request_id = ?",
            (request_id,),
        ).fetchone()
        conn.execute(
            """UPDATE withdrawal_requests
               SET status = 'rejected', resolved_at = ?, resolved_by = ?
               WHERE request_id = ?""",
            (int(time.time()), admin_id, request_id),
        )
        if row:
            conn.execute(
                "UPDATE users SET liber = liber + ? WHERE user_id = ?",
                (row["liber_amount"], row["user_id"]),
            )


def grant_subscription(user_id, tier, months, stars_amount, charge_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT subscription_expires FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()
        now = int(time.time())
        base = row["subscription_expires"] if row and row["subscription_expires"] and row["subscription_expires"] > now else now
        new_expiry = base + months * 30 * 86400
        conn.execute(
            "UPDATE users SET subscription_tier = ?, subscription_expires = ? WHERE user_id = ?",
            (tier, new_expiry, user_id),
        )
        conn.execute(
            """INSERT INTO star_payments (user_id, tier, months, stars_amount, telegram_payment_charge_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, tier, months, stars_amount, charge_id, now),
        )
        return new_expiry


def register_referral(inviter_id, invitee_id, bonus_liber):
    with get_conn() as conn:
        exists = conn.execute(
            "SELECT 1 FROM referrals WHERE invitee_id = ?", (invitee_id,)
        ).fetchone()
        if exists:
            return False
        conn.execute(
            """INSERT INTO referrals (inviter_id, invitee_id, bonus_liber, created_at)
               VALUES (?, ?, ?, ?)""",
            (inviter_id, invitee_id, bonus_liber, int(time.time())),
        )
        conn.execute(
            "UPDATE users SET liber = liber + ? WHERE user_id = ?",
            (bonus_liber, inviter_id),
        )
        return True


def count_referrals(user_id):
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM referrals WHERE inviter_id = ?", (user_id,)
        ).fetchone()
        return row["c"] if row else 0


def get_comp_profile(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM comp_profile WHERE user_id = ?", (user_id,)).fetchone()
        if row:
            return row
        conn.execute("INSERT INTO comp_profile (user_id) VALUES (?)", (user_id,))
        return conn.execute("SELECT * FROM comp_profile WHERE user_id = ?", (user_id,)).fetchone()


def get_comp_season():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM comp_season WHERE id = 1").fetchone()


def comp_join_queue(user_id, rank_index):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO comp_queue (user_id, rank_index, joined_at) VALUES (?, ?, ?)",
            (user_id, rank_index, int(time.time())),
        )


def comp_leave_queue(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM comp_queue WHERE user_id = ?", (user_id,))


def comp_is_queued(user_id):
    with get_conn() as conn:
        return bool(conn.execute("SELECT 1 FROM comp_queue WHERE user_id = ?", (user_id,)).fetchone())


def comp_find_opponent(user_id, rank_index):
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM comp_queue WHERE rank_index = ? AND user_id != ? LIMIT 1",
            (rank_index, user_id),
        ).fetchone()


def comp_all_queued():
    with get_conn() as conn:
        return conn.execute("SELECT * FROM comp_queue ORDER BY joined_at ASC").fetchall()


def comp_record_result(user_id, outcome, medals_gain=0, liber_gain=0):
    with get_conn() as conn:
        if outcome == "win":
            conn.execute(
                "UPDATE comp_profile SET wins = wins + 1, medals = medals + ?, season_medals = season_medals + ? WHERE user_id = ?",
                (medals_gain, medals_gain, user_id),
            )
        elif outcome == "draw":
            conn.execute(
                "UPDATE comp_profile SET draws = draws + 1, medals = medals + ?, season_medals = season_medals + ? WHERE user_id = ?",
                (medals_gain, medals_gain, user_id),
            )
        else:
            conn.execute("UPDATE comp_profile SET losses = losses + 1 WHERE user_id = ?", (user_id,))
        if liber_gain:
            conn.execute("UPDATE users SET liber = liber + ? WHERE user_id = ?", (liber_gain, user_id))


def comp_promote_if_ready(user_id, wins_required_fn, medals_per_win_fn, max_rank_index):
    profile = get_comp_profile(user_id)
    if profile["rank_index"] >= max_rank_index:
        return None
    needed_wins = wins_required_fn(profile["rank_index"])
    threshold = needed_wins * medals_per_win_fn(profile["rank_index"])
    if profile["medals"] >= threshold:
        new_rank = profile["rank_index"] + 1
        with get_conn() as conn:
            conn.execute(
                "UPDATE comp_profile SET rank_index = ?, medals = 0 WHERE user_id = ?",
                (new_rank, user_id),
            )
        return new_rank
    return None


def comp_top_season(limit=10):
    with get_conn() as conn:
        return conn.execute(
            "SELECT user_id, rank_index, season_medals FROM comp_profile ORDER BY season_medals DESC LIMIT ?",
            (limit,),
        ).fetchall()


def comp_reset_season():
    with get_conn() as conn:
        season = conn.execute("SELECT * FROM comp_season WHERE id = 1").fetchone()
        new_number = season["season_number"] + 1
        conn.execute("UPDATE comp_profile SET season_medals = 0")
        conn.execute(
            "UPDATE comp_season SET season_number = ?, started_at = ? WHERE id = 1",
            (new_number, int(time.time())),
        )
        return new_number


def comp_daily_mission_progress(user_id):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM comp_daily_mission WHERE user_id = ? AND mission_date = ?",
            (user_id, today),
        ).fetchone()


def comp_daily_mission_add_win(user_id):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM comp_daily_mission WHERE user_id = ? AND mission_date = ?",
            (user_id, today),
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO comp_daily_mission (user_id, mission_date, wins_needed, wins_done) VALUES (?, ?, 1, 1)",
                (user_id, today),
            )
        elif row["wins_done"] < row["wins_needed"]:
            conn.execute(
                "UPDATE comp_daily_mission SET wins_done = wins_done + 1 WHERE user_id = ? AND mission_date = ?",
                (user_id, today),
            )


def comp_daily_mission_claim(user_id, reward):
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with get_conn() as conn:
        conn.execute(
            "UPDATE comp_daily_mission SET claimed = 1 WHERE user_id = ? AND mission_date = ?",
            (user_id, today),
        )
        conn.execute("UPDATE users SET liber = liber + ? WHERE user_id = ?", (reward, user_id))


def all_comp_user_ids():
    with get_conn() as conn:
        return [r["user_id"] for r in conn.execute("SELECT user_id FROM comp_profile").fetchall()]


def get_stats():
    with get_conn() as conn:
        total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        banned = conn.execute("SELECT COUNT(*) c FROM users WHERE is_banned = 1").fetchone()["c"]
        total_liber = conn.execute("SELECT COALESCE(SUM(liber), 0) s FROM users").fetchone()["s"]
        pending_withdraws = conn.execute(
            "SELECT COUNT(*) c FROM withdrawal_requests WHERE status = 'pending'"
        ).fetchone()["c"]
        return {
            "total_users": total_users,
            "banned": banned,
            "total_liber": round(total_liber, 2),
            "pending_withdraws": pending_withdraws,
        }


def all_user_ids():
    with get_conn() as conn:
        return [r["user_id"] for r in conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()]


# SECTION 3: KEYBOARDS — دکمه‌های شیشه‌ای
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def force_join_keyboard():
    rows = [[InlineKeyboardButton(f"📢 عضویت در {ch['title']}", url=ch["url"])] for ch in FORCE_JOIN_CHANNELS]
    rows.append([InlineKeyboardButton("✅ عضو شدم، بررسی کن", callback_data="check_join")])
    return InlineKeyboardMarkup(rows)


def main_menu_keyboard(is_admin=False):
    rows = [
        [InlineKeyboardButton("👤 پروفایل", callback_data="menu_profile"),
         InlineKeyboardButton("🌍 کشور", callback_data="menu_country"),
         InlineKeyboardButton("💹 بازار", callback_data="menu_market")],
        [InlineKeyboardButton("🏦 بانک", callback_data="menu_bank"),
         InlineKeyboardButton("🏪 صندوق‌ها", callback_data="menu_chests"),
         InlineKeyboardButton("💼 شغل", callback_data="menu_job")],
        [InlineKeyboardButton("🤝 اتحاد", callback_data="menu_alliance"),
         InlineKeyboardButton("⚔️ جنگ کلن", callback_data="menu_clanwar2"),
         InlineKeyboardButton("🏷 مزایده", callback_data="menu_auction")],
        [InlineKeyboardButton("🔬 تحقیقات", callback_data="menu_research"),
         InlineKeyboardButton("🛡 دفاع", callback_data="menu_defense"),
         InlineKeyboardButton("🌌 اکتشاف", callback_data="menu_explore")],
        [InlineKeyboardButton("🤖 مشاور هوشمند", callback_data="menu_advisor"),
         InlineKeyboardButton("📰 اخبار جهان", callback_data="menu_news"),
         InlineKeyboardButton("🎟 پیش‌بینی قیمت", callback_data="menu_predict")],
        [InlineKeyboardButton("⭐ اشتراک ویژه", callback_data="menu_subscription"),
         InlineKeyboardButton("👥 دعوت دوستان", callback_data="menu_referral"),
         InlineKeyboardButton("📤 برداشت", callback_data="withdraw_start")],
        [InlineKeyboardButton("🎰 گردونه شانس", callback_data="menu_wheel"),
         InlineKeyboardButton("🎁 کد هدیه", callback_data="menu_giftcode"),
         InlineKeyboardButton("🎖 دستاوردها", callback_data="menu_achievements")],
        [InlineKeyboardButton("🏆 رتبه دعوت ماهانه", callback_data="menu_referral_top")],
        [InlineKeyboardButton("🔥 جنگ بزرگ سروری", callback_data="menu_serverwar"),
         InlineKeyboardButton("👹 چالش هفتگی باس", callback_data="menu_weeklyboss")],
        [InlineKeyboardButton("📅 ماموریت هفتگی", callback_data="menu_weeklymission"),
         InlineKeyboardButton("🎫 قرعه‌کشی روزانه", callback_data="menu_lottery")],
        [InlineKeyboardButton("🎨 فروشگاه ظاهری", callback_data="menu_cosmetic"),
         InlineKeyboardButton("💸 ارسال LIBER", callback_data="menu_transfer")],
        [InlineKeyboardButton("🎫 باشگاه مشتریان (۴ ماموریت هفتگی)", callback_data="menu_club")],
        [InlineKeyboardButton("🏅 لیگ کشورها", callback_data="league_menu"),
         InlineKeyboardButton("🎓 منتورشیپ", callback_data="mentor_menu")],
        [InlineKeyboardButton("🗺 همسایگی کشورها", callback_data="neighbors_menu"),
         InlineKeyboardButton("🔎 پروفایل عمومی", callback_data="profile_lookup_start")],
        [InlineKeyboardButton("🎖 برترین‌های سرور", callback_data="hall_of_fame"),
         InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings_menu")],
        [InlineKeyboardButton("🧾 تاریخچه‌ی تراکنش‌ها", callback_data="tx_history")],
        [InlineKeyboardButton("🔎 پیگیری سفارش", callback_data="track_order_start"),
         InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="support_contact_start")],
        [InlineKeyboardButton("🎯 ماموریت روزانه (اجباری)", callback_data="daily_mission")],
        [InlineKeyboardButton("⚔️ رقابت آنلاین", callback_data="competition_menu")],
        [InlineKeyboardButton("🎁 گیفت استارز (بوست پست)", callback_data="giftboost_menu"),
         InlineKeyboardButton("🚀 حمایت از کانال (بوست)", callback_data="channel_boost_menu")],
        [InlineKeyboardButton("❓ راهنما", callback_data="menu_help")],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def back_keyboard(target="main_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=target)]])


def market_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 خرید لیبر", callback_data="market_buy"),
         InlineKeyboardButton("🔴 فروش لیبر", callback_data="market_sell")],
        [InlineKeyboardButton("🎚 خرید با استپر", callback_data="market_stepper:buy"),
         InlineKeyboardButton("🎚 فروش با استپر", callback_data="market_stepper:sell")],
        [InlineKeyboardButton("📊 نمودار ۲۴ ساعت اخیر", callback_data="market_chart")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


def bank_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ واریز", callback_data="bank_deposit"),
         InlineKeyboardButton("➖ برداشت سپرده", callback_data="bank_withdraw")],
        [InlineKeyboardButton("💳 وام", callback_data="bank_loan")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


def chests_keyboard():
    rows = []
    for key, chest in CHEST_TABLE.items():
        cost_text = "رایگان" if not chest["cost"] else ", ".join(f"{v} {k}" for k, v in chest["cost"].items())
        rows.append([InlineKeyboardButton(f"🎁 {key} ({cost_text})", callback_data=f"chest_open:{key}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def subscription_menu_keyboard():
    rows = [[InlineKeyboardButton(tier["title"], callback_data=f"sub_tier:{key}")]
            for key, tier in SUBSCRIPTION_TIERS.items()]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def subscription_duration_keyboard(tier_key, discount_pct=0):
    tier = SUBSCRIPTION_TIERS[tier_key]
    rows = []
    for months, stars in tier["options"].items():
        if discount_pct:
            discounted = max(1, round(stars * (1 - discount_pct / 100)))
            label = f"{months} ماهه — {discounted}⭐ (به‌جای {stars}⭐ 🔥)"
        else:
            label = f"{months} ماهه — {stars}⭐"
        rows.append([InlineKeyboardButton(label, callback_data=f"sub_buy:{tier_key}:{months}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_subscription")])
    return InlineKeyboardMarkup(rows)


def withdraw_confirm_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تایید و ارسال درخواست", callback_data="withdraw_confirm")],
        [InlineKeyboardButton("❌ انصراف", callback_data="main_menu")],
    ])


def admin_withdraw_review_keyboard(request_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول و پرداخت شد", callback_data=f"admin_wd_approve:{request_id}"),
         InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_wd_reject:{request_id}")],
    ])


def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 درخواست‌های برداشت", callback_data="admin_pending_withdraws")],
        [InlineKeyboardButton("🎁 سفارش‌های گیفت در انتظار", callback_data="admin_pending_giftboost")],
        [InlineKeyboardButton("🚀 سفارش‌های بوست کانال در انتظار", callback_data="admin_pending_channelboost")],
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 افزودن سکه/لیبر به کاربر", callback_data="admin_give_currency")],
        [InlineKeyboardButton("🎫 فعال‌سازی دستی اشتراک", callback_data="admin_grant_sub")],
        [InlineKeyboardButton("🎁 ساخت کد هدیه", callback_data="giftcode_admin_create")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🚫 مدیریت کاربر (بن/رفع بن)", callback_data="admin_user_manage")],
        [InlineKeyboardButton("🔙 خروج از پنل", callback_data="main_menu")],
    ])


def admin_grant_sub_tier_keyboard():
    rows = [[InlineKeyboardButton(tier["title"], callback_data=f"admin_gsub_tier:{key}")]
            for key, tier in SUBSCRIPTION_TIERS.items()]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def admin_grant_sub_months_keyboard(tier_key):
    tier = SUBSCRIPTION_TIERS[tier_key]
    rows = [[InlineKeyboardButton(f"{months} ماهه", callback_data=f"admin_gsub_months:{tier_key}:{months}")]
            for months in tier["options"]]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin_grant_sub")])
    return InlineKeyboardMarkup(rows)


def admin_grant_sub_target_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 برای خودم (تست سریع)", callback_data="admin_gsub_self")],
        [InlineKeyboardButton("👤 برای کاربر دیگر (وارد کردن آیدی)", callback_data="admin_gsub_other")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_grant_sub")],
    ])


def competition_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ شروع مسابقه", callback_data="comp_start"),
         InlineKeyboardButton("🚪 خروج از صف", callback_data="comp_leave")],
        [InlineKeyboardButton("👤 پروفایل رقابتی", callback_data="comp_profile"),
         InlineKeyboardButton("🏆 برترین‌ها", callback_data="comp_top")],
        [InlineKeyboardButton("🎯 ماموریت امروز", callback_data="comp_mission"),
         InlineKeyboardButton("📆 فصل فعلی", callback_data="comp_season")],
        [InlineKeyboardButton("🥋 تکنیک‌های رقابتی", callback_data="technique_menu")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


# SECTION 4: COMPETITION HANDLERS — رقابت آنلاین رنک‌بندی‌شده
import time
import random
import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError


logger = logging.getLogger("LIBER.competition")

_last_start_time = {}


def _player_power(rank_index, user_id=None):
    """قدرت پایه‌ی بازیکن در یک مسابقه. اگر user_id داده شود، بونوس دائمی
    درخت تکنیک‌های رقابتی (handlers_competition_boost.py) هم اعمال می‌شود."""
    base = 40 + rank_index * 12
    power = base + random.randint(-10, 10)
    if user_id is not None:
        try:
            import handlers_competition_boost
            bonus_pct = handlers_competition_boost.get_technique_bonus_percent(user_id)
            if bonus_pct:
                power = round(power * (1 + bonus_pct / 100))
        except Exception:
            pass
    return power


def _play_match(power_a, power_b):
    score_a = score_b = 0
    for _ in range(5):
        roll_a = power_a + random.randint(-10, 10)
        roll_b = power_b + random.randint(-10, 10)
        if roll_a > roll_b:
            score_a += 1
        elif roll_b > roll_a:
            score_b += 1
    if score_a == score_b:
        return "draw", score_a, score_b
    return ("a" if score_a > score_b else "b"), score_a, score_b


_win_streaks = {}


def _apply_result(user_id, outcome):
    profile = get_comp_profile(user_id)
    rank_index = profile["rank_index"]

    if outcome == "loss":
        comp_record_result(user_id, "loss")
        _win_streaks[user_id] = 0
        return "😔 باختی. فقط هزینه‌ی ورود از دست رفت، مدالی کم نشد."

    medals_per_win = medals_per_win_for_rank(min(rank_index, MAX_RANK_INDEX - 1))

    if outcome == "draw":
        medals_gain = round(medals_per_win / 2, 2)
        liber_gain = MATCH_ENTRY_FEE
        comp_record_result(user_id, "draw", medals_gain, liber_gain)
        text = f"⚖️ تساوی شد! +{medals_gain} مدال، {liber_gain} LIBER (هزینه‌ی ورود) برگشت."
    else:
        reward = reward_for_rank(rank_index)
        comp_record_result(user_id, "win", medals_per_win, reward)
        text = f"🏆 بردی! +{medals_per_win} مدال، +{reward} LIBER"
        comp_daily_mission_add_win(user_id)
        _win_streaks[user_id] = _win_streaks.get(user_id, 0) + 1
        import handlers_social
        handlers_social.record_weekly_win(user_id)
        handlers_social.record_club_task_progress(user_id, "win2")

    new_rank = comp_promote_if_ready(
        user_id, wins_required_for_rank, medals_per_win_for_rank, MAX_RANK_INDEX
    )
    if new_rank is not None:
        text += f"\n\n🎉 ارتقا! رنک جدید شما: {RANKS[new_rank]}"

    log_transaction(user_id, "competition_match", outcome)
    return text


async def _resolve_match(bot, user_a, user_b, vs_bot):
    profile_a = get_comp_profile(user_a)
    power_a = _player_power(profile_a["rank_index"], user_a)

    if vs_bot:
        power_b = max(20, power_a + random.randint(-15, 15))
        outcome, score_a, score_b = _play_match(power_a, power_b)
        result = "win" if outcome == "a" else ("draw" if outcome == "draw" else "loss")
        text_a = _apply_result(user_a, result)
        try:
            await bot.send_message(user_a, f"⚔️ نتیجه‌ی مسابقه با ربات: {score_a} - {score_b}\n\n{text_a}")
        except TelegramError:
            pass
        if result == "win":
            import handlers_bonus
            await handlers_bonus.check_win_streak_achievement(user_a, _win_streaks.get(user_a, 0), bot)
        return

    profile_b = get_comp_profile(user_b)
    power_b = _player_power(profile_b["rank_index"], user_b)
    outcome, score_a, score_b = _play_match(power_a, power_b)

    if outcome == "draw":
        outcome_a, outcome_b = "draw", "draw"
    elif outcome == "a":
        outcome_a, outcome_b = "win", "loss"
    else:
        outcome_a, outcome_b = "loss", "win"

    text_a = _apply_result(user_a, outcome_a)
    text_b = _apply_result(user_b, outcome_b)

    user_a_info = get_user(user_a)
    user_b_info = get_user(user_b)
    name_a = user_a_info["first_name"] if user_a_info else "بازیکن ۱"
    name_b = user_b_info["first_name"] if user_b_info else "بازیکن ۲"

    try:
        await bot.send_message(user_a, f"⚔️ مسابقه با {name_b}! نتیجه: {score_a} - {score_b}\n\n{text_a}")
    except TelegramError:
        pass
    try:
        await bot.send_message(user_b, f"⚔️ مسابقه با {name_a}! نتیجه: {score_b} - {score_a}\n\n{text_b}")
    except TelegramError:
        pass

    import handlers_bonus
    if outcome_a == "win":
        await handlers_bonus.check_win_streak_achievement(user_a, _win_streaks.get(user_a, 0), bot)
    if outcome_b == "win":
        await handlers_bonus.check_win_streak_achievement(user_b, _win_streaks.get(user_b, 0), bot)


async def competition_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profile = get_comp_profile(update.effective_user.id)
    text = (
        f"⚔️ رقابت آنلاین LIBER\n\n"
        f"رنک فعلی: {RANKS[profile['rank_index']]}\n"
        f"مدال این رنک: {profile['medals']:.1f}\n"
        f"🏆 برد: {profile['wins']}  😔 باخت: {profile['losses']}  ⚖️ تساوی: {profile['draws']}\n\n"
        f"هزینه‌ی ورود به هر مسابقه: {MATCH_ENTRY_FEE} LIBER"
    )
    await update.message.reply_text(text, reply_markup=competition_menu_keyboard())


async def competition_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    profile = get_comp_profile(q.from_user.id)
    text = (
        f"⚔️ رقابت آنلاین LIBER\n\n"
        f"رنک فعلی: {RANKS[profile['rank_index']]}\n"
        f"مدال این رنک: {profile['medals']:.1f}\n"
        f"🏆 برد: {profile['wins']}  😔 باخت: {profile['losses']}  ⚖️ تساوی: {profile['draws']}\n\n"
        f"هزینه‌ی ورود به هر مسابقه: {MATCH_ENTRY_FEE} LIBER"
    )
    await q.edit_message_text(text, reply_markup=competition_menu_keyboard())


async def competition_profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    profile = get_comp_profile(q.from_user.id)
    text = (
        f"👤 پروفایل رقابتی\n\n"
        f"رنک: {RANKS[profile['rank_index']]}\n"
        f"مدال این رنک: {profile['medals']:.1f}\n"
        f"مدال فصل: {profile['season_medals']:.1f}\n"
        f"🏆 برد: {profile['wins']}  😔 باخت: {profile['losses']}  ⚖️ تساوی: {profile['draws']}"
    )
    await q.edit_message_text(text, reply_markup=competition_menu_keyboard())


async def competition_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    rows = comp_top_season(10)
    lines = ["🏆 برترین‌های فصل\n"]
    for i, r in enumerate(rows, start=1):
        u = get_user(r["user_id"])
        name = u["first_name"] if u else str(r["user_id"])
        lines.append(f"{i}. {name} — {RANKS[r['rank_index']]} ({r['season_medals']:.1f} مدال)")
    text = "\n".join(lines) if rows else "هنوز کسی بازی نکرده."
    await q.edit_message_text(text, reply_markup=competition_menu_keyboard())


async def competition_season_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    season = get_comp_season()
    now = int(time.time())
    days_left = max(0, (TOURNAMENT_INTERVAL_SECONDS - (now - season["started_at"])) // 86400)
    r = TOURNAMENT_REWARDS
    text = (
        f"📆 فصل {season['season_number']}\n\n"
        f"{days_left} روز تا پایان تورنمنت فصلی مانده.\n"
        f"در پایان فصل، ۳ نفر برتر خودکار جایزه می‌گیرند:\n"
        f"🥇 {r[1]} LIBER   🥈 {r[2]} LIBER   🥉 {r[3]} LIBER"
    )
    await q.edit_message_text(text, reply_markup=competition_menu_keyboard())


async def competition_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    row = comp_daily_mission_progress(user_id)

    if not row:
        text = f"🎯 ماموریت امروز: {COMPETITION_DAILY_MISSION_WINS} برد بگیر → {COMPETITION_DAILY_MISSION_REWARD} LIBER."
    elif row["claimed"]:
        text = "✅ جایزه‌ی امروز رو قبلاً گرفتی."
    elif row["wins_done"] >= row["wins_needed"]:
        comp_daily_mission_claim(user_id, COMPETITION_DAILY_MISSION_REWARD)
        text = f"🎉 ماموریت کامل شد! +{COMPETITION_DAILY_MISSION_REWARD} LIBER گرفتی."
    else:
        text = f"🎯 پیشرفت: {row['wins_done']}/{row['wins_needed']} برد."

    await q.edit_message_text(text, reply_markup=competition_menu_keyboard())


async def competition_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    comp_leave_queue(q.from_user.id)
    await q.edit_message_text("🚪 از صف مسابقه خارج شدی.", reply_markup=competition_menu_keyboard())


async def competition_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id

    now = time.monotonic()
    last = _last_start_time.get(user_id, 0)
    if now - last < MATCH_MIN_SECONDS_BETWEEN_STARTS:
        await q.answer("⏳ لطفاً چند ثانیه صبر کن و دوباره امتحان کن.", show_alert=True)
        return
    _last_start_time[user_id] = now

    if not has_done_daily_mission(user_id):
        await q.answer(
            "🔒 اول باید «🎯 ماموریت روزانه» رو از منوی اصلی انجام بدید تا بتونید وارد رقابت بشید.",
            show_alert=True,
        )
        return

    user = get_user(user_id)
    if not user or user["liber"] < MATCH_ENTRY_FEE:
        await q.answer(f"❌ حداقل {MATCH_ENTRY_FEE} LIBER برای ورود لازم است.", show_alert=True)
        return

    if comp_is_queued(user_id):
        await q.answer("⏳ شما در حال حاضر در صف انتظار هستید.", show_alert=True)
        return

    await q.answer()
    profile = get_comp_profile(user_id)
    opponent = comp_find_opponent(user_id, profile["rank_index"])

    update_balance(user_id, coin=0, liber=-MATCH_ENTRY_FEE)

    if opponent:
        comp_leave_queue(opponent["user_id"])
        await q.edit_message_text("⚔️ حریف پیدا شد! نتیجه به‌زودی برای هر دو نفر ارسال می‌شود...")
        await _resolve_match(context.bot, user_id, opponent["user_id"], vs_bot=False)
    else:
        comp_join_queue(user_id, profile["rank_index"])
        await q.edit_message_text(
            f"⏳ وارد صف شدی! منتظر حریف هم‌رنک ({RANKS[profile['rank_index']]}) هستیم.\n"
            f"اگر تا {MATCH_BOT_FALLBACK_SECONDS // 60} دقیقه حریف واقعی پیدا نشه، خودکار با ربات بازی می‌کنی.",
            reply_markup=competition_menu_keyboard(),
        )


async def queue_matchmaking_job(context: ContextTypes.DEFAULT_TYPE):
    now = int(time.time())
    queued = comp_all_queued()

    by_rank = {}
    for row in queued:
        by_rank.setdefault(row["rank_index"], []).append(row)

    matched = set()
    for rank_index, users in by_rank.items():
        while len(users) >= 2:
            u1 = users.pop(0)
            u2 = users.pop(0)
            comp_leave_queue(u1["user_id"])
            comp_leave_queue(u2["user_id"])
            matched.add(u1["user_id"])
            matched.add(u2["user_id"])
            await _resolve_match(context.bot, u1["user_id"], u2["user_id"], vs_bot=False)

    for row in queued:
        if row["user_id"] in matched:
            continue
        if now - row["joined_at"] >= MATCH_BOT_FALLBACK_SECONDS:
            comp_leave_queue(row["user_id"])
            await _resolve_match(context.bot, row["user_id"], None, vs_bot=True)


async def tournament_job(context: ContextTypes.DEFAULT_TYPE):
    season = get_comp_season()
    now = int(time.time())
    if now - season["started_at"] < TOURNAMENT_INTERVAL_SECONDS:
        return

    rows = comp_top_season(3)
    for i, row in enumerate(rows, start=1):
        if row["season_medals"] <= 0:
            continue
        reward = TOURNAMENT_REWARDS.get(i, 0)
        update_balance(row["user_id"], coin=0, liber=reward)
        log_transaction(row["user_id"], "tournament_reward", f"rank={i} reward={reward}")
        try:
            await context.bot.send_message(
                row["user_id"],
                f"🏆 تبریک! در تورنمنت فصلی رتبه‌ی {i} شدی و {reward} LIBER جایزه گرفتی! 🎉",
            )
        except TelegramError:
            pass

    new_season = comp_reset_season()

    for user_id in all_comp_user_ids():
        try:
            await context.bot.send_message(
                user_id,
                f"📆 فصل جدید شروع شد: فصل {new_season}!\nمدال فصلی همه صفر شد — رنک اصلی‌تون دست‌نخورده باقی موند.",
            )
        except TelegramError:
            pass

    logger.info(f"تورنمنت فصلی برگزار شد. فصل جدید: {new_season}")


COMPETITION_CALLBACKS = {
    "competition_menu": competition_menu_callback,
    "comp_profile": competition_profile_callback,
    "comp_top": competition_top_callback,
    "comp_season": competition_season_callback,
    "comp_mission": competition_mission_callback,
    "comp_leave": competition_leave_callback,
    "comp_start": competition_start_callback,
}


async def competition_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    handler = COMPETITION_CALLBACKS.get(data)
    if handler:
        await handler(update, context)


# SECTION 5: USER HANDLERS — منو، بازار، بانک، صندوق، اشتراک، برداشت
import calendar

from telegram import LabeledPrice, InlineKeyboardButton


_action_log = {}


async def spam_guard(user_id, update: Update) -> bool:
    now = time.time()
    hits = _action_log.setdefault(user_id, [])
    hits[:] = [t for t in hits if now - t < SPAM_WINDOW_SECONDS]
    hits.append(now)
    if len(hits) <= SPAM_MAX_ACTIONS:
        return False

    warnings, banned = add_warning(user_id)
    target = update.callback_query.message if update.callback_query else update.message
    if banned:
        await target.reply_text("🚫 به دلیل اسپم مکرر، حساب شما مسدود شد.")
    else:
        await target.reply_text(
            f"⚠️ اخطار {warnings}/{SPAM_WARN_LIMIT}: لطفاً سریع دکمه نزنید. "
            f"با رسیدن به {SPAM_WARN_LIMIT} اخطار، حساب مسدود می‌شود."
        )
    return True


def get_subscription_perks(user_id):
    tier_key = get_active_subscription_tier(user_id)
    if not tier_key:
        return None
    return SUBSCRIPTION_TIERS.get(tier_key)


async def is_member_of_all_channels(bot, user_id) -> bool:
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramError:
            return False
    return True


async def post_to_orders_channel(bot, text, reply_markup=None):
    """پیام سفارش/آپدیت وضعیت رو تو کانال سفارشات منتشر می‌کنه؛ اگه ربات
    ادمین اون کانال نباشه فقط لاگ می‌کنه، کرش نمی‌کنه."""
    try:
        await bot.send_message(ORDERS_CHANNEL_ID, text, reply_markup=reply_markup)
    except TelegramError as e:
        logger.warning(f"ارسال به کانال سفارشات ناموفق بود: {e}")


async def _show_onboarding_or_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """منطق کامل (قوانین/کشور/منو) برای کوتاه ماندن این فایل به handlers_extra.py منتقل شده."""
    import handlers_extra
    await handlers_extra.show_onboarding_or_menu(update, context, send_main_menu)


async def onboarding_accept_rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    import handlers_extra
    await handlers_extra.onboarding_accept_rules_callback(update, context)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = None
    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referred_by = ref_id
        except ValueError:
            pass

    is_new = ensure_user(user.id, user.username or "", user.first_name or "", referred_by)

    if is_new and referred_by and get_user(referred_by):
        bonus = REFERRAL_BONUS_PREMIUM if user.is_premium else REFERRAL_BONUS_NORMAL
        registered = register_referral(referred_by, user.id, bonus)
        if registered:
            try:
                await context.bot.send_message(
                    referred_by,
                    f"🎉 یک دوست جدید با لینک شما عضو شد! {bonus} LIBER به شما اضافه شد."
                )
            except TelegramError:
                pass

    if not await is_member_of_all_channels(context.bot, user.id):
        await update.message.reply_text(
            "برای استفاده از ربات ابتدا باید در کانال(های) زیر عضو شوید:",
            reply_markup=force_join_keyboard(),
        )
        return

    await _show_onboarding_or_menu(update, context)


async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, greet=False):
    user = update.effective_user
    is_admin = user.id in ADMIN_IDS
    text = (
        f"سلام جناب {user.first_name} 👋 به LIBER خوش آمدید!\n\n"
        "از دکمه‌های زیر برای مدیریت دارایی، بازار، اشتراک و برداشت استفاده کنید:"
        if greet else "🏠 منوی اصلی"
    )
    markup = main_menu_keyboard(is_admin=is_admin)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.message.reply_text(text, reply_markup=markup)


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if await is_member_of_all_channels(context.bot, q.from_user.id):
        await q.answer()
        await _show_onboarding_or_menu(update, context)
    else:
        await q.answer("هنوز در همه‌ی کانال‌ها عضو نشده‌اید ❌", show_alert=True)


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    u = get_user(user_id)
    if not u:
        await q.edit_message_text("ابتدا /start را بزنید.")
        return

    sub_block = "🎫 اشتراک: ندارد — از «⭐ اشتراک ویژه» یکی بگیر و مزایا رو فعال کن!"
    tier_key = get_active_subscription_tier(user_id)
    if tier_key:
        tier = SUBSCRIPTION_TIERS[tier_key]
        days_left = (u["subscription_expires"] - int(time.time())) // 86400
        perks_lines = "\n".join(f"   ✔️ {p}" for p in tier["perks"])
        sub_block = (
            f"{tier['badge']} اشتراک فعال: {tier['title']} ({days_left} روز باقی‌مانده)\n{perks_lines}"
        )

    text = (
        f"👤 پروفایل شما\n\n"
        f"🪙 سکه: {u['coin']}\n"
        f"💎 الماس: {u['diamond']}\n"
        f"🔷 LIBER: {round(u['liber'], 2)}\n"
        f"⭐ سطح: {u['level']} ({u['xp']} XP)\n"
        f"🏦 موجودی بانک: {round(u['bank_balance'], 2)}\n\n"
        f"{sub_block}\n"
    )

    markup = back_keyboard()
    if tier_key:
        import handlers_bonus
        vip_rows = handlers_bonus.vip_bonus_button_rows(user_id)
        if vip_rows:
            from telegram import InlineKeyboardMarkup
            markup = InlineKeyboardMarkup(vip_rows + [[markup.keyboard[0][0]]])

    await q.edit_message_text(text, reply_markup=markup)


async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    price = get_market_price()
    text = (
        f"💹 بازار LIBER\n\n"
        f"قیمت فعلی هر ۱ LIBER: {price} سکه\n"
        f"کارمزد خرید: {BUY_FEE_PERCENT}٪  |  کارمزد فروش: {SELL_FEE_PERCENT}٪\n"
        f"قیمت هر یک ساعت بروزرسانی می‌شود."
    )
    await q.edit_message_text(text, reply_markup=market_keyboard())


async def market_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "market_buy_amount"
    await q.edit_message_text(
        "چند LIBER می‌خواهید بخرید؟ عدد را ارسال کنید.",
        reply_markup=back_keyboard("menu_market"),
    )


async def market_sell_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "market_sell_amount"
    await q.edit_message_text(
        "چند LIBER می‌خواهید بفروشید؟ عدد را ارسال کنید.",
        reply_markup=back_keyboard("menu_market"),
    )


async def _do_market_buy(update, context, amount):
    user_id = update.effective_user.id
    price = get_market_price()
    perks = get_subscription_perks(user_id)
    fee_pct = BUY_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["market_fee_discount_percent"] / 100), 4)
    cost = round(amount * price * (1 + fee_pct / 100), 2)
    u = get_user(user_id)
    if u["coin"] < cost:
        await update.message.reply_text(f"❌ سکه کافی ندارید. نیاز: {cost}، موجودی: {u['coin']}")
        return
    update_balance(user_id, coin=-cost, liber=amount)
    log_transaction(user_id, "market_buy", f"{amount} LIBER @ {price}")
    import handlers_social
    handlers_social.record_club_task_progress(user_id, "trade2")
    discount_note = f" (🎫 با تخفیف اشتراک: {fee_pct}٪ کارمزد)" if perks else ""
    await update.message.reply_text(
        f"✅ خرید موفق: {amount} LIBER با {cost} سکه.{discount_note}",
        reply_markup=back_keyboard(),
    )


async def _do_market_sell(update, context, amount):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if u["liber"] < amount:
        await update.message.reply_text(f"❌ LIBER کافی ندارید. موجودی: {round(u['liber'],2)}")
        return
    price = get_market_price()
    perks = get_subscription_perks(user_id)
    fee_pct = SELL_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["market_fee_discount_percent"] / 100), 4)
    gain = round(amount * price * (1 - fee_pct / 100), 2)
    update_balance(user_id, coin=gain, liber=-amount)
    log_transaction(user_id, "market_sell", f"{amount} LIBER @ {price}")
    import handlers_social
    handlers_social.record_club_task_progress(user_id, "trade2")
    discount_note = f" (🎫 با تخفیف اشتراک: {fee_pct}٪ کارمزد)" if perks else ""
    await update.message.reply_text(
        f"✅ فروش موفق: {amount} LIBER به ازای {gain} سکه.{discount_note}",
        reply_markup=back_keyboard(),
    )


async def bank_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    interest = apply_daily_interest(q.from_user.id)
    u = get_user(q.from_user.id)
    note = f"\n\n💰 سود روزانه‌ی {interest} به حسابتان اضافه شد." if interest else ""
    loan_note = f"\n💳 بدهی وام فعلی: {round(u['loan_balance'], 2)} LIBER" if u["loan_balance"] > 0 else ""
    text = (
        f"🏦 بانک LIBER\n\n"
        f"موجودی سپرده: {round(u['bank_balance'], 2)} سکه\n"
        f"سود روزانه: {BANK_INTEREST_PERCENT}٪{loan_note}{note}"
    )
    await q.edit_message_text(text, reply_markup=bank_keyboard())


async def bank_deposit_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "bank_deposit_amount"
    await q.edit_message_text("چند سکه می‌خواهید واریز کنید؟", reply_markup=back_keyboard("menu_bank"))


async def bank_withdraw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    total = bank_withdraw_all(q.from_user.id)
    if total <= 0:
        await q.edit_message_text("سپرده‌ای برای برداشت وجود ندارد.", reply_markup=back_keyboard("menu_bank"))
        return
    await q.edit_message_text(f"✅ {round(total,2)} سکه برداشت شد.", reply_markup=back_keyboard("menu_bank"))


async def bank_loan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    u = get_user(user_id)
    max_loan = max_loan_for_level(u["level"], LOAN_BASE_PER_LEVEL, MAX_LOAN_MULTIPLIER)

    if u["loan_balance"] > 0:
        text = (
            f"💳 وام\n\n"
            f"بدهی فعلی شما: {round(u['loan_balance'], 2)} LIBER\n\n"
            "تا تسویه‌ی کامل نمی‌تونید وام جدید بگیرید. می‌تونید بخشی یا کل بدهی رو پرداخت کنید:"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 پرداخت وام", callback_data="loan_repay_start")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_bank")],
        ])
    else:
        text = (
            f"💳 وام\n\n"
            f"سقف وام شما (بر اساس سطح {u['level']}): {max_loan} LIBER\n"
            f"کارمزد: {LOAN_INTEREST_PERCENT}٪ (یعنی مبلغ بدهی کمی بیشتر از مبلغ دریافتی می‌شه)\n\n"
            "چقدر می‌خواید وام بگیرید؟"
        )
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 درخواست وام", callback_data="loan_take_start")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_bank")],
        ])
    await q.edit_message_text(text, reply_markup=markup)


async def loan_take_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    u = get_user(user_id)
    if u["loan_balance"] > 0:
        await q.answer("اول باید وام قبلی رو تسویه کنید.", show_alert=True)
        return
    await q.answer()
    max_loan = max_loan_for_level(u["level"], LOAN_BASE_PER_LEVEL, MAX_LOAN_MULTIPLIER)
    context.user_data["awaiting"] = "loan_take_amount"
    await q.edit_message_text(f"💳 چقدر LIBER می‌خواید وام بگیرید؟ (حداکثر {max_loan})")


async def loan_repay_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "loan_repay_amount"
    await q.edit_message_text("💰 چقدر می‌خواید پرداخت کنید؟")


async def _do_loan_take(update, context, amount):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if u["loan_balance"] > 0:
        await update.message.reply_text("اول باید وام قبلی رو تسویه کنید.", reply_markup=back_keyboard("menu_bank"))
        return
    max_loan = max_loan_for_level(u["level"], LOAN_BASE_PER_LEVEL, MAX_LOAN_MULTIPLIER)
    if amount <= 0 or amount > max_loan:
        await update.message.reply_text(f"❌ مبلغ باید بین ۱ تا {max_loan} باشد.")
        return
    owed = take_loan(user_id, amount, LOAN_INTEREST_PERCENT)
    log_transaction(user_id, "LOAN_TAKE", f"amount={amount} owed={owed}")
    await update.message.reply_text(
        f"✅ {amount} LIBER به حسابت اضافه شد.\n💳 بدهی شما (با کارمزد): {owed} LIBER",
        reply_markup=back_keyboard("menu_bank"),
    )


async def _do_loan_repay(update, context, amount):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if u["loan_balance"] <= 0:
        await update.message.reply_text("بدهی‌ای برای پرداخت ندارید.", reply_markup=back_keyboard("menu_bank"))
        return
    if u["liber"] < amount:
        await update.message.reply_text("❌ موجودی LIBER کافی نیست.")
        return
    actual = repay_loan(user_id, amount)
    log_transaction(user_id, "LOAN_REPAY", str(actual))
    remaining = get_user(user_id)["loan_balance"]
    note = "✅ وام کامل تسویه شد!" if remaining <= 0 else f"باقی‌مانده‌ی بدهی: {round(remaining, 2)} LIBER"
    await update.message.reply_text(f"💰 {actual} LIBER پرداخت شد.\n{note}", reply_markup=back_keyboard("menu_bank"))


async def _do_bank_deposit(update, context, amount):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if u["coin"] < amount:
        await update.message.reply_text("❌ سکه کافی ندارید.")
        return
    bank_deposit(user_id, amount)
    await update.message.reply_text(f"✅ {amount} سکه واریز شد.", reply_markup=back_keyboard())


async def chests_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🏪 صندوق موردنظر را انتخاب کنید:", reply_markup=chests_keyboard())


async def chest_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    chest_key = q.data.split(":", 1)[1]
    chest = CHEST_TABLE.get(chest_key)
    if not chest:
        await q.answer()
        await q.edit_message_text("صندوق نامعتبر است.", reply_markup=back_keyboard())
        return

    user_id = q.from_user.id

    if chest_key == "free" and not has_done_daily_mission(user_id):
        await q.answer(
            "🔒 اول باید «🎯 ماموریت روزانه» رو از منو انجام بدید تا صندوق رایگان باز شه.",
            show_alert=True,
        )
        return

    u = get_user(user_id)
    for currency, amount in chest["cost"].items():
        if u[currency] < amount:
            await q.answer(f"❌ {currency} کافی ندارید.", show_alert=True)
            return

    deltas = {"coin": 0, "liber": 0, "diamond": 0, "xp": 0}
    for currency, amount in chest["cost"].items():
        deltas[currency] -= amount

    await q.answer()
    reward_lines = []
    for reward_type, low, high in chest["rewards"]:
        amount = random.randint(low, high)
        deltas[reward_type] = deltas.get(reward_type, 0) + amount
        reward_lines.append(f"+{amount} {reward_type}")

    update_balance(user_id, coin=deltas.get("coin", 0), liber=deltas.get("liber", 0),
                       diamond=deltas.get("diamond", 0), xp=deltas.get("xp", 0))
    log_transaction(user_id, "chest_open", chest_key)

    import handlers_social
    handlers_social.record_club_task_progress(user_id, "chest2")

    await q.edit_message_text(
        f"🎉 صندوق {chest_key} باز شد!\n\n" + "\n".join(reward_lines),
        reply_markup=back_keyboard("menu_chests"),
    )


async def daily_mission_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    u = get_user(user_id)
    now = int(time.time())
    today_start = int(now // 86400) * 86400

    if u["last_daily"] >= today_start:
        tomorrow_start = today_start + 86400
        hours = (tomorrow_start - now) // 3600
        await q.answer(f"⏳ ماموریت امروز رو قبلاً انجام دادی. تا {hours} ساعت دیگر ماموریت جدید فعال می‌شود.", show_alert=True)
        return

    await q.answer()
    perks = get_subscription_perks(user_id)
    liber_reward = DAILY_MISSION_LIBER
    xp_reward = DAILY_MISSION_XP
    bonus_note = ""
    if perks:
        bonus_pct = perks["daily_bonus_percent"]
        liber_reward = round(liber_reward * (1 + bonus_pct / 100), 2)
        xp_reward = round(xp_reward * (1 + bonus_pct / 100))
        bonus_note = f" (🎫 شامل {bonus_pct}٪ بونوس اشتراک {perks['title']})"

    # بونوس منتورشیپ (اگه کاربر الان شاگرد یک نفره)
    import handlers_features2
    mentee_bonus_pct = handlers_features2.get_mentee_bonus_percent(user_id)
    if mentee_bonus_pct:
        liber_reward = round(liber_reward * (1 + mentee_bonus_pct / 100), 2)
        bonus_note += f" (🎓 شامل {mentee_bonus_pct}٪ بونوس منتورشیپ)"

    update_balance(user_id, liber=liber_reward, xp=xp_reward)
    import handlers_social
    handlers_social.record_club_task_progress(user_id, "daily3")
    with get_conn() as conn:
        conn.execute("UPDATE users SET last_daily = ? WHERE user_id = ?", (now, user_id))

    # به منتور (اگه داره) خبر و پاداش می‌دیم
    await handlers_features2.apply_mentorship_daily_bonus(user_id, context.bot)

    # استریک روزانه
    import handlers_features3
    streak_note = await handlers_features3.record_daily_streak(user_id, context.bot)

    await q.edit_message_text(
        f"✅ ماموریت روزانه انجام شد!\n+{liber_reward} LIBER, +{xp_reward} XP{bonus_note}\n\n"
        f"🔓 حالا صندوق رایگان و رقابت آنلاین امروز برات باز شدن!{streak_note}",
        reply_markup=back_keyboard(),
    )


async def referral_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    bot_username = (await context.bot.get_me()).username
    user_id = q.from_user.id
    link = f"https://t.me/{bot_username}?start={user_id}"
    count = count_referrals(user_id)

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT r.invitee_id, r.bonus_liber, u.first_name FROM referrals r
               LEFT JOIN users u ON u.user_id = r.invitee_id
               WHERE r.inviter_id = ? ORDER BY r.created_at DESC LIMIT 15""",
            (user_id,),
        ).fetchall()

    sub_lines = ""
    if rows:
        sub_lines = "\n\n👤 زیرمجموعه‌های شما:\n"
        for r in rows:
            name = r["first_name"] or str(r["invitee_id"])
            kind = "پرمیوم 💎" if r["bonus_liber"] == REFERRAL_BONUS_PREMIUM else "عادی"
            sub_lines += f"  • {name} — {kind} (+{r['bonus_liber']} LIBER)\n"

    text = (
        f"👥 دعوت دوستان\n\n"
        f"لینک اختصاصی شما:\n{link}\n\n"
        f"🎁 پاداش هر دعوت‌شده‌ی عادی: {REFERRAL_BONUS_NORMAL} LIBER\n"
        f"🎁 پاداش هر دعوت‌شده‌ی پرمیوم تلگرام: {REFERRAL_BONUS_PREMIUM} LIBER\n\n"
        f"تعداد دعوت‌های موفق شما: {count}"
        f"{sub_lines}"
    )
    await q.edit_message_text(text, reply_markup=back_keyboard())


def is_month_end_today():
    now = time.gmtime()
    last_day = calendar.monthrange(now.tm_year, now.tm_mon)[1]
    return now.tm_mday == last_day


def _discounted_stars(tier_key, stars):
    if not is_month_end_today():
        return stars, 0
    pct = MONTH_END_DISCOUNT_PERCENT.get(tier_key, 0)
    if not pct:
        return stars, 0
    discounted = max(1, round(stars * (1 - pct / 100)))
    return discounted, pct


async def subscription_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    banner = ""
    if is_month_end_today():
        banner = (
            "🔥 امروز آخرین روز ماهه! تخفیف ویژه‌ی پایان ماه فعاله:\n"
            f"عادی ۵٪ | دراگون ۱۰٪ | لیبری ۱۵٪ تخفیف — فقط امروز ⏳\n\n"
        )
    await q.edit_message_text(
        banner + "⭐ یکی از تعرفه‌های اشتراک را انتخاب کنید:", reply_markup=subscription_menu_keyboard()
    )


async def subscription_tier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    tier_key = q.data.split(":", 1)[1]
    tier = SUBSCRIPTION_TIERS[tier_key]
    perks = "\n".join(f"• {p}" for p in tier["perks"])
    discount_pct = MONTH_END_DISCOUNT_PERCENT.get(tier_key, 0) if is_month_end_today() else 0
    text = f"{tier['title']}\n\n{perks}\n\nمدت را انتخاب کنید:"
    await q.edit_message_text(text, reply_markup=subscription_duration_keyboard(tier_key, discount_pct))


async def subscription_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, tier_key, months = q.data.split(":")
    months = int(months)
    tier = SUBSCRIPTION_TIERS[tier_key]
    base_stars = tier["options"][months]
    stars, discount_pct = _discounted_stars(tier_key, base_stars)

    context.user_data["pending_sub"] = {"tier": tier_key, "months": months}

    title = f"{tier['title']} - {months} ماهه"
    description = f"خرید {tier['title']} به مدت {months} ماه"
    if discount_pct:
        title += f" ({discount_pct}٪ تخفیف پایان ماه 🔥)"
        description += f" — با {discount_pct}٪ تخفیف ویژه‌ی امروز!"

    await context.bot.send_invoice(
        chat_id=q.from_user.id,
        title=title,
        description=description,
        payload=f"sub:{tier_key}:{months}:{q.from_user.id}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(label=tier["title"], amount=stars)],
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload_parts = payment.invoice_payload.split(":")
    if len(payload_parts) != 4 or payload_parts[0] != "sub":
        await update.message.reply_text("خطا در پردازش پرداخت. با ادمین تماس بگیرید.")
        return

    _, tier_key, months, user_id_str = payload_parts
    user_id = int(user_id_str)
    months = int(months)
    stars = payment.total_amount

    new_expiry = grant_subscription(
        user_id, tier_key, months, stars, payment.telegram_payment_charge_id
    )
    tier = SUBSCRIPTION_TIERS[tier_key]
    perks_text = "\n".join(f"✔️ {p}" for p in tier["perks"])
    user = update.effective_user
    username_display = f"@{user.username}" if user.username else user.first_name
    expiry_str = time.strftime("%Y/%m/%d — %H:%M UTC", time.gmtime(new_expiry))

    await update.message.reply_text(
        f"🎉 تراکنش با موفقیت انجام شد!\n\n"
        f"👤 کاربر: {username_display}\n"
        f"{tier['badge']} اشتراک: {tier['title']}\n"
        f"⏳ مدت: {months} ماه\n"
        f"📅 اعتبار تا: {expiry_str}\n\n"
        f"🎁 مزایای فعال‌شده:\n{perks_text}\n\n"
        "از همین حالا فعاله — از منو لذت ببرید! 🥂",
        reply_markup=back_keyboard(),
    )

    import handlers_bonus
    await handlers_bonus.check_first_subscription_achievement(user_id, context.bot)
    await handlers_bonus.check_whale_status(user_id, context.bot)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"💳 پرداخت استارز جدید\nکاربر: {user_id}\nتعرفه: {tier['title']}\nمدت: {months} ماه\nمبلغ: {stars}⭐",
            )
        except TelegramError:
            pass


async def withdraw_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    u = get_user(q.from_user.id)
    if u["liber"] < MIN_WITHDRAW_LIBER:
        await q.edit_message_text(
            f"❌ حداقل موجودی برای برداشت {MIN_WITHDRAW_LIBER} LIBER است.\n"
            f"موجودی فعلی شما: {round(u['liber'], 2)} LIBER",
            reply_markup=back_keyboard(),
        )
        return
    context.user_data["awaiting"] = "withdraw_amount"
    await q.edit_message_text(
        f"📤 برداشت TON\n\nموجودی شما: {round(u['liber'],2)} LIBER\n"
        f"کارمزد برداشت: {WITHDRAW_FEE_PERCENT}٪\n\n"
        f"چه مقدار LIBER می‌خواهید برداشت کنید؟ (حداقل {MIN_WITHDRAW_LIBER})",
        reply_markup=back_keyboard(),
    )


async def _do_withdraw_amount(update, context, amount):
    user_id = update.effective_user.id
    u = get_user(user_id)
    if amount < MIN_WITHDRAW_LIBER:
        await update.message.reply_text(f"❌ حداقل مقدار برداشت {MIN_WITHDRAW_LIBER} LIBER است.")
        return
    if u["liber"] < amount:
        await update.message.reply_text("❌ موجودی کافی نیست.")
        return

    context.user_data["withdraw_amount"] = amount
    context.user_data["awaiting"] = "withdraw_address"
    await update.message.reply_text("لطفاً آدرس ولت TonKeeper خود را وارد کنید:")


async def _do_withdraw_address(update, context, address):
    context.user_data["withdraw_address"] = address
    context.user_data["awaiting"] = None
    user_id = update.effective_user.id
    amount = context.user_data.get("withdraw_amount", 0)
    perks = get_subscription_perks(user_id)
    fee_pct = WITHDRAW_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["withdraw_fee_discount_percent"] / 100), 4)
    fee = round(amount * fee_pct / 100, 2)
    net = round(amount - fee, 2)
    ton_amount = round(net / MARKET_BASE_PRICE, 4)
    discount_note = f" (🎫 با تخفیف اشتراک: {fee_pct}٪ کارمزد)" if perks else ""

    text = (
        f"لطفاً بررسی و تایید کنید:\n\n"
        f"مقدار برداشت: {amount} LIBER\n"
        f"کارمزد: {fee} LIBER{discount_note}\n"
        f"خالص: {net} LIBER  (≈ {ton_amount} TON)\n"
        f"آدرس مقصد: {address}\n"
    )
    await update.message.reply_text(text, reply_markup=withdraw_confirm_keyboard())


async def withdraw_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    amount = context.user_data.get("withdraw_amount")
    address = context.user_data.get("withdraw_address")
    if not amount or not address:
        await q.edit_message_text("درخواست منقضی شده، دوباره تلاش کنید.", reply_markup=back_keyboard())
        return

    perks = get_subscription_perks(user_id)
    fee_pct = WITHDRAW_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["withdraw_fee_discount_percent"] / 100), 4)
    fee = round(amount * fee_pct / 100, 2)
    net = round(amount - fee, 2)
    ton_amount = round(net / MARKET_BASE_PRICE, 4)

    request_id = create_withdraw_request(user_id, amount, fee, ton_amount, address)
    context.user_data["withdraw_amount"] = None
    context.user_data["withdraw_address"] = None

    await q.edit_message_text(WITHDRAW_PENDING_TEXT, reply_markup=back_keyboard())

    await post_to_orders_channel(
        context.bot,
        f"📥 سفارش جدید — برداشت TON\n\n"
        f"🎫 کد پیگیری: #{request_id}\n"
        f"نوع: برداشت TON\n"
        f"مقدار: {amount} LIBER (خالص {net})\n"
        f"آدرس تونکیپر: {address}\n"
        f"وضعیت: ⏳ در حال بررسی",
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📥 درخواست برداشت جدید #{request_id}\n"
                f"کاربر: {user_id}\n"
                f"مقدار: {amount} LIBER (خالص {net})\n"
                f"معادل: {ton_amount} TON\n"
                f"آدرس: {address}",
                reply_markup=admin_withdraw_review_keyboard(request_id),
            )
        except TelegramError:
            pass

    import handlers_bonus
    await handlers_bonus.check_first_withdraw_achievement(user_id, context.bot)


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        "❓ راهنمای ربات LIBER\n\n"
        "• همه‌ی عملیات از طریق دکمه‌های شیشه‌ای انجام می‌شود.\n"
        "• LIBER ارز اصلی داخل ربات است که با سکه در بازار معامله می‌شود.\n"
        "• با دعوت دوستان، انجام ماموریت روزانه و باز کردن صندوق‌ها LIBER جمع کنید.\n"
        "🔒 ماموریت روزانه اجباری است: تا انجامش ندید، نه صندوق رایگان باز می‌شه نه می‌تونید وارد رقابت آنلاین بشید.\n"
        f"• حداقل برداشت {MIN_WITHDRAW_LIBER} LIBER است.\n"
        "• اشتراک ویژه با استارز تلگرام قابل خرید است و مزایای اقتصادی می‌دهد."
    )
    await q.edit_message_text(text, reply_markup=back_keyboard())


async def text_message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_banned(user_id):
        return

    if await spam_guard(user_id, update):
        return

    import admin_panel
    if await admin_panel.admin_text_router(update, context):
        return

    import handlers_extra
    if await handlers_extra.extra_text_router(update, context):
        return

    import handlers_bonus
    if await handlers_bonus.bonus_text_router(update, context):
        return

    import handlers_social
    if await handlers_social.social_text_router(update, context):
        return

    import handlers_war
    if await handlers_war.war_text_router(update, context):
        return

    import handlers_market
    if await handlers_market.market_text_router(update, context):
        return

    import handlers_country_alliance
    if await handlers_country_alliance.country_alliance_text_router(update, context):
        return

    import handlers_competition_boost
    if await handlers_competition_boost.boost_text_router(update, context):
        return

    import handlers_features2
    if await handlers_features2.features2_text_router(update, context):
        return

    import handlers_features3
    if await handlers_features3.features3_text_router(update, context):
        return

    import handlers_support
    if await handlers_support.support_text_router(update, context):
        return

    awaiting = context.user_data.get("awaiting")
    raw_text = update.message.text.strip()

    if awaiting in ("market_buy_amount", "market_sell_amount", "bank_deposit_amount", "withdraw_amount",
                    "loan_take_amount", "loan_repay_amount"):
        try:
            amount = float(raw_text)
            if amount <= 0:
                raise ValueError
        except ValueError:
            await update.message.reply_text("لطفاً یک عدد معتبر و مثبت وارد کنید.")
            return

        context.user_data["awaiting"] = None
        if awaiting == "market_buy_amount":
            await _do_market_buy(update, context, amount)
        elif awaiting == "market_sell_amount":
            await _do_market_sell(update, context, amount)
        elif awaiting == "bank_deposit_amount":
            await _do_bank_deposit(update, context, amount)
        elif awaiting == "withdraw_amount":
            await _do_withdraw_amount(update, context, amount)
        elif awaiting == "loan_take_amount":
            await _do_loan_take(update, context, amount)
        elif awaiting == "loan_repay_amount":
            await _do_loan_repay(update, context, amount)
        return

    if awaiting == "withdraw_address":
        await _do_withdraw_address(update, context, raw_text)
        return

    await send_main_menu(update, context)


SIMPLE_CALLBACKS = {
    "main_menu": send_main_menu,
    "menu_profile": profile_callback,
    "menu_market": market_callback,
    "market_buy": market_buy_callback,
    "market_sell": market_sell_callback,
    "menu_bank": bank_callback,
    "bank_deposit": bank_deposit_callback,
    "bank_withdraw": bank_withdraw_callback,
    "bank_loan": bank_loan_callback,
    "loan_take_start": loan_take_start_callback,
    "loan_repay_start": loan_repay_start_callback,
    "menu_chests": chests_callback,
    "menu_subscription": subscription_menu_callback,
    "menu_referral": referral_callback,
    "withdraw_start": withdraw_start_callback,
    "withdraw_confirm": withdraw_confirm_callback,
    "daily_mission": daily_mission_callback,
    "menu_help": help_callback,
    "check_join": check_join_callback,
    "onboarding_accept_rules": onboarding_accept_rules_callback,
}


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id

    if is_banned(user_id):
        await q.answer("🚫 حساب شما مسدود است.", show_alert=True)
        return

    if await spam_guard(user_id, update):
        return

    data = q.data

    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return

    if data.startswith("chest_open:"):
        await chest_open_callback(update, context)
    elif data.startswith("sub_tier:"):
        await subscription_tier_callback(update, context)
    elif data.startswith("sub_buy:"):
        await subscription_buy_callback(update, context)
    elif data.startswith("comp") or data == "competition_menu":
            await competition_router(update, context)
    elif data.startswith("admin"):
        import admin_panel
        await admin_panel.admin_router(update, context)
    else:
        import handlers_extra
        handled = await handlers_extra.extra_callback_router(update, context)
        if not handled:
            import handlers_bonus
            handled = await handlers_bonus.bonus_callback_router(update, context)
        if not handled:
            import handlers_social
            handled = await handlers_social.social_callback_router(update, context)
        if not handled:
            import handlers_clanwar
            handled = await handlers_clanwar.clanwar_callback_router(update, context)
        if not handled:
            import handlers_military
            handled = await handlers_military.military_callback_router(update, context)
        if not handled:
            import handlers_war
            handled = await handlers_war.war_callback_router(update, context)
        if not handled:
            import handlers_market
            handled = await handlers_market.market_callback_router(update, context)
        if not handled:
            import handlers_country_alliance
            handled = await handlers_country_alliance.country_alliance_callback_router(update, context)
        if not handled:
            import handlers_competition_boost
            handled = await handlers_competition_boost.boost_callback_router(update, context)
        if not handled:
            import handlers_features2
            handled = await handlers_features2.features2_callback_router(update, context)
        if not handled:
            import handlers_features3
            handled = await handlers_features3.features3_callback_router(update, context)
        if not handled:
            import handlers_support
            await handlers_support.support_callback_router(update, context)


# SECTION 6: MAIN — اجرای ربات
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("LIBER.main")


async def admin_secret_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    await update.message.reply_text("👑 پنل مدیریت LIBER", reply_markup=admin_panel_keyboard())


async def error_handler(update, context: ContextTypes.DEFAULT_TYPE):
    logger.error("خطا در پردازش آپدیت:", exc_info=context.error)


def build_application() -> Application:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CommandHandler(ADMIN_SECRET_COMMAND.lstrip("/"), admin_secret_command))
    app.add_handler(CallbackQueryHandler(callback_router))
    app.add_handler(CommandHandler("competition", competition_command))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_router))
    app.add_error_handler(error_handler)

    return app


def schedule_jobs(app: Application):
    jq = app.job_queue
    if jq is None:
        logger.warning("job_queue فعال نیست — برای فعال‌سازی: pip install 'python-telegram-bot[job-queue]'")
        return

    jq.run_repeating(
        lambda context: _fluctuate_market_job(context),
        interval=MARKET_UPDATE_INTERVAL_SECONDS,
        first=60,
    )
    jq.run_repeating(queue_matchmaking_job, interval=MATCH_QUEUE_CHECK_SECONDS, first=30)
    jq.run_repeating(tournament_job, interval=86400, first=120)
    jq.run_repeating(_referral_monthly_job, interval=86400, first=180)
    jq.run_repeating(_vip_tournament_job, interval=86400, first=200)
    jq.run_repeating(_clan_war_matching_job, interval=180, first=90)
    jq.run_repeating(_clan_tournament_job, interval=86400, first=240)
    jq.run_repeating(_server_war_job, interval=180, first=60)
    # ⚡ جایزه‌ی برق‌آسا حذف شد (طبق درخواست کاربر) — دیگر هیچ دوری اجرا نمی‌شود.
    jq.run_repeating(_market_sweep_job, interval=300, first=90)
    jq.run_repeating(_league_monthly_job, interval=86400, first=260)
    jq.run_repeating(_reminder_job, interval=86400, first=3600)


async def _league_monthly_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_features2
    await handlers_features2.league_monthly_job(context)

async def _reminder_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_features2
    await handlers_features2.reminder_job(context)

async def _market_sweep_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_market
    await handlers_market.market_sweep_job(context)

async def _clan_war_matching_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_clanwar
    await handlers_clanwar.clan_war_matching_job(context)

async def _clan_tournament_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_clanwar
    await handlers_clanwar.clan_tournament_job(context)

async def _server_war_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_social
    await handlers_social.server_war_matching_job(context)

async def _referral_monthly_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_bonus
    await handlers_bonus.referral_monthly_reward_job(context)

async def _vip_tournament_job(context: ContextTypes.DEFAULT_TYPE):
    import handlers_bonus
    await handlers_bonus.vip_tournament_reward_job(context)


async def _fluctuate_market_job(context: ContextTypes.DEFAULT_TYPE):
    low, high = MARKET_FLUCTUATION_RANGE
    old_price, new_price, change_pct = fluctuate_market(low, high)
    logger.info(f"بازار بروزرسانی شد: {old_price} → {new_price} ({change_pct:+.2%})")

    import handlers_extra
    await handlers_extra.resolve_predictions_job(context)

    import handlers_features2
    handlers_features2.record_price_history(new_price)


def main():
    init_db()
    app = build_application()
    schedule_jobs(app)

    logger.info("🚀 ربات LIBER در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
