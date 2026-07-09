import sqlite3
import logging
import random
import time
import json
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("LIBER")

# ============================================================
#  تنظیمات کلی
# ============================================================

BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"
ADMIN_IDS = [123456789]

FORCE_JOIN_CHANNELS = [
    {"id": "@your_channel_1", "title": "کانال اول", "url": "https://t.me/your_channel_1"},
    {"id": "@your_channel_2", "title": "کانال دوم", "url": "https://t.me/your_channel_2"},
]

DB_PATH = "liber.db"

MARKET_BASE_PRICE = 100
BUY_FEE_PERCENT = 2
SELL_FEE_PERCENT = 2
MARKET_FLUCTUATION_RANGE = (-0.07, 0.07)   # هر ساعت
MARKET_UPDATE_INTERVAL_SECONDS = 3600      # هر ۱ ساعت

BANK_INTEREST_PERCENT = 1.5     # سود روزانه سپرده
LOAN_INTEREST_PERCENT = 5       # کارمزد وام
MAX_LOAN_MULTIPLIER = 3         # سقف وام بر اساس سطح

XP_PER_LEVEL = 100
DAILY_MISSION_XP = 20
DAILY_MISSION_LIBER = 15

CHEST_TABLE = {
    "free":      {"cost": {}, "rewards": [("coin", 50, 150), ("liber", 1, 5)]},
    "bronze":    {"cost": {"coin": 300}, "rewards": [("coin", 100, 400), ("liber", 3, 10), ("xp", 10, 20)]},
    "silver":    {"cost": {"coin": 800}, "rewards": [("liber", 10, 30), ("diamond", 1, 2), ("xp", 20, 40)]},
    "gold":      {"cost": {"liber": 100}, "rewards": [("liber", 30, 80), ("diamond", 2, 5), ("medal", 1, 3)]},
    "diamond":   {"cost": {"diamond": 20}, "rewards": [("liber", 80, 200), ("diamond", 5, 10), ("medal", 2, 5)]},
}

VIP_TIERS = {
    "silver":  {"cost_diamond": 50,  "xp_bonus": 1.1, "income_bonus": 1.1},
    "gold":    {"cost_diamond": 150, "xp_bonus": 1.25, "income_bonus": 1.25},
    "diamond": {"cost_diamond": 400, "xp_bonus": 1.5, "income_bonus": 1.5},
    "titan":   {"cost_diamond": 1000, "xp_bonus": 2.0, "income_bonus": 2.0},
}

LEAGUE_THRESHOLDS = [
    (0, "🥉 برنز"),
    (500, "🥈 نقره"),
    (1500, "🥇 طلا"),
    (4000, "💠 پلاتینیوم"),
    (10000, "💎 الماس"),
    (25000, "👑 تایتان"),
    (60000, "🌌 افسانه‌ای"),
]

SPAM_COOLDOWN_SECONDS = 1.0
_last_action_time = {}
_warn_count = {}


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
            country_name TEXT DEFAULT '',
            country_pop INTEGER DEFAULT 0,
            country_budget REAL DEFAULT 0,
            bank_deposit REAL DEFAULT 0,
            loan_amount REAL DEFAULT 0,
            alliance_id INTEGER DEFAULT 0,
            ref_by INTEGER DEFAULT 0,
            ref_count INTEGER DEFAULT 0,
            last_daily_mission TEXT DEFAULT '',
            last_daily_reward TEXT DEFAULT '',
            banned INTEGER DEFAULT 0,
            warn_count INTEGER DEFAULT 0
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY,
            price REAL
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS alliances (
            alliance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            leader_id INTEGER,
            treasury REAL DEFAULT 0
        )
        """
    )
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
    vip = u["vip"]
    bonus = VIP_TIERS.get(vip, {}).get("xp_bonus", 1.0)
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
    else:
        c.execute(
            """
            INSERT INTO users (user_id, username, first_name, joined_at, last_seen, ref_by)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
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


# ============================================================
#  کیبوردها
# ============================================================

