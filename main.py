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
#  تنظیمات کلی
# ===============================
=============================

TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"
ADMIN_IDS = [123456789]

FORCE_JOIN_CHANNELS = [
    {"id": "@Libercoin1", "title": "کانال LIBER", "url": "https://t.me/Libercoin1"},
    # کانال یا گروه دیگری داری، همینجا یک آیتم دیگر اضافه کن:
    # {"id": "@your_channel_2", "title": "کانال دوم", "url": "https://t.me/your_channel_2"},
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

# ------------------------------------------------------------
#  اشتراک ویژه با تلگرام استارز (Telegram Stars) ⭐
# ------------------------------------------------------------
# قیمت‌ها به ستاره تلگرام (XTR) است — قیمت‌ها منصفانه و شفاف نگه داشته شده‌اند.
STAR_SUBSCRIPTIONS = {
    "normal": {
        "title": "🥈 اشتراک عادی",
        "benefits": "درآمد +۱۰٪ | XP +۱۰٪ | یک صندوق نقره‌ای رایگان در ماه",
        "durations": {30: 60, 90: 150},   # {روز: قیمت به استارز}
    },
    "dragon": {
        "title": "🐉 اشتراک دراگون",
        "benefits": "درآمد +۲۵٪ | XP +۲۵٪ | یک صندوق طلایی رایگان در ماه | قاب اختصاصی دراگون",
        "durations": {30: 150, 90: 380},
    },
    "dragon_legend": {
        "title": "🐲 اشتراک دراگون لجند",
        "benefits": "درآمد +۵۰٪ | XP +۵۰٪ | صندوق الماسی رایگان در ماه | قاب اختصاصی لجند | ورود رایگان به مسابقه سخت هر هفته",
        "durations": {30: 300, 90: 750},
    },
}

# ------------------------------------------------------------
#  خرید LIBER با تلگرام استارز (نرخ منصفانه و ثابت)
# ------------------------------------------------------------
STAR_LIBER_PACKS = {
    "pack_small":  {"title": "📦 بسته کوچک", "liber": 100,  "stars": 50},
    "pack_medium": {"title": "📦 بسته متوسط", "liber": 300,  "stars": 130},
    "pack_large":  {"title": "📦 بسته بزرگ",  "liber": 1000, "stars": 400},
    "pack_mega":   {"title": "📦 بسته مگا",   "liber": 3000, "stars": 1100},
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

# ------------------------------------------------------------
#  فروشگاه
# ------------------------------------------------------------
SHOP_ITEMS = {
    "energy_50":   {"title": "⚡ ۵۰ انرژی",        "cost": {"coin": 200},    "give": ("energy", 50)},
    "energy_200":  {"title": "⚡ ۲۰۰ انرژی",       "cost": {"coin": 700},    "give": ("energy", 200)},
    "diamond_10":  {"title": "💎 ۱۰ الماس",        "cost": {"liber": 150},   "give": ("diamond", 10)},
    "diamond_50":  {"title": "💎 ۵۰ الماس",        "cost": {"liber": 650},   "give": ("diamond", 50)},
    "frame_gold":  {"title": "🖼 قاب طلایی",       "cost": {"diamond": 30},  "give": ("frame", "gold")},
    "frame_neon":  {"title": "🖼 قاب نئونی",        "cost": {"diamond": 60},  "give": ("frame", "neon")},
}

# ------------------------------------------------------------
#  دستاوردها
# ------------------------------------------------------------
ACHIEVEMENTS = {
    "first_trade":     {"title": "🥇 اولین معامله",      "desc": "اولین خرید یا فروش در بازار", "reward_liber": 20},
    "trader_100":      {"title": "📈 معامله‌گر",          "desc": "۱۰۰ بار در بازار معامله کن",   "reward_liber": 200},
    "chest_opener":    {"title": "🎁 صندوق‌باز",          "desc": "۵۰ صندوق باز کن",             "reward_diamond": 20},
    "country_founder": {"title": "🏛 بنیان‌گذار",         "desc": "یک کشور بساز",                "reward_coin": 300},
    "level_10":        {"title": "⭐ سطح ۱۰",             "desc": "به سطح ۱۰ برس",               "reward_diamond": 30},
    "level_25":        {"title": "🌟 سطح ۲۵",             "desc": "به سطح ۲۵ برس",               "reward_diamond": 100},
    "referral_10":     {"title": "👥 جذب‌کننده",          "desc": "۱۰ نفر دعوت کن",              "reward_liber": 300},
    "alliance_join":   {"title": "🤝 هم‌پیمان",           "desc": "به یک اتحاد بپیوند",          "reward_coin": 200},
    "vip_member":      {"title": "👑 عضو VIP",            "desc": "هر سطحی از VIP را بخر",       "reward_medal": 5},
    "bank_saver":      {"title": "🏦 پس‌انداز کن",        "desc": "۱۰۰۰ Coin سپرده بگذار",       "reward_coin": 150},
}

# ------------------------------------------------------------
#  تحقیقات / فناوری
# ------------------------------------------------------------
RESEARCH_TREE = [
    {"level": 1, "name": "کشاورزی مدرن", "cost_coin": 300,  "effect": "production +10%"},
    {"level": 2, "name": "معدن‌کاری پیشرفته", "cost_coin": 700,  "effect": "production +20%"},
    {"level": 3, "name": "انرژی خورشیدی", "cost_coin": 1500, "effect": "production +35%"},
    {"level": 4, "name": "هوش مصنوعی صنعتی", "cost_coin": 3000, "effect": "production +50%"},
    {"level": 5, "name": "فناوری کوانتومی", "cost_coin": 6000, "effect": "production +75%"},
]

# ------------------------------------------------------------
#  دفاع نظامی
# ------------------------------------------------------------
DEFENSE_UPGRADE_BASE_COST = 250
DEFENSE_UPGRADE_GROWTH = 1.6

# ------------------------------------------------------------
#  اکتشاف
# ------------------------------------------------------------
EXPLORATION_MIN_LEVEL = 5
EXPLORATION_ENERGY_COST = 20
EXPLORATION_REWARDS = [
    ("coin", 50, 300),
    ("liber", 5, 40),
    ("diamond", 0, 3),
]

# ------------------------------------------------------------
#  بازار سیاه (روزانه تغییر می‌کند)
# ------------------------------------------------------------
BLACK_MARKET_POOL = [
    {"title": "👑 آیتم افسانه‌ای کمیاب", "cost": {"diamond": 80}, "give": ("medal", 10)},
    {"title": "💎 پیشنهاد ویژه الماس",   "cost": {"liber": 500}, "give": ("diamond", 40)},
    {"title": "🎁 جعبه رمز و راز",        "cost": {"coin": 1000}, "give": ("liber", 60)},
    {"title": "🏅 مدال کمیاب",           "cost": {"diamond": 40}, "give": ("medal", 5)},
]

# ------------------------------------------------------------
#  فصل بازی
# ------------------------------------------------------------
SEASON_LENGTH_DAYS = 90

# ------------------------------------------------------------
#  معامله مستقیم بین بازیکنان
# ------------------------------------------------------------
TRADE_FEE_PERCENT = 3

# ------------------------------------------------------------
#  بازار پیش‌بینی قیمت
# ------------------------------------------------------------
PREDICTION_BET_AMOUNT = 50
PREDICTION_WIN_MULTIPLIER = 1.8

# ------------------------------------------------------------
#  فیلتر فحش (نمونه ساده - قابل گسترش)
# ------------------------------------------------------------
BANNED_WORDS = ["kosekhar", "fuckyou"]
MAX_WARN_BEFORE_BAN = 5

# ------------------------------------------------------------
#  رقابت آنلاین (فوتبال / بسکتبال)
# ------------------------------------------------------------
SPORTS = {
    "football": {
        "title": "⚽ فوتبال",
        "stats": {
            "life": "❤️ جون",
            "accuracy": "🎯 دقت",
            "intensity": "🔥 شدت",
            "shot": "🥅 شوت",
            "technique": "🌀 تکنیک",
            "physical": "💪 بدنی",
        },
    },
    "basketball": {
        "title": "🏀 بسکتبال",
        "stats": {
            "speed": "⚡ سرعت",
            "accuracy": "🎯 دقت",
            "press": "🧱 پرس",
            "physical": "💪 بدنی",
            "life": "❤️ جون",
        },
    },
}

STAT_UPGRADE_BASE_COST = 40
STAT_UPGRADE_GROWTH = 1.35
STAT_MAX_LEVEL = 50

MATCH_ENTRY_FEE = 20          # هزینه ورود به هر مسابقه رنک (LIBER)
MATCH_POT_FEE_PERCENT = 12    # کارمزد ربات از مجموع جایزه
MATCH_POSSESSIONS = 5         # تعداد حمله در هر مسابقه

HARD_MATCH_ENTRY_FEE = 4000    # هزینه ورود مسابقه سخت (Coin)
HARD_MATCH_REWARD = 8000       # جایزه برد مسابقه سخت (Coin)
HARD_MATCH_OPPONENT_BOOST = 1.35  # حریف سخت قوی‌تر از خودت شبیه‌سازی می‌شود

RANK_WIN_POINTS = 15
RANK_DRAW_POINTS = 6
RANK_LOSS_POINTS = -5

LEAGUE_TIERS = [
    (0,     "🥉 مبتدی"),
    (100,   "🥈 حرفه‌ای"),
    (300,   "🥇 استاد"),
    (700,   "🐉 اژدهای آزاد"),
    (1500,  "🐲 اژدهای افسانه‌ای"),
    (3000,  "🐉👑 اژدهای کامل افسانه‌ای"),
    (6000,  "💎 لیبر لجند وان"),
]

TOURNAMENT_LENGTH_DAYS = 60   # هر ۲ ماه
TOURNAMENT_REWARDS = {1: 700, 2: 500, 3: 300}   # LIBER (نفرات اول تا سوم)
TOURNAMENT_MEDAL_REWARDS = {4: 100, 5: 50}      # مدال (نفرات چهارم و پنجم)


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
            warn_count INTEGER DEFAULT 0,
            frame TEXT DEFAULT 'normal',
            trade_count INTEGER DEFAULT 0,
            chest_count INTEGER DEFAULT 0,
            research_level INTEGER DEFAULT 0,
            defense_level INTEGER DEFAULT 0,
            achievements TEXT DEFAULT '[]',
            bio TEXT DEFAULT '',
            football_life INTEGER DEFAULT 10,
            football_accuracy INTEGER DEFAULT 10,
            football_intensity INTEGER DEFAULT 10,
            football_shot INTEGER DEFAULT 10,
            football_technique INTEGER DEFAULT 10,
            football_physical INTEGER DEFAULT 10,
            basketball_speed INTEGER DEFAULT 10,
            basketball_accuracy INTEGER DEFAULT 10,
            basketball_press INTEGER DEFAULT 10,
            basketball_physical INTEGER DEFAULT 10,
            basketball_life INTEGER DEFAULT 10,
            rank_points INTEGER DEFAULT 0,
            matches_played INTEGER DEFAULT 0,
            matches_won INTEGER DEFAULT 0,
            vip_expires_at TEXT DEFAULT ''
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
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS trades (
            trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER,
            item_field TEXT,
            item_amount REAL,
            price_coin REAL,
            status TEXT DEFAULT 'open',
            buyer_id INTEGER DEFAULT 0,
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS predictions (
            pred_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            direction TEXT,
            start_price REAL,
            bet_amount REAL,
            status TEXT DEFAULT 'open',
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS season (
            id INTEGER PRIMARY KEY,
            season_number INTEGER,
            started_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS black_market_stock (
            id INTEGER PRIMARY KEY,
            item_index INTEGER,
            day TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS match_queue (
            user_id INTEGER PRIMARY KEY,
            sport TEXT,
            joined_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            opponent_id INTEGER,
            sport TEXT,
            player_score INTEGER,
            opponent_score INTEGER,
            result TEXT,
            log TEXT,
            created_at TEXT
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS tournament (
            id INTEGER PRIMARY KEY,
            started_at TEXT
        )
        """
    )
    c.execute("SELECT COUNT(*) as cnt FROM tournament")
    if c.fetchone()["cnt"] == 0:
        c.execute(
            "INSERT INTO tournament (id, started_at) VALUES (1, ?)",
            (datetime.now().strftime("%Y-%m-%d"),),
        )
    c.execute("SELECT COUNT(*) as cnt FROM market")
    if c.fetchone()["cnt"] == 0:
        c.execute("INSERT INTO market (id, price) VALUES (1, ?)", (MARKET_BASE_PRICE,))
    c.execute("SELECT COUNT(*) as cnt FROM season")
    if c.fetchone()["cnt"] == 0:
        c.execute(
            "INSERT INTO season (id, season_number, started_at) VALUES (1, 1, ?)",
            (datetime.now().strftime("%Y-%m-%d"),),
        )
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
#  دستاوردها
# ============================================================

def get_achievements(user_id):
    u = get_user(user_id)
    try:
        return json.loads(u["achievements"])
    except Exception:
        return []


def unlock_achievement(user_id, key):
    unlocked = get_achievements(user_id)
    if key in unlocked:
        return False
    unlocked.append(key)
    set_field(user_id, "achievements", json.dumps(unlocked))
    ach = ACHIEVEMENTS[key]
    if "reward_liber" in ach:
        add_currency(user_id, "liber", ach["reward_liber"])
    if "reward_coin" in ach:
        add_currency(user_id, "coin", ach["reward_coin"])
    if "reward_diamond" in ach:
        add_currency(user_id, "diamond", ach["reward_diamond"])
    if "reward_medal" in ach:
        add_currency(user_id, "medal", ach["reward_medal"])
    return True


def check_achievements(user_id):
    """بررسی و باز کردن خودکار دستاوردهایی که شرایطشان برآورده شده. خروجی: لیست عنوان‌های تازه باز شده."""
    u = get_user(user_id)
    newly_unlocked = []

    checks = {
        "first_trade": u["trade_count"] >= 1,
        "trader_100": u["trade_count"] >= 100,
        "chest_opener": u["chest_count"] >= 50,
        "country_founder": bool(u["country_name"]),
        "level_10": u["level"] >= 10,
        "level_25": u["level"] >= 25,
        "referral_10": u["ref_count"] >= 10,
        "alliance_join": u["alliance_id"] != 0,
        "vip_member": u["vip"] != "none",
        "bank_saver": u["bank_deposit"] >= 1000,
    }
    for key, condition in checks.items():
        if condition and unlock_achievement(user_id, key):
            newly_unlocked.append(ACHIEVEMENTS[key]["title"])
    return newly_unlocked


# ============================================================
#  تحقیقات / فناوری
# ============================================================

def get_research_info(user_id):
    u = get_user(user_id)
    level = u["research_level"]
    if level >= len(RESEARCH_TREE):
        return None
    return RESEARCH_TREE[level]


def upgrade_research(user_id):
    u = get_user(user_id)
    info = get_research_info(user_id)
    if not info:
        return False, "🔬 تمام سطوح تحقیقاتی را کامل کرده‌ای."
    if u["coin"] < info["cost_coin"]:
        return False, "❌ Coin کافی نداری."
    add_currency(user_id, "coin", -info["cost_coin"])
    set_field(user_id, "research_level", u["research_level"] + 1)
    return True, f"🔬 تحقیق «{info['name']}» تکمیل شد! ({info['effect']})"


# ============================================================
#  دفاع نظامی
# ============================================================

def get_defense_upgrade_cost(current_level):
    return round(DEFENSE_UPGRADE_BASE_COST * (DEFENSE_UPGRADE_GROWTH ** current_level), 2)


def upgrade_defense(user_id):
    u = get_user(user_id)
    cost = get_defense_upgrade_cost(u["defense_level"])
    if u["coin"] < cost:
        return False, f"❌ برای ارتقا به {cost} Coin نیاز داری."
    add_currency(user_id, "coin", -cost)
    set_field(user_id, "defense_level", u["defense_level"] + 1)
    return True, f"🛡 دفاع کشورت به سطح {u['defense_level']+1} ارتقا یافت."


# ============================================================
#  اکتشاف
# ============================================================

def do_exploration(user_id):
    u = get_user(user_id)
    if u["level"] < EXPLORATION_MIN_LEVEL:
        return False, f"🌌 اکتشاف فقط برای سطح {EXPLORATION_MIN_LEVEL} به بالا باز است."
    if u["energy"] < EXPLORATION_ENERGY_COST:
        return False, "⚡ انرژی کافی نداری."
    add_currency(user_id, "energy", -EXPLORATION_ENERGY_COST)
    lines = []
    for field, low, high in EXPLORATION_REWARDS:
        amount = random.randint(low, high)
        if amount > 0:
            add_currency(user_id, field, amount)
            lines.append(f"+ {amount} {field}")
    add_xp(user_id, 15)
    return True, "🌌 اکتشاف موفق!\n" + "\n".join(lines)


# ============================================================
#  بازار سیاه
# ============================================================

def get_black_market_today():
    today = datetime.now().strftime("%Y-%m-%d")
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM black_market_stock WHERE day=?", (today,))
    row = c.fetchone()
    if row:
        conn.close()
        return BLACK_MARKET_POOL[row["item_index"] % len(BLACK_MARKET_POOL)]
    index = random.randint(0, len(BLACK_MARKET_POOL) - 1)
    c.execute("DELETE FROM black_market_stock")
    c.execute("INSERT INTO black_market_stock (item_index, day) VALUES (?, ?)", (index, today))
    conn.commit()
    conn.close()
    return BLACK_MARKET_POOL[index]


def buy_black_market_item(user_id):
    item = get_black_market_today()
    u = get_user(user_id)
    for currency, cost in item["cost"].items():
        if u[currency] < cost:
            return False, f"❌ {currency} کافی برای این پیشنهاد نداری."
    for currency, cost in item["cost"].items():
        add_currency(user_id, currency, -cost)
    field, amount = item["give"]
    add_currency(user_id, field, amount)
    return True, f"🕵 خرید موفق: {item['title']} (+{amount} {field})"


# ============================================================
#  فصل بازی
# ============================================================

def get_season_info():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM season WHERE id=1")
    row = c.fetchone()
    conn.close()
    started = datetime.strptime(row["started_at"], "%Y-%m-%d")
    days_passed = (datetime.now() - started).days
    days_left = max(0, SEASON_LENGTH_DAYS - days_passed)
    return row["season_number"], days_left


def maybe_reset_season():
    number, days_left = get_season_info()
    if days_left <= 0:
        conn = db()
        c = conn.cursor()
        c.execute(
            "UPDATE season SET season_number=?, started_at=? WHERE id=1",
            (number + 1, datetime.now().strftime("%Y-%m-%d")),
        )
        conn.commit()
        conn.close()
        return True
    return False


# ============================================================
#  معامله مستقیم بین بازیکنان
# ============================================================

def create_trade_offer(seller_id, item_field, item_amount, price_coin):
    u = get_user(seller_id)
    if u[item_field] < item_amount:
        return False, "❌ موجودی کافی برای این پیشنهاد نداری."
    add_currency(seller_id, item_field, -item_amount)
    conn = db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO trades (seller_id, item_field, item_amount, price_coin, created_at) VALUES (?, ?, ?, ?, ?)",
        (seller_id, item_field, item_amount, price_coin, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return True, "✅ پیشنهاد معامله ثبت شد."


def list_open_trades(limit=10):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE status='open' ORDER BY trade_id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    return rows


def accept_trade_offer(buyer_id, trade_id):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM trades WHERE trade_id=? AND status='open'", (trade_id,))
    trade = c.fetchone()
    if not trade:
        conn.close()
        return False, "❌ این معامله دیگر در دسترس نیست."
    buyer = get_user(buyer_id)
    if buyer["coin"] < trade["price_coin"]:
        conn.close()
        return False, "❌ Coin کافی برای خرید نداری."
    fee = trade["price_coin"] * TRADE_FEE_PERCENT / 100
    seller_gets = trade["price_coin"] - fee
    add_currency(buyer_id, "coin", -trade["price_coin"])
    add_currency(buyer_id, trade["item_field"], trade["item_amount"])
    add_currency(trade["seller_id"], "coin", seller_gets)
    c.execute("UPDATE trades SET status='closed', buyer_id=? WHERE trade_id=?", (buyer_id, trade_id))
    conn.commit()
    conn.close()
    return True, f"✅ معامله انجام شد! {trade['item_amount']} {trade['item_field']} دریافت کردی."


# ============================================================
#  بازار پیش‌بینی قیمت
# ============================================================

def place_prediction(user_id, direction):
    u = get_user(user_id)
    if u["coin"] < PREDICTION_BET_AMOUNT:
        return False, "❌ Coin کافی برای شرط‌بندی نداری."
    add_currency(user_id, "coin", -PREDICTION_BET_AMOUNT)
    price = get_market_price()
    conn = db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO predictions (user_id, direction, start_price, bet_amount, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, direction, price, PREDICTION_BET_AMOUNT, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()
    return True, f"🎟 شرط ثبت شد: پیش‌بینی {direction} روی قیمت {price} Coin"


def resolve_predictions():
    """این تابع در job ساعتی بعد از تغییر قیمت صدا زده می‌شود تا شرط‌های باز را ببندد."""
    new_price = get_market_price()
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM predictions WHERE status='open'")
    open_bets = c.fetchall()
    results = []
    for bet in open_bets:
        won = (bet["direction"] == "up" and new_price > bet["start_price"]) or (
            bet["direction"] == "down" and new_price < bet["start_price"]
        )
        if won:
            payout = bet["bet_amount"] * PREDICTION_WIN_MULTIPLIER
            add_currency(bet["user_id"], "coin", payout)
            results.append((bet["user_id"], True, payout))
        else:
            results.append((bet["user_id"], False, 0))
        c.execute("UPDATE predictions SET status='closed' WHERE pred_id=?", (bet["pred_id"],))
    conn.commit()
    conn.close()
    return results


# ============================================================
#  فیلتر فحش
# ============================================================

def contains_banned_word(text):
    if not text:
        return False
    lowered = text.lower()
    return any(word in lowered for word in BANNED_WORDS)


# ============================================================
#  رقابت آنلاین (فوتبال / بسکتبال)
# ============================================================

def get_stat_upgrade_cost(level):
    return int(STAT_UPGRADE_BASE_COST * (STAT_UPGRADE_GROWTH ** level))


def upgrade_stat(user_id, sport, stat_key):
    field = f"{sport}_{stat_key}"
    u = get_user(user_id)
    level = u[field]
    if level >= STAT_MAX_LEVEL:
        return False, "🔒 این مهارت به حداکثر سطح رسیده."
    cost = get_stat_upgrade_cost(level)
    if u["coin"] < cost:
        return False, f"❌ برای ارتقا به {cost} Coin نیاز داری."
    add_currency(user_id, "coin", -cost)
    set_field(user_id, field, level + 1)
    return True, f"✅ مهارت ارتقا یافت! سطح جدید: {level+1} (هزینه: {cost} Coin)"


def get_total_power(user_id, sport):
    u = get_user(user_id)
    stats = SPORTS[sport]["stats"].keys()
    return sum(u[f"{sport}_{stat}"] for stat in stats)


def get_league_tier_name(points):
    name = LEAGUE_TIERS[0][1]
    for threshold, tier_name in LEAGUE_TIERS:
        if points >= threshold:
            name = tier_name
    return name


# ============================================================
#  اشتراک ویژه با تلگرام استارز
# ============================================================

def activate_star_subscription(user_id, tier_key, days):
    """اشتراک را برای کاربر فعال می‌کند و تاریخ شروع/پایان را برمی‌گرداند."""
    u = get_user(user_id)
    now = datetime.now()
    # اگر اشتراک فعلی هنوز منقضی نشده، مدت جدید را به آن اضافه می‌کند
    current_expiry = None
    if u["vip_expires_at"]:
        try:
            current_expiry = datetime.strptime(u["vip_expires_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            current_expiry = None

    start_from = current_expiry if (current_expiry and current_expiry > now) else now
    new_expiry = start_from + timedelta(days=days)

    set_field(user_id, "vip", tier_key)
    set_field(user_id, "vip_expires_at", new_expiry.strftime("%Y-%m-%d %H:%M:%S"))
    return now, new_expiry


def check_and_expire_subscription(user_id):
    """اگر اشتراک منقضی شده باشد، کاربر را به حالت بدون اشتراک برمی‌گرداند."""
    u = get_user(user_id)
    if u["vip"] != "none" and u["vip_expires_at"]:
        try:
            expiry = datetime.strptime(u["vip_expires_at"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return
        if datetime.now() > expiry:
            set_field(user_id, "vip", "none")
            set_field(user_id, "vip_expires_at", "")


def expire_all_subscriptions_job():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id FROM users WHERE vip != 'none' AND vip_expires_at != ''")
    rows = c.fetchall()
    conn.close()
    for row in rows:
        check_and_expire_subscription(row["user_id"])


def grant_liber_pack(user_id, pack_key):
    pack = STAR_LIBER_PACKS.get(pack_key)
    if not pack:
        return 0
    add_currency(user_id, "liber", pack["liber"])
    return pack["liber"]


def join_match_queue(user_id, sport):
    """اگر حریفی در صف باشد بلافاصله مسابقه شبیه‌سازی می‌شود، وگرنه کاربر در صف انتظار قرار می‌گیرد."""
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM match_queue WHERE sport=? AND user_id != ? LIMIT 1", (sport, user_id))
    opponent_row = c.fetchone()

    if opponent_row:
        c.execute("DELETE FROM match_queue WHERE user_id=?", (opponent_row["user_id"],))
        conn.commit()
        conn.close()
        opponent_id = opponent_row["user_id"]
        return "matched", opponent_id
    else:
        c.execute("DELETE FROM match_queue WHERE user_id=?", (user_id,))
        c.execute(
            "INSERT INTO match_queue (user_id, sport, joined_at) VALUES (?, ?, ?)",
            (user_id, sport, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
        conn.close()
        return "waiting", None


def leave_match_queue(user_id):
    conn = db()
    c = conn.cursor()
    c.execute("DELETE FROM match_queue WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()


def _run_possession_battle(player_power, opponent_power, opponent_name):
    """هسته مشترک شبیه‌سازی حمله‌به‌حمله؛ هم برای مسابقه رنک هم مسابقه سخت استفاده می‌شود."""
    player_score = 0
    opponent_score = 0
    log_lines = []
    attacker = "player"

    for possession in range(1, MATCH_POSSESSIONS + 1):
        if attacker == "player":
            atk_power = player_power + random.randint(-10, 10)
            def_power = opponent_power + random.randint(-10, 10)
            atk_label = "شما"
        else:
            atk_power = opponent_power + random.randint(-10, 10)
            def_power = player_power + random.randint(-10, 10)
            atk_label = opponent_name

        log_lines.append(f"🔵 حمله {possession}: {atk_label} توپ را ارسال کرد...")
        if atk_power > def_power:
            log_lines.append(f"⚽ گل شد! ({atk_power} در برابر {def_power})")
            if attacker == "player":
                player_score += 1
            else:
                opponent_score += 1
        elif atk_power == def_power:
            log_lines.append(f"⚔️ قدرت مساوی بود ({atk_power} = {def_power}) — دفاع در آخرین لحظه گل را گرفت.")
        else:
            log_lines.append(f"🛡 دفاع موفق بود ({def_power} در برابر {atk_power})")

        attacker = "opponent" if attacker == "player" else "player"

    if player_score == opponent_score:
        log_lines.append("⏱ نتیجه مساوی شد — ضربات پنالتی تعیین‌کننده...")
        if player_power + random.randint(0, 15) >= opponent_power + random.randint(0, 15):
            player_score += 1
        else:
            opponent_score += 1

    result = "win" if player_score > opponent_score else "loss"
    return player_score, opponent_score, result, log_lines


def simulate_match(player_id, opponent_id, sport, vs_bot=False):
    """شبیه‌سازی مسابقه رنک عادی (با حریف واقعی یا هوش مصنوعی متعادل)."""
    player_power = get_total_power(player_id, sport)
    if vs_bot:
        opponent_power = max(20, player_power + random.randint(-15, 15))
        opponent_name = "🤖 حریف هوش مصنوعی"
    else:
        opponent_power = get_total_power(opponent_id, sport)
        opp_user = get_user(opponent_id)
        opponent_name = opp_user["first_name"] or "حریف"

    player_score, opponent_score, result, log_lines = _run_possession_battle(
        player_power, opponent_power, opponent_name
    )

    return {
        "player_score": player_score,
        "opponent_score": opponent_score,
        "result": result,
        "log": log_lines,
        "opponent_name": opponent_name,
        "player_power": player_power,
        "opponent_power": opponent_power,
    }


def simulate_hard_match(player_id, sport):
    """شبیه‌سازی مسابقه سخت/پرمخاطره برابر حریف هوش مصنوعی قوی‌تر."""
    player_power = get_total_power(player_id, sport)
    opponent_power = max(30, int(player_power * HARD_MATCH_OPPONENT_BOOST) + random.randint(0, 20))
    opponent_name = "🔥 حریف سخت (هوش مصنوعی)"

    player_score, opponent_score, result, log_lines = _run_possession_battle(
        player_power, opponent_power, opponent_name
    )

    return {
        "player_score": player_score,
        "opponent_score": opponent_score,
        "result": result,
        "log": log_lines,
        "opponent_name": opponent_name,
        "player_power": player_power,
        "opponent_power": opponent_power,
    }


def apply_match_result(player_id, opponent_id, sport, match_data, vs_bot=False):
    conn = db()
    c = conn.cursor()
    c.execute(
        "INSERT INTO matches (player_id, opponent_id, sport, player_score, opponent_score, result, log, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            player_id,
            opponent_id if not vs_bot else 0,
            sport,
            match_data["player_score"],
            match_data["opponent_score"],
            match_data["result"],
            json.dumps(match_data["log"], ensure_ascii=False),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()

    add_currency(player_id, "matches_played", 1)
    if not vs_bot:
        add_currency(opponent_id, "matches_played", 1)

    pot = MATCH_ENTRY_FEE * (1 if vs_bot else 2)
    fee = pot * MATCH_POT_FEE_PERCENT / 100
    prize = round(pot - fee, 2)

    if match_data["result"] == "win":
        add_currency(player_id, "liber", prize)
        add_currency(player_id, "matches_won", 1)
        add_currency(player_id, "rank_points", RANK_WIN_POINTS)
        if not vs_bot:
            add_currency(opponent_id, "rank_points", RANK_LOSS_POINTS)
    else:
        if not vs_bot:
            add_currency(opponent_id, "liber", prize)
            add_currency(opponent_id, "matches_won", 1)
            add_currency(opponent_id, "rank_points", RANK_WIN_POINTS)
        add_currency(player_id, "rank_points", RANK_LOSS_POINTS)

    # جلوگیری از منفی شدن امتیاز رنک
    for uid in ([player_id] if vs_bot else [player_id, opponent_id]):
        u2 = get_user(uid)
        if u2["rank_points"] < 0:
            set_field(uid, "rank_points", 0)


def get_tournament_info():
    conn = db()
    c = conn.cursor()
    c.execute("SELECT * FROM tournament WHERE id=1")
    row = c.fetchone()
    conn.close()
    started = datetime.strptime(row["started_at"], "%Y-%m-%d")
    days_passed = (datetime.now() - started).days
    days_left = max(0, TOURNAMENT_LENGTH_DAYS - days_passed)
    return days_left


async def maybe_resolve_tournament(bot):
    days_left = get_tournament_info()
    if days_left > 0:
        return
    await _resolve_tournament_now(bot)


async def maybe_resolve_tournament_forced(bot):
    await _resolve_tournament_now(bot)


async def _resolve_tournament_now(bot):
    conn = db()
    c = conn.cursor()
    c.execute("SELECT user_id, first_name, rank_points FROM users ORDER BY rank_points DESC LIMIT 5")
    top5 = c.fetchall()
    conn.close()

    for i, row in enumerate(top5, start=1):
        if row["rank_points"] <= 0:
            continue
        liber_reward = TOURNAMENT_REWARDS.get(i, 0)
        medal_reward = TOURNAMENT_MEDAL_REWARDS.get(i, 0)
        if liber_reward:
            add_currency(row["user_id"], "liber", liber_reward)
        if medal_reward:
            add_currency(row["user_id"], "medal", medal_reward)
        if liber_reward or medal_reward:
            reward_text = f"{liber_reward} LIBER" if liber_reward else f"{medal_reward} مدال"
            try:
                await bot.send_message(
                    row["user_id"],
                    f"🏆 تبریک! در تورنمت فصلی رتبه {i} را کسب کردی و {reward_text} جایزه گرفتی!",
                )
            except Exception:
                pass

    conn = db()
    c = conn.cursor()
    c.execute("UPDATE tournament SET started_at=? WHERE id=1", (datetime.now().strftime("%Y-%m-%d"),))
    c.execute("UPDATE users SET rank_points=0")
    conn.commit()
    conn.close()


# ============================================================
#  کیبوردها
# ============================================================

def main_menu_keyboard(user_id=None):
    buttons = [
        [InlineKeyboardButton("👤 پروفایل من", callback_data="profile"),
         InlineKeyboardButton("🌍 امپراتوری من", callback_data="country"),
         InlineKeyboardButton("💹 بازار زنده", callback_data="market")],
        [InlineKeyboardButton("💰 گنجینه من", callback_data="wallet"),
         InlineKeyboardButton("🏦 بانک مرکزی", callback_data="bank"),
         InlineKeyboardButton("🏪 فروشگاه ویژه", callback_data="shop")],
        [InlineKeyboardButton("🎁 صندوق شانس", callback_data="chests"),
         InlineKeyboardButton("🎯 مأموریت روزانه", callback_data="missions"),
         InlineKeyboardButton("🏆 لیگ من", callback_data="league")],
        [InlineKeyboardButton("🤝 اتحاد قدرت", callback_data="alliance"),
         InlineKeyboardButton("📊 برترین‌ها", callback_data="ranking"),
         InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip")],
        [InlineKeyboardButton("👥 زیرمجموعه‌گیری", callback_data="invite"),
         InlineKeyboardButton("🎁 جایزه ورود روزانه", callback_data="daily"),
         InlineKeyboardButton("📰 اخبار جهان", callback_data="news")],
        [InlineKeyboardButton("🎖 دستاوردهای من", callback_data="achievements"),
         InlineKeyboardButton("🔬 آزمایشگاه فناوری", callback_data="research"),
         InlineKeyboardButton("🛡 قدرت دفاعی", callback_data="defense")],
        [InlineKeyboardButton("🌌 اکتشاف سرزمین", callback_data="exploration"),
         InlineKeyboardButton("🕵 بازار سیاه امروز", callback_data="black_market"),
         InlineKeyboardButton("📆 فصل بازی", callback_data="season")],
        [InlineKeyboardButton("📦 بازار بازیکنان", callback_data="p2p_market"),
         InlineKeyboardButton("🎟 حدس قیمت", callback_data="prediction")],
        [InlineKeyboardButton("⚔ رقابت آنلاین", callback_data="competition")],
        [InlineKeyboardButton("❓ راهنمای کامل", callback_data="help"),
         InlineKeyboardButton("☎ پشتیبانی", callback_data="support")],
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton("👑 پنل مدیریت TITAN", callback_data="admin_panel")])
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

    await update.message.reply_text(welcome, parse_mode=ParseMode.HTML, reply_markup=main_menu_keyboard(user_id))


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

    results = resolve_predictions()
    for target_user_id, won, payout in results:
        try:
            if won:
                text = f"🎉 پیش‌بینی‌ات درست بود! {round(payout,2)} Coin گرفتی."
            else:
                text = "😔 پیش‌بینی‌ات این‌بار درست نبود."
            await context.bot.send_message(target_user_id, text)
        except Exception as e:
            logger.warning(f"Could not notify user {target_user_id}: {e}")

    maybe_reset_season()
    await maybe_resolve_tournament(context.bot)
    expire_all_subscriptions_job()


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
            await query.message.edit_text("✅ عضویت شما تایید شد! از منوی زیر استفاده کن:", reply_markup=main_menu_keyboard(user_id))
        return

    if data == "back_main":
        await query.message.edit_text("🌍 منوی اصلی LIBER:", reply_markup=main_menu_keyboard(user_id))
        return

    u = get_user(user_id)

    # ---------------- پروفایل ----------------
    if data == "profile":
        league = get_league_name(u["xp"] + u["level"] * XP_PER_LEVEL)
        comp_league = get_league_tier_name(u["rank_points"])
        username_display = f"@{u['username']}" if u["username"] else "ثبت نشده"
        bio_display = u["bio"] or "بیوگرافی ثبت نشده (با /setbio متن بنویس)"
        text = (
            "👤 <b>پروفایل شما</b>\n"
            "━━━━━━━━━━━━━━━\n"
            f"🪪 نام کاربری: {username_display}\n"
            f"🆔 آیدی عددی: <code>{user_id}</code>\n"
            f"📛 نام: {u['first_name']}\n"
            f"📝 بیو: {bio_display}\n"
            "━━━━━━━━━━━━━━━\n"
            f"⭐ سطح: {u['level']}  |  💎 XP: {u['xp']}/{u['level']*XP_PER_LEVEL}\n"
            f"🏆 لیگ اقتصادی: {league}\n"
            f"⚔ لیگ رقابتی: {comp_league} ({u['rank_points']} امتیاز)\n"
            f"🏅 مدال: {u['medal']}\n"
            f"👑 اشتراک VIP: {u['vip'] if u['vip'] != 'none' else 'ندارد'}\n"
            "━━━━━━━━━━━━━━━\n"
            f"🪙 موجودی LIBER: {u['liber']}\n"
            f"🌍 کشور: {u['country_name'] or 'ثبت نشده'}\n"
            f"👥 زیرمجموعه‌ها: {u['ref_count']} نفر\n"
            f"⚠️ اخطارها: {u['warn_count']}/{MAX_WARN_BEFORE_BAN}\n"
            "━━━━━━━━━━━━━━━\n"
            f"📅 تاریخ عضویت: {u['joined_at']}\n"
            f"🔁 تعداد ورود به ربات: {u['login_count']}"
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
            add_currency(user_id, "trade_count", 1)
            unlocked = check_achievements(user_id)
            text = f"✅ خرید موفق!\n{amount} LIBER خریدی به قیمت {round(cost,2)} Coin (+ کارمزد {round(fee,2)})"
            if unlocked:
                text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
            await query.message.edit_text(text, reply_markup=back_keyboard())
        else:
            if u["liber"] < amount:
                await query.message.edit_text("❌ موجودی LIBER کافی نیست.", reply_markup=back_keyboard())
                return
            fee = cost * SELL_FEE_PERCENT / 100
            net = cost - fee
            add_currency(user_id, "liber", -amount)
            add_currency(user_id, "coin", net)
            add_currency(user_id, "trade_count", 1)
            unlocked = check_achievements(user_id)
            text = f"✅ فروش موفق!\n{amount} LIBER فروختی و {round(net,2)} Coin گرفتی (کارمزد {round(fee,2)})"
            if unlocked:
                text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
            await query.message.edit_text(text, reply_markup=back_keyboard())

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
        unlocked = check_achievements(user_id)
        text = f"✅ {amount} Coin به سپرده بانکی اضافه شد."
        if unlocked:
            text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
        await query.message.edit_text(text, reply_markup=back_keyboard("bank"))

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
        unlocked = check_achievements(user_id)
        text = "🎉 کشورت ساخته شد! ۱۰۰ جمعیت و ۲۰۰ Coin بودجه اولیه گرفتی."
        if unlocked:
            text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
        await query.message.edit_text(text, reply_markup=back_keyboard())

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

        add_currency(user_id, "chest_count", 1)
        unlocked = check_achievements(user_id)
        text = f"🎉 صندوق {key} باز شد!\n\n" + "\n".join(reward_lines)
        if unlocked:
            text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
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
        check_and_expire_subscription(user_id)
        u = get_user(user_id)
        expiry_line = ""
        if u["vip"] != "none" and u["vip_expires_at"]:
            expiry_line = f"\n\n⏳ اشتراک فعلی تو ({u['vip']}) تا {u['vip_expires_at']} معتبر است."
        text = (
            "⭐ <b>سطوح VIP</b>\n\n"
            + "\n".join(
                f"{tier}: {info['cost_diamond']} Diamond — درآمد و XP x{info['income_bonus']}"
                for tier, info in VIP_TIERS.items()
            )
            + expiry_line
            + "\n\n🌟 همچنین می‌تونی با تلگرام استارز اشتراک ویژه با مزایای بیشتر بخری:"
        )
        buttons = [[InlineKeyboardButton(f"خرید {tier}", callback_data=f"vip_{tier}")] for tier in VIP_TIERS]
        buttons.append([InlineKeyboardButton("⭐ خرید اشتراک با استارز", callback_data="star_vip_menu")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("vip_") and not data.startswith("vip_star"):
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
        unlocked = check_achievements(user_id)
        text = f"🎉 تبریک! اکنون VIP {tier} هستی."
        if unlocked:
            text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
        await query.message.edit_text(text, reply_markup=back_keyboard("vip"))

    # ---------------- اشتراک ویژه با تلگرام استارز ⭐ ----------------
    elif data == "star_vip_menu":
        text = "🌟 <b>اشتراک‌های ویژه LIBER (پرداخت با تلگرام استارز)</b>\n\nیک اشتراک را انتخاب کن تا مزایا و قیمت‌هایش را ببینی:"
        buttons = [
            [InlineKeyboardButton(info["title"], callback_data=f"star_tier_{key}")]
            for key, info in STAR_SUBSCRIPTIONS.items()
        ]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="vip")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("star_tier_"):
        tier_key = data.split("_", 2)[2]
        plan = STAR_SUBSCRIPTIONS.get(tier_key)
        if not plan:
            await query.message.edit_text("❌ اشتراک نامعتبر.", reply_markup=back_keyboard("star_vip_menu"))
            return
        text = (
            f"{plan['title']}\n\n"
            f"🎁 مزایا: {plan['benefits']}\n\n"
            "مدت اشتراک را انتخاب کن:"
        )
        buttons = [
            [InlineKeyboardButton(f"{days} روز — ⭐ {stars} استارز", callback_data=f"star_buy_{tier_key}_{days}")]
            for days, stars in plan["durations"].items()
        ]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="star_vip_menu")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("star_buy_"):
        _, _, tier_key, days_str = data.split("_", 3)
        days = int(days_str)
        plan = STAR_SUBSCRIPTIONS.get(tier_key)
        if not plan or days not in plan["durations"]:
            await query.message.edit_text("❌ گزینه نامعتبر.", reply_markup=back_keyboard("star_vip_menu"))
            return
        stars_price = plan["durations"][days]
        await context.bot.send_invoice(
            chat_id=user_id,
            title=f"{plan['title']} — {days} روزه",
            description=f"مزایا: {plan['benefits']}",
            payload=f"vip:{tier_key}:{days}",
            currency="XTR",
            prices=[LabeledPrice(f"{plan['title']} ({days} روز)", stars_price)],
            provider_token="",
        )
        await query.answer("⭐ فاکتور پرداخت با استارز برایت ارسال شد.", show_alert=True)

    elif data == "star_liber_menu":
        text = "🌟 <b>خرید LIBER با تلگرام استارز</b>\n\nقیمت‌ها منصفانه و ثابت هستند. یک بسته انتخاب کن:"
        buttons = [
            [InlineKeyboardButton(f"{pack['title']} — {pack['liber']} LIBER — ⭐ {pack['stars']}", callback_data=f"star_liber_buy_{key}")]
            for key, pack in STAR_LIBER_PACKS.items()
        ]
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="shop")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("star_liber_buy_"):
        pack_key = data.split("star_liber_buy_", 1)[1]
        pack = STAR_LIBER_PACKS.get(pack_key)
        if not pack:
            await query.message.edit_text("❌ بسته نامعتبر.", reply_markup=back_keyboard("star_liber_menu"))
            return
        await context.bot.send_invoice(
            chat_id=user_id,
            title=pack["title"],
            description=f"{pack['liber']} LIBER مستقیم به کیف پول شما اضافه می‌شود.",
            payload=f"liber:{pack_key}",
            currency="XTR",
            prices=[LabeledPrice(pack["title"], pack["stars"])],
            provider_token="",
        )
        await query.answer("⭐ فاکتور پرداخت با استارز برایت ارسال شد.", show_alert=True)

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
        unlocked = check_achievements(user_id)
        text = "🎉 اتحاد جدید ساخته شد و رهبر آن شدی!"
        if unlocked:
            text += "\n\n🎖 دستاورد جدید: " + ", ".join(unlocked)
        await query.message.edit_text(text, reply_markup=back_keyboard("alliance"))

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

    # ---------------- فروشگاه ----------------
    elif data == "shop":
        buttons = []
        row = []
        for key, item in SHOP_ITEMS.items():
            row.append(InlineKeyboardButton(item["title"], callback_data=f"shop_{key}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🌟 خرید LIBER با استارز", callback_data="star_liber_menu")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")])
        await query.message.edit_text("🏪 فروشگاه LIBER:", reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith("shop_"):
        key = data.split("_", 1)[1]
        item = SHOP_ITEMS.get(key)
        if not item:
            await query.message.edit_text("❌ آیتم نامعتبر.", reply_markup=back_keyboard("shop"))
            return
        for currency, cost in item["cost"].items():
            if u[currency] < cost:
                await query.message.edit_text(f"❌ {currency} کافی نداری.", reply_markup=back_keyboard("shop"))
                return
        for currency, cost in item["cost"].items():
            add_currency(user_id, currency, -cost)
        field, amount = item["give"]
        if field == "frame":
            set_field(user_id, "frame", amount)
            await query.message.edit_text(f"✅ خرید موفق: {item['title']}", reply_markup=back_keyboard("shop"))
        else:
            add_currency(user_id, field, amount)
            await query.message.edit_text(f"✅ خرید موفق: {item['title']}", reply_markup=back_keyboard("shop"))

    # ---------------- دستاوردها ----------------
    elif data == "achievements":
        unlocked = check_achievements(user_id)
        unlocked_keys = get_achievements(user_id)
        lines = []
        for key, ach in ACHIEVEMENTS.items():
            mark = "✅" if key in unlocked_keys else "🔒"
            lines.append(f"{mark} {ach['title']} — {ach['desc']}")
        text = "🎖 <b>دستاوردهای شما</b>\n\n" + "\n".join(lines)
        if unlocked:
            text += "\n\n🎉 دستاورد جدید باز شد: " + ", ".join(unlocked)
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- تحقیقات ----------------
    elif data == "research":
        info = get_research_info(user_id)
        if info:
            text = (
                "🔬 <b>تحقیقات</b>\n\n"
                f"سطح فعلی: {u['research_level']}\n"
                f"تحقیق بعدی: {info['name']}\n"
                f"هزینه: {info['cost_coin']} Coin\n"
                f"اثر: {info['effect']}"
            )
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔬 ارتقا", callback_data="research_upgrade")],
                [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
            ])
        else:
            text = "🔬 تمام سطوح تحقیقاتی را کامل کرده‌ای! 🎉"
            kb = back_keyboard()
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "research_upgrade":
        success, msg = upgrade_research(user_id)
        await query.message.edit_text(msg, reply_markup=back_keyboard("research"))

    # ---------------- دفاع ----------------
    elif data == "defense":
        cost = get_defense_upgrade_cost(u["defense_level"])
        text = (
            "🛡 <b>دفاع کشور</b>\n\n"
            f"سطح فعلی دفاع: {u['defense_level']}\n"
            f"هزینه ارتقای بعدی: {cost} Coin"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛡 ارتقای دفاع", callback_data="defense_upgrade")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "defense_upgrade":
        success, msg = upgrade_defense(user_id)
        await query.message.edit_text(msg, reply_markup=back_keyboard("defense"))

    # ---------------- اکتشاف ----------------
    elif data == "exploration":
        text = (
            "🌌 <b>اکتشاف</b>\n\n"
            f"حداقل سطح لازم: {EXPLORATION_MIN_LEVEL}\n"
            f"هزینه انرژی: {EXPLORATION_ENERGY_COST}\n"
            f"سطح فعلی شما: {u['level']} | انرژی: {u['energy']}"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🌌 شروع اکتشاف", callback_data="exploration_go")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "exploration_go":
        success, msg = do_exploration(user_id)
        await query.message.edit_text(msg, reply_markup=back_keyboard("exploration"))

    # ---------------- بازار سیاه ----------------
    elif data == "black_market":
        item = get_black_market_today()
        cost_text = ", ".join(f"{c} {k}" for k, c in item["cost"].items())
        text = (
            "🕵 <b>بازار سیاه امروز</b>\n\n"
            f"{item['title']}\n"
            f"💰 قیمت: {cost_text}\n"
            "⏳ این پیشنهاد فردا تغییر می‌کند."
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 خرید", callback_data="black_market_buy")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "black_market_buy":
        success, msg = buy_black_market_item(user_id)
        await query.message.edit_text(msg, reply_markup=back_keyboard("black_market"))

    # ---------------- فصل ----------------
    elif data == "season":
        maybe_reset_season()
        number, days_left = get_season_info()
        text = (
            "📆 <b>فصل بازی</b>\n\n"
            f"فصل فعلی: {number}\n"
            f"روزهای باقی‌مانده: {days_left}\n"
            "🏆 در پایان هر فصل، جوایز و مدال به برترین بازیکنان تعلق می‌گیرد."
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- بازار بازیکنان (P2P) ----------------
    elif data == "p2p_market":
        trades = list_open_trades()
        lines = [
            f"#{t['trade_id']} — {t['item_amount']} {t['item_field']} به {t['price_coin']} Coin"
            for t in trades
        ] or ["فعلاً هیچ پیشنهادی موجود نیست."]
        text = "📦 <b>بازار مستقیم بازیکنان</b>\n\n" + "\n".join(lines)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ ثبت پیشنهاد فروش LIBER", callback_data="p2p_sell_offer")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "p2p_sell_offer":
        # پیشنهاد پیش‌فرض نمونه: فروش ۲۰ LIBER به قیمت بازار فعلی ضربدر ۲۰
        amount = 20
        price = round(get_market_price() * amount * 1.05, 2)
        success, msg = create_trade_offer(user_id, "liber", amount, price)
        await query.message.edit_text(msg, reply_markup=back_keyboard("p2p_market"))

    elif data.startswith("p2p_buy_"):
        trade_id = int(data.split("_")[-1])
        success, msg = accept_trade_offer(user_id, trade_id)
        await query.message.edit_text(msg, reply_markup=back_keyboard("p2p_market"))

    # ---------------- بازار پیش‌بینی قیمت ----------------
    elif data == "prediction":
        price = get_market_price()
        text = (
            "🎟 <b>بازار پیش‌بینی قیمت LIBER</b>\n\n"
            f"📈 قیمت فعلی: {price} Coin\n"
            f"💰 مبلغ شرط: {PREDICTION_BET_AMOUNT} Coin\n"
            f"🏆 در صورت برد: ضریب {PREDICTION_WIN_MULTIPLIER}x\n\n"
            "پیش‌بینی می‌کنی قیمت تا ساعت بعد بالا برود یا پایین بیاید؟"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 صعودی", callback_data="predict_up"),
             InlineKeyboardButton("📉 نزولی", callback_data="predict_down")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data in ("predict_up", "predict_down"):
        direction = "up" if data == "predict_up" else "down"
        success, msg = place_prediction(user_id, direction)
        await query.message.edit_text(msg, reply_markup=back_keyboard("prediction"))

    # ---------------- رقابت آنلاین ----------------
    elif data == "competition":
        comp_league = get_league_tier_name(u["rank_points"])
        days_left = get_tournament_info()
        text = (
            "⚔ <b>رقابت آنلاین LIBER</b>\n\n"
            f"⚔ لیگ رقابتی فعلی: {comp_league}\n"
            f"📊 امتیاز رنک: {u['rank_points']}\n"
            f"🎮 بازی‌ها: {u['matches_played']} | 🏆 برد: {u['matches_won']}\n"
            f"🏆 تا پایان تورنمت فصلی: {days_left} روز\n"
            f"🥇 جوایز تورنمت (۵ نفر برتر): "
            f"اول {TOURNAMENT_REWARDS[1]} LIBER، دوم {TOURNAMENT_REWARDS[2]}، سوم {TOURNAMENT_REWARDS[3]}، "
            f"چهارم {TOURNAMENT_MEDAL_REWARDS[4]} مدال، پنجم {TOURNAMENT_MEDAL_REWARDS[5]} مدال\n\n"
            "یک ورزش را انتخاب کن:"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚽ فوتبال", callback_data="sport_football"),
             InlineKeyboardButton("🏀 بسکتبال", callback_data="sport_basketball")],
            [InlineKeyboardButton("❓ راهنمای رقابت", callback_data="competition_help")],
            [InlineKeyboardButton("🔙 بازگشت به منو", callback_data="back_main")],
        ])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)

    elif data == "competition_help":
        text = (
            "❓ <b>راهنمای رقابت آنلاین</b>\n\n"
            "1️⃣ یک ورزش (فوتبال یا بسکتبال) انتخاب کن.\n"
            "2️⃣ مهارت‌هایت را با Coin ارتقا بده — هرچه مجموع قدرت بالاتر باشد شانس بردت بیشتر می‌شود.\n"
            "3️⃣ روی «شروع مسابقه رنک» بزن. اگر همان لحظه حریف واقعی منتظر باشد با او بازی می‌کنی؛ در غیر این صورت بلافاصله با هوش مصنوعی ربات مسابقه می‌دهی تا معطل نمانی.\n"
            f"4️⃣ ورودی هر مسابقه رنک {MATCH_ENTRY_FEE} LIBER است. برنده مجموع جایزه (منهای کارمزد {MATCH_POT_FEE_PERCENT}%) را می‌برد.\n"
            f"5️⃣ در هر مسابقه {MATCH_POSSESSIONS} حمله رد و بدل می‌شود؛ در هر حمله قدرت حمله‌کننده با قدرت دفاع مقایسه می‌شود — قدرت بیشتر یعنی گل بیشتر. تساوی یعنی دفاع در آخرین لحظه گل را گرفته.\n"
            "6️⃣ اگر نتیجه مساوی شود، ضربات پنالتی تعیین‌کننده است.\n"
            "7️⃣ بردها امتیاز رنک می‌دهند، باخت‌ها کم می‌کنند. امتیاز رنک تعیین‌کننده لیگ رقابتی توست: مبتدی ← حرفه‌ای ← استاد ← اژدهای آزاد ← اژدهای افسانه‌ای ← اژدهای کامل افسانه‌ای ← لیبر لجند وان.\n"
            "8️⃣ هر ۲ ماه یک‌بار تورنمت فصلی بسته می‌شود و ۵ نفر برتر جایزه می‌گیرند (سه نفر اول LIBER نقد، نفر چهارم و پنجم مدال).\n"
            f"9️⃣ 🔥 «مسابقه سخت» یک حالت پرمخاطره است: {HARD_MATCH_ENTRY_FEE} Coin ورودی می‌دهی، حریف هوش مصنوعی قوی‌تر از حد معمول شبیه‌سازی می‌شود، اما اگر ببری {HARD_MATCH_REWARD} Coin جایزه می‌گیری."
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard("competition"))

    elif data.startswith("sport_"):
        sport = data.split("_", 1)[1]
        sport_info = SPORTS[sport]
        stats_lines = [
            f"{label}: سطح {u[f'{sport}_{key}']}" for key, label in sport_info["stats"].items()
        ]
        total_power = get_total_power(user_id, sport)
        text = (
            f"{sport_info['title']} — <b>پنل مهارت‌ها</b>\n\n"
            + "\n".join(stats_lines)
            + f"\n\n🔋 مجموع قدرت: {total_power}"
        )
        stat_buttons = [
            InlineKeyboardButton(f"⬆️ {label}", callback_data=f"upgrade_{sport}_{key}")
            for key, label in sport_info["stats"].items()
        ]
        rows = [stat_buttons[i:i+2] for i in range(0, len(stat_buttons), 2)]
        rows.append([InlineKeyboardButton("🎮 شروع مسابقه رنک", callback_data=f"match_start_{sport}")])
        rows.append([InlineKeyboardButton("🔥 مسابقه سخت (پرمخاطره)", callback_data=f"match_hard_{sport}")])
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="competition")])
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=InlineKeyboardMarkup(rows))

    elif data.startswith("upgrade_"):
        _, sport, stat_key = data.split("_", 2)
        success, msg = upgrade_stat(user_id, sport, stat_key)
        await query.message.edit_text(msg, reply_markup=back_keyboard(f"sport_{sport}"))

    elif data.startswith("match_start_"):
        sport = data.split("_", 2)[2]
        if u["liber"] < MATCH_ENTRY_FEE:
            await query.message.edit_text(
                f"❌ برای شرکت در مسابقه به {MATCH_ENTRY_FEE} LIBER نیاز داری.",
                reply_markup=back_keyboard(f"sport_{sport}"),
            )
            return

        add_currency(user_id, "liber", -MATCH_ENTRY_FEE)
        status, opponent_id = join_match_queue(user_id, sport)

        if status == "waiting":
            # حریف واقعی آنلاین نبود؛ برای اینکه کاربر معطل نماند بلافاصله با هوش مصنوعی مسابقه می‌دهد
            leave_match_queue(user_id)
            match_data = simulate_match(user_id, None, sport, vs_bot=True)
            apply_match_result(user_id, 0, sport, match_data, vs_bot=True)

            result_emoji = "🏆 بردی!" if match_data["result"] == "win" else "😔 باختی."
            text = (
                f"⚔ <b>نتیجه مسابقه {SPORTS[sport]['title']} (هوش مصنوعی)</b>\n"
                "حریف واقعی آنلاین نبود، مسابقه با ربات برگزار شد:\n\n"
                + "\n".join(match_data["log"])
                + f"\n\n📊 نتیجه نهایی: شما {match_data['player_score']} — {match_data['opponent_score']} {match_data['opponent_name']}\n"
                + f"🔋 قدرت شما: {match_data['player_power']} | قدرت حریف: {match_data['opponent_power']}\n\n"
                + result_emoji
            )
            await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard(f"sport_{sport}"))
            return

        # حریف واقعی پیدا شد (حریف قبلاً هزینه ورودی خودش را هنگام ورود به صف پرداخت کرده است)
        match_data = simulate_match(user_id, opponent_id, sport, vs_bot=False)
        apply_match_result(user_id, opponent_id, sport, match_data, vs_bot=False)

        result_emoji = "🏆 بردی!" if match_data["result"] == "win" else "😔 باختی."
        text = (
            f"⚔ <b>نتیجه مسابقه {SPORTS[sport]['title']}</b>\n\n"
            + "\n".join(match_data["log"])
            + f"\n\n📊 نتیجه نهایی: شما {match_data['player_score']} — {match_data['opponent_score']} {match_data['opponent_name']}\n"
            + f"🔋 قدرت شما: {match_data['player_power']} | قدرت حریف: {match_data['opponent_power']}\n\n"
            + result_emoji
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard(f"sport_{sport}"))

        try:
            opp_result = "win" if match_data["result"] == "loss" else "loss"
            opp_emoji = "🏆 بردی!" if opp_result == "win" else "😔 باختی."
            await context.bot.send_message(
                opponent_id,
                f"⚔ مسابقه {SPORTS[sport]['title']} تمام شد!\n"
                f"نتیجه: {match_data['opponent_score']} — {match_data['player_score']}\n{opp_emoji}",
            )
        except Exception:
            pass

    elif data.startswith("match_hard_"):
        sport = data.split("_", 2)[2]
        if u["coin"] < HARD_MATCH_ENTRY_FEE:
            await query.message.edit_text(
                f"❌ برای مسابقه سخت به {HARD_MATCH_ENTRY_FEE} Coin نیاز داری.",
                reply_markup=back_keyboard(f"sport_{sport}"),
            )
            return

        add_currency(user_id, "coin", -HARD_MATCH_ENTRY_FEE)
        match_data = simulate_hard_match(user_id, sport)
        add_currency(user_id, "matches_played", 1)

        if match_data["result"] == "win":
            add_currency(user_id, "coin", HARD_MATCH_REWARD)
            add_currency(user_id, "matches_won", 1)
            add_currency(user_id, "rank_points", RANK_WIN_POINTS)
            result_emoji = f"🔥🏆 بردی! {HARD_MATCH_REWARD} Coin جایزه گرفتی!"
        else:
            u2 = get_user(user_id)
            if u2["rank_points"] + RANK_LOSS_POINTS < 0:
                set_field(user_id, "rank_points", 0)
            else:
                add_currency(user_id, "rank_points", RANK_LOSS_POINTS)
            result_emoji = f"😔 باختی و {HARD_MATCH_ENTRY_FEE} Coin را از دست دادی. حریف سخت بود!"

        text = (
            f"🔥 <b>مسابقه سخت {SPORTS[sport]['title']}</b>\n\n"
            + "\n".join(match_data["log"])
            + f"\n\n📊 نتیجه نهایی: شما {match_data['player_score']} — {match_data['opponent_score']} {match_data['opponent_name']}\n"
            + f"🔋 قدرت شما: {match_data['player_power']} | قدرت حریف: {match_data['opponent_power']}\n\n"
            + result_emoji
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard(f"sport_{sport}"))

    elif data == "match_cancel_queue":
        leave_match_queue(user_id)
        await query.message.edit_text("❌ از صف انتظار خارج شدی.", reply_markup=back_keyboard("competition"))

    # ---------------- پنل ادمین ----------------
    elif data == "admin_panel" and user_id in ADMIN_IDS:
        await show_admin_panel(query)

    elif data == "admin_force_tournament" and user_id in ADMIN_IDS:
        await maybe_resolve_tournament_forced(context.bot)
        await query.message.edit_text("✅ تورنمت فصلی برگزار شد و جوایز ارسال شد.", reply_markup=back_keyboard("admin_panel"))

    elif data == "admin_info_broadcast" and user_id in ADMIN_IDS:
        await query.message.edit_text(
            "📢 برای ارسال پیام همگانی از دستور زیر در چت استفاده کن:\n<code>/broadcast متن پیام</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard("admin_panel"),
        )

    elif data == "admin_info_ban" and user_id in ADMIN_IDS:
        await query.message.edit_text(
            "🚫 برای مسدود یا رفع مسدودی کاربر از دستورات زیر استفاده کن:\n"
            "<code>/ban USER_ID</code>\n<code>/unban USER_ID</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard("admin_panel"),
        )

    # ---------------- راهنما ----------------
    elif data == "help":
        text = (
            "❓ <b>راهنمای کامل LIBER</b>\n\n"
            "🌍 <b>امپراتوری من:</b> کشورت رو بساز، مالیات جمع کن، دفاع و فناوری‌ات رو ارتقا بده.\n"
            "💹 <b>بازار زنده:</b> LIBER بخر و بفروش؛ قیمت هر ساعت خودش تغییر می‌کنه.\n"
            "🏦 <b>بانک مرکزی:</b> سپرده بذار سود بگیر، یا وام بگیر.\n"
            "🎁 <b>صندوق شانس:</b> با Coin/LIBER/Diamond صندوق باز کن و جایزه شانسی بگیر.\n"
            "🎯 <b>مأموریت روزانه:</b> هر روز با یک کلیک XP و LIBER رایگان بگیر.\n"
            "⚔ <b>رقابت آنلاین:</b> فوتبال یا بسکتبال انتخاب کن، مهارت‌هاتو ارتقا بده و رنک‌بازی کن.\n"
            "⭐ <b>VIP:</b> با Diamond یا با تلگرام استارز اشتراک ویژه بگیر و مزایای بیشتر داشته باش.\n"
            "🌟 <b>خرید با استارز:</b> از فروشگاه می‌تونی مستقیم با تلگرام استارز LIBER یا اشتراک بخری.\n"
            "☎ <b>پشتیبانی:</b> هر مشکلی داشتی از دکمه پشتیبانی پیام بده، مستقیم برای ادمین ارسال می‌شه.\n\n"
            "هر سوالی داشتی از پشتیبانی بپرس! 💬"
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # ---------------- پشتیبانی ----------------
    elif data == "support":
        context.user_data["awaiting_support"] = True
        text = (
            "☎ <b>پشتیبانی LIBER</b>\n\n"
            "پیام خود را همینجا در چت تایپ و ارسال کن؛ پیام شما مستقیماً برای ادمین ارسال می‌شود "
            "و به‌زودی پاسخ داده می‌شود.\n\n"
            "برای خرید اشتراک هم می‌تونی همینجا بنویسی، یا مستقیم از بخش ⭐ VIP اقدام کنی."
        )
        await query.message.edit_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    else:
        placeholders = {
            "news": "📰 اخبار جهانی به‌زودی فعال می‌شود.",
            "withdraw": "📤 برداشت TON: این بخش نیازمند تایید ادمین است.",
            "deposit": "📥 واریز: به‌زودی فعال می‌شود.",
        }
        text = placeholders.get(data, "🔧 این بخش هنوز در حال توسعه است.")
        await query.message.edit_text(text, reply_markup=back_keyboard())


async def build_admin_dashboard_text():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = db()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) as cnt FROM users")
    total_users = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM users WHERE banned=1")
    banned_users = c.fetchone()["cnt"]
    c.execute("SELECT COALESCE(SUM(liber),0) as s FROM users")
    total_liber = c.fetchone()["s"]
    c.execute("SELECT COALESCE(SUM(coin),0) as s FROM users")
    total_coin = c.fetchone()["s"]
    c.execute("SELECT COUNT(*) as cnt FROM matches")
    total_matches = c.fetchone()["cnt"]
    c.execute("SELECT COUNT(*) as cnt FROM match_queue")
    queue_count = c.fetchone()["cnt"]
    c.execute("SELECT first_name, rank_points FROM users ORDER BY rank_points DESC LIMIT 1")
    top_row = c.fetchone()
    c.execute("SELECT COUNT(*) as cnt FROM users WHERE warn_count > 0")
    warned_users = c.fetchone()["cnt"]
    conn.close()

    days_left = get_tournament_info()
    top_competitor = f"{top_row['first_name']} ({top_row['rank_points']} امتیاز)" if top_row else "—"

    text = (
        "👑 <b>پنل مدیریت TITAN</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🕒 زمان سرور: {now}\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🚫 کاربران مسدود: {banned_users}\n"
        f"⚠️ کاربران دارای اخطار: {warned_users}\n"
        "━━━━━━━━━━━━━━━\n"
        f"📈 قیمت بازار: {get_market_price()} Coin\n"
        f"🪙 مجموع LIBER در اقتصاد: {round(total_liber,2)}\n"
        f"💵 مجموع Coin در اقتصاد: {round(total_coin,2)}\n"
        "━━━━━━━━━━━━━━━\n"
        f"⚔ مجموع مسابقات انجام‌شده: {total_matches}\n"
        f"⏳ کاربران در صف انتظار مسابقه: {queue_count}\n"
        f"🥇 برترین رقابت‌گر: {top_competitor}\n"
        f"🏆 تا پایان تورنمت فصلی: {days_left} روز"
    )
    return text


async def show_admin_panel(query):
    text = await build_admin_dashboard_text()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_panel"),
         InlineKeyboardButton("🏆 برگزاری فوری تورنمت", callback_data="admin_force_tournament")],
        [InlineKeyboardButton("📢 پیام همگانی (/broadcast)", callback_data="admin_info_broadcast"),
         InlineKeyboardButton("🚫 مسدودسازی (/ban)", callback_data="admin_info_ban")],
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
    text = await build_admin_dashboard_text()
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 بروزرسانی", callback_data="admin_panel"),
         InlineKeyboardButton("🏆 برگزاری فوری تورنمت", callback_data="admin_force_tournament")],
    ])
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


async def setbio_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_banned(user_id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /setbio متن بیوگرافی تو\nمثال: /setbio عاشق اقتصاد و فوتبالم ⚽💰")
        return
    bio_text = " ".join(context.args)
    if contains_banned_word(bio_text):
        await update.message.reply_text("⚠️ این متن شامل الفاظ نامناسب است و ذخیره نشد.")
        return
    if len(bio_text) > 150:
        bio_text = bio_text[:150]
    set_field(user_id, "bio", bio_text)
    await update.message.reply_text("✅ بیوگرافی شما بروزرسانی شد. از منوی «پروفایل من» می‌توانی آن را ببینی.")


async def text_message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اول پیام پشتیبانی را بررسی می‌کند، سپس فیلتر فحش ساده را روی پیام‌های متنی کاربر اجرا می‌کند."""
    if not update.message or not update.message.text:
        return
    user_id = update.effective_user.id
    if is_banned(user_id):
        return

    # ---------------- پیام پشتیبانی ----------------
    if context.user_data.get("awaiting_support"):
        context.user_data["awaiting_support"] = False
        u = get_user(user_id)
        username_display = f"@{u['username']}" if u and u["username"] else "بدون نام کاربری"
        forward_text = (
            "📩 <b>پیام پشتیبانی جدید</b>\n\n"
            f"👤 نام: {update.effective_user.first_name}\n"
            f"🪪 نام کاربری: {username_display}\n"
            f"🆔 آیدی: <code>{user_id}</code>\n\n"
            f"✉️ متن پیام:\n{update.message.text}\n\n"
            f"برای پاسخ: <code>/reply {user_id} متن پاسخ</code>"
        )
        sent_to_any = False
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id, forward_text, parse_mode=ParseMode.HTML)
                sent_to_any = True
            except Exception as e:
                logger.warning(f"C