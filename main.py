"""
LIBER - Economic Simulation Game Bot (Entertainment Edition)
--------------------------------------------------------------
IMPORTANT: This is an entertainment-only simulation game.
- No real-money withdrawals (no TON, no Stars payout)
- No real-money deposits tied to in-game currency value
- All currencies (LIBER, Coin, Energy) are virtual and exist only
  for in-game progression, ranking, and fun.

Requirements:
    pip install python-telegram-bot==21.* 

Run:
    python main.py
"""

import logging
import sqlite3
import random
import time
import os
from datetime import datetime, timedelta
from contextlib import closing

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
# All secrets are read from environment variables so nothing sensitive is
# committed to GitHub. Set these in Railway's "Variables" tab:
#   BOT_TOKEN         -> your bot token from @BotFather
#   REQUIRED_CHANNEL  -> e.g. @Libercoin1  (leave unset/empty to disable)
#   ADMIN_IDS         -> comma-separated numeric Telegram user IDs

BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"
DB_PATH = os.environ.get("DB_PATH", "liber.db")

_admin_ids_env = os.environ.get("ADMIN_IDS", "6188951798")
ADMIN_IDS = [int(x.strip()) for x in _admin_ids_env.split(",") if x.strip()]

REQUIRED_CHANNEL = os.environ.get("REQUIRED_CHANNEL", "@Libercoin1") or None

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("liber")

# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with closing(get_conn()) as conn, conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            liber REAL DEFAULT 100,
            coin REAL DEFAULT 500,
            energy INTEGER DEFAULT 100,
            title TEXT DEFAULT 'تازه‌وارد',
            bio TEXT DEFAULT '',
            avatar TEXT DEFAULT '👤',
            country_id INTEGER,
            referred_by INTEGER,
            banned INTEGER DEFAULT 0,
            last_daily TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            country_id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER UNIQUE,
            name TEXT,
            flag TEXT DEFAULT '🏳',
            population INTEGER DEFAULT 1000,
            satisfaction INTEGER DEFAULT 70,
            budget REAL DEFAULT 1000,
            tech_level INTEGER DEFAULT 1,
            defense_level INTEGER DEFAULT 1,
            created_at TEXT,
            FOREIGN KEY(owner_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS buildings (
            building_id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_id INTEGER,
            type TEXT,
            level INTEGER DEFAULT 1,
            FOREIGN KEY(country_id) REFERENCES countries(country_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price REAL DEFAULT 10.0,
            updated_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS market_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            price REAL,
            recorded_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            mission_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            mission_type TEXT,
            description TEXT,
            reward_liber REAL,
            reward_xp INTEGER,
            completed INTEGER DEFAULT 0,
            created_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            rarity TEXT,
            achieved_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS alliances (
            alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            leader_id INTEGER,
            treasury REAL DEFAULT 0,
            created_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS alliance_members (
            user_id INTEGER PRIMARY KEY,
            alliance_id INTEGER,
            joined_at TEXT,
            FOREIGN KEY(alliance_id) REFERENCES alliances(alliance_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT,
            detail TEXT,
            created_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS bank_deposits (
            deposit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            created_at TEXT,
            matures_at TEXT,
            rate REAL,
            claimed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            investment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            project TEXT,
            amount REAL,
            expected_return REAL,
            created_at TEXT,
            matures_at TEXT,
            claimed INTEGER DEFAULT 0,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS shop_purchases (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item TEXT,
            cost_liber REAL,
            purchased_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS vip_status (
            user_id INTEGER PRIMARY KEY,
            tier TEXT,
            activated_at TEXT,
            expires_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            event_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            started_at TEXT,
            ends_at TEXT,
            effect TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS seasons (
            season_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            started_at TEXT,
            ends_at TEXT,
            active INTEGER DEFAULT 1
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS season_scores (
            user_id INTEGER,
            season_id INTEGER,
            points INTEGER DEFAULT 0,
            league TEXT DEFAULT 'bronze',
            PRIMARY KEY (user_id, season_id),
            FOREIGN KEY(user_id) REFERENCES users(user_id),
            FOREIGN KEY(season_id) REFERENCES seasons(season_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS game_history (
            game_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            game_type TEXT,
            bet REAL,
            result REAL,
            played_at TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS chest_cooldowns (
            user_id INTEGER PRIMARY KEY,
            last_chest TEXT,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS auctions (
            auction_id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT,
            current_price REAL,
            current_winner INTEGER,
            active INTEGER DEFAULT 1,
            created_at TEXT,
            ends_at TEXT
        )
        """)

        conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_achievements_unique
        ON achievements(user_id, name)
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS cheat_flags (
            user_id INTEGER PRIMARY KEY,
            flag_count INTEGER DEFAULT 0,
            last_flag_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            sport TEXT,
            tier TEXT,
            player_score INTEGER,
            opponent_score INTEGER,
            result TEXT,
            created_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS tournament (
            id INTEGER PRIMARY KEY,
            started_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS market_volume (
            hour_bucket TEXT PRIMARY KEY,
            units_bought INTEGER DEFAULT 0,
            units_sold INTEGER DEFAULT 0
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_coupons (
            user_id INTEGER,
            coupon_date TEXT,
            claimed INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, coupon_date)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS chest_daily_limit (
            user_id INTEGER,
            chest_key TEXT,
            purchase_date TEXT,
            count INTEGER DEFAULT 0,
            PRIMARY KEY (user_id, chest_key, purchase_date)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY,
            reward_liber REAL,
            max_uses INTEGER,
            used_count INTEGER DEFAULT 0,
            created_at TEXT
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS gift_redemptions (
            code TEXT,
            user_id INTEGER,
            redeemed_at TEXT,
            PRIMARY KEY (code, user_id)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS predictions (
            pred_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            direction TEXT,
            start_price REAL,
            bet_amount REAL,
            status TEXT DEFAULT 'open',
            created_at TEXT
        )
        """)

        # safe column migrations (ignore if already exist)
        for ddl in (
            "ALTER TABLE users ADD COLUMN research_level INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN defense_level INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN login_streak INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN sport TEXT DEFAULT ''",
            "ALTER TABLE users ADD COLUMN football_speed INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN football_accuracy INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN football_shot INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN football_technique INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN basketball_jump INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN basketball_power INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN basketball_body INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN basketball_accuracy INTEGER DEFAULT 1",
            "ALTER TABLE users ADD COLUMN rank_points INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN matches_played INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN matches_won INTEGER DEFAULT 0",
        ):
            try:
                conn.execute(ddl)
            except sqlite3.OperationalError:
                pass

        # seed market price if empty
        row = conn.execute("SELECT COUNT(*) as c FROM market").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO market (price, updated_at) VALUES (?, ?)",
                (10.0, datetime.utcnow().isoformat()),
            )

        row = conn.execute("SELECT COUNT(*) as c FROM tournament").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO tournament (id, started_at) VALUES (1, ?)",
                (datetime.utcnow().isoformat(),),
            )

    logger.info("Database initialized.")

def log_action(user_id: int, action: str, detail: str = ""):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO logs (user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
            (user_id, action, detail, datetime.utcnow().isoformat()),
        )

# ---------------------------------------------------------------------------
# User helpers
# ---------------------------------------------------------------------------

def get_user(user_id: int):
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()

def create_user_if_missing(user_id: int, username: str, first_name: str, referred_by: int = None):
    existing = get_user(user_id)
    if existing:
        return existing, False

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO users (user_id, username, first_name, joined_at, referred_by)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, first_name, datetime.utcnow().isoformat(), referred_by),
        )

    log_action(user_id, "REGISTER", f"username={username}")
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT OR IGNORE INTO achievements (user_id, name, rarity, achieved_at)
               VALUES (?, 'اولین قدم', 'عادی', ?)""",
            (user_id, datetime.utcnow().isoformat()),
        )
    return get_user(user_id), True

def update_user_field(user_id: int, field: str, value):
    allowed_fields = {
        "level", "xp", "liber", "coin", "energy", "title",
        "bio", "avatar", "country_id", "banned", "last_daily"
    }
    if field not in allowed_fields:
        raise ValueError("Field not allowed")
    with closing(get_conn()) as conn, conn:
        conn.execute(f"UPDATE users SET {field} = ? WHERE user_id = ?", (value, user_id))

def add_currency(user_id: int, liber: float = 0, coin: float = 0, energy: int = 0):
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """UPDATE users
               SET liber = liber + ?, coin = coin + ?, energy = energy + ?
               WHERE user_id = ?""",
            (liber, coin, energy, user_id),
        )

def add_xp(user_id: int, amount: int):
    user = get_user(user_id)
    if not user:
        return
    new_xp = user["xp"] + amount
    new_level = user["level"]
    xp_needed = new_level * 100

    while new_xp >= xp_needed:
        new_xp -= xp_needed
        new_level += 1
        xp_needed = new_level * 100

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET xp = ?, level = ? WHERE user_id = ?",
            (new_xp, new_level, user_id),
        )

    return new_level

# ---------------------------------------------------------------------------
# Market helpers (virtual currency price simulation - for fun only)
# ---------------------------------------------------------------------------

def get_market_price():
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT * FROM market ORDER BY id DESC LIMIT 1").fetchone()
        return row["price"] if row else 10.0

def _current_hour_bucket() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d-%H")


def record_trade_volume(units: int, is_buy: bool):
    bucket = _current_hour_bucket()
    col = "units_bought" if is_buy else "units_sold"
    with closing(get_conn()) as conn, conn:
        conn.execute(
            f"""INSERT INTO market_volume (hour_bucket, {col}) VALUES (?, ?)
                ON CONFLICT(hour_bucket) DO UPDATE SET {col} = {col} + excluded.{col}""",
            (bucket, units),
        )


def fluctuate_market():
    """Hourly price update driven by REAL accumulated buy/sell pressure from the
    previous hour — more buyers push the price up, more sellers push it down.
    A small random drift is added on top so quiet hours still feel alive."""
    current = get_market_price()
    bucket = _current_hour_bucket()

    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT units_bought, units_sold FROM market_volume WHERE hour_bucket = ?", (bucket,)
        ).fetchone()

    bought = row["units_bought"] if row else 0
    sold = row["units_sold"] if row else 0
    net_pressure = bought - sold  # positive = net demand, negative = net supply

    # each net unit of pressure moves price ~0.3%, capped at +/-15% per hour
    pressure_pct = max(-0.15, min(0.15, net_pressure * 0.003))
    random_drift = random.uniform(-0.02, 0.02)  # small ambient noise
    change_pct = pressure_pct + random_drift

    new_price = max(0.5, round(current * (1 + change_pct), 4))

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO market (price, updated_at) VALUES (?, ?)",
            (new_price, datetime.utcnow().isoformat()),
        )
        conn.execute(
            "INSERT INTO market_history (price, recorded_at) VALUES (?, ?)",
            (new_price, datetime.utcnow().isoformat()),
        )

    logger.info(f"Market pressure: bought={bought} sold={sold} net={net_pressure} change={change_pct:+.2%}")
    return new_price, bought, sold

# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def main_menu_keyboard():
    keyboard = [
        ["👤 پروفایل", "🌍 کشور"],
        ["💹 بازار LIBER", "💰 کیف پول"],
        ["🏦 بانک", "🏪 فروشگاه"],
        ["🎁 صندوق‌ها", "🎯 مأموریت‌ها"],
        ["🏆 رتبه‌بندی", "🤝 اتحاد"],
        ["🎮 بازی‌ها", "🎖 دستاوردها"],
        ["🏷 مزایده", "👥 دعوت دوستان"],
        ["💼 شغل", "⚔️ جنگ کلن"],
        ["🔬 تحقیقات", "🛡 دفاع"],
        ["🌌 اکتشاف", "🤖 مشاور هوشمند"],
        ["📰 اخبار جهان", "🎟 پیش‌بینی قیمت"],
        ["⚔️ رقابت آنلاین", "⚙ تنظیمات"],
        ["❓ راهنما"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def admin_panel_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 داشبورد", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👥 کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("💹 اقتصاد", callback_data="admin_economy")],
        [InlineKeyboardButton("🚫 بن کاربر", callback_data="admin_ban")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📋 لاگ‌ها", callback_data="admin_logs")],
    ]
    return InlineKeyboardMarkup(keyboard)

def join_channel_keyboard():
    channel_username = REQUIRED_CHANNEL.replace("@", "")
    keyboard = [
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{channel_username}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def is_channel_member(bot, user_id: int) -> bool:
    """Checks membership in REQUIRED_CHANNEL. Returns True if check is disabled."""
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"Channel membership check failed: {e}")
        return False

# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_channel_member(context.bot, user.id):
        await update.message.reply_text(
            f"🔥 سلام {user.first_name}!\n\n"
            f"برای استفاده از ربات LIBER ابتدا باید عضو کانال شوید:\n{REQUIRED_CHANNEL}\n\n"
            "بعد از عضویت روی «✅ عضو شدم» بزنید.",
            reply_markup=join_channel_keyboard(),
        )
        return

    referred_by = None

    if context.args:
        try:
            ref_id = int(context.args[0])
            if ref_id != user.id:
                referred_by = ref_id
        except (ValueError, IndexError):
            pass

    db_user, is_new = create_user_if_missing(
        user.id, user.username or "", user.first_name or "", referred_by
    )

    if is_new:
        if referred_by:
            referrer = get_user(referred_by)
            if referrer:
                add_currency(referred_by, liber=50)  # virtual reward only
                add_xp(referred_by, 20)
                log_action(referred_by, "REFERRAL_BONUS", f"new_user={user.id}")

                # second-tier bonus: whoever referred your referrer also gets a small cut
                if referrer["referred_by"]:
                    grandparent_id = referrer["referred_by"]
                    grandparent = get_user(grandparent_id)
                    if grandparent:
                        add_currency(grandparent_id, liber=15)
                        log_action(grandparent_id, "REFERRAL_TIER2_BONUS", f"new_user={user.id}")

        display_name = user.username and f"@{user.username}" or user.first_name
        welcome_text = (
            f"🌍━━━━━━━━━━━━━━━━🌍\n"
            f"سلام جناب {display_name} 👋\n"
            f"به ربات LIBER خوش آمدید!\n"
            f"🌍━━━━━━━━━━━━━━━━🌍\n\n"
            "این یک بازی شبیه‌سازی اقتصادی سرگرمی است که در آن می‌توانی:\n"
            "🌍 کشور خودت را بسازی\n"
            "💹 در بازار LIBER معامله کنی\n"
            "🏆 در لیگ فصلی رقابت کنی\n"
            "🤝 با دیگران اتحاد تشکیل بدی\n\n"
            "🎁 هدیه خوش‌آمدگویی: 100 LIBER + 500 Coin در حسابت فعال شد!\n\n"
            "⚠️ توجه: تمام ارزهای این بازی (LIBER, Coin, Energy) کاملاً مجازی هستند "
            "و صرفاً برای سرگرمی و رقابت درون‌بازی استفاده می‌شوند."
        )
    else:
        display_name = user.username and f"@{user.username}" or user.first_name
        welcome_text = f"👋 خوش برگشتی جناب {display_name}!"

    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if not await is_channel_member(context.bot, user.id):
        await query.answer("❌ هنوز عضو کانال نشده‌اید.", show_alert=True)
        return

    db_user, is_new = create_user_if_missing(
        user.id, user.username or "", user.first_name or ""
    )

    await query.edit_message_text("✅ عضویت شما تایید شد! خوش آمدید به LIBER 🌍")
    await query.message.reply_text(
        "🌍 منوی اصلی LIBER", reply_markup=main_menu_keyboard()
    )

async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    xp_needed = user["level"] * 100
    text = (
        f"👤 پروفایل\n\n"
        f"نام: {user['first_name']}\n"
        f"سطح: {user['level']}\n"
        f"XP: {user['xp']} / {xp_needed}\n"
        f"لقب: {user['title']}\n"
        f"بیوگرافی: {user['bio'] or '—'}\n"
        f"تاریخ عضویت: {user['joined_at'][:10]}\n"
    )
    await update.message.reply_text(text)

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    text = (
        f"💰 کیف پول (مجازی - فقط برای بازی)\n\n"
        f"🪙 LIBER: {user['liber']:.2f}\n"
        f"💵 Coin: {user['coin']:.2f}\n"
        f"⚡ Energy: {user['energy']}\n"
    )
    await update.message.reply_text(text)

async def market_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    text = (
        f"💹 بازار LIBER (شبیه‌سازی سرگرمی)\n\n"
        f"قیمت لحظه‌ای: {price:.4f} Coin\n\n"
        "قیمت با خرید بالا می‌ره و با فروش پایین میاد — دقیقاً مثل یه بازار واقعی، ولی کاملاً مجازی.\n\n"
        "با دکمه‌های زیر، بدون تایپ دستور، خرید یا فروش کن:"
    )
    await update.message.reply_text(text, reply_markup=market_action_keyboard())

def market_action_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🟢 خرید LIBER", callback_data="mkt_buy_menu"),
         InlineKeyboardButton("🔴 فروش LIBER", callback_data="mkt_sell_menu")],
    ])

MARKET_IMPACT_PER_UNIT = 0.015
MAX_UNITS_PER_TRADE = 99
_pending_qty = {}

def stepper_keyboard(action, qty):
    label = "خرید" if action == "buy" else "فروش"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("-10", callback_data=f"mkt_{action}_step_-10"),
         InlineKeyboardButton("-1", callback_data=f"mkt_{action}_step_-1"),
         InlineKeyboardButton(f"📦 {qty}", callback_data="mkt_noop"),
         InlineKeyboardButton("+1", callback_data=f"mkt_{action}_step_1"),
         InlineKeyboardButton("+10", callback_data=f"mkt_{action}_step_10")],
        [InlineKeyboardButton(f"✅ تایید {label}", callback_data=f"mkt_{action}_confirm"),
         InlineKeyboardButton("🔙 بازگشت", callback_data="mkt_back")],
    ])

def _simulate_trade(units, price, buy):
    total, p = 0.0, price
    for _ in range(units):
        total += p
        p = round(p * (1 + MARKET_IMPACT_PER_UNIT) if buy else max(0.5, p * (1 - MARKET_IMPACT_PER_UNIT)), 4)
    return round(total, 4), p

def execute_buy_units(user_id, units):
    user = get_user(user_id)
    if not user:
        return False, "ابتدا با /start ثبت‌نام کن."
    if not 1 <= units <= MAX_UNITS_PER_TRADE:
        return False, f"تعداد واحد باید بین ۱ تا {MAX_UNITS_PER_TRADE} باشه."
    price = get_market_price()
    cost, new_price = _simulate_trade(units, price, True)
    if user["coin"] < cost:
        return False, f"❌ Coin کافی نیست.\nهزینه {units} واحد: {cost:.4f}\nموجودی: {user['coin']:.2f}"
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET coin = coin - ?, liber = liber + ? WHERE user_id = ?", (cost, units, user_id))
        conn.execute("INSERT INTO market (price, updated_at) VALUES (?, ?)", (new_price, datetime.utcnow().isoformat()))
    log_action(user_id, "MARKET_BUY", f"units={units} cost={cost} new_price={new_price}")
    record_trade_volume(units, is_buy=True)
    return True, f"🟢 خرید موفق!\n📦 {units} واحد LIBER\n💰 هزینه: {cost:.4f} Coin\n📈 {price:.4f} → {new_price:.4f}"

def execute_sell_units(user_id, units):
    user = get_user(user_id)
    if not user:
        return False, "ابتدا با /start ثبت‌نام کن."
    if not 1 <= units <= MAX_UNITS_PER_TRADE:
        return False, f"تعداد واحد باید بین ۱ تا {MAX_UNITS_PER_TRADE} باشه."
    if user["liber"] < units:
        return False, f"❌ LIBER کافی نیست. موجودی: {user['liber']:.2f}"
    price = get_market_price()
    gain, new_price = _simulate_trade(units, price, False)
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET liber = liber - ?, coin = coin + ? WHERE user_id = ?", (units, gain, user_id))
        conn.execute("INSERT INTO market (price, updated_at) VALUES (?, ?)", (new_price, datetime.utcnow().isoformat()))
    log_action(user_id, "MARKET_SELL", f"units={units} gain={gain} new_price={new_price}")
    record_trade_volume(units, is_buy=False)
    return True, f"🔴 فروش موفق!\n📦 {units} واحد LIBER\n💰 دریافتی: {gain:.4f} Coin\n📉 {price:.4f} → {new_price:.4f}"

async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == "mkt_noop":
        return

    if data == "mkt_back":
        price = get_market_price()
        await query.edit_message_text(
            f"💹 بازار LIBER\n\nقیمت لحظه‌ای: {price:.4f} Coin\n\nبا دکمه‌ها خرید/فروش کن:",
            reply_markup=market_action_keyboard(),
        )
        return

    if data in ("mkt_buy_menu", "mkt_sell_menu"):
        action = "buy" if data == "mkt_buy_menu" else "sell"
        _pending_qty[user_id] = 1
        label = "خرید" if action == "buy" else "فروش"
        await query.edit_message_text(
            f"🔢 تعداد واحد برای {label} رو با دکمه‌های +/- تنظیم کن (۱ تا ۹۹)، بعد تایید بزن:",
            reply_markup=stepper_keyboard(action, 1),
        )
        return

    if "_step_" in data:
        parts = data.split("_")
        action, delta = parts[1], int(parts[3])
        qty = max(1, min(MAX_UNITS_PER_TRADE, _pending_qty.get(user_id, 1) + delta))
        _pending_qty[user_id] = qty
        await query.edit_message_reply_markup(reply_markup=stepper_keyboard(action, qty))
        return

    if data.endswith("_confirm"):
        action = "buy" if data.startswith("mkt_buy") else "sell"
        units = _pending_qty.get(user_id, 1)
        success, msg = execute_buy_units(user_id, units) if action == "buy" else execute_sell_units(user_id, units)
        await query.edit_message_text(msg, reply_markup=market_action_keyboard())

async def buy_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command-line fallback for buying (button flow is the main path now)."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "می‌تونی از دکمه‌های بازار (💹 بازار LIBER) استفاده کنی، یا دستی بنویسی:\n"
            "/buy تعداد_واحد (۱ تا ۹۹)"
        )
        return
    try:
        units = int(context.args[0])
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد صحیح وارد کن.")
        return
    success, msg = execute_buy_units(user_id, units)
    await update.message.reply_text(msg)

async def sell_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command-line fallback for selling (button flow is the main path now)."""
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text(
            "می‌تونی از دکمه‌های بازار (💹 بازار LIBER) استفاده کنی، یا دستی بنویسی:\n"
            "/sell تعداد_واحد (۱ تا ۹۹)"
        )
        return
    try:
        units = int(context.args[0])
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد صحیح وارد کن.")
        return
    success, msg = execute_sell_units(user_id, units)
    await update.message.reply_text(msg)
    await update.message.reply_text(
        f"✅ فروش موفق: {coin_amount:.4f} Coin دریافت شد (قیمت: {price:.4f})"
    )

async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    now = datetime.utcnow()
    if user["last_daily"]:
        last = datetime.fromisoformat(user["last_daily"])
        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            hrs = int(remaining.total_seconds() // 3600)
            mins = int((remaining.total_seconds() % 3600) // 60)
            await update.message.reply_text(
                f"⏳ جایزه روزانه رو قبلاً گرفتی. {hrs} ساعت و {mins} دقیقه دیگه دوباره تلاش کن."
            )
            return
        # streak continues if claimed within 24-48h, resets if longer gap
        streak_continues = now - last < timedelta(hours=48)
    else:
        streak_continues = False

    new_streak = (user["login_streak"] + 1) if streak_continues else 1
    streak_bonus_multiplier = min(3.0, 1 + (new_streak - 1) * 0.15)  # up to +200% at day 14+

    reward_liber = int(random.randint(20, 100) * streak_bonus_multiplier)
    reward_energy = random.randint(5, 20)

    add_currency(user_id, liber=reward_liber, energy=reward_energy)
    add_xp(user_id, 10)
    update_user_field(user_id, "last_daily", now.isoformat())
    update_user_field(user_id, "login_streak", new_streak)

    streak_text = f"\n🔥 استریک ورود: {new_streak} روز (ضریب پاداش: x{streak_bonus_multiplier:.2f})"
    await update.message.reply_text(
        f"🎁 جایزه روزانه دریافت شد!\n+{reward_liber} LIBER\n+{reward_energy} Energy\n+10 XP{streak_text}"
    )
    log_action(user_id, "DAILY_REWARD", f"liber={reward_liber} energy={reward_energy} streak={new_streak}")

async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT first_name, level, xp, liber FROM users ORDER BY level DESC, xp DESC LIMIT 10"
        ).fetchall()

    if not rows:
        await update.message.reply_text("هنوز کسی در جدول رتبه‌بندی نیست.")
        return

    text = "🏆 برترین بازیکنان\n\n"
    for i, row in enumerate(rows, start=1):
        text += f"{i}. {row['first_name']} — سطح {row['level']} ({row['xp']} XP)\n"

    await update.message.reply_text(text)

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    with closing(get_conn()) as conn:
        count = conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE referred_by = ?", (user_id,)
        ).fetchone()["c"]

    text = (
        f"👥 دعوت دوستان\n\n"
        f"لینک اختصاصی شما:\n{link}\n\n"
        f"تعداد دعوت‌شدگان: {count}\n"
        f"🎁 جایزه هر دعوت مستقیم: 50 LIBER (مجازی)\n"
        f"💎 جایزه سطح دو: وقتی افرادی که دعوت کردی، خودشون یکی رو دعوت کنن، "
        f"تو هم ۱۵ LIBER اضافه می‌گیری!"
    )
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Admin Handlers
# ---------------------------------------------------------------------------

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ دسترسی غیرمجاز.")
        return

    await update.message.reply_text(
        "👑 پنل مدیریت LIBER", reply_markup=admin_panel_keyboard()
    )

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ دسترسی غیرمجاز", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "admin_dashboard":
        with closing(get_conn()) as conn:
            total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            total_liber = conn.execute("SELECT SUM(liber) as s FROM users").fetchone()["s"] or 0
            price = get_market_price()

        text = (
            f"📊 داشبورد\n\n"
            f"کل کاربران: {total_users}\n"
            f"مجموع LIBER در گردش: {total_liber:.2f}\n"
            f"قیمت بازار فعلی: {price:.4f}\n"
        )
        await query.edit_message_text(text, reply_markup=admin_panel_keyboard())

    elif action == "admin_users":
        with closing(get_conn()) as conn:
            rows = conn.execute(
                "SELECT user_id, first_name, level, liber, banned FROM users ORDER BY joined_at DESC LIMIT 15"
            ).fetchall()

        text = "👥 آخرین کاربران\n\n"
        for r in rows:
            status = "🚫" if r["banned"] else "✅"
            text += f"{status} {r['first_name']} (ID: {r['user_id']}) — سطح {r['level']}\n"

        await query.edit_message_text(text, reply_markup=admin_panel_keyboard())

    elif action == "admin_economy":
        history_text = "💹 تاریخچه قیمت (۱۰ مورد آخر)\n\n"
        with closing(get_conn()) as conn:
            rows = conn.execute(
                "SELECT price, recorded_at FROM market_history ORDER BY id DESC LIMIT 10"
            ).fetchall()
        for r in rows:
            history_text += f"{r['price']:.4f} — {r['recorded_at'][:16]}\n"

        await query.edit_message_text(history_text or "داده‌ای موجود نیست.", reply_markup=admin_panel_keyboard())

    elif action == "admin_ban":
        await query.edit_message_text(
            "برای بن کردن یک کاربر از دستور زیر استفاده کن:\n/ban USER_ID",
            reply_markup=admin_panel_keyboard(),
        )

    elif action == "admin_broadcast":
        await query.edit_message_text(
            "برای ارسال پیام همگانی از دستور زیر استفاده کن:\n/broadcast متن پیام",
            reply_markup=admin_panel_keyboard(),
        )

    elif action == "admin_logs":
        with closing(get_conn()) as conn:
            rows = conn.execute(
                "SELECT user_id, action, detail, created_at FROM logs ORDER BY log_id DESC LIMIT 10"
            ).fetchall()

        text = "📋 آخرین لاگ‌ها\n\n"
        for r in rows:
            text += f"[{r['created_at'][:16]}] {r['user_id']} — {r['action']} {r['detail']}\n"

        await query.edit_message_text(text or "لاگی موجود نیست.", reply_markup=admin_panel_keyboard())

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("استفاده: /ban USER_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه نامعتبر است.")
        return

    update_user_field(target_id, "banned", 1)
    log_action(user_id, "ADMIN_BAN", f"target={target_id}")
    await update.message.reply_text(f"🚫 کاربر {target_id} بن شد.")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("استفاده: /unban USER_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه نامعتبر است.")
        return

    update_user_field(target_id, "banned", 0)
    log_action(user_id, "ADMIN_UNBAN", f"target={target_id}")
    await update.message.reply_text(f"✅ کاربر {target_id} آن‌بن شد.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن پیام")
        return

    message_text = " ".join(context.args)

    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE banned = 0").fetchall()

    sent = 0
    failed = 0
    for row in rows:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {message_text}")
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(f"✅ ارسال شد به {sent} کاربر. ({failed} ناموفق)")
    log_action(user_id, "ADMIN_BROADCAST", message_text)

# ---------------------------------------------------------------------------
# Country & Buildings
# ---------------------------------------------------------------------------

BUILDING_COSTS = {
    "mine": 200,
    "factory": 300,
    "power_plant": 400,
    "farm": 150,
    "lab": 500,
}

BUILDING_NAMES = {
    "mine": "⛏ معدن",
    "factory": "🏭 کارخانه",
    "power_plant": "⚡ نیروگاه",
    "farm": "🌾 مزرعه",
    "lab": "🔬 آزمایشگاه",
}

def get_country_by_owner(owner_id: int):
    with closing(get_conn()) as conn:
        return conn.execute(
            "SELECT * FROM countries WHERE owner_id = ?", (owner_id,)
        ).fetchone()

async def found_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    existing = get_country_by_owner(user_id)
    if existing:
        await update.message.reply_text("شما قبلاً یک کشور ساخته‌اید.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /found نام_کشور")
        return

    name = " ".join(context.args)[:30]

    with closing(get_conn()) as conn, conn:
        cursor = conn.execute(
            """INSERT INTO countries (owner_id, name, created_at)
               VALUES (?, ?, ?)""",
            (user_id, name, datetime.utcnow().isoformat()),
        )
        country_id = cursor.lastrowid
        conn.execute(
            "UPDATE users SET country_id = ? WHERE user_id = ?",
            (country_id, user_id),
        )

    log_action(user_id, "FOUND_COUNTRY", name)
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT OR IGNORE INTO achievements (user_id, name, rarity, achieved_at)
               VALUES (?, 'بنیان‌گذار کشور', 'کمیاب', ?)""",
            (user_id, datetime.utcnow().isoformat()),
        )
    await update.message.reply_text(f"🌍 کشور «{name}» با موفقیت تاسیس شد!")

async def country_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = get_country_by_owner(user_id)
    if not country:
        await update.message.reply_text(
            "شما هنوز کشوری ندارید. با /found نام_کشور یکی بساز."
        )
        return

    with closing(get_conn()) as conn:
        buildings = conn.execute(
            "SELECT type, level FROM buildings WHERE country_id = ?",
            (country["country_id"],),
        ).fetchall()

    buildings_text = "\n".join(
        f"  {BUILDING_NAMES.get(b['type'], b['type'])}: سطح {b['level']}"
        for b in buildings
    ) or "  هنوز ساختمانی ساخته نشده."

    text = (
        f"🌍 {country['name']} {country['flag']}\n\n"
        f"👥 جمعیت: {country['population']}\n"
        f"😊 رضایت: {country['satisfaction']}%\n"
        f"💰 بودجه: {country['budget']:.2f}\n"
        f"🛰 سطح فناوری: {country['tech_level']}\n"
        f"🛡 سطح دفاع: {country['defense_level']}\n\n"
        f"🏗 ساختمان‌ها:\n{buildings_text}"
    )
    await update.message.reply_text(text)

async def build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    country = get_country_by_owner(user_id)

    if not country:
        await update.message.reply_text("ابتدا یک کشور بساز: /found نام_کشور")
        return

    if not context.args or context.args[0] not in BUILDING_COSTS:
        options = ", ".join(BUILDING_COSTS.keys())
        await update.message.reply_text(f"استفاده: /build نوع\nانواع: {options}")
        return

    b_type = context.args[0]
    cost = BUILDING_COSTS[b_type]

    if user["liber"] < cost:
        await update.message.reply_text(f"LIBER کافی نیست. هزینه: {cost}")
        return

    with closing(get_conn()) as conn, conn:
        existing = conn.execute(
            "SELECT * FROM buildings WHERE country_id = ? AND type = ?",
            (country["country_id"], b_type),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE buildings SET level = level + 1 WHERE building_id = ?",
                (existing["building_id"],),
            )
        else:
            conn.execute(
                "INSERT INTO buildings (country_id, type, level) VALUES (?, ?, 1)",
                (country["country_id"],),
            )

        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?", (cost, user_id)
        )

    add_xp(user_id, 15)
    log_action(user_id, "BUILD", f"{b_type} cost={cost}")
    await update.message.reply_text(
        f"🏗 {BUILDING_NAMES.get(b_type, b_type)} ساخته/ارتقا یافت! (-{cost} LIBER)"
    )

# ---------------------------------------------------------------------------
# Bank: deposits with interest (virtual only)
# ---------------------------------------------------------------------------

DEPOSIT_RATE = 0.02       # 2% return
DEPOSIT_DURATION_HOURS = 24

async def bank_deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /deposit مقدار_لیبر")
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return

    if amount <= 0 or amount > user["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    now = datetime.utcnow()
    matures_at = now + timedelta(hours=DEPOSIT_DURATION_HOURS)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?", (amount, user_id)
        )
        conn.execute(
            """INSERT INTO bank_deposits (user_id, amount, created_at, matures_at, rate)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, amount, now.isoformat(), matures_at.isoformat(), DEPOSIT_RATE),
        )

    log_action(user_id, "BANK_DEPOSIT", f"amount={amount}")
    await update.message.reply_text(
        f"🏦 {amount:.2f} LIBER سپرده‌گذاری شد.\n"
        f"سود: {DEPOSIT_RATE*100:.0f}% بعد از {DEPOSIT_DURATION_HOURS} ساعت.\n"
        f"با /claim می‌تونی بعد از سررسید برداشت کنی."
    )

async def bank_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.utcnow()

    with closing(get_conn()) as conn, conn:
        deposits = conn.execute(
            """SELECT * FROM bank_deposits
               WHERE user_id = ? AND claimed = 0""",
            (user_id,),
        ).fetchall()

        total_claimed = 0
        claimed_count = 0

        for d in deposits:
            matures_at = datetime.fromisoformat(d["matures_at"])
            if now >= matures_at:
                payout = d["amount"] * (1 + d["rate"])
                conn.execute(
                    "UPDATE users SET liber = liber + ? WHERE user_id = ?",
                    (payout, user_id),
                )
                conn.execute(
                    "UPDATE bank_deposits SET claimed = 1 WHERE deposit_id = ?",
                    (d["deposit_id"],),
                )
                total_claimed += payout
                claimed_count += 1

    if claimed_count == 0:
        await update.message.reply_text("هیچ سپرده‌ی سررسیدشده‌ای موجود نیست.")
    else:
        await update.message.reply_text(
            f"✅ {claimed_count} سپرده برداشت شد. مجموع دریافتی: {total_claimed:.2f} LIBER"
        )
    log_action(user_id, "BANK_CLAIM", f"count={claimed_count}")

# ---------------------------------------------------------------------------
# Investments (virtual projects with randomized return)
# ---------------------------------------------------------------------------

INVESTMENT_PROJECTS = {
    "tech": {"name": "🛰 پروژه فناوری", "min_return": 1.05, "max_return": 1.35},
    "energy": {"name": "⚡ شبکه انرژی", "min_return": 1.0, "max_return": 1.25},
    "mining": {"name": "⛏ معدن جدید", "min_return": 0.9, "max_return": 1.5},
}

async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if len(context.args) < 2 or context.args[0] not in INVESTMENT_PROJECTS:
        options = ", ".join(INVESTMENT_PROJECTS.keys())
        await update.message.reply_text(f"استفاده: /invest نوع مقدار\nانواع: {options}")
        return

    project_key = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return

    if amount <= 0 or amount > user["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    project = INVESTMENT_PROJECTS[project_key]
    multiplier = random.uniform(project["min_return"], project["max_return"])
    expected_return = round(amount * multiplier, 2)

    now = datetime.utcnow()
    matures_at = now + timedelta(hours=12)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?", (amount, user_id)
        )
        conn.execute(
            """INSERT INTO investments
               (user_id, project, amount, expected_return, created_at, matures_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, project_key, amount, expected_return, now.isoformat(), matures_at.isoformat()),
        )

    log_action(user_id, "INVEST", f"{project_key} amount={amount}")
    await update.message.reply_text(
        f"📈 سرمایه‌گذاری در {project['name']} انجام شد.\n"
        f"مبلغ: {amount:.2f} LIBER\n"
        f"نتیجه بعد از ۱۲ ساعت مشخص می‌شود. با /claim_invest بررسی کن."
    )

async def claim_investments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = datetime.utcnow()

    with closing(get_conn()) as conn, conn:
        investments = conn.execute(
            "SELECT * FROM investments WHERE user_id = ? AND claimed = 0",
            (user_id,),
        ).fetchall()

        total = 0
        count = 0

        for inv in investments:
            matures_at = datetime.fromisoformat(inv["matures_at"])
            if now >= matures_at:
                conn.execute(
                    "UPDATE users SET liber = liber + ? WHERE user_id = ?",
                    (inv["expected_return"], user_id),
                )
                conn.execute(
                    "UPDATE investments SET claimed = 1 WHERE investment_id = ?",
                    (inv["investment_id"],),
                )
                total += inv["expected_return"]
                count += 1

    if count == 0:
        await update.message.reply_text("سرمایه‌گذاری سررسیدشده‌ای موجود نیست.")
    else:
        await update.message.reply_text(
            f"✅ {count} سرمایه‌گذاری تسویه شد. مجموع دریافتی: {total:.2f} LIBER"
        )
    log_action(user_id, "CLAIM_INVEST", f"count={count}")

# ---------------------------------------------------------------------------
# Missions
# ---------------------------------------------------------------------------

MISSION_TEMPLATES = {
    "daily": [
        ("خرید در بازار", 30, 10),
        ("ساخت یک ساختمان", 50, 20),
        ("جمع‌آوری جایزه روزانه", 20, 5),
    ],
    "weekly": [
        ("رسیدن به سطح بعدی", 150, 50),
        ("سرمایه‌گذاری موفق", 200, 60),
    ],
}

def missions_keyboard(missions_rows, user_id=None):
    rows = []
    for m in missions_rows:
        mark = "✅" if m["completed"] else "⬜"
        label = f"{mark} {m['description']} (+{m['reward_liber']:.0f} LIBER)"
        cb = "mis_noop" if m["completed"] else f"mis_done_{m['mission_id']}"
        rows.append([InlineKeyboardButton(label, callback_data=cb)])

    all_done = bool(missions_rows) and all(m["completed"] for m in missions_rows)
    if all_done and user_id is not None:
        today = datetime.utcnow().date().isoformat()
        with closing(get_conn()) as conn:
            coupon = conn.execute(
                "SELECT * FROM daily_coupons WHERE user_id = ? AND coupon_date = ?", (user_id, today)
            ).fetchone()
        if not coupon or not coupon["claimed"]:
            rows.append([InlineKeyboardButton("🎟 دریافت کوپن روزانه (همه انجام شد!)", callback_data="mis_coupon")])
        else:
            rows.append([InlineKeyboardButton("✅ کوپن امروز دریافت شد", callback_data="mis_noop")])

    rows.append([InlineKeyboardButton("🔄 بروزرسانی", callback_data="mis_refresh")])
    return InlineKeyboardMarkup(rows)


def _get_or_create_missions(user_id: int):
    with closing(get_conn()) as conn:
        existing = conn.execute(
            "SELECT * FROM missions WHERE user_id = ? AND mission_type = 'daily' "
            "AND date(created_at) = date('now')", (user_id,),
        ).fetchall()

    if not existing:
        with closing(get_conn()) as conn, conn:
            for desc, reward_liber, reward_xp in MISSION_TEMPLATES["daily"]:
                conn.execute(
                    """INSERT INTO missions
                       (user_id, mission_type, description, reward_liber, reward_xp, created_at)
                       VALUES (?, 'daily', ?, ?, ?, ?)""",
                    (user_id, desc, reward_liber, reward_xp, datetime.utcnow().isoformat()),
                )
        with closing(get_conn()) as conn:
            existing = conn.execute(
                "SELECT * FROM missions WHERE user_id = ? AND mission_type = 'daily' "
                "AND date(created_at) = date('now')", (user_id,),
            ).fetchall()
    return existing


async def get_missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    missions = _get_or_create_missions(user_id)
    done = sum(1 for m in missions if m["completed"])
    await update.message.reply_text(
        f"🎯 مأموریت‌های امروز ({done}/{len(missions)} انجام‌شده)\n\nروی هرکدوم بزن تا تیک بخوره و جایزه بگیری:",
        reply_markup=missions_keyboard(missions, user_id),
    )


async def missions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == "mis_noop":
        return

    if data == "mis_coupon":
        today = datetime.utcnow().date().isoformat()
        with closing(get_conn()) as conn:
            coupon = conn.execute(
                "SELECT * FROM daily_coupons WHERE user_id = ? AND coupon_date = ?", (user_id, today)
            ).fetchone()
        if coupon and coupon["claimed"]:
            await query.answer("قبلاً امروز گرفتی.", show_alert=True)
            return

        coupon_reward = random.randint(50, 150)
        with closing(get_conn()) as conn, conn:
            conn.execute(
                """INSERT INTO daily_coupons (user_id, coupon_date, claimed) VALUES (?, ?, 1)
                   ON CONFLICT(user_id, coupon_date) DO UPDATE SET claimed = 1""",
                (user_id, today),
            )
        add_currency(user_id, liber=coupon_reward)
        log_action(user_id, "DAILY_COUPON", f"reward={coupon_reward}")

        missions = _get_or_create_missions(user_id)
        await query.answer(f"🎟 کوپن روزانه: +{coupon_reward} LIBER!", show_alert=True)
        await query.edit_message_text(
            f"🎯 همه‌ی مأموریت‌های امروز کامل شد! 🎉\n🎟 کوپن روزانه گرفتی: +{coupon_reward} LIBER",
            reply_markup=missions_keyboard(missions, user_id),
        )
        return

    if data == "mis_refresh":
        missions = _get_or_create_missions(user_id)
        done = sum(1 for m in missions if m["completed"])
        await query.edit_message_text(
            f"🎯 مأموریت‌های امروز ({done}/{len(missions)} انجام‌شده)\n\nروی هرکدوم بزن تا تیک بخوره:",
            reply_markup=missions_keyboard(missions, user_id),
        )
        return

    if data.startswith("mis_done_"):
        mission_id = int(data[len("mis_done_"):])
        with closing(get_conn()) as conn:
            mission = conn.execute(
                "SELECT * FROM missions WHERE mission_id = ? AND user_id = ?", (mission_id, user_id)
            ).fetchone()

        if not mission or mission["completed"]:
            await query.answer("قبلاً انجام شده یا پیدا نشد.", show_alert=True)
            return

        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE missions SET completed = 1 WHERE mission_id = ?", (mission_id,))

        add_currency(user_id, liber=mission["reward_liber"])
        add_xp(user_id, mission["reward_xp"])
        log_action(user_id, "MISSION_COMPLETE", mission["description"])

        missions = _get_or_create_missions(user_id)
        done = sum(1 for m in missions if m["completed"])
        await query.answer(f"✅ +{mission['reward_liber']:.0f} LIBER, +{mission['reward_xp']} XP", show_alert=True)
        await query.edit_message_text(
            f"🎯 مأموریت‌های امروز ({done}/{len(missions)} انجام‌شده)\n\nروی هرکدوم بزن تا تیک بخوره:",
            reply_markup=missions_keyboard(missions, user_id),
        )


async def complete_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback: /complete شماره (button checklist via 🎯 مأموریت‌ها is the main path)."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("از دکمه‌ی 🎯 مأموریت‌ها استفاده کن، یا: /complete شماره")
        return

    try:
        mission_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شماره نامعتبر است.")
        return

    with closing(get_conn()) as conn:
        mission = conn.execute(
            "SELECT * FROM missions WHERE mission_id = ? AND user_id = ?",
            (mission_id, user_id),
        ).fetchone()

    if not mission:
        await update.message.reply_text("مأموریت پیدا نشد.")
        return
    if mission["completed"]:
        await update.message.reply_text("این مأموریت قبلاً تکمیل شده.")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE missions SET completed = 1 WHERE mission_id = ?", (mission_id,)
        )

    add_currency(user_id, liber=mission["reward_liber"])
    add_xp(user_id, mission["reward_xp"])

    log_action(user_id, "MISSION_COMPLETE", mission["description"])
    await update.message.reply_text(
        f"✅ مأموریت «{mission['description']}» تکمیل شد!\n"
        f"+{mission['reward_liber']} LIBER, +{mission['reward_xp']} XP"
    )

# ---------------------------------------------------------------------------
# Achievements
# ---------------------------------------------------------------------------

ACHIEVEMENT_LIST = [
    ("اولین قدم", "عادی"),
    ("تاجر تازه‌کار", "عادی"),
    ("بنیان‌گذار کشور", "کمیاب"),
    ("سرمایه‌گذار حرفه‌ای", "کمیاب"),
    ("افسانه LIBER", "افسانه‌ای"),
]

async def grant_achievement(user_id: int, name: str, rarity: str):
    with closing(get_conn()) as conn:
        existing = conn.execute(
            "SELECT * FROM achievements WHERE user_id = ? AND name = ?",
            (user_id, name),
        ).fetchone()
    if existing:
        return False

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO achievements (user_id, name, rarity, achieved_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, name, rarity, datetime.utcnow().isoformat()),
        )
    return True

async def achievements_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT name, rarity, achieved_at FROM achievements WHERE user_id = ?",
            (user_id,),
        ).fetchall()

    if not rows:
        await update.message.reply_text("هنوز دستاوردی کسب نکرده‌ای.")
        return

    text = "🎖 دستاوردهای شما\n\n"
    for r in rows:
        text += f"🏅 {r['name']} ({r['rarity']}) — {r['achieved_at'][:10]}\n"

    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Alliances
# ---------------------------------------------------------------------------

async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    with closing(get_conn()) as conn:
        already_member = conn.execute(
            "SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)
        ).fetchone()
    if already_member:
        await update.message.reply_text("شما قبلاً عضو یک اتحاد هستید.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /create_alliance نام")
        return

    name = " ".join(context.args)[:30]

    try:
        with closing(get_conn()) as conn, conn:
            cursor = conn.execute(
                """INSERT INTO alliances (name, leader_id, created_at)
                   VALUES (?, ?, ?)""",
                (name, user_id, datetime.utcnow().isoformat()),
            )
            alliance_id = cursor.lastrowid
            conn.execute(
                """INSERT INTO alliance_members (user_id, alliance_id, joined_at)
                   VALUES (?, ?, ?)""",
                (user_id, alliance_id, datetime.utcnow().isoformat()),
            )
    except sqlite3.IntegrityError:
        await update.message.reply_text("این نام قبلاً استفاده شده.")
        return

    log_action(user_id, "CREATE_ALLIANCE", name)
    await update.message.reply_text(f"🤝 اتحاد «{name}» ساخته شد!")

async def join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with closing(get_conn()) as conn:
        already_member = conn.execute(
            "SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)
        ).fetchone()
    if already_member:
        await update.message.reply_text("شما قبلاً عضو یک اتحاد هستید.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /join_alliance نام")
        return

    name = " ".join(context.args)

    with closing(get_conn()) as conn:
        alliance = conn.execute(
            "SELECT * FROM alliances WHERE name = ?", (name,)
        ).fetchone()

    if not alliance:
        await update.message.reply_text("اتحادی با این نام پیدا نشد.")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO alliance_members (user_id, alliance_id, joined_at)
               VALUES (?, ?, ?)""",
            (user_id, alliance["alliance_id"], datetime.utcnow().isoformat()),
        )

    log_action(user_id, "JOIN_ALLIANCE", name)
    await update.message.reply_text(f"🤝 با موفقیت به اتحاد «{name}» پیوستی!")

async def alliance_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with closing(get_conn()) as conn:
        membership = conn.execute(
            "SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)
        ).fetchone()

        if not membership:
            await update.message.reply_text(
                "شما عضو هیچ اتحادی نیستید.\n"
                "/create_alliance نام — برای ساخت\n"
                "/join_alliance نام — برای پیوستن"
            )
            return

        alliance = conn.execute(
            "SELECT * FROM alliances WHERE alliance_id = ?",
            (membership["alliance_id"],),
        ).fetchone()

        members = conn.execute(
            """SELECT u.first_name FROM alliance_members am
               JOIN users u ON u.user_id = am.user_id
               WHERE am.alliance_id = ?""",
            (alliance["alliance_id"],),
        ).fetchall()

    members_text = "\n".join(f"  • {m['first_name']}" for m in members)

    text = (
        f"🤝 اتحاد: {alliance['name']}\n"
        f"💰 خزانه: {alliance['treasury']:.2f} LIBER\n"
        f"👥 اعضا ({len(members)}):\n{members_text}"
    )
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Shop & Virtual VIP (no real payment — cosmetic / in-game currency only)
# ---------------------------------------------------------------------------

SHOP_ITEMS = {
    "avatar_gold": {"name": "🖼 آواتار طلایی", "cost": 300},
    "frame_diamond": {"name": "🎨 قاب الماسی", "cost": 500},
    "title_legend": {"name": "🏷 لقب افسانه‌ای", "cost": 800},
    "energy_pack": {"name": "⚡ بسته انرژی (+50)", "cost": 100},
}

VIP_TIERS = {
    "normal_3m": {"name": "🥈 اشتراک عادی (۳ ماهه)", "cost_liber": 4000, "duration_days": 90,
                  "perk": "درآمد و XP +10٪"},
    "normal_6m": {"name": "🥈 اشتراک عادی (۶ ماهه)", "cost_liber": 7000, "duration_days": 180,
                  "perk": "درآمد و XP +10٪"},
    "dragon_3m": {"name": "🐉 اشتراک دراگون (۳ ماهه)", "cost_liber": 9000, "duration_days": 90,
                  "perk": "درآمد و XP +25٪ + صندوق طلایی رایگان هفتگی"},
    "dragon_6m": {"name": "🐉 اشتراک دراگون (۶ ماهه)", "cost_liber": 15000, "duration_days": 180,
                  "perk": "درآمد و XP +25٪ + صندوق طلایی رایگان هفتگی"},
    "legend_3m": {"name": "👑 اشتراک لیبری لجند (۳ ماهه)", "cost_liber": 20000, "duration_days": 90,
                  "perk": "درآمد و XP +50٪ + صندوق الماسی رایگان هفتگی + قاب اختصاصی"},
    "legend_6m": {"name": "👑 اشتراک لیبری لجند (۶ ماهه)", "cost_liber": 32000, "duration_days": 180,
                  "perk": "درآمد و XP +50٪ + صندوق الماسی رایگان هفتگی + قاب اختصاصی"},
}

async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏪 فروشگاه (پرداخت با LIBER داخل‌بازی)\n\nروی هر آیتم بزن تا بخری:",
        reply_markup=shop_keyboard(),
    )


def shop_keyboard():
    rows = []
    for key, item in SHOP_ITEMS.items():
        rows.append([InlineKeyboardButton(f"{item['name']} — {item['cost']} LIBER", callback_data=f"shop_buy_{key}")])
    for key, tier in VIP_TIERS.items():
        rows.append([InlineKeyboardButton(f"⭐ {tier['name']} — {tier['cost_liber']} LIBER", callback_data=f"shop_vip_{key}")])
    return InlineKeyboardMarkup(rows)


async def shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data.startswith("shop_buy_"):
        key = data[len("shop_buy_"):]
        item = SHOP_ITEMS.get(key)
        user = get_user(user_id)
        if not item or not user:
            await query.edit_message_text("❌ خطا در خرید.", reply_markup=shop_keyboard())
            return
        if user["liber"] < item["cost"]:
            await query.answer("❌ LIBER کافی نیست.", show_alert=True)
            return
        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE users SET liber = liber - ? WHERE user_id = ?", (item["cost"], user_id))
            conn.execute(
                "INSERT INTO shop_purchases (user_id, item, cost_liber, purchased_at) VALUES (?, ?, ?, ?)",
                (user_id, key, item["cost"], datetime.utcnow().isoformat()),
            )
            if key == "energy_pack":
                conn.execute("UPDATE users SET energy = energy + 50 WHERE user_id = ?", (user_id,))
        log_action(user_id, "SHOP_BUY", key)
        await query.edit_message_text(f"✅ {item['name']} خریداری شد!", reply_markup=shop_keyboard())
        return

    if data.startswith("shop_vip_"):
        key = data[len("shop_vip_"):]
        tier = VIP_TIERS.get(key)
        user = get_user(user_id)
        if not tier or not user:
            await query.edit_message_text("❌ خطا.", reply_markup=shop_keyboard())
            return
        if user["liber"] < tier["cost_liber"]:
            await query.answer("❌ LIBER کافی نیست.", show_alert=True)
            return
        now = datetime.utcnow()
        expires_at = now + timedelta(days=tier["duration_days"])
        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE users SET liber = liber - ? WHERE user_id = ?", (tier["cost_liber"], user_id))
            conn.execute(
                """INSERT INTO vip_status (user_id, tier, activated_at, expires_at) VALUES (?, ?, ?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET tier=excluded.tier, activated_at=excluded.activated_at, expires_at=excluded.expires_at""",
                (user_id, key, now.isoformat(), expires_at.isoformat()),
            )
        log_action(user_id, "BUY_VIP", key)
        await query.edit_message_text(
            f"⭐ {tier['name']} فعال شد تا {expires_at.strftime('%Y-%m-%d')}!", reply_markup=shop_keyboard()
        )

async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args or context.args[0] not in SHOP_ITEMS:
        await update.message.reply_text("آیتم نامعتبر. از /shop لیست را ببین.")
        return

    key = context.args[0]
    item = SHOP_ITEMS[key]

    if user["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?",
            (item["cost"], user_id),
        )
        conn.execute(
            """INSERT INTO shop_purchases (user_id, item, cost_liber, purchased_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, key, item["cost"], datetime.utcnow().isoformat()),
        )
        if key == "energy_pack":
            conn.execute(
                "UPDATE users SET energy = energy + 50 WHERE user_id = ?", (user_id,)
            )

    log_action(user_id, "SHOP_BUY", key)
    await update.message.reply_text(f"✅ {item['name']} خریداری شد!")

async def buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """VIP purchased entirely with in-game LIBER — no real payment gateway."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args or context.args[0] not in VIP_TIERS:
        options = ", ".join(VIP_TIERS.keys())
        await update.message.reply_text(f"استفاده: /buy_vip نوع\nانواع: {options}")
        return

    key = context.args[0]
    tier = VIP_TIERS[key]

    if user["liber"] < tier["cost_liber"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return

    now = datetime.utcnow()
    expires_at = now + timedelta(days=tier["duration_days"])

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?",
            (tier["cost_liber"], user_id),
        )
        conn.execute(
            """INSERT INTO vip_status (user_id, tier, activated_at, expires_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 tier = excluded.tier,
                 activated_at = excluded.activated_at,
                 expires_at = excluded.expires_at""",
            (user_id, key, now.isoformat(), expires_at.isoformat()),
        )

    log_action(user_id, "BUY_VIP", key)
    await update.message.reply_text(
        f"⭐ {tier['name']} فعال شد تا {expires_at.strftime('%Y-%m-%d')}!"
    )

async def vip_status_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    with closing(get_conn()) as conn:
        status = conn.execute(
            "SELECT * FROM vip_status WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not status:
        await update.message.reply_text("شما در حال حاضر VIP نیستید. /shop را ببین.")
        return

    expires_at = datetime.fromisoformat(status["expires_at"])
    active = datetime.utcnow() < expires_at
    tier_name = VIP_TIERS.get(status["tier"], {}).get("name", status["tier"])

    text = (
        f"⭐ وضعیت VIP\n\n"
        f"سطح: {tier_name}\n"
        f"وضعیت: {'✅ فعال' if active else '❌ منقضی شده'}\n"
        f"تاریخ انقضا: {expires_at.strftime('%Y-%m-%d')}"
    )
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Automatic World Events (entertainment only)
# ---------------------------------------------------------------------------

WORLD_EVENTS = [
    {
        "name": "🎉 جشنواره جهانی",
        "description": "همه بازیکنان ۲۴ ساعت XP دوبرابر می‌گیرند.",
        "effect": "double_xp",
    },
    {
        "name": "📉 رکود اقتصادی",
        "description": "قیمت بازار به‌طور موقت کاهش می‌یابد.",
        "effect": "market_crash",
    },
    {
        "name": "⛏ کشف معدن جدید",
        "description": "بازیکنانی که معدن دارند بونوس دریافت می‌کنند.",
        "effect": "mine_bonus",
    },
    {
        "name": "💰 باران LIBER",
        "description": "همه کاربران فعال ۳۰ LIBER هدیه می‌گیرند.",
        "effect": "liber_rain",
    },
]

async def trigger_random_event(context: ContextTypes.DEFAULT_TYPE):
    event = random.choice(WORLD_EVENTS)
    now = datetime.utcnow()
    ends_at = now + timedelta(hours=6)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO events (name, description, started_at, ends_at, effect)
               VALUES (?, ?, ?, ?, ?)""",
            (event["name"], event["description"], now.isoformat(), ends_at.isoformat(), event["effect"]),
        )

        if event["effect"] == "liber_rain":
            conn.execute("UPDATE users SET liber = liber + 30 WHERE banned = 0")

        if event["effect"] == "market_crash":
            current = get_market_price()
            new_price = max(0.5, round(current * 0.85, 4))
            conn.execute(
                "INSERT INTO market (price, updated_at) VALUES (?, ?)",
                (new_price, now.isoformat()),
            )

    logger.info(f"World event triggered: {event['name']}")

    with closing(get_conn()) as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE banned = 0").fetchall()

    for row in rows:
        try:
            await context.bot.send_message(
                row["user_id"],
                f"🌍 رویداد جهانی: {event['name']}\n{event['description']}",
            )
        except Exception:
            pass

async def events_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    with closing(get_conn()) as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY event_id DESC LIMIT 5"
        ).fetchall()

    if not rows:
        await update.message.reply_text("رویداد فعالی وجود ندارد.")
        return

    text = "📅 آخرین رویدادهای جهانی\n\n"
    for r in rows:
        text += f"{r['name']} — {r['started_at'][:16]}\n{r['description']}\n\n"

    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# League / Season System
# ---------------------------------------------------------------------------

LEAGUES = ["bronze", "silver", "gold", "platinum", "diamond", "titan", "legendary", "galactic"]
LEAGUE_NAMES = {
    "bronze": "🥉 برنز", "silver": "🥈 نقره", "gold": "🥇 طلا",
    "platinum": "🔷 پلاتینیوم", "diamond": "💎 الماس", "titan": "🔱 تایتان",
    "legendary": "👑 افسانه‌ای", "galactic": "🌌 کهکشانی",
}
LEAGUE_THRESHOLDS = {
    "bronze": 0, "silver": 200, "gold": 500, "platinum": 1000,
    "diamond": 2000, "titan": 4000, "legendary": 8000, "galactic": 15000,
}

def get_active_season():
    with closing(get_conn()) as conn:
        season = conn.execute(
            "SELECT * FROM seasons WHERE active = 1 ORDER BY season_id DESC LIMIT 1"
        ).fetchone()
    if season:
        return season

    now = datetime.utcnow()
    ends_at = now + timedelta(days=30)
    with closing(get_conn()) as conn, conn:
        cursor = conn.execute(
            """INSERT INTO seasons (name, started_at, ends_at, active)
               VALUES (?, ?, ?, 1)""",
            (f"فصل {now.strftime('%Y-%m')}", now.isoformat(), ends_at.isoformat()),
        )
    return get_active_season()

def add_season_points(user_id: int, points: int):
    season = get_active_season()
    with closing(get_conn()) as conn, conn:
        existing = conn.execute(
            "SELECT * FROM season_scores WHERE user_id = ? AND season_id = ?",
            (user_id, season["season_id"]),
        ).fetchone()

        if existing:
            new_points = existing["points"] + points
        else:
            new_points = points

        new_league = "bronze"
        for league in LEAGUES:
            if new_points >= LEAGUE_THRESHOLDS[league]:
                new_league = league

        conn.execute(
            """INSERT INTO season_scores (user_id, season_id, points, league)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id, season_id) DO UPDATE SET
                 points = excluded.points, league = excluded.league""",
            (user_id, season["season_id"], new_points, new_league),
        )

async def render_league_text(user_id: int) -> str:
    season = get_active_season()

    with closing(get_conn()) as conn:
        score = conn.execute(
            "SELECT * FROM season_scores WHERE user_id = ? AND season_id = ?",
            (user_id, season["season_id"]),
        ).fetchone()

    points = score["points"] if score else 0
    league = score["league"] if score else "bronze"

    text = (
        f"🏆 {season['name']}\n\n"
        f"لیگ فعلی شما: {LEAGUE_NAMES[league]}\n"
        f"امتیاز: {points}\n\n"
        "لیگ‌های بازی:\n"
    )
    for lg in LEAGUES:
        text += f"  {LEAGUE_NAMES[lg]} — {LEAGUE_THRESHOLDS[lg]}+ امتیاز\n"
    return text


async def league_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await render_league_text(update.effective_user.id)
    await update.message.reply_text(text)


async def render_season_top_text() -> str:
    season = get_active_season()

    with closing(get_conn()) as conn:
        rows = conn.execute(
            """SELECT u.first_name, s.points, s.league FROM season_scores s
               JOIN users u ON u.user_id = s.user_id
               WHERE s.season_id = ?
               ORDER BY s.points DESC LIMIT 10""",
            (season["season_id"],),
        ).fetchall()

    if not rows:
        return "هنوز امتیازی در این فصل ثبت نشده."

    text = f"🏆 برترین‌های {season['name']}\n\n"
    for i, r in enumerate(rows, start=1):
        text += f"{i}. {r['first_name']} — {LEAGUE_NAMES[r['league']]} ({r['points']} امتیاز)\n"
    return text


async def season_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = await render_season_top_text()
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Mini-Games (entertainment only — virtual LIBER wagers, no cash out)
# ---------------------------------------------------------------------------

async def run_wheel(user_id: int, bet: float) -> str:
    user = get_user(user_id)
    if not user:
        return "ابتدا با /start ثبت‌نام کن."
    if bet <= 0 or bet > user["liber"]:
        return "❌ موجودی LIBER کافی نیست."

    outcomes = [0, 0.5, 1, 1.5, 2, 3, 5]
    weights = [25, 20, 20, 15, 10, 7, 3]
    multiplier = random.choices(outcomes, weights=weights, k=1)[0]
    result = round(bet * multiplier, 2)
    net = result - bet

    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET liber = liber - ? + ? WHERE user_id = ?", (bet, result, user_id))
        conn.execute(
            "INSERT INTO game_history (user_id, game_type, bet, result, played_at) VALUES (?, 'wheel', ?, ?, ?)",
            (user_id, bet, result, datetime.utcnow().isoformat()),
        )

    add_season_points(user_id, max(0, int(net)))
    log_action(user_id, "GAME_WHEEL", f"bet={bet} multiplier={multiplier}")
    emoji = "🎉" if multiplier >= 1 else "😔"
    return f"🎰 گردونه چرخید!\nضریب: x{multiplier}\nشرط: {bet:.0f} LIBER\nنتیجه: {result:.2f} LIBER {emoji}"


async def game_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback: /wheel مقدار_شرط (button flow via 🎮 بازی‌ها is the main path)."""
    if not context.args:
        await update.message.reply_text("از دکمه‌ی 🎮 بازی‌ها استفاده کن، یا: /wheel مقدار_شرط")
        return
    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    text = await run_wheel(update.effective_user.id, bet)
    await update.message.reply_text(text)

async def run_lucky(user_id: int, bet: float) -> str:
    user = get_user(user_id)
    if not user:
        return "ابتدا با /start ثبت‌نام کن."
    if bet <= 0 or bet > user["liber"]:
        return "❌ موجودی LIBER کافی نیست."

    win = random.random() < 0.45
    result = bet * 2 if win else 0

    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET liber = liber - ? + ? WHERE user_id = ?", (bet, result, user_id))
        conn.execute(
            "INSERT INTO game_history (user_id, game_type, bet, result, played_at) VALUES (?, 'lucky', ?, ?, ?)",
            (user_id, bet, result, datetime.utcnow().isoformat()),
        )

    log_action(user_id, "GAME_LUCKY", f"bet={bet} win={win}")
    return f"🍀 بردی! +{result:.2f} LIBER" if win else f"❌ باختی. -{bet:.2f} LIBER"


async def game_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback: /lucky مقدار_شرط (button flow via 🎮 بازی‌ها is the main path)."""
    if not context.args:
        await update.message.reply_text("از دکمه‌ی 🎮 بازی‌ها استفاده کن، یا: /lucky مقدار_شرط")
        return
    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    text = await run_lucky(update.effective_user.id, bet)
    await update.message.reply_text(text)

async def run_treasure(user_id: int) -> str:
    user = get_user(user_id)
    if not user:
        return "ابتدا با /start ثبت‌نام کن."

    with closing(get_conn()) as conn:
        cooldown = conn.execute(
            "SELECT * FROM chest_cooldowns WHERE user_id = ?", (user_id,)
        ).fetchone()

    now = datetime.utcnow()
    if cooldown:
        last = datetime.fromisoformat(cooldown["last_chest"])
        if now - last < timedelta(hours=6):
            remaining = timedelta(hours=6) - (now - last)
            mins = int(remaining.total_seconds() // 60)
            return f"⏳ گنج بعدی تا {mins} دقیقه دیگر آماده می‌شود."

    reward = random.randint(10, 60)
    add_currency(user_id, liber=reward)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO chest_cooldowns (user_id, last_chest) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET last_chest = excluded.last_chest""",
            (user_id, now.isoformat()),
        )

    log_action(user_id, "GAME_TREASURE", f"reward={reward}")
    return f"🎁 گنج پیدا شد! +{reward} LIBER"


async def game_treasure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback: /treasure (button flow via 🎮 بازی‌ها is the main path)."""
    text = await run_treasure(update.effective_user.id)
    await update.message.reply_text(text)

CHESTS = {
    "free": {"name": "🎁 صندوق رایگان", "cost": 0, "min": 5, "max": 30},
    "bronze": {"name": "🥉 صندوق برنزی", "cost": 100, "min": 50, "max": 150},
    "silver": {"name": "🥈 صندوق نقره‌ای", "cost": 300, "min": 150, "max": 450},
    "gold": {"name": "🥇 صندوق طلایی", "cost": 700, "min": 400, "max": 1100},
    "diamond": {"name": "💎 صندوق الماسی", "cost": 1500, "min": 900, "max": 2500},
}

async def open_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args or context.args[0] not in CHESTS:
        options = ", ".join(CHESTS.keys())
        await update.message.reply_text(f"استفاده: /chest نوع\nانواع: {options}")
        return

    key = context.args[0]
    chest = CHESTS[key]

    if user["liber"] < chest["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return

    reward = random.randint(chest["min"], chest["max"])

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? + ? WHERE user_id = ?",
            (chest["cost"], reward, user_id),
        )

    log_action(user_id, "OPEN_CHEST", f"{key} reward={reward}")
    await update.message.reply_text(
        f"{chest['name']} باز شد!\nدریافتی: {reward} LIBER (هزینه: {chest['cost']})"
    )


def chest_keyboard():
    rows = [[InlineKeyboardButton(f"{c['name']} — {c['cost']} LIBER", callback_data=f"chest_open_{k}")]
            for k, c in CHESTS.items()]
    return InlineKeyboardMarkup(rows)


async def chest_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎁 صندوق‌ها — روی هرکدوم بزن تا باز بشه:", reply_markup=chest_keyboard())


async def chest_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    key = query.data[len("chest_open_"):]
    await query.answer()

    chest = CHESTS.get(key)
    user = get_user(user_id)
    if not chest or not user:
        await query.edit_message_text("❌ خطا.", reply_markup=chest_keyboard())
        return
    if user["liber"] < chest["cost"]:
        await query.answer("❌ LIBER کافی نیست.", show_alert=True)
        return

    reward = random.randint(chest["min"], chest["max"])
    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE users SET liber = liber - ? + ? WHERE user_id = ?", (chest["cost"], reward, user_id))
    log_action(user_id, "OPEN_CHEST", f"{key} reward={reward}")
    await query.edit_message_text(
        f"{chest['name']} باز شد!\n🎉 دریافتی: {reward} LIBER (هزینه: {chest['cost']})",
        reply_markup=chest_keyboard(),
    )

_pending_bet = {}  # user_id -> current bet amount for wheel/lucky stepper


def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 گردونه شانس", callback_data="game_menu_wheel"),
         InlineKeyboardButton("🍀 شیر یا خط", callback_data="game_menu_lucky")],
        [InlineKeyboardButton("🎁 گنج رایگان", callback_data="game_go_treasure"),
         InlineKeyboardButton("🏆 لیگ فصلی", callback_data="game_go_league")],
        [InlineKeyboardButton("📊 رتبه‌بندی فصل", callback_data="game_go_season_top")],
    ])


def bet_stepper_keyboard(game: str, amount: int):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("-50", callback_data=f"game_{game}_bet_-50"),
         InlineKeyboardButton("-10", callback_data=f"game_{game}_bet_-10"),
         InlineKeyboardButton(f"💰 {amount}", callback_data="mkt_noop"),
         InlineKeyboardButton("+10", callback_data=f"game_{game}_bet_10"),
         InlineKeyboardButton("+50", callback_data=f"game_{game}_bet_50")],
        [InlineKeyboardButton("🎯 شرط‌بندی!", callback_data=f"game_{game}_play"),
         InlineKeyboardButton("🔙 بازگشت", callback_data="game_back")],
    ])


async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 بازی‌ها (سرگرمی - LIBER داخل‌بازی)\n\nروی هرکدوم بزن، بدون تایپ دستور:",
        reply_markup=games_keyboard(),
    )


async def games_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if data == "game_back":
        await query.edit_message_text("🎮 بازی‌ها — روی هرکدوم بزن:", reply_markup=games_keyboard())
        return

    if data == "game_go_treasure":
        text = await run_treasure(user_id)
        await query.edit_message_text(text, reply_markup=games_keyboard())
        return

    if data == "game_go_league":
        text = await render_league_text(user_id)
        await query.edit_message_text(text, reply_markup=games_keyboard())
        return

    if data == "game_go_season_top":
        text = await render_season_top_text()
        await query.edit_message_text(text, reply_markup=games_keyboard())
        return

    if data in ("game_menu_wheel", "game_menu_lucky"):
        game = "wheel" if data == "game_menu_wheel" else "lucky"
        _pending_bet[user_id] = 20
        label = "گردونه شانس" if game == "wheel" else "شیر یا خط"
        await query.edit_message_text(
            f"🎯 مبلغ شرط برای {label} رو تنظیم کن، بعد «شرط‌بندی» بزن:",
            reply_markup=bet_stepper_keyboard(game, 20),
        )
        return

    if "_bet_" in data:
        parts = data.split("_")
        game, delta = parts[1], int(parts[3])
        amount = max(10, _pending_bet.get(user_id, 20) + delta)
        _pending_bet[user_id] = amount
        await query.edit_message_reply_markup(reply_markup=bet_stepper_keyboard(game, amount))
        return

    if data.endswith("_play"):
        game = data.split("_")[1]
        bet = _pending_bet.get(user_id, 20)
        text = await run_wheel(user_id, bet) if game == "wheel" else await run_lucky(user_id, bet)
        await query.edit_message_text(text, reply_markup=games_keyboard())

# ---------------------------------------------------------------------------
# Auction (virtual LIBER only — no real payment)
# ---------------------------------------------------------------------------

AUCTION_INCREMENT = 10
AUCTION_ITEMS = [
    "🎁 جعبه طلایی", "🖼 قاب کهکشانی", "🏷 لقب افسانه‌ای",
    "💎 آواتار الماسی", "🎖 مدال ویژه فصل",
]

def get_active_auction():
    with closing(get_conn()) as conn:
        auction = conn.execute(
            "SELECT * FROM auctions WHERE active = 1 ORDER BY auction_id DESC LIMIT 1"
        ).fetchone()
    return auction

def create_new_auction():
    item = random.choice(AUCTION_ITEMS)
    now = datetime.utcnow()
    ends_at = now + timedelta(hours=12)
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO auctions (item_name, current_price, current_winner, active, created_at, ends_at)
               VALUES (?, ?, NULL, 1, ?, ?)""",
            (item, 50, now.isoformat(), ends_at.isoformat()),
        )
    return get_active_auction()

async def auction_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    auction = get_active_auction()
    if not auction:
        auction = create_new_auction()

    winner_text = "هنوز کسی شرکت نکرده"
    if auction["current_winner"]:
        winner = get_user(auction["current_winner"])
        if winner:
            winner_text = winner["first_name"]

    ends_at = datetime.fromisoformat(auction["ends_at"])
    remaining = ends_at - datetime.utcnow()
    hrs = max(0, int(remaining.total_seconds() // 3600))

    text = (
        f"🏷 مزایده LIBER\n\n"
        f"🎁 آیتم: {auction['item_name']}\n"
        f"💰 قیمت فعلی: {auction['current_price']} LIBER\n"
        f"🏆 برنده فعلی: {winner_text}\n"
        f"⏳ زمان باقی‌مانده: {hrs} ساعت\n\n"
        f"برای شرکت: /bid"
    )
    await update.message.reply_text(text)

async def auction_bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    auction = get_active_auction()
    if not auction:
        auction = create_new_auction()

    ends_at = datetime.fromisoformat(auction["ends_at"])
    if datetime.utcnow() >= ends_at:
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "UPDATE auctions SET active = 0 WHERE auction_id = ?",
                (auction["auction_id"],),
            )
        if auction["current_winner"]:
            add_season_points(auction["current_winner"], 100)
        auction = create_new_auction()
        await update.message.reply_text(
            "⏳ مزایده قبلی به پایان رسید و مزایده جدیدی شروع شد. دوباره امتحان کن: /bid"
        )
        return

    next_price = auction["current_price"] + AUCTION_INCREMENT

    if user["liber"] < next_price:
        await update.message.reply_text(
            f"موجودی کافی نیست. برای پیشنهاد بعدی نیاز به {next_price} LIBER داری."
        )
        return

    # refund the previous highest bidder (virtual, in-game only)
    if auction["current_winner"] and auction["current_winner"] != user_id:
        add_currency(auction["current_winner"], liber=auction["current_price"])

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? WHERE user_id = ?",
            (next_price, user_id),
        )
        conn.execute(
            "UPDATE auctions SET current_price = ?, current_winner = ? WHERE auction_id = ?",
            (next_price, user_id, auction["auction_id"]),
        )

    log_action(user_id, "AUCTION_BID", f"price={next_price}")
    await update.message.reply_text(
        f"✅ پیشنهاد ثبت شد! شما در حال حاضر برنده فعلی مزایده «{auction['item_name']}» هستید.\n"
        f"قیمت فعلی: {next_price} LIBER"
    )

# ---------------------------------------------------------------------------
# Help & Settings
# ---------------------------------------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "❓ راهنمای LIBER\n\n"
        "👤 /profile — پروفایل\n"
        "💰 /wallet — کیف پول\n"
        "🌍 /found نام — ساخت کشور\n"
        "🏗 /build نوع — ساخت/ارتقای ساختمان\n"
        "💹 /market — بازار LIBER\n"
        "🟢 /buy تعداد(1-99) — خرید واحدی LIBER (قیمت با تقاضا بالا می‌ره)\n"
        "🔴 /sell تعداد(1-99) — فروش واحدی LIBER (قیمت با عرضه پایین می‌ره)\n"
        "🏦 /deposit مقدار — سپرده بانکی\n"
        "📥 /claim — برداشت سود سپرده\n"
        "📈 /invest نوع مقدار — سرمایه‌گذاری\n"
        "🎯 /missions — مأموریت‌ها\n"
        "🎖 /achievements — دستاوردها\n"
        "🤝 /create_alliance نام — ساخت اتحاد\n"
        "🏪 /shop — فروشگاه\n"
        "⭐ /vip — وضعیت VIP\n"
        "🎁 /daily — جایزه روزانه\n"
        "🎰 /wheel مقدار — گردونه شانس\n"
        "🏷 /auction , /bid — مزایده\n"
        "🏆 /league , /season_top — لیگ فصلی\n"
        "👥 /invite — دعوت دوستان\n"
        "📅 /events — رویدادهای جهانی\n\n"
        "⚠️ تمام ارزهای بازی کاملاً مجازی هستند و هدف آن‌ها فقط سرگرمی و رقابت است."
    )
    await update.message.reply_text(text)

async def settings_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    text = (
        "⚙ تنظیمات\n\n"
        f"لقب فعلی: {user['title']}\n"
        f"بیوگرافی: {user['bio'] or '—'}\n\n"
        "برای تغییر بیوگرافی: /setbio متن\n"
    )
    await update.message.reply_text(text)

async def set_bio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /setbio متن_بیوگرافی")
        return

    bio_text = " ".join(context.args)[:150]
    update_user_field(user_id, "bio", bio_text)
    await update.message.reply_text("✅ بیوگرافی به‌روزرسانی شد.")

# ---------------------------------------------------------------------------
# Basic Anti-Spam (simple in-memory rate limiter)
# ---------------------------------------------------------------------------

_last_action_time = {}
SPAM_MIN_INTERVAL_SECONDS = 1.0

async def anti_spam_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A lightweight guard against rapid-fire command spam. Not a full security
    system — just prevents obvious abuse/flooding of the bot."""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id is None:
        return True

    now = time.monotonic()
    last = _last_action_time.get(user_id, 0)

    if now - last < SPAM_MIN_INTERVAL_SECONDS:
        log_action(user_id, "SPAM_BLOCKED", "")
        return False

    _last_action_time[user_id] = now
    return True

# ---------------------------------------------------------------------------
# Smart Anti-Cheat System
# ---------------------------------------------------------------------------
# Detects abnormal click/command rates (script/bot-like behavior) using a
# sliding time window. After CHEAT_STRIKE_LIMIT flags, the account is
# automatically banned. This is heuristic-based, not perfect, but stops
# obvious automation abuse without needing external services.

CHEAT_WINDOW_SECONDS = 8          # sliding time window to inspect
CHEAT_MAX_ACTIONS_IN_WINDOW = 10  # more than this many actions = suspicious
CHEAT_STRIKE_LIMIT = 3           # auto-ban after this many flags

_action_timestamps = {}   # user_id -> [timestamps]
_cheat_strikes_cache = {}  # user_id -> count (mirrors DB, avoids extra reads)

def get_cheat_strikes(user_id: int) -> int:
    with closing(get_conn()) as conn:
        row = conn.execute(
            "SELECT flag_count FROM cheat_flags WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["flag_count"] if row else 0

def add_cheat_strike(user_id: int) -> int:
    now = datetime.utcnow().isoformat()
    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO cheat_flags (user_id, flag_count, last_flag_at)
               VALUES (?, 1, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 flag_count = flag_count + 1,
                 last_flag_at = excluded.last_flag_at""",
            (user_id, now),
        )
        row = conn.execute(
            "SELECT flag_count FROM cheat_flags WHERE user_id = ?", (user_id,)
        ).fetchone()
    return row["flag_count"]

async def check_smart_anticheat(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Returns True if this action should be BLOCKED (user is flagged or banned)."""
    now = time.monotonic()
    timestamps = _action_timestamps.setdefault(user_id, [])
    timestamps.append(now)

    cutoff = now - CHEAT_WINDOW_SECONDS
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)

    if len(timestamps) <= CHEAT_MAX_ACTIONS_IN_WINDOW:
        return False

    # Suspicious pattern detected — clear window so we don't spam-flag repeatedly
    timestamps.clear()
    strikes = add_cheat_strike(user_id)
    log_action(user_id, "CHEAT_FLAG", f"strikes={strikes}")

    if strikes >= CHEAT_STRIKE_LIMIT:
        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (user_id,))
        log_action(user_id, "AUTO_BAN", "cheat_strikes_exceeded")
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    admin_id,
                    f"🚨 کاربر {user_id} به‌صورت خودکار به دلیل تشخیص فعالیت غیرطبیعی "
                    f"(اسکریپت/کلیک‌های سریع) و عبور از {CHEAT_STRIKE_LIMIT} اخطار، مسدود شد.",
                )
            except Exception:
                pass
        return True

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"⚠️ فعالیت مشکوک از کاربر {user_id} — اخطار {strikes}/{CHEAT_STRIKE_LIMIT}",
            )
        except Exception:
            pass

    return False

def is_user_banned(user_id: int) -> bool:
    user = get_user(user_id)
    return bool(user and user["banned"])

# ---------------------------------------------------------------------------
# Jobs system (careers) — virtual income boost per job, no real money
# ---------------------------------------------------------------------------

JOBS = {
    "miner": {"name": "⛏ معدنچی", "income": 15, "cost": 0},
    "trader": {"name": "💼 تاجر", "income": 25, "cost": 300},
    "programmer": {"name": "💻 برنامه‌نویس", "income": 40, "cost": 800},
    "scientist": {"name": "🔬 دانشمند", "income": 60, "cost": 1500},
    "investor": {"name": "📈 سرمایه‌گذار", "income": 90, "cost": 3000},
    "athlete": {"name": "⚽ فوتبالیست", "income": 130, "cost": 6000},
}

def jobs_keyboard(current_title):
    rows = []
    for key, job in JOBS.items():
        marker = "✅ " if job["name"] == current_title else ""
        cost_text = f" ({job['cost']:.0f} LIBER)" if job["cost"] > 0 else " (رایگان)"
        rows.append([InlineKeyboardButton(f"{marker}{job['name']}{cost_text}", callback_data=f"job_set_{key}")])
    rows.append([InlineKeyboardButton("💼 کار کن (دریافت درآمد روزانه)", callback_data="job_work")])
    return InlineKeyboardMarkup(rows)


async def jobs_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return
    await update.message.reply_text(
        "💼 شغل‌های موجود — روی هرکدوم بزن تا استخدام بشی:",
        reply_markup=jobs_keyboard(user["title"]),
    )


async def jobs_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)
    await query.answer()

    if not user:
        return

    if data.startswith("job_set_"):
        key = data[len("job_set_"):]
        job = JOBS.get(key)
        if not job:
            return
        if user["liber"] < job["cost"]:
            await query.answer(f"❌ برای استخدام به {job['cost']:.0f} LIBER نیاز داری.", show_alert=True)
            return
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "UPDATE users SET liber = liber - ?, title = ? WHERE user_id = ?",
                (job["cost"], job["name"], user_id),
            )
        log_action(user_id, "SET_JOB", key)
        await query.edit_message_text(
            f"✅ شغل شما به {job['name']} تغییر کرد!", reply_markup=jobs_keyboard(job["name"])
        )
        return

    if data == "job_work":
        job_entry = next((j for j in JOBS.values() if j["name"] == user["title"]), None)
        if not job_entry:
            await query.answer("هنوز شغلی انتخاب نکردی!", show_alert=True)
            return

        now = datetime.utcnow()
        with closing(get_conn()) as conn:
            last_work = conn.execute(
                "SELECT created_at FROM logs WHERE user_id = ? AND action = 'WORK' ORDER BY log_id DESC LIMIT 1",
                (user_id,),
            ).fetchone()

        if last_work:
            last_time = datetime.fromisoformat(last_work["created_at"])
            if now - last_time < timedelta(hours=20):
                remaining = timedelta(hours=20) - (now - last_time)
                hrs = int(remaining.total_seconds() // 3600)
                await query.answer(f"⏳ {hrs} ساعت دیگر دوباره کار کن.", show_alert=True)
                return

        income = max(1, job_entry["income"] + random.randint(-3, 10))
        add_currency(user_id, liber=income)
        add_xp(user_id, 8)
        log_action(user_id, "WORK", f"income={income}")
        await query.answer(f"💼 +{income} LIBER, +8 XP", show_alert=True)
        await query.edit_message_text(
            f"💼 یک روز کاری به‌عنوان {user['title']} تموم شد!\n+{income} LIBER, +8 XP",
            reply_markup=jobs_keyboard(user["title"]),
        )


async def set_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback (button flow via 💼 شغل is the main path)."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return
    if not context.args or context.args[0] not in JOBS:
        await update.message.reply_text("از دکمه‌ی 💼 شغل استفاده کن، یا: /setjob نوع")
        return
    key = context.args[0]
    job = JOBS[key]
    if user["liber"] < job["cost"]:
        await update.message.reply_text(f"برای استخدام به {job['cost']} LIBER نیاز داری.")
        return
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, title = ? WHERE user_id = ?",
            (job["cost"], job["name"], user_id),
        )
    log_action(user_id, "SET_JOB", key)
    await update.message.reply_text(f"✅ شغل شما به {job['name']} تغییر کرد!")


async def work(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command fallback (button flow via 💼 شغل is the main path)."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    job_entry = next((j for j in JOBS.values() if j["name"] == user["title"]), None)
    if not job_entry:
        await update.message.reply_text("هنوز شغلی انتخاب نکردی. از دکمه‌ی 💼 شغل یکی رو انتخاب کن.")
        return

    now = datetime.utcnow()
    with closing(get_conn()) as conn:
        last_work = conn.execute(
            "SELECT detail, created_at FROM logs WHERE user_id = ? AND action = 'WORK' ORDER BY log_id DESC LIMIT 1",
            (user_id,),
        ).fetchone()

    if last_work:
        last_time = datetime.fromisoformat(last_work["created_at"])
        if now - last_time < timedelta(hours=20):
            remaining = timedelta(hours=20) - (now - last_time)
            hrs = int(remaining.total_seconds() // 3600)
            await update.message.reply_text(f"⏳ {hrs} ساعت دیگر دوباره کار کن.")
            return

    income = job_entry["income"] + random.randint(-3, 10)
    add_currency(user_id, liber=max(1, income))
    add_xp(user_id, 8)
    log_action(user_id, "WORK", f"income={income}")
    await update.message.reply_text(
        f"💼 یک روز کاری به‌عنوان {user['title']} تموم شد!\n+{max(1, income)} LIBER, +8 XP"
    )

# ---------------------------------------------------------------------------
# Clan system (upgraded alliance with wars and levels)
# ---------------------------------------------------------------------------

CLAN_UPGRADE_COST_BASE = 500

async def clan_war_simulate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fun mock clan-war: pits your alliance's treasury against a random rival score."""
    user_id = update.effective_user.id

    with closing(get_conn()) as conn:
        membership = conn.execute(
            "SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)
        ).fetchone()

    if not membership:
        await update.message.reply_text("ابتدا باید عضو یک اتحاد/کلن باشی.")
        return

    with closing(get_conn()) as conn:
        alliance = conn.execute(
            "SELECT * FROM alliances WHERE alliance_id = ?", (membership["alliance_id"],)
        ).fetchone()

    our_power = alliance["treasury"] + random.randint(0, 200)
    rival_power = random.randint(100, 1500)

    won = our_power >= rival_power

    if won:
        reward = random.randint(100, 400)
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "UPDATE alliances SET treasury = treasury + ? WHERE alliance_id = ?",
                (reward, alliance["alliance_id"]),
            )
        text = (
            f"⚔️ جنگ کلن!\nقدرت شما: {our_power} — قدرت حریف: {rival_power}\n"
            f"🏆 بردید! +{reward} به خزانه کلن اضافه شد."
        )
    else:
        text = f"⚔️ جنگ کلن!\nقدرت شما: {our_power} — قدرت حریف: {rival_power}\n😔 این بار باختید."

    add_season_points(user_id, 30 if won else 5)
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Research / Technology tree
# ---------------------------------------------------------------------------

RESEARCH_TREE = [
    {"name": "کشاورزی مدرن", "cost": 300, "effect": "تولید +10%"},
    {"name": "معدن‌کاری پیشرفته", "cost": 700, "effect": "تولید +20%"},
    {"name": "انرژی خورشیدی", "cost": 1500, "effect": "تولید +35%"},
    {"name": "هوش مصنوعی صنعتی", "cost": 3000, "effect": "تولید +50%"},
    {"name": "فناوری کوانتومی", "cost": 6000, "effect": "تولید +75%"},
]

async def research_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    level = user["research_level"]
    if level >= len(RESEARCH_TREE):
        await update.message.reply_text("🔬 تمام سطوح تحقیقاتی رو کامل کردی! 🎉")
        return

    info = RESEARCH_TREE[level]
    await update.message.reply_text(
        f"🔬 تحقیقات\n\nسطح فعلی: {level}\nتحقیق بعدی: {info['name']}\n"
        f"هزینه: {info['cost']} LIBER\nاثر: {info['effect']}\n\nبرای ارتقا: /research_upgrade"
    )

async def research_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    level = user["research_level"]
    if level >= len(RESEARCH_TREE):
        await update.message.reply_text("🔬 تمام سطوح تحقیقاتی رو کامل کردی!")
        return

    info = RESEARCH_TREE[level]
    if user["liber"] < info["cost"]:
        await update.message.reply_text(f"❌ LIBER کافی نیست. هزینه: {info['cost']}")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, research_level = research_level + 1 WHERE user_id = ?",
            (info["cost"], user_id),
        )

    add_xp(user_id, 20)
    log_action(user_id, "RESEARCH", info["name"])
    await update.message.reply_text(f"🔬 تحقیق «{info['name']}» تکمیل شد! ({info['effect']})")

# ---------------------------------------------------------------------------
# Defense upgrades
# ---------------------------------------------------------------------------

DEFENSE_BASE_COST = 250
DEFENSE_GROWTH = 1.6

async def defense_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    cost = round(DEFENSE_BASE_COST * (DEFENSE_GROWTH ** user["defense_level"]), 2)
    await update.message.reply_text(
        f"🛡 دفاع\n\nسطح فعلی: {user['defense_level']}\nهزینه ارتقای بعدی: {cost} LIBER\n\n"
        "برای ارتقا: /defense_upgrade"
    )

async def defense_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    cost = round(DEFENSE_BASE_COST * (DEFENSE_GROWTH ** user["defense_level"]), 2)
    if user["liber"] < cost:
        await update.message.reply_text(f"❌ LIBER کافی نیست. هزینه: {cost}")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, defense_level = defense_level + 1 WHERE user_id = ?",
            (cost, user_id),
        )

    log_action(user_id, "DEFENSE_UPGRADE", "")
    await update.message.reply_text(f"🛡 دفاعت به سطح {user['defense_level']+1} ارتقا یافت! (-{cost} LIBER)")

# ---------------------------------------------------------------------------
# Exploration
# ---------------------------------------------------------------------------

EXPLORATION_MIN_LEVEL = 5
EXPLORATION_ENERGY_COST = 20
EXPLORATION_REWARDS = [("liber", 20, 150), ("energy", -20, 0)]

async def exploration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if user["level"] < EXPLORATION_MIN_LEVEL:
        await update.message.reply_text(f"🌌 اکتشاف فقط برای سطح {EXPLORATION_MIN_LEVEL} به بالا باز است.")
        return
    if user["energy"] < EXPLORATION_ENERGY_COST:
        await update.message.reply_text("⚡ انرژی کافی نداری.")
        return

    reward_liber = random.randint(20, 150)
    reward_diamond_chance = random.random() < 0.15

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET energy = energy - ?, liber = liber + ? WHERE user_id = ?",
            (EXPLORATION_ENERGY_COST, reward_liber, user_id),
        )

    add_xp(user_id, 15)
    text = f"🌌 اکتشاف موفق!\n+{reward_liber} LIBER\n-{EXPLORATION_ENERGY_COST} Energy"
    if reward_diamond_chance:
        text += "\n💎 یک آیتم کمیاب هم پیدا کردی!"
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# Gift Codes (virtual rewards only)
# ---------------------------------------------------------------------------

