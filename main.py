import sqlite3
import logging
import random
import time
import json
from datetime import datetime, timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("LIBER")

# ============================================================
#                       تنظیمات کلی
# ============================================================

BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"
ADMIN_IDS = [123456789]

FORCE_JOIN_CHANNELS = [
    {"id": "@Libercoin1", "title": "کانال LIBER", "url": "https://t.me/Libercoin1"},
    # همینجا یک آیتم دیگر اضافه کن، اگر کانال یا گروه دیگری داری:
    # {"id": "@your_channel_2", "title": "کانال دوم", "url": "https://t.me/your_channel_2"},
]

DB_PATH = "liber.db"

MARKET_BASE_PRICE = 100
BUY_FEE_PERCENT = 2
SELL_FEE_PERCENT = 2
MARKET_FLUCTUATION_RANGE = (-0.07, 0.07)          # هر ساعت
MARKET_UPDATE_INTERVAL_SECONDS = 3600             # هر ۱ ساعت

BANK_INTEREST_PERCENT = 1.5     # سود روزانه سپرده
LOAN_INTEREST_PERCENT = 5       # کارمزد وام
MAX_LOAN_MULTIPLIER = 3         # سقف وام بر اساس سطح

XP_PER_LEVEL = 100
DAILY_MISSION_XP = 20
DAILY_MISSION_LIBER = 8

FREE_CHEST_COOLDOWN_HOURS = 8
WHEEL_COOLDOWN_HOURS = 24
AUCTION_DURATION_MINUTES = 60
CLAN_CREATE_COST_DIAMOND = 30

CHEST_TABLE = {
    "free":    {"cost": {}, "rewards": [("coin", 40, 120), ("liber", 1, 3)]},
    "bronze":  {"cost": {"coin": 350}, "rewards": [("coin", 90, 350), ("liber", 2, 7), ("xp", 8, 18)]},
    "silver":  {"cost": {"coin": 900}, "rewards": [("liber", 6, 20), ("diamond", 1, 2), ("xp", 15, 35)]},
    "gold":    {"cost": {"liber": 130}, "rewards": [("liber", 18, 55), ("diamond", 2, 4), ("medal", 1, 2)]},
    "diamond": {"cost": {"diamond": 25}, "rewards": [("liber", 50, 140), ("diamond", 4, 8), ("medal", 1, 4)]},
}

VIP_TIERS = {
    "silver":  {"cost_diamond": 50,   "xp_bonus": 1.1,  "income_bonus": 1.1},
    "gold":    {"cost_diamond": 150,  "xp_bonus": 1.25, "income_bonus": 1.25},
    "diamond": {"cost_diamond": 400,  "xp_bonus": 1.5,  "income_bonus": 1.5},
    "titan":   {"cost_diamond": 1000, "xp_bonus": 2.0,  "income_bonus": 2.0},
}

# چرخ شانس: (عنوان, نوع پاداش, حداقل, حداکثر, وزن شانس)
WHEEL_PRIZES = [
    ("۵۰ سکه",        "coin",    50, 50,   30),
    ("۱۵۰ سکه",       "coin",    150, 150, 20),
    ("۲ لیبر",        "liber",   2, 2,     20),
    ("۵ لیبر",        "liber",   5, 5,     12),
    ("۱ الماس",       "diamond", 1, 1,     10),
    ("۳ الماس",       "diamond", 3, 3,     5),
    ("جک‌پات! ۱۰ الماس", "diamond", 10, 10, 3),
]

LEAGUE_THRESHOLDS = [
    (0, "مبتدی"), (500, "برنزی"), (1500, "نقره‌ای"),
    (4000, "طلایی"), (10000, "الماسی"), (25000, "افسانه‌ای"),
]

