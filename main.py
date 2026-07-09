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

BOT_TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"
DB_PATH = "liber.db"
ADMIN_IDS = [6188951798]  # admins who can access the admin panel
REQUIRED_CHANNEL = "@Libercoin1"  # set to None to disable mandatory join check

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

        # seed market price if empty
        row = conn.execute("SELECT COUNT(*) as c FROM market").fetchone()
        if row["c"] == 0:
            conn.execute(
                "INSERT INTO market (price, updated_at) VALUES (?, ?)",
                (10.0, datetime.utcnow().isoformat()),
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


def fluctuate_market():
    """Randomly changes the LIBER virtual market price. For entertainment only."""
    current = get_market_price()
    change_pct = random.uniform(-0.05, 0.05)  # +/-5%
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
    return new_price


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
        ["👥 دعوت دوستان", "❓ راهنما"],
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

        welcome_text = (
            f"🌍 به دنیای LIBER خوش اومدی {user.first_name}!\n\n"
            "این یک بازی شبیه‌سازی اقتصادی سرگرمی است.\n"
            "با ساختن کشور، پیشرفت در بازار، و رقابت با دیگران XP و امتیاز کسب کن.\n\n"
            "⚠️ توجه: تمام ارزهای این بازی (LIBER, Coin, Energy) کاملاً مجازی هستند "
            "و صرفاً برای سرگرمی و رقابت درون‌بازی استفاده می‌شوند."
        )
    else:
        welcome_text = f"👋 خوش برگشتی {user.first_name}!"

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
        "این قیمت صرفاً بخشی از شبیه‌سازی بازی است و ارزش واقعی ندارد."
    )
    await update.message.reply_text(text)


async def buy_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy virtual LIBER using virtual Coin (in-game only)."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /buy مقدار_کوین")
        return

    try:
        amount_coin = float(context.args[0])
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کن.")
        return

    if amount_coin <= 0 or amount_coin > user["coin"]:
        await update.message.reply_text("موجودی Coin کافی نیست.")
        return

    price = get_market_price()
    liber_amount = round(amount_coin / price, 4)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET coin = coin - ?, liber = liber + ? WHERE user_id = ?",
            (amount_coin, liber_amount, user_id),
        )

    log_action(user_id, "MARKET_BUY", f"coin={amount_coin} liber={liber_amount}")
    await update.message.reply_text(
        f"✅ خرید موفق: {liber_amount:.4f} LIBER دریافت شد (قیمت: {price:.4f})"
    )


async def sell_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sell virtual LIBER back to virtual Coin (in-game only)."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /sell مقدار_لیبر")
        return

    try:
        amount_liber = float(context.args[0])
    except ValueError:
        await update.message.reply_text("لطفاً یک عدد معتبر وارد کن.")
        return

    if amount_liber <= 0 or amount_liber > user["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    price = get_market_price()
    coin_amount = round(amount_liber * price, 4)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, coin = coin + ? WHERE user_id = ?",
            (amount_liber, coin_amount, user_id),
        )

    log_action(user_id, "MARKET_SELL", f"liber={amount_liber} coin={coin_amount}")
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

    reward_liber = random.randint(20, 100)
    reward_energy = random.randint(5, 20)

    add_currency(user_id, liber=reward_liber, energy=reward_energy)
    add_xp(user_id, 10)
    update_user_field(user_id, "last_daily", now.isoformat())

    await update.message.reply_text(
        f"🎁 جایزه روزانه دریافت شد!\n+{reward_liber} LIBER\n+{reward_energy} Energy\n+10 XP"
    )
    log_action(user_id, "DAILY_REWARD", f"liber={reward_liber} energy={reward_energy}")


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
        f"جایزه هر دعوت: 50 LIBER (مجازی)"
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


async def get_missions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    with closing(get_conn()) as conn:
        existing = conn.execute(
            "SELECT * FROM missions WHERE user_id = ? AND completed = 0",
            (user_id,),
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
                "SELECT * FROM missions WHERE user_id = ? AND completed = 0",
                (user_id,),
            ).fetchall()

    text = "🎯 مأموریت‌های فعال\n\n"
    for m in existing:
        text += f"#{m['mission_id']} — {m['description']} (+{m['reward_liber']} LIBER, +{m['reward_xp']} XP)\n"
    text += "\nبرای تکمیل: /complete شماره_مأموریت"

    await update.message.reply_text(text)


async def complete_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text("استفاده: /complete شماره_مأموریت")
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
    "silver": {"name": "⭐ VIP نقره‌ای", "cost_liber": 1000, "duration_days": 7},
    "gold": {"name": "🥇 VIP طلایی", "cost_liber": 2500, "duration_days": 7},
    "diamond": {"name": "💎 VIP الماسی", "cost_liber": 5000, "duration_days": 7},
}


async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏪 فروشگاه (پرداخت با LIBER داخل‌بازی)\n\n"
    for key, item in SHOP_ITEMS.items():
        text += f"{item['name']} — {item['cost']} LIBER — /buy_item {key}\n"

    text += "\n⭐ VIP (فقط با LIBER داخل‌بازی، بدون پرداخت واقعی):\n"
    for key, tier in VIP_TIERS.items():
        text += f"{tier['name']} — {tier['cost_liber']} LIBER / {tier['duration_days']} روز — /buy_vip {key}\n"

    await update.message.reply_text(text)


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