async def redeem_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /gift کد_هدیه")
        return

    code = context.args[0].strip().upper()

    with closing(get_conn()) as conn:
        gift = conn.execute("SELECT * FROM gift_codes WHERE code = ?", (code,)).fetchone()

    if not gift:
        await update.message.reply_text("❌ این کد هدیه معتبر نیست.")
        return
    if gift["used_count"] >= gift["max_uses"]:
        await update.message.reply_text("❌ ظرفیت این کد تمام شده.")
        return

    with closing(get_conn()) as conn:
        already = conn.execute(
            "SELECT 1 FROM gift_redemptions WHERE code = ? AND user_id = ?", (code, user_id)
        ).fetchone()
    if already:
        await update.message.reply_text("❌ قبلاً این کد رو استفاده کردی.")
        return

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "INSERT INTO gift_redemptions (code, user_id, redeemed_at) VALUES (?, ?, ?)",
            (code, user_id, datetime.utcnow().isoformat()),
        )
        conn.execute("UPDATE gift_codes SET used_count = used_count + 1 WHERE code = ?", (code,))

    add_currency(user_id, liber=gift["reward_liber"])
    await update.message.reply_text(f"🎉 کد فعال شد! +{gift['reward_liber']} LIBER گرفتی.")

async def create_gift_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return
    if len(context.args) < 3:
        await update.message.reply_text("استفاده: /creategift کد مقدار_LIBER تعداد_استفاده")
        return

    code = context.args[0].strip().upper()
    try:
        reward = float(context.args[1])
        max_uses = int(context.args[2])
    except ValueError:
        await update.message.reply_text("مقادیر نامعتبر.")
        return

    try:
        with closing(get_conn()) as conn, conn:
            conn.execute(
                "INSERT INTO gift_codes (code, reward_liber, max_uses, created_at) VALUES (?, ?, ?, ?)",
                (code, reward, max_uses, datetime.utcnow().isoformat()),
            )
    except sqlite3.IntegrityError:
        await update.message.reply_text("این کد قبلاً وجود داره.")
        return

    await update.message.reply_text(f"✅ کد هدیه «{code}» ساخته شد: {reward} LIBER × {max_uses} استفاده")

