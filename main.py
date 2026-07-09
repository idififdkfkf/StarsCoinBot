"""
LIBER UNIVERSE - Complete Bot (Entertainment Simulation Edition)
-----------------------------------------------------------------
Simple JSON-file storage style, single file, all features merged.

- All currencies (LIBER, Coin, Energy, Diamond) are 100% virtual.
- /withdraw only creates a request record for manual admin review.
  No blockchain transaction is ever sent automatically by this bot.

Setup:
    pip install "python-telegram-bot[job-queue]"==21.*
    export BOT_TOKEN=your:token          (never hardcode it in a public repo)
    python main.py
"""

import os
import sys
import json
import random
import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# =====================================================================
# SETTINGS
# =====================================================================

TOKEN = os.environ.get("8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y", "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y")
CHANNEL = "@Libercoin1"          # mandatory channel — set to None to disable
ADMIN_IDS = [6188951798]
DATA_FILE = "liber_data.json"

MIN_WITHDRAW = 2000
DEPOSIT_RATE = 0.02
DEPOSIT_HOURS = 24

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("liber")

# =====================================================================
# DATABASE (single JSON file, simple + human-readable)
# =====================================================================

db = {
    "users": {},          # uid -> profile dict
    "countries": {},      # uid -> country dict
    "alliances": {},      # name -> alliance dict
    "market": {"price": 100.0, "history": [], "updated": str(datetime.utcnow())},
    "auction": None,      # active auction dict or None
    "global_projects": {
        "smart_city": {"name": "🏙 شهر هوشمند", "goal": 50000, "reward": 200, "contributed": 0, "done": False},
        "energy_grid": {"name": "⚡ شبکه انرژی جهانی", "goal": 80000, "reward": 300, "contributed": 0, "done": False},
    },
    "withdrawals": [],    # list of request dicts
    "logs": [],           # simple action log
    "events": [],         # world event history
}


def load_data():
    global db
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        db.update(loaded)


def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


load_data()


def log_action(user_id, action, detail=""):
    db["logs"].append(
        {"user_id": user_id, "action": action, "detail": detail, "at": str(datetime.utcnow())}
    )
    db["logs"] = db["logs"][-500:]  # keep it bounded
    save_data()


# =====================================================================
# USER HELPERS
# =====================================================================

def get_user(user, referred_by=None):
    uid = str(user.id)
    is_new = uid not in db["users"]

    if is_new:
        db["users"][uid] = {
            "id": user.id,
            "name": user.first_name or "",
            "username": user.username or "",
            "liber": 100,
            "coin": 500,
            "energy": 100,
            "diamond": 0,
            "level": 1,
            "xp": 0,
            "title": "تازه‌وارد",
            "bio": "",
            "vip": None,
            "vip_expires": None,
            "banned": False,
            "referred_by": referred_by,
            "last_daily": None,
            "deposits": [],
            "investments": [],
            "achievements": [],
            "season_points": 0,
            "league": "bronze",
            "chest_cooldown": None,
            "created": str(datetime.utcnow()),
        }
        save_data()
        log_action(user.id, "REGISTER", user.username or "")

    return db["users"][uid], is_new


def u(user_id):
    """Shortcut to fetch a user dict by plain id (assumes already registered)."""
    return db["users"].get(str(user_id))


def add_currency(user_id, liber=0, coin=0, energy=0, diamond=0):
    user = u(user_id)
    if not user:
        return
    user["liber"] += liber
    user["coin"] += coin
    user["energy"] += energy
    user["diamond"] += diamond
    save_data()


def add_xp(user_id, amount):
    user = u(user_id)
    if not user:
        return
    user["xp"] += amount
    needed = user["level"] * 100
    while user["xp"] >= needed:
        user["xp"] -= needed
        user["level"] += 1
        needed = user["level"] * 100
    save_data()


def add_season_points(user_id, points):
    user = u(user_id)
    if not user:
        return
    user["season_points"] = max(0, user["season_points"] + points)
    thresholds = [
        ("galactic", 15000), ("legendary", 8000), ("titan", 4000), ("diamond", 2000),
        ("platinum", 1000), ("gold", 500), ("silver", 200), ("bronze", 0),
    ]
    for name, threshold in thresholds:
        if user["season_points"] >= threshold:
            user["league"] = name
            break
    save_data()


def grant_achievement(user_id, name):
    user = u(user_id)
    if not user or name in user["achievements"]:
        return False
    user["achievements"].append(name)
    save_data()
    return True


# =====================================================================
# MARKET (auto price fluctuation, once per hour)
# =====================================================================

def update_market():
    last_updated = datetime.fromisoformat(db["market"]["updated"])
    if datetime.utcnow() - last_updated >= timedelta(hours=1):
        change = random.randint(-10, 15)
        new_price = max(10, db["market"]["price"] + change)
        db["market"]["price"] = new_price
        db["market"]["updated"] = str(datetime.utcnow())
        db["market"]["history"].append({"price": new_price, "at": str(datetime.utcnow())})
        db["market"]["history"] = db["market"]["history"][-50:]
        save_data()


# =====================================================================
# KEYBOARDS
# =====================================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "🌍 کشور"],
        ["🪙 بازار LIBER", "💰 موجودی"],
        ["🏦 بانک", "🏪 فروشگاه"],
        ["🎯 مأموریت‌ها", "🎮 بازی‌ها"],
        ["🏷 مزایده", "🤝 اتحاد"],
        ["⚔️ رقابت", "💎 اشتراک VIP"],
        ["👥 دعوت دوستان", "📤 برداشت"],
        ["🏛 پروژه جهانی", "🗺 نقشه جهان"],
        ["🕵 بازار سیاه", "🎖 دستاوردها"],
        ["⚙ تنظیمات", "❓ راهنما"],
    ],
    resize_keyboard=True,
)


def admin_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 داشبورد", callback_data="a_dash")],
        [InlineKeyboardButton("👥 کاربران", callback_data="a_users")],
        [InlineKeyboardButton("💹 اقتصاد", callback_data="a_econ")],
        [InlineKeyboardButton("📤 برداشت‌ها", callback_data="a_withdraw")],
        [InlineKeyboardButton("📋 لاگ‌ها", callback_data="a_logs")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="a_broadcast")],
    ])


def join_keyboard():
    uname = CHANNEL.replace("@", "")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{uname}")],
        [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")],
    ])