async def league_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
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

    await update.message.reply_text(text)


async def season_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("هنوز امتیازی در این فصل ثبت نشده.")
        return

    text = f"🏆 برترین‌های {season['name']}\n\n"
    for i, r in enumerate(rows, start=1):
        text += f"{i}. {r['first_name']} — {LEAGUE_NAMES[r['league']]} ({r['points']} امتیاز)\n"

    await update.message.reply_text(text)


# ---------------------------------------------------------------------------
# Mini-Games (entertainment only — virtual LIBER wagers, no cash out)
# ---------------------------------------------------------------------------

async def game_wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Spin the wheel: bet virtual LIBER, win a random multiplier."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /wheel مقدار_شرط")
        return

    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return

    if bet <= 0 or bet > user["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    outcomes = [0, 0.5, 1, 1.5, 2, 3, 5]
    weights = [25, 20, 20, 15, 10, 7, 3]
    multiplier = random.choices(outcomes, weights=weights, k=1)[0]
    result = round(bet * multiplier, 2)
    net = result - bet

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? + ? WHERE user_id = ?",
            (bet, result, user_id),
        )
        conn.execute(
            """INSERT INTO game_history (user_id, game_type, bet, result, played_at)
               VALUES (?, 'wheel', ?, ?, ?)""",
            (user_id, bet, result, datetime.utcnow().isoformat()),
        )

    add_season_points(user_id, max(0, int(net)))
    log_action(user_id, "GAME_WHEEL", f"bet={bet} multiplier={multiplier}")

    emoji = "🎉" if multiplier >= 1 else "😔"
    await update.message.reply_text(
        f"🎰 گردونه چرخید!\nضریب: x{multiplier}\nنتیجه: {result:.2f} LIBER {emoji}"
    )


async def game_lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple 50/50-ish coin flip style game with in-game LIBER."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

    if not context.args:
        await update.message.reply_text("استفاده: /lucky مقدار_شرط")
        return

    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return

    if bet <= 0 or bet > user["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    win = random.random() < 0.45  # slightly under 50% for house balance
    result = bet * 2 if win else 0

    with closing(get_conn()) as conn, conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? + ? WHERE user_id = ?",
            (bet, result, user_id),
        )
        conn.execute(
            """INSERT INTO game_history (user_id, game_type, bet, result, played_at)
               VALUES (?, 'lucky', ?, ?, ?)""",
            (user_id, bet, result, datetime.utcnow().isoformat()),
        )

    log_action(user_id, "GAME_LUCKY", f"bet={bet} win={win}")

    if win:
        await update.message.reply_text(f"🍀 بردی! +{result:.2f} LIBER")
    else:
        await update.message.reply_text(f"❌ باختی. -{bet:.2f} LIBER")


async def game_treasure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Free daily treasure hunt — small random virtual reward, no bet required."""
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        await update.message.reply_text("ابتدا با /start ثبت‌نام کن.")
        return

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
            await update.message.reply_text(f"⏳ گنج بعدی تا {mins} دقیقه دیگر آماده می‌شود.")
            return

    reward = random.randint(10, 60)
    add_currency(user_id, liber=reward)

    with closing(get_conn()) as conn, conn:
        conn.execute(
            """INSERT INTO chest_cooldowns (user_id, last_chest) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET last_chest = excluded.last_chest""",
            (user_id, now.isoformat()),
        )

    log_action(user_id, "GAME_TREASURE", f"reward={reward}")
    await update.message.reply_text(f"🎁 گنج پیدا شد! +{reward} LIBER")


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


async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🎮 بازی‌ها (سرگرمی - LIBER داخل‌بازی)\n\n"
        "🎰 /wheel مقدار — گردونه شانس\n"
        "🍀 /lucky مقدار — شیر یا خط\n"
        "🎁 /treasure — گنج رایگان (هر ۶ ساعت)\n"
        "📦 /chest نوع — صندوق‌ها (free, bronze, silver, gold, diamond)\n"
        "🏆 /league — وضعیت لیگ فصلی\n"
        "📊 /season_top — رتبه‌بندی فصل"
    )
    await update.message.reply_text(text)


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
# Message router for reply-keyboard buttons
# ---------------------------------------------------------------------------

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "🎯 مأموریت‌ها": get_missions,
        "🎖 دستاوردها": achievements_view,
        "🤝 اتحاد": alliance_view,
        "🎮 بازی‌ها": games_menu,
        "🏷 مزایده": auction_view,
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

async def market_job(context: ContextTypes.DEFAULT_TYPE):
    new_price = fluctuate_market()
    logger.info(f"Market price updated: {new_price}")


# ---------------------------------------------------------------------------
# Application setup
# ---------------------------------------------------------------------------

def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("wallet", wallet))
    app.add_handler(CommandHandler("market", market_view))
    app.add_handler(CommandHandler("buy", buy_liber))
    app.add_handler(CommandHandler("sell", sell_liber))
    app.add_handler(CommandHandler("daily", daily_reward))
    app.add_handler(CommandHandler("top", leaderboard))
    app.add_handler(CommandHandler("invite", invite))

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
    app.add_handler(CommandHandler("chest", open_chest))

    # Auction
    app.add_handler(CommandHandler("auction", auction_view))
    app.add_handler(CommandHandler("bid", auction_bid))

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

    logger.info("LIBER bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