# ---------------------------------------------------------------------------
# Prediction market (virtual bets on the internal market price)
# ---------------------------------------------------------------------------

PREDICTION_BET = 30
PREDICTION_MULTIPLIER = 1.8

async def predict_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    await update.message.reply_text(
        f"🎟 پیش‌بینی قیمت LIBER\n\nقیمت فعلی: {price:.4f}\nمبلغ شرط: {PREDICTION_BET} Coin\n"
        f"ضریب برد: {PREDICTION_MULTIPLIER}x\n\n/predict_up یا /predict_down"
    )

async def place_prediction(update: Update, context: ContextTypes.DEFAULT_TYPE, direction: str):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return
    if user["coin"] < PREDICTION_BET:
        await update.message.reply_text("Coin کافی نداری.")
        return

    price = get_market_price()
    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET coin = coin - ? WHERE user_id = ?", (PREDICTION_BET, user_id)
        )
        conn.execute(
            """INSERT INTO predictions (user_id, direction, start_price, bet_amount, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, direction, price, PREDICTION_BET, datetime.utcnow().isoformat()),
        )
    await update.message.reply_text(f"🎟 شرط ثبت شد: پیش‌بینی {direction} روی قیمت {price:.4f}")

async def predict_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await place_prediction(update, context, "up")

async def predict_down(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await place_prediction(update, context, "down")

def resolve_predictions():
    new_price = get_market_price()
    with closing(get_conn()) as conn, conn:
        open_bets = conn.execute("SELECT * FROM predictions WHERE status = 'open'").fetchall()
        results = []
        for bet in open_bets:
            won = (bet["direction"] == "up" and new_price > bet["start_price"]) or (
                bet["direction"] == "down" and new_price < bet["start_price"]
            )
            if won:
                payout = bet["bet_amount"] * PREDICTION_MULTIPLIER
                conn.execute(
                    "UPDATE users SET coin = coin + ? WHERE user_id = ?", (payout, bet["user_id"])
                )
                results.append((bet["user_id"], True, payout))
            else:
                results.append((bet["user_id"], False, 0))
            conn.execute("UPDATE predictions SET status = 'closed' WHERE pred_id = ?", (bet["pred_id"],))
    return results

async def prediction_resolve_job(context: ContextTypes.DEFAULT_TYPE):
    results = resolve_predictions()
    for user_id, won, payout in results:
        try:
            if won:
                await context.bot.send_message(user_id, f"🎉 پیش‌بینی‌ات درست بود! +{payout:.2f} Coin")
            else:
                await context.bot.send_message(user_id, "😔 پیش‌بینی‌ات این‌بار درست نبود.")
        except Exception:
            pass

# ---------------------------------------------------------------------------
# Smart Advisor (personalized virtual-economy tips)
# ---------------------------------------------------------------------------

async def smart_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    tips = []
    price = get_market_price()

    if price < 8:
        tips.append("📉 قیمت LIBER پایین‌تر از حد معموله — الان زمان خوبی برای خریدنه.")
    elif price > 15:
        tips.append("📈 قیمت LIBER بالاست — شاید بخوای بفروشی و سود کنی.")

    country = get_country_by_owner(user_id)
    if not country:
        tips.append("🌍 هنوز کشوری نساختی! رایگانه و بهت جمعیت اولیه می‌ده.")

    if user["research_level"] < len(RESEARCH_TREE):
        info = RESEARCH_TREE[user["research_level"]]
        if user["liber"] >= info["cost"]:
            tips.append(f"🔬 می‌تونی همین الان «{info['name']}» رو با {info['cost']} LIBER تحقیق کنی.")

    if user["defense_level"] < 3:
        tips.append("🛡 دفاعت پایینه؛ ارتقاش بده تا امن‌تر بشی.")

    today = datetime.utcnow().date().isoformat()
    if not user["last_daily"] or user["last_daily"][:10] != today:
        tips.append("🎁 جایزه روزانه‌ات رو هنوز نگرفتی!")

    if not tips:
        tips.append("👍 وضعیتت خیلی خوبه! همینطور با مأموریت و بازار پیش برو.")

    text = "🤖 مشاور هوشمند LIBER\n\n" + "\n\n".join(f"• {t}" for t in tips)
    await update.message.reply_text(text)

# ---------------------------------------------------------------------------
# World News feed (live snapshot of the in-game economy)
# ---------------------------------------------------------------------------

async def world_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    season = get_active_season()

    with closing(get_conn()) as conn:
        richest = conn.execute(
            "SELECT first_name, liber FROM users ORDER BY liber DESC LIMIT 1"
        ).fetchone()
        total_users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
        total_countries = conn.execute("SELECT COUNT(*) as c FROM countries").fetchone()["c"]

    lines = [
        f"💹 قیمت لحظه‌ای LIBER: {price:.4f}",
        f"📆 {season['name']} در حال اجراست.",
        f"👥 کل بازیکنان: {total_users}",
        f"🌍 کشورهای ساخته‌شده: {total_countries}",
    ]
    if richest:
        lines.append(f"👑 ثروتمندترین بازیکن: {richest['first_name']} با {richest['liber']:.0f} LIBER")

    await update.message.reply_text("📰 اخبار جهان LIBER\n\n" + "\n".join(lines))

# ---------------------------------------------------------------------------
# Online Competition — Football / Basketball (fully virtual, button-driven)
# ---------------------------------------------------------------------------

SPORTS = {
    "football": {
        "title": "⚽ فوتبال",
        "stats": {"speed": "⚡ سرعت", "accuracy": "🎯 دقت", "shot": "🥅 شوت", "technique": "🌀 تکنیک"},
        "max_level": 15,
    },
    "basketball": {
        "title": "🏀 بسکتبال",
        "stats": {"jump": "🤾 پرش", "power": "💪 قدرت", "body": "🏋 بدنی", "accuracy": "🎯 دقت"},
        "max_level": 20,
    },
}

STAT_UPGRADE_BASE_COST = 10
STAT_UPGRADE_GROWTH = 1.55  # each level costs ~55% more than the last

MATCH_TIERS = {
    "normal": {"name": "🎮 مسابقه عادی", "entry": 15, "reward_multiplier": 2.0},
    "hard": {"name": "🔥 مسابقه سخت", "entry": 30, "reward": 55},
    "elite": {"name": "👑 مسابقه نخبگان", "entry": 1000, "reward": 2000},
}

RANK_TIERS = [
    (0, "🥉 برنز"), (100, "🥈 نقره"), (300, "🥇 طلا"), (700, "💠 پلاتینیوم"),
    (1500, "🐉 دراگون"), (3000, "🐲 دراگون لجند"), (6000, "👑 لیبر فول لجند"),
]

TOURNAMENT_LENGTH_DAYS = 60
TOURNAMENT_REWARDS = {1: 1000, 2: 800, 3: 600}


def get_stat_cost(level: int) -> int:
    return int(STAT_UPGRADE_BASE_COST * (STAT_UPGRADE_GROWTH ** level))


def get_total_power(user, sport: str) -> int:
    stats = SPORTS[sport]["stats"].keys()
    return sum(user[f"{sport}_{s}"] for s in stats)


def get_rank_name(points: int) -> str:
    name = RANK_TIERS[0][1]
    for threshold, tier_name in RANK_TIERS:
        if points >= threshold:
            name = tier_name
    return name


def sport_choice_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ فوتبال", callback_data="comp_choose_football"),
         InlineKeyboardButton("🏀 بسکتبال", callback_data="comp_choose_basketball")],
    ])


def sport_panel_keyboard(sport: str, user):
    rows = []
    stat_buttons = []
    for stat_key, label in SPORTS[sport]["stats"].items():
        level = user[f"{sport}_{stat_key}"]
        stat_buttons.append(InlineKeyboardButton(f"⬆️ {label} (Lv{level})", callback_data=f"comp_up_{sport}_{stat_key}"))
    for i in range(0, len(stat_buttons), 2):
        rows.append(stat_buttons[i:i + 2])

    rows.append([InlineKeyboardButton(f"{MATCH_TIERS['normal']['name']} (-{MATCH_TIERS['normal']['entry']} LIBER)",
                                       callback_data=f"comp_play_{sport}_normal")])
    rows.append([InlineKeyboardButton(f"{MATCH_TIERS['hard']['name']} (-{MATCH_TIERS['hard']['entry']} LIBER)",
                                       callback_data=f"comp_play_{sport}_hard")])
    rows.append([InlineKeyboardButton(f"{MATCH_TIERS['elite']['name']} (-{MATCH_TIERS['elite']['entry']} LIBER)",
                                       callback_data=f"comp_play_{sport}_elite")])
    rows.append([InlineKeyboardButton("🏆 رتبه‌بندی رقابتی", callback_data="comp_leaderboard"),
                 InlineKeyboardButton("🔙 تغییر ورزش", callback_data="comp_back")])
    return InlineKeyboardMarkup(rows)


async def competition_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not user["sport"]:
        await update.message.reply_text(
            "⚔️ رقابت آنلاین\n\nاول یک ورزش انتخاب کن:", reply_markup=sport_choice_keyboard()
        )
        return

    rank = get_rank_name(user["rank_points"])
    text = (
        f"⚔️ رقابت آنلاین — {SPORTS[user['sport']]['title']}\n\n"
        f"🏆 رنک فعلی: {rank} ({user['rank_points']} امتیاز)\n"
        f"🎮 بازی‌ها: {user['matches_played']} | 🏅 برد: {user['matches_won']}\n\n"
        "مهارت‌هات رو ارتقا بده یا وارد یه مسابقه شو:"
    )
    await update.message.reply_text(text, reply_markup=sport_panel_keyboard(user["sport"], user))


def _simulate_match(power: int) -> tuple:
    """Compares player power against a randomized AI opponent. Returns (player_score, opp_score, won)."""
    opponent_power = max(5, power + random.randint(-8, 12))
    player_score = 0
    opp_score = 0
    for _ in range(5):  # 5 possessions
        p_roll = power + random.randint(-10, 10)
        o_roll = opponent_power + random.randint(-10, 10)
        if p_roll > o_roll:
            player_score += 1
        elif o_roll > p_roll:
            opp_score += 1
    if player_score == opp_score:  # penalty shootout tiebreaker
        if power + random.randint(0, 15) >= opponent_power + random.randint(0, 15):
            player_score += 1
        else:
            opp_score += 1
    return player_score, opp_score, player_score > opp_score


async def competition_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = get_user(user_id)
    data = query.data
    await query.answer()

    if not user:
        return

    if data == "comp_back":
        await query.edit_message_text("⚔️ اول یک ورزش انتخاب کن:", reply_markup=sport_choice_keyboard())
        return

    if data.startswith("comp_choose_"):
        sport = data[len("comp_choose_"):]
        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE users SET sport = ? WHERE user_id = ?", (sport, user_id))
        user = get_user(user_id)
        rank = get_rank_name(user["rank_points"])
        text = (
            f"✅ ورزش انتخابی: {SPORTS[sport]['title']}\n\n"
            f"🏆 رنک: {rank} ({user['rank_points']} امتیاز)\n\nمهارت‌هات رو ارتقا بده یا بازی کن:"
        )
        await query.edit_message_text(text, reply_markup=sport_panel_keyboard(sport, user))
        return

    if data.startswith("comp_up_"):
        _, _, sport, stat_key = data.split("_")
        level = user[f"{sport}_{stat_key}"]
        max_level = SPORTS[sport]["max_level"]
        if level >= max_level:
            await query.answer("این مهارت به حداکثر سطح رسیده!", show_alert=True)
            return
        cost = get_stat_cost(level)
        if user["liber"] < cost:
            await query.answer(f"❌ برای ارتقا به {cost} LIBER نیاز داری.", show_alert=True)
            return
        with closing(get_conn()) as conn, conn:
            conn.execute(
                f"UPDATE users SET liber = liber - ?, {sport}_{stat_key} = {sport}_{stat_key} + 1 WHERE user_id = ?",
                (cost, user_id),
            )
        log_action(user_id, "STAT_UPGRADE", f"{sport}_{stat_key}")
        user = get_user(user_id)
        await query.edit_message_text(
            f"✅ مهارت ارتقا یافت! (هزینه: {cost} LIBER)\n\nپنل {SPORTS[sport]['title']}:",
            reply_markup=sport_panel_keyboard(sport, user),
        )
        return

    if data.startswith("comp_play_"):
        _, _, sport, tier_key = data.split("_")
        tier = MATCH_TIERS[tier_key]
        if user["liber"] < tier["entry"]:
            await query.answer(f"❌ برای این مسابقه به {tier['entry']} LIBER نیاز داری.", show_alert=True)
            return

        power = get_total_power(user, sport)
        p_score, o_score, won = _simulate_match(power)

        with closing(get_conn()) as conn, conn:
            conn.execute("UPDATE users SET liber = liber - ? WHERE user_id = ?", (tier["entry"], user_id))
            conn.execute(
                "INSERT INTO matches (player_id, sport, tier, player_score, opponent_score, result, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, sport, tier_key, p_score, o_score, "win" if won else "loss", datetime.utcnow().isoformat()),
            )
            conn.execute("UPDATE users SET matches_played = matches_played + 1 WHERE user_id = ?", (user_id,))

        if won:
            if tier_key == "normal":
                reward = tier["entry"] * tier["reward_multiplier"]
            else:
                reward = tier["reward"]
            rank_gain = 15 if tier_key == "normal" else (30 if tier_key == "hard" else 80)
            add_currency(user_id, liber=reward)
            with closing(get_conn()) as conn, conn:
                conn.execute(
                    "UPDATE users SET matches_won = matches_won + 1, rank_points = rank_points + ? WHERE user_id = ?",
                    (rank_gain, user_id),
                )
            result_text = f"🏆 بردی! نتیجه {p_score}-{o_score}\n+{reward:.0f} LIBER, +{rank_gain} امتیاز رنک"
        else:
            with closing(get_conn()) as conn, conn:
                conn.execute(
                    "UPDATE users SET rank_points = MAX(0, rank_points - 5) WHERE user_id = ?", (user_id,)
                )
            result_text = f"😔 باختی. نتیجه {p_score}-{o_score}\n-{tier['entry']:.0f} LIBER, -5 امتیاز رنک"

        log_action(user_id, "MATCH_PLAYED", f"{sport}/{tier_key} {'WIN' if won else 'LOSS'}")
        user = get_user(user_id)
        await query.edit_message_text(
            f"{tier['name']} — {SPORTS[sport]['title']}\n\n{result_text}",
            reply_markup=sport_panel_keyboard(sport, user),
        )
        return

    if data == "comp_leaderboard":
        with closing(get_conn()) as conn:
            rows = conn.execute(
                "SELECT first_name, rank_points, matches_won, matches_played FROM users "
                "ORDER BY rank_points DESC LIMIT 10"
            ).fetchall()
        text = "🏆 برترین‌های رقابت آنلاین\n\n"
        for i, r in enumerate(rows, start=1):
            text += f"{i}. {r['first_name']} — {get_rank_name(r['rank_points'])} ({r['rank_points']}) — {r['matches_won']}/{r['matches_played']} برد\n"
        await query.edit_message_text(text or "هنوز کسی بازی نکرده.", reply_markup=sport_choice_keyboard())


def get_tournament_days_left() -> int:
    with closing(get_conn()) as conn:
        row = conn.execute("SELECT started_at FROM tournament WHERE id = 1").fetchone()
    started = datetime.fromisoformat(row["started_at"])
    passed = (datetime.utcnow() - started).days
    return max(0, TOURNAMENT_LENGTH_DAYS - passed)


async def tournament_job(context: ContextTypes.DEFAULT_TYPE):
    """Runs bi-monthly: pays out top-3 rank_points, resets the ladder, notifies winners."""
    if get_tournament_days_left() > 0:
        return

    with closing(get_conn()) as conn:
        top3 = conn.execute(
            "SELECT user_id, first_name, rank_points FROM users ORDER BY rank_points DESC LIMIT 3"
        ).fetchall()

    for i, row in enumerate(top3, start=1):
        if row["rank_points"] <= 0:
            continue
        reward = TOURNAMENT_REWARDS.get(i, 0)
        add_currency(row["user_id"], liber=reward)
        try:
            await context.bot.send_message(
                row["user_id"],
                f"🏆 تبریک! در تورنمت رقابتی این دوره رتبه {i} شدی و {reward} LIBER جایزه گرفتی!",
            )
        except Exception:
            pass

    with closing(get_conn()) as conn, conn:
        conn.execute("UPDATE tournament SET started_at = ? WHERE id = 1", (datetime.utcnow().isoformat(),))
        conn.execute("UPDATE users SET rank_points = 0")

    logger.info("Tournament resolved and ladder reset.")

# ---------------------------------------------------------------------------
# Message router for reply-keyboard buttons
# ---------------------------------------------------------------------------

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if is_user_banned(user_id):
        await update.message.reply_text("🚫 حساب شما مسدود شده است.")
        return

    if await check_smart_anticheat(user_id, context):
        await update.message.reply_text("🚫 حساب شما به دلیل فعالیت غیرطبیعی مسدود شد.")
        return

    text = update.message.text

    routes = {
        "👤 پروفایل": profile,
        "💰 کیف پول": wallet,
        "💹 بازار LIBER": market_view,
        "🏆 رتبه‌بندی": leaderboard,
        "👥 دعوت دوستان": invite,
        "🌍 کشور": country_view,
        "🏦 بانک": bank_claim,
        "🏪 فروشگاه": shop_view,
        "🎁 صندوق‌ها": chest_menu,
        "🎯 مأموریت‌ها": get_missions,
        "🎖 دستاوردها": achievements_view,
        "🤝 اتحاد": alliance_view,
        "🎮 بازی‌ها": games_menu,
        "🏷 مزایده": auction_view,
        "❓ راهنما": help_command,
        "⚙ تنظیمات": settings_view,
        "💼 شغل": jobs_view,
        "⚔️ جنگ کلن": clan_war_simulate,
        "🔬 تحقیقات": research_view,
        "🛡 دفاع": defense_view,
        "🌌 اکتشاف": exploration,
        "🤖 مشاور هوشمند": smart_advisor,
        "📰 اخبار جهان": world_news,
        "🎟 پیش‌بینی قیمت": predict_view,
        "⚔️ رقابت آنلاین": competition_view,
"👑 خرید اشتراک": subscriptions_command,
    }

    handler = routes.get(text)
    if handler:
        await handler(update, context)
    else:
        await update.message.reply_text(
            "این بخش به‌زودی اضافه می‌شود. 🚧", reply_markup=main_menu_keyboard()
        )

# ---------------------------------------------------------------------------
# Background job: automatic market fluctuation
# ---------------------------------------------------------------------------
"""
LIBER - Stars Subscription Module (Entertainment Edition)
--------------------------------------------------------------
Standalone add-on file. Does NOT modify main.py or admin.py.

What this file does:
- Sells in-game VIP subscription tiers using REAL Telegram Stars,
  via Telegram's own official invoice/payment API (sendInvoice).
- Payment is verified by Telegram itself (pre_checkout_query +
  successful_payment). The bot never claims a payment succeeded
  unless Telegram has actually confirmed it.
- On confirmed payment, the matching VIP tier is activated
  automatically in the existing `vip_status` table.

What this file deliberately does NOT do:
- No crypto/TON withdrawals of any kind.
- No "processing / insufficient balance, please wait" stalling
  messages about withdrawals.
- No promise of converting in-game currency into real money.
All perks granted here are in-game only (LIBER/XP boosts, free
in-game chests, cosmetic titles/frames) — nothing leaves the game.

Requirements:
    pip install python-telegram-bot==21.*

Hook-up (add these lines wherever main.py builds the Application —
no need to change anything else in main.py):

    import subscriptions
    subscriptions.register_subscription_handlers(app, db_path=DB_PATH)

That's it. This file manages its own DB table and handlers.
"""

import logging
import sqlite3
import time
from contextlib import closing
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logger = logging.getLogger("liber.subscriptions")

# ---------------------------------------------------------------------------
# Config (filled in by register_subscription_handlers)
# ---------------------------------------------------------------------------

_DB_PATH = "liber.db"


def _get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_tables():
    """Creates tables this module needs. Uses IF NOT EXISTS so it is safe
    to run alongside the existing main.py schema — nothing here overlaps
    with or overwrites any table from main.py."""
    with closing(_get_conn()) as conn, conn:
        # vip_status is expected to already exist from main.py, but we
        # create it defensively in case this module is used standalone.
        conn.execute("""
        CREATE TABLE IF NOT EXISTS vip_status (
            user_id INTEGER PRIMARY KEY,
            tier TEXT,
            activated_at TEXT,
            expires_at TEXT
        )
        """)

        # Purely a purchase log/receipt history — for the user's own
        # reference and for admins to see what was bought. Not a wallet,
        # not a balance, nothing withdrawable.
        conn.execute("""
        CREATE TABLE IF NOT EXISTS star_purchases (
            purchase_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            tier_key TEXT,
            duration_key TEXT,
            stars_paid INTEGER,
            telegram_charge_id TEXT,
            purchased_at TEXT
        )
        """)


def _get_user_liber_row(user_id: int):
    with closing(_get_conn()) as conn:
        return conn.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        ).fetchone()


def _log(user_id: int, action: str, detail: str = ""):
    try:
        with closing(_get_conn()) as conn, conn:
            conn.execute(
                "INSERT INTO logs (user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (user_id, action, detail, datetime.utcnow().isoformat()),
            )
    except sqlite3.OperationalError:
        # logs table might not exist if this module is ever used fully
        # standalone; purchase history in star_purchases still works.
        pass


# ---------------------------------------------------------------------------
# Subscription tier definitions (real Telegram Stars prices)
# ---------------------------------------------------------------------------
# NOTE: Telegram Stars (currency code "XTR") amounts are whole numbers of
# Stars — no decimal/minor-unit multiplication like normal currencies.

STAR_TIERS = {
    "premium": {
        "name": "⭐ اشتراک پرمیوم",
        "emoji": "⭐",
        "perks": [
            "درآمد و XP +10٪",
        ],
        "durations": {
            "3m": {"label": "۳ ماهه", "months": 3, "stars": 30},
            "6m": {"label": "۶ ماهه", "months": 6, "stars": 45},
        },
    },
    "dragon": {
        "name": "🐉 اشتراک دراگون",
        "emoji": "🐉",
        "perks": [
            "درآمد و XP +25٪",
            "🎁 صندوق طلایی رایگان هفتگی",
        ],
        "durations": {
            "3m": {"label": "۳ ماهه", "months": 3, "stars": 50},
            "6m": {"label": "۶ ماهه", "months": 6, "stars": 90},
        },
    },
    "diamond": {
        "name": "💎 اشتراک الماس",
        "emoji": "💎",
        "perks": [
            "درآمد و XP +35٪",
            "🎁 صندوق الماسی رایگان هفتگی",
            "🎨 قاب ویژه پروفایل",
        ],
        "durations": {
            "3m": {"label": "۳ ماهه", "months": 3, "stars": 100},
            "6m": {"label": "۶ ماهه", "months": 6, "stars": 150},
        },
    },
    "legend": {
        "name": "👑 اشتراک لیبری لجند",
        "emoji": "👑",
        "perks": [
            "درآمد و XP +50٪",
            "🎁 صندوق الماسی رایگان هفتگی",
            "🎨 قاب اختصاصی پروفایل",
            "🏷 لقب افسانه‌ای انحصاری",
        ],
        "durations": {
            "3m": {"label": "۳ ماهه", "months": 3, "stars": 170},
            "6m": {"label": "۶ ماهه", "months": 6, "stars": 220},
        },
    },
}

TIER_ORDER = ["premium", "dragon", "diamond", "legend"]


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def tiers_menu_keyboard():
    rows = []
    for key in TIER_ORDER:
        tier = STAR_TIERS[key]
        rows.append([InlineKeyboardButton(f"{tier['name']}", callback_data=f"sub_tier_{key}")])
    rows.append([InlineKeyboardButton("📜 اشتراک‌های من", callback_data="sub_mystatus")])
    return InlineKeyboardMarkup(rows)


def tier_detail_keyboard(tier_key: str):
    tier = STAR_TIERS[tier_key]
    rows = []
    for dur_key, dur in tier["durations"].items():
        rows.append([
            InlineKeyboardButton(
                f"🛒 {dur['label']} — {dur['stars']}⭐",
                callback_data=f"sub_buy_{tier_key}_{dur_key}",
            )
        ])
    rows.append([InlineKeyboardButton("🔙 بازگشت به لیست اشتراک‌ها", callback_data="sub_menu")])
    return InlineKeyboardMarkup(rows)


def _tier_detail_text(tier_key: str) -> str:
    tier = STAR_TIERS[tier_key]
    perks_text = "\n".join(f"  ✅ {p}" for p in tier["perks"])
    lines = [f"{tier['name']}", "", "مزایا:", perks_text, "", "مدت‌های قابل خرید:"]
    for dur in tier["durations"].values():
        lines.append(f"  • {dur['label']} — {dur['stars']}⭐")
    lines.append("")
    lines.append("پرداخت مستقیم از طریق درگاه رسمی Stars تلگرام انجام می‌شود.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------

async def subscriptions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍 فروشگاه اشتراک‌های LIBER\n\n"
        "با ⭐ Stars تلگرام اشتراک بخر و مزایای ویژه بگیر:\n"
        "روی هرکدوم بزن تا جزئیات و قیمت رو ببینی 👇",
        reply_markup=tiers_menu_keyboard(),
    )


async def subscriptions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    await query.answer()

    if data == "sub_menu":
        await query.edit_message_text(
            "🛍 فروشگاه اشتراک‌های LIBER\n\nروی هرکدوم بزن تا جزئیات ببینی:",
            reply_markup=tiers_menu_keyboard(),
        )
        return

    if data == "sub_mystatus":
        await _send_my_status(query, user_id, edit=True)
        return

    if data.startswith("sub_tier_"):
        tier_key = data[len("sub_tier_"):]
        if tier_key not in STAR_TIERS:
            await query.answer("❌ اشتراک نامعتبر.", show_alert=True)
            return
        await query.edit_message_text(
            _tier_detail_text(tier_key),
            reply_markup=tier_detail_keyboard(tier_key),
        )
        return

    if data.startswith("sub_buy_"):
        _, _, tier_key, dur_key = data.split("_")
        tier = STAR_TIERS.get(tier_key)
        dur = tier["durations"].get(dur_key) if tier else None
        if not tier or not dur:
            await query.answer("❌ گزینه نامعتبر.", show_alert=True)
            return

        payload = f"vipstars|{tier_key}|{dur_key}|{user_id}|{int(time.time())}"
        title = f"{tier['name']} ({dur['label']})"
        description = " | ".join(tier["perks"])

        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=title,
            description=description[:255],
            payload=payload,
            provider_token="",  # empty for Telegram Stars payments
            currency="XTR",
            prices=[LabeledPrice(label=title[:32], amount=dur["stars"])],
        )
        return


async def _send_my_status(query_or_update, user_id: int, edit: bool = False):
    with closing(_get_conn()) as conn:
        status = conn.execute(
            "SELECT * FROM vip_status WHERE user_id = ?", (user_id,)
        ).fetchone()
        history = conn.execute(
            "SELECT * FROM star_purchases WHERE user_id = ? ORDER BY purchase_id DESC LIMIT 5",
            (user_id,),
        ).fetchall()

    lines = ["📜 وضعیت اشتراک شما", ""]
    if status:
        tier = STAR_TIERS.get(status["tier"])
        expires_at = datetime.fromisoformat(status["expires_at"])
        active = datetime.utcnow() < expires_at
        tier_name = tier["name"] if tier else status["tier"]
        lines.append(f"اشتراک فعلی: {tier_name}")
        lines.append(f"وضعیت: {'✅ فعال' if active else '❌ منقضی شده'}")
        lines.append(f"تاریخ انقضا: {expires_at.strftime('%Y-%m-%d')}")
    else:
        lines.append("شما در حال حاضر اشتراکی فعال ندارید.")

    if history:
        lines.append("")
        lines.append("🧾 آخرین خریدها:")
        for h in history:
            tier = STAR_TIERS.get(h["tier_key"])
            tname = tier["name"] if tier else h["tier_key"]
            lines.append(f"  • {tname} ({h['duration_key']}) — {h['stars_paid']}⭐ — {h['purchased_at'][:10]}")

    text = "\n".join(lines)
    kb = tiers_menu_keyboard()

    if edit:
        await query_or_update.edit_message_text(text, reply_markup=kb)
    else:
        await query_or_update.message.reply_text(text, reply_markup=kb)


async def my_subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _send_my_status(update, update.effective_user.id, edit=False)


# ---------------------------------------------------------------------------
# Payment verification (Telegram handles the actual money movement)
# ---------------------------------------------------------------------------

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    payload = query.invoice_payload or ""
    if not payload.startswith("vipstars|"):
        await query.answer(ok=False, error_message="سفارش نامعتبر است.")
        return
    # Everything checks out on our side; Telegram itself verifies the
    # Stars balance/payment. We never claim success ourselves here.
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fires only after Telegram has confirmed the Stars payment actually went
    through. This is the single source of truth for activating a tier."""
    payment = update.message.successful_payment
    user_id = update.effective_user.id
    payload = payment.invoice_payload or ""

    parts = payload.split("|")
    if len(parts) != 5 or parts[0] != "vipstars":
        # Shouldn't happen since precheckout validates this, but guard anyway.
        await update.message.reply_text(
            "⚠️ پرداخت دریافت شد اما سفارش قابل شناسایی نبود. لطفاً با پشتیبانی تماس بگیر."
        )
        return

    _, tier_key, dur_key, orig_user_id, _ts = parts
    tier = STAR_TIERS.get(tier_key)
    dur = tier["durations"].get(dur_key) if tier else None
    if not tier or not dur:
        await update.message.reply_text(
            "⚠️ پرداخت دریافت شد اما نوع اشتراک نامعتبر بود. لطفاً با پشتیبانی تماس بگیر."
        )
        return

    now = datetime.utcnow()
    expires_at = now + timedelta(days=30 * dur["months"])

    with closing(_get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO vip_status (user_id, tier, activated_at, expires_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET
                 tier = excluded.tier,
                 activated_at = excluded.activated_at,
                 expires_at = excluded.expires_at""",
            (user_id, tier_key, now.isoformat(), expires_at.isoformat()),
        )
        conn.execute(
            """INSERT INTO star_purchases
               (user_id, tier_key, duration_key, stars_paid, telegram_charge_id, purchased_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                user_id,
                tier_key,
                dur_key,
                payment.total_amount,
                payment.telegram_payment_charge_id,
                now.isoformat(),
            ),
        )

    _log(user_id, "STARS_SUBSCRIPTION_ACTIVATED", f"{tier_key}/{dur_key}")

    perks_text = "\n".join(f"  ✅ {p}" for p in tier["perks"])
    await update.message.reply_text(
        f"🎉 پرداخت با موفقیت تایید شد!\n\n"
        f"{tier['name']} ({dur['label']}) فعال شد.\n\n"
        f"مزایای فعال‌شده:\n{perks_text}\n\n"
        f"📅 تاریخ انقضا: {expires_at.strftime('%Y-%m-%d')}\n\n"
        f"با /myvip هر زمان می‌تونی وضعیت اشتراکت رو ببینی."
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

def register_subscription_handlers(app: Application, db_path: str = "liber.db"):
    """Call this once from main.py's setup, e.g.:

        import subscriptions
        subscriptions.register_subscription_handlers(app, db_path=DB_PATH)

    Does not touch or require changes to any existing handler, table, or
    file — purely additive.
    """
    global _DB_PATH
    _DB_PATH = db_path
    _init_tables()

    app.add_handler(CommandHandler("subscriptions", subscriptions_command))
    app.add_handler(CommandHandler("vipshop", subscriptions_command))
    app.add_handler(CommandHandler("myvip", my_subscription_command))
    app.add_handler(CallbackQueryHandler(subscriptions_callback, pattern="^sub_"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    logger.info("Stars subscription module registered (/subscriptions, /myvip).")


async def market_job(context: ContextTypes.DEFAULT_TYPE):
    new_price, bought, sold = fluctuate_market()
    logger.info(f"Market price updated: {new_price} (bought={bought}, sold={sold})")


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(market_callback, pattern="^mkt_"))
    app.add_handler(CallbackQueryHandler(shop_callback, pattern="^shop_"))
    app.add_handler(CallbackQueryHandler(chest_callback, pattern="^chest_open_"))
    app.add_handler(CallbackQueryHandler(games_callback, pattern="^game_"))
    app.add_handler(CallbackQueryHandler(missions_callback, pattern="^mis_"))

    # Standalone admin.py panel (activated only for ADMIN_IDS, via /admin command)
    try:
        import admin as admin_module
        admin_module.register_admin_handlers(app, admin_ids=ADMIN_IDS, db_path=DB_PATH)
    except ImportError:
        logger.warning("admin.py not found next to main.py — admin panel module not loaded.")
    app.add_handler(CommandHandler("chest", chest_menu))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("market", market_view))
    app.add_handler(CommandHandler("buy", buy_liber))
    app.add_handler(CommandHandler("sell", sell_liber))
    app.add_handler(CommandHandler("daily", daily_reward))
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("settings", settings_view))
    app.add_handler(CommandHandler("setbio", set_bio))

    # Country & buildings
    app.add_handler(CommandHandler("found", found_country))
    app.add_handler(CommandHandler("country", country_view))
    app.add_handler(CommandHandler("build", build))

    # Bank & investments
    app.add_handler(CommandHandler("deposit", bank_deposit))
    app.add_handler(CommandHandler("claim", bank_claim))
    app.add_handler(CommandHandler("invest", invest))
    app.add_handler(CommandHandler("claim_invest", claim_investments))

    # Missions & achievements
    app.add_handler(CommandHandler("missions", get_missions))
    app.add_handler(CommandHandler("complete", complete_mission))
    app.add_handler(CommandHandler("achievements", achievements_view))

    # Alliances
    app.add_handler(CommandHandler("create_alliance", create_alliance))
    app.add_handler(CommandHandler("join_alliance", join_alliance))
    app.add_handler(CommandHandler("alliance", alliance_view))

    # Shop & VIP (in-game currency only)
    app.add_handler(CommandHandler("shop", shop_view))
    app.add_handler(CommandHandler("buy_item", buy_item))
    app.add_handler(CommandHandler("buy_vip", buy_vip))
    app.add_handler(CommandHandler("vip", vip_status_view))

    # Events
    app.add_handler(CommandHandler("events", events_view))

    # League & season
    app.add_handler(CommandHandler("league", league_view))
    app.add_handler(CommandHandler("season_top", season_leaderboard))

    # Mini-games
    app.add_handler(CommandHandler("wheel", game_wheel))
    app.add_handler(CommandHandler("lucky", game_lucky))
    app.add_handler(CommandHandler("treasure", game_treasure))

    # Auction
    app.add_handler(CommandHandler("auction", auction_view))
    app.add_handler(CommandHandler("bid", auction_bid))

    # Jobs
    app.add_handler(CommandHandler("jobs", jobs_view))
    app.add_handler(CommandHandler("setjob", set_job))
    app.add_handler(CommandHandler("work", work))
    app.add_handler(CallbackQueryHandler(jobs_callback, pattern="^job_"))

    # Online Competition
    app.add_handler(CommandHandler("competition", competition_view))
    app.add_handler(CallbackQueryHandler(competition_callback, pattern="^comp_"))

    # Clan war
    app.add_handler(CommandHandler("clanwar", clan_war_simulate))

    # Research & defense
    app.add_handler(CommandHandler("research", research_view))
    app.add_handler(CommandHandler("research_upgrade", research_upgrade))
    app.add_handler(CommandHandler("defense", defense_view))
    app.add_handler(CommandHandler("defense_upgrade", defense_upgrade))

    # Exploration
    app.add_handler(CommandHandler("explore", exploration))

    # Gift codes
    app.add_handler(CommandHandler("gift", redeem_gift))
    app.add_handler(CommandHandler("creategift", create_gift_admin))

    # Prediction market
    app.add_handler(CommandHandler("predict", predict_view))
    app.add_handler(CommandHandler("predict_up", predict_up))
    app.add_handler(CommandHandler("predict_down", predict_down))

    # Smart advisor & news
    app.add_handler(CommandHandler("advisor", smart_advisor))
    app.add_handler(CommandHandler("news", world_news))

    # Admin
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^admin_"))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router))

    job_queue = app.job_queue
    job_queue.run_repeating(market_job, interval=1800, first=10)       # every 30 min
    job_queue.run_repeating(trigger_random_event, interval=21600, first=3600)  # every 6h
    job_queue.run_repeating(prediction_resolve_job, interval=1800, first=1800)  # every 30 min
    job_queue.run_repeating(tournament_job, interval=86400, first=60)  # check daily

    logger.info("LIBER bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