def quick_actions_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 پروفایل", callback_data="qa_profile"),
            InlineKeyboardButton("💰 موجودی", callback_data="qa_balance"),
        ],
        [
            InlineKeyboardButton("🪙 بازار LIBER", callback_data="qa_market"),
            InlineKeyboardButton("🏷 مزایده", callback_data="qa_auction"),
        ],
    ])


async def is_member(bot, user_id) -> bool:
    if not CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"channel check failed: {e}")
        return False


def is_admin(user_id) -> bool:
    return user_id in ADMIN_IDS


# =====================================================================
# CORE COMMANDS
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_member(context.bot, user.id):
        await update.message.reply_text(
            f"لطفاً در کانال زیر عضو شوید:\n{CHANNEL}",
            reply_markup=join_keyboard(),
        )
        return

    referred_by = None
    if context.args:
        try:
            ref = int(context.args[0])
            if ref != user.id:
                referred_by = ref
        except ValueError:
            pass

    data, is_new = get_user(user, referred_by)
    display_name = f"@{user.username}" if user.username else user.first_name

    if is_new:
        if referred_by and u(referred_by):
            add_currency(referred_by, liber=50)
            add_xp(referred_by, 20)
        text = (
            f"سلام جناب {display_name} 👋\n"
            f"به ربات LIBER کوین خوش آمدید!\n\n"
            f"💰 موجودی اولیه: {data['liber']} LIBER\n\n"
            "⚠️ همه ارزها (LIBER, Coin, Energy, Diamond) کاملاً مجازی و فقط برای بازی هستند."
        )
    else:
        text = f"سلام جناب {display_name} 👋\nبه ربات LIBER کوین خوش برگشتید!"

    await update.message.reply_text(text, reply_markup=MAIN_MENU)
    await update.message.reply_text("دسترسی سریع:", reply_markup=quick_actions_keyboard())


async def check_join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if not await is_member(context.bot, user.id):
        await query.answer("❌ هنوز عضو نشدی.", show_alert=True)
        return

    data, is_new = get_user(user)
    display_name = f"@{user.username}" if user.username else user.first_name

    await query.edit_message_text("✅ عضویت شما با موفقیت انجام شد.")

    if is_new:
        welcome = (
            f"سلام جناب {display_name} 👋\n"
            f"به ربات LIBER کوین خوش آمدید!\n\n"
            f"💰 موجودی اولیه: {data['liber']} LIBER\n\n"
            "⚠️ همه ارزها (LIBER, Coin, Energy, Diamond) کاملاً مجازی و فقط برای بازی هستند."
        )
    else:
        welcome = f"سلام جناب {display_name} 👋\nبه ربات LIBER کوین خوش برگشتید!"

    await query.message.reply_text(welcome, reply_markup=MAIN_MENU)
    await query.message.reply_text("دسترسی سریع:", reply_markup=quick_actions_keyboard())