# ============================================================
#                        پایگاه داده
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        coin INTEGER DEFAULT 200,
        liber REAL DEFAULT 0,
        diamond INTEGER DEFAULT 0,
        xp INTEGER DEFAULT 0,
        bank_balance INTEGER DEFAULT 0,
        loan_balance INTEGER DEFAULT 0,
        vip_tier TEXT DEFAULT '',
        vip_until TEXT DEFAULT '',
        ref_by INTEGER DEFAULT 0,
        referral_count INTEGER DEFAULT 0,
        clan_id INTEGER DEFAULT 0,
        banned INTEGER DEFAULT 0,
        last_free_chest TEXT DEFAULT '',
        last_wheel TEXT DEFAULT '',
        joined_at TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS market (id INTEGER PRIMARY KEY, price REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS gift_codes (
        code TEXT PRIMARY KEY, field TEXT, amount REAL,
        max_uses INTEGER, used_count INTEGER DEFAULT 0, created_by INTEGER
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS gift_redemptions (
        code TEXT, user_id INTEGER, PRIMARY KEY (code, user_id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS withdrawals (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount REAL,
        ton_address TEXT, status TEXT DEFAULT 'pending', created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS clans (
        id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE,
        owner_id INTEGER, bank_coin INTEGER DEFAULT 0, created_at TEXT
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, seller_id INTEGER,
        item_field TEXT, item_amount REAL, min_bid INTEGER,
        current_bid INTEGER DEFAULT 0, current_bidder INTEGER DEFAULT 0,
        end_time TEXT, status TEXT DEFAULT 'open'
    )""")
    c.execute("SELECT COUNT(*) AS n FROM market")
    if c.fetchone()["n"] == 0:
        c.execute("INSERT INTO market (id, price) VALUES (1, ?)", (MARKET_BASE_PRICE,))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = db()
    row = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    return row


def ensure_user(tg_user, ref_by=0):
    conn = db()
    row = conn.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,)).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO users (user_id, username, first_name, ref_by, joined_at) VALUES (?, ?, ?, ?, ?)",
            (tg_user.id, tg_user.username or "", tg_user.first_name or "", ref_by, datetime.now().isoformat()),
        )
        if ref_by and ref_by != tg_user.id:
            conn.execute("UPDATE users SET referral_count = referral_count + 1, coin = coin + 100 WHERE user_id=?", (ref_by,))
        conn.commit()
    conn.close()


def set_field(user_id, field, value):
    conn = db()
    conn.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()


def add_currency(user_id, field, amount):
    conn = db()
    conn.execute(f"UPDATE users SET {field} = {field} + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def add_xp(user_id, amount):
    u = get_user(user_id)
    vip = u["vip_tier"]
    bonus = VIP_TIERS.get(vip, {}).get("xp_bonus", 1.0)
    add_currency(user_id, "xp", int(amount * bonus))


def get_league_name(xp_total):
    name = LEAGUE_THRESHOLDS[0][1]
    for threshold, league_name in LEAGUE_THRESHOLDS:
        if xp_total >= threshold:
            name = league_name
    return name


def is_banned(user_id):
    u = get_user(user_id)
    return bool(u and u["banned"])


# ============================================================
#                          بازار
# ============================================================

def get_market_price():
    conn = db()
    row = conn.execute("SELECT price FROM market WHERE id=1").fetchone()
    conn.close()
    return row["price"]


def set_market_price(price):
    conn = db()
    conn.execute("UPDATE market SET price=? WHERE id=1", (price,))
    conn.commit()
    conn.close()


async def hourly_market_job(context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    change = random.uniform(*MARKET_FLUCTUATION_RANGE)
    new_price = max(10, price * (1 + change))
    set_market_price(round(new_price, 2))


def buy_liber(user_id, coin_amount):
    u = get_user(user_id)
    if u["coin"] < coin_amount:
        return False, "سکه کافی نداری."
    price = get_market_price()
    fee = coin_amount * BUY_FEE_PERCENT / 100
    liber_bought = (coin_amount - fee) / price
    add_currency(user_id, "coin", -coin_amount)
    add_currency(user_id, "liber", liber_bought)
    return True, liber_bought


def sell_liber(user_id, liber_amount):
    u = get_user(user_id)
    if u["liber"] < liber_amount:
        return False, "لیبر کافی نداری."
    price = get_market_price()
    coin_gained = liber_amount * price
    fee = coin_gained * SELL_FEE_PERCENT / 100
    coin_gained -= fee
    add_currency(user_id, "liber", -liber_amount)
    add_currency(user_id, "coin", coin_gained)
    return True, coin_gained


# ============================================================
#                       بانک و وام
# ============================================================

async def daily_bank_interest_job(context: ContextTypes.DEFAULT_TYPE):
    conn = db()
    rows = conn.execute("SELECT user_id, bank_balance FROM users WHERE bank_balance > 0").fetchall()
    for r in rows:
        interest = r["bank_balance"] * BANK_INTEREST_PERCENT / 100
        conn.execute("UPDATE users SET bank_balance = bank_balance + ? WHERE user_id=?", (interest, r["user_id"]))
    conn.commit()
    conn.close()


def bank_deposit(user_id, amount):
    u = get_user(user_id)
    if u["coin"] < amount:
        return False
    add_currency(user_id, "coin", -amount)
    add_currency(user_id, "bank_balance", amount)
    return True


def bank_withdraw(user_id, amount):
    u = get_user(user_id)
    if u["bank_balance"] < amount:
        return False
    add_currency(user_id, "bank_balance", -amount)
    add_currency(user_id, "coin", amount)
    return True


def take_loan(user_id, amount):
    u = get_user(user_id)
    level = u["xp"] // XP_PER_LEVEL + 1
    max_loan = level * 200 * MAX_LOAN_MULTIPLIER
    if u["loan_balance"] > 0:
        return False, "ابتدا وام قبلی را تسویه کن."
    if amount > max_loan:
        return False, f"سقف وام تو {max_loan} سکه است."
    add_currency(user_id, "coin", amount)
    add_currency(user_id, "loan_balance", amount * (1 + LOAN_INTEREST_PERCENT / 100))
    return True, amount


def repay_loan(user_id, amount):
    u = get_user(user_id)
    if u["loan_balance"] <= 0:
        return False, "وامی نداری."
    if u["coin"] < amount:
        return False, "سکه کافی نداری."
    pay = min(amount, u["loan_balance"])
    add_currency(user_id, "coin", -pay)
    add_currency(user_id, "loan_balance", -pay)
    return True, pay


# ============================================================
#                          صندوق‌ها
# ============================================================

def open_chest(user_id, chest_key):
    chest = CHEST_TABLE.get(chest_key)
    if not chest:
        return False, "صندوق نامعتبر."
    u = get_user(user_id)

    if chest_key == "free":
        if u["last_free_chest"]:
            last = datetime.fromisoformat(u["last_free_chest"])
            if datetime.now() - last < timedelta(hours=FREE_CHEST_COOLDOWN_HOURS):
                remain = timedelta(hours=FREE_CHEST_COOLDOWN_HOURS) - (datetime.now() - last)
                return False, f"صندوق رایگان تا {int(remain.seconds/3600)} ساعت دیگر آماده می‌شود."
        set_field(user_id, "last_free_chest", datetime.now().isoformat())
    else:
        for field, cost in chest["cost"].items():
            if u[field] < cost:
                return False, "موجودی کافی برای باز کردن این صندوق نداری."
        for field, cost in chest["cost"].items():
            add_currency(user_id, field, -cost)

    results = []
    for field, lo, hi in chest["rewards"]:
        amount = random.randint(lo, hi) if isinstance(lo, int) else round(random.uniform(lo, hi), 2)
        if field == "xp":
            add_xp(user_id, amount)
        elif field == "medal":
            pass  # می‌توان بعدا جدول مدال جدا اضافه کرد
        else:
            add_currency(user_id, field, amount)
        results.append((field, amount))
    return True, results


# ============================================================
#                       چرخ شانس (جدید)
# ============================================================

def spin_wheel(user_id):
    u = get_user(user_id)
    if u["last_wheel"]:
        last = datetime.fromisoformat(u["last_wheel"])
        if datetime.now() - last < timedelta(hours=WHEEL_COOLDOWN_HOURS):
            remain = timedelta(hours=WHEEL_COOLDOWN_HOURS) - (datetime.now() - last)
            hours = int(remain.total_seconds() // 3600)
            return False, f"چرخ‌شانس تا {hours} ساعت دیگر آماده می‌شود."

    weights = [p[4] for p in WHEEL_PRIZES]
    choice = random.choices(WHEEL_PRIZES, weights=weights, k=1)[0]
    title, field, lo, hi, _ = choice
    amount = random.randint(lo, hi)
    add_currency(user_id, field, amount)
    set_field(user_id, "last_wheel", datetime.now().isoformat())
    return True, title


# ============================================================
#                        مزایده (جدید)
# ============================================================

def create_auction(seller_id, item_field, item_amount, min_bid):
    u = get_user(seller_id)
    if u[item_field] < item_amount:
        return False, "موجودی کافی نداری."
    add_currency(seller_id, item_field, -item_amount)
    end_time = (datetime.now() + timedelta(minutes=AUCTION_DURATION_MINUTES)).isoformat()
    conn = db()
    conn.execute(
        "INSERT INTO auctions (seller_id, item_field, item_amount, min_bid, end_time) VALUES (?, ?, ?, ?, ?)",
        (seller_id, item_field, item_amount, min_bid, end_time),
    )
    conn.commit()
    conn.close()
    return True, "مزایده ثبت شد."


def list_open_auctions():
    resolve_expired_auctions()
    conn = db()
    rows = conn.execute("SELECT * FROM auctions WHERE status='open' ORDER BY id DESC LIMIT 15").fetchall()
    conn.close()
    return rows


def place_bid(auction_id, bidder_id, bid_amount):
    conn = db()
    row = conn.execute("SELECT * FROM auctions WHERE id=? AND status='open'", (auction_id,)).fetchone()
    if not row:
        conn.close()
        return False, "این مزایده دیگر باز نیست."
    if bid_amount <= row["current_bid"] or bid_amount < row["min_bid"]:
        conn.close()
        return False, "پیشنهاد باید بیشتر از پیشنهاد فعلی و حداقل قیمت باشد."
    bidder = get_user(bidder_id)
    if bidder["coin"] < bid_amount:
        conn.close()
        return False, "سکه کافی نداری."
    if row["current_bidder"]:
        add_currency(row["current_bidder"], "coin", row["current_bid"])
    add_currency(bidder_id, "coin", -bid_amount)
    conn.execute("UPDATE auctions SET current_bid=?, current_bidder=? WHERE id=?", (bid_amount, bidder_id, auction_id))
    conn.commit()
    conn.close()
    return True, "پیشنهاد تو ثبت شد."


def resolve_expired_auctions():
    conn = db()
    rows = conn.execute("SELECT * FROM auctions WHERE status='open'").fetchall()
    for row in rows:
        if datetime.now() >= datetime.fromisoformat(row["end_time"]):
            if row["current_bidder"]:
                add_currency(row["current_bidder"], row["item_field"], row["item_amount"])
                add_currency(row["seller_id"], "coin", row["current_bid"])
            else:
                add_currency(row["seller_id"], row["item_field"], row["item_amount"])
            conn.execute("UPDATE auctions SET status='closed' WHERE id=?", (row["id"],))
    conn.commit()
    conn.close()


# ============================================================
#                      باشگاه / کلن (جدید)
# ============================================================

def create_clan(owner_id, name):
    u = get_user(owner_id)
    if u["clan_id"]:
        return False, "تو قبلاً عضو یک باشگاهی."
    if u["diamond"] < CLAN_CREATE_COST_DIAMOND:
        return False, f"برای ساخت باشگاه {CLAN_CREATE_COST_DIAMOND} الماس لازم است."
    conn = db()
    existing = conn.execute("SELECT id FROM clans WHERE name=?", (name,)).fetchone()
    if existing:
        conn.close()
        return False, "این اسم قبلاً استفاده شده."
    add_currency(owner_id, "diamond", -CLAN_CREATE_COST_DIAMOND)
    cur = conn.execute(
        "INSERT INTO clans (name, owner_id, created_at) VALUES (?, ?, ?)",
        (name, owner_id, datetime.now().isoformat()),
    )
    clan_id = cur.lastrowid
    conn.execute("UPDATE users SET clan_id=? WHERE user_id=?", (clan_id, owner_id))
    conn.commit()
    conn.close()
    return True, clan_id


def join_clan(user_id, clan_id):
    u = get_user(user_id)
    if u["clan_id"]:
        return False, "اول باید از باشگاه فعلی خارج شوی."
    conn = db()
    clan = conn.execute("SELECT * FROM clans WHERE id=?", (clan_id,)).fetchone()
    if not clan:
        conn.close()
        return False, "باشگاه یافت نشد."
    conn.execute("UPDATE users SET clan_id=? WHERE user_id=?", (clan_id, user_id))
    conn.commit()
    conn.close()
    return True, clan["name"]


def leave_clan(user_id):
    set_field(user_id, "clan_id", 0)


def clan_deposit(user_id, amount):
    u = get_user(user_id)
    if not u["clan_id"]:
        return False, "عضو هیچ باشگاهی نیستی."
    if u["coin"] < amount:
        return False, "سکه کافی نداری."
    add_currency(user_id, "coin", -amount)
    conn = db()
    conn.execute("UPDATE clans SET bank_coin = bank_coin + ? WHERE id=?", (amount, u["clan_id"]))
    conn.commit()
    conn.close()
    return True, amount


def list_clans(limit=10):
    conn = db()
    rows = conn.execute("SELECT * FROM clans ORDER BY bank_coin DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def get_clan(clan_id):
    conn = db()
    row = conn.execute("SELECT * FROM clans WHERE id=?", (clan_id,)).fetchone()
    conn.close()
    return row


# ============================================================
#                    کد هدیه / برداشت / VIP
# ============================================================

def create_gift_code(code, field, amount, max_uses):
    conn = db()
    conn.execute(
        "INSERT INTO gift_codes (code, field, amount, max_uses) VALUES (?, ?, ?, ?)",
        (code, field, amount, max_uses),
    )
    conn.commit()
    conn.close()


def redeem_gift_code(user_id, code):
    conn = db()
    row = conn.execute("SELECT * FROM gift_codes WHERE code=?", (code,)).fetchone()
    if not row:
        conn.close()
        return False, "کد نامعتبر است."
    if row["used_count"] >= row["max_uses"]:
        conn.close()
        return False, "ظرفیت این کد تمام شده."
    used = conn.execute("SELECT 1 FROM gift_redemptions WHERE code=? AND user_id=?", (code, user_id)).fetchone()
    if used:
        conn.close()
        return False, "قبلاً این کد را استفاده کرده‌ای."
    conn.execute("INSERT INTO gift_redemptions (code, user_id) VALUES (?, ?)", (code, user_id))
    conn.execute("UPDATE gift_codes SET used_count = used_count + 1 WHERE code=?", (code,))
    conn.commit()
    conn.close()
    add_currency(user_id, row["field"], row["amount"])
    return True, (row["field"], row["amount"])


def activate_vip_subscription(user_id, tier_key, days):
    u = get_user(user_id)
    base = datetime.now()
    if u["vip_until"]:
        try:
            current_until = datetime.fromisoformat(u["vip_until"])
            if current_until > base:
                base = current_until
        except ValueError:
            pass
    new_until = base + timedelta(days=days)
    set_field(user_id, "vip_tier", tier_key)
    set_field(user_id, "vip_until", new_until.isoformat())


def expire_vip_subscriptions_job_sync():
    conn = db()
    rows = conn.execute("SELECT user_id, vip_until FROM users WHERE vip_tier != ''").fetchall()
    for r in rows:
        try:
            if datetime.fromisoformat(r["vip_until"]) < datetime.now():
                conn.execute("UPDATE users SET vip_tier='', vip_until='' WHERE user_id=?", (r["user_id"],))
        except ValueError:
            continue
    conn.commit()
    conn.close()


async def expire_vip_subscriptions_job(context: ContextTypes.DEFAULT_TYPE):
    expire_vip_subscriptions_job_sync()


def create_withdraw_request(user_id, amount, ton_address):
    u = get_user(user_id)
    if u["liber"] < amount:
        return False, "لیبر کافی نداری."
    add_currency(user_id, "liber", -amount)
    conn = db()
    conn.execute(
        "INSERT INTO withdrawals (user_id, amount, ton_address, created_at) VALUES (?, ?, ?, ?)",
        (user_id, amount, ton_address, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return True, "درخواست برداشت ثبت شد و منتظر تایید ادمین است."


def list_pending_withdrawals(limit=20):
    conn = db()
    rows = conn.execute("SELECT * FROM withdrawals WHERE status='pending' ORDER BY id LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


def approve_withdraw_request(request_id):
    conn = db()
    conn.execute("UPDATE withdrawals SET status='approved' WHERE id=?", (request_id,))
    conn.commit()
    conn.close()


def reject_withdraw_request(request_id):
    conn = db()
    row = conn.execute("SELECT * FROM withdrawals WHERE id=?", (request_id,)).fetchone()
    if row:
        add_currency(row["user_id"], "liber", row["amount"])
        conn.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (request_id,))
        conn.commit()
    conn.close()


# ============================================================
#                    رتبه‌بندی و دستاوردها
# ============================================================

def get_leaderboard(limit=10):
    conn = db()
    rows = conn.execute("SELECT user_id, first_name, xp FROM users ORDER BY xp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return rows


# ============================================================
#                      کیبوردها / منوها
# ============================================================

def main_menu_keyboard(user_id=None):
    kb = [
        [InlineKeyboardButton("👛 کیف پول", callback_data="wallet"), InlineKeyboardButton("📈 بازار", callback_data="market")],
        [InlineKeyboardButton("🏦 بانک", callback_data="bank"), InlineKeyboardButton("💳 وام", callback_data="loan")],
        [InlineKeyboardButton("🎁 صندوق‌ها", callback_data="chests"), InlineKeyboardButton("🎡 چرخ‌شانس", callback_data="wheel")],
        [InlineKeyboardButton("🔨 مزایده", callback_data="auction_list"), InlineKeyboardButton("🛡 باشگاه", callback_data="clan_menu")],
        [InlineKeyboardButton("⭐ اشتراک VIP", callback_data="vip_menu"), InlineKeyboardButton("🏆 رتبه‌بندی", callback_data="leaderboard")],
        [InlineKeyboardButton("🎟 کد هدیه", callback_data="gift_prompt"), InlineKeyboardButton("💸 برداشت", callback_data="withdraw_prompt")],
        [InlineKeyboardButton("👥 دعوت دوستان", callback_data="referral")],
    ]
    if user_id in ADMIN_IDS:
        kb.append([InlineKeyboardButton("🛠 پنل مدیریت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(kb)


def back_keyboard(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=target)]])


# ============================================================
#                        شروع / عضویت اجباری
# ============================================================

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id) -> bool:
    if not FORCE_JOIN_CHANNELS:
        return True
    not_joined = []
    for ch in FORCE_JOIN_CHANNELS:
        try:
            member = await context.bot.get_chat_member(ch["id"], user_id)
            if member.status in ("left", "kicked"):
                not_joined.append(ch)
        except Exception:
            not_joined.append(ch)
    if not_joined:
        kb = [[InlineKeyboardButton(f"📢 عضویت در {ch['title']}", url=ch["url"])] for ch in not_joined]
        kb.append([InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")])
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            "برای استفاده از ربات ابتدا باید در کانال‌های زیر عضو شوی:",
            reply_markup=InlineKeyboardMarkup(kb),
        )
        return False
    return True


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_id = tg_user.id
    ref_by = 0
    if context.args:
        try:
            ref_by = int(context.args[0])
        except ValueError:
            ref_by = 0
    ensure_user(tg_user, ref_by)

    if is_banned(user_id):
        await update.message.reply_text("⛔ حساب تو مسدود شده است.")
        return

    if not await check_force_join(update, context, user_id):
        return

    await update.message.reply_text(
        f"سلام {tg_user.first_name} 👋\nبه اقتصاد LIBER خوش آمدی!\nهمه‌چیز رو از دکمه‌های زیر انتخاب کن:",
        reply_markup=main_menu_keyboard(user_id),
    )


# ============================================================
#                    متن‌های نمایشی هر بخش
# ============================================================

def wallet_text(u):
    league = get_league_name(u["xp"])
    vip_line = f"⭐ اشتراک: {u['vip_tier']} تا {u['vip_until'][:10]}" if u["vip_tier"] else "⭐ اشتراک: ندارد"
    return (
        f"👛 کیف پول شما\n\n"
        f"🪙 سکه: {u['coin']:.0f}\n"
        f"💠 لیبر: {u['liber']:.2f}\n"
        f"💎 الماس: {u['diamond']}\n"
        f"✨ تجربه (XP): {u['xp']}  |  لیگ: {league}\n"
        f"🏦 موجودی بانک: {u['bank_balance']:.0f}\n"
        f"💳 بدهی وام: {u['loan_balance']:.0f}\n"
        f"{vip_line}"
    )


async def build_admin_dashboard_text():
    conn = db()
    total_users = conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"]
    banned = conn.execute("SELECT COUNT(*) AS n FROM users WHERE banned=1").fetchone()["n"]
    totals = conn.execute("SELECT SUM(coin) AS c, SUM(liber) AS l, SUM(diamond) AS d FROM users").fetchone()
    pending_w = conn.execute("SELECT COUNT(*) AS n FROM withdrawals WHERE status='pending'").fetchone()["n"]
    conn.close()
    return (
        "🛠 پنل مدیریت\n\n"
        f"👥 کل کاربران: {total_users}\n"
        f"⛔ مسدودشده‌ها: {banned}\n"
        f"🪙 مجموع سکه در بازی: {totals['c'] or 0:.0f}\n"
        f"💠 مجموع لیبر: {totals['l'] or 0:.2f}\n"
        f"💎 مجموع الماس: {totals['d'] or 0}\n"
        f"💸 درخواست برداشت در انتظار: {pending_w}\n"
    )


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💸 درخواست‌های برداشت", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast_prompt")],
        [InlineKeyboardButton("🚫 مسدود/آزاد کردن کاربر", callback_data="admin_ban_prompt")],
        [InlineKeyboardButton("🎟 ساخت کد هدیه", callback_data="admin_gift_prompt")],
        [InlineKeyboardButton("⭐ اعطای VIP دستی", callback_data="admin_vip_prompt")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
    ])


# ============================================================
#                       مدیریت دکمه‌ها
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    await query.answer()

    if is_banned(user_id) and data != "check_join":
        await query.message.reply_text("⛔ حساب تو مسدود شده است.")
        return

    if data == "check_join":
        if await check_force_join(update, context, user_id):
            await query.message.reply_text("✅ عضویت تایید شد. خوش آمدی!", reply_markup=main_menu_keyboard(user_id))
        return

    if data == "back_main":
        await query.edit_message_text("منوی اصلی 👇", reply_markup=main_menu_keyboard(user_id))
        return

    u = get_user(user_id)

    # ---------------- کیف پول ----------------
    if data == "wallet":
        await query.edit_message_text(wallet_text(u), reply_markup=back_keyboard())

    # ---------------- بازار ----------------
    elif data == "market":
        price = get_market_price()
        text = (f"📈 بازار لیبر\n\nقیمت هر لیبر: {price:.2f} سکه\n"
                f"کارمزد خرید: {BUY_FEE_PERCENT}%  |  کارمزد فروش: {SELL_FEE_PERCENT}%")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 خرید ۱۰۰ سکه لیبر", callback_data="market_buy_100"),
             InlineKeyboardButton("🟢 خرید ۵۰۰ سکه لیبر", callback_data="market_buy_500")],
            [InlineKeyboardButton("🔴 فروش ۱ لیبر", callback_data="market_sell_1"),
             InlineKeyboardButton("🔴 فروش ۵ لیبر", callback_data="market_sell_5")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.edit_message_text(text, reply_markup=kb)

    elif data.startswith("market_buy_"):
        amount = int(data.split("_")[-1])
        ok, res = buy_liber(user_id, amount)
        msg = f"✅ {res:.2f} لیبر خریداری شد." if ok else f"❌ {res}"
        await query.message.reply_text(msg, reply_markup=back_keyboard("market"))

    elif data.startswith("market_sell_"):
        amount = float(data.split("_")[-1])
        ok, res = sell_liber(user_id, amount)
        msg = f"✅ {res:.0f} سکه دریافت شد." if ok else f"❌ {res}"
        await query.message.reply_text(msg, reply_markup=back_keyboard("market"))

    # ---------------- بانک ----------------
    elif data == "bank":
        text = f"🏦 بانک\n\nموجودی سپرده: {u['bank_balance']:.0f} سکه\nسود روزانه: {BANK_INTEREST_PERCENT}%"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⬆️ واریز ۲۰۰", callback_data="bank_dep_200"),
             InlineKeyboardButton("⬇️ برداشت ۲۰۰", callback_data="bank_wd_200")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.edit_message_text(text, reply_markup=kb)

    elif data == "bank_dep_200":
        ok = bank_deposit(user_id, 200)
        await query.message.reply_text("✅ واریز شد." if ok else "❌ سکه کافی نداری.", reply_markup=back_keyboard("bank"))

    elif data == "bank_wd_200":
        ok = bank_withdraw(user_id, 200)
        await query.message.reply_text("✅ برداشت شد." if ok else "❌ موجودی بانک کافی نیست.", reply_markup=back_keyboard("bank"))

    # ---------------- وام ----------------
    elif data == "loan":
        text = f"💳 وام\n\nبدهی فعلی: {u['loan_balance']:.0f} سکه\nکارمزد: {LOAN_INTEREST_PERCENT}%"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📥 دریافت وام ۵۰۰", callback_data="loan_take_500")],
            [InlineKeyboardButton("📤 تسویه ۲۰۰", callback_data="loan_pay_200")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.edit_message_text(text, reply_markup=kb)

    elif data == "loan_take_500":
        ok, res = take_loan(user_id, 500)
        msg = f"✅ {res} سکه وام گرفتی." if ok else f"❌ {res}"
        await query.message.reply_text(msg, reply_markup=back_keyboard("loan"))

    elif data == "loan_pay_200":
        ok, res = repay_loan(user_id, 200)
        msg = f"✅ {res:.0f} سکه از وام تسویه شد." if ok else f"❌ {res}"
        await query.message.reply_text(msg, reply_markup=back_keyboard("loan"))

    # ---------------- صندوق‌ها ----------------
    elif data == "chests":
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🆓 رایگان", callback_data="chest_free"), InlineKeyboardButton("🥉 برنزی", callback_data="chest_bronze")],
            [InlineKeyboardButton("🥈 نقره‌ای", callback_data="chest_silver"), InlineKeyboardButton("🥇 طلایی", callback_data="chest_gold")],
            [InlineKeyboardButton("💎 الماسی", callback_data="chest_diamond")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.edit_message_text("🎁 یک صندوق را انتخاب کن:", reply_markup=kb)

    elif data.startswith("chest_"):
        key = data.split("_", 1)[1]
        ok, res = open_chest(user_id, key)
        if ok:
            lines = "\n".join(f"+ {amt} {field}" for field, amt in res)
            msg = f"🎉 صندوق باز شد!\n{lines}"
        else:
            msg = f"❌ {res}"
        await query.message.reply_text(msg, reply_markup=back_keyboard("chests"))

    # ---------------- چرخ‌شانس ----------------
    elif data == "wheel":
        ok, res = spin_wheel(user_id)
        msg = f"🎡 چرخ‌شانس چرخید...\n🎊 جایزه تو: {res}" if ok else f"⏳ {res}"
        await query.edit_message_text(msg, reply_markup=back_keyboard())

    # ---------------- مزایده ----------------
    elif data == "auction_list":
        auctions = list_open_auctions()
        if not auctions:
            text = "در حال حاضر مزایده‌ای باز نیست."
        else:
            text = "🔨 مزایده‌های باز:\n\n"
            for a in auctions:
                text += (f"#{a['id']} — {a['item_amount']} {a['item_field']}\n"
                         f"پیشنهاد فعلی: {a['current_bid']} سکه (حداقل {a['min_bid']})\n\n")
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ ثبت مزایده جدید", callback_data="auction_new")],
            [InlineKeyboardButton("💰 پیشنهاد قیمت", callback_data="auction_bid_prompt")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.edit_message_text(text, reply_markup=kb)

    elif data == "auction_new":
        context.user_data["awaiting"] = "auction_new"
        await query.message.reply_text(
            "برای ثبت مزایده پیام را به این شکل بفرست:\nliber مقدار حداقل_قیمت\nمثال: liber 5 200"
        )

    elif data == "auction_bid_prompt":
        context.user_data["awaiting"] = "auction_bid"
        await query.message.reply_text("پیام را به این شکل بفرست:\nشماره_مزایده مبلغ_پیشنهادی\nمثال: 3 250")

    # ---------------- باشگاه ----------------
    elif data == "clan_menu":
        if u["clan_id"]:
            clan = get_clan(u["clan_id"])
            text = f"🛡 باشگاه تو: {clan['name']}\n💰 خزانه: {clan['bank_coin']} سکه"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 واریز ۱۰۰ به خزانه", callback_data="clan_dep_100")],
                [InlineKeyboardButton("🚪 خروج از باشگاه", callback_data="clan_leave")],
                [InlineKeyboardButton("🏆 برترین باشگاه‌ها", callback_data="clan_top")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
            ])
        else:
            text = f"عضو هیچ باشگاهی نیستی.\nساخت باشگاه: {CLAN_CREATE_COST_DIAMOND} الماس"
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ ساخت باشگاه", callback_data="clan_create_prompt")],
                [InlineKeyboardButton("📋 لیست باشگاه‌ها", callback_data="clan_top")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
            ])
        await query.edit_message_text(text, reply_markup=kb)

    elif data == "clan_create_prompt":
        context.user_data["awaiting"] = "clan_create"
        await query.message.reply_text("اسم باشگاه مورد نظرت را بفرست:")

    elif data == "clan_dep_100":
        ok, res = clan_deposit(user_id, 100)
        await query.message.reply_text("✅ واریز شد." if ok else f"❌ {res}", reply_markup=back_keyboard("clan_menu"))

    elif data == "clan_leave":
        leave_clan(user_id)
        await query.message.reply_text("از باشگاه خارج شدی.", reply_markup=back_keyboard())

    elif data == "clan_top":
        clans = list_clans()
        if not clans:
            text = "هنوز باشگاهی ساخته نشده."
        else:
            text = "🏆 برترین باشگاه‌ها:\n\n" + "\n".join(
                f"{i+1}. {c['name']} — {c['bank_coin']} سکه" for i, c in enumerate(clans)
            )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 بازگشت", callback_data="clan_menu")],
        ])
        await query.edit_message_text(text, reply_markup=kb)

    # ---------------- VIP ----------------
    elif data == "vip_menu":
        kb_rows = []
        for tier, info in VIP_TIERS.items():
            kb_rows.append([InlineKeyboardButton(f"⭐ {tier} — {info['cost_diamond']} الماس", callback_data=f"vip_buy_{tier}")])
        kb_rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        await query.edit_message_text("⭐ اشتراک VIP\nهر تیر جایزه و سود بیشتری می‌دهد:", reply_markup=InlineKeyboardMarkup(kb_rows))

    elif data.startswith("vip_buy_"):
        tier = data.split("_", 2)[2]
        cost = VIP_TIERS[tier]["cost_diamond"]
        if u["diamond"] < cost:
            await query.message.reply_text("❌ الماس کافی نداری.", reply_markup=back_keyboard("vip_menu"))
        else:
            add_currency(user_id, "diamond", -cost)
            activate_vip_subscription(user_id, tier, 30)
            await query.message.reply_text(f"✅ اشتراک {tier} برای ۳۰ روز فعال شد!", reply_markup=back_keyboard())

    # ---------------- رتبه‌بندی ----------------
    elif data == "leaderboard":
        rows = get_leaderboard()
        text = "🏆 رتبه‌بندی برترین کاربران:\n\n" + "\n".join(
            f"{i+1}. {r['first_name']} — {r['xp']} XP" for i, r in enumerate(rows)
        )
        await query.edit_message_text(text, reply_markup=back_keyboard())

    # ---------------- کد هدیه ----------------
    elif data == "gift_prompt":
        context.user_data["awaiting"] = "gift_code"
        await query.message.reply_text("کد هدیه را بفرست:")

    # ---------------- برداشت ----------------
    elif data == "withdraw_prompt":
        context.user_data["awaiting"] = "withdraw"
        await query.message.reply_text("پیام را به این شکل بفرست:\nمقدار_لیبر آدرس_کیف‌پول_TON\nمثال: 10 UQABCDEF...")

    # ---------------- دعوت دوستان ----------------
    elif data == "referral":
        bot_username = (await context.bot.get_me()).username
        link = f"https://t.me/{bot_username}?start={user_id}"
        await query.edit_message_text(
            f"👥 دوستانت را دعوت کن و برای هر نفر ۱۰۰ سکه بگیر!\n\nلینک اختصاصی تو:\n{link}\n\nتعداد دعوت‌شده‌ها: {u['referral_count']}",
            reply_markup=back_keyboard(),
        )

    # ---------------- پنل ادمین ----------------
    elif data == "admin_panel":
        if user_id not in ADMIN_IDS:
            return
        text = await build_admin_dashboard_text()
        await query.edit_message_text(text, reply_markup=admin_keyboard())

    elif data == "admin_withdrawals":
        if user_id not in ADMIN_IDS:
            return
        rows = list_pending_withdrawals()
        if not rows:
            text = "درخواست برداشتی در انتظار نیست."
        else:
            text = "درخواست‌های در انتظار:\n\n" + "\n".join(
                f"#{r['id']} — کاربر {r['user_id']} — {r['amount']} لیبر → {r['ton_address']}" for r in rows
            )
        await query.edit_message_text(text, reply_markup=admin_keyboard())

    elif data == "admin_broadcast_prompt":
        if user_id not in ADMIN_IDS:
            return
        context.user_data["awaiting"] = "broadcast"
        await query.message.reply_text("متن پیام همگانی را بفرست:")

    elif data == "admin_ban_prompt":
        if user_id not in ADMIN_IDS:
            return
        context.user_data["awaiting"] = "admin_ban"
        await query.message.reply_text("پیام را به این شکل بفرست:\nuser_id ban یا user_id unban")

    elif data == "admin_gift_prompt":
        if user_id not in ADMIN_IDS:
            return
        context.user_data["awaiting"] = "admin_gift"
        await query.message.reply_text("پیام را به این شکل بفرست:\nکد فیلد مقدار حداکثر_استفاده\nمثال: WELCOME coin 100 500")

    elif data == "admin_vip_prompt":
        if user_id not in ADMIN_IDS:
            return
        context.user_data["awaiting"] = "admin_vip"
        await query.message.reply_text("پیام را به این شکل بفرست:\nuser_id تیر تعداد_روز\nمثال: 123456 gold 30")


# ============================================================
#              پیام‌های متنی (برای فرم‌های ساده)
# ============================================================

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return
    text = update.message.text.strip()
    context.user_data["awaiting"] = None

    try:
        if awaiting == "gift_code":
            ok, res = redeem_gift_code(user_id, text)
            if ok:
                await update.message.reply_text(f"✅ {res[1]} {res[0]} دریافت کردی!")
            else:
                await update.message.reply_text(f"❌ {res}")

        elif awaiting == "withdraw":
            amount_str, address = text.split(maxsplit=1)
            ok, res = create_withdraw_request(user_id, float(amount_str), address)
            await update.message.reply_text(("✅ " if ok else "❌ ") + res)

        elif awaiting == "auction_new":
            field, amount_str, min_bid_str = text.split()
            ok, res = create_auction(user_id, field, float(amount_str), int(min_bid_str))
            await update.message.reply_text(("✅ " if ok else "❌ ") + res)

        elif awaiting == "auction_bid":
            auction_id_str, amount_str = text.split()
            ok, res = place_bid(int(auction_id_str), user_id, int(amount_str))
            await update.message.reply_text(("✅ " if ok else "❌ ") + res)

        elif awaiting == "clan_create":
            ok, res = create_clan(user_id, text)
            await update.message.reply_text(f"✅ باشگاه «{text}» ساخته شد!" if ok else f"❌ {res}")

        elif awaiting == "broadcast" and user_id in ADMIN_IDS:
            conn = db()
            rows = conn.execute("SELECT user_id FROM users").fetchall()
            conn.close()
            sent = 0
            for r in rows:
                try:
                    await context.bot.send_message(r["user_id"], f"📢 پیام همگانی:\n\n{text}")
                    sent += 1
                except Exception:
                    continue
            await update.message.reply_text(f"✅ پیام برای {sent} کاربر ارسال شد.")

        elif awaiting == "admin_ban" and user_id in ADMIN_IDS:
            uid_str, action = text.split()
            set_field(int(uid_str), "banned", 1 if action == "ban" else 0)
            await update.message.reply_text("✅ انجام شد.")

        elif awaiting == "admin_gift" and user_id in ADMIN_IDS:
            code, field, amount_str, max_uses_str = text.split()
            create_gift_code(code, field, float(amount_str), int(max_uses_str))
            await update.message.reply_text(f"✅ کد {code} ساخته شد.")

        elif awaiting == "admin_vip" and user_id in ADMIN_IDS:
            uid_str, tier, days_str = text.split()
            activate_vip_subscription(int(uid_str), tier, int(days_str))
            await update.message.reply_text("✅ اشتراک اعطا شد.")

    except ValueError:
        await update.message.reply_text("❌ فرمت پیام درست نبود، دوباره تلاش کن.")


# ============================================================
#                      پرداخت با Telegram Stars
# ============================================================

async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    payload = payment.invoice_payload
    user_id = update.effective_user.id
    if payload.startswith("vip_"):
        tier = payload.split("_", 1)[1]
        activate_vip_subscription(user_id, tier, 30)
        await update.message.reply_text(f"✅ اشتراک {tier} با موفقیت فعال شد!")


# ============================================================
#                          دستورات ادمین
# ============================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
    text = await build_admin_dashboard_text()
    await update.message.reply_text(text, reply_markup=admin_keyboard())


# ============================================================
#                            اجرا
# ============================================================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    job_queue = app.job_queue
    job_queue.run_repeating(hourly_market_job, interval=MARKET_UPDATE_INTERVAL_SECONDS, first=10)
    job_queue.run_repeating(daily_bank_interest_job, interval=timedelta(days=1), first=60)
    job_queue.run_repeating(expire_vip_subscriptions_job, interval=timedelta(hours=1), first=30)

    logger.info("ربات LIBER در حال اجراست...")
    app.run_polling()


if __name__ == "__main__":
    main()
