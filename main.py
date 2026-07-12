"""
LIBER — Main Bot (Entertainment Simulation Edition)
====================================================
Two-file project:
    main.py   -> this file: core bot, all player-facing features
    admin.py  -> admin-only panel, imports shared helpers from this file

IMPORTANT (read before deploying):
- All currencies (LIBER, Coin, Energy, Diamond, Medal) are 100% virtual,
  used only for in-game progression and fun.
- Telegram Stars (XTR) purchases in this file are real, official Telegram
  monetization for digital goods (subscriptions/cosmetics) — standard bot
  functionality, handled through PreCheckoutQueryHandler.
- The TON withdrawal flow only COLLECTS a wallet address and creates a
  pending request. No blockchain transaction is ever sent automatically.
  An admin must manually verify and pay out outside the bot, then mark
  the request approved/rejected from admin.py.

Setup:
    pip install "python-telegram-bot[job-queue]"==21.6
    pip install APScheduler
    export BOT_TOKEN=your:token         (never hardcode a real token)
    python main.py
"""

import os
import sys
import json
import random
import logging
from datetime import datetime, timedelta

from telegram import (
    Update,
    ReplyKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)

# =====================================================================
# CONFIG
# =====================================================================

TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y" 
CHANNEL = "@Libercoin1"
ADMIN_IDS = [6188951798]
DATA_FILE = "liber_data.json"

MIN_WITHDRAW_LIBER = 1500
DEPOSIT_RATE = 0.02
DEPOSIT_HOURS = 24
XP_PER_LEVEL = 100

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger("liber")

# =====================================================================
# DATABASE (single JSON file)
# =====================================================================

db = {
    "users": {},
    "clans": {},
    "market": {"price": 100.0, "history": [], "updated": str(datetime.utcnow())},
    "auction": None,
    "gift_codes": {},
    "withdrawals": [],
    "logs": [],
    "events": [],
    "news": [],
    "tournament": {"started_at": str(datetime.utcnow()), "length_days": 14},
    "p2p_offers": [],
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
    db["logs"] = db["logs"][-500:]
    save_data()


# =====================================================================
# USER HELPERS
# =====================================================================

JOBS = {
    "none": {"name": "بیکار", "income": 0},
    "miner": {"name": "⛏ کارگر معدن", "income": 15},
    "farmer": {"name": "🌾 کشاورز", "income": 12},
    "trader": {"name": "💹 معامله‌گر", "income": 20},
    "engineer": {"name": "🔧 مهندس", "income": 25},
    "banker": {"name": "🏦 بانکدار", "income": 30},
}

SUBSCRIPTION_TIERS = {
    "silver": {
        "name": "🥈 Silver", "cost_liber": 1000, "stars": 60, "days": 30,
        "income_bonus": 0.10, "xp_bonus": 0.10,
        "perks": "🎁 صندوق اضافه روزانه، ⚡ ۲۰٪ انرژی بیشتر، 📜 یک مأموریت اضافه",
    },
    "gold": {
        "name": "🥇 Gold", "cost_liber": 2500, "stars": 150, "days": 30,
        "income_bonus": 0.20, "xp_bonus": 0.20,
        "perks": "همه مزایای Silver + 🏙 ارتقای سریع‌تر شهر، 🎟 بلیت مسابقه هفتگی",
    },
    "diamond": {
        "name": "💎 Diamond", "cost_liber": 5000, "stars": 300, "days": 30,
        "income_bonus": 0.35, "xp_bonus": 0.35,
        "perks": "همه مزایای Gold + 📦 صندوق الماسی هفتگی، 🐉 یک Pet ویژه",
    },
    "titan": {
        "name": "👑 Titan", "cost_liber": 9000, "stars": 550, "days": 30,
        "income_bonus": 0.50, "xp_bonus": 0.50,
        "perks": "همه مزایای Diamond + 🏆 لیگ Titan، 👑 نشان ویژه، 🎨 قاب متحرک",
    },
}


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
            "medal": 0,
            "level": 1,
            "xp": 0,
            "title": "تازه‌وارد",
            "job": "none",
            "city_level": 1,
            "buildings": {"bank": 0, "mine": 0, "factory": 0, "power_plant": 0, "warehouse": 0},
            "bio": "",
            "pet": None,
            "frame": "normal",
            "sub_tier": None,
            "sub_expires": None,
            "banned": False,
            "warn_count": 0,
            "last_daily": None,
            "last_weekly": None,
            "last_job_collect": None,
            "deposits": [],
            "achievements": [],
            "clan_id": None,
            "referred_by": referred_by,
            "ref_count": 0,
            "rank_points": 0,
            "matches_played": 0,
            "matches_won": 0,
            "trade_count": 0,
            "chest_count": 0,
            "season_points": 0,
            "league": "bronze",
            "chest_cooldown": None,
            "created": str(datetime.utcnow()),
        }
        if referred_by:
            ref_user = db["users"].get(str(referred_by))
            if ref_user:
                ref_user["ref_count"] += 1
        save_data()
        log_action(user.id, "REGISTER", user.username or "")

    return db["users"][uid], is_new


def u(user_id):
    return db["users"].get(str(user_id))


def is_admin(user_id) -> bool:
    return user_id in ADMIN_IDS


def sub_bonus(user_id, field):
    user = u(user_id)
    if not user or not user["sub_tier"]:
        return 0
    if user["sub_expires"] and datetime.utcnow() > datetime.fromisoformat(user["sub_expires"]):
        user["sub_tier"] = None
        user["sub_expires"] = None
        save_data()
        return 0
    return SUBSCRIPTION_TIERS.get(user["sub_tier"], {}).get(field, 0)


def add_currency(user_id, liber=0, coin=0, energy=0, diamond=0, medal=0):
    user = u(user_id)
    if not user:
        return
    if liber > 0:
        liber = liber * (1 + sub_bonus(user_id, "income_bonus"))
    user["liber"] += liber
    user["coin"] += coin
    user["energy"] += energy
    user["diamond"] += diamond
    user["medal"] += medal
    save_data()


MEDAL_LEVELS = {5: "🥉 سطح ۵", 10: "🥈 سطح ۱۰", 20: "🥇 سطح ۲۰", 40: "🏆 سطح ۴۰"}


def add_xp(user_id, amount):
    user = u(user_id)
    if not user:
        return
    amount = int(amount * (1 + sub_bonus(user_id, "xp_bonus")))
    user["xp"] += amount
    needed = user["level"] * XP_PER_LEVEL
    while user["xp"] >= needed:
        user["xp"] -= needed
        user["level"] += 1
        needed = user["level"] * XP_PER_LEVEL
        medal = MEDAL_LEVELS.get(user["level"])
        if medal and medal not in user["achievements"]:
            user["achievements"].append(medal)
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


LEAGUE_NAMES = {
    "bronze": "🥉 برنز", "silver": "🥈 نقره", "gold": "🥇 طلا", "platinum": "🔷 پلاتینیوم",
    "diamond": "💎 الماس", "titan": "🔱 تایتان", "legendary": "👑 افسانه‌ای", "galactic": "🌌 کهکشانی",
}

MAX_WARNINGS = 3
_last_action_time = {}
ANTI_SPAM_COOLDOWN_SECONDS = 0.6


async def warn_user(context, user_id, reason):
    """Adds a warning; auto-bans after MAX_WARNINGS. Notifies the user and all admins."""
    user = u(user_id)
    if not user:
        return
    user["warn_count"] += 1
    save_data()
    log_action(user_id, "WARNING", f"{reason} ({user['warn_count']}/{MAX_WARNINGS})")

    if user["warn_count"] >= MAX_WARNINGS:
        user["banned"] = True
        save_data()
        try:
            await context.bot.send_message(user_id, "🚫 حساب شما به دلیل دریافت ۳ اخطار مسدود شد.")
        except Exception:
            pass
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, f"🚫 کاربر {user_id} پس از ۳ اخطار خودکار مسدود شد.\nدلیل آخر: {reason}")
            except Exception:
                pass
    else:
        try:
            await context.bot.send_message(
                user_id, f"⚠️ اخطار {user['warn_count']}/{MAX_WARNINGS}: {reason}\nبا رسیدن به {MAX_WARNINGS} اخطار، حساب مسدود می‌شود."
            )
        except Exception:
            pass


def anti_spam_flag(user_id) -> bool:
    """Returns True if this action is happening suspiciously fast (possible script/bot click)."""
    now = datetime.utcnow().timestamp()
    last = _last_action_time.get(user_id, 0)
    _last_action_time[user_id] = now
    return (now - last) < ANTI_SPAM_COOLDOWN_SECONDS


async def is_user_banned(update: Update) -> bool:
    data, _ = get_user(update.effective_user)
    if data["banned"]:
        await update.message.reply_text("🚫 حساب شما مسدود شده است. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
        return True
    return False


# =====================================================================
# MARKET
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
# REPLY KEYBOARDS (no inline/glass buttons for navigation)
# =====================================================================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "🪙 کیف پول"],
        ["🏙 شهر", "💼 شغل"],
        ["🛒 بازار", "⚔ رقابت آنلاین"],
        ["👑 کلن", "🎁 مأموریت‌ها"],
        ["📦 صندوق‌ها", "🏆 رتبه‌بندی"],
        ["🛍 فروشگاه", "👑 خرید اشتراک"],
        ["💸 برداشت TON", "👥 دعوت دوستان"],
        ["🏅 دستاوردها", "📅 رویدادها"],
        ["🌍 دنیای LIBER", "🤖 مشاور هوشمند"],
        ["⚙ تنظیمات", "❓ راهنما"],
    ],
    resize_keyboard=True,
)