async def quick_action_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()
    data, _ = get_user(user)
    action = query.data

    if action == "qa_profile":
        needed = data["level"] * 100
        await query.message.reply_text(
f"""👤 پروفایل

نام: {data['name']}
⭐ Level: {data['level']}
✨ XP: {data['xp']} / {needed}
🏷 لقب: {data['title']}
💎 VIP: {data['vip'] or 'ندارد'}
🏆 لیگ فصلی: {data['league']}"""
        )

    elif action == "qa_balance":
        await query.message.reply_text(
f"""💰 موجودی شما

🪙 LIBER: {data['liber']}
💵 Coin: {data['coin']}
⚡ Energy: {data['energy']}
💎 Diamond: {data['diamond']}"""
        )

    elif action == "qa_market":
        update_market()
        await query.message.reply_text(
f"""🪙 بازار LIBER

💰 قیمت فعلی: {db['market']['price']} Coin

هر ۱ ساعت قیمت به‌صورت خودکار تغییر می‌کند.

🛒 /buy مقدار_کوین — خرید LIBER
🔴 /sell مقدار_لیبر — فروش LIBER"""
        )

    elif action == "qa_auction":
        if not db["auction"]:
            new_auction()
        a = db["auction"]
        winner_name = u(a["winner"])["name"] if a["winner"] and u(a["winner"]) else "کسی هنوز شرکت نکرده"
        remaining = datetime.fromisoformat(a["ends"]) - datetime.utcnow()
        hrs = max(0, int(remaining.total_seconds() // 3600))
        await query.message.reply_text(
f"""🏷 مزایده

🎁 آیتم: {a['item']}
💰 قیمت فعلی: {a['price']} LIBER
🏆 برنده فعلی: {winner_name}
⏳ باقی‌مانده: {hrs} ساعت

برای شرکت: /bid"""
        )


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    needed = data["level"] * 100
    await update.message.reply_text(
f"""👤 پروفایل

نام: {data['name']}
⭐ Level: {data['level']}
✨ XP: {data['xp']} / {needed}
🏷 لقب: {data['title']}
💎 VIP: {data['vip'] or 'ندارد'}
🏆 لیگ فصلی: {data['league']}
📅 عضویت: {data['created'][:10]}"""
    )


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
f"""💰 موجودی شما

🪙 LIBER: {data['liber']}
💵 Coin: {data['coin']}
⚡ Energy: {data['energy']}
💎 Diamond: {data['diamond']}"""
    )


async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_market()
    await update.message.reply_text(
f"""🪙 بازار LIBER

💰 قیمت فعلی: {db['market']['price']} Coin

هر ۱ ساعت قیمت به‌صورت خودکار تغییر می‌کند.

🛒 /buy مقدار_کوین — خرید LIBER
🔴 /sell مقدار_لیبر — فروش LIBER
🏷 مزایده — /auction"""
    )


async def buy_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    update_market()

    if not context.args:
        await update.message.reply_text("استفاده: /buy مقدار_کوین")
        return
    try:
        coin_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if coin_amount <= 0 or coin_amount > data["coin"]:
        await update.message.reply_text("موجودی Coin کافی نیست.")
        return

    price = db["market"]["price"]
    liber_amount = round(coin_amount / price, 2)
    data["coin"] -= coin_amount
    data["liber"] += liber_amount
    save_data()
    log_action(update.effective_user.id, "BUY", f"coin={coin_amount} liber={liber_amount}")
    await update.message.reply_text(f"✅ {liber_amount} LIBER خریداری شد (قیمت: {price})")


async def sell_liber(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    update_market()

    if not context.args:
        await update.message.reply_text("استفاده: /sell مقدار_لیبر")
        return
    try:
        liber_amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if liber_amount <= 0 or liber_amount > data["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    price = db["market"]["price"]
    coin_amount = round(liber_amount * price, 2)
    data["liber"] -= liber_amount
    data["coin"] += coin_amount
    save_data()
    log_action(update.effective_user.id, "SELL", f"liber={liber_amount} coin={coin_amount}")
    await update.message.reply_text(f"✅ {coin_amount} Coin دریافت شد (قیمت: {price})")


async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    now = datetime.utcnow()

    if data["last_daily"]:
        last = datetime.fromisoformat(data["last_daily"])
        if now - last < timedelta(hours=24):
            remaining = timedelta(hours=24) - (now - last)
            h, m = int(remaining.seconds // 3600), int((remaining.seconds % 3600) // 60)
            await update.message.reply_text(f"⏳ {h} ساعت و {m} دقیقه دیگه دوباره بیا.")
            return

    reward_liber = random.randint(20, 100)
    reward_energy = random.randint(5, 20)
    data["liber"] += reward_liber
    data["energy"] += reward_energy
    data["last_daily"] = str(now)
    save_data()
    add_xp(update.effective_user.id, 10)
    await update.message.reply_text(f"🎁 جایزه روزانه!\n+{reward_liber} LIBER\n+{reward_energy} Energy\n+10 XP")


async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranked = sorted(db["users"].values(), key=lambda d: (d["level"], d["xp"]), reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز کسی ثبت‌نام نکرده.")
        return
    text = "🏆 برترین بازیکنان\n\n"
    for i, d in enumerate(ranked, 1):
        text += f"{i}. {d['name']} — سطح {d['level']} ({d['xp']} XP)\n"
    await update.message.reply_text(text)


async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    count = sum(1 for d in db["users"].values() if d.get("referred_by") == user_id)
    await update.message.reply_text(
        f"👥 دعوت دوستان\n\nلینک شما:\n{link}\n\nدعوت‌شدگان: {count}\nجایزه هر نفر: 50 LIBER"
    )


# =====================================================================
# COUNTRY
# =====================================================================

BUILDING_COSTS = {"mine": 200, "factory": 300, "power_plant": 400, "farm": 150, "lab": 500}
BUILDING_NAMES = {
    "mine": "⛏ معدن", "factory": "🏭 کارخانه", "power_plant": "⚡ نیروگاه",
    "farm": "🌾 مزرعه", "lab": "🔬 آزمایشگاه",
}


async def found_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(update.effective_user)
    uid = str(user_id)

    if uid in db["countries"]:
        await update.message.reply_text("شما قبلاً کشوری ساخته‌اید.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /found نام_کشور")
        return

    name = " ".join(context.args)[:30]
    db["countries"][uid] = {
        "name": name, "flag": "🏳", "population": 1000, "satisfaction": 70,
        "budget": 1000, "tech": 1, "defense": 1, "buildings": {},
        "created": str(datetime.utcnow()),
    }
    save_data()
    log_action(user_id, "FOUND_COUNTRY", name)
    await update.message.reply_text(f"🌍 کشور «{name}» تاسیس شد!")


async def country_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    c = db["countries"].get(uid)
    if not c:
        await update.message.reply_text("هنوز کشوری نداری. /found نام_کشور")
        return

    b_text = "\n".join(
        f"  {BUILDING_NAMES.get(k, k)}: سطح {v}" for k, v in c["buildings"].items()
    ) or "  هیچ ساختمانی نیست."

    await update.message.reply_text(
f"""🌍 {c['name']} {c['flag']}

👥 جمعیت: {c['population']}
😊 رضایت: {c['satisfaction']}%
💰 بودجه: {c['budget']}
🛰 فناوری: {c['tech']}
🛡 دفاع: {c['defense']}

🏗 ساختمان‌ها:
{b_text}"""
    )


async def build(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    uid = str(user_id)
    c = db["countries"].get(uid)

    if not c:
        await update.message.reply_text("ابتدا کشور بساز: /found نام_کشور")
        return
    if not context.args or context.args[0] not in BUILDING_COSTS:
        await update.message.reply_text(f"استفاده: /build نوع\nانواع: {', '.join(BUILDING_COSTS)}")
        return

    b_type = context.args[0]
    cost = BUILDING_COSTS[b_type]
    if data["liber"] < cost:
        await update.message.reply_text(f"LIBER کافی نیست. هزینه: {cost}")
        return

    data["liber"] -= cost
    c["buildings"][b_type] = c["buildings"].get(b_type, 0) + 1
    save_data()
    add_xp(user_id, 15)
    log_action(user_id, "BUILD", b_type)
    await update.message.reply_text(f"🏗 {BUILDING_NAMES[b_type]} ساخته/ارتقا شد! (-{cost} LIBER)")


async def world_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranked = sorted(db["countries"].values(), key=lambda c: c["population"], reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز کشوری روی نقشه نیست.")
        return
    text = "🗺 نقشه جهان (برترین کشورها)\n\n"
    for i, c in enumerate(ranked, 1):
        text += f"{i}. {c['flag']} {c['name']} — 👥{c['population']} | 🛰{c['tech']} | 🛡{c['defense']}\n"
    await update.message.reply_text(text)


# =====================================================================
# BANK & INVESTMENTS
# =====================================================================

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /deposit مقدار")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if amount <= 0 or amount > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    data["liber"] -= amount
    matures = datetime.utcnow() + timedelta(hours=DEPOSIT_HOURS)
    data["deposits"].append({"amount": amount, "matures": str(matures), "claimed": False})
    save_data()
    await update.message.reply_text(
        f"🏦 {amount} LIBER سپرده شد.\nسود {DEPOSIT_RATE*100:.0f}٪ بعد از {DEPOSIT_HOURS} ساعت. با /claim بگیر."
    )


async def claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    now = datetime.utcnow()
    total, count = 0, 0
    for d in data["deposits"]:
        if not d["claimed"] and now >= datetime.fromisoformat(d["matures"]):
            payout = d["amount"] * (1 + DEPOSIT_RATE)
            data["liber"] += payout
            d["claimed"] = True
            total += payout
            count += 1
    save_data()
    if count == 0:
        await update.message.reply_text("سپرده سررسیدشده‌ای نیست.")
    else:
        await update.message.reply_text(f"✅ {count} سپرده تسویه شد. مجموع: {total:.2f} LIBER")


INVESTMENT_PROJECTS = {
    "tech": {"name": "🛰 فناوری", "min": 1.05, "max": 1.35},
    "energy": {"name": "⚡ انرژی", "min": 1.0, "max": 1.25},
    "mining": {"name": "⛏ معدن", "min": 0.9, "max": 1.5},
}


async def invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if len(context.args) < 2 or context.args[0] not in INVESTMENT_PROJECTS:
        await update.message.reply_text(f"استفاده: /invest نوع مقدار\nانواع: {', '.join(INVESTMENT_PROJECTS)}")
        return
    key = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if amount <= 0 or amount > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    proj = INVESTMENT_PROJECTS[key]
    mult = random.uniform(proj["min"], proj["max"])
    expected = round(amount * mult, 2)
    data["liber"] -= amount
    matures = datetime.utcnow() + timedelta(hours=12)
    data["investments"].append({"project": key, "amount": amount, "expected": expected, "matures": str(matures), "claimed": False})
    save_data()
    await update.message.reply_text(f"📈 سرمایه‌گذاری در {proj['name']} ثبت شد. نتیجه بعد از ۱۲ ساعت — /claim_invest")


async def claim_invest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    now = datetime.utcnow()
    total, count = 0, 0
    for inv in data["investments"]:
        if not inv["claimed"] and now >= datetime.fromisoformat(inv["matures"]):
            data["liber"] += inv["expected"]
            inv["claimed"] = True
            total += inv["expected"]
            count += 1
    save_data()
    if count == 0:
        await update.message.reply_text("سرمایه‌گذاری سررسیدشده‌ای نیست.")
    else:
        await update.message.reply_text(f"✅ {count} سرمایه‌گذاری تسویه شد. مجموع: {total:.2f} LIBER")


# =====================================================================
# MISSIONS & ACHIEVEMENTS
# =====================================================================

DAILY_MISSIONS = [
    ("خرید در بازار", 30, 10),
    ("ساخت یک ساختمان", 50, 20),
    ("جمع‌آوری جایزه روزانه", 20, 5),
]


async def missions_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎯 مأموریت‌های روزانه\n\n"
    for i, (desc, r_liber, r_xp) in enumerate(DAILY_MISSIONS, 1):
        text += f"{i}. {desc} (+{r_liber} LIBER, +{r_xp} XP)\n"
    text += "\nبرای تکمیل: /complete شماره"
    await update.message.reply_text(text)


async def complete_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /complete شماره")
        return
    try:
        idx = int(context.args[0]) - 1
        desc, r_liber, r_xp = DAILY_MISSIONS[idx]
    except (ValueError, IndexError):
        await update.message.reply_text("شماره نامعتبر است.")
        return

    data["liber"] += r_liber
    save_data()
    add_xp(update.effective_user.id, r_xp)
    await update.message.reply_text(f"✅ «{desc}» تکمیل شد! +{r_liber} LIBER, +{r_xp} XP")


async def achievements_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["achievements"]:
        await update.message.reply_text("هنوز دستاوردی نداری.")
        return
    text = "🎖 دستاوردهای شما\n\n" + "\n".join(f"🏅 {a}" for a in data["achievements"])
    await update.message.reply_text(text)


# =====================================================================
# ALLIANCES
# =====================================================================

async def create_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /create_alliance نام")
        return
    name = " ".join(context.args)[:30]
    if name in db["alliances"]:
        await update.message.reply_text("این نام قبلاً استفاده شده.")
        return
    for a in db["alliances"].values():
        if user_id in a["members"]:
            await update.message.reply_text("قبلاً عضو یک اتحادی.")
            return

    db["alliances"][name] = {"leader": user_id, "treasury": 0, "members": [user_id], "created": str(datetime.utcnow())}
    save_data()
    await update.message.reply_text(f"🤝 اتحاد «{name}» ساخته شد!")


async def join_alliance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    get_user(update.effective_user)
    for a in db["alliances"].values():
        if user_id in a["members"]:
            await update.message.reply_text("قبلاً عضو یک اتحادی.")
            return
    if not context.args:
        await update.message.reply_text("استفاده: /join_alliance نام")
        return
    name = " ".join(context.args)
    a = db["alliances"].get(name)
    if not a:
        await update.message.reply_text("اتحادی با این نام نیست.")
        return
    a["members"].append(user_id)
    save_data()
    await update.message.reply_text(f"🤝 پیوستی به «{name}»!")


async def alliance_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    for name, a in db["alliances"].items():
        if user_id in a["members"]:
            members_txt = "\n".join(f"  • {u(m)['name'] if u(m) else m}" for m in a["members"])
            await update.message.reply_text(
                f"🤝 اتحاد: {name}\n💰 خزانه: {a['treasury']}\n👥 اعضا:\n{members_txt}"
            )
            return
    await update.message.reply_text("عضو هیچ اتحادی نیستی.\n/create_alliance نام\n/join_alliance نام")


# =====================================================================
# SHOP & VIP
# =====================================================================

SHOP_ITEMS = {
    "avatar_gold": {"name": "🖼 آواتار طلایی", "cost": 300},
    "frame_diamond": {"name": "🎨 قاب الماسی", "cost": 500},
    "title_legend": {"name": "🏷 لقب افسانه‌ای", "cost": 800},
    "energy_pack": {"name": "⚡ بسته انرژی (+50)", "cost": 100},
}

VIP_TIERS = {
    "silver": {"name": "⭐ نقره‌ای", "cost": 1000, "days": 7},
    "gold": {"name": "🥇 طلایی", "cost": 2500, "days": 7},
    "diamond": {"name": "💎 الماسی", "cost": 5000, "days": 7},
}


async def shop_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏪 فروشگاه\n\n"
    for k, item in SHOP_ITEMS.items():
        text += f"{item['name']} — {item['cost']} LIBER — /buy_item {k}\n"
    text += "\n💎 VIP:\n"
    for k, tier in VIP_TIERS.items():
        text += f"{tier['name']} — {tier['cost']} LIBER / {tier['days']} روز — /buy_vip {k}\n"
    await update.message.reply_text(text)


async def buy_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SHOP_ITEMS:
        await update.message.reply_text("آیتم نامعتبر. /shop رو ببین.")
        return
    key = context.args[0]
    item = SHOP_ITEMS[key]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    if key == "energy_pack":
        data["energy"] += 50
    save_data()
    await update.message.reply_text(f"✅ {item['name']} خریداری شد!")


async def buy_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in VIP_TIERS:
        await update.message.reply_text(f"استفاده: /buy_vip نوع\nانواع: {', '.join(VIP_TIERS)}")
        return
    key = context.args[0]
    tier = VIP_TIERS[key]
    if data["liber"] < tier["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= tier["cost"]
    data["vip"] = key
    data["vip_expires"] = str(datetime.utcnow() + timedelta(days=tier["days"]))
    save_data()
    await update.message.reply_text(f"💎 {tier['name']} فعال شد تا {data['vip_expires'][:10]}!")


async def vip_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["vip"]:
        await update.message.reply_text("VIP نیستی. /shop رو ببین.")
        return
    active = datetime.utcnow() < datetime.fromisoformat(data["vip_expires"])
    tier_name = VIP_TIERS.get(data["vip"], {}).get("name", data["vip"])
    await update.message.reply_text(
        f"💎 VIP: {tier_name}\nوضعیت: {'✅ فعال' if active else '❌ منقضی'}\nتا: {data['vip_expires'][:10]}"
    )


# =====================================================================
# LEAGUE
# =====================================================================

LEAGUE_NAMES = {
    "bronze": "🥉 برنز", "silver": "🥈 نقره", "gold": "🥇 طلا", "platinum": "🔷 پلاتینیوم",
    "diamond": "💎 الماس", "titan": "🔱 تایتان", "legendary": "👑 افسانه‌ای", "galactic": "🌌 کهکشانی",
}


async def league_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
        f"🏆 لیگ فعلی: {LEAGUE_NAMES[data['league']]}\n✨ امتیاز فصلی: {data['season_points']}"
    )


async def season_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranked = sorted(db["users"].values(), key=lambda d: d["season_points"], reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز امتیازی ثبت نشده.")
        return
    text = "🏆 برترین‌های فصل\n\n"
    for i, d in enumerate(ranked, 1):
        text += f"{i}. {d['name']} — {LEAGUE_NAMES[d['league']]} ({d['season_points']})\n"
    await update.message.reply_text(text)


# =====================================================================
# MINI-GAMES
# =====================================================================

async def wheel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /wheel مقدار")
        return
    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if bet <= 0 or bet > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    outcomes = [0, 0.5, 1, 1.5, 2, 3, 5]
    weights = [25, 20, 20, 15, 10, 7, 3]
    mult = random.choices(outcomes, weights=weights, k=1)[0]
    result = round(bet * mult, 2)
    data["liber"] = data["liber"] - bet + result
    save_data()
    add_season_points(update.effective_user.id, max(0, int(result - bet)))
    emoji = "🎉" if mult >= 1 else "😔"
    await update.message.reply_text(f"🎰 ضریب: x{mult}\nنتیجه: {result} LIBER {emoji}")


async def lucky(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /lucky مقدار")
        return
    try:
        bet = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if bet <= 0 or bet > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    win = random.random() < 0.45
    result = bet * 2 if win else 0
    data["liber"] = data["liber"] - bet + result
    save_data()
    await update.message.reply_text(f"🍀 بردی! +{result} LIBER" if win else f"❌ باختی. -{bet} LIBER")


async def treasure(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    now = datetime.utcnow()
    if data["chest_cooldown"]:
        last = datetime.fromisoformat(data["chest_cooldown"])
        if now - last < timedelta(hours=6):
            remaining = timedelta(hours=6) - (now - last)
            mins = int(remaining.seconds // 60)
            await update.message.reply_text(f"⏳ {mins} دقیقه دیگر بیا.")
            return
    reward = random.randint(10, 60)
    data["liber"] += reward
    data["chest_cooldown"] = str(now)
    save_data()
    await update.message.reply_text(f"🎁 گنج پیدا شد! +{reward} LIBER")


CHESTS = {
    "free": {"name": "🎁 رایگان", "cost": 0, "min": 5, "max": 30},
    "bronze": {"name": "🥉 برنزی", "cost": 100, "min": 50, "max": 150},
    "silver": {"name": "🥈 نقره‌ای", "cost": 300, "min": 150, "max": 450},
    "gold": {"name": "🥇 طلایی", "cost": 700, "min": 400, "max": 1100},
    "diamond": {"name": "💎 الماسی", "cost": 1500, "min": 900, "max": 2500},
}


async def chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in CHESTS:
        await update.message.reply_text(f"استفاده: /chest نوع\nانواع: {', '.join(CHESTS)}")
        return
    c = CHESTS[context.args[0]]
    if data["liber"] < c["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    reward = random.randint(c["min"], c["max"])
    data["liber"] = data["liber"] - c["cost"] + reward
    save_data()
    await update.message.reply_text(f"{c['name']} باز شد! +{reward} LIBER (هزینه {c['cost']})")


async def games_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
"""🎮 بازی‌ها

🎰 /wheel مقدار — گردونه
🍀 /lucky مقدار — شیر یا خط
🎁 /treasure — گنج رایگان (۶ ساعت)
📦 /chest نوع — صندوق (free/bronze/silver/gold/diamond)
🏆 /league — لیگ فصلی
📊 /season_top — رتبه فصل"""
    )


# =====================================================================
# AUCTION (single shared auction stored in db["auction"])
# =====================================================================

AUCTION_ITEMS = ["🎁 جعبه طلایی", "🖼 قاب کهکشانی", "🏷 لقب افسانه‌ای", "💎 آواتار الماسی", "🎖 مدال ویژه فصل"]
AUCTION_STEP = 10


def new_auction():
    db["auction"] = {
        "item": random.choice(AUCTION_ITEMS), "price": 50, "winner": None,
        "ends": str(datetime.utcnow() + timedelta(hours=12)),
    }
    save_data()


async def auction_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["auction"]:
        new_auction()
    a = db["auction"]
    winner_name = u(a["winner"])["name"] if a["winner"] and u(a["winner"]) else "کسی هنوز شرکت نکرده"
    remaining = datetime.fromisoformat(a["ends"]) - datetime.utcnow()
    hrs = max(0, int(remaining.total_seconds() // 3600))
    await update.message.reply_text(
f"""🏷 مزایده

🎁 آیتم: {a['item']}
💰 قیمت فعلی: {a['price']} LIBER
🏆 برنده فعلی: {winner_name}
⏳ باقی‌مانده: {hrs} ساعت

برای شرکت: /bid"""
    )


async def bid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if not db["auction"]:
        new_auction()
    a = db["auction"]

    if datetime.utcnow() >= datetime.fromisoformat(a["ends"]):
        if a["winner"]:
            add_season_points(a["winner"], 100)
        new_auction()
        await update.message.reply_text("⏳ مزایده قبلی تمام شد، جدیدش شروع شد. /bid رو دوباره بزن.")
        return

    next_price = a["price"] + AUCTION_STEP
    if data["liber"] < next_price:
        await update.message.reply_text(f"موجودی کافی نیست. نیاز به {next_price} LIBER داری.")
        return

    if a["winner"] and a["winner"] != user_id and u(a["winner"]):
        u(a["winner"])["liber"] += a["price"]

    data["liber"] -= next_price
    a["price"] = next_price
    a["winner"] = user_id
    save_data()
    await update.message.reply_text(f"✅ الان برنده فعلی «{a['item']}» هستی! قیمت: {next_price} LIBER")


# =====================================================================
# WORLD EVENTS (background job)
# =====================================================================

WORLD_EVENTS = [
    {"name": "🎉 جشنواره جهانی", "desc": "۲۴ ساعت XP دوبرابر.", "effect": "double_xp"},
    {"name": "📉 رکود اقتصادی", "desc": "قیمت بازار موقتاً کاهش می‌یابد.", "effect": "crash"},
    {"name": "💰 باران LIBER", "desc": "همه کاربران فعال ۳۰ LIBER می‌گیرند.", "effect": "rain"},
]


async def world_event_job(context: ContextTypes.DEFAULT_TYPE):
    event = random.choice(WORLD_EVENTS)
    db["events"].append({"name": event["name"], "desc": event["desc"], "at": str(datetime.utcnow())})
    db["events"] = db["events"][-30:]

    if event["effect"] == "rain":
        for d in db["users"].values():
            if not d["banned"]:
                d["liber"] += 30
    elif event["effect"] == "crash":
        db["market"]["price"] = max(10, round(db["market"]["price"] * 0.85))

    save_data()
    logger.info(f"world event: {event['name']}")

    for uid_str, d in db["users"].items():
        if d["banned"]:
            continue
        try:
            await context.bot.send_message(int(uid_str), f"🌍 رویداد جهانی: {event['name']}\n{event['desc']}")
        except Exception:
            pass


async def events_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["events"]:
        await update.message.reply_text("رویدادی ثبت نشده.")
        return
    text = "📅 آخرین رویدادها\n\n"
    for e in db["events"][-5:]:
        text += f"{e['name']} — {e['at'][:16]}\n{e['desc']}\n\n"
    await update.message.reply_text(text)


async def market_fluctuation_job(context: ContextTypes.DEFAULT_TYPE):
    update_market()


# =====================================================================
# GLOBAL PROJECTS & BLACK MARKET
# =====================================================================

async def global_project_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🏛 پروژه‌های جهانی\n\n"
    for key, p in db["global_projects"].items():
        pct = min(100, round(p["contributed"] / p["goal"] * 100, 1))
        status = "✅ تکمیل" if p["done"] else f"{pct}%"
        text += f"{p['name']} — {p['contributed']}/{p['goal']} ({status})\n  /contribute {key} مقدار\n\n"
    await update.message.reply_text(text)


async def contribute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if len(context.args) < 2 or context.args[0] not in db["global_projects"]:
        await update.message.reply_text(f"استفاده: /contribute نوع مقدار\nانواع: {', '.join(db['global_projects'])}")
        return
    key = context.args[0]
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if amount <= 0 or amount > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    p = db["global_projects"][key]
    data["liber"] -= amount
    p["contributed"] += amount

    just_done = False
    if p["contributed"] >= p["goal"] and not p["done"]:
        p["done"] = True
        just_done = True
        for d in db["users"].values():
            if not d["banned"]:
                d["liber"] += p["reward"]

    save_data()
    await update.message.reply_text(f"✅ {amount} LIBER به «{p['name']}» اضافه شد.")

    if just_done:
        for uid_str, d in db["users"].items():
            if d["banned"]:
                continue
            try:
                await context.bot.send_message(
                    int(uid_str), f"🎉 پروژه «{p['name']}» تکمیل شد! همه +{p['reward']} LIBER گرفتند."
                )
            except Exception:
                pass


BLACK_MARKET_ITEMS = {
    "rare_tech": {"name": "🧬 فناوری کمیاب", "cost": 3000},
    "legend_medal": {"name": "🎖 مدال افسانه‌ای", "cost": 5000},
    "ancient_map": {"name": "🗺 نقشه باستانی", "cost": 4000},
}


async def black_market_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🕵 بازار سیاه\n\n"
    for k, item in BLACK_MARKET_ITEMS.items():
        text += f"{item['name']} — {item['cost']} LIBER — /bm_buy {k}\n"
    await update.message.reply_text(text)


async def bm_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in BLACK_MARKET_ITEMS:
        await update.message.reply_text("آیتم نامعتبر.")
        return
    item = BLACK_MARKET_ITEMS[context.args[0]]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    save_data()
    await update.message.reply_text(f"🕵 {item['name']} خریداری شد!")


# =====================================================================
# WITHDRAWAL (manual admin review only — no automatic crypto payout)
# =====================================================================

async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)

    if len(context.args) < 2:
        await update.message.reply_text(f"استفاده: /withdraw مقدار آدرس_کیف‌پول\nحداقل: {MIN_WITHDRAW} LIBER")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.")
        return
    wallet = context.args[1]

    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"حداقل برداشت {MIN_WITHDRAW} LIBER است.")
        return
    if amount > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    data["liber"] -= amount
    req = {"user_id": user_id, "amount": amount, "wallet": wallet, "status": "pending", "at": str(datetime.utcnow())}
    db["withdrawals"].append(req)
    save_data()

    await update.message.reply_text("📤 درخواست ثبت شد و منتظر بررسی ادمین است. /withdrawals رو ببین.")

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📥 درخواست برداشت جدید\nکاربر: {user_id}\nمبلغ: {amount} LIBER\nکیف‌پول: {wallet}\n\n"
                f"/approve {user_id}   /reject {user_id}",
            )
        except Exception:
            pass


async def withdrawals_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    mine = [w for w in db["withdrawals"] if w["user_id"] == user_id]
    if not mine:
        await update.message.reply_text("درخواستی ثبت نکرده‌ای.")
        return
    labels = {"pending": "⏳ در انتظار", "approved": "✅ تایید", "rejected": "❌ رد شده"}
    text = "📜 درخواست‌های برداشت شما\n\n"
    for w in mine[-10:]:
        text += f"{w['amount']} LIBER — {labels.get(w['status'], w['status'])}\n"
    await update.message.reply_text(text)


async def approve_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /approve USER_ID")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه نامعتبر.")
        return

    for w in db["withdrawals"]:
        if w["user_id"] == target and w["status"] == "pending":
            w["status"] = "approved"
            save_data()
            await update.message.reply_text(f"✅ تایید شد. پرداخت واقعی باید دستی و خارج از ربات انجام شود.")
            try:
                await context.bot.send_message(target, f"✅ درخواست برداشت {w['amount']} LIBER تایید شد.")
            except Exception:
                pass
            return
    await update.message.reply_text("درخواست در انتظاری پیدا نشد.")


async def reject_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /reject USER_ID")
        return
    try:
        target = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شناسه نامعتبر.")
        return

    for w in db["withdrawals"]:
        if w["user_id"] == target and w["status"] == "pending":
            w["status"] = "rejected"
            if u(target):
                u(target)["liber"] += w["amount"]
            save_data()
            await update.message.reply_text("❌ رد شد و مبلغ بازگردانده شد.")
            try:
                await context.bot.send_message(target, f"❌ درخواست برداشت رد شد و {w['amount']} LIBER بازگشت.")
            except Exception:
                pass
            return
    await update.message.reply_text("درخواست در انتظاری پیدا نشد.")


async def referral_top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = {}
    for d in db["users"].values():
        ref = d.get("referred_by")
        if ref:
            counts[ref] = counts.get(ref, 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز کسی دعوتی ثبت نکرده.")
        return
    text = "👥 برترین دعوت‌کنندگان\n\n"
    for i, (ref_id, count) in enumerate(ranked, 1):
        name = u(ref_id)["name"] if u(ref_id) else str(ref_id)
        text += f"{i}. {name} — {count} دعوت\n"
    await update.message.reply_text(text)


async def vip_bonus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Idea: an exclusive daily bonus only VIP members can claim, separate from /daily."""
    data, _ = get_user(update.effective_user)
    if not data["vip"]:
        await update.message.reply_text("این جایزه فقط برای اعضای VIP است. /shop رو ببین.")
        return
    if data["vip_expires"] and datetime.utcnow() >= datetime.fromisoformat(data["vip_expires"]):
        await update.message.reply_text("اشتراک VIP شما منقضی شده. /shop رو ببین.")
        return

    now = datetime.utcnow()
    last = data.get("vip_bonus_last")
    if last and now - datetime.fromisoformat(last) < timedelta(hours=24):
        remaining = timedelta(hours=24) - (now - datetime.fromisoformat(last))
        h = int(remaining.seconds // 3600)
        await update.message.reply_text(f"⏳ {h} ساعت دیگه دوباره بیا.")
        return

    reward = random.randint(80, 200)
    data["liber"] += reward
    data["vip_bonus_last"] = str(now)
    save_data()
    await update.message.reply_text(f"💎 جایزه ویژه VIP دریافت شد! +{reward} LIBER")




async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ دسترسی ندارید.")
        return
    await update.message.reply_text("👑 پنل مدیریت LIBER", reply_markup=admin_keyboard())


async def admin_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not is_admin(query.from_user.id):
        await query.answer("⛔ دسترسی ندارید", show_alert=True)
        return
    await query.answer()
    action = query.data

    if action == "a_dash":
        total_users = len(db["users"])
        total_liber = sum(d["liber"] for d in db["users"].values())
        pending = sum(1 for w in db["withdrawals"] if w["status"] == "pending")
        text = (
            f"📊 داشبورد\n\nکاربران: {total_users}\nکشورها: {len(db['countries'])}\n"
            f"مجموع LIBER: {total_liber:.2f}\nقیمت بازار: {db['market']['price']}\n"
            f"برداشت در انتظار: {pending}"
        )
        await query.edit_message_text(text, reply_markup=admin_keyboard())

    elif action == "a_users":
        rows = list(db["users"].values())[-15:]
        text = "👥 آخرین کاربران\n\n" + "\n".join(
            f"{'🚫' if r['banned'] else '✅'} {r['name']} (ID:{r['id']}) — سطح {r['level']}" for r in rows
        )
        await query.edit_message_text(text or "کاربری نیست.", reply_markup=admin_keyboard())

    elif action == "a_econ":
        hist = db["market"]["history"][-10:]
        text = "💹 تاریخچه قیمت\n\n" + "\n".join(f"{h['price']} — {h['at'][:16]}" for h in hist)
        await query.edit_message_text(text or "داده‌ای نیست.", reply_markup=admin_keyboard())

    elif action == "a_withdraw":
        pending = [w for w in db["withdrawals"] if w["status"] == "pending"][:10]
        if not pending:
            text = "درخواست در انتظاری نیست."
        else:
            text = "📤 درخواست‌های در انتظار\n\n" + "\n".join(
                f"کاربر {w['user_id']} — {w['amount']} LIBER — /approve {w['user_id']} یا /reject {w['user_id']}"
                for w in pending
            )
        await query.edit_message_text(text, reply_markup=admin_keyboard())

    elif action == "a_logs":
        rows = db["logs"][-10:]
        text = "📋 آخرین لاگ‌ها\n\n" + "\n".join(
            f"[{r['at'][:16]}] {r['user_id']} — {r['action']} {r['detail']}" for r in rows
        )
        await query.edit_message_text(text or "لاگی نیست.", reply_markup=admin_keyboard())

    elif action == "a_broadcast":
        await query.edit_message_text("برای پیام همگانی: /broadcast متن پیام", reply_markup=admin_keyboard())


async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not context.args:
        return
    target = u(context.args[0])
    if target:
        target["banned"] = True
        save_data()
        await update.message.reply_text(f"🚫 {context.args[0]} بن شد.")


async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not context.args:
        return
    target = u(context.args[0])
    if target:
        target["banned"] = False
        save_data()
        await update.message.reply_text(f"✅ {context.args[0]} آن‌بن شد.")


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن پیام")
        return
    msg = " ".join(context.args)
    sent, failed = 0, 0
    for uid_str, d in db["users"].items():
        if d["banned"]:
            continue
        try:
            await context.bot.send_message(int(uid_str), f"📢 {msg}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ ارسال شد به {sent} کاربر ({failed} ناموفق)")


# =====================================================================
# SETTINGS / HELP
# =====================================================================

async def settings_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⚙ تنظیمات\n\n🔔 اعلان‌ها: فعال\n🌐 زبان: فارسی")


async def help_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
"""❓ راهنما

/start /profile /موجودی
/buy /sell مقدار
/daily — جایزه روزانه
/found /country /build نوع — کشور
/deposit /claim — بانک
/invest /claim_invest — سرمایه‌گذاری
/missions /complete شماره — مأموریت
/achievements — دستاورد
/create_alliance /join_alliance /alliance
/shop /buy_item /buy_vip /vip
/wheel /lucky /treasure /chest — بازی
/auction /bid — مزایده
/league /season_top
/globalproject /contribute — پروژه جهانی
/worldmap — نقشه جهان
/blackmarket /bm_buy — بازار سیاه
/invite — دعوت دوستان
/withdraw /withdrawals — برداشت
/events — رویدادها
/referral_top — برترین دعوت‌کنندگان
/vip_bonus — جایزه روزانه ویژه VIP
/top — رتبه‌بندی"""
    )


# =====================================================================
# MENU ROUTER (matches the reply-keyboard buttons)
# =====================================================================

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    routes = {
        "👤 پروفایل": profile,
        "💰 موجودی": balance,
        "🪙 بازار LIBER": market_menu,
        "🌍 کشور": country_view,
        "🏦 بانک": claim,
        "🏪 فروشگاه": shop_view,
        "🎯 مأموریت‌ها": missions_view,
        "🎮 بازی‌ها": games_menu,
        "🏷 مزایده": auction_view,
        "🤝 اتحاد": alliance_view,
        "⚔️ رقابت": league_view,
        "💎 اشتراک VIP": vip_view,
        "👥 دعوت دوستان": invite,
        "📤 برداشت": withdrawals_view,
        "🏛 پروژه جهانی": global_project_view,
        "🗺 نقشه جهان": world_map,
        "🕵 بازار سیاه": black_market_view,
        "🎖 دستاوردها": achievements_view,
        "⚙ تنظیمات": settings_view,
        "❓ راهنما": help_view,
    }
    handler = routes.get(update.message.text)
    if handler:
        await handler(update, context)
    else:
        await update.message.reply_text("این بخش به‌زودی اضافه می‌شود. 🚧", reply_markup=MAIN_MENU)


# =====================================================================
# APP SETUP
# =====================================================================

def build_app():
    if not TOKEN or TOKEN == "TOKEN_HERE":
        sys.exit(
            "❌ TOKEN تنظیم نشده.\n"
            "export BOT_TOKEN=توکن_واقعی   (یا مقدار TOKEN بالای فایل را عوض کن)"
        )

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(check_join_cb, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(quick_action_cb, pattern="^qa_"))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("buy", buy_liber))
    app.add_handler(CommandHandler("sell", sell_liber))
    app.add_handler(CommandHandler("daily", daily))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("invite", invite))

    app.add_handler(CommandHandler("found", found_country))
    app.add_handler(CommandHandler("country", country_view))
    app.add_handler(CommandHandler("build", build))
    app.add_handler(CommandHandler("worldmap", world_map))

    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("claim", claim))
    app.add_handler(CommandHandler("invest", invest))
    app.add_handler(CommandHandler("claim_invest", claim_invest))

    app.add_handler(CommandHandler("missions", missions_view))
    app.add_handler(CommandHandler("complete", complete_mission))
    app.add_handler(CommandHandler("achievements", achievements_view))

    app.add_handler(CommandHandler("create_alliance", create_alliance))
    app.add_handler(CommandHandler("join_alliance", join_alliance))
    app.add_handler(CommandHandler("alliance", alliance_view))

    app.add_handler(CommandHandler("shop", shop_view))
    app.add_handler(CommandHandler("buy_item", buy_item))
    app.add_handler(CommandHandler("buy_vip", buy_vip))
    app.add_handler(CommandHandler("vip", vip_view))

    app.add_handler(CommandHandler("league", league_view))
    app.add_handler(CommandHandler("season_top", season_top))

    app.add_handler(CommandHandler("wheel", wheel))
    app.add_handler(CommandHandler("lucky", lucky))
    app.add_handler(CommandHandler("treasure", treasure))
    app.add_handler(CommandHandler("chest", chest))
    app.add_handler(CommandHandler("games", games_menu))

    app.add_handler(CommandHandler("auction", auction_view))
    app.add_handler(CommandHandler("bid", bid))

    app.add_handler(CommandHandler("globalproject", global_project_view))
    app.add_handler(CommandHandler("contribute", contribute))
    app.add_handler(CommandHandler("blackmarket", black_market_view))
    app.add_handler(CommandHandler("bm_buy", bm_buy))

    app.add_handler(CommandHandler("withdraw", withdraw))
    app.add_handler(CommandHandler("withdrawals", withdrawals_view))
    app.add_handler(CommandHandler("approve", approve_withdraw))
    app.add_handler(CommandHandler("reject", reject_withdraw))

    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(admin_cb, pattern="^a_"))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CommandHandler("events", events_view))
    app.add_handler(CommandHandler("referral_top", referral_top))
    app.add_handler(CommandHandler("vip_bonus", vip_bonus))
    app.add_handler(CommandHandler("settings", settings_view))
    app.add_handler(CommandHandler("help", help_view))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router))

    job_queue = app.job_queue
    if job_queue is None:
        sys.exit('❌ JobQueue در دسترس نیست.\npip install "python-telegram-bot[job-queue]"==21.*')
    job_queue.run_repeating(market_fluctuation_job, interval=1800, first=60)
    job_queue.run_repeating(world_event_job, interval=21600, first=300)

    return app


if __name__ == "__main__":
    logger.info("LIBER UNIVERSE bot starting...")
    application = build_app()
    application.run_polling()
