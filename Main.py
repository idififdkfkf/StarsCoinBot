import sqlite3
import logging
import random
import time
import json
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("LIBER")

# ============================================================
#  تنظیمات کلی
# ============================================================

BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"   # از متغیر محیطی هم می‌تونی بخونی: os.environ.get("BOT_TOKEN")
ADMIN_IDS = [123456789]

FORCE_JOIN_CHANNELS = [
    {"id": "@Libercoin1", "title": "کانال LIBER", "url": "https://t.me/Libercoin1"},
]

DB_PATH = "liber.db"

MARKET_BASE_PRICE = 100
BUY_FEE_PERCENT = 2
SELL_FEE_PERCENT = 2
MARKET_FLUCTUATION_RANGE = (-0.07, 0.07)
MARKET_UPDATE_INTERVAL_SECONDS = 3600

BANK_INTEREST_PERCENT = 1.5
LOAN_INTEREST_PERCENT = 5
MAX_LOAN_MULTIPLIER = 3

XP_PER_LEVEL = 100
DAILY_MISSION_XP = 20
DAILY_MISSION_LIBER = 15

CHEST_TABLE = {
    "free":    {"cost": {}, "rewards": [("coin", 50, 150), ("liber", 1, 5)]},
    "bronze":  {"cost": {"coin": 300}, "rewards": [("coin", 100, 400), ("liber", 3, 10), ("xp", 10, 20)]},
    "silver":  {"cost": {"coin": 800}, "rewards": [("liber", 10, 30), ("diamond", 1, 2), ("xp", 20, 40)]},
    "gold":    {"cost": {"liber": 100}, "rewards": [("liber", 30, 80), ("diamond", 2, 5), ("medal", 1, 3)]},
    "diamond": {"cost": {"diamond": 20}, "rewards": [("liber", 80, 200), ("diamond", 5, 10), ("medal", 2, 5)]},
}

VIP_TIERS = {
    "silver":  {"cost_diamond": 50,  "xp_bonus": 1.1, "income_bonus": 1.1},
    "gold":    {"cost_diamond": 150, "xp_bonus": 1.25, "income_bonus": 1.25},
    "diamond": {"cost_diamond": 400, "xp_bonus": 1.5, "income_bonus": 1.5},
    "titan":   {"cost_diamond": 1000, "xp_bonus": 2.0, "income_bonus": 2.0},
}

LEAGUE_THRESHOLDS = [
    (0, "🥉 برنز"), (500, "🥈 نقره"), (1500, "🥇 طلا"), (4000, "💠 پلاتینیوم"),
    (10000, "💎 الماس"), (25000, "👑 تایتان"), (60000, "🌌 افسانه‌ای"),
]

SHOP_ITEMS = {
    "energy_50":  {"title": "⚡ ۵۰ انرژی", "cost": {"coin": 200}, "give": ("energy", 50)},
    "energy_200": {"title": "⚡ ۲۰۰ انرژی", "cost": {"coin": 700}, "give": ("energy", 200)},
    "diamond_10": {"title": "💎 ۱۰ الماس", "cost": {"liber": 150}, "give": ("diamond", 10)},
    "diamond_50": {"title": "💎 ۵۰ الماس", "cost": {"liber": 650}, "give": ("diamond", 50)},
}

SPAM_COOLDOWN_SECONDS = 1.0
_last_action_time = {}
_warn_count = {}
MAX_WARN_BEFORE_BAN = 5
BANNED_WORDS = ["fuckyou"]