CITY_MENU = ReplyKeyboardMarkup(
    [
        ["🏦 بانک", "⛏ معدن"],
        ["🏭 کارخانه", "⚡ نیروگاه"],
        ["📦 انبار", "🚀 ارتقا شهر"],
        ["🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)

SHOP_MENU = ReplyKeyboardMarkup(
    [
        ["👑 خرید اشتراک", "🎁 خرید صندوق"],
        ["⚡ خرید انرژی", "🎨 خرید آواتار"],
        ["🖼 خرید قاب", "🐉 خرید Pet"],
        ["🎫 خرید بلیت مسابقه", "🎟 کد هدیه"],
        ["🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)

COMPETITION_MENU = ReplyKeyboardMarkup(
    [
        ["🥊 نبرد ۱ به ۱", "🏆 لیگ من"],
        ["👑 تورنمنت", "🎯 مأموریت رقابتی"],
        ["📊 رتبه‌بندی رقابتی", "🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)

CLAN_MENU = ReplyKeyboardMarkup(
    [
        ["🏛 ساخت کلن", "🔍 جستجوی کلن"],
        ["👥 اعضای کلن", "⚔ جنگ کلن"],
        ["💰 صندوق کلن", "🚀 ارتقا کلن"],
        ["🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)

WORLD_MENU = ReplyKeyboardMarkup(
    [
        ["🗺 نقشه شهرها", "📰 اخبار بازی"],
        ["📅 رویداد فعال", "⏳ شمارش معکوس مسابقات"],
        ["💹 تغییرات قیمت LIBER", "👥 آمار آنلاین"],
        ["🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)

SUB_MENU = ReplyKeyboardMarkup(
    [
        ["🥈 Silver", "🥇 Gold"],
        ["💎 Diamond", "👑 Titan"],
        ["🔙 بازگشت به منو"],
    ],
    resize_keyboard=True,
)


def join_message_text():
    uname = CHANNEL.replace("@", "")
    return f"لطفاً ابتدا در کانال زیر عضو شوید، سپس دوباره /start را بزنید:\nhttps://t.me/{uname}"


async def is_member(bot, user_id) -> bool:
    if not CHANNEL:
        return True
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"channel check failed: {e}")
        return False


# =====================================================================
# CORE COMMANDS
# =====================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await is_member(context.bot, user.id):
        await update.message.reply_text(join_message_text())
        return

    if str(user.id) in db["users"] and db["users"][str(user.id)]["banned"]:
        await update.message.reply_text("🚫 حساب شما مسدود شده است. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
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
            "به ربات LIBER کوین خوش آمدید!\n\n"
            f"💰 موجودی اولیه: {data['liber']} LIBER، {data['coin']} Coin\n\n"
            "این یک بازی شبیه‌سازی اقتصادی سرگرمی است — همه ارزها (LIBER, Coin, "
            "Energy, Diamond, Medal) کاملاً مجازی و فقط برای پیشرفت داخل بازی هستند.\n\n"
            "از دکمه‌های پایین صفحه برای گشت‌وگذار توی بازی استفاده کن. هر بخش "
            "زیرمنوی خودش رو داره — مثلاً 🏙 شهر یک منوی جدید با بانک/معدن/کارخانه باز می‌کنه."
        )
    else:
        text = f"سلام جناب {display_name} 👋\nبه ربات LIBER کوین خوش برگشتید!"

    await update.message.reply_text(text, reply_markup=MAIN_MENU)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    needed = data["level"] * XP_PER_LEVEL
    job_name = JOBS[data["job"]]["name"]
    sub_name = SUBSCRIPTION_TIERS.get(data["sub_tier"], {}).get("name", "ندارد") if data["sub_tier"] else "ندارد"
    clan_name = data["clan_id"] if data["clan_id"] else "—"

    await update.message.reply_text(
f"""👤 پروفایل کامل

نام: {data['name']}
یوزرنیم: @{data['username'] or '—'}
آیدی عددی: {data['id']}
شغل: {job_name}
⭐ سطح: {data['level']}   ✨ XP: {data['xp']} / {needed}
🏅 مدال: {data['medal']}
🏆 رتبه فصلی: {LEAGUE_NAMES.get(data['league'], data['league'])} ({data['season_points']} امتیاز)
⚔ امتیاز رقابتی: {data['rank_points']}
👑 اشتراک: {sub_name}
👥 کلن: {clan_name}
🏙 سطح شهر: {data['city_level']}
🪙 موجودی LIBER: {data['liber']:.2f}
📅 تاریخ عضویت: {data['created'][:10]}
📝 بیو: {data['bio'] or '—'}"""
    )


async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
f"""🪙 کیف پول شما

🪙 LIBER: {data['liber']:.2f}
💵 Coin: {data['coin']:.2f}
⚡ Energy: {data['energy']}
💎 Diamond: {data['diamond']}
🏅 Medal: {data['medal']}

📜 برای برداشت واقعی به TON: دکمه «💸 برداشت TON»"""
    )


# =====================================================================
# CITY
# =====================================================================

BUILDING_INFO = {
    "bank": {"label": "🏦 بانک", "base_cost": 300, "income": 8},
    "mine": {"label": "⛏ معدن", "base_cost": 250, "income": 10},
    "factory": {"label": "🏭 کارخانه", "base_cost": 400, "income": 14},
    "power_plant": {"label": "⚡ نیروگاه", "base_cost": 500, "income": 18},
    "warehouse": {"label": "📦 انبار", "base_cost": 200, "income": 5},
}


async def city_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    lines = [f"🏙 شهر شما — سطح {data['city_level']}\n"]
    for key, info in BUILDING_INFO.items():
        level = data["buildings"].get(key, 0)
        lines.append(f"{info['label']}: سطح {level}")
    lines.append("\nیک ساختمان رو از منوی پایین انتخاب کن تا جزئیات و ارتقاش رو ببینی.")
    await update.message.reply_text("\n".join(lines), reply_markup=CITY_MENU)


async def building_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    data, _ = get_user(update.effective_user)
    info = BUILDING_INFO[key]
    level = data["buildings"].get(key, 0)
    cost = int(info["base_cost"] * (1.5 ** level))
    income = info["income"] * (level + 1)

    await update.message.reply_text(
f"""{info['label']}

سطح فعلی: {level}
درآمد فعلی هر جمع‌آوری: {income} Coin
هزینه ارتقا به سطح {level + 1}: {cost} LIBER

برای ارتقا بنویس: /upgrade {key}
برای جمع‌آوری درآمد بنویس: /collect {key}"""
    )


async def upgrade_building(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in BUILDING_INFO:
        await update.message.reply_text(f"استفاده: /upgrade نوع\nانواع: {', '.join(BUILDING_INFO)}")
        return
    key = context.args[0]
    info = BUILDING_INFO[key]
    level = data["buildings"].get(key, 0)
    cost = int(info["base_cost"] * (1.5 ** level))

    if data["liber"] < cost:
        await update.message.reply_text(f"❌ LIBER کافی نیست. هزینه ارتقا: {cost}")
        return

    data["liber"] -= cost
    data["buildings"][key] = level + 1
    save_data()
    add_xp(update.effective_user.id, 15)
    log_action(update.effective_user.id, "UPGRADE_BUILDING", f"{key} -> {level+1}")
    await update.message.reply_text(f"✅ {info['label']} به سطح {level + 1} ارتقا یافت! (-{cost} LIBER)")


async def collect_building(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in BUILDING_INFO:
        await update.message.reply_text(f"استفاده: /collect نوع\nانواع: {', '.join(BUILDING_INFO)}")
        return
    key = context.args[0]
    info = BUILDING_INFO[key]
    level = data["buildings"].get(key, 0)
    if level == 0:
        await update.message.reply_text(f"هنوز {info['label']} نساختی. /upgrade {key} رو بزن.")
        return

    income = info["income"] * level
    data["coin"] += income
    save_data()
    add_xp(update.effective_user.id, 3)
    await update.message.reply_text(f"💰 {income} Coin از {info['label']} جمع‌آوری شد!")


async def upgrade_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    cost = data["city_level"] * 800
    if data["liber"] < cost:
        await update.message.reply_text(f"🚀 ارتقای شهر\n\nسطح فعلی: {data['city_level']}\nهزینه: {cost} LIBER\nکافی نیست.")
        return
    data["liber"] -= cost
    data["city_level"] += 1
    save_data()
    add_xp(update.effective_user.id, 40)
    await update.message.reply_text(f"🎉 شهرت به سطح {data['city_level']} ارتقا یافت! (-{cost} LIBER)")


# =====================================================================
# JOB SYSTEM
# =====================================================================

async def job_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    job_name = JOBS[data["job"]]["name"]
    lines = [f"💼 شغل فعلی: {job_name}\n\nمشاغل قابل انتخاب:"]
    for key, info in JOBS.items():
        if key == "none":
            continue
        lines.append(f"  {info['name']} — درآمد پایه: {info['income']} Coin/ساعت — /setjob {key}")
    lines.append("\nبرای جمع‌آوری درآمد شغل: /workincome")
    await update.message.reply_text("\n".join(lines))


async def set_job(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in JOBS:
        await update.message.reply_text(f"استفاده: /setjob نوع\nانواع: {', '.join(k for k in JOBS if k != 'none')}")
        return
    data["job"] = context.args[0]
    save_data()
    await update.message.reply_text(f"✅ شغل شما به {JOBS[data['job']]['name']} تغییر کرد.")


async def work_income(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if data["job"] == "none":
        await update.message.reply_text("هنوز شغلی انتخاب نکردی. از /setjob استفاده کن.")
        return

    now = datetime.utcnow()
    last = data.get("last_job_collect")
    if last and now - datetime.fromisoformat(last) < timedelta(hours=1):
        remaining = timedelta(hours=1) - (now - datetime.fromisoformat(last))
        mins = int(remaining.seconds // 60)
        await update.message.reply_text(f"⏳ {mins} دقیقه دیگه دوباره سر کار بیا.")
        return

    income = JOBS[data["job"]]["income"] * data["level"]
    data["coin"] += income
    data["last_job_collect"] = str(now)
    save_data()
    add_xp(update.effective_user.id, 5)
    await update.message.reply_text(f"💼 {income} Coin از شغلت گرفتی!")


# =====================================================================
# MARKET (buy/sell/auction/p2p)
# =====================================================================

async def market_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_market()
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
f"""🛒 بازار LIBER

💰 قیمت لحظه‌ای: {db['market']['price']} Coin
📈 قیمت هر ۱ ساعت به‌صورت خودکار تغییر می‌کند.
💼 موجودی شما: {data['liber']:.2f} LIBER | {data['coin']:.2f} Coin

🟢 /buy مقدار_کوین — خرید LIBER
🔴 /sell مقدار_لیبر — فروش LIBER
🏷 /auction — مزایده
📦 /p2p_list — بازار کاربران (پیشنهادهای فروش باز)
➕ /p2p_sell مقدار قیمت — ثبت پیشنهاد فروش LIBER"""
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
    data["trade_count"] += 1
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
    data["trade_count"] += 1
    save_data()
    log_action(update.effective_user.id, "SELL", f"liber={liber_amount} coin={coin_amount}")
    await update.message.reply_text(f"✅ {coin_amount} Coin دریافت شد (قیمت: {price})")


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
        await update.message.reply_text("⏳ مزایده قبلی تمام شد. /bid رو دوباره بزن.")
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


async def p2p_sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /p2p_sell مقدار_لیبر قیمت_کوین")
        return
    try:
        amount = float(context.args[0])
        price = float(context.args[1])
    except ValueError:
        await update.message.reply_text("اعداد معتبر وارد کن.")
        return
    if amount <= 0 or amount > data["liber"]:
        await update.message.reply_text("موجودی LIBER کافی نیست.")
        return

    data["liber"] -= amount
    offers = db["p2p_offers"]
    offer_id = len(offers) + 1
    offers.append({"id": offer_id, "seller": user_id, "amount": amount, "price": price, "open": True})
    save_data()
    await update.message.reply_text(f"✅ پیشنهاد #{offer_id} ثبت شد: {amount} LIBER به {price} Coin.")


async def p2p_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    offers = [o for o in db["p2p_offers"] if o["open"]]
    if not offers:
        await update.message.reply_text("فعلاً هیچ پیشنهادی موجود نیست. /p2p_sell مقدار قیمت")
        return
    text = "📦 بازار کاربران\n\n"
    for o in offers[-10:]:
        seller = u(o["seller"])
        seller_name = seller["name"] if seller else str(o["seller"])
        text += f"#{o['id']} — {seller_name}: {o['amount']} LIBER به {o['price']} Coin — /p2p_buy {o['id']}\n"
    await update.message.reply_text(text)


async def p2p_buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /p2p_buy شماره_پیشنهاد")
        return
    try:
        offer_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("شماره نامعتبر است.")
        return

    offers = db["p2p_offers"]
    offer = next((o for o in offers if o["id"] == offer_id and o["open"]), None)
    if not offer:
        await update.message.reply_text("این پیشنهاد دیگر در دسترس نیست.")
        return
    if data["coin"] < offer["price"]:
        await update.message.reply_text("Coin کافی نداری.")
        return

    fee = offer["price"] * 0.03
    seller_gets = offer["price"] - fee
    data["coin"] -= offer["price"]
    data["liber"] += offer["amount"]
    seller = u(offer["seller"])
    if seller:
        seller["coin"] += seller_gets
    offer["open"] = False
    save_data()
    await update.message.reply_text(f"✅ خریداری شد! {offer['amount']} LIBER دریافت کردی.")


# =====================================================================
# MISSIONS
# =====================================================================

DAILY_MISSIONS = [
    ("خرید یا فروش در بازار", 30, 10),
    ("جمع‌آوری درآمد یک ساختمان", 40, 15),
    ("جمع‌آوری جایزه روزانه", 20, 5),
]

WEEKLY_MISSIONS = [
    ("۵ بار معامله در بازار", 300, 80),
    ("رسیدن به یک سطح جدید", 250, 60),
]


async def missions_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎁 مأموریت‌ها\n\n📅 روزانه:\n"
    for i, (desc, r_liber, r_xp) in enumerate(DAILY_MISSIONS, 1):
        text += f"  {i}. {desc} (+{r_liber} LIBER, +{r_xp} XP) — /complete_daily {i}\n"
    text += "\n📆 هفتگی:\n"
    for i, (desc, r_liber, r_xp) in enumerate(WEEKLY_MISSIONS, 1):
        text += f"  {i}. {desc} (+{r_liber} LIBER, +{r_xp} XP) — /complete_weekly {i}\n"
    text += "\n🕵 مخفی و فصلی هم به‌صورت رویدادهای خودکار ظاهر می‌شوند — از منوی «📅 رویدادها» چک کن."
    await update.message.reply_text(text)


async def complete_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استفاده: /complete_daily شماره")
        return
    try:
        idx = int(context.args[0]) - 1
        desc, r_liber, r_xp = DAILY_MISSIONS[idx]
    except (ValueError, IndexError):
        await update.message.reply_text("شماره نامعتبر است.")
        return
    add_currency(update.effective_user.id, liber=r_liber)
    add_xp(update.effective_user.id, r_xp)
    await update.message.reply_text(f"✅ «{desc}» تکمیل شد! +{r_liber} LIBER, +{r_xp} XP")


async def complete_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("استفاده: /complete_weekly شماره")
        return
    try:
        idx = int(context.args[0]) - 1
        desc, r_liber, r_xp = WEEKLY_MISSIONS[idx]
    except (ValueError, IndexError):
        await update.message.reply_text("شماره نامعتبر است.")
        return
    add_currency(update.effective_user.id, liber=r_liber)
    add_xp(update.effective_user.id, r_xp)
    await update.message.reply_text(f"✅ «{desc}» تکمیل شد! +{r_liber} LIBER, +{r_xp} XP")


async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    add_currency(update.effective_user.id, liber=reward_liber, energy=reward_energy)
    data["last_daily"] = str(now)
    save_data()
    add_xp(update.effective_user.id, 10)
    await update.message.reply_text(f"🎁 جایزه روزانه!\n+{reward_liber} LIBER\n+{reward_energy} Energy\n+10 XP")


# =====================================================================
# ACHIEVEMENTS
# =====================================================================

async def achievements_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["achievements"]:
        await update.message.reply_text("هنوز دستاورد یا مدالی نگرفتی. با بالا رفتن سطح، مدال می‌گیری.")
        return
    text = "🏅 دستاوردها و مدال‌های شما\n\n" + "\n".join(f"🏅 {a}" for a in data["achievements"])
    await update.message.reply_text(text)


# =====================================================================
# CHESTS
# =====================================================================

CHESTS = {
    "free": {"name": "🎁 رایگان", "cost": 0, "min": 5, "max": 30},
    "bronze": {"name": "🥉 برنزی", "cost": 100, "min": 50, "max": 150},
    "silver": {"name": "🥈 نقره‌ای", "cost": 300, "min": 150, "max": 450},
    "gold": {"name": "🥇 طلایی", "cost": 700, "min": 400, "max": 1100},
    "diamond": {"name": "💎 الماسی", "cost": 1500, "min": 900, "max": 2500},
    "legendary": {"name": "👑 افسانه‌ای", "cost": 3000, "min": 1800, "max": 5000},
}


async def chests_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "📦 صندوق‌ها\n\n"
    for key, c in CHESTS.items():
        text += f"{c['name']} — هزینه: {c['cost']} LIBER — /chest {key}\n"
    await update.message.reply_text(text)


async def open_chest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in CHESTS:
        await update.message.reply_text(f"استفاده: /chest نوع\nانواع: {', '.join(CHESTS)}")
        return
    c = CHESTS[context.args[0]]
    if data["liber"] < c["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    reward = random.randint(c["min"], c["max"])
    data["liber"] -= c["cost"]
    add_currency(update.effective_user.id, liber=reward)
    data["chest_count"] += 1
    save_data()
    await update.message.reply_text(f"{c['name']} باز شد! +{reward} LIBER (هزینه {c['cost']})")


# =====================================================================
# RANKING
# =====================================================================

async def ranking_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    by_liber = sorted(db["users"].values(), key=lambda d: d["liber"], reverse=True)[:5]
    by_rank = sorted(db["users"].values(), key=lambda d: d["rank_points"], reverse=True)[:5]
    by_city = sorted(db["users"].values(), key=lambda d: d["city_level"], reverse=True)[:5]

    text = "🏆 رتبه‌بندی برترین‌ها\n\n💰 ثروتمندترین‌ها:\n"
    for i, d in enumerate(by_liber, 1):
        text += f"  {i}. {d['name']} — {d['liber']:.0f} LIBER\n"
    text += "\n⚔ قوی‌ترین رقابت‌گران:\n"
    for i, d in enumerate(by_rank, 1):
        text += f"  {i}. {d['name']} — {d['rank_points']} امتیاز\n"
    text += "\n🏙 بهترین شهرها:\n"
    for i, d in enumerate(by_city, 1):
        text += f"  {i}. {d['name']} — سطح {d['city_level']}\n"

    await update.message.reply_text(text)


# =====================================================================
# CLAN
# =====================================================================

async def clan_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👑 کلن\n\nاز منوی پایین انتخاب کن، یا مستقیم دستور بزن:\n"
        "/create_clan نام\n/join_clan نام\n/clan_info\n/clan_donate مقدار",
        reply_markup=CLAN_MENU,
    )


async def create_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if data["clan_id"]:
        await update.message.reply_text("قبلاً عضو یک کلنی.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /create_clan نام")
        return
    name = " ".join(context.args)[:30]
    if name in db["clans"]:
        await update.message.reply_text("این نام قبلاً استفاده شده.")
        return

    db["clans"][name] = {
        "leader": user_id, "treasury": 0, "level": 1, "members": [user_id],
        "war_score": 0, "created": str(datetime.utcnow()),
    }
    data["clan_id"] = name
    save_data()
    await update.message.reply_text(f"🏛 کلن «{name}» ساخته شد و رهبرش شدی!")


async def join_clan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if data["clan_id"]:
        await update.message.reply_text("قبلاً عضو یک کلنی.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /join_clan نام")
        return
    name = " ".join(context.args)
    clan = db["clans"].get(name)
    if not clan:
        await update.message.reply_text("کلنی با این نام پیدا نشد.")
        return
    clan["members"].append(user_id)
    data["clan_id"] = name
    save_data()
    await update.message.reply_text(f"👥 با موفقیت به کلن «{name}» پیوستی!")


async def clan_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["clans"]:
        await update.message.reply_text("هنوز هیچ کلنی ساخته نشده. /create_clan نام")
        return
    text = "🔍 کلن‌های موجود\n\n"
    for name, c in list(db["clans"].items())[:15]:
        text += f"👑 {name} — سطح {c['level']} — {len(c['members'])} عضو — /join_clan {name}\n"
    await update.message.reply_text(text)


async def clan_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["clan_id"]:
        await update.message.reply_text("عضو هیچ کلنی نیستی.\n/create_clan نام\n/join_clan نام")
        return
    clan = db["clans"][data["clan_id"]]
    members_txt = "\n".join(f"  • {u(m)['name'] if u(m) else m}" for m in clan["members"])
    await update.message.reply_text(
f"""👑 کلن: {data['clan_id']}

سطح: {clan['level']}
💰 خزانه: {clan['treasury']:.0f} Coin
⚔ امتیاز جنگ: {clan['war_score']}
👥 اعضا ({len(clan['members'])}):
{members_txt}"""
    )


async def clan_donate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["clan_id"]:
        await update.message.reply_text("عضو هیچ کلنی نیستی.")
        return
    if not context.args:
        await update.message.reply_text("استفاده: /clan_donate مقدار_کوین")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("عدد معتبر وارد کن.")
        return
    if amount <= 0 or amount > data["coin"]:
        await update.message.reply_text("موجودی Coin کافی نیست.")
        return
    data["coin"] -= amount
    db["clans"][data["clan_id"]]["treasury"] += amount
    save_data()
    await update.message.reply_text(f"✅ {amount} Coin به خزانه کلن اضافه شد.")


async def clan_upgrade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["clan_id"]:
        await update.message.reply_text("عضو هیچ کلنی نیستی.")
        return
    clan = db["clans"][data["clan_id"]]
    cost = clan["level"] * 2000
    if clan["treasury"] < cost:
        await update.message.reply_text(f"🚀 ارتقای کلن\n\nسطح: {clan['level']}\nهزینه: {cost} Coin از خزانه\nکافی نیست.")
        return
    clan["treasury"] -= cost
    clan["level"] += 1
    save_data()
    await update.message.reply_text(f"🎉 کلن به سطح {clan['level']} ارتقا یافت!")


async def clan_war(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not data["clan_id"]:
        await update.message.reply_text("عضو هیچ کلنی نیستی.")
        return
    clan = db["clans"][data["clan_id"]]
    others = [name for name in db["clans"] if name != data["clan_id"]]
    if not others:
        await update.message.reply_text("⚔ کلن دیگری برای جنگ وجود نداره هنوز.")
        return

    opponent_name = random.choice(others)
    opponent = db["clans"][opponent_name]
    my_power = sum(u(m)["rank_points"] for m in clan["members"] if u(m)) + clan["level"] * 100
    opp_power = sum(u(m)["rank_points"] for m in opponent["members"] if u(m)) + opponent["level"] * 100

    my_roll = my_power + random.randint(0, 200)
    opp_roll = opp_power + random.randint(0, 200)

    if my_roll >= opp_roll:
        clan["war_score"] += 10
        clan["treasury"] += 500
        result = f"🏆 کلن شما «{data['clan_id']}» در جنگ برابر «{opponent_name}» پیروز شد! +500 Coin خزانه."
    else:
        opponent["war_score"] += 10
        result = f"😔 کلن شما این‌بار برابر «{opponent_name}» شکست خورد."

    save_data()
    await update.message.reply_text(f"⚔ جنگ کلن\n\nقدرت شما: {my_roll}\nقدرت حریف: {opp_roll}\n\n{result}")


# =====================================================================
# COMPETITION
# =====================================================================

async def competition_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
f"""⚔ رقابت آنلاین

⚔ امتیاز رنک: {data['rank_points']}
🏆 لیگ: {LEAGUE_NAMES.get(data['league'], data['league'])}
🎮 مسابقات: {data['matches_played']} | 🏆 برد: {data['matches_won']}

از منوی پایین یکی رو انتخاب کن.""",
        reply_markup=COMPETITION_MENU,
    )


PVP_ENTRY_FEE = 30


async def pvp_battle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if data["liber"] < PVP_ENTRY_FEE:
        await update.message.reply_text(f"❌ برای نبرد به {PVP_ENTRY_FEE} LIBER نیاز داری.")
        return

    data["liber"] -= PVP_ENTRY_FEE

    my_power = data["level"] * 10 + data["rank_points"]
    candidates = [
        d for d in db["users"].values()
        if d["id"] != user_id and abs((d["level"] * 10 + d["rank_points"]) - my_power) <= 150
    ]
    if candidates:
        opponent = random.choice(candidates)
        opp_power = opponent["level"] * 10 + opponent["rank_points"]
        opponent_name = opponent["name"]
        real_opponent_id = opponent["id"]
    else:
        opp_power = my_power + random.randint(-20, 20)
        opponent_name = "🤖 حریف هوش مصنوعی"
        real_opponent_id = None

    my_roll = my_power + random.randint(-25, 25)
    opp_roll = opp_power + random.randint(-25, 25)

    data["matches_played"] += 1
    if real_opponent_id:
        u(real_opponent_id)["matches_played"] += 1

    if my_roll >= opp_roll:
        prize = int(PVP_ENTRY_FEE * 1.7)
        data["liber"] += prize
        data["matches_won"] += 1
        add_season_points(user_id, 15)
        if real_opponent_id:
            add_season_points(real_opponent_id, -5)
        text = f"🏆 بردی برابر {opponent_name}!\nقدرت شما: {my_roll} | قدرت حریف: {opp_roll}\n+{prize} LIBER, +15 امتیاز رنک"
    else:
        add_season_points(user_id, -5)
        if real_opponent_id:
            opp = u(real_opponent_id)
            opp["liber"] += int(PVP_ENTRY_FEE * 1.7)
            opp["matches_won"] += 1
            add_season_points(real_opponent_id, 15)
        text = f"😔 باختی برابر {opponent_name}.\nقدرت شما: {my_roll} | قدرت حریف: {opp_roll}\n-5 امتیاز رنک"

    save_data()
    await update.message.reply_text(text)


async def league_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    await update.message.reply_text(
        f"🏆 لیگ فعلی: {LEAGUE_NAMES.get(data['league'], data['league'])}\n✨ امتیاز فصلی: {data['season_points']}"
    )


async def tournament_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    started = datetime.fromisoformat(db["tournament"]["started_at"])
    days_passed = (datetime.utcnow() - started).days
    days_left = max(0, db["tournament"]["length_days"] - days_passed)
    await update.message.reply_text(
f"""👑 تورنمنت فصلی

⏳ روزهای باقی‌مانده: {days_left}
🥇 جوایز: نفر اول ۷۰۰ LIBER، دوم ۵۰۰، سوم ۳۰۰

رتبه‌ات رو با /league یا از منوی «🏆 لیگ من» ببین."""
    )


async def competitive_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 مأموریت رقابتی امروز\n\n"
        "اولین کسی که امروز ۱۰۰۰ LIBER جمع کنه، ۲۰۰ LIBER جایزه می‌گیره!\n"
        "این مسابقه به‌صورت خودکار توسط ربات بررسی و برنده اعلام می‌شود."
    )


async def competitive_ranking(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranked = sorted(db["users"].values(), key=lambda d: d["rank_points"], reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز کسی امتیاز رنک نگرفته.")
        return
    text = "📊 رتبه‌بندی رقابتی\n\n"
    for i, d in enumerate(ranked, 1):
        text += f"{i}. {d['name']} — {d['rank_points']} امتیاز ({d['matches_won']}/{d['matches_played']} برد)\n"
    await update.message.reply_text(text)


# =====================================================================
# SUBSCRIPTIONS
# =====================================================================

async def subscription_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "👑 خرید اشتراک LIBER\n\n"
    for key, tier in SUBSCRIPTION_TIERS.items():
        text += (
            f"{tier['name']} — {tier['days']} روز\n"
            f"  مزایا: {tier['perks']}\n"
            f"  قیمت: {tier['cost_liber']} LIBER  یا  ⭐ {tier['stars']} استارز\n"
            f"  خرید با LIBER: /buy_sub {key}\n"
            f"  خرید با استارز: /buy_sub_stars {key}\n\n"
        )
    text += "⚠️ VIP فقط پیشرفت رو سریع‌تر می‌کنه و تجربه رو بهتر می‌کنه — برد رو تضمین نمی‌کنه."
    await update.message.reply_text(text, reply_markup=SUB_MENU)


async def buy_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SUBSCRIPTION_TIERS:
        await update.message.reply_text(f"استفاده: /buy_sub نوع\nانواع: {', '.join(SUBSCRIPTION_TIERS)}")
        return
    key = context.args[0]
    tier = SUBSCRIPTION_TIERS[key]
    if data["liber"] < tier["cost_liber"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return

    data["liber"] -= tier["cost_liber"]
    data["sub_tier"] = key
    data["sub_expires"] = str(datetime.utcnow() + timedelta(days=tier["days"]))
    save_data()
    await update.message.reply_text(f"🎉 اشتراک {tier['name']} فعال شد تا {data['sub_expires'][:10]}!")


async def buy_sub_stars(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in SUBSCRIPTION_TIERS:
        await update.message.reply_text(f"استفاده: /buy_sub_stars نوع\nانواع: {', '.join(SUBSCRIPTION_TIERS)}")
        return
    key = context.args[0]
    tier = SUBSCRIPTION_TIERS[key]

    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title=f"{tier['name']} — {tier['days']} روزه",
        description=tier["perks"],
        payload=f"sub:{key}",
        currency="XTR",
        prices=[LabeledPrice(f"{tier['name']} ({tier['days']} روز)", tier["stars"])],
        provider_token="",
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payload = update.message.successful_payment.invoice_payload
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)

    if payload.startswith("sub:"):
        key = payload.split(":", 1)[1]
        tier = SUBSCRIPTION_TIERS.get(key)
        if tier:
            data["sub_tier"] = key
            data["sub_expires"] = str(datetime.utcnow() + timedelta(days=tier["days"]))
            save_data()
            log_action(user_id, "STARS_SUB_PURCHASE", key)
            await update.message.reply_text(f"🎉 پرداخت موفق! اشتراک {tier['name']} فعال شد تا {data['sub_expires'][:10]}.")


# =====================================================================
# SHOP
# =====================================================================

SHOP_ENERGY = {"small": {"amount": 50, "cost": 100}, "large": {"amount": 200, "cost": 350}}
SHOP_AVATARS = {"gold": {"name": "🖼 آواتار طلایی", "cost": 300}, "dragon": {"name": "🐉 آواتار اژدها", "cost": 600}}
SHOP_FRAMES = {"neon": {"name": "🎨 قاب نئونی", "cost": 400}, "galaxy": {"name": "🎨 قاب کهکشانی", "cost": 900}}
SHOP_PETS = {"cat": {"name": "🐱 گربه شانس", "cost": 800}, "dragon": {"name": "🐉 اژدهای کوچک", "cost": 2000}}
MATCH_TICKET_COST = 500


async def shop_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍 فروشگاه LIBER\n\nاز منوی پایین دسته مورد نظر رو انتخاب کن.",
        reply_markup=SHOP_MENU,
    )


async def shop_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "⚡ خرید انرژی\n\n"
    for k, v in SHOP_ENERGY.items():
        text += f"+{v['amount']} Energy — {v['cost']} LIBER — /buy_energy {k}\n"
    await update.message.reply_text(text)


async def buy_energy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SHOP_ENERGY:
        await update.message.reply_text("گزینه نامعتبر.")
        return
    item = SHOP_ENERGY[context.args[0]]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    data["energy"] += item["amount"]
    save_data()
    await update.message.reply_text(f"✅ +{item['amount']} Energy خریداری شد!")


async def shop_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🎨 خرید آواتار\n\n"
    for k, v in SHOP_AVATARS.items():
        text += f"{v['name']} — {v['cost']} LIBER — /buy_avatar {k}\n"
    await update.message.reply_text(text)


async def buy_avatar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SHOP_AVATARS:
        await update.message.reply_text("گزینه نامعتبر.")
        return
    item = SHOP_AVATARS[context.args[0]]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    save_data()
    await update.message.reply_text(f"✅ {item['name']} خریداری شد!")


async def shop_frame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🖼 خرید قاب پروفایل\n\n"
    for k, v in SHOP_FRAMES.items():
        text += f"{v['name']} — {v['cost']} LIBER — /buy_frame {k}\n"
    await update.message.reply_text(text)


async def buy_frame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SHOP_FRAMES:
        await update.message.reply_text("گزینه نامعتبر.")
        return
    item = SHOP_FRAMES[context.args[0]]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    data["frame"] = context.args[0]
    save_data()
    await update.message.reply_text(f"✅ {item['name']} فعال شد!")


async def shop_pet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "🐉 خرید همراه (Pet)\n\n"
    for k, v in SHOP_PETS.items():
        text += f"{v['name']} — {v['cost']} LIBER — /buy_pet {k}\n"
    await update.message.reply_text(text)


async def buy_pet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args or context.args[0] not in SHOP_PETS:
        await update.message.reply_text("گزینه نامعتبر.")
        return
    item = SHOP_PETS[context.args[0]]
    if data["liber"] < item["cost"]:
        await update.message.reply_text("LIBER کافی نیست.")
        return
    data["liber"] -= item["cost"]
    data["pet"] = context.args[0]
    save_data()
    await update.message.reply_text(f"✅ {item['name']} همراه تو شد!")


async def shop_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if data["liber"] < MATCH_TICKET_COST:
        await update.message.reply_text(f"🎫 بلیت مسابقه ویژه — {MATCH_TICKET_COST} LIBER\nLIBER کافی نیست.")
        return
    data["liber"] -= MATCH_TICKET_COST
    data["rank_points"] += 50
    save_data()
    await update.message.reply_text("🎫 بلیت خریداری شد! +50 امتیاز رقابتی هدیه گرفتی.")


async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /redeem کد_هدیه")
        return
    code = context.args[0].upper()
    entry = db["gift_codes"].get(code)
    if not entry:
        await update.message.reply_text("❌ کد نامعتبر است.")
        return
    if entry["uses_left"] <= 0:
        await update.message.reply_text("❌ ظرفیت این کد تمام شده.")
        return
    if user_id in entry["redeemed_by"]:
        await update.message.reply_text("❌ قبلاً این کد را استفاده کرده‌ای.")
        return

    data["liber"] += entry["reward"]
    entry["uses_left"] -= 1
    entry["redeemed_by"].append(user_id)
    save_data()
    log_action(user_id, "REDEEM_CODE", code)
    await update.message.reply_text(f"🎟 کد فعال شد! +{entry['reward']} LIBER")


async def gift_code_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎟 کد هدیه\n\nاگه کد هدیه داری، بنویس:\n/redeem کد_هدیه")


# =====================================================================
# TON WITHDRAWAL
# =====================================================================

async def withdraw_ton(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)

    if data["liber"] < MIN_WITHDRAW_LIBER:
        await update.message.reply_text(
            f"💸 برداشت TON\n\n❌ موجودی کافی نیست.\nحداقل برداشت: {MIN_WITHDRAW_LIBER} LIBER\nموجودی شما: {data['liber']:.2f}"
        )
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            f"استفاده: /withdraw مقدار آدرس_کیف‌پول_TON\nحداقل: {MIN_WITHDRAW_LIBER} LIBER\n\n"
            "⚠️ این فقط یک درخواست ثبت می‌کند؛ پرداخت واقعی توسط ادمین بعد از بررسی دستی انجام می‌شود."
        )
        return

    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.")
        return
    wallet_address = context.args[1]

    if amount < MIN_WITHDRAW_LIBER:
        await update.message.reply_text(f"حداقل برداشت {MIN_WITHDRAW_LIBER} LIBER است.")
        return
    if amount > data["liber"]:
        await update.message.reply_text("موجودی کافی نیست.")
        return

    data["liber"] -= amount
    req = {
        "user_id": user_id, "amount": amount, "wallet": wallet_address,
        "status": "pending", "at": str(datetime.utcnow()),
    }
    db["withdrawals"].append(req)
    save_data()

    await update.message.reply_text(
        "📤 درخواست برداشت ثبت شد و در صف بررسی ادمین قرار گرفت.\n"
        f"مبلغ: {amount:.2f} LIBER\nآدرس: {wallet_address}\n\n"
        "وضعیت رو با /withdrawals ببین."
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📥 درخواست برداشت جدید\nکاربر: {user_id}\nمبلغ: {amount:.2f} LIBER\nآدرس TON: {wallet_address}\n\n"
                f"برای تایید/رد از admin.py دستور /approve {user_id} یا /reject {user_id} رو بزن.",
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
        text += f"{w['amount']:.2f} LIBER — {labels.get(w['status'], w['status'])}\n"
    await update.message.reply_text(text)


# =====================================================================
# INVITE
# =====================================================================

async def invite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data, _ = get_user(update.effective_user)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.message.reply_text(
        f"👥 دعوت دوستان\n\nلینک اختصاصی شما:\n{link}\n\n"
        f"تعداد دعوت‌شدگان: {data['ref_count']}\nجایزه هر دعوت: 50 LIBER + 20 XP برای شما"
    )


# =====================================================================
# LIVE WORLD HUB
# =====================================================================

async def world_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌍 دنیای LIBER — دنیای زنده و همیشه در حال تغییر\n\nاز منوی پایین یکی رو انتخاب کن.",
        reply_markup=WORLD_MENU,
    )


async def world_map(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ranked = sorted(db["users"].values(), key=lambda d: d["city_level"], reverse=True)[:10]
    if not ranked:
        await update.message.reply_text("هنوز شهری روی نقشه نیست.")
        return
    text = "🗺 نقشه شهرها (برترین‌ها)\n\n"
    for i, d in enumerate(ranked, 1):
        text += f"{i}. {d['name']} — سطح شهر {d['city_level']}\n"
    await update.message.reply_text(text)


async def world_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["📰 اخبار زنده LIBER\n"]
    lines.append(f"💹 قیمت لحظه‌ای LIBER: {db['market']['price']} Coin")
    if db["users"]:
        richest = max(db["users"].values(), key=lambda d: d["liber"])
        lines.append(f"👑 ثروتمندترین بازیکن این لحظه: {richest['name']} با {richest['liber']:.0f} LIBER")
        top_fighter = max(db["users"].values(), key=lambda d: d["rank_points"])
        if top_fighter["rank_points"] > 0:
            lines.append(f"⚔ برترین رقابت‌گر این لحظه: {top_fighter['name']} با {top_fighter['rank_points']} امتیاز")
    lines.append(f"🌍 تعداد کاربران ثبت‌نام‌شده: {len(db['users'])}")
    if db["news"]:
        lines.append("\n📰 آخرین خبرها:")
        for n in db["news"][-3:][::-1]:
            lines.append(f"• {n['text']}")
    await update.message.reply_text("\n".join(lines))


async def active_events(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not db["events"]:
        await update.message.reply_text("رویداد فعالی وجود ندارد.")
        return
    text = "📅 آخرین رویدادهای جهانی\n\n"
    for e in db["events"][-5:]:
        text += f"{e['name']} — {e['at'][:16]}\n{e['desc']}\n\n"
    await update.message.reply_text(text)


async def match_countdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    started = datetime.fromisoformat(db["tournament"]["started_at"])
    days_passed = (datetime.utcnow() - started).days
    days_left = max(0, db["tournament"]["length_days"] - days_passed)
    await update.message.reply_text(f"⏳ شمارش معکوس تورنمنت فصلی: {days_left} روز باقی مانده.")


async def price_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hist = db["market"]["history"][-10:]
    if not hist:
        await update.message.reply_text("هنوز تاریخچه‌ای ثبت نشده.")
        return
    text = "💹 تغییرات اخیر قیمت LIBER\n\n" + "\n".join(f"{h['price']} — {h['at'][:16]}" for h in hist)
    await update.message.reply_text(text)


async def online_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total = len(db["users"])
    active_today = sum(
        1 for d in db["users"].values()
        if d.get("last_daily") and (datetime.utcnow() - datetime.fromisoformat(d["last_daily"])).days < 1
    )
    await update.message.reply_text(
        f"👥 آمار جهان LIBER\n\nکل کاربران ثبت‌نامی: {total}\nفعال امروز (گرفتن جایزه روزانه): {active_today}\n"
        f"کلن‌های ثبت‌شده: {len(db['clans'])}"
    )


# =====================================================================
# SMART ADVISOR
# =====================================================================

async def smart_advisor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    tips = []
    price = db["market"]["price"]

    if price < 90:
        tips.append("📉 قیمت LIBER پایین‌تر از حد معمول است — الان زمان خوبی برای خریدنه.")
    elif price > 120:
        tips.append("📈 قیمت LIBER بالاست — اگه LIBER اضافه داری شاید بفروشی سود کنی.")

    if data["job"] == "none":
        tips.append("💼 هنوز شغلی انتخاب نکردی؛ با /setjob یک شغل بگیر تا هر ساعت درآمد بگیری.")

    if sum(data["buildings"].values()) == 0:
        tips.append("🏙 هنوز هیچ ساختمانی توی شهرت نساختی. اولین معدن یا مزرعه رو با /upgrade بساز.")

    if not data["clan_id"]:
        tips.append("👑 عضو هیچ کلنی نیستی؛ با پیوستن به یک کلن، از خزانه و جنگ‌های کلن سود می‌بری.")

    if not data["sub_tier"]:
        tips.append("👑 با فعال کردن اشتراک، درآمد و XP بیشتری می‌گیری — از منوی «خرید اشتراک» ببین.")

    today = str(datetime.utcnow().date())
    if not data["last_daily"] or data["last_daily"][:10] != today:
        tips.append("🎁 جایزه روزانه‌ات رو هنوز نگرفتی — رایگانه، از دستش نده.")

    if data["energy"] < 20:
        tips.append("⚡ انرژی‌ات کمه؛ از فروشگاه انرژی بخر یا صبر کن تا شارژ بشه.")

    if not tips:
        tips.append("👍 وضعیتت خیلی خوبه! همینطور با مسابقه، صندوق و مأموریت روزانه پیش برو.")

    text = "🤖 مشاور هوشمند LIBER\n\nبر اساس وضعیت فعلی‌ات:\n\n" + "\n\n".join(f"• {t}" for t in tips)
    await update.message.reply_text(text)


# =====================================================================
# SETTINGS / HELP
# =====================================================================

async def settings_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚙ تنظیمات\n\n"
        "🌐 زبان: فارسی\n"
        "🔔 اعلان‌ها: فعال\n\n"
        "برای تغییر بیو: /setbio متن_جدید\n"
        "برای دیدن قوانین: /rules"
    )


async def setbio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data, _ = get_user(update.effective_user)
    if not context.args:
        await update.message.reply_text("استفاده: /setbio متن بیوگرافی تو")
        return
    data["bio"] = " ".join(context.args)[:150]
    save_data()
    await update.message.reply_text("✅ بیوگرافی بروزرسانی شد.")


async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📜 قوانین LIBER\n\n"
        "1. اسپم و فحاشی ممنوعه و باعث اخطار یا مسدودی می‌شه.\n"
        "2. تقلب یا سوءاستفاده از باگ‌ها ممنوعه.\n"
        "3. همه ارزهای داخل بازی مجازی‌ان و ارزش واقعی ندارن جز از طریق درخواست برداشت TON که ادمین دستی بررسی می‌کنه.\n"
        "4. رعایت احترام نسبت به بازیکنان دیگه الزامیه."
    )


async def help_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
"""❓ راهنمای کامل LIBER

👤 /profile — پروفایل کامل
🪙 /wallet — کیف پول
🏙 شهر: /upgrade نوع، /collect نوع، /upgrade_city
💼 شغل: /setjob نوع، /workincome
🛒 بازار: /buy، /sell، /auction، /bid، /p2p_sell، /p2p_list، /p2p_buy
⚔ رقابت: نبرد از منو، /league، تورنمنت از منو
👑 کلن: /create_clan، /join_clan، /clan_info، /clan_donate
🎁 مأموریت: /complete_daily، /complete_weekly، /daily
📦 صندوق: /chest نوع
🛍 فروشگاه: /buy_energy، /buy_avatar، /buy_frame، /buy_pet
👑 اشتراک: /buy_sub، /buy_sub_stars
💸 برداشت: /withdraw مقدار آدرس، /withdrawals
👥 /invite — دعوت دوستان
🏅 /achievements — دستاوردها
🌍 دنیای LIBER: نقشه، اخبار، رویدادها، آمار
🤖 /smart_advisor — پیشنهاد هوشمند بر اساس وضعیتت
⚙ /setbio، /rules، /settings"""
    )


# =====================================================================
# BACKGROUND JOBS
# =====================================================================

WORLD_EVENTS = [
    {"name": "🎉 جشنواره جهانی", "desc": "۲۴ ساعت XP دوبرابر برای همه.", "effect": "double_xp"},
    {"name": "📉 رکود اقتصادی", "desc": "قیمت بازار موقتاً کاهش می‌یابد.", "effect": "crash"},
    {"name": "💰 باران LIBER", "desc": "همه کاربران فعال ۳۰ LIBER می‌گیرند.", "effect": "rain"},
]


async def market_job(context: ContextTypes.DEFAULT_TYPE):
    update_market()


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

    for uid_str, d in db["users"].items():
        if d["banned"]:
            continue
        try:
            await context.bot.send_message(int(uid_str), f"🌍 رویداد جهانی: {event['name']}\n{event['desc']}")
        except Exception:
            pass


async def tournament_job(context: ContextTypes.DEFAULT_TYPE):
    started = datetime.fromisoformat(db["tournament"]["started_at"])
    days_passed = (datetime.utcnow() - started).days
    if days_passed < db["tournament"]["length_days"]:
        return

    ranked = sorted(db["users"].values(), key=lambda d: d["rank_points"], reverse=True)[:3]
    rewards = {0: 700, 1: 500, 2: 300}
    for i, d in enumerate(ranked):
        if d["rank_points"] <= 0:
            continue
        d["liber"] += rewards.get(i, 0)
        try:
            await context.bot.send_message(
                d["id"], f"🏆 تبریک! در تورنمنت فصلی رتبه {i+1} را کسب کردی و {rewards.get(i,0)} LIBER جایزه گرفتی!"
            )
        except Exception:
            pass

    for d in db["users"].values():
        d["rank_points"] = 0
    db["tournament"]["started_at"] = str(datetime.utcnow())
    save_data()


# =====================================================================
# MENU ROUTER (reply-keyboard button dispatch — no inline buttons)
# =====================================================================

async def _back_to_main(update, context):
    await update.message.reply_text("🌍 منوی اصلی LIBER", reply_markup=MAIN_MENU)


async def _hint_create_clan(update, context):
    await update.message.reply_text("استفاده: /create_clan نام")


async def _hint_withdraw(update, context):
    await update.message.reply_text(f"استفاده: /withdraw مقدار آدرس_کیف‌پول\nحداقل: {MIN_WITHDRAW_LIBER} LIBER")


def _sub_hint(key):
    async def _inner(update, context):
        await update.message.reply_text(
            f"خرید با LIBER: /buy_sub {key}\nخرید با استارز: /buy_sub_stars {key}"
        )
    return _inner


async def _bank_detail(update, context):
    await building_detail(update, context, "bank")


async def _mine_detail(update, context):
    await building_detail(update, context, "mine")


async def _factory_detail(update, context):
    await building_detail(update, context, "factory")


async def _power_detail(update, context):
    await building_detail(update, context, "power_plant")


async def _warehouse_detail(update, context):
    await building_detail(update, context, "warehouse")


MENU_ROUTES = {
    "👤 پروفایل": profile,
    "🪙 کیف پول": wallet,
    "🏙 شهر": city_menu,
    "💼 شغل": job_menu,
    "🛒 بازار": market_menu,
    "⚔ رقابت آنلاین": competition_menu,
    "👑 کلن": clan_menu,
    "🎁 مأموریت‌ها": missions_menu,
    "📦 صندوق‌ها": chests_menu,
    "🏆 رتبه‌بندی": ranking_menu,
    "🛍 فروشگاه": shop_menu,
    "👑 خرید اشتراک": subscription_menu,
    "👥 دعوت دوستان": invite,
    "🏅 دستاوردها": achievements_view,
    "📅 رویدادها": active_events,
    "🌍 دنیای LIBER": world_menu,
    "🤖 مشاور هوشمند": smart_advisor,
    "⚙ تنظیمات": settings_view,
    "❓ راهنما": help_view,
    "🏦 بانک": _bank_detail,
    "⛏ معدن": _mine_detail,
    "🏭 کارخانه": _factory_detail,
    "⚡ نیروگاه": _power_detail,
    "📦 انبار": _warehouse_detail,
    "🚀 ارتقا شهر": upgrade_city,
    "🎁 خرید صندوق": chests_menu,
    "⚡ خرید انرژی": shop_energy,
    "🎨 خرید آواتار": shop_avatar,
    "🖼 خرید قاب": shop_frame,
    "🐉 خرید Pet": shop_pet,
    "🎫 خرید بلیت مسابقه": shop_ticket,
    "🎟 کد هدیه": gift_code_info,
    "🥊 نبرد ۱ به ۱": pvp_battle,
    "🏆 لیگ من": league_view,
    "👑 تورنمنت": tournament_info,
    "🎯 مأموریت رقابتی": competitive_mission,
    "📊 رتبه‌بندی رقابتی": competitive_ranking,
    "🔍 جستجوی کلن": clan_search,
    "👥 اعضای کلن": clan_info,
    "⚔ جنگ کلن": clan_war,
    "💰 صندوق کلن": clan_info,
    "🚀 ارتقا کلن": clan_upgrade,
    "🏛 ساخت کلن": _hint_create_clan,
    "🗺 نقشه شهرها": world_map,
    "📰 اخبار بازی": world_news,
    "📅 رویداد فعال": active_events,
    "⏳ شمارش معکوس مسابقات": match_countdown,
    "💹 تغییرات قیمت LIBER": price_history,
    "👥 آمار آنلاین": online_stats,
    "🥈 Silver": _sub_hint("silver"),
    "🥇 Gold": _sub_hint("gold"),
    "💎 Diamond": _sub_hint("diamond"),
    "👑 Titan": _sub_hint("titan"),
    "💸 برداشت TON": _hint_withdraw,
    "🔙 بازگشت به منو": _back_to_main,
}


async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await is_user_banned(update):
        return

    user_id = update.effective_user.id
    get_user(update.effective_user)

    if anti_spam_flag(user_id):
        await warn_user(context, user_id, "الگوی کلیک غیرطبیعی/اسپم")
        if u(user_id)["banned"]:
            return

    handler = MENU_ROUTES.get(update.message.text)
    if handler:
        await handler(update, context)
    else:
        await update.message.reply_text("این بخش به‌زودی اضافه می‌شود. 🚧", reply_markup=MAIN_MENU)


# =====================================================================
# APP SETUP
# =====================================================================

def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("wallet", wallet))

    app.add_handler(CommandHandler("upgrade", upgrade_building))
    app.add_handler(CommandHandler("collect", collect_building))
    app.add_handler(CommandHandler("upgrade_city", upgrade_city))

    app.add_handler(CommandHandler("setjob", set_job))
    app.add_handler(CommandHandler("workincome", work_income))

    app.add_handler(CommandHandler("buy", buy_liber))
    app.add_handler(CommandHandler("sell", sell_liber))
    app.add_handler(CommandHandler("auction", auction_view))
    app.add_handler(CommandHandler("bid", bid))
    app.add_handler(CommandHandler("p2p_sell", p2p_sell))
    app.add_handler(CommandHandler("p2p_list", p2p_list))
    app.add_handler(CommandHandler("p2p_buy", p2p_buy))

    app.add_handler(CommandHandler("complete_daily", complete_daily))
    app.add_handler(CommandHandler("complete_weekly", complete_weekly))
    app.add_handler(CommandHandler("daily", daily_reward))

    app.add_handler(CommandHandler("create_clan", create_clan))
    app.add_handler(CommandHandler("join_clan", join_clan))
    app.add_handler(CommandHandler("clan_info", clan_info))
    app.add_handler(CommandHandler("clan_donate", clan_donate))

    app.add_handler(CommandHandler("buy_energy", buy_energy))
    app.add_handler(CommandHandler("buy_avatar", buy_avatar))
    app.add_handler(CommandHandler("buy_frame", buy_frame))
    app.add_handler(CommandHandler("buy_pet", buy_pet))
    app.add_handler(CommandHandler("redeem", redeem))

    app.add_handler(CommandHandler("buy_sub", buy_sub))
    app.add_handler(CommandHandler("buy_sub_stars", buy_sub_stars))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback))

    app.add_handler(CommandHandler("withdraw", withdraw_ton))
    app.add_handler(CommandHandler("withdrawals", withdrawals_view))

    app.add_handler(CommandHandler("invite", invite))
    app.add_handler(CommandHandler("achievements", achievements_view))
    app.add_handler(CommandHandler("chest", open_chest))

    app.add_handler(CommandHandler("smart_advisor", smart_advisor))
    app.add_handler(CommandHandler("setbio", setbio))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("help", help_view))
    app.add_handler(CommandHandler("settings", settings_view))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_router))

    # lazy import avoids a circular import at module load time
    from admin import register_admin_handlers
    register_admin_handlers(app)

    job_queue = app.job_queue
    if job_queue is None:
        sys.exit('❌ JobQueue در دسترس نیست.\npip install "python-telegram-bot[job-queue]"==21.6\npip install APScheduler')
    job_queue.run_repeating(market_job, interval=1800, first=60)
    job_queue.run_repeating(world_event_job, interval=21600, first=300)
    job_queue.run_repeating(tournament_job, interval=3600, first=120)


def main():
    if not TOKEN or TOKEN == "TOKEN_HERE":
        sys.exit(
            "❌ BOT_TOKEN تنظیم نشده.\n"
            "export BOT_TOKEN=توکن_واقعی_ربات   (یا مقدار TOKEN بالای main.py را عوض کن)"
        )

    app = ApplicationBuilder().token(TOKEN).build()
    register_handlers(app)

    logger.info("LIBER bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