def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton("👤 پروفایل", callback_data="profile"),
         InlineKeyboardButton("🌍 کشور", callback_data="country"),
         InlineKeyboardButton("💹 بازار", callback_data="market")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet"),
         InlineKeyboardButton("🏦 بانک", callback_data="bank"),
         InlineKeyboardButton("🏪 فروشگاه", callback_data="shop")],
        [InlineKeyboardButton("🎁 صندوق‌ها", callback_data="chests"),
         InlineKeyboardButton("🎯 مأموریت‌ها", callback_data="missions"),
         InlineKeyboardButton("🏆 لیگ", callback_data="league")],
        [InlineKeyboardButton("🤝 اتحاد", callback_data="alliance"),
         InlineKeyboardButton("📊 رتبه‌بندی", callback_data="ranking"),
         InlineKeyboardButton("⭐ VIP", callback_data="vip")],
        [InlineKeyboardButton("👥 دعوت دوستان", callback_data="invite"),
         InlineKeyboardButton("🎁 جایزه روزانه", callback_data="daily"),
         InlineKeyboardButton("📰 اخبار", callback_data="news")],
        [InlineKeyboardButton("❓ راهنما", callback_data="help"),
         InlineKeyboardButton("☎ پشتیبانی", callback_data="support")],
    ]
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
        buttons = [
            [InlineKeyboardButton(f"📢 عضویت در {ch['title']}", url=ch["url"])]
            for ch in not_joined
        ]
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
        await update.message.reply_text("🚫 حساب شما مسدود شده است. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
        return

    joined_ok = await check_force_join(update, context, user_id)
    if not joined_ok:
        return

    is_new = create_user_if_not_exists(tg_user, ref_by)
    u = get_user(user_id)

    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    current_date = now.strftime("%Y-%m-%d")
    last_year = now.year - 1

    welcome = (
        "🌌 ═══════════════════ 🌌\n"
        f"✨ خوش اومدی به دنیای <b>LIBER</b> ✨\n"
        "🌌 ═══════════════════ 🌌\n\n"
        f"👋 سلام جناب <b>{tg_user.first_name}</b> خوش اومدی به لیبر!\n\n"
        f"🪪 آیدی عددی: <code>{user_id}</code>\n"
        f"👤 نام کاربری: @{tg_user.username if tg_user.username else 'ندارد'}\n"
        f"📅 تاریخ ورود: {current_date}\n"
        f"🕒 ساعت فعلی: {current_time}\n"
        f"📆 یک سال قبل: {last_year}\n"
        f"🔁 تعداد ورود: {u['login_count']}\n\n"
        f"💰 موجودی فعلی:\n"
        f"🪙 LIBER: <b>{u['liber']}</b>\n"
        f"💵 Coin: <b>{u['coin']}</b>\n"
        f"⚡ Energy: <b>{u['energy']}</b>\n"
        f"💎 Diamond: <b>{u['diamond']}</b>\n"
        f"🏅 Medal: <b>{u['medal']}</b>\n\n"
        "⚠️ توجه: تقلب، فحاشی و اسپم در ربات ممنوع است و باعث اخطار یا مسدودی می‌شود.\n\n"
        "👇 از دکمه‌های زیر برای شروع بازی استفاده کن:"
    )

    if is_new:
        welcome += "\n\n🎉 چون تازه به LIBER پیوستی، ۱۰۰ LIBER و ۵۰۰ Coin هدیه گرفتی!"

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard())


# ============================================================
#  Job ساعتی نوسان بازار
# ============================================================

async def hourly_market_job(context: ContextTypes.DEFAULT_TYPE):
    price = get_market_price()
    change = random.uniform(*MARKET_FLUCTUATION_RANGE)
    new_price = max(1, round(price * (1 + change), 2))
    set_market_price(new_price)
    direction = "📈 صعودی" if new_price >= price else "📉 نزولی"
    logger.info(f"Market price updated: {price} -> {new_price} ({direction})")