# ============================================================
#  دیتابیس
# ============================================================

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TEXT,
            last_seen TEXT,
            login_count INTEGER DEFAULT 1,
            level INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            liber REAL DEFAULT 100,
            coin REAL DEFAULT 500,
            energy INTEGER DEFAULT 100,
            diamond INTEGER DEFAULT 0,
            medal INTEGER DEFAULT 0,
            vip TEXT DEFAULT 'none',
            bank_deposit REAL DEFAULT 0,
            loan_amount REAL DEFAULT 0,
            ref_by INTEGER DEFAULT 0,
            ref_count INTEGER DEFAULT 0,
            last_daily_mission TEXT DEFAULT '',
            last_daily_reward TEXT DEFAULT '',
            banned INTEGER DEFAULT 0,
            warn_count INTEGER DEFAULT 0,
            chest_count INTEGER DEFAULT 0
        )
        """
    )
    c.execute("CREATE TABLE IF NOT EXISTS market (id INTEGER PRIMARY KEY, price REAL)")
    c.execute("SELECT COUNT(*) as cnt FROM market")
    if c.fetchone()["cnt"] == 0:
        c.execute("INSERT INTO market (id, price) VALUES (1, ?)", (MARKET_BASE_PRICE,))
    conn.commit()
    conn.close()


def get_user(user_id):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    return row


def set_field(user_id, field, value):
    conn = db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, user_id))
    conn.commit()
    conn.close()


def add_currency(user_id, field, amount):
    conn = db()
    c = conn.cursor()
    c.execute(f"UPDATE users SET {field} = {field} + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()


def add_xp(user_id, amount):
    u = get_user(user_id)
    bonus = VIP_TIERS.get(u["vip"], {}).get("xp_bonus", 1.0)
    amount = int(amount * bonus)
    new_xp = u["xp"] + amount
    new_level = u["level"]
    while new_xp >= new_level * XP_PER_LEVEL:
        new_xp -= new_level * XP_PER_LEVEL
        new_level += 1
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE users SET xp=?, level=? WHERE user_id=?", (new_xp, new_level, user_id))
    conn.commit()
    conn.close()
    return new_level


def get_market_price():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT price FROM market WHERE id=1")
    price = c.fetchone()["price"]
    conn.close()
    return price


def set_market_price(price):
    conn = db()
    c = conn.cursor()
    c.execute("UPDATE market SET price=? WHERE id=1", (price,))
    conn.commit()
    conn.close()


def get_league_name(xp_total):
    name = LEAGUE_THRESHOLDS[0][1]
    for threshold, league_name in LEAGUE_THRESHOLDS:
        if xp_total >= threshold:
            name = league_name
    return name


def create_user_if_not_exists(tg_user, ref_by=0):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE user_id=?", (tg_user.id,))
    existing = c.fetchone()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if existing:
        c.execute(
            "UPDATE users SET last_seen=?, login_count=login_count+1, username=?, first_name=? WHERE user_id=?",
            (now, tg_user.username or "", tg_user.first_name or "", tg_user.id),
        )
        conn.commit()
        conn.close()
        return False
    c.execute(
        "INSERT INTO users (user_id, username, first_name, joined_at, last_seen, ref_by) VALUES (?, ?, ?, ?, ?, ?)",
        (tg_user.id, tg_user.username or "", tg_user.first_name or "", now, now, ref_by),
    )
    if ref_by:
        c.execute(
            "UPDATE users SET ref_count=ref_count+1, liber=liber+50, coin=coin+200 WHERE user_id=?",
            (ref_by,),
        )
    conn.commit()
    conn.close()
    return True


def is_banned(user_id):
    u = get_user(user_id)
    return bool(u and u["banned"] == 1)


def anti_spam_check(user_id):
    now = time.time()
    last = _last_action_time.get(user_id, 0)
    if now - last < SPAM_COOLDOWN_SECONDS:
        _warn_count[user_id] = _warn_count.get(user_id, 0) + 1
        return False, _warn_count[user_id]
    _last_action_time[user_id] = now
    _warn_count[user_id] = 0
    return True, 0


def contains_banned_word(text):
    if not text:
        return False
    lowered = text.lower()
    return any(w in lowered for w in BANNED_WORDS)


# ============================================================
#  کیبوردها
# ============================================================

def main_menu_keyboard(user_id=None):
    buttons = [
        [InlineKeyboardButton("👤 پروفایل من", callback_data="profile"),
         InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
         InlineKeyboardButton("💹 بازار زنده", callback_data="market")],
        [InlineKeyboardButton("🏦 بانک", callback_data="bank"),
         InlineKeyboardButton("🏪 فروشگاه", callback_data="shop"),
         InlineKeyboardButton("🎁 صندوق‌ها", callback_data="chests")],
        [InlineKeyboardButton("🎯 مأموریت روزانه", callback_data="missions"),
         InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily"),
         InlineKeyboardButton("🏆 لیگ من", callback_data="league")],
        [InlineKeyboardButton("📊 برترین‌ها", callback_data="ranking"),
         InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip"),
         InlineKeyboardButton("👥 زیرمجموعه", callback_data="invite")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help"),
         InlineKeyboardButton("☎ پشتیبانی", callback_data="support")],
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("👑 پنل مدیریت", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def back_keyboard(target="back_main"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منو", callback_data=target)]])


# ============================================================
#  عضویت اجباری
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
        except Exception as e:
            logger.warning(f"Force join check failed for {ch['id']}: {e}")
            not_joined.append(ch)

    if not_joined:
        buttons = [[InlineKeyboardButton(f"📢 عضویت در {ch['title']}", url=ch["url"])] for ch in not_joined]
        buttons.append([InlineKeyboardButton("✅ عضو شدم، بررسی مجدد", callback_data="check_join")])
        text = "🔒 برای استفاده از ربات LIBER ابتدا باید در کانال‌های زیر عضو شوی:"
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        elif update.callback_query:
            await update.callback_query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return False
    return True


# ============================================================
#  /start
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    user_id = tg_user.id

    ref_by = 0
    if context.args:
        try:
            possible_ref = int(context.args[0])
            if possible_ref != user_id:
                ref_by = possible_ref
        except ValueError:
            pass

    if is_banned(user_id):
        await update.message.reply_text("🚫 حساب شما مسدود شده است.")
        return

    if not await check_force_join(update, context, user_id):
        return

    is_new = create_user_if_not_exists(tg_user, ref_by)
    u = get_user(user_id)

    now = datetime.now()
    username_display = f"@{tg_user.username}" if tg_user.username else "ندارد"

    welcome = (
        "🌌 ═══════════════ 🌌\n"
        "✨ به دنیای <b>LIBER</b> خوش آمدید ✨\n"
        "🌌 ═══════════════ 🌌\n\n"
        f"👋 سلام جناب <b>{tg_user.first_name}</b>، نام کاربری {username_display} به لیبر خوش آمدید!\n\n"
        f"🪪 آیدی عددی: <code>{user_id}</code>\n"
        f"📅 تاریخ: {now.strftime('%Y-%m-%d')}\n"
        f"🕒 ساعت: {now.strftime('%H:%M:%S')}\n"
        f"🔁 تعداد ورود: {u['login_count']}\n\n"
        f"💰 موجودی فعلی:\n"
        f"🪙 LIBER: <b>{u['liber']}</b>\n"
        f"💵 Coin: <b>{u['coin']}</b>\n"
        f"⚡ Energy: <b>{u['energy']}</b>\n"
        f"💎 Diamond: <b>{u['diamond']}</b>\n"
        f"🏅 Medal: <b>{u['medal']}</b>\n\n"
        "⚠️ توجه: تقلب، فحاشی و اسپم ممنوع است و باعث اخطار یا مسدودی می‌شود.\n"
        "ℹ️ همه ارزها کاملاً درون‌بازی هستند و ارزش مالی واقعی ندارند.\n\n"
        "👇 از دکمه‌های زیر استفاده کن:"
    )
    if is_new:
        welcome += "\n\n🎉 چون تازه پیوستی، ۱۰۰ LIBER و ۵۰۰ Coin هدیه گرفتی!"

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(user_id))


# ============================================================
#  Job ساعتی نوسان بازار
# ============================================================

async def hourly_market_job(context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    change = random.uniform(*MARKET_FLUCTUATION_RANGE)
    new_price = max(1, round(price * (1 + change), 2))
    set_market_price(new_price)
    logger.info(f"Market price updated: {price} -> {new_price}")


# ============================================================
#  هندلر دکمه‌ها
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_banned(user_id):
        await query.answer("🚫 حساب شما مسدود است.", show_alert=True)
        return

    ok, warns = anti_spam_check(user_id)
    if not ok:
        await query.answer("⚠️ کمی آرام‌تر!", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "check_join":
        if await check_force_join(update, context, user_id):
            await query.message.edit_text("✅ عضویت تایید شد!", reply_markup=main_menu_keyboard(user_id))
        return

    if data == "back_main":
        await query.message.edit_text("🌍 منوی اصلی LIBER:", reply_markup=main_menu_keyboard(user_id))
        return

    u = get_user(user_id)

    if data == "profile":
        league = get_league_name(u["xp"] + u["level"] * XP_PER_LEVEL)
        text = (
            "👤 <b>پروفایل شما</b>\n━━━━━━━━━━━\n"
            f"🆔 آیدی: <code>{user_id}</code>\n"
            f"📛 نام: {u['first_name']}\n"
            f"⭐ سطح: {u['level']} | 💎 XP: {u['xp']}/{u['level']*XP_PER_LEVEL}\n"
            f"🏆 لیگ: {league}\n"
            f"🏅 مدال: {u['medal']}\n"
            f"👑 VIP: {u['vip'] if u['vip'] != 'none' else 'ندارد'}\n"
            f"👥 زیرمجموعه: {u['ref_count']} نفر\n"
            f"📅 عضویت: {u['joined_at']}\n"
            f"🔁 ورود: {u['login_count']}"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "wallet":
        text = (
            "💰 <b>کیف پول شما</b>\n\n"
            f"🪙 LIBER: {u['liber']}\n💵 Coin: {u['coin']}\n"
            f"⚡ Energy: {u['energy']}\n💎 Diamond: {u['diamond']}\n🏅 Medal: {u['medal']}"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "market":
        price = get_market_price()
        text = (
            "💹 <b>بازار LIBER</b>\n\n"
            f"📈 قیمت فعلی: <b>{price} Coin</b>\n⏱ هر ۱ ساعت خودکار تغییر می‌کند.\n"
            f"💼 موجودی: {u['liber']} LIBER | {u['coin']} Coin"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 خرید", callback_data="market_buy"),
             InlineKeyboardButton("🔴 فروش", callback_data="market_sell")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data in ("market_buy", "market_sell"):
        action = "buy" if data == "market_buy" else "sell"
        amounts = [10, 50, 100, 500]
        buttons = [
            [InlineKeyboardButton(f"{a} LIBER", callback_data=f"{action}_{a}") for a in amounts[:2]],
            [InlineKeyboardButton(f"{a} LIBER", callback_data=f"{action}_{a}") for a in amounts[2:]],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="market")],
        ]
        await query.message.edit_text("💱 مقدار را انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("buy_") or data.startswith("sell_"):
        action, amt_str = data.split("_")
        amount = float(amt_str)
        price = get_market_price()
        cost = amount * price
        if action == "buy":
            fee = cost * BUY_FEE_PERCENT / 100
            if u["coin"] < cost + fee:
                await query.message.edit_text("❌ موجودی Coin کافی نیست.", reply_markup=back_keyboard())
                return
            add_currency(user_id, "coin", -(cost + fee))
            add_currency(user_id, "liber", amount)
            await query.message.edit_text(
                f"✅ {amount} LIBER خریداری شد ({round(cost,2)} Coin + کارمزد {round(fee,2)})",
                reply_markup=back_keyboard(),
            )
        else:
            if u["liber"] < amount:
                await query.message.edit_text("❌ موجودی LIBER کافی نیست.", reply_markup=back_keyboard())
                return
            fee = cost * SELL_FEE_PERCENT / 100
            net = cost - fee
            add_currency(user_id, "liber", -amount)
            add_currency(user_id, "coin", net)
            await query.message.edit_text(
                f"✅ {amount} LIBER فروخته شد (+{round(net,2)} Coin، کارمزد {round(fee,2)})",
                reply_markup=back_keyboard(),
            )

    elif data == "bank":
        text = (
            "🏦 <b>بانک LIBER</b>\n\n"
            f"💰 سپرده: {u['bank_deposit']} Coin\n📈 سود روزانه: {BANK_INTEREST_PERCENT}%\n"
            f"💳 وام: {u['loan_amount']} Coin\n📊 کارمزد وام: {LOAN_INTEREST_PERCENT}%"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ سپرده‌گذاری", callback_data="bank_deposit"),
             InlineKeyboardButton("➖ برداشت سپرده", callback_data="bank_withdraw")],
            [InlineKeyboardButton("💳 وام", callback_data="bank_loan"),
             InlineKeyboardButton("✅ پرداخت وام", callback_data="bank_payloan")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "bank_deposit":
        amount = min(500, u["coin"])
        if amount <= 0:
            await query.message.edit_text("❌ موجودی Coin کافی نیست.", reply_markup=back_keyboard("bank"))
            return
        add_currency(user_id, "coin", -amount)
        add_currency(user_id, "bank_deposit", amount)
        await query.message.edit_text(f"✅ {amount} Coin سپرده شد.", reply_markup=back_keyboard("bank"))

    elif data == "bank_withdraw":
        amount = u["bank_deposit"]
        if amount <= 0:
            await query.message.edit_text("❌ سپرده‌ای نداری.", reply_markup=back_keyboard("bank"))
            return
        interest = amount * BANK_INTEREST_PERCENT / 100
        total = amount + interest
        set_field(user_id, "bank_deposit", 0)
        add_currency(user_id, "coin", total)
        await query.message.edit_text(f"✅ {round(total,2)} Coin برداشت شد (شامل سود {round(interest,2)})", reply_markup=back_keyboard("bank"))

    elif data == "bank_loan":
        if u["loan_amount"] > 0:
            await query.message.edit_text("❌ ابتدا وام فعلی را پرداخت کن.", reply_markup=back_keyboard("bank"))
            return
        loan = u["level"] * 100 * MAX_LOAN_MULTIPLIER
        add_currency(user_id, "coin", loan)
        set_field(user_id, "loan_amount", loan * (1 + LOAN_INTEREST_PERCENT / 100))
        await query.message.edit_text(f"✅ وام {loan} Coin دریافت شد.", reply_markup=back_keyboard("bank"))

    elif data == "bank_payloan":
        if u["loan_amount"] <= 0:
            await query.message.edit_text("✅ وامی نداری.", reply_markup=back_keyboard("bank"))
            return
        if u["coin"] < u["loan_amount"]:
            await query.message.edit_text("❌ Coin کافی نیست.", reply_markup=back_keyboard("bank"))
            return
        add_currency(user_id, "coin", -u["loan_amount"])
        set_field(user_id, "loan_amount", 0)
        await query.message.edit_text("✅ وام پرداخت شد.", reply_markup=back_keyboard("bank"))

    elif data == "shop":
        buttons = [[InlineKeyboardButton(item["title"], callback_data=f"shop_{k}")] for k, item in SHOP_ITEMS.items()]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        await query.message.edit_text("🏪 فروشگاه:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("shop_"):
        key = data.split("_", 1)[1]
        item = SHOP_ITEMS.get(key)
        if not item:
            await query.message.edit_text("❌ نامعتبر.", reply_markup=back_keyboard("shop"))
            return
        for cur, cost in item["cost"].items():
            if u[cur] < cost:
                await query.message.edit_text(f"❌ {cur} کافی نداری.", reply_markup=back_keyboard("shop"))
                return
        for cur, cost in item["cost"].items():
            add_currency(user_id, cur, -cost)
        field, amount = item["give"]
        add_currency(user_id, field, amount)
        await query.message.edit_text(f"✅ خرید موفق: {item['title']}", reply_markup=back_keyboard("shop"))

    elif data == "chests":
        buttons = [[InlineKeyboardButton(f"🎁 {k}", callback_data=f"chest_{k}")] for k in CHEST_TABLE]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        await query.message.edit_text("🎁 یک صندوق انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("chest_"):
        key = data.split("_", 1)[1]
        chest = CHEST_TABLE.get(key)
        if not chest:
            await query.message.edit_text("❌ نامعتبر.", reply_markup=back_keyboard("chests"))
            return
        for cur, cost in chest["cost"].items():
            if u[cur] < cost:
                await query.message.edit_text(f"❌ {cur} کافی نداری.", reply_markup=back_keyboard("chests"))
                return
        for cur, cost in chest["cost"].items():
            add_currency(user_id, cur, -cost)
        lines = []
        for field, lo, hi in chest["rewards"]:
            amount = random.randint(lo, hi)
            if field == "xp":
                add_xp(user_id, amount)
            else:
                add_currency(user_id, field, amount)
            lines.append(f"+ {amount} {field}")
        add_currency(user_id, "chest_count", 1)
        await query.message.edit_text(f"🎉 صندوق {key} باز شد!\n\n" + "\n".join(lines), reply_markup=back_keyboard("chests"))

    elif data == "missions":
        today = datetime.now().strftime("%Y-%m-%d")
        done = u["last_daily_mission"] == today
        text = (
            "🎯 <b>مأموریت روزانه</b>\n\n📋 با ربات تعامل داشته باش.\n"
            f"🎁 جایزه: {DAILY_MISSION_XP} XP + {DAILY_MISSION_LIBER} LIBER\n\n"
            + ("✅ امروز گرفتی." if done else "🟢 آماده دریافت!")
        )
        buttons = []
        if not done:
            buttons.append([InlineKeyboardButton("✅ دریافت جایزه", callback_data="mission_claim")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data == "mission_claim":
        today = datetime.now().strftime("%Y-%m-%d")
        if u["last_daily_mission"] == today:
            await query.message.edit_text("✅ امروز قبلاً گرفتی.", reply_markup=back_keyboard("missions"))
            return
        set_field(user_id, "last_daily_mission", today)
        add_currency(user_id, "liber", DAILY_MISSION_LIBER)
        new_level = add_xp(user_id, DAILY_MISSION_XP)
        await query.message.edit_text(
            f"🎉 +{DAILY_MISSION_XP} XP و +{DAILY_MISSION_LIBER} LIBER گرفتی! (سطح: {new_level})",
            reply_markup=back_keyboard("missions"),
        )

    elif data == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        if u["last_daily_reward"] == today:
            await query.message.edit_text("✅ امروز قبلاً گرفتی.", reply_markup=back_keyboard())
            return
        reward = random.randint(5, 30)
        set_field(user_id, "last_daily_reward", today)
        add_currency(user_id, "liber", reward)
        await query.message.edit_text(f"🎁 +{reward} LIBER دریافت شد!", reply_markup=back_keyboard())

    elif data == "league":
        total_xp = u["xp"] + u["level"] * XP_PER_LEVEL
        league = get_league_name(total_xp)
        await query.message.edit_text(
            f"🏆 لیگ فعلی: {league}\n💎 مجموع XP: {total_xp}",
            reply_markup=back_keyboard(),
        )

    elif data == "ranking":
        conn = db()
        c = conn.cursor()
        c.execute("SELECT first_name, liber FROM users ORDER BY liber DESC LIMIT 10")
        rows = c.fetchall()
        conn.close()
        lines = [f"{i+1}. {r['first_name']} — {r['liber']} LIBER" for i, r in enumerate(rows)]
        text = "📊 <b>برترین‌ها</b>\n\n" + ("\n".join(lines) if lines else "داده‌ای نیست.")
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "vip":
        text = "⭐ <b>سطوح VIP</b>\n\n" + "\n".join(
            f"{tier}: {info['cost_diamond']} Diamond — درآمد/XP x{info['income_bonus']}"
            for tier, info in VIP_TIERS.items()
        )
        buttons = [[InlineKeyboardButton(f"خرید {tier}", callback_data=f"vip_{tier}")] for tier in VIP_TIERS]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_main")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("vip_"):
        tier = data.split("_", 1)[1]
        info = VIP_TIERS.get(tier)
        if not info:
            await query.message.edit_text("❌ نامعتبر.", reply_markup=back_keyboard("vip"))
            return
        if u["diamond"] < info["cost_diamond"]:
            await query.message.edit_text("❌ Diamond کافی نداری.", reply_markup=back_keyboard("vip"))
            return
        add_currency(user_id, "diamond", -info["cost_diamond"])
        set_field(user_id, "vip", tier)
        await query.message.edit_text(f"🎉 اکنون VIP {tier} هستی!", reply_markup=back_keyboard("vip"))

    elif data == "invite":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user_id}"
        await query.message.edit_text(
            f"👥 <b>دعوت دوستان</b>\n\n🔗 لینک شما:\n{link}\n\n"
            f"👥 زیرمجموعه: {u['ref_count']} نفر\n🎁 جایزه هر دعوت: 50 LIBER + 200 Coin",
            parse_mode=ParseMode.HTML, reply_markup=back_keyboard(),
        )

    elif data == "help":
        text = (
            "❓ <b>راهنما</b>\n\n"
            "💰 کیف پول: موجودی ارزهای بازی\n"
            "💹 بازار: خرید/فروش LIBER با قیمت نوسانی\n"
            "🏦 بانک: سپرده و وام\n"
            "🎁 صندوق: باز کردن با شانس جایزه\n"
            "🎯 مأموریت روزانه: هر روز جایزه رایگان\n"
            "⭐ VIP: با Diamond مزایای ویژه بگیر\n\n"
            "همه ارزها فقط برای بازی هستند و قابل تبدیل به پول واقعی نیستند."
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "support":
        await query.message.edit_text("☎ برای پشتیبانی پیام خود را همینجا تایپ کن.", reply_markup=back_keyboard())

    elif data == "admin_panel" and user_id in ADMIN_IDS:
        conn = db()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) as cnt FROM users")
        total = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM users WHERE banned=1")
        banned = c.fetchone()["cnt"]
        conn.close()
        text = (
            f"👑 <b>پنل مدیریت</b>\n\n👥 کل کاربران: {total}\n🚫 مسدود: {banned}\n"
            f"📈 قیمت بازار: {get_market_price()} Coin\n\n"
            "دستورات: /ban ID  /unban ID  /broadcast متن"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    else:
        await query.message.edit_text("🔧 این بخش به‌زودی اضافه می‌شود.", reply_markup=back_keyboard())


# ============================================================
#  دستورات ادمین
# ============================================================

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /ban USER_ID")
        return
    set_field(int(context.args[0]), "banned", 1)
    await update.message.reply_text("🚫 مسدود شد.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /unban USER_ID")
        return
    set_field(int(context.args[0]), "banned", 0)
    await update.message.reply_text("✅ رفع مسدودی شد.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن")
        return
    msg = " ".join(context.args)
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    rows = c.fetchall()
    conn.close()
    sent = 0
    for row in rows:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {msg}")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ برای {sent} کاربر ارسال شد.")


async def text_message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    if is_banned(user_id):
        return
    if contains_banned_word(update.message.text):
        conn = db()
        c = conn.cursor()
        c.execute("UPDATE users SET warn_count=warn_count+1 WHERE user_id=?", (user_id,))
        conn.commit()
        c.execute("SELECT warn_count FROM users WHERE user_id=?", (user_id,))
        warn_count = c.fetchone()["warn_count"]
        conn.close()
        if warn_count >= MAX_WARN_BEFORE_BAN:
            set_field(user_id, "banned", 1)
            await update.message.reply_text("🚫 به دلیل استفاده مکرر از الفاظ نامناسب، مسدود شدی.")
        else:
            await update.message.reply_text(f"⚠️ از الفاظ نامناسب استفاده نکن. اخطار {warn_count}/{MAX_WARN_BEFORE_BAN}")


# ============================================================
#  main
# ============================================================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_filter))

    app.job_queue.run_repeating(hourly_market_job, interval=MARKET_UPDATE_INTERVAL_SECONDS, first=MARKET_UPDATE_INTERVAL_SECONDS)

    logger.info("LIBER bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
