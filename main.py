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

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
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