# ============================================================
#  هندلر اصلی دکمه‌ها
# ============================================================

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if is_banned(user_id):
        await query.answer("🚫 حساب شما مسدود است.", show_alert=True)
        return

    ok, warns = anti_spam_check(user_id)
    if not ok:
        if warns >= 5:
            conn = db()
            c = conn.cursor()
            c.execute("UPDATE users SET warn_count=warn_count+1 WHERE user_id=?", (user_id,))
            conn.commit()
            conn.close()
        await query.answer("⚠️ لطفاً کمی آرام‌تر! (ضد اسپم فعال شد)", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "check_join":
        joined_ok = await check_force_join(update, context, user_id)
        if joined_ok:
            await query.message.edit_text("✅ عضویت شما تایید شد! از منوی زیر استفاده کن:", reply_markup=main_menu_keyboard())
        return

    if data == "back_main":
        await query.message.edit_text("🌍 منوی اصلی LIBER:", reply_markup=main_menu_keyboard())
        return

    u = get_user(user_id)

    # ---------------- پروفایل ----------------
    if data == "profile":
        league = get_league_name(u["xp"] + u["level"] * XP_PER_LEVEL)
        text = (
            "👤 <b>پروفایل شما</b>\n\n"
            f"🆔 آیدی: <code>{user_id}</code>\n"
            f"📛 نام: {u['first_name']}\n"
            f"⭐ سطح: {u['level']}\n"
            f"💎 XP: {u['xp']} / {u['level']*XP_PER_LEVEL}\n"
            f"🏆 لیگ: {league}\n"
            f"🏅 مدال: {u['medal']}\n"
            f"👑 VIP: {u['vip']}\n"
            f"🌍 کشور: {u['country_name'] or 'ثبت نشده'}\n"
            f"👥 زیرمجموعه: {u['ref_count']} نفر\n"
            f"📅 عضویت: {u['joined_at']}\n"
            f"🔁 تعداد ورود: {u['login_count']}"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- کیف پول ----------------
    elif data == "wallet":
        text = (
            "💰 <b>کیف پول شما</b>\n\n"
            f"🪙 LIBER: {u['liber']}\n"
            f"💵 Coin: {u['coin']}\n"
            f"⚡ Energy: {u['energy']}\n"
            f"💎 Diamond: {u['diamond']}\n"
            f"🏅 Medal: {u['medal']}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📤 برداشت", callback_data="withdraw"),
             InlineKeyboardButton("📥 واریز", callback_data="deposit")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    # ---------------- بازار ----------------
    elif data == "market":
        price = get_market_price()
        text = (
            "💹 <b>بازار LIBER</b>\n\n"
            f"📈 قیمت لحظه‌ای هر LIBER: <b>{price} Coin</b>\n"
            f"⏱ قیمت هر ۱ ساعت به‌صورت خودکار نوسان می‌کند.\n"
            f"💼 موجودی شما: {u['liber']} LIBER | {u['coin']} Coin"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🟢 خرید", callback_data="market_buy"),
             InlineKeyboardButton("🔴 فروش", callback_data="market_sell")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data in ("market_buy", "market_sell"):
        action = "buy" if data == "market_buy" else "sell"
        amounts = [10, 50, 100, 500]
        buttons = [
            [InlineKeyboardButton(f"{amt} LIBER", callback_data=f"{action}_{amt}") for amt in amounts[:2]],
            [InlineKeyboardButton(f"{amt} LIBER", callback_data=f"{action}_{amt}") for amt in amounts[2:]],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="market")],
        ]
        label = "خرید" if action == "buy" else "فروش"
        await query.message.edit_text(f"💱 مقدار {label} را انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("buy_") or data.startswith("sell_"):
        action, amt_str = data.split("_")
        amount = float(amt_str)
        price = get_market_price()
        cost = amount * price

        if action == "buy":
            fee = cost * BUY_FEE_PERCENT / 100
            total_cost = cost + fee
            if u["coin"] < total_cost:
                await query.message.edit_text("❌ موجودی Coin کافی نیست.", reply_markup=back_keyboard())
                return
            add_currency(user_id, "coin", -total_cost)
            add_currency(user_id, "liber", amount)
            await query.message.edit_text(
                f"✅ خرید موفق!\n{amount} LIBER خریدی به قیمت {round(cost,2)} Coin (+ کارمزد {round(fee,2)})",
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
                f"✅ فروش موفق!\n{amount} LIBER فروختی و {round(net,2)} Coin گرفتی (کارمزد {round(fee,2)})",
                reply_markup=back_keyboard(),
            )

    # ---------------- بانک ----------------
    elif data == "bank":
        text = (
            "🏦 <b>بانک LIBER</b>\n\n"
            f"💰 سپرده فعلی: {u['bank_deposit']} Coin\n"
            f"📈 سود روزانه سپرده: {BANK_INTEREST_PERCENT}%\n"
            f"💳 وام فعلی: {u['loan_amount']} Coin\n"
            f"📊 کارمزد وام: {LOAN_INTEREST_PERCENT}%"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ سپرده‌گذاری", callback_data="bank_deposit"),
             InlineKeyboardButton("➖ برداشت سپرده", callback_data="bank_withdraw")],
            [InlineKeyboardButton("💳 درخواست وام", callback_data="bank_loan"),
             InlineKeyboardButton("✅ پرداخت وام", callback_data="bank_payloan")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "bank_deposit":
        amount = min(500, u["coin"])
        if amount <= 0:
            await query.message.edit_text("❌ موجودی Coin کافی نیست.", reply_markup=back_keyboard("bank"))
            return
        add_currency(user_id, "coin", -amount)
        add_currency(user_id, "bank_deposit", amount)
        await query.message.edit_text(f"✅ {amount} Coin به سپرده بانکی اضافه شد.", reply_markup=back_keyboard("bank"))

    elif data == "bank_withdraw":
        u2 = get_user(user_id)
        amount = u2["bank_deposit"]
        if amount <= 0:
            await query.message.edit_text("❌ سپرده‌ای برای برداشت وجود ندارد.", reply_markup=back_keyboard("bank"))
            return
        interest = amount * BANK_INTEREST_PERCENT / 100
        total = amount + interest
        set_field(user_id, "bank_deposit", 0)
        add_currency(user_id, "coin", total)
        await query.message.edit_text(
            f"✅ کل سپرده برداشت شد: {round(total,2)} Coin (شامل {round(interest,2)} سود)",
            reply_markup=back_keyboard("bank"),
        )

    elif data == "bank_loan":
        max_loan = u["level"] * 100 * MAX_LOAN_MULTIPLIER
        if u["loan_amount"] > 0:
            await query.message.edit_text("❌ ابتدا وام فعلی را پرداخت کن.", reply_markup=back_keyboard("bank"))
            return
        loan = max_loan
        add_currency(user_id, "coin", loan)
        set_field(user_id, "loan_amount", loan * (1 + LOAN_INTEREST_PERCENT / 100))
        await query.message.edit_text(
            f"✅ وام {loan} Coin دریافت شد. مبلغ بازپرداخت با کارمزد: {round(loan*(1+LOAN_INTEREST_PERCENT/100),2)} Coin",
            reply_markup=back_keyboard("bank"),
        )

    elif data == "bank_payloan":
        u2 = get_user(user_id)
        if u2["loan_amount"] <= 0:
            await query.message.edit_text("✅ شما وامی ندارید.", reply_markup=back_keyboard("bank"))
            return
        if u2["coin"] < u2["loan_amount"]:
            await query.message.edit_text("❌ موجودی Coin برای پرداخت کامل وام کافی نیست.", reply_markup=back_keyboard("bank"))
            return
        add_currency(user_id, "coin", -u2["loan_amount"])
        set_field(user_id, "loan_amount", 0)
        await query.message.edit_text("✅ وام با موفقیت پرداخت شد.", reply_markup=back_keyboard("bank"))

    # ---------------- کشور ----------------
    elif data == "country":
        if not u["country_name"]:
            text = "🌍 هنوز کشوری نساخته‌ای! با ثبت کشور، جمعیت و بودجه اولیه می‌گیری."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏛 ساخت کشور", callback_data="country_create")],
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
            ])
            await query.message.edit_text(text, reply_markup=kb)
        else:
            text = (
                f"🌍 <b>کشور {u['country_name']}</b>\n\n"
                f"👥 جمعیت: {u['country_pop']}\n"
                f"💰 بودجه: {u['country_budget']} Coin\n"
                "📈 هر بار «جمع‌آوری مالیات» بزنی، بر اساس جمعیت درآمد می‌گیری."
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 جمع‌آوری مالیات", callback_data="country_tax")],
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
            ])
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "country_create":
        set_field(user_id, "country_name", f"کشور {u['first_name']}")
        set_field(user_id, "country_pop", 100)
        set_field(user_id, "country_budget", 200)
        await query.message.edit_text("🎉 کشورت ساخته شد! ۱۰۰ جمعیت و ۲۰۰ Coin بودجه اولیه گرفتی.", reply_markup=back_keyboard())

    elif data == "country_tax":
        u2 = get_user(user_id)
        tax_income = round(u2["country_pop"] * 0.5, 2)
        add_currency(user_id, "country_budget", tax_income)
        add_currency(user_id, "coin", tax_income)
        new_level = add_xp(user_id, 5)
        await query.message.edit_text(
            f"💰 مالیات جمع‌آوری شد: {tax_income} Coin\n⭐ 5 XP گرفتی (سطح فعلی: {new_level})",
            reply_markup=back_keyboard(),
        )

    # ---------------- صندوق‌ها ----------------
    elif data == "chests":
        buttons = []
        row = []
        for i, key in enumerate(CHEST_TABLE.keys()):
            row.append(InlineKeyboardButton(f"🎁 {key}", callback_data=f"chest_{key}"))
            if len(row) == 3:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")])
        await query.message.edit_text("🎁 یک صندوق را برای باز کردن انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("chest_"):
        key = data.split("_", 1)[1]
        chest = CHEST_TABLE.get(key)
        if not chest:
            await query.message.edit_text("❌ صندوق نامعتبر.", reply_markup=back_keyboard("chests"))
            return
        for currency, cost in chest["cost"].items():
            if u[currency] < cost:
                await query.message.edit_text(f"❌ {currency} کافی برای باز کردن این صندوق نداری.", reply_markup=back_keyboard("chests"))
                return
        for currency, cost in chest["cost"].items():
            add_currency(user_id, currency, -cost)

        reward_lines = []
        for field, low, high in chest["rewards"]:
            amount = random.randint(low, high)
            if field == "xp":
                add_xp(user_id, amount)
            else:
                add_currency(user_id, field, amount)
            reward_lines.append(f"+ {amount} {field}")

        text = f"🎉 صندوق {key} باز شد!\n\n" + "\n".join(reward_lines)
        await query.message.edit_text(text, reply_markup=back_keyboard("chests"))

    # ---------------- مأموریت‌ها ----------------
    elif data == "missions":
        today = datetime.now().strftime("%Y-%m-%d")
        done_today = u["last_daily_mission"] == today
        text = (
            "🎯 <b>مأموریت روزانه</b>\n\n"
            "📋 وظیفه: با ربات تعامل داشته باش (باز کردن این منو کافیست)\n"
            f"🎁 جایزه: {DAILY_MISSION_XP} XP + {DAILY_MISSION_LIBER} LIBER\n\n"
            + ("✅ امروز قبلاً دریافت کردی." if done_today else "🟢 آماده دریافت جایزه!")
        )
        kb_buttons = []
        if not done_today:
            kb_buttons.append([InlineKeyboardButton("✅ دریافت جایزه", callback_data="mission_claim")])
        kb_buttons.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(kb_buttons))

    elif data == "mission_claim":
        today = datetime.now().strftime("%Y-%m-%d")
        if u["last_daily_mission"] == today:
            await query.message.edit_text("✅ امروز قبلاً دریافت کردی.", reply_markup=back_keyboard("missions"))
            return
        set_field(user_id, "last_daily_mission", today)
        add_currency(user_id, "liber", DAILY_MISSION_LIBER)
        new_level = add_xp(user_id, DAILY_MISSION_XP)
        await query.message.edit_text(
            f"🎉 جایزه مأموریت روزانه گرفتی: {DAILY_MISSION_XP} XP + {DAILY_MISSION_LIBER} LIBER\n(سطح فعلی: {new_level})",
            reply_markup=back_keyboard("missions"),
        )

    # ---------------- لیگ ----------------
    elif data == "league":
        total_xp = u["xp"] + u["level"] * XP_PER_LEVEL
        league = get_league_name(total_xp)
        text = (
            "🏆 <b>لیگ شما</b>\n\n"
            f"🎖 لیگ فعلی: {league}\n"
            f"💎 مجموع XP: {total_xp}\n\n"
            "📈 با کسب XP بیشتر (مأموریت، بازار، مالیات) به لیگ بالاتر می‌روی."
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- رتبه‌بندی ----------------
    elif data == "ranking":
        conn = db()
        c = conn.cursor()
        c.execute("SELECT first_name, liber FROM users ORDER BY liber DESC LIMIT 10")
        top = c.fetchall()
        conn.close()
        lines = [f"{i+1}. {row['first_name']} — {row['liber']} LIBER" for i, row in enumerate(top)]
        text = "📊 <b>برترین‌های LIBER</b>\n\n" + "\n".join(lines) if lines else "هنوز داده‌ای موجود نیست."
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- VIP ----------------
    elif data == "vip":
        text = "⭐ <b>سطوح VIP</b>\n\n" + "\n".join(
            f"{tier}: {info['cost_diamond']} Diamond — درآمد و XP x{info['income_bonus']}"
            for tier, info in VIP_TIERS.items()
        )
        buttons = [[InlineKeyboardButton(f"خرید {tier}", callback_data=f"vip_{tier}")] for tier in VIP_TIERS]
        buttons.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("vip_"):
        tier = data.split("_", 1)[1]
        info = VIP_TIERS.get(tier)
        if not info:
            await query.message.edit_text("❌ سطح VIP نامعتبر.", reply_markup=back_keyboard("vip"))
            return
        if u["diamond"] < info["cost_diamond"]:
            await query.message.edit_text("❌ Diamond کافی نداری.", reply_markup=back_keyboard("vip"))
            return
        add_currency(user_id, "diamond", -info["cost_diamond"])
        set_field(user_id, "vip", tier)
        await query.message.edit_text(f"🎉 تبریک! اکنون VIP {tier} هستی.", reply_markup=back_keyboard("vip"))

    # ---------------- اتحاد ----------------
    elif data == "alliance":
        if u["alliance_id"]:
            conn = db()
            c = conn.cursor()
            c.execute("SELECT * FROM alliances WHERE alliance_id=?", (u["alliance_id"],))
            alliance = c.fetchone()
            conn.close()
            text = (
                f"🤝 <b>اتحاد {alliance['name']}</b>\n\n"
                f"💰 خزانه: {alliance['treasury']} Coin\n"
                f"👑 رهبر: {alliance['leader_id']}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("💰 کمک به خزانه", callback_data="alliance_donate")],
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
            ])
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)
        else:
            text = "🤝 هنوز عضو هیچ اتحادی نیستی."
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🏛 ساخت اتحاد جدید", callback_data="alliance_create")],
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
            ])
            await query.message.edit_text(text, reply_markup=kb)

    elif data == "alliance_create":
        conn = db()
        c = conn.cursor()
        c.execute(
            "INSERT INTO alliances (name, leader_id, treasury) VALUES (?, ?, 0)",
            (f"اتحاد {u['first_name']}", user_id),
        )
        alliance_id = c.lastrowid
        conn.commit()
        conn.close()
        set_field(user_id, "alliance_id", alliance_id)
        await query.message.edit_text("🎉 اتحاد جدید ساخته شد و رهبر آن شدی!", reply_markup=back_keyboard("alliance"))

    elif data == "alliance_donate":
        amount = min(100, u["coin"])
        if amount <= 0:
            await query.message.edit_text("❌ Coin کافی نداری.", reply_markup=back_keyboard("alliance"))
            return
        add_currency(user_id, "coin", -amount)
        conn = db()
        c = conn.cursor()
        c.execute("UPDATE alliances SET treasury = treasury + ? WHERE alliance_id=?", (amount, u["alliance_id"]))
        conn.commit()
        conn.close()
        await query.message.edit_text(f"✅ {amount} Coin به خزانه اتحاد اضافه شد.", reply_markup=back_keyboard("alliance"))

    # ---------------- دعوت ----------------
    elif data == "invite":
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user_id}"
        text = (
            "👥 <b>دعوت دوستان</b>\n\n"
            f"🔗 لینک اختصاصی شما:\n{link}\n\n"
            f"👥 تعداد زیرمجموعه: {u['ref_count']} نفر\n"
            "🎁 هر دعوت جدید: 50 LIBER + 200 Coin"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- جایزه روزانه ----------------
    elif data == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        if u["last_daily_reward"] == today:
            await query.message.edit_text("✅ جایزه امروزت را قبلاً گرفتی.", reply_markup=back_keyboard())
            return
        reward_liber = random.randint(5, 30)
        set_field(user_id, "last_daily_reward", today)
        add_currency(user_id, "liber", reward_liber)
        await query.message.edit_text(
            f"🎁 جایزه روزانه دریافت شد: <b>{reward_liber} LIBER</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard(),
        )

    # ---------------- پنل ادمین ----------------
    elif data == "admin_panel" and user_id in ADMIN_IDS:
        await show_admin_panel(query)

    else:
        placeholders = {
            "shop": "🏪 فروشگاه (خرید صندوق و انرژی با Coin/Diamond) در نسخه بعدی گسترش می‌یابد.",
            "news": "📰 اخبار جهانی به‌زودی فعال می‌شود.",
            "help": "❓ راهنما: از منوی اصلی گزینه‌ها را انتخاب کن.",
            "support": "☎ پشتیبانی: به‌زودی آیدی پشتیبانی اضافه می‌شود.",
            "withdraw": "📤 برداشت TON: این بخش نیازمند تایید ادمین است.",
            "deposit": "📥 واریز: به‌زودی فعال می‌شود.",
        }
        text = placeholders.get(data, "🔧 این بخش هنوز در حال توسعه است.")
        await query.message.edit_text(text, reply_markup=back_keyboard())


async def show_admin_panel(query):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM users WHERE banned=1")
    banned_users = c.fetchone()["cnt"]
    conn.close()
    text = (
        "👑 <b>پنل مدیریت TITAN</b>\n\n"
        f"🕒 زمان سرور: {now}\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🚫 کاربران مسدود: {banned_users}\n"
        f"📈 قیمت بازار: {get_market_price()} Coin"
    )
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_panel")],
        [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
    ])
    await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


# ============================================================
#  دستورات ادمین (متنی)
# ============================================================

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = c.fetchone()["cnt"]
    conn.close()
    text = (
        "👑 <b>پنل مدیریت TITAN</b>\n\n"
        f"🕒 زمان سرور: {now}\n"
        f"👥 کل کاربران: {total_users}\n"
        f"📈 قیمت بازار: {get_market_price()} Coin"
    )
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_panel")]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /ban USER_ID")
        return
    target_id = int(context.args[0])
    set_field(target_id, "banned", 1)
    await update.message.reply_text(f"🚫 کاربر {target_id} مسدود شد.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /unban USER_ID")
        return
    target_id = int(context.args[0])
    set_field(target_id, "banned", 0)
    await update.message.reply_text(f"✅ کاربر {target_id} از مسدودی خارج شد.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن پیام")
        return
    message_text = " ".join(context.args)
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    all_users = c.fetchall()
    conn.close()
    sent = 0
    for row in all_users:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {message_text}")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ پیام برای {sent} کاربر ارسال شد.")


# ============================================================
#  main
# ============================================================

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    # نوسان خودکار قیمت بازار هر ۱ ساعت
    app.job_queue.run_repeating(
        hourly_market_job,
        interval=MARKET_UPDATE_INTERVAL_SECONDS,
        first=MARKET_UPDATE_INTERVAL_SECONDS,
    )

    logger.info("LIBER bot (all-in-one) started.")
    app.run_polling()


if __name__ == "__main__":
    main()
