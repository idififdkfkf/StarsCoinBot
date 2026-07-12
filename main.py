import sqlite3
import logging
import random
import time
import json
from datetime import
datetime, timedelta
from telegram import (
Update,
InlineKeyboardButton,
InlineKeyboardMarkup,
LabeledPrice,
)
from telegram.constants
import ParseMode
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
format="%(asctime)s - %
(name)s - %(levelname)s - %
(message)s",
level=logging.INFO,
)
logger =
logging.getLogger("LIBER")
#
============================
============================
====
#

‫تنظیمات کلی‬

#
============================

============================
====
BOT_TOKEN =
"8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y"
ADMIN_IDS = [123456789]
FORCE_JOIN_CHANNELS = [
{"id": "@Libercoin1",
"title": "‫ کانال‬LIBER", "url":
"https://t.me/Libercoin1"},
# ‫ همینجا‬،‫کانال یا گروه دیگری داری‬

‫یک آیتم دیگر اضافه کن‬:
# {"id":

"@your_channel_2", "title":
"‫"کانال دوم‬, "url":
"https://t.me/your_channel_2
"},
]
DB_PATH = "liber.db"

MARKET_BASE_PRICE = 100
BUY_FEE_PERCENT = 2
SELL_FEE_PERCENT = 2
MARKET_FLUCTUATION_RANGE =
# ‫هر ساعت‬

(-0.07, 0.07)

MARKET_UPDATE_INTERVAL_SECON
# ‫ ساعت‬۱ ‫هر‬

DS = 3600

BANK_INTEREST_PERCENT =
1.5

# ‫سود روزانه سپرده‬

LOAN_INTEREST_PERCENT =
5

# ‫کارمزد وام‬

MAX_LOAN_MULTIPLIER =
3
‫سطح‬

# ‫سقف وام بر اساس‬

XP_PER_LEVEL = 100
DAILY_MISSION_XP = 20
DAILY_MISSION_LIBER = 8
)۱۵ ‫‌تر شد (قبًال‬
‫سخت‬
CHEST_TABLE = {

#

"free":

{"cost":

{}, "rewards": [("coin", 40,
120), ("liber", 1, 3)]},
"bronze":

{"cost":

{"coin": 350}, "rewards":
[("coin", 90, 350),
("liber", 2, 7), ("xp", 8,
18)]},
"silver":

{"cost":

{"coin": 900}, "rewards":
[("liber", 6, 20),
("diamond", 1, 2), ("xp",
15, 35)]},
"gold":

{"cost":

{"liber": 130}, "rewards":
[("liber", 18, 55),
("diamond", 2, 4), ("medal",
1, 2)]},
"diamond":

{"cost":

{"diamond": 25}, "rewards":
[("liber", 50, 140),
("diamond", 4, 8), ("medal",

1, 4)]},
}
VIP_TIERS = {
"silver":
{"cost_diamond": 50,
"xp_bonus": 1.1,
"income_bonus": 1.1},
"gold":
{"cost_diamond": 150,
"xp_bonus": 1.25,
"income_bonus": 1.25},
"diamond":
{"cost_diamond": 400,
"xp_bonus": 1.5,
"income_bonus": 1.5},
"titan":
{"cost_diamond": 1000,
"xp_bonus": 2.0,
"income_bonus": 2.0},
}

‫‪# -------------------------‬‬‫‪---------------------------‬‬‫‪-----‬‬‫اشتراک ویژه با تلگرام استارز‬

‫⭐‬

‫‪#‬‬

‫)‪(Telegram Stars‬‬

‫‪# -------------------------‬‬‫‪---------------------------‬‬‫‪-----‬‬‫‌ها به ستاره تلگرام ‪#‬‬
‫است )‪ (XTR‬قیمت‬
‫‌ها منصفانه و شفاف نگه داشته‬
‫— قیمت‬
‫‌اند‬
‫‪.‬شده‬

‫{ = ‪STAR_SUBSCRIPTIONS‬‬

‫اشتراک 🥈‬

‫{ ‪"normal":‬‬

‫" ‪"title":‬‬

‫‪٪‬درآمد ‪"benefits": "۱۰+‬‬

‫‪",‬عادی‬

‫‌ای رایگان | ‪| XP +۱۰٪‬‬
‫یک صندوق نقره‬
‫‪"durations": {30:‬‬

‫روز‪ :‬قیمت به{ ‪#‬‬

‫‪",‬در ماه‬

‫‪60, 90: 150},‬‬
‫}استارز‬
‫‪},‬‬

‫اشتراک 🐉‬

‫{ ‪"dragon":‬‬

‫" ‪"title":‬‬

‫‪٪‬درآمد ‪"benefits": "۲۵+‬‬

‫‪",‬دراگون‬

‫یک صندوق طالیی رایگان | ‪| XP +۲۵٪‬‬
‫‪",‬در ماه | قاب اختصاصی دراگون‬

‫‪"durations": {30:‬‬
‫‪150, 90: 380},‬‬
‫‪},‬‬
‫{ ‪"dragon_legend":‬‬

‫اشتراک 🐲‬

‫" ‪"title":‬‬
‫‪",‬دراگون لجند‬

‫‪٪‬درآمد ‪"benefits": "۵۰+‬‬

‫صندوق الماسی رایگان در | ‪| XP +۵۰٪‬‬

‫ماه | قاب اختصاصی لجند | ورود رایگان‬
‫‪",‬به مسابقه سخت هر هفته‬

‫‪"durations": {30:‬‬
‫‪300, 90: 750},‬‬
‫‪},‬‬
‫}‬
‫‪# --------------------------‬‬

--------------------------------#

‫ خرید‬LIBER ‫با تلگرام استارز (نرخ‬

)‫منصفانه و ثابت‬

# ---------------------------------------------------------STAR_LIBER_PACKS = {
"pack_small":

{"title":

📦 ‫"بسته کوچک‬, "liber": 100,

"

"stars": 50},

"pack_medium": {"title":

📦 ‫"بسته متوسط‬, "liber":

"

300,

"stars": 130},

"pack_large":

{"title":

📦 ‫"بسته بزرگ‬, "liber": 1000,

"

"stars": 400},

"pack_mega":

📦 ‫"بسته مگا‬,

"

"liber": 3000,

"stars": 1100},
}

{"title":

# ---------------------------------------------------------#

‫( کد هدیه‬Gift Code)

# ---------------------------------------------------------GIFT_CODE_MAX_USES_DEFAULT =
1
# ---------------------------------------------------------#

‫ برداشت‬TON

# ---------------------------------------------------------MIN_WITHDRAW_LIBER = 2000
WITHDRAW_FEE_PERCENT = 5
‫کارمزد برداشت‬
LEAGUE_THRESHOLDS = [

#

‫‪"),‬برنز 🥉‬
‫‪"),‬نقره 🥈" ‪(500,‬‬
‫‪"),‬طال 🥇" ‪(1500,‬‬
‫‪"),‬پالتینیوم 💠" ‪(4000,‬‬
‫‪"),‬الماس 💎" ‪(10000,‬‬
‫‪"),‬تایتان 👑" ‪(25000,‬‬
‫‌ای 🌌" ‪(60000,‬‬
‫‪"),‬افسانه‬
‫" ‪(0,‬‬

‫]‬

‫‪SPAM_COOLDOWN_SECONDS = 1.0‬‬
‫}{ = ‪_last_action_time‬‬
‫}{ = ‪_warn_count‬‬
‫‪# -------------------------‬‬‫‪---------------------------‬‬‫‪-----‬‬‫سیستم هوشمند ضد تقلب‬

‫‪#‬‬

‫‪# -------------------------‬‬‫‪---------------------------‬‬‫‪-----‬‬‫‪CHEAT_ACTION_WINDOW_SECONDS‬‬
‫بازه زمانی بررسی ‪#‬‬

‫‪= 10‬‬

‫= ‪CHEAT_ACTION_MAX_IN_WINDOW‬‬
‫بیش از این تعداد کلیک در ‪#‬‬

‫‪12‬‬

‫بازه = مشکوک‬

‫= ‪CHEAT_FLAG_BAN_THRESHOLD‬‬
‫بعد از این تعداد پرچم ‪#‬‬

‫‪4‬‬

‫‌شود‬
‫مشکوک‪ ،‬خودکار مسدود می‬

‫‪SUSPICIOUS_LIBER_GAIN_THRESH‬‬
‫افزایش ناگهانی بیش ‪#‬‬

‫‪OLD = 2000‬‬

‫از این مقدار در یک عملیات‪ ،‬بررسی‬
‫‌شود‬
‫می‬

‫‪#‬‬

‫}{ = ‪_action_log‬‬

‫]‪user_id -> [timestamps‬‬
‫‪#‬‬

‫}{ = ‪_cheat_flags‬‬
‫‪user_id -> count‬‬

‫‪# -------------------------‬‬‫‪---------------------------‬‬‫‪-----‬‬‫فروشگاه‬

‫‪#‬‬

‫‪# -------------------------‬‬‫‪----------------------------‬‬

-----SHOP_ITEMS = {
"energy_50":

⚡ ۵۰ ‫"انرژی‬,

{"title":

"

{"coin": 200},

"cost":
"give":

("energy", 50)},
"energy_200":

⚡ ۲۰۰ ‫"انرژی‬,

{"title":

"

"cost":

{"coin": 700},

"give":

("energy", 200)},
"diamond_10":

💎 ۱۰ ‫"الماس‬,

{"title":

"

{"liber": 150},

"cost":
"give":

("diamond", 10)},
"diamond_50":

💎 ۵۰ ‫"الماس‬,

{"title":

"

{"liber": 650},

"cost":
"give":

("diamond", 50)},
"frame_gold":

🖼 ‫"قاب طالیی‬,

{"title":

"

{"diamond": 30},

"cost":
"give":

("frame", "gold")},

"frame_neon":

{"title":

🖼 ‫"قاب نئونی‬,

"

"cost":

{"diamond": 60},

"give":

("frame", "neon")},
}
# ---------------------------------------------------------#

‫دستاوردها‬

# ---------------------------------------------------------ACHIEVEMENTS = {
"first_trade":

🥇 ‫"اولین معامله‬,

{"title": "

"desc": "‫اولین خرید یا فروش در‬

‫"بازار‬, "reward_liber": 20},
"trader_100":

📈

{"title": "
‫‌گر‬
‫"معامله‬,

‫"بار در بازار معامله کن‬,

"desc": "۱۰۰

"reward_liber": 200},
"chest_opener":

🎁

{"title": "
‫‌باز‬
‫"صندوق‬,

"desc": "۵۰

‫"صندوق باز کن‬,
"reward_diamond": 20},
"country_founder":

🏛

{"title": "
‫‌گذار‬
‫"بنیان‬,

"desc": "‫یک‬

‫"کشور بساز‬,
"reward_coin": 300},
"level_10":

⭐ ‫سطح‬

{"title": "
۱۰",

"desc": "‫به‬

‫ برس‬۱۰ ‫"سطح‬,
"reward_diamond": 30},
"level_25":

🌟 ‫سطح‬

{"title": "
۲۵",

"desc": "‫به‬

‫ برس‬۲۵ ‫"سطح‬,
"reward_diamond": 100},
"referral_10":

👥

{"title": "
‫‌کننده‬
‫"جذب‬,

"desc": "۱۰

‫"نفر دعوت کن‬,

"reward_liber": 300},
"alliance_join":

🤝

{"title": "
‫‌پیمان‬
‫"هم‬,

"desc": "‫به‬

‫"یک اتحاد بپیوند‬,

"reward_coin": 200},
"vip_member":

👑 ‫عضو‬

{"title": "
VIP",

"desc": "‫هر‬

‫ سطحی از‬VIP ‫"را بخر‬,

"reward_medal": 5},
"bank_saver":

🏦 ‫پس‌انداز‬

{"title": "
‫"کن‬,

"desc": "۱۰۰۰ Coin

‫"سپرده بگذار‬,

"reward_coin": 150},
}
# --------------------------

--------------------------------#

‫ فناوری‬/ ‫تحقیقات‬

# ---------------------------------------------------------RESEARCH_TREE = [
{"level": 1, "name":
"‫"کشاورزی مدرن‬, "cost_coin":
300,

"effect": "production

+10%"},
{"level": 2, "name":
"‫‌کاری پیشرفته‬
‫"معدن‬, "cost_coin":
700,

"effect": "production

+20%"},
{"level": 3, "name":
"‫"انرژی خورشیدی‬, "cost_coin":
1500, "effect": "production
+35%"},
{"level": 4, "name":
"‫"هوش مصنوعی صنعتی‬,
"cost_coin": 3000, "effect":

"production +50%"},
{"level": 5, "name":
"‫"فناوری کوانتومی‬, "cost_coin":

6000, "effect": "production
+75%"},
]
# ---------------------------------------------------------#

‫دفاع نظامی‬

# ---------------------------------------------------------DEFENSE_UPGRADE_BASE_COST =
250
DEFENSE_UPGRADE_GROWTH = 1.6
# ---------------------------------------------------------#

‫اکتشاف‬

# ---------------------------------------------------------EXPLORATION_MIN_LEVEL = 5
EXPLORATION_ENERGY_COST = 20
EXPLORATION_REWARDS = [
("coin", 50, 300),
("liber", 5, 40),
("diamond", 0, 3),
]
# ---------------------------------------------------------#

)‫‌کند‬
‫بازار سیاه (روزانه تغییر می‬

# ---------------------------------------------------------BLACK_MARKET_POOL = [

👑 ‫آیتم افسانه‌ای‬

{"title": "

‫"کمیاب‬, "cost": {"diamond":

80}, "give": ("medal", 10)},

💎 ‫پیشنهاد ویژه‬

{"title": "
‫"الماس‬,

"cost": {"liber":

500}, "give": ("diamond",
40)},

🎁 ‫جعبه رمز و‬

{"title": "
‫"راز‬,

"cost": {"coin":

1000}, "give": ("liber",
60)},

🏅 ‫مدال‬

{"title": "
‫"کمیاب‬,

"cost":

{"diamond": 40}, "give":
("medal", 5)},
]
# ---------------------------------------------------------#

‫فصل بازی‬

# ---------------------------------------------------------SEASON_LENGTH_DAYS = 90

# ---------------------------------------------------------#

‫معامله مستقیم بین بازیکنان‬

# ---------------------------------------------------------TRADE_FEE_PERCENT = 3
# ---------------------------------------------------------#

‫‌بینی قیمت‬
‫بازار پیش‬

# ---------------------------------------------------------PREDICTION_BET_AMOUNT = 50
PREDICTION_WIN_MULTIPLIER =
1.8
# --------------------------

--------------------------------#

‫ قابل‬- ‫فیلتر فحش (نمونه ساده‬

)‫گسترش‬

# ---------------------------------------------------------BANNED_WORDS = ["kosekhar",
"fuckyou"]
MAX_WARN_BEFORE_BAN = 5
# ---------------------------------------------------------#

)‫ بسکتبال‬/ ‫رقابت آنالین (فوتبال‬

# ---------------------------------------------------------SPORTS = {
"football": {

⚽ ‫"فوتبال‬,

"title": "
"stats": {

❤️ ‫"جون‬,
"accuracy": "🎯
"intensity": "🔥
"shot": "🥅
"technique": "🌀
"physical": "💪
"life": "

‫"دقت‬,
‫"شدت‬,
‫"شوت‬,
‫"تکنیک‬,
‫"بدنی‬,
},
},

"basketball": {

🏀 ‫"بسکتبال‬,
"stats": {
"speed": "⚡
‫"سرعت‬,
"accuracy": "🎯
‫"دقت‬,
"press": "🧱
"title": "

‫"پرس‬,

‫💪‬

‫" ‪"physical":‬‬
‫‪",‬بدنی‬

‫‪",‬جون ️❤‬

‫" ‪"life":‬‬
‫‪},‬‬
‫‪},‬‬
‫}‬

‫‪STAT_UPGRADE_BASE_COST = 40‬‬
‫‪STAT_UPGRADE_GROWTH = 1.42‬‬
‫‌تر و ‪#‬‬
‫هرچه سطح باالتر‪ ،‬ارتقا سخت‬
‫‌شود‬
‫‌تر می‬
‫پرهزینه‬

‫‪STAT_MAX_LEVEL = 50‬‬
‫= ‪MATCH_ENTRY_FEE‬‬
‫هزینه ورود به هر ‪#‬‬

‫‪20‬‬

‫)‪ (LIBER‬مسابقه رنک‬

‫= ‪MATCH_POT_FEE_PERCENT‬‬
‫کارمزد ربات از مجموع جایزه ‪#‬‬

‫‪18‬‬

‫‌تر شد‪ ،‬قبًال ‪)٪۱۲‬‬
‫(سخت‬

‫= ‪MATCH_POSSESSIONS‬‬
‫تعداد حمله در هر مسابقه ‪#‬‬

‫‪5‬‬

‫= ‪HARD_MATCH_ENTRY_FEE‬‬
‫هزینه ورود مسابقه سخت ‪#‬‬

‫‪4000‬‬
‫)‪(Coin‬‬

‫= ‪HARD_MATCH_REWARD‬‬
‫جایزه برد مسابقه ‪#‬‬

‫‪8000‬‬
‫)‪ (Coin‬سخت‬

‫= ‪HARD_MATCH_OPPONENT_BOOST‬‬
‫‌تر از خودت ‪#‬‬
‫حریف سخت قوی‬

‫‪1.35‬‬

‫‌شود‬
‫‌سازی می‬
‫شبیه‬

‫‪RANK_WIN_POINTS = 15‬‬
‫‪RANK_DRAW_POINTS = 6‬‬
‫‪RANK_LOSS_POINTS = -5‬‬
‫[ = ‪LEAGUE_TIERS‬‬

‫‪"),‬مبتدی 🥉‬
‫‪(100,‬‬
‫‌ای 🥈"‬
‫‪"),‬حرفه‬
‫‪(300,‬‬
‫‪"),‬استاد 🥇"‬
‫‪(700,‬‬
‫‪"),‬اژدهای آزاد 🐉"‬
‫اژدهای 🐲" ‪(1500,‬‬
‫‌ای‬
‫‪"),‬افسانه‬
‫اژدهای کامل 👑🐉" ‪(3000,‬‬
‫"‬

‫‪(0,‬‬

‫‌ای‬
‫)"افسانه‬,
(6000,
]

💎 ‫)"لیبر لجند وان‬,

"

TOURNAMENT_LENGTH_DAYS =
# ‫ ماه‬۲ ‫هر‬

60

TOURNAMENT_REWARDS = {1:
700, 2: 500, 3: 300}

#

LIBER (‫)نفرات اول تا سوم‬
TOURNAMENT_MEDAL_REWARDS =
{4: 100, 5: 50}
)‫(نفرات چهارم و پنجم‬

# ‫مدال‬

#
============================
============================
====
#

‫دیتابیس‬

#
============================
============================

====
def db():
conn =
sqlite3.connect(DB_PATH)
conn.row_factory =
sqlite3.Row
return conn

def init_db():
conn = db()
c = conn.cursor()
c.execute(
"""
CREATE TABLE IF NOT
EXISTS users (
user_id INTEGER
PRIMARY KEY,
username TEXT,
first_name TEXT,
joined_at TEXT,

last_seen TEXT,
login_count
INTEGER DEFAULT 1,
level INTEGER
DEFAULT 1,
xp INTEGER
DEFAULT 0,
liber REAL
DEFAULT 100,
coin REAL
DEFAULT 500,
energy INTEGER
DEFAULT 100,
diamond INTEGER
DEFAULT 0,
medal INTEGER
DEFAULT 0,
vip TEXT DEFAULT
'none',
country_name
TEXT DEFAULT '',
country_pop

INTEGER DEFAULT 0,
country_budget
REAL DEFAULT 0,
bank_deposit
REAL DEFAULT 0,
loan_amount REAL
DEFAULT 0,
alliance_id
INTEGER DEFAULT 0,
ref_by INTEGER
DEFAULT 0,
ref_count
INTEGER DEFAULT 0,
last_daily_mission TEXT
DEFAULT '',
last_daily_reward TEXT
DEFAULT '',
banned INTEGER
DEFAULT 0,
warn_count

INTEGER DEFAULT 0,
frame TEXT
DEFAULT 'normal',
trade_count
INTEGER DEFAULT 0,
chest_count
INTEGER DEFAULT 0,
research_level
INTEGER DEFAULT 0,
defense_level
INTEGER DEFAULT 0,
achievements
TEXT DEFAULT '[]',
bio TEXT DEFAULT
'',
football_life
INTEGER DEFAULT 10,
football_accuracy INTEGER
DEFAULT 10,
football_intensity INTEGER

DEFAULT 10,
football_shot
INTEGER DEFAULT 10,
football_technique INTEGER
DEFAULT 10,
football_physical INTEGER
DEFAULT 10,
basketball_speed
INTEGER DEFAULT 10,
basketball_accuracy INTEGER
DEFAULT 10,
basketball_press
INTEGER DEFAULT 10,
basketball_physical INTEGER
DEFAULT 10,
basketball_life
INTEGER DEFAULT 10,
rank_points

INTEGER DEFAULT 0,
matches_played
INTEGER DEFAULT 0,
matches_won
INTEGER DEFAULT 0,
vip_expires_at
TEXT DEFAULT ''
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS market (
id INTEGER
PRIMARY KEY,
price REAL
)
"""
)
c.execute(
"""

CREATE TABLE IF NOT
EXISTS alliances (
alliance_id
INTEGER PRIMARY KEY
AUTOINCREMENT,
name TEXT,
leader_id
INTEGER,
treasury REAL
DEFAULT 0
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS trades (
trade_id INTEGER
PRIMARY KEY AUTOINCREMENT,
seller_id
INTEGER,
item_field TEXT,

item_amount
REAL,
price_coin REAL,
status TEXT
DEFAULT 'open',
buyer_id INTEGER
DEFAULT 0,
created_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS predictions (
pred_id INTEGER
PRIMARY KEY AUTOINCREMENT,
user_id INTEGER,
direction TEXT,
start_price
REAL,
bet_amount REAL,

status TEXT
DEFAULT 'open',
created_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS season (
id INTEGER
PRIMARY KEY,
season_number
INTEGER,
started_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS black_market_stock (

id INTEGER
PRIMARY KEY,
item_index
INTEGER,
day TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS match_queue (
user_id INTEGER
PRIMARY KEY,
sport TEXT,
joined_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT

EXISTS matches (
match_id INTEGER
PRIMARY KEY AUTOINCREMENT,
player_id
INTEGER,
opponent_id
INTEGER,
sport TEXT,
player_score
INTEGER,
opponent_score
INTEGER,
result TEXT,
log TEXT,
created_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS tournament (

id INTEGER
PRIMARY KEY,
started_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS gift_codes (
code TEXT
PRIMARY KEY,
reward_field
TEXT,
reward_amount
REAL,
max_uses
INTEGER,
used_count
INTEGER DEFAULT 0,
created_by
INTEGER,

created_at TEXT
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS gift_code_redemptions
(
code TEXT,
user_id INTEGER,
redeemed_at
TEXT,
PRIMARY KEY
(code, user_id)
)
"""
)
c.execute(
"""
CREATE TABLE IF NOT
EXISTS withdrawal_requests (

request_id
INTEGER PRIMARY KEY
AUTOINCREMENT,
user_id INTEGER,
amount_liber
REAL,
fee_liber REAL,
ton_address
TEXT,
status TEXT
DEFAULT 'pending',
created_at TEXT,
processed_at
TEXT
)
"""
)
c.execute("SELECT
COUNT(*) as cnt FROM
tournament")
if c.fetchone()["cnt"]
== 0:

c.execute(
"INSERT INTO
tournament (id, started_at)
VALUES (1, ?)",
(datetime.now().strftime("%Y
-%m-%d"),),
)
c.execute("SELECT
COUNT(*) as cnt FROM
market")
if c.fetchone()["cnt"]
== 0:
c.execute("INSERT
INTO market (id, price)
VALUES (1, ?)",
(MARKET_BASE_PRICE,))
c.execute("SELECT
COUNT(*) as cnt FROM
season")
if c.fetchone()["cnt"]
== 0:

c.execute(
"INSERT INTO
season (id, season_number,
started_at) VALUES (1, 1,
?)",
(datetime.now().strftime("%Y
-%m-%d"),),
)
conn.commit()
conn.close()

def get_user(user_id):
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
users WHERE user_id=?",
(user_id,))
row = c.fetchone()
conn.close()
return row

def set_field(user_id,
field, value):
conn = db()
c = conn.cursor()
c.execute(f"UPDATE users
SET {field}=? WHERE
user_id=?", (value,
user_id))
conn.commit()
conn.close()

def add_currency(user_id,
field, amount):
conn = db()
c = conn.cursor()
c.execute(f"UPDATE users
SET {field} = {field} + ?
WHERE user_id=?", (amount,
user_id))

conn.commit()
conn.close()

def add_xp(user_id, amount):
u = get_user(user_id)
vip = u["vip"]
bonus =
VIP_TIERS.get(vip,
{}).get("xp_bonus", 1.0)
amount = int(amount *
bonus)
new_xp = u["xp"] +
amount
new_level = u["level"]
while new_xp >=
new_level * XP_PER_LEVEL:
new_xp -= new_level
* XP_PER_LEVEL
new_level += 1
conn = db()
c = conn.cursor()

c.execute("UPDATE users
SET xp=?, level=? WHERE
user_id=?", (new_xp,
new_level, user_id))
conn.commit()
conn.close()
return new_level

def get_market_price():
conn = db()
c = conn.cursor()
c.execute("SELECT price
FROM market WHERE id=1")
price = c.fetchone()
["price"]
conn.close()
return price

def set_market_price(price):
conn = db()

c = conn.cursor()
c.execute("UPDATE market
SET price=? WHERE id=1",
(price,))
conn.commit()
conn.close()

def
get_league_name(xp_total):
name =
LEAGUE_THRESHOLDS[0][1]
for threshold,
league_name in
LEAGUE_THRESHOLDS:
if xp_total >=
threshold:
name =
league_name
return name

def
create_user_if_not_exists(tg
_user, ref_by=0):
conn = db()
c = conn.cursor()
c.execute("SELECT
user_id FROM users WHERE
user_id=?", (tg_user.id,))
existing = c.fetchone()
now =
datetime.now().strftime("%Y%m-%d %H:%M:%S")
if existing:
c.execute(
"UPDATE users
SET last_seen=?,
login_count=login_count+1,
username=?, first_name=?
WHERE user_id=?",
(now,
tg_user.username or "",
tg_user.first_name or "",

tg_user.id),
)
conn.commit()
conn.close()
return False
else:
c.execute(
"""
INSERT INTO
users (user_id, username,
first_name, joined_at,
last_seen, ref_by)
VALUES (?, ?, ?,
?, ?, ?)
""",
(tg_user.id,
tg_user.username or "",
tg_user.first_name or "",
now, now, ref_by),
)
if ref_by:
c.execute(

"UPDATE
users SET
ref_count=ref_count+1,
liber=liber+50,
coin=coin+200 WHERE
user_id=?",
(ref_by,),
)
conn.commit()
conn.close()
return True

def is_banned(user_id):
u = get_user(user_id)
return bool(u and
u["banned"] == 1)

def
anti_spam_check(user_id):
now = time.time()

last =
_last_action_time.get(user_i
d, 0)
if now - last <
SPAM_COOLDOWN_SECONDS:
_warn_count[user_id]
= _warn_count.get(user_id,
0) + 1
return False,
_warn_count[user_id]
_last_action_time[user_id] =
now
_warn_count[user_id] = 0
return True, 0

def
check_click_rate_cheat(user_
id):
"""،‫با یک پنجره زمانی متحرک‬

‫بات) را‬/‫الگوی کلیک غیرطبیعی (اسکریپت‬

‫‌دهد‬
‫تشخیص می‬.

‫خروجی‬: True ‫اگر رفتار مشکوک‬

‫تشخیص داده شد‬."""

now = time.time()
log =

_action_log.setdefault(user_
id, [])
log.append(now)
# ‫فقط رویدادهای داخل بازه زمانی‬

‫‌داریم‬
‫را نگه می‬

cutoff = now CHEAT_ACTION_WINDOW_SECONDS
while log and log[0] <
cutoff:
log.pop(0)
if len(log) >
CHEAT_ACTION_MAX_IN_WINDOW:
_cheat_flags[user_id] =
_cheat_flags.get(user_id, 0)
+ 1

log.clear()
return True
return False

async def
flag_suspicious_activity(use
r_id, context, reason):
"""‫یک پرچم تخلف برای کاربر ثبت‬

،‫‌کند؛ در صورت عبور از حد مجاز‬
‫می‬
‫‌شود‬
‫خودکار مسدود می‬."""
count =

_cheat_flags.get(user_id, 0)
if count >=
CHEAT_FLAG_BAN_THRESHOLD:
set_field(user_id,
"banned", 1)
for admin_id in
ADMIN_IDS:
try:
await
context.bot.send_message(

admin_id,

🚨

f"

<b>‫<تشخیص خودکار تقلب‬/b>\n\n‫کاربر‬
<code>{user_id}</code> ‫به دلیل‬
«{reason}» "
f"‫و عبور از‬

‫‌صورت‬
‫ به‬،‫‌های مشکوک‬
‫حد مجاز پرچم‬
‫خودکار مسدود شد‬.",

parse_mode=ParseMode.HTML,
)
except
Exception:
pass
elif count > 0:
for admin_id in
ADMIN_IDS:
try:
await
context.bot.send_message(

admin_id,

⚠️

f"

<b>‫<فعالیت مشکوک‬/b>\n\n‫کاربر‬
<code>{user_id}</code>:
{reason} "

f"(‫پرچم‬
{count}/{CHEAT_FLAG_BAN_THRE
SHOLD})",
parse_mode=ParseMode.HTML,
)
except
Exception:
pass

def
check_suspicious_liber_gain(
user_id, amount,
threshold=SUSPICIOUS_LIBER_G
AIN_THRESHOLD):
"""‫ اگر مقدار یک تراکنش‬LIBER

‫‌عنوان مشکوک‬
‫ به‬،‫از حد مجاز بیشتر باشد‬
‫‌زند‬
‫عالمت می‬."""

return amount is not
None and amount >= threshold

#
============================
============================
====
#

‫دستاوردها‬

#
============================
============================
====
def
get_achievements(user_id):
u = get_user(user_id)
try:
return
json.loads(u["achievements"]

)
except Exception:
return []

def
unlock_achievement(user_id,
key):
unlocked =
get_achievements(user_id)
if key in unlocked:
return False
unlocked.append(key)
set_field(user_id,
"achievements",
json.dumps(unlocked))
ach = ACHIEVEMENTS[key]
if "reward_liber" in
ach:
add_currency(user_id,
"liber",

ach["reward_liber"])
if "reward_coin" in ach:
add_currency(user_id,
"coin", ach["reward_coin"])
if "reward_diamond" in
ach:
add_currency(user_id,
"diamond",
ach["reward_diamond"])
if "reward_medal" in
ach:
add_currency(user_id,
"medal",
ach["reward_medal"])
return True

def
check_achievements(user_id):

"""‫بررسی و باز کردن خودکار‬

.‫دستاوردهایی که شرایطشان برآورده شده‬
‫‌های تازه باز‬
‫ لیست عنوان‬:‫خروجی‬
‫شده‬."""

u = get_user(user_id)
newly_unlocked = []
checks = {
"first_trade":
u["trade_count"] >= 1,
"trader_100":
u["trade_count"] >= 100,
"chest_opener":
u["chest_count"] >= 50,
"country_founder":
bool(u["country_name"]),
"level_10":
u["level"] >= 10,
"level_25":
u["level"] >= 25,
"referral_10":
u["ref_count"] >= 10,

"alliance_join":
u["alliance_id"] != 0,
"vip_member":
u["vip"] != "none",
"bank_saver":
u["bank_deposit"] >= 1000,
}
for key, condition in
checks.items():
if condition and
unlock_achievement(user_id,
key):
newly_unlocked.append(ACHIEV
EMENTS[key]["title"])
return newly_unlocked

#
============================
============================
====

#

‫ فناوری‬/ ‫تحقیقات‬

#
============================
============================
====
def
get_research_info(user_id):
u = get_user(user_id)
level =
u["research_level"]
if level >=
len(RESEARCH_TREE):
return None
return
RESEARCH_TREE[level]

def
upgrade_research(user_id):
u = get_user(user_id)
info =

get_research_info(user_id)
if not info:

🔬 ‫تمام‬

return False, "

‫‌ای‬
‫سطوح تحقیقاتی را کامل کرده‬."
if u["coin"] <
info["cost_coin"]:

❌

return False, "
Coin ‫کافی نداری‬."

add_currency(user_id,

"coin", -info["cost_coin"])
set_field(user_id,
"research_level",
u["research_level"] + 1)
return True, f"

🔬 ‫تحقیق‬

«{info['name']}» ‫!تکمیل شد‬
({info['effect']})"

#
============================
============================
====

#

‫دفاع نظامی‬

#
============================
============================
====
def
get_defense_upgrade_cost(cur
rent_level):
return
round(DEFENSE_UPGRADE_BASE_C
OST *
(DEFENSE_UPGRADE_GROWTH **
current_level), 2)

def
upgrade_defense(user_id):
u = get_user(user_id)
cost =
get_defense_upgrade_cost(u["
defense_level"])

if u["coin"] < cost:
return False, f"
‫{ برای ارتقا به‬cost} Coin ‫نیاز‬

❌

‫داری‬."

add_currency(user_id,
"coin", -cost)
set_field(user_id,
"defense_level",
u["defense_level"] + 1)
return True, f"
‫کشورت به سطح‬

🛡 ‫دفاع‬

{u['defense_level']+1} ‫ارتقا‬
‫یافت‬."

#
============================
============================
====
#

‫اکتشاف‬

#
============================

============================
====
def do_exploration(user_id):
u = get_user(user_id)
if u["level"] <
EXPLORATION_MIN_LEVEL:
return False, f"
‫اکتشاف فقط برای سطح‬

🌌

{EXPLORATION_MIN_LEVEL} ‫به باال‬
‫باز است‬."

if u["energy"] <
EXPLORATION_ENERGY_COST:

⚡

return False, "
‫انرژی کافی نداری‬."

add_currency(user_id,
"energy", EXPLORATION_ENERGY_COST)
lines = []
for field, low, high in
EXPLORATION_REWARDS:
amount =

random.randint(low, high)
if amount > 0:
add_currency(user_id, field,
amount)
lines.append(f"+
{amount} {field}")
add_xp(user_id, 15)

🌌 ‫اکتشاف‬

return True, "

‫\!موفق‬n" + "\n".join(lines)

#
============================
============================
====
#

‫بازار سیاه‬

#
============================
============================
====

def
get_black_market_today():
today =
datetime.now().strftime("%Y%m-%d")
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
black_market_stock WHERE
day=?", (today,))
row = c.fetchone()
if row:
conn.close()
return
BLACK_MARKET_POOL[row["item_
index"] %
len(BLACK_MARKET_POOL)]
index =
random.randint(0,
len(BLACK_MARKET_POOL) - 1)
c.execute("DELETE FROM
black_market_stock")

c.execute("INSERT INTO
black_market_stock
(item_index, day) VALUES (?,
?)", (index, today))
conn.commit()
conn.close()
return
BLACK_MARKET_POOL[index]

def
buy_black_market_item(user_i
d):
item =
get_black_market_today()
u = get_user(user_id)
for currency, cost in
item["cost"].items():
if u[currency] <
cost:
return False,

f"

❌ {currency} ‫کافی برای این‬

‫پیشنهاد نداری‬."
for currency, cost in
item["cost"].items():
add_currency(user_id,
currency, -cost)
field, amount =
item["give"]
add_currency(user_id,
field, amount)
return True, f"

🕵 ‫خرید‬

‫موفق‬: {item['title']} (+
{amount} {field})"

#
============================
============================
====
#

‫فصل بازی‬

#
============================

============================
====
def get_season_info():
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
season WHERE id=1")
row = c.fetchone()
conn.close()
started =
datetime.strptime(row["start
ed_at"], "%Y-%m-%d")
days_passed =
(datetime.now() started).days
days_left = max(0,
SEASON_LENGTH_DAYS days_passed)
return
row["season_number"],
days_left

def maybe_reset_season():
number, days_left =
get_season_info()
if days_left <= 0:
conn = db()
c = conn.cursor()
c.execute(
"UPDATE season
SET season_number=?,
started_at=? WHERE id=1",
(number + 1,
datetime.now().strftime("%Y%m-%d")),
)
conn.commit()
conn.close()
return True
return False

#
============================
============================
====
#

‫معامله مستقیم بین بازیکنان‬

#
============================
============================
====
def
create_trade_offer(seller_id
, item_field, item_amount,
price_coin):
u = get_user(seller_id)
if u[item_field] <
item_amount:

❌

return False, "

‫موجودی کافی برای این پیشنهاد نداری‬."
add_currency(seller_id,
item_field, -item_amount)
conn = db()

c = conn.cursor()
c.execute(
"INSERT INTO trades
(seller_id, item_field,
item_amount, price_coin,
created_at) VALUES (?, ?, ?,
?, ?)",
(seller_id,
item_field, item_amount,
price_coin,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)
conn.commit()
conn.close()

✅ ‫پیشنهاد‬

return True, "
‫معامله ثبت شد‬."

def
list_open_trades(limit=10):
conn = db()

c = conn.cursor()
c.execute("SELECT * FROM
trades WHERE status='open'
ORDER BY trade_id DESC LIMIT
?", (limit,))
rows = c.fetchall()
conn.close()
return rows

def
accept_trade_offer(buyer_id,
trade_id):
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
trades WHERE trade_id=? AND
status='open'", (trade_id,))
trade = c.fetchone()
if not trade:
conn.close()

❌ ‫این‬

return False, "

‫معامله دیگر در دسترس نیست‬."
buyer =
get_user(buyer_id)
if buyer["coin"] <
trade["price_coin"]:
conn.close()

❌

return False, "
Coin ‫کافی برای خرید نداری‬."
fee =

trade["price_coin"] *
TRADE_FEE_PERCENT / 100
seller_gets =
trade["price_coin"] - fee
add_currency(buyer_id,
"coin", trade["price_coin"])
add_currency(buyer_id,
trade["item_field"],
trade["item_amount"])
add_currency(trade["seller_i
d"], "coin", seller_gets)

c.execute("UPDATE trades
SET status='closed',
buyer_id=? WHERE
trade_id=?", (buyer_id,
trade_id))
conn.commit()
conn.close()
return True, f"
‫!انجام شد‬

✅ ‫معامله‬

{trade['item_amount']}
{trade['item_field']} ‫دریافت‬
‫کردی‬."

#
============================
============================
====
#

‫‌بینی قیمت‬
‫بازار پیش‬

#
============================
============================

====
def
place_prediction(user_id,
direction):
u = get_user(user_id)
if u["coin"] <
PREDICTION_BET_AMOUNT:

❌

return False, "

Coin ‫‌بندی نداری‬
‫کافی برای شرط‬."

add_currency(user_id,
"coin", PREDICTION_BET_AMOUNT)
price =
get_market_price()
conn = db()
c = conn.cursor()
c.execute(
"INSERT INTO
predictions (user_id,
direction, start_price,
bet_amount, created_at)

VALUES (?, ?, ?, ?, ?)",
(user_id, direction,
price,
PREDICTION_BET_AMOUNT,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)
conn.commit()
conn.close()
return True, f"

🎟 ‫شرط ثبت‬

‫‌بینی‬
‫ پیش‬:‫{ شد‬direction} ‫روی‬
‫{ قیمت‬price} Coin"

def resolve_predictions():
"""‫ این تابع در‬job ‫ساعتی بعد از‬

‫‌های‬
‫‌شود تا شرط‬
‫تغییر قیمت صدا زده می‬
‫باز را ببندد‬."""

new_price =

get_market_price()
conn = db()
c = conn.cursor()

c.execute("SELECT * FROM
predictions WHERE
status='open'")
open_bets = c.fetchall()
results = []
for bet in open_bets:
won =
(bet["direction"] == "up"
and new_price >
bet["start_price"]) or (
bet["direction"]
== "down" and new_price <
bet["start_price"]
)
if won:
payout =
bet["bet_amount"] *
PREDICTION_WIN_MULTIPLIER
add_currency(bet["user_id"],
"coin", payout)

results.append((bet["user_id
"], True, payout))
else:
results.append((bet["user_id
"], False, 0))
c.execute("UPDATE
predictions SET
status='closed' WHERE
pred_id=?",
(bet["pred_id"],))
conn.commit()
conn.close()
return results

#
============================
============================
====
#
#

‫فیلتر فحش‬

============================
============================
====
def
contains_banned_word(text):
if not text:
return False
lowered = text.lower()
return any(word in
lowered for word in
BANNED_WORDS)

#
============================
============================
====
#

)‫ بسکتبال‬/ ‫رقابت آنالین (فوتبال‬

#
============================
============================

====
def
get_stat_upgrade_cost(level)
:
return
int(STAT_UPGRADE_BASE_COST *
(STAT_UPGRADE_GROWTH **
level))

def upgrade_stat(user_id,
sport, stat_key):
field = f"
{sport}_{stat_key}"
u = get_user(user_id)
level = u[field]
if level >=
STAT_MAX_LEVEL:

🔒 ‫این‬

return False, "
‫مهارت به حداکثر سطح رسیده‬."
cost =

get_stat_upgrade_cost(level)
if u["coin"] < cost:
return False, f"
‫{ برای ارتقا به‬cost} Coin ‫نیاز‬

❌

‫داری‬."

add_currency(user_id,
"coin", -cost)
set_field(user_id,
field, level + 1)
return True, f"

✅ ‫مهارت‬

‫ارتقا یافت! سطح جدید‬: {level+1}
(‫هزینه‬: {cost} Coin)"

def get_total_power(user_id,
sport):
u = get_user(user_id)
stats = SPORTS[sport]
["stats"].keys()
return sum(u[f"
{sport}_{stat}"] for stat in
stats)

def
get_league_tier_name(points)
:
name = LEAGUE_TIERS[0]
[1]
for threshold, tier_name
in LEAGUE_TIERS:
if points >=
threshold:
name = tier_name
return name

#
============================
============================
====
#

‫اشتراک ویژه با تلگرام استارز‬

#
============================

============================
====
def
activate_star_subscription(u
ser_id, tier_key, days):
"""‫اشتراک را برای کاربر فعال‬

‫پایان را‬/‫‌کند و تاریخ شروع‬
‫می‬
‫‌گرداند‬
‫برمی‬."""

u = get_user(user_id)
now = datetime.now()
# ‫اگر اشتراک فعلی هنوز منقضی‬

‫‌کند‬
‫ مدت جدید را به آن اضافه می‬،‫نشده‬
current_expiry = None

if u["vip_expires_at"]:
try:
current_expiry =
datetime.strptime(u["vip_exp
ires_at"], "%Y-%m-%d
%H:%M:%S")
except ValueError:
current_expiry =

None
start_from =
current_expiry if
(current_expiry and
current_expiry > now) else
now
new_expiry = start_from
+ timedelta(days=days)
set_field(user_id,
"vip", tier_key)
set_field(user_id,
"vip_expires_at",
new_expiry.strftime("%Y-%m%d %H:%M:%S"))
return now, new_expiry

def
check_and_expire_subscriptio
n(user_id):

"""،‫اگر اشتراک منقضی شده باشد‬

‫کاربر را به حالت بدون اشتراک‬
‫‌گرداند‬
‫برمی‬."""

u = get_user(user_id)
if u["vip"] != "none"

and u["vip_expires_at"]:
try:
expiry =
datetime.strptime(u["vip_exp
ires_at"], "%Y-%m-%d
%H:%M:%S")
except ValueError:
return
if datetime.now() >
expiry:
set_field(user_id, "vip",
"none")
set_field(user_id,
"vip_expires_at", "")

def
expire_all_subscriptions_job
():
conn = db()
c = conn.cursor()
c.execute("SELECT
user_id FROM users WHERE vip
!= 'none' AND vip_expires_at
!= ''")
rows = c.fetchall()
conn.close()
for row in rows:
check_and_expire_subscriptio
n(row["user_id"])

def
grant_liber_pack(user_id,
pack_key):
pack =

STAR_LIBER_PACKS.get(pack_ke
y)
if not pack:
return 0
add_currency(user_id,
"liber", pack["liber"])
return pack["liber"]

#
============================
============================
====
#

‫( کد هدیه‬Gift Code)

#
============================
============================
====
def create_gift_code(code,
reward_field, reward_amount,
max_uses, created_by):

conn = db()
c = conn.cursor()
try:
c.execute(
"INSERT INTO
gift_codes (code,
reward_field, reward_amount,
max_uses, created_by,
created_at) VALUES (?, ?, ?,
?, ?, ?)",
(code.upper(),
reward_field, reward_amount,
max_uses, created_by,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)
conn.commit()
success = True
except
sqlite3.IntegrityError:
success = False
conn.close()

return success

def
redeem_gift_code(user_id,
code):
code =
code.strip().upper()
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
gift_codes WHERE code=?",
(code,))
gift = c.fetchone()
if not gift:
conn.close()

❌ ‫این‬

return False, "
‫کد هدیه معتبر نیست‬."

if gift["used_count"] >=
gift["max_uses"]:
conn.close()

❌

return False, "

‫ظرفیت استفاده از این کد تمام شده‬
‫است‬."

c.execute("SELECT 1 FROM
gift_code_redemptions WHERE
code=? AND user_id=?",
(code, user_id))
if c.fetchone():
conn.close()

❌ ‫قبًال‬

return False, "
‫‌ای‬
‫این کد را استفاده کرده‬."
c.execute(
"INSERT INTO

gift_code_redemptions (code,
user_id, redeemed_at) VALUES
(?, ?, ?)",
(code, user_id,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)

c.execute("UPDATE
gift_codes SET used_count =
used_count + 1 WHERE
code=?", (code,))
conn.commit()
conn.close()
add_currency(user_id,
gift["reward_field"],
gift["reward_amount"])
return True, f"
‫ !فعال شد‬+

🎉 ‫کد هدیه‬

{gift['reward_amount']}
{gift['reward_field']} ‫گرفتی‬."

#
============================
============================
====
#
#

‫مشاور هوشمند‬

🤖

============================
============================
====
def
get_smart_advice(user_id):
"""‫بر اساس وضعیت واقعی کاربر و‬

‫‌شده تولید‬
‫‌سازی‬
‫ چند پیشنهاد شخصی‬،‫اقتصاد‬
‫‌کند‬
‫می‬."""

u = get_user(user_id)
tips = []
price =
get_market_price()
if price <
MARKET_BASE_PRICE * 0.9:

📉 ‫قیمت‬

tips.append("

LIBER — ‫‌تر از حد معمول است‬
‫پایین‬

‫االن زمان خوبی برای خریدن است‬.")
elif price >
MARKET_BASE_PRICE * 1.2:

📈 ‫قیمت‬

tips.append("

‫اضافه ‪ LIBER‬باالست — اگر ‪LIBER‬‬
‫)"‪.‬داری‪ ،‬شاید بفروشی سود کنی‬

‫== ]"‪if u["bank_deposit‬‬
‫‪0 and u["coin"] > 500:‬‬

‫🏦‬

‫"‪tips.append(f‬‬

‫بدون ‪{int(u['coin'])} Coin‬‬

‫استفاده داری؛ در بانک سپرده بذار تا سود‬
‫‪{BANK_INTEREST_PERCENT}%‬‬
‫)"‪.‬بگیری‬
‫‪if not‬‬

‫هنوز 🌍‬

‫‪u["country_name"]:‬‬

‫"(‪tips.append‬‬

‫کشوری نساختی! ساختنش رایگانه و بهت‬
‫‌ده‬
‫)"‪.‬جمعیت و بودجه اولیه می‬

‫> ]"‪elif u["country_pop‬‬

‫یادت 💰‬

‫‪0:‬‬

‫"(‪tips.append‬‬

‫نره هر روز مالیات کشورت رو جمع کنی‪،‬‬
‫‌گیری ‪ Coin‬و ‪ XP‬رایگان‬
‫)"‪.‬می‬

research_info =
get_research_info(user_id)
if research_info and
u["coin"] >=
research_info["cost_coin"]:

🔬

tips.append(f"
‫‌تونی همین االن تحقیق‬
‫می‬

«{research_info['name']}» ‫رو‬
‫با‬

{research_info['cost_coin']}
Coin ‫کامل کنی‬.")
if u["defense_level"] <
3:

🛡 ‫سطح‬

tips.append("

‫‌تر‬
‫دفاعت پایینه؛ ارتقاش بده تا کشورت امن‬
‫بشه‬.")

football_power =
get_total_power(user_id,
"football")
basketball_power =

get_total_power(user_id,
"basketball")
if max(football_power,
basketball_power) < 80:
tips.append("⚔ ‫قدرت‬

‫‌ات هنوز کمه — چند تا مهارت‬
‫رقابتی‬

‫‌ها بیشتر‬
‫ورزشی رو ارتقا بده تا تو مسابقه‬
‫ببری‬.")

today =
datetime.now().strftime("%Y%m-%d")
if
u["last_daily_reward"] !=
today:

🎁 ‫جایزه‬

tips.append("

‫ از‬،‫‌ات رو هنوز نگرفتی — رایگانه‬
‫روزانه‬
‫)"!دستش نده‬
if

u["last_daily_mission"] !=
today:

🎯

tips.append("

‫مأموریت روزانه هم هنوز باز نشده‪ ،‬برو‬
‫)"‪.‬کاملش کن‬

‫‪if u["vip"] == "none":‬‬

‫با فعال ⭐‬

‫"(‪tips.append‬‬

‫بیشتری ‪ XP‬درآمد و ‪ VIP،‬کردن اشتراک‬
‫‌گیری‬
‫)"‪.‬می‬

‫👍‬

‫‪if not tips:‬‬

‫"(‪tips.append‬‬

‫وضعیتت خیلی خوبه! همینطور با مسابقه‪،‬‬
‫)"‪.‬صندوق و مأموریت روزانه پیش برو‬
‫‪return tips‬‬

‫‪#‬‬
‫============================‬
‫============================‬
‫====‬
‫‪ TON‬برداشت‬

‫‪#‬‬
‫‪#‬‬

============================
============================
====
def
create_withdraw_request(user
_id, amount, ton_address):
u = get_user(user_id)
if amount <
MIN_WITHDRAW_LIBER:
return False, f"
‫حداقل مبلغ برداشت‬

❌

{MIN_WITHDRAW_LIBER} LIBER
‫است‬."
if u["liber"] < amount:

❌

return False, "
‫ موجودی‬LIBER ‫کافی نیست‬."

fee = round(amount *
WITHDRAW_FEE_PERCENT / 100,
2)
add_currency(user_id,

"liber", -amount)

# ‫مبلغ فورًا‬

‫‌شود تا امانتی نزد‬
‫از حساب کسر می‬
‫سیستم بماند‬

conn = db()
c = conn.cursor()
c.execute(
"INSERT INTO

withdrawal_requests
(user_id, amount_liber,
fee_liber, ton_address,
created_at) VALUES (?, ?, ?,
?, ?)",
(user_id, amount,
fee, ton_address,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)
request_id = c.lastrowid
conn.commit()
conn.close()
return True, request_id

def
list_user_withdrawals(user_i
d, limit=10):
conn = db()
c = conn.cursor()
c.execute(
"SELECT * FROM
withdrawal_requests WHERE
user_id=? ORDER BY
request_id DESC LIMIT ?",
(user_id, limit),
)
rows = c.fetchall()
conn.close()
return rows

def
list_pending_withdrawals(lim
it=20):
conn = db()

c = conn.cursor()
c.execute("SELECT * FROM
withdrawal_requests WHERE
status='pending' ORDER BY
request_id ASC LIMIT ?",
(limit,))
rows = c.fetchall()
conn.close()
return rows

def
approve_withdraw_request(req
uest_id):
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
withdrawal_requests WHERE
request_id=? AND
status='pending'",
(request_id,))
req = c.fetchone()

if not req:
conn.close()
return False, None
c.execute(
"UPDATE
withdrawal_requests SET
status='approved',
processed_at=? WHERE
request_id=?",
(datetime.now().strftime("%Y
-%m-%d %H:%M:%S"),
request_id),
)
conn.commit()
conn.close()
return True, req

def
reject_withdraw_request(requ
est_id):

conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
withdrawal_requests WHERE
request_id=? AND
status='pending'",
(request_id,))
req = c.fetchone()
if not req:
conn.close()
return False, None
c.execute(
"UPDATE
withdrawal_requests SET
status='rejected',
processed_at=? WHERE
request_id=?",
(datetime.now().strftime("%Y
-%m-%d %H:%M:%S"),
request_id),
)

conn.commit()
conn.close()
# ‫بازگرداندن مبلغ به کاربر چون‬

‫درخواست رد شده‬

add_currency(req["user_id"],
"liber",
req["amount_liber"])
return True, req

#
============================
============================
====
#

‫اخبار جهانی‬

#

📰

============================
============================
====
def get_world_news():

"""‫یک فید خبری زنده از‬

‫‌سازد‬
‫رویدادهای واقعی درون بازی می‬."""
lines = []
price =
get_market_price()
lines.append(f"

💹 ‫قیمت‬

‫‌ای‬
‫ لحظه‬LIBER: {price} Coin")
number, season_days_left
= get_season_info()
lines.append(f"
{number} ‫— فعلی‬

📆 ‫فصل‬

{season_days_left} ‫روز تا‬
‫پایان‬.")

tournament_days_left =
get_tournament_info()
lines.append(f"

🏆

{tournament_days_left} ‫روز تا‬
‫پایان تورنمت رقابتی فصلی‬.")

item =
get_black_market_today()
lines.append(f"
‫ویژه بازار سیاه امروز‬:

🕵 ‫پیشنهاد‬

{item['title']}")
conn = db()
c = conn.cursor()
c.execute("SELECT
first_name, liber FROM users
ORDER BY liber DESC LIMIT
1")
richest = c.fetchone()
if richest:

👑

lines.append(f"
‫ثروتمندترین بازیکن این لحظه‬:

{richest['first_name']} ‫با‬
{richest['liber']} LIBER")
c.execute("SELECT
first_name, rank_points FROM
users ORDER BY rank_points

DESC LIMIT 1")
top_fighter =
c.fetchone()
if top_fighter and
top_fighter["rank_points"] >
0:
lines.append(f"⚔
‫‌گر این لحظه‬
‫برترین رقابت‬:

{top_fighter['first_name']} ‫با‬
{top_fighter['rank_points']}
‫)"امتیاز رنک‬
c.execute("SELECT
COUNT(*) as cnt FROM
matches")
total_matches =
c.fetchone()["cnt"]
lines.append(f"
‫مسابقات برگزارشده تا االن‬:

🎮 ‫مجموع‬

{total_matches}")
c.execute("SELECT

COUNT(*) as cnt FROM users
WHERE country_name != ''")
total_countries =
c.fetchone()["cnt"]
lines.append(f"

🌍 ‫تعداد‬

‫‌شده در جهان‬
‫ کشورهای ساخته‬LIBER:
{total_countries}")
conn.close()
return lines

def
join_match_queue(user_id,
sport):
"""‫اگر حریفی در صف باشد‬

‫ وگرنه‬،‫‌شود‬
‫‌سازی می‬
‫بالفاصله مسابقه شبیه‬
‫‌گیرد‬
‫کاربر در صف انتظار قرار می‬."""
conn = db()

c = conn.cursor()
c.execute("SELECT * FROM
match_queue WHERE sport=?

AND user_id != ? LIMIT 1",
(sport, user_id))
opponent_row =
c.fetchone()
if opponent_row:
c.execute("DELETE
FROM match_queue WHERE
user_id=?",
(opponent_row["user_id"],))
conn.commit()
conn.close()
opponent_id =
opponent_row["user_id"]
return "matched",
opponent_id
else:
c.execute("DELETE
FROM match_queue WHERE
user_id=?", (user_id,))
c.execute(
"INSERT INTO

match_queue (user_id, sport,
joined_at) VALUES (?, ?,
?)",
(user_id, sport,
datetime.now().strftime("%Y%m-%d %H:%M:%S")),
)
conn.commit()
conn.close()
return "waiting",
None

def
leave_match_queue(user_id):
conn = db()
c = conn.cursor()
c.execute("DELETE FROM
match_queue WHERE
user_id=?", (user_id,))
conn.commit()
conn.close()

def
_run_possession_battle(playe
r_power, opponent_power,
opponent_name):
"""‫‌سازی‬
‫هسته مشترک شبیه‬

‫‌حمله؛ هم برای مسابقه رنک هم‬
‫‌به‬
‫حمله‬
‫‌شود‬
‫مسابقه سخت استفاده می‬."""
player_score = 0
opponent_score = 0
log_lines = []
attacker = "player"
for possession in
range(1, MATCH_POSSESSIONS +
1):
if attacker ==
"player":
atk_power =
player_power +
random.randint(-10, 10)

def_power =
opponent_power +
random.randint(-10, 10)
atk_label = "‫"شما‬
else:
atk_power =
opponent_power +
random.randint(-10, 10)
def_power =
player_power +
random.randint(-10, 10)
atk_label =
opponent_name

log_lines.append(f"

🔵 ‫حمله‬

{possession}: {atk_label} ‫توپ‬
‫را ارسال کرد‬...")

if atk_power >

def_power:
log_lines.append(f"

⚽ ‫!گل شد‬

({atk_power} ‫در برابر‬
{def_power})")
if attacker ==
"player":
player_score
+= 1
else:
opponent_score += 1
elif atk_power ==
def_power:
log_lines.append(f"

⚔️ ‫قدرت‬

‫{( مساوی بود‬atk_power} =

{def_power}) — ‫دفاع در آخرین‬
‫لحظه گل را گرفت‬.")
else:
log_lines.append(f"

🛡 ‫دفاع‬

‫{( موفق بود‬def_power} ‫در برابر‬
{atk_power})")

attacker =
"opponent" if attacker ==
"player" else "player"
if player_score ==
opponent_score:
log_lines.append("⏱
‫نتیجه مساوی شد — ضربات پنالتی‬
‫‌کننده‬
‫تعیین‬...")

if player_power +
random.randint(0, 15) >=
opponent_power +
random.randint(0, 15):
player_score +=
1
else:
opponent_score
+= 1
result = "win" if
player_score >
opponent_score else "loss"

return player_score,
opponent_score, result,
log_lines

def
simulate_match(player_id,
opponent_id, sport,
vs_bot=False):
"""‫‌سازی مسابقه رنک عادی (با‬
‫شبیه‬

‫حریف واقعی یا هوش مصنوعی‬
)‫متعادل‬."""
player_power =

get_total_power(player_id,
sport)
if vs_bot:
opponent_power =
max(20, player_power +
random.randint(-15, 15))
opponent_name = "
‫"حریف هوش مصنوعی‬
else:

🤖

opponent_power =
get_total_power(opponent_id,
sport)
opp_user =
get_user(opponent_id)
opponent_name =
opp_user["first_name"] or
"‫"حریف‬
player_score,
opponent_score, result,
log_lines =
_run_possession_battle(
player_power,
opponent_power,
opponent_name
)
return {
"player_score":
player_score,
"opponent_score":

opponent_score,
"result": result,
"log": log_lines,
"opponent_name":
opponent_name,
"player_power":
player_power,
"opponent_power":
opponent_power,
}

def
simulate_hard_match(player_i
d, sport):
"""/‫‌سازی مسابقه سخت‬
‫شبیه‬

‫پرمخاطره برابر حریف هوش مصنوعی‬
‫‌تر‬
‫قوی‬."""

player_power =

get_total_power(player_id,
sport)
opponent_power = max(30,

int(player_power *
HARD_MATCH_OPPONENT_BOOST) +
random.randint(0, 20))

🔥 ‫حریف‬

opponent_name = "
)‫"سخت (هوش مصنوعی‬
player_score,

opponent_score, result,
log_lines =
_run_possession_battle(
player_power,
opponent_power,
opponent_name
)
return {
"player_score":
player_score,
"opponent_score":
opponent_score,
"result": result,
"log": log_lines,

"opponent_name":
opponent_name,
"player_power":
player_power,
"opponent_power":
opponent_power,
}

def
apply_match_result(player_id
, opponent_id, sport,
match_data, vs_bot=False):
conn = db()
c = conn.cursor()
c.execute(
"INSERT INTO matches
(player_id, opponent_id,
sport, player_score,
opponent_score, result, log,
created_at) VALUES (?, ?, ?,
?, ?, ?, ?, ?)",

(
player_id,
opponent_id if
not vs_bot else 0,
sport,
match_data["player_score"],
match_data["opponent_score"]
,
match_data["result"],
json.dumps(match_data["log"]
, ensure_ascii=False),
datetime.now().strftime("%Y%m-%d %H:%M:%S"),
),
)
conn.commit()
conn.close()

add_currency(player_id,
"matches_played", 1)
if not vs_bot:
add_currency(opponent_id,
"matches_played", 1)
pot = MATCH_ENTRY_FEE *
(1 if vs_bot else 2)
fee = pot *
MATCH_POT_FEE_PERCENT / 100
prize = round(pot - fee,
2)
if match_data["result"]
== "win":
add_currency(player_id,
"liber", prize)
add_currency(player_id,

"matches_won", 1)
add_currency(player_id,
"rank_points",
RANK_WIN_POINTS)
if not vs_bot:
add_currency(opponent_id,
"rank_points",
RANK_LOSS_POINTS)
else:
if not vs_bot:
add_currency(opponent_id,
"liber", prize)
add_currency(opponent_id,
"matches_won", 1)
add_currency(opponent_id,
"rank_points",
RANK_WIN_POINTS)

add_currency(player_id,
"rank_points",
RANK_LOSS_POINTS)

‫رنک‬

# ‫جلوگیری از منفی شدن امتیاز‬
for uid in ([player_id]

if vs_bot else [player_id,
opponent_id]):
u2 = get_user(uid)
if u2["rank_points"]
< 0:
set_field(uid,
"rank_points", 0)

def get_tournament_info():
conn = db()
c = conn.cursor()
c.execute("SELECT * FROM
tournament WHERE id=1")

row = c.fetchone()
conn.close()
started =
datetime.strptime(row["start
ed_at"], "%Y-%m-%d")
days_passed =
(datetime.now() started).days
days_left = max(0,
TOURNAMENT_LENGTH_DAYS days_passed)
return days_left

async def
maybe_resolve_tournament(bot
):
days_left =
get_tournament_info()
if days_left > 0:
return
await

_resolve_tournament_now(bot)

async def
maybe_resolve_tournament_for
ced(bot):
await
_resolve_tournament_now(bot)

async def
_resolve_tournament_now(bot)
:
conn = db()
c = conn.cursor()
c.execute("SELECT
user_id, first_name,
rank_points FROM users ORDER
BY rank_points DESC LIMIT
5")
top5 = c.fetchall()
conn.close()

for i, row in
enumerate(top5, start=1):
if
row["rank_points"] <= 0:
continue
liber_reward =
TOURNAMENT_REWARDS.get(i, 0)
medal_reward =
TOURNAMENT_MEDAL_REWARDS.get
(i, 0)
if liber_reward:
add_currency(row["user_id"],
"liber", liber_reward)
if medal_reward:
add_currency(row["user_id"],
"medal", medal_reward)
if liber_reward or
medal_reward:
reward_text = f"

{liber_reward} LIBER" if
liber_reward else f"
{medal_reward} ‫"مدال‬
try:

await
bot.send_message(
row["user_id"],

🏆

f"

‫{ تبریک! در تورنمت فصلی رتبه‬i} ‫را‬

‫{ کسب کردی و‬reward_text} ‫جایزه‬
‫"!گرفتی‬,

)
except
Exception:
pass
conn = db()
c = conn.cursor()
c.execute("UPDATE
tournament SET started_at=?
WHERE id=1",

(datetime.now().strftime("%Y
-%m-%d"),))
c.execute("UPDATE users
SET rank_points=0")
conn.commit()
conn.close()

def
get_competition_leaderboard(
limit=10):
conn = db()
c = conn.cursor()
c.execute(
"SELECT first_name,
rank_points, matches_played,
matches_won FROM users "
"WHERE rank_points >
0 ORDER BY rank_points DESC
LIMIT ?",
(limit,),
)

rows = c.fetchall()
conn.close()
return rows

def
get_recent_matches(limit=5):
conn = db()
c = conn.cursor()
c.execute(
"SELECT m.*,
u1.first_name as
player_name, u2.first_name
as opponent_name "
"FROM matches m "
"LEFT JOIN users u1
ON m.player_id = u1.user_id
"
"LEFT JOIN users u2
ON m.opponent_id =
u2.user_id "
"ORDER BY m.match_id

DESC LIMIT ?",
(limit,),
)
rows = c.fetchall()
conn.close()
return rows

#
============================
============================
====
#
#

‫کیبوردها‬

============================
============================
====
def
main_menu_keyboard(user_id=N
one):
today =

datetime.now().strftime("%Y%m-%d")
daily_badge = ""
mission_badge = ""
u = get_user(user_id) if
user_id else None
if u:
if
u["last_daily_reward"] !=
today:
daily_badge = "

🔴"

if

u["last_daily_mission"] !=
today:
"

🔴"

mission_badge =

buttons = [

👤

[InlineKeyboardButton("
‫"پروفایل من‬,

callback_data="profile"),

🌍

InlineKeyboardButton("
‫"امپراتوری من‬,

callback_data="country"),

💹 ‫بازار‬

InlineKeyboardButton("
‫"زنده‬,

callback_data="market")],

💰

[InlineKeyboardButton("
‫"گنجینه من‬,

callback_data="wallet"),

🏦 ‫بانک‬

InlineKeyboardButton("

‫"مرکزی‬, callback_data="bank"),

🏪

InlineKeyboardButton("
‫"فروشگاه ویژه‬,

callback_data="shop")],

🎁

[InlineKeyboardButton("

‫"صندوق شانس‬,
callback_data="chests"),

🎯

InlineKeyboardButton(f"

‫{مأموریت روزانه‬mission_badge}",
callback_data="missions"),

🏆 ‫لیگ‬

InlineKeyboardButton("
‫"من‬,

callback_data="league")],

🤝

[InlineKeyboardButton("
‫"اتحاد قدرت‬,

callback_data="alliance"),

📊

InlineKeyboardButton("
‫‌ها‬
‫"برترین‬,

callback_data="ranking"),

⭐

InlineKeyboardButton("
‫ عضویت‬VIP",

callback_data="vip")],

👥

[InlineKeyboardButton("
‫‌گیری‬
‫"زیرمجموعه‬,

callback_data="invite"),

🎁

InlineKeyboardButton(f"

‫{جایزه ورود روزانه‬daily_badge}",
callback_data="daily"),

📰 ‫اخبار‬

InlineKeyboardButton("
‫"جهان‬,

callback_data="news")],

🎖

[InlineKeyboardButton("
‫"دستاوردهای من‬,

callback_data="achievements"
),

🔬

InlineKeyboardButton("
‫"آزمایشگاه فناوری‬,

callback_data="research"),

🛡 ‫قدرت‬

InlineKeyboardButton("
‫"دفاعی‬,

callback_data="defense")],

🌌

[InlineKeyboardButton("
‫"اکتشاف سرزمین‬,

callback_data="exploration")
,

🕵 ‫بازار‬

InlineKeyboardButton("
‫"سیاه امروز‬,

callback_data="black_market"
),

📆 ‫فصل‬

InlineKeyboardButton("
‫"بازی‬,

callback_data="season")],

📦 ‫بازار‬

[InlineKeyboardButton("
‫"بازیکنان‬,

callback_data="p2p_market"),

🎟 ‫حدس‬

InlineKeyboardButton("
‫"قیمت‬,

callback_data="prediction")]
,

⚔️

[InlineKeyboardButton("
‫"آوردگاه رقابت‬,

callback_data="competition")
],

🤖

[InlineKeyboardButton("
‫"مشاور هوشمند‬,

callback_data="smart_advisor
"),

🎁 ‫کد‬

InlineKeyboardButton("
‫"هدیه‬,

callback_data="gift_code")],

❓

[InlineKeyboardButton("
‫"راهنمای کامل‬,
callback_data="help"),

InlineKeyboardButton("☎
‫"پشتیبانی‬,

callback_data="support")],
]
if user_id in ADMIN_IDS:
pending_count =
len(list_pending_withdrawals
())
admin_badge = f"

🔴{pending_count}" if

pending_count else ""
buttons.append([InlineKeyboa

👑 ‫پنل مدیریت‬

rdButton(f"

TITAN{admin_badge}",

callback_data="admin_panel")
])
return
InlineKeyboardMarkup(buttons
)

def
back_keyboard(target="back_m
ain"):
return
InlineKeyboardMarkup([[Inlin

🔙 ‫بازگشت به‬

eKeyboardButton("
‫"منو‬,

callback_data=target)]])

#
============================
============================
====
#

‫عضویت اجباری‬

#
============================
============================
====
async def

check_force_join(update:
Update, context:
ContextTypes.DEFAULT_TYPE,
user_id) -> bool:
if not
FORCE_JOIN_CHANNELS:
return True
not_joined = []
for ch in
FORCE_JOIN_CHANNELS:
try:
member = await
context.bot.get_chat_member(
ch["id"], user_id)
if member.status
in ("left", "kicked"):
not_joined.append(ch)
except Exception as
e:
logger.warning(f"Force join

check failed for {ch['id']}:
{e}")
not_joined.append(ch)
if not_joined:
buttons = [
[InlineKeyboardButton(f"
‫{ عضویت در‬ch['title']}",

📢

url=ch["url"])]
for ch in
not_joined
]
buttons.append([InlineKeyboa

✅ ‫ بررسی‬،‫عضو شدم‬

rdButton("
‫"مجدد‬,

callback_data="check_join")]
)
text = "

🔒 ‫برای استفاده‬

‫ از ربات‬LIBER ‫‌های‬
‫ابتدا باید در کانال‬

‫زیر عضو شوی‬:"
if update.message:
await
update.message.reply_text(te
xt,
reply_markup=InlineKeyboardM
arkup(buttons))
elif
update.callback_query:
await
update.callback_query.messag
e.reply_text(text,
reply_markup=InlineKeyboardM
arkup(buttons))
return False
return True

#
============================
============================
====

#

/start

#
============================
============================
====
async def start(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
tg_user =
update.effective_user
user_id = tg_user.id
ref_by = 0
if context.args:
try:
possible_ref =
int(context.args[0])
if possible_ref
!= user_id:
ref_by =
possible_ref

except ValueError:
pass
if is_banned(user_id):
await
update.message.reply_text("

🚫 ‫ برای‬.‫حساب شما مسدود شده است‬
‫اطالعات بیشتر با پشتیبانی تماس‬
‫بگیرید‬.")

return
joined_ok = await
check_force_join(update,
context, user_id)
if not joined_ok:
return
is_new =
create_user_if_not_exists(tg
_user, ref_by)
u = get_user(user_id)

now = datetime.now()
current_time =
now.strftime("%H:%M:%S")
current_date =
now.strftime("%Y-%m-%d")
last_year = now.year - 1
welcome = (

🌌
═══════════════════ 🌌\n"
f"✨ ‫خوش اومدی به دنیای‬
<b>LIBER</b> ✨\n"
"🌌
═══════════════════ 🌌
\n\n"
f"👋 ‫< سالم جناب‬b>
"

{tg_user.first_name}</b> ‫خوش‬
‫\!اومدی به لیبر‬n\n"

🪪 ‫آیدی عددی‬: <code>
{user_id}</code>\n"
f"👤 ‫نام کاربری‬:
f"

@{tg_user.username if

tg_user.username else
'‫\}'ندارد‬n"

📅 ‫تاریخ ورود‬:
{current_date}\n"
f"🕒 ‫ساعت فعلی‬:
{current_time}\n"
f"📆 ‫یک سال قبل‬:
{last_year}\n"
f"🔁 ‫تعداد ورود‬:
{u['login_count']}\n\n"
f"💰 ‫موجودی فعلی‬:\n"
f"🪙 LIBER: <b>
{u['liber']}</b>\n"
f"💵 Coin: <b>
{u['coin']}</b>\n"
f"⚡ Energy: <b>
{u['energy']}</b>\n"
f"💎 Diamond: <b>
{u['diamond']}</b>\n"
f"🏅 Medal: <b>
{u['medal']}</b>\n\n"
"⚠️ ‫ فحاشی و‬،‫ تقلب‬:‫توجه‬
f"

‫اسپم در ربات ممنوع است و باعث اخطار‬
‫‌شود‬
‫یا مسدودی می‬.\n\n"

👇 ‫از دکمه‌های زیر برای‬

"

‫شروع بازی استفاده کن‬:"
)
if is_new:

welcome += "\n\n
‫ چون تازه به‬LIBER ۱۰۰ ،‫پیوستی‬

🎉

LIBER ۵۰۰ ‫ و‬Coin ‫"!هدیه گرفتی‬
await
update.message.reply_text(we
lcome,
parse_mode=ParseMode.HTML,
reply_markup=main_menu_keybo
ard(user_id))

#
============================
============================

====
#

Job ‫ساعتی نوسان بازار‬

#
============================
============================
====
async def
hourly_market_job(context:
ContextTypes.DEFAULT_TYPE):
price =
get_market_price()
change =
random.uniform(*MARKET_FLUCT
UATION_RANGE)
new_price = max(1,
round(price * (1 + change),
2))
set_market_price(new_price)

📈 ‫ "صعودی‬if
new_price >= price else "📉
direction = "

‫"نزولی‬
logger.info(f"Market
price updated: {price} ->
{new_price} ({direction})")
results =
resolve_predictions()
for target_user_id, won,
payout in results:
try:
if won:
text = f"
‫‌ات درست بود‬
‫‌بینی‬
‫!پیش‬

🎉

{round(payout,2)} Coin ‫گرفتی‬."
else:
text = "
‫‌بار درست نبود‬
‫‌ات این‬
‫‌بینی‬
‫پیش‬."

😔

await
context.bot.send_message(tar
get_user_id, text)
except Exception as
e:

logger.warning(f"Could not
notify user
{target_user_id}: {e}")
maybe_reset_season()
await
maybe_resolve_tournament(con
text.bot)
expire_all_subscriptions_job
()

#
============================
============================
====
#

‫‌ها‬
‫هندلر اصلی دکمه‬

#
============================
============================

====
async def
button_handler(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
query =
update.callback_query
user_id =
query.from_user.id
if is_banned(user_id):
await

🚫 ‫حساب شما‬

query.answer("

‫مسدود است‬.", show_alert=True)
return
ok, warns =
anti_spam_check(user_id)
if not ok:
if warns >= 5:
conn = db()

c =
conn.cursor()
c.execute("UPDATE users SET
warn_count=warn_count+1
WHERE user_id=?",
(user_id,))
conn.commit()
conn.close()
await

⚠️ !‫لطفًا کمی آرام‌تر‬

query.answer("

)‫"(ضد اسپم فعال شد‬,
show_alert=True)
return

# ‫تشخیص هوشمند الگوی کلیک‬

)‫‌گونه (فراتر از حد طبیعی یک انسان‬
‫ربات‬
if
check_click_rate_cheat(user_
id):
await
flag_suspicious_activity(use

r_id, context, "‫الگوی کلیک‬
‫اسکریپتی‬/‫)"غیرطبیعی‬
if
is_banned(user_id):
await

🚫 ‫حساب شما به‬

query.answer("

‫دلیل فعالیت مشکوک مسدود شد‬.",
show_alert=True)
return
await

⚠️ ‫فعالیت غیرطبیعی‬

query.answer("

‫‌تر پیش‬
‫ کمی آرام‬.‫تشخیص داده شد‬
‫برو‬.", show_alert=True)
return

await query.answer()
data = query.data
if data == "check_join":
joined_ok = await
check_force_join(update,
context, user_id)

if joined_ok:
await
query.message.edit_text("
‫عضویت شما تایید شد! از منوی زیر‬

✅

‫استفاده کن‬:",

reply_markup=main_menu_keybo
ard(user_id))
return
if data == "back_main":
await
query.message.edit_text("
‫ منوی اصلی‬LIBER:",

🌍

reply_markup=main_menu_keybo
ard(user_id))
return
u = get_user(user_id)
# ---------------- ‫پروفایل‬
---------------if data == "profile":

league =
get_league_name(u["xp"] +
u["level"] * XP_PER_LEVEL)
comp_league =
get_league_tier_name(u["rank
_points"])
username_display =
f"@{u['username']}" if
u["username"] else "‫"ثبت نشده‬
bio_display =
u["bio"] or "‫با( بیوگرافی ثبت نشده‬
/setbio ‫")متن بنویس‬
text = (

👤 <b>‫پروفایل‬

"
‫<شما‬/b>\n"

"━━━━━━━━━━━━━━━\n"

🪪 ‫نام کاربری‬:
{username_display}\n"
f"🆔 ‫آیدی عددی‬:
<code>{user_id}</code>\n"
f"📛 ‫نام‬:
f"

{u['first_name']}\n"

📝 ‫بیو‬:

f"

{bio_display}\n"

"━━━━━━━━━━━━━━━\n"

⭐ ‫سطح‬:
{u['level']} | 💎 XP:
f"

{u['xp']}/{u['level']*XP_PER
_LEVEL}\n"

🏆 ‫لیگ اقتصادی‬:

f"
{league}\n"

f"⚔ ‫لیگ رقابتی‬:
{comp_league}
({u['rank_points']} ‫\)امتیاز‬n"

🏅 ‫مدال‬:
{u['medal']}\n"
f"👑 ‫ اشتراک‬VIP:
f"

{u['vip'] if u['vip'] !=
'none' else '‫\}'ندارد‬n"
"━━━━━━━━━━━━━━━\n"

🪙 ‫موجودی‬

f"

LIBER: {u['liber']}\n"

🌍 ‫کشور‬:

f"

{u['country_name'] or '‫ثبت‬
‫\}'نشده‬n"

👥 ‫زیرمجموعه‌ها‬:
{u['ref_count']} ‫\نفر‬n"
f"⚠️ ‫اخطارها‬:
f"

{u['warn_count']}/{MAX_WARN_
BEFORE_BAN}\n"
"━━━━━━━━━━━━━━━\n"

📅 ‫تاریخ عضویت‬:
{u['joined_at']}\n"
f"🔁 ‫تعداد ورود به‬
f"

‫ربات‬: {u['login_count']}"
)
await

query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)

# ---------------- ‫کیف‬

‫ پول‬----------------

elif data == "wallet":
text = (

💰 <b>‫کیف پول‬
‫<شما‬/b>\n\n"
f"🪙 LIBER:
{u['liber']}\n"
f"💵 Coin:
{u['coin']}\n"
f"⚡ Energy:
{u['energy']}\n"
f"💎 Diamond:
{u['diamond']}\n"
f"🏅 Medal:
"

{u['medal']}"
)
kb =

InlineKeyboardMarkup([

📤

[InlineKeyboardButton("
‫"برداشت‬,

callback_data="withdraw"),

📥

InlineKeyboardButton("
‫"واریز‬,

callback_data="deposit")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
# ---------------- ‫ بازار‬--------------elif data == "market":
price =
get_market_price()
text = (

💹 <b>‫بازار‬

"

LIBER</b>\n\n"

📈 ‫قیمت لحظه‌ای هر‬

f"

LIBER: <b>{price}
Coin</b>\n"

f"⏱ ‫ ساعت‬۱ ‫قیمت هر‬

‫‌کند‬
‫‌صورت خودکار نوسان می‬
‫به‬.\n"

💼 ‫موجودی شما‬:

f"

{u['liber']} LIBER |
{u['coin']} Coin"
)
kb =

InlineKeyboardMarkup([

🟢

[InlineKeyboardButton("
‫"خرید‬,

callback_data="market_buy"),

🔴

InlineKeyboardButton("
‫"فروش‬,

callback_data="market_sell")
],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data in
("market_buy",
"market_sell"):
action = "buy" if
data == "market_buy" else
"sell"
amounts = [10, 50,
100, 500]
buttons = [
[InlineKeyboardButton(f"
{amt} LIBER",
callback_data=f"

{action}_{amt}") for amt in
amounts[:2]],
[InlineKeyboardButton(f"
{amt} LIBER",
callback_data=f"
{action}_{amt}") for amt in
amounts[2:]],

🔙

[InlineKeyboardButton("
‫"بازگشت‬,

callback_data="market")],
]
label = "‫ "خرید‬if
action == "buy" else "‫"فروش‬
await

💱

query.message.edit_text(f"
‫{ مقدار‬label} ‫را انتخاب کن‬:",

reply_markup=InlineKeyboardM
arkup(buttons))
elif

data.startswith("buy_") or
data.startswith("sell_"):
action, amt_str =
data.split("_")
amount =
float(amt_str)
price =
get_market_price()
cost = amount *
price
if action == "buy":
fee = cost *
BUY_FEE_PERCENT / 100
total_cost =
cost + fee
if u["coin"] <
total_cost:
await
query.message.edit_text("
‫ موجودی‬Coin ‫کافی نیست‬.",

❌

reply_markup=back_keyboard()

)
return
add_currency(user_id,
"coin", -total_cost)
add_currency(user_id,
"liber", amount)
add_currency(user_id,
"trade_count", 1)
unlocked =
check_achievements(user_id)

✅ ‫خرید‬

text = f"

‫\!موفق‬n{amount} LIBER ‫خریدی به‬
‫{ قیمت‬round(cost,2)} Coin (+
‫{ کارمزد‬round(fee,2)})"

if unlocked:
text +=

🎖 ‫دستاورد جدید‬: " + ",

"\n\n

".join(unlocked)

await

query.message.edit_text(text
,
reply_markup=back_keyboard()
)
else:
if u["liber"] <
amount:
await
query.message.edit_text("
‫ موجودی‬LIBER ‫کافی نیست‬.",

❌

reply_markup=back_keyboard()
)
return
fee = cost *
SELL_FEE_PERCENT / 100
net = cost - fee
add_currency(user_id,
"liber", -amount)
add_currency(user_id,
"coin", net)

add_currency(user_id,
"trade_count", 1)
unlocked =
check_achievements(user_id)

✅ ‫فروش‬

text = f"

‫\!موفق‬n{amount} LIBER ‫فروختی و‬
{round(net,2)} Coin ‫گرفتی‬
(‫{ کارمزد‬round(fee,2)})"

if unlocked:
text +=

🎖 ‫دستاورد جدید‬: " + ",

"\n\n

".join(unlocked)

await
query.message.edit_text(text
,
reply_markup=back_keyboard()
)
# ---------------- ‫ بانک‬--------------elif data == "bank":

text = (

🏦 <b>‫بانک‬
LIBER</b>\n\n"
f"💰 ‫سپرده فعلی‬:
{u['bank_deposit']} Coin\n"
f"📈 ‫سود روزانه‬
"

‫سپرده‬:

{BANK_INTEREST_PERCENT}%\n"

💳 ‫وام فعلی‬:
{u['loan_amount']} Coin\n"
f"📊 ‫کارمزد وام‬:
f"

{LOAN_INTEREST_PERCENT}%"
)
kb =
InlineKeyboardMarkup([

➕

[InlineKeyboardButton("
‫‌گذاری‬
‫"سپرده‬,

callback_data="bank_deposit"
),

➖

InlineKeyboardButton("

‫"برداشت سپرده‬,
callback_data="bank_withdraw
")],

💳

[InlineKeyboardButton("
‫"درخواست وام‬,

callback_data="bank_loan"),

✅

InlineKeyboardButton("
‫"پرداخت وام‬,

callback_data="bank_payloan"
)],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)

elif data ==
"bank_deposit":
amount = min(500,
u["coin"])
if amount <= 0:
await
query.message.edit_text("
‫ موجودی‬Coin ‫کافی نیست‬.",

❌

reply_markup=back_keyboard("
bank"))
return
add_currency(user_id,
"coin", -amount)
add_currency(user_id,
"bank_deposit", amount)
unlocked =
check_achievements(user_id)

✅ {amount}

text = f"

Coin ‫به سپرده بانکی اضافه شد‬."
if unlocked:

text += "\n\n
‫دستاورد جدید‬: " + ",

🎖

".join(unlocked)
await
query.message.edit_text(text
,
reply_markup=back_keyboard("
bank"))
elif data ==
"bank_withdraw":
u2 =
get_user(user_id)
amount =
u2["bank_deposit"]
if amount <= 0:
await
query.message.edit_text("

❌

‫‌ای برای برداشت وجود ندارد‬
‫سپرده‬.",

reply_markup=back_keyboard("
bank"))
return

interest = amount *
BANK_INTEREST_PERCENT / 100
total = amount +
interest
set_field(user_id,
"bank_deposit", 0)
add_currency(user_id,
"coin", total)
await
query.message.edit_text(

✅ ‫کل سپرده‬

f"

‫برداشت شد‬: {round(total,2)}
Coin (‫شامل‬

{round(interest,2)} ‫")سود‬,
reply_markup=back_keyboard("
bank"),
)
elif data ==
"bank_loan":

max_loan =
u["level"] * 100 *
MAX_LOAN_MULTIPLIER
if u["loan_amount"]
> 0:
await
query.message.edit_text("
‫ابتدا وام فعلی را پرداخت کن‬.",

❌

reply_markup=back_keyboard("
bank"))
return
loan = max_loan
add_currency(user_id,
"coin", loan)
set_field(user_id,
"loan_amount", loan * (1 +
LOAN_INTEREST_PERCENT /
100))
await
query.message.edit_text(

✅ ‫{ وام‬loan}

f"

Coin ‫ مبلغ بازپرداخت با‬.‫دریافت شد‬
‫کارمزد‬: {round(loan*

(1+LOAN_INTEREST_PERCENT/100
),2)} Coin",
reply_markup=back_keyboard("
bank"),
)
elif data ==
"bank_payloan":
u2 =
get_user(user_id)
if u2["loan_amount"]
<= 0:
await
query.message.edit_text("
‫شما وامی ندارید‬.",

✅

reply_markup=back_keyboard("
bank"))
return
if u2["coin"] <

u2["loan_amount"]:
await
query.message.edit_text("

❌

‫ موجودی‬Coin ‫برای پرداخت کامل وام‬
‫کافی نیست‬.",

reply_markup=back_keyboard("
bank"))
return
add_currency(user_id,
"coin", -u2["loan_amount"])
set_field(user_id,
"loan_amount", 0)
await
query.message.edit_text("
‫وام با موفقیت پرداخت شد‬.",

✅

reply_markup=back_keyboard("
bank"))
# ---------------- ‫ کشور‬--------------elif data == "country":

if not
u["country_name"]:
text = "

🌍 ‫هنوز‬

‫ جمعیت‬،‫‌ای! با ثبت کشور‬
‫کشوری نساخته‬
‫‌گیری‬
‫و بودجه اولیه می‬."
kb =
InlineKeyboardMarkup([

🏛

[InlineKeyboardButton("
‫"ساخت کشور‬,

callback_data="country_creat
e")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, reply_markup=kb)
else:
text = (

🌍 <b>‫کشور‬
{u['country_name']}</b>\n\n"
f"👥 ‫جمعیت‬:
{u['country_pop']}\n"
f"💰 ‫بودجه‬:
f"

{u['country_budget']}
Coin\n"

📈 ‫هر بار‬

"

‫ بر اساس جمعیت‬،‫‌آوری مالیات» بزنی‬
‫«جمع‬
‫‌گیری‬
‫درآمد می‬."

)
kb =
InlineKeyboardMarkup([

💰

[InlineKeyboardButton("
‫‌آوری مالیات‬
‫"جمع‬,

callback_data="country_tax")
],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],

])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"country_create":
set_field(user_id,
"country_name", f"‫کشور‬
{u['first_name']}")
set_field(user_id,
"country_pop", 100)
set_field(user_id,
"country_budget", 200)
unlocked =
check_achievements(user_id)
text = "

🎉 ‫کشورت ساخته‬

۲۰۰ ‫ جمعیت و‬۱۰۰ !‫ شد‬Coin ‫بودجه‬
‫اولیه گرفتی‬."

if unlocked:
text += "\n\n

🎖

‫دستاورد جدید‬: " + ",
".join(unlocked)
await
query.message.edit_text(text
,
reply_markup=back_keyboard()
)
elif data ==
"country_tax":
u2 =
get_user(user_id)
tax_income =
round(u2["country_pop"] *
0.5, 2)
add_currency(user_id,
"country_budget",
tax_income)
add_currency(user_id,
"coin", tax_income)

new_level =
add_xp(user_id, 5)
await
query.message.edit_text(

💰 ‫مالیات جمع‌آوری‬
‫شد‬: {tax_income} Coin\n⭐ 5
f"

XP ‫سطح فعلی( گرفتی‬:
{new_level})",

reply_markup=back_keyboard()
,
)
# ---------------- ‫‌ها‬
‫صندوق‬
---------------elif data == "chests":
buttons = []
row = []
for i, key in
enumerate(CHEST_TABLE.keys()
):

row.append(InlineKeyboardBut

🎁 {key}",

ton(f"

callback_data=f"chest_{key}"
))
if len(row) ==
3:
buttons.append(row)
row = []
if row:
buttons.append(row)
buttons.append([InlineKeyboa

🔙 ‫"بازگشت به منو‬,

rdButton("

callback_data="back_main")])
await
query.message.edit_text("
‫یک صندوق را برای باز کردن انتخاب‬

🎁

‫کن‬:",

reply_markup=InlineKeyboardM
arkup(buttons))

elif
data.startswith("chest_"):
key =
data.split("_", 1)[1]
chest =
CHEST_TABLE.get(key)
if not chest:
await
query.message.edit_text("
‫صندوق نامعتبر‬.",

❌

reply_markup=back_keyboard("
chests"))
return
for currency, cost
in chest["cost"].items():
if u[currency] <
cost:
await

❌

query.message.edit_text(f"

{currency} ‫کافی برای باز کردن این‬
‫صندوق نداری‬.",

reply_markup=back_keyboard("
chests"))
return
for currency, cost
in chest["cost"].items():
add_currency(user_id,
currency, -cost)
reward_lines = []
for field, low, high
in chest["rewards"]:
amount =
random.randint(low, high)
if field ==
"xp":
add_xp(user_id, amount)
else:
add_currency(user_id, field,
amount)

reward_lines.append(f"+
{amount} {field}")

add_currency(user_id,
"chest_count", 1)
unlocked =
check_achievements(user_id)

🎉 ‫صندوق‬

text = f"

{key} ‫\!باز شد‬n\n" +

"\n".join(reward_lines)
if unlocked:
text += "\n\n
‫دستاورد جدید‬: " + ",

🎖

".join(unlocked)
await
query.message.edit_text(text
,
reply_markup=back_keyboard("
chests"))

# ---------------‫‌ها‬
‫ مأموریت‬---------------elif data == "missions":
today =
datetime.now().strftime("%Y%m-%d")
done_today =
u["last_daily_mission"] ==
today
text = (

🎯 <b>‫مأموریت‬
‫<روزانه‬/b>\n\n"
"📋 ‫ با ربات‬:‫وظیفه‬
"

‫تعامل داشته باش (باز کردن این منو‬
)‫\کافیست‬n"

🎁 ‫جایزه‬:

f"

{DAILY_MISSION_XP} XP +
{DAILY_MISSION_LIBER}
LIBER\n\n"
+ ("

✅ ‫امروز قبًال‬

‫دریافت کردی‬." if done_today

🟢 ‫)"!آماده دریافت جایزه‬

else "

)
kb_buttons = []
if not done_today:
kb_buttons.append([InlineKey

✅ ‫"دریافت جایزه‬,

boardButton("

callback_data="mission_claim
")])
kb_buttons.append([InlineKey

🔙 ‫"بازگشت به منو‬,

boardButton("

callback_data="back_main")])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=InlineKeyboardM
arkup(kb_buttons))
elif data ==
"mission_claim":
today =
datetime.now().strftime("%Y-

%m-%d")
if
u["last_daily_mission"] ==
today:
await
query.message.edit_text("
‫امروز قبًال دریافت کردی‬.",

✅

reply_markup=back_keyboard("
missions"))
return
set_field(user_id,
"last_daily_mission", today)
add_currency(user_id,
"liber",
DAILY_MISSION_LIBER)
new_level =
add_xp(user_id,
DAILY_MISSION_XP)
await
query.message.edit_text(

🎉 ‫جایزه مأموریت‬

f"

‫روزانه گرفتی‬: {DAILY_MISSION_XP}
XP + {DAILY_MISSION_LIBER}
LIBER\n(‫سطح فعلی‬:
{new_level})",

reply_markup=back_keyboard("
missions"),
)
# ---------------- ‫ لیگ‬--------------elif data == "league":
total_xp = u["xp"] +
u["level"] * XP_PER_LEVEL
league =
get_league_name(total_xp)
text = (

🏆 <b>‫لیگ‬
‫<شما‬/b>\n\n"
f"🎖 ‫لیگ فعلی‬:
{league}\n"
f"💎 ‫ مجموع‬XP:
"

{total_xp}\n\n"

📈 ‫ با کسب‬XP ‫بیشتر‬

"

‫ مالیات) به لیگ باالتر‬،‫ بازار‬،‫(مأموریت‬
‫‌روی‬
‫می‬."

)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)
# ---------------- ‫‌بندی‬
‫رتبه‬
---------------elif data == "ranking":
conn = db()
c = conn.cursor()
c.execute("SELECT
first_name, liber FROM users
ORDER BY liber DESC LIMIT
10")
top = c.fetchall()
conn.close()

lines = [f"{i+1}.
{row['first_name']} —
{row['liber']} LIBER" for i,
row in enumerate(top)]
text = "
LIBER</b>\n\n" +

📊 <b>‫برترین‌های‬

"\n".join(lines) if lines
else "‫‌ای موجود نیست‬
‫هنوز داده‬."
await

query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)
# ---------------- VIP --------------elif data == "vip":
check_and_expire_subscriptio
n(user_id)
u =
get_user(user_id)

expiry_line = ""
if u["vip"] !=
"none" and
u["vip_expires_at"]:
expiry_line =

⏳ ‫اشتراک فعلی تو‬

f"\n\n

({u['vip']}) ‫تا‬

{u['vip_expires_at']} ‫معتبر‬
‫است‬."

text = (

⭐ <b>‫سطوح‬

"
VIP</b>\n\n"

+ "\n".join(
f"{tier}:
{info['cost_diamond']}
Diamond — ‫ درآمد و‬XP
x{info['income_bonus']}"
for tier,
info in VIP_TIERS.items()
)
+ expiry_line
+ "\n\n

🌟 ‫همچنین‬

‫‌تونی با تلگرام استارز اشتراک ویژه با‬
‫می‬
‫مزایای بیشتر بخری‬:"
)
buttons =
[[InlineKeyboardButton(f"‫خرید‬
{tier}",
callback_data=f"vip_{tier}")
] for tier in VIP_TIERS]
buttons.append([InlineKeyboa

⭐ ‫خرید اشتراک با‬

rdButton("
‫"استارز‬,

callback_data="star_vip_menu
")])
buttons.append([InlineKeyboa

🔙 ‫"بازگشت به منو‬,

rdButton("

callback_data="back_main")])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=InlineKeyboardM

arkup(buttons))
elif
data.startswith("vip_") and
not
data.startswith("vip_star"):
tier =
data.split("_", 1)[1]
info =
VIP_TIERS.get(tier)
if not info:
await
query.message.edit_text("
‫ سطح‬VIP ‫نامعتبر‬.",

❌

reply_markup=back_keyboard("
vip"))
return
if u["diamond"] <
info["cost_diamond"]:
await
query.message.edit_text("
Diamond ‫کافی نداری‬.",

❌

reply_markup=back_keyboard("
vip"))
return
add_currency(user_id,
"diamond", info["cost_diamond"])
set_field(user_id,
"vip", tier)
unlocked =
check_achievements(user_id)

🎉 ‫تبریک! اکنون‬

text = f"
VIP {tier} ‫هستی‬."

if unlocked:
text += "\n\n

‫دستاورد جدید‬: " + ",

🎖

".join(unlocked)
await
query.message.edit_text(text
,
reply_markup=back_keyboard("
vip"))

# ---------------- ‫اشتراک‬

‫ویژه با تلگرام استارز‬
-----

⭐ -----------

elif data ==
"star_vip_menu":
text = "

🌟 <b>‫اشتراک‌های‬

‫ ویژه‬LIBER (‫)پرداخت با تلگرام استارز‬
</b>\n\n‫یک اشتراک را انتخاب کن تا‬
‫‌هایش را ببینی‬
‫مزایا و قیمت‬:"
buttons = [

[InlineKeyboardButton(info["
title"],
callback_data=f"star_tier_{k
ey}")]
for key, info in
STAR_SUBSCRIPTIONS.items()
]
buttons.append([InlineKeyboa

🔙 ‫"بازگشت‬,

rdButton("

callback_data="vip")])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=InlineKeyboardM
arkup(buttons))
elif
data.startswith("star_tier_"
):
tier_key =
data.split("_", 2)[2]
plan =
STAR_SUBSCRIPTIONS.get(tier_
key)
if not plan:
await
query.message.edit_text("
‫اشتراک نامعتبر‬.",

❌

reply_markup=back_keyboard("
star_vip_menu"))
return

text = (
f"
{plan['title']}\n\n"

🎁 ‫مزایا‬:

f"

{plan['benefits']}\n\n"
"‫مدت اشتراک را انتخاب‬

‫کن‬:"
)

buttons = [
[InlineKeyboardButton(f"
{days} ‫— روز‬

⭐ {stars} ‫"استارز‬,

callback_data=f"star_buy_{ti
er_key}_{days}")]
for days, stars
in plan["durations"].items()
]
buttons.append([InlineKeyboa

🔙 ‫"بازگشت‬,

rdButton("

callback_data="star_vip_menu
")])

await
query.message.edit_text(text
,
reply_markup=InlineKeyboardM
arkup(buttons))
elif
data.startswith("star_buy_")
:
_, _, tier_key,
days_str = data.split("_",
3)
days = int(days_str)
plan =
STAR_SUBSCRIPTIONS.get(tier_
key)
if not plan or days
not in plan["durations"]:
await
query.message.edit_text("
‫گزینه نامعتبر‬.",

❌

reply_markup=back_keyboard("

star_vip_menu"))
return
stars_price =
plan["durations"][days]
await
context.bot.send_invoice(
chat_id=user_id,
title=f"
{plan['title']} — {days}
‫"روزه‬,
description=f"‫مزایا‬:
{plan['benefits']}",
payload=f"vip:
{tier_key}:{days}",
currency="XTR",
prices=
[LabeledPrice(f"
{plan['title']} ({days}
‫")روز‬, stars_price)],
provider_token="",

)
await

⭐ ‫فاکتور پرداخت با‬

query.answer("

‫استارز برایت ارسال شد‬.",
show_alert=True)
elif data ==
"star_liber_menu":
text = "

🌟 <b>‫خرید‬

LIBER ‫<با تلگرام استارز‬/b>\n\n‫‌ها‬
‫قیمت‬
‫ یک بسته انتخاب‬.‫منصفانه و ثابت هستند‬
‫کن‬:"

buttons = [
[InlineKeyboardButton(f"
{pack['title']} —
{pack['liber']} LIBER —
{pack['stars']}",

⭐

callback_data=f"star_liber_b
uy_{key}")]
for key, pack in
STAR_LIBER_PACKS.items()

]
buttons.append([InlineKeyboa

🔙 ‫"بازگشت‬,

rdButton("

callback_data="shop")])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=InlineKeyboardM
arkup(buttons))
elif
data.startswith("star_liber_
buy_"):
pack_key =
data.split("star_liber_buy_"
, 1)[1]
pack =
STAR_LIBER_PACKS.get(pack_ke
y)
if not pack:
await

query.message.edit_text("
‫بسته نامعتبر‬.",

❌

reply_markup=back_keyboard("
star_liber_menu"))
return
await
context.bot.send_invoice(
chat_id=user_id,
title=pack["title"],
description=f"
{pack['liber']} LIBER ‫مستقیم به‬
‫‌شود‬
‫کیف پول شما اضافه می‬.",

payload=f"liber:

{pack_key}",
currency="XTR",
prices=
[LabeledPrice(pack["title"],
pack["stars"])],
provider_token="",
)

await

⭐ ‫فاکتور پرداخت با‬

query.answer("

‫استارز برایت ارسال شد‬.",
show_alert=True)

# ---------------- ‫ اتحاد‬--------------elif data == "alliance":
if u["alliance_id"]:
conn = db()
c =
conn.cursor()
c.execute("SELECT * FROM
alliances WHERE
alliance_id=?",
(u["alliance_id"],))
alliance =
c.fetchone()
conn.close()
text = (

🤝 <b>‫اتحاد‬

f"

{alliance['name']}</b>\n\n"

💰 ‫خزانه‬:

f"

{alliance['treasury']}
Coin\n"

👑 ‫رهبر‬:

f"

{alliance['leader_id']}"
)
kb =
InlineKeyboardMarkup([

💰 ‫کمک‬

[InlineKeyboardButton("
‫"به خزانه‬,

callback_data="alliance_dona
te")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,

reply_markup=kb)
else:
text = "
‫عضو هیچ اتحادی نیستی‬."

🤝 ‫هنوز‬

kb =
InlineKeyboardMarkup([

🏛

[InlineKeyboardButton("
‫"ساخت اتحاد جدید‬,

callback_data="alliance_crea
te")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, reply_markup=kb)
elif data ==
"alliance_create":

conn = db()
c = conn.cursor()
c.execute(
"INSERT INTO
alliances (name, leader_id,
treasury) VALUES (?, ?, 0)",
(f"‫اتحاد‬
{u['first_name']}",
user_id),
)
alliance_id =
c.lastrowid
conn.commit()
conn.close()
set_field(user_id,
"alliance_id", alliance_id)
unlocked =
check_achievements(user_id)
text = "

🎉 ‫اتحاد جدید‬

‫"!ساخته شد و رهبر آن شدی‬
if unlocked:

text += "\n\n

🎖

‫دستاورد جدید‬: " + ",
".join(unlocked)
await
query.message.edit_text(text
,
reply_markup=back_keyboard("
alliance"))
elif data ==
"alliance_donate":
amount = min(100,
u["coin"])
if amount <= 0:
await
query.message.edit_text("
Coin ‫کافی نداری‬.",

❌

reply_markup=back_keyboard("
alliance"))
return
add_currency(user_id,
"coin", -amount)

conn = db()
c = conn.cursor()
c.execute("UPDATE
alliances SET treasury =
treasury + ? WHERE
alliance_id=?", (amount,
u["alliance_id"]))
conn.commit()
conn.close()
await

✅

query.message.edit_text(f"

{amount} Coin ‫به خزانه اتحاد اضافه‬
‫شد‬.",

reply_markup=back_keyboard("
alliance"))
# ---------------- ‫ دعوت‬--------------elif data == "invite":
bot_username =
context.bot.username
link =

f"https://t.me/{bot_username
}?start={user_id}"
text = (

👥 <b>‫دعوت‬
‫<دوستان‬/b>\n\n"
f"🔗 ‫لینک اختصاصی‬
‫شما‬:\n{link}\n\n"
f"👥 ‫تعداد زیرمجموعه‬:
{u['ref_count']} ‫\نفر‬n"
"🎁 :‫هر دعوت جدید‬
"

50 LIBER + 200 Coin"
)
await

query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)
# ---------------- ‫جایزه‬

‫ روزانه‬----------------

elif data == "daily":
today =

datetime.now().strftime("%Y%m-%d")
if
u["last_daily_reward"] ==
today:
await
query.message.edit_text("
‫جایزه امروزت را قبًال گرفتی‬.",

✅

reply_markup=back_keyboard()
)
return
reward_liber =
random.randint(3, 15)
set_field(user_id,
"last_daily_reward", today)
add_currency(user_id,
"liber", reward_liber)
await
query.message.edit_text(

🎁 ‫جایزه روزانه‬

f"

‫دریافت شد‬: <b>{reward_liber}

LIBER</b>",
parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
,
)
# ---------------- ‫فروشگاه‬
---------------elif data == "shop":
buttons = []
row = []
for key, item in
SHOP_ITEMS.items():
row.append(InlineKeyboardBut
ton(item["title"],
callback_data=f"shop_{key}")
)
if len(row) ==
2:

buttons.append(row)
row = []
if row:
buttons.append(row)
buttons.append([InlineKeyboa

🌟 ‫ خرید‬LIBER ‫با‬

rdButton("
‫"استارز‬,

callback_data="star_liber_me
nu")])
buttons.append([InlineKeyboa

🔙 ‫"بازگشت به منو‬,

rdButton("

callback_data="back_main")])
await
query.message.edit_text("
‫ فروشگاه‬LIBER:",

🏪

reply_markup=InlineKeyboardM
arkup(buttons))

elif
data.startswith("shop_"):
key =
data.split("_", 1)[1]
item =
SHOP_ITEMS.get(key)
if not item:
await
query.message.edit_text("
‫آیتم نامعتبر‬.",

❌

reply_markup=back_keyboard("
shop"))
return
for currency, cost
in item["cost"].items():
if u[currency] <
cost:
await

❌

query.message.edit_text(f"
{currency} ‫کافی نداری‬.",

reply_markup=back_keyboard("
shop"))

return
for currency, cost
in item["cost"].items():
add_currency(user_id,
currency, -cost)
field, amount =
item["give"]
if field == "frame":
set_field(user_id, "frame",
amount)
await

✅

query.message.edit_text(f"

‫خرید موفق‬: {item['title']}",

reply_markup=back_keyboard("
shop"))
else:
add_currency(user_id, field,
amount)
await

✅

query.message.edit_text(f"

‫خرید موفق‬: {item['title']}",

reply_markup=back_keyboard("
shop"))
# ---------------‫ دستاوردها‬---------------elif data ==
"achievements":
unlocked =
check_achievements(user_id)
unlocked_keys =
get_achievements(user_id)
lines = []
for key, ach in
ACHIEVEMENTS.items():
mark = "

✅" if

key in unlocked_keys else

🔒"

"

lines.append(f"

{mark} {ach['title']} —
{ach['desc']}")

text = "

🎖

<b>‫<دستاوردهای شما‬/b>\n\n" +
"\n".join(lines)
if unlocked:
text += "\n\n
‫دستاورد جدید باز شد‬: " + ",

🎉

".join(unlocked)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)
# ---------------- ‫تحقیقات‬
---------------elif data == "research":
info =
get_research_info(user_id)
if info:
text = (

🔬

"

<b>‫<تحقیقات‬/b>\n\n"

f"‫سطح فعلی‬:
{u['research_level']}\n"
f"‫تحقیق بعدی‬:

{info['name']}\n"

f"‫هزینه‬:
{info['cost_coin']} Coin\n"
f"‫اثر‬:
{info['effect']}"
)
kb =
InlineKeyboardMarkup([

🔬

[InlineKeyboardButton("
‫"ارتقا‬,

callback_data="research_upgr
ade")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
else:

🔬 ‫تمام‬
‫‌ای‬
‫"🎉 !سطوح تحقیقاتی را کامل کرده‬
text = "
kb =

back_keyboard()
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"research_upgrade":
success, msg =
upgrade_research(user_id)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
research"))
# ---------------- ‫ دفاع‬--------------elif data == "defense":
cost =

get_defense_upgrade_cost(u["
defense_level"])
text = (

🛡 <b>‫دفاع‬

"
‫<کشور‬/b>\n\n"

f"‫سطح فعلی دفاع‬:

{u['defense_level']}\n"
f"‫هزینه ارتقای بعدی‬:

{cost} Coin"
)
kb =

InlineKeyboardMarkup([

🛡

[InlineKeyboardButton("
‫"ارتقای دفاع‬,

callback_data="defense_upgra
de")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])

await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"defense_upgrade":
success, msg =
upgrade_defense(user_id)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
defense"))
# ---------------- ‫اکتشاف‬
---------------elif data ==
"exploration":
text = (

🌌

"

<b>‫<اکتشاف‬/b>\n\n"
f"‫حداقل سطح الزم‬:

{EXPLORATION_MIN_LEVEL}\n"
f"‫هزینه انرژی‬:
{EXPLORATION_ENERGY_COST}\n"
f"‫سطح فعلی شما‬:

{u['level']} | ‫انرژی‬:
{u['energy']}"
)
kb =

InlineKeyboardMarkup([

🌌

[InlineKeyboardButton("
‫"شروع اکتشاف‬,

callback_data="exploration_g
o")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,

reply_markup=kb)
elif data ==
"exploration_go":
success, msg =
do_exploration(user_id)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
exploration"))
# ---------------- ‫بازار‬

‫ سیاه‬---------------elif data ==

"black_market":
item =
get_black_market_today()
cost_text = ",
".join(f"{c} {k}" for k, c
in item["cost"].items())
text = (

🕵 <b>‫بازار سیاه‬

"

‫<امروز‬/b>\n\n"
f"
{item['title']}\n"

💰 ‫قیمت‬:
{cost_text}\n"
"⏳ ‫این پیشنهاد فردا‬
f"

‫‌کند‬
‫تغییر می‬."
)

kb =
InlineKeyboardMarkup([

🛒

[InlineKeyboardButton("
‫"خرید‬,

callback_data="black_market_
buy")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text

, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"black_market_buy":
success, msg =
buy_black_market_item(user_i
d)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
black_market"))
# ---------------- ‫ فصل‬--------------elif data == "season":
maybe_reset_season()
number, days_left =
get_season_info()
text = (

📆 <b>‫فصل‬

"
‫<بازی‬/b>\n\n"

f"‫فصل فعلی‬:
{number}\n"
f"‫‌مانده‬
‫روزهای باقی‬:

{days_left}\n"

🏆 ،‫در پایان هر فصل‬

"

‫جوایز و مدال به برترین بازیکنان تعلق‬
‫‌گیرد‬
‫می‬."

)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard()
)
# ---------------- ‫بازار‬

‫( بازیکنان‬P2P) ---------------elif data ==
"p2p_market":
trades =
list_open_trades()
lines = [
f"#

{t['trade_id']} —
{t['item_amount']}
{t['item_field']} ‫به‬

{t['price_coin']} Coin"
for t in trades
] or ["‫فعًال هیچ پیشنهادی‬

‫موجود نیست‬."]

text = "

📦 <b>‫بازار‬

‫<مستقیم بازیکنان‬/b>\n\n" +
"\n".join(lines)
kb =

InlineKeyboardMarkup([

➕ ‫ثبت‬

[InlineKeyboardButton("
‫ پیشنهاد فروش‬LIBER",

callback_data="p2p_sell_offe
r")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])

await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"p2p_sell_offer":
# :‫‌فرض نمونه‬
‫پیشنهاد پیش‬

۲۰ ‫ فروش‬LIBER ‫به قیمت بازار فعلی‬
۲۰ ‫ضربدر‬

amount = 20
price =
round(get_market_price() *
amount * 1.05, 2)
success, msg =
create_trade_offer(user_id,
"liber", amount, price)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
p2p_market"))

elif
data.startswith("p2p_buy_"):
trade_id =
int(data.split("_")[-1])
success, msg =
accept_trade_offer(user_id,
trade_id)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("
p2p_market"))
# ---------------- ‫بازار‬

‫‌بینی قیمت‬
‫ پیش‬---------------elif data ==
"prediction":
price =
get_market_price()
text = (

🎟 <b>‫بازار پیش‌بینی‬
‫ قیمت‬LIBER</b>\n\n"
f"📈 ‫قیمت فعلی‬:
"

{price} Coin\n"

💰 ‫مبلغ شرط‬:

f"

{PREDICTION_BET_AMOUNT}
Coin\n"

🏆 :‫در صورت برد‬

f"
‫ضریب‬

{PREDICTION_WIN_MULTIPLIER}x
\n\n"
"‫‌کنی قیمت‬
‫‌بینی می‬
‫پیش‬

‫"تا ساعت بعد باال برود یا پایین بیاید؟‬
)
kb =
InlineKeyboardMarkup([

📈

[InlineKeyboardButton("
‫"صعودی‬,

callback_data="predict_up"),

📉

InlineKeyboardButton("
‫"نزولی‬,

callback_data="predict_down"
)],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data in
("predict_up",
"predict_down"):
direction = "up" if
data == "predict_up" else
"down"
success, msg =
place_prediction(user_id,
direction)
await
query.message.edit_text(msg,
reply_markup=back_keyboard("

prediction"))
# ---------------- ‫رقابت‬

‫ آنالین‬---------------elif data ==
"competition":

comp_league =
get_league_tier_name(u["rank
_points"])
days_left =
get_tournament_info()
text = (
"⚔ <b>‫رقابت آنالین‬

LIBER</b>\n\n"

f"⚔ ‫لیگ رقابتی فعلی‬:
{comp_league}\n"

📊 ‫امتیاز رنک‬:
{u['rank_points']}\n"
f"🎮 ‫‌ها‬
‫بازی‬:
{u['matches_played']} | 🏆
‫برد‬: {u['matches_won']}\n"
f"🏆 ‫تا پایان تورنمت‬
f"

‫فصلی‬: {days_left} ‫\روز‬n"

🥇 ۵( ‫جوایز تورنمت‬

f"
)‫نفر برتر‬: "

f"‫اول‬

{TOURNAMENT_REWARDS[1]}
LIBER، ‫دوم‬

{TOURNAMENT_REWARDS[2]}، ‫سوم‬
{TOURNAMENT_REWARDS[3]}، "
f"‫چهارم‬
{TOURNAMENT_MEDAL_REWARDS[4]
} ‫ پنجم‬،‫مدال‬
{TOURNAMENT_MEDAL_REWARDS[5]
} ‫\مدال‬n\n"
‫کن‬:"

"‫یک ورزش را انتخاب‬

)
kb =
InlineKeyboardMarkup([

⚽

[InlineKeyboardButton("
‫"فوتبال‬,

callback_data="sport_footbal

l"),

🏀

InlineKeyboardButton("
‫"بسکتبال‬,

callback_data="sport_basketb
all")],

🏅

[InlineKeyboardButton("
‫‌بندی رقابتی‬
‫"رتبه‬,

callback_data="competition_l
eaderboard"),

🏟

InlineKeyboardButton("
‫"مسابقات اخیر‬,

callback_data="competition_r
ecent")],

❓

[InlineKeyboardButton("
‫"راهنمای رقابت‬,

callback_data="competition_h
elp")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"competition_leaderboard":
rows =
get_competition_leaderboard(
)
if not rows:
text = "

🏅

<b>‫‌بندی رقابتی‬
‫<رتبه‬/b>\n\n‫هنوز کسی‬
‫"!امتیاز رنک نگرفته — اولین نفر باش‬
else:

lines = [
f"{i+1}.
{r['first_name']} —

{r['rank_points']} ‫امتیاز‬
({get_league_tier_name(r['ra
nk_points'])}) | "
f"
{r['matches_won']}/{r['match
es_played']} ‫"برد‬
for i, r in
enumerate(rows)
]
text = "

🏅

<b>‫‌بندی رقابتی برتر‬
‫<رتبه‬/b>\n\n" +
"\n".join(lines)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard("
competition"))
elif data ==
"competition_recent":
rows =
get_recent_matches()

if not rows:
text = "

🏟

<b>‫<مسابقات اخیر‬/b>\n\n‫هنوز هیچ‬
‫‌ای برگزار نشده‬
‫مسابقه‬."
else:
lines = []
for r in rows:
opp_name =
r["opponent_name"] if
r["opponent_id"] != 0 else

🤖 ‫"هوش مصنوعی‬

"

lines.append(
f"⚔
{SPORTS[r['sport']]
['title']} —
{r['player_name']}
{r['player_score']} {r['opponent_score']}
{opp_name}"
)
text = "

🏟

‫‪</b>\n\n" +‬مسابقات اخیر>‪<b‬‬
‫)‪"\n".join(lines‬‬
‫‪await‬‬
‫‪query.message.edit_text(text‬‬
‫‪, parse_mode=ParseMode.HTML,‬‬
‫"(‪reply_markup=back_keyboard‬‬
‫))"‪competition‬‬
‫== ‪elif data‬‬
‫‪"competition_help":‬‬
‫( = ‪text‬‬

‫راهنمای رقابت>‪❓ <b‬‬
‫"‪</b>\n\n‬آنالین‬
‫یک ورزش (فوتبال ⃣️‪"1‬‬
‫"‪.\n‬یا بسکتبال) انتخاب کن‬
‫‌هایت را با ⃣️‪"2‬‬
‫مهارت‬
‫"‬

‫ارتقا بده — هرچه مجموع قدرت ‪Coin‬‬
‫باالتر باشد شانس بردت بیشتر‬

‫روی «شروع ⃣️‪3‬‬

‫‌شود‬
‫"‪.\n‬می‬

‫"‬

‫مسابقه رنک» بزن‪ .‬اگر همان لحظه حریف‬
‫‌کنی؛ در‬
‫واقعی منتظر باشد با او بازی می‬

‫غیر این صورت بالفاصله با هوش مصنوعی‬
‫‌دهی تا معطل نمانی‬
‫"‪.\n‬ربات مسابقه می‬

‫ورودی هر مسابقه ⃣️‪4‬‬

‫"‪f‬‬

‫‪ {MATCH_ENTRY_FEE} LIBER‬رنک‬

‫منهای کارمزد( است‪ .‬برنده مجموع جایزه‬
‫را )‪{MATCH_POT_FEE_PERCENT}%‬‬
‫‌برد‬
‫"‪.\n‬می‬

‫در هر مسابقه ⃣️‪5‬‬

‫"‪f‬‬

‫حمله رد و }‪{MATCH_POSSESSIONS‬‬

‫‌کننده‬
‫‌شود؛ در هر حمله قدرت حمله‬
‫بدل می‬
‫‌شود — قدرت‬
‫با قدرت دفاع مقایسه می‬

‫بیشتر یعنی گل بیشتر‪ .‬تساوی یعنی دفاع‬
‫"‪.\n‬در آخرین لحظه گل را گرفته‬

‫اگر نتیجه مساوی ⃣️‪6‬‬
‫‌کننده است‬
‫"‪.\n‬شود‪ ،‬ضربات پنالتی تعیین‬
‫بردها امتیاز رنک ⃣️‪"7‬‬
‫"‬

‫‌کنند‪ .‬امتیاز رنک‬
‫‌ها کم می‬
‫‌دهند‪ ،‬باخت‬
‫می‬

‫‌کننده لیگ رقابتی توست‪ :‬مبتدی ←‬
‫تعیین‬
‫‌ای ← استاد ← اژدهای آزاد ←‬
‫حرفه‬

‫‌ای‬
‫‌ای ← اژدهای کامل افسانه‬
‫اژدهای افسانه‬
‫"‪ ←.\n‬لیبر لجند وان‬

‫هر ‪ ۲‬ماه یک‌بار ⃣️‪8‬‬

‫"‬

‫ نفر برتر‬۵ ‫‌شود و‬
‫تورنمت فصلی بسته می‬

‫‌گیرند‬
‫ سه نفر اول( جایزه می‬LIBER ،‫نقد‬
‫)نفر چهارم و پنجم مدال‬.\n"

9️⃣ 🔥 «‫مسابقه‬

f"

‫سخت» یک حالت پرمخاطره است‬:

{HARD_MATCH_ENTRY_FEE} Coin
‫ حریف هوش مصنوعی‬،‫‌دهی‬
‫ورودی می‬

،‫‌شود‬
‫‌سازی می‬
‫‌تر از حد معمول شبیه‬
‫قوی‬

‫{ اما اگر ببری‬HARD_MATCH_REWARD}
Coin ‫‌گیری‬
‫جایزه می‬."
)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard("
competition"))
elif
data.startswith("sport_"):
sport =
data.split("_", 1)[1]
sport_info =

SPORTS[sport]
stats_lines = [
f"{label}: ‫سطح‬

{u[f'{sport}_{key}']}" for
key, label in

sport_info["stats"].items()
]
total_power =
get_total_power(user_id,
sport)
text = (
f"
{sport_info['title']} —
<b>‫‌ها‬
‫<پنل مهارت‬/b>\n\n"
+
"\n".join(stats_lines)
+ f"\n\n
‫قدرت‬: {total_power}"

🔋 ‫مجموع‬

)

stat_buttons = [

⬆️

InlineKeyboardButton(f"

{label}",
callback_data=f"upgrade_{spo
rt}_{key}")
for key, label
in
sport_info["stats"].items()
]
rows =
[stat_buttons[i:i+2] for i
in range(0,
len(stat_buttons), 2)]
rows.append([InlineKeyboardB

🎮 ‫"شروع مسابقه رنک‬,

utton("

callback_data=f"match_start_
{sport}")])
rows.append([InlineKeyboardB

🔥 ‫مسابقه سخت‬

utton("

)‫"(پرمخاطره‬,

callback_data=f"match_hard_{
sport}")])

rows.append([InlineKeyboardB

🔙 ‫"بازگشت‬,

utton("

callback_data="competition")
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=InlineKeyboardM
arkup(rows))
elif
data.startswith("upgrade_"):
_, sport, stat_key =
data.split("_", 2)
success, msg =
upgrade_stat(user_id, sport,
stat_key)
await
query.message.edit_text(msg,
reply_markup=back_keyboard(f
"sport_{sport}"))

elif
data.startswith("match_start
_"):
sport =
data.split("_", 2)[2]
if u["liber"] <
MATCH_ENTRY_FEE:
await
query.message.edit_text(

❌ ‫برای شرکت‬

f"

‫{ در مسابقه به‬MATCH_ENTRY_FEE}
LIBER ‫نیاز داری‬.",

reply_markup=back_keyboard(f
"sport_{sport}"),
)
return

add_currency(user_id,
"liber", -MATCH_ENTRY_FEE)

status, opponent_id
= join_match_queue(user_id,
sport)
if status ==
"waiting":
# ‫حریف واقعی آنالین‬

‫نبود؛ برای اینکه کاربر معطل نماند بالفاصله‬
‫‌دهد‬
‫با هوش مصنوعی مسابقه می‬

leave_match_queue(user_id)
match_data =
simulate_match(user_id,
None, sport, vs_bot=True)
apply_match_result(user_id,
0, sport, match_data,
vs_bot=True)

🏆 ‫ "!بردی‬if

result_emoji =

"

match_data["result"] ==

😔 ‫باختی‬."

"win" else "

text = (

f"⚔ <b>‫نتیجه‬
‫{ مسابقه‬SPORTS[sport]

['title']} (‫)هوش مصنوعی‬
</b>\n"
"‫حریف واقعی‬

‫ مسابقه با ربات برگزار‬،‫آنالین نبود‬
‫شد‬:\n\n"

+
"\n".join(match_data["log"])
+ f"\n\n
‫ شما‬:‫نتیجه نهایی‬

📊

{match_data['player_score']}
—
{match_data['opponent_score'
]}
{match_data['opponent_name']
}\n"
+ f"
‫شما‬:

🔋 ‫قدرت‬

{match_data['player_power']}

| ‫قدرت حریف‬:
{match_data['opponent_power'
]}\n\n"
+
result_emoji
)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard(f
"sport_{sport}"))
return
# ‫حریف واقعی پیدا شد‬
‫(حریف قبًال هزینه ورودی خودش را هنگام‬
)‫ورود به صف پرداخت کرده است‬
match_data =
simulate_match(user_id,
opponent_id, sport,
vs_bot=False)
apply_match_result(user_id,

opponent_id, sport,
match_data, vs_bot=False)
result_emoji = "

🏆

‫ "!بردی‬if match_data["result"]

😔 ‫باختی‬."

== "win" else "

text = (

f"⚔ <b>‫نتیجه مسابقه‬

{SPORTS[sport]['title']}
</b>\n\n"
+

"\n".join(match_data["log"])
+ f"\n\n
‫ شما‬:‫نهایی‬

📊 ‫نتیجه‬

{match_data['player_score']}
—
{match_data['opponent_score'
]}
{match_data['opponent_name']
}\n"
+ f"

🔋 ‫قدرت شما‬:

{match_data['player_power']}

| ‫قدرت حریف‬:
{match_data['opponent_power'
]}\n\n"
+ result_emoji
)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard(f
"sport_{sport}"))
try:
opp_result =
"win" if
match_data["result"] ==
"loss" else "loss"
opp_emoji = "

🏆

‫ "!بردی‬if opp_result == "win"

😔 ‫باختی‬."

else "

await

context.bot.send_message(
opponent_id,

f"⚔ ‫مسابقه‬

{SPORTS[sport]['title']} ‫تمام‬
‫\!شد‬n"

f"‫نتیجه‬:

{match_data['opponent_score'
]} —
{match_data['player_score']}
\n{opp_emoji}",
)
except Exception:
pass
elif
data.startswith("match_hard_
"):
sport =
data.split("_", 2)[2]
if u["coin"] <
HARD_MATCH_ENTRY_FEE:
await
query.message.edit_text(

❌ ‫برای مسابقه‬

f"

‫{ سخت به‬HARD_MATCH_ENTRY_FEE}
Coin ‫نیاز داری‬.",

reply_markup=back_keyboard(f
"sport_{sport}"),
)
return

add_currency(user_id,
"coin", HARD_MATCH_ENTRY_FEE)
match_data =
simulate_hard_match(user_id,
sport)
add_currency(user_id,
"matches_played", 1)
if
match_data["result"] ==
"win":

add_currency(user_id,
"coin", HARD_MATCH_REWARD)
add_currency(user_id,
"matches_won", 1)
add_currency(user_id,
"rank_points",
RANK_WIN_POINTS)
f"

🔥🏆 ‫!بردی‬

result_emoji =

{HARD_MATCH_REWARD} Coin ‫جایزه‬
‫"!گرفتی‬

else:
u2 =
get_user(user_id)
if
u2["rank_points"] +
RANK_LOSS_POINTS < 0:
set_field(user_id,

"rank_points", 0)
else:
add_currency(user_id,
"rank_points",
RANK_LOSS_POINTS)
f"

😔 ‫باختی و‬

result_emoji =

{HARD_MATCH_ENTRY_FEE} Coin
‫ حریف سخت بود‬.‫"!را از دست دادی‬
text = (

🔥 <b>‫مسابقه سخت‬

f"

{SPORTS[sport]['title']}
</b>\n\n"
+

"\n".join(match_data["log"])
+ f"\n\n
‫ شما‬:‫نهایی‬

📊 ‫نتیجه‬

{match_data['player_score']}
—
{match_data['opponent_score'

]}
{match_data['opponent_name']
}\n"
+ f"

🔋 ‫قدرت شما‬:

{match_data['player_power']}
| ‫قدرت حریف‬:
{match_data['opponent_power'
]}\n\n"
+ result_emoji
)
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=back_keyboard(f
"sport_{sport}"))
elif data ==
"match_cancel_queue":
leave_match_queue(user_id)
await
query.message.edit_text("

❌

‫از صف انتظار خارج شدی‬.",
reply_markup=back_keyboard("
competition"))
# ---------------- ‫پنل‬

‫ ادمین‬---------------elif data ==

"admin_panel" and user_id in
ADMIN_IDS:
await
show_admin_panel(query)
elif data ==
"admin_force_tournament" and
user_id in ADMIN_IDS:
await
maybe_resolve_tournament_for
ced(context.bot)
await
query.message.edit_text("

✅

‫تورنمت فصلی برگزار شد و جوایز ارسال‬
‫شد‬.",

reply_markup=back_keyboard("
admin_panel"))
elif data ==
"admin_info_broadcast" and
user_id in ADMIN_IDS:
await
query.message.edit_text(

📢 ‫برای ارسال پیام‬

"

‫همگانی از دستور زیر در چت استفاده‬
‫کن‬:\n<code>/broadcast ‫متن‬
‫<پیام‬/code>",

parse_mode=ParseMode.HTML,
reply_markup=back_keyboard("
admin_panel"),
)
elif data ==
"admin_info_ban" and user_id
in ADMIN_IDS:

await
query.message.edit_text(

🚫 ‫برای مسدود یا رفع‬

"

‫مسدودی کاربر از دستورات زیر استفاده‬
‫کن‬:\n"

"<code>/ban
USER_ID</code>\n<code>/unban
USER_ID</code>",
parse_mode=ParseMode.HTML,
reply_markup=back_keyboard("
admin_panel"),
)
# ---------------- ‫ راهنما‬--------------elif data == "help":
text = (

❓ <b>‫راهنمای کامل‬
LIBER</b>\n\n"
"🌍 <b>‫امپراتوری من‬:
"

‫کشورت رو بساز‪ ،‬مالیات جمع کن‪</b> ،‬‬
‫‌ات رو ارتقا بده‬
‫"‪.\n‬دفاع و فناوری‬

‫‪:‬بازار زنده>‪💹 <b‬‬

‫"‬

‫بخر و بفروش؛ قیمت هر ‪</b> LIBER‬‬
‫‌کنه‬
‫"‪.\n‬ساعت خودش تغییر می‬

‫‪:‬بانک مرکزی>‪🏦 <b‬‬

‫"‬

‫سپرده بذار سود بگیر‪ ،‬یا وام >‪</b‬‬

‫صندوق>‪🎁 <b‬‬

‫"‬

‫"‪.\n‬بگیر‬

‫با >‪:</b‬شانس‬

‫صندوق باز کن ‪Coin/LIBER/Diamond‬‬
‫"‪.\n‬و جایزه شانسی بگیر‬

‫مأموریت>‪🎯 <b‬‬

‫"‬

‫و ‪ XP‬هر روز با یک کلیک >‪:</b‬روزانه‬
‫"‪.\n‬رایگان بگیر ‪LIBER‬‬

‫‪:‬رقابت آنالین>‪"⚔ <b‬‬

‫فوتبال یا بسکتبال انتخاب کن‪</b> ،‬‬

‫‌بازی کن‬
‫‌هاتو ارتقا بده و رنک‬
‫"‪.\n‬مهارت‬

‫با >‪⭐ <b>VIP:</b‬‬

‫"‬

‫یا با تلگرام استارز اشتراک ‪Diamond‬‬
‫ویژه بگیر و مزایای بیشتر داشته‬
‫"‪.\n‬باش‬

‫خرید با>‪🌟 <b‬‬

‫"‬

‫‌تونی مستقیم >‪:</b‬استارز‬
‫از فروشگاه می‬
‫یا اشتراک ‪ LIBER‬با تلگرام استارز‬
‫"‪.\n‬بخری‬

‫‪:‬پشتیبانی>‪"☎ <b‬‬
‫هر مشکلی داشتی از دکمه پشتیبانی >‪</b‬‬
‫پیام بده‪ ،‬مستقیم برای ادمین ارسال‬

‫هر سوالی داشتی از"‬

‫"💬‬

‫‌شه‬
‫"‪.\n\n‬می‬

‫!پشتیبانی بپرس‬
‫)‬

‫‪await‬‬
‫‪query.message.edit_text(text‬‬
‫‪, parse_mode=ParseMode.HTML,‬‬
‫)(‪reply_markup=back_keyboard‬‬
‫)‬
‫پشتیبانی ‪# ----------------‬‬

‫‪----------------‬‬

‫‪elif data == "support":‬‬
‫_‪context.user_data["awaiting‬‬

‫‪support"] = True‬‬
‫( = ‪text‬‬
‫پشتیبانی>‪"☎ <b‬‬
‫"‪LIBER</b>\n\n‬‬
‫پیام خود را همینجا در"‬

‫چت تایپ و ارسال کن؛ پیام شما مستقیمًا‬

‫‌شود‬
‫" برای ادمین ارسال می‬

‫‌زودی پاسخ داده"‬
‫و به‬
‫برای خرید اشتراک هم"‬

‫‌شود‬
‫"‪.\n\n‬می‬

‫‌تونی همینجا بنویسی‪ ،‬یا مستقیم از‬
‫می‬

‫"‪.‬اقدام کنی ‪⭐ VIP‬‬

‫بخش‬

‫)‬

‫‪await‬‬
‫‪query.message.edit_text(text‬‬
‫‪, parse_mode=ParseMode.HTML,‬‬
‫)(‪reply_markup=back_keyboard‬‬
‫)‬
‫مشاور ‪# ----------------‬‬

‫‪ ---------------‬هوشمند‬‫== ‪elif data‬‬

"smart_advisor":
tips =
get_smart_advice(user_id)
text = "

🤖 <b>‫مشاور‬

‫ هوشمند‬LIBER</b>\n\n‫بر اساس‬
‫ این پیشنهادها رو‬،‫‌ات‬
‫وضعیت فعلی‬

‫دارم‬:\n\n" + "\n\n".join(
f"• {tip}" for
tip in tips
)
kb =
InlineKeyboardMarkup([

🔄

[InlineKeyboardButton("
‫"تحلیل مجدد‬,

callback_data="smart_advisor
")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])

await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
# ---------------- ‫کد هدیه‬
---------------elif data ==
"gift_code":
context.user_data["awaiting_
gift_code"] = True
text = (

🎁 <b>‫کد‬

"
‫<هدیه‬/b>\n\n"

"‫‌ات را همینجا‬
‫کد هدیه‬

‫‌اش را‬
‫در چت تایپ و ارسال کن تا جایزه‬
‫دریافت کنی‬."
)

await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,

reply_markup=back_keyboard()
)
# ---------------- ‫اخبار‬

‫ جهانی‬----------------

elif data == "news":
news_lines =
get_world_news()
text = "

📰 <b>‫اخبار زنده‬

‫ جهان‬LIBER</b>\n\n" +

"\n\n".join(f"• {line}" for
line in news_lines)
kb =
InlineKeyboardMarkup([

🔄

[InlineKeyboardButton("
‫"بروزرسانی اخبار‬,

callback_data="news")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],

])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
# ---------------- ‫برداشت‬
TON ---------------elif data == "withdraw":
my_requests =
list_user_withdrawals(user_i
d, limit=5)
lines = [
f"#
{r['request_id']} —
{r['amount_liber']} LIBER —
{r['status']}"
for r in
my_requests
‫‌ای‬
‫نکرده‬."]

] or ["‫هیچ درخواستی ثبت‬
text = (

📤 <b>‫برداشت‬
LIBER ‫ به‬TON</b>\n\n"
f"💼 ‫موجودی فعلی‬:
{u['liber']} LIBER\n"
f"📉 ‫حداقل مبلغ‬
"

‫برداشت‬: {MIN_WITHDRAW_LIBER}
LIBER\n"

💸 ‫کارمزد برداشت‬:
{WITHDRAW_FEE_PERCENT}%\n\n"
"📜 ‫آخرین‬
f"

‫‌های تو‬
‫درخواست‬:\n" +
"\n".join(lines)
)
kb =

InlineKeyboardMarkup([

📤 ‫ثبت‬

[InlineKeyboardButton("
‫"درخواست برداشت جدید‬,

callback_data="withdraw_new"
)],

🔙

[InlineKeyboardButton("

‫"بازگشت به منو‬,
callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
elif data ==
"withdraw_new":
if u["liber"] <
MIN_WITHDRAW_LIBER:
await
query.message.edit_text(

❌ ‫برای ثبت‬

f"

‫درخواست برداشت حداقل به‬

{MIN_WITHDRAW_LIBER} LIBER
‫نیاز داری‬.\n"

f"‫موجودی فعلی‬

‫تو‬: {u['liber']} LIBER",

reply_markup=back_keyboard("

withdraw"),
)
return
context.user_data["awaiting_
withdraw_amount"] = True
await
query.message.edit_text(

📤 ‫ چند‬LIBER

f"

‫‌خوای برداشت کنی؟‬
‫\می‬n"

f"(‫حداقل‬
{MIN_WITHDRAW_LIBER}، ‫حداکثر‬
{u['liber']})\n\n"
"‫فقط عدد رو تایپ‬

‫کن‬:",

reply_markup=back_keyboard("
withdraw"),
)
# ---------------- ‫ واریز‬---------------

‫‪elif data == "deposit":‬‬
‫( = ‪text‬‬

‫واریز ‪📥 <b>/‬‬

‫"‬

‫"‪</b>\n\n‬افزایش موجودی‬

‫در حال حاضر امکان"‬

‫‌صورت خودکار وجود ‪ TON‬واریز مستقیم‬
‫به‬
‫‌تونی همین االن‬
‫" ندارد‪ ،‬ولی می‬

‫با تلگرام استارز"‬

‫بخری و آنی به کیف پولت اضافه ‪LIBER‬‬
‫بشه — سریع‪ ،‬امن و بدون نیاز به تایید‬
‫"‪.‬ادمین‬

‫)‬
‫= ‪kb‬‬
‫[(‪InlineKeyboardMarkup‬‬

‫🌟‬

‫"(‪[InlineKeyboardButton‬‬
‫‪",‬با استارز ‪ LIBER‬خرید‬

‫‪callback_data="star_liber_me‬‬
‫‪nu")],‬‬

‫🔙‬

‫"(‪[InlineKeyboardButton‬‬
‫‪",‬بازگشت به منو‬

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)
else:
await
query.message.edit_text("

🔧

‫این بخش هنوز در حال توسعه است‬.",
reply_markup=back_keyboard()
)

async def
build_admin_dashboard_text()
:
now =
datetime.now().strftime("%Y%m-%d %H:%M:%S")
conn = db()

c = conn.cursor()
c.execute("SELECT
COUNT(*) as cnt FROM users")
total_users =
c.fetchone()["cnt"]
c.execute("SELECT
COUNT(*) as cnt FROM users
WHERE banned=1")
banned_users =
c.fetchone()["cnt"]
c.execute("SELECT
COALESCE(SUM(liber),0) as s
FROM users")
total_liber =
c.fetchone()["s"]
c.execute("SELECT
COALESCE(SUM(coin),0) as s
FROM users")
total_coin =
c.fetchone()["s"]
c.execute("SELECT
COUNT(*) as cnt FROM

matches")
total_matches =
c.fetchone()["cnt"]
c.execute("SELECT
COUNT(*) as cnt FROM
match_queue")
queue_count =
c.fetchone()["cnt"]
c.execute("SELECT
first_name, rank_points FROM
users ORDER BY rank_points
DESC LIMIT 1")
top_row = c.fetchone()
c.execute("SELECT
COUNT(*) as cnt FROM users
WHERE warn_count > 0")
warned_users =
c.fetchone()["cnt"]
c.execute("SELECT
COUNT(*) as cnt FROM
withdrawal_requests WHERE
status='pending'")

pending_withdrawals =
c.fetchone()["cnt"]
conn.close()
days_left =
get_tournament_info()
top_competitor = f"
{top_row['first_name']}
({top_row['rank_points']}
‫ ")امتیاز‬if top_row else "—"
text = (

👑 <b>‫پنل مدیریت‬

"

TITAN</b>\n"

"━━━━━━━━━━━━━━━\n"

🕒 ‫زمان سرور‬:
{now}\n"
f"👥 ‫کل کاربران‬:
{total_users}\n"
f"🚫 ‫کاربران مسدود‬:
f"

{banned_users}\n"

⚠️ ‫کاربران دارای اخطار‬:

f"

{warned_users}\n"

"━━━━━━━━━━━━━━━\n"

📈 ‫قیمت بازار‬:
{get_market_price()} Coin\n"
f"🪙 ‫ مجموع‬LIBER ‫در‬
f"

‫اقتصاد‬:

{round(total_liber,2)}\n"

💵 ‫ مجموع‬Coin ‫در‬

f"
‫اقتصاد‬:

{round(total_coin,2)}\n"
"━━━━━━━━━━━━━━━\n"
f"⚔ ‫مجموع مسابقات‬

‫‌شده‬
‫انجام‬: {total_matches}\n"

⏳ ‫کاربران در صف انتظار‬
‫مسابقه‬: {queue_count}\n"
f"🥇 ‫‌گر‬
‫برترین رقابت‬:
{top_competitor}\n"
f"🏆 ‫تا پایان تورنمت فصلی‬:
f"

{days_left} ‫\روز‬n"

📤 ‫درخواست‌های برداشت‬

f"

‫در انتظار‬: {pending_withdrawals}
(/withdrawals)"
)
return text

async def
show_admin_panel(query):
text = await
build_admin_dashboard_text()
kb =
InlineKeyboardMarkup([

🔄

[InlineKeyboardButton("
‫"بروزرسانی‬,

callback_data="admin_panel")
,

🏆

InlineKeyboardButton("
‫"برگزاری فوری تورنمت‬,

callback_data="admin_force_t

ournament")],

📢 ‫پیام‬

[InlineKeyboardButton("
‫( همگانی‬/broadcast)",

callback_data="admin_info_br
oadcast"),

🚫

InlineKeyboardButton("
‫( مسدودسازی‬/ban)",

callback_data="admin_info_ba
n")],

🔙

[InlineKeyboardButton("
‫"بازگشت به منو‬,

callback_data="back_main")],
])
await
query.message.edit_text(text
, parse_mode=ParseMode.HTML,
reply_markup=kb)

#
============================
============================
====
#

)‫دستورات ادمین (متنی‬

#
============================
============================
====
async def
admin_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
user_id =
update.effective_user.id
if user_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

text = await
build_admin_dashboard_text()
kb =
InlineKeyboardMarkup([

🔄

[InlineKeyboardButton("
‫"بروزرسانی‬,

callback_data="admin_panel")
,

🏆

InlineKeyboardButton("
‫"برگزاری فوری تورنمت‬,

callback_data="admin_force_t
ournament")],
])
await
update.message.reply_text(te
xt,
parse_mode=ParseMode.HTML,
reply_markup=kb)

async def
ban_command(update: Update,
context:
ContextTypes.DEFAULT_TYPE):
user_id =
update.effective_user.id
if user_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /ban USER_ID")
return
target_id =
int(context.args[0])
set_field(target_id,
"banned", 1)
await

update.message.reply_text(f"

🚫 ‫{ کاربر‬target_id} ‫مسدود شد‬.")
async def
unban_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
user_id =
update.effective_user.id
if user_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /unban USER_ID")
return
target_id =

int(context.args[0])
set_field(target_id,
"banned", 0)
await
update.message.reply_text(f"

✅ ‫{ کاربر‬target_id} ‫از مسدودی‬
‫خارج شد‬.")

async def
broadcast_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
user_id =
update.effective_user.id
if user_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:

await
update.message.reply_text("‫سا‬
‫ادهتف‬: /broadcast ‫)"متن پیام‬
return

message_text = "
".join(context.args)
conn = db()
c = conn.cursor()
c.execute("SELECT
user_id FROM users")
all_users = c.fetchall()
conn.close()
sent = 0
for row in all_users:
try:
await
context.bot.send_message(row

📢

["user_id"], f"

{message_text}")

sent += 1
except Exception:
pass

await
update.message.reply_text(f"

✅ ‫{ پیام برای‬sent} ‫کاربر ارسال‬
‫شد‬.")

async def
setbio_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
user_id =
update.effective_user.id
if is_banned(user_id):
return
if not context.args:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /setbio ‫متن بیوگرافی‬

‫\تو‬n‫مثال‬: /setbio ‫عاشق اقتصاد و‬
‫فوتبالم‬

⚽💰")

return

bio_text = "

".join(context.args)
if
contains_banned_word(bio_tex
t):
await
update.message.reply_text("

⚠️ ‫این متن شامل الفاظ نامناسب است و‬
‫ذخیره نشد‬.")

return

if len(bio_text) > 150:
bio_text =
bio_text[:150]
set_field(user_id,
"bio", bio_text)
await
update.message.reply_text("

✅ ‫ از منوی‬.‫بیوگرافی شما بروزرسانی شد‬
‫‌توانی آن را ببینی‬
‫«پروفایل من» می‬.")

async def
text_message_filter(update:

Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫اول پیام پشتیبانی را بررسی‬

‫ سپس فیلتر فحش ساده را روی‬،‫‌کند‬
‫می‬
‫‌کند‬
‫‌های متنی کاربر اجرا می‬
‫پیام‬."""

if not update.message or
not update.message.text:
return
user_id =
update.effective_user.id
if is_banned(user_id):
return
# ---------------- ‫پیام‬

‫ پشتیبانی‬---------------if

context.user_data.get("await
ing_support"):
context.user_data["awaiting_
support"] = False
u =

get_user(user_id)
username_display =
f"@{u['username']}" if u and
u["username"] else "‫بدون نام‬
‫"کاربری‬

forward_text = (

📩 <b>‫پیام پشتیبانی‬
‫<جدید‬/b>\n\n"
f"👤 ‫نام‬:
"

{update.effective_user.first
_name}\n"

🪪 ‫نام کاربری‬:
{username_display}\n"
f"🆔 ‫آیدی‬: <code>
{user_id}</code>\n\n"
f"✉️ ‫متن‬
f"

‫پیام‬:\n{update.message.text}\n
\n"
f"‫برای پاسخ‬:

<code>/reply {user_id} ‫متن‬
‫<پاسخ‬/code>"
)

sent_to_any = False
for admin_id in
ADMIN_IDS:
try:
await
context.bot.send_message(adm
in_id, forward_text,
parse_mode=ParseMode.HTML)
sent_to_any
= True
except Exception
as e:
logger.warning(f"Could not
forward support message to
admin {admin_id}: {e}")
if sent_to_any:
await
update.message.reply_text("

✅ .‫پیام شما برای پشتیبانی ارسال شد‬
‫‌شود‬
‫‌زودی پاسخ داده می‬
‫به‬.")
else:

await
update.message.reply_text("

⚠️ ‫در حال حاضر پشتیبانی در دسترس‬
‫ بعدًا دوباره امتحان کن‬،‫نیست‬.")
return

# ---------------- ‫کد هدیه‬
---------------if
context.user_data.get("await
ing_gift_code"):
context.user_data["awaiting_
gift_code"] = False
success, msg =
redeem_gift_code(user_id,
update.message.text)
await
update.message.reply_text(ms
g)
return

# ---------------- ‫برداشت‬

TON: )‫ (مبلغ‬۱ ‫ مرحله‬--------------if
context.user_data.get("await
ing_withdraw_amount"):
context.user_data["awaiting_
withdraw_amount"] = False
u =
get_user(user_id)
try:
amount =
float(update.message.text.st
rip())
except ValueError:
await
update.message.reply_text("
‫لطفًا فقط عدد وارد کن‬.")

❌

return
if amount <

MIN_WITHDRAW_LIBER:

await
update.message.reply_text(f"

❌ ‫حداقل مبلغ برداشت‬

{MIN_WITHDRAW_LIBER} LIBER
‫است‬.")
return
if amount >
u["liber"]:
await
update.message.reply_text(f"

❌ ‫ موجودی فعلی‬.‫موجودی کافی نداری‬:
{u['liber']} LIBER")
return
context.user_data["pending_w
ithdraw_amount"] = amount
context.user_data["awaiting_
withdraw_address"] = True
await
update.message.reply_text("

💳 ‫ حاال آدرس کیف پول‬TON ‫خودت رو‬

‫وارد کن‬:")
return
# ---------------- ‫برداشت‬

TON: )‫ (آدرس‬۲ ‫ مرحله‬--------------if
context.user_data.get("await
ing_withdraw_address"):
context.user_data["awaiting_
withdraw_address"] = False
amount =
context.user_data.pop("pendi
ng_withdraw_amount", None)
if not amount:
await
update.message.reply_text("

❌ ‫ دوباره از‬،‫خطا در ثبت درخواست‬
‫منوی برداشت شروع کن‬.")
return
ton_address =

update.message.text.strip()
success, result =
create_withdraw_request(user
_id, amount, ton_address)
if not success:
await
update.message.reply_text(re
sult)
return
request_id = result
u =
get_user(user_id)
is_suspicious =
check_suspicious_liber_gain(
user_id, amount)
await
update.message.reply_text(

✅ ‫درخواست برداشت‬

f"

#{request_id} ‫ثبت شد و در انتظار‬
‫تایید ادمین است‬.\n"

💰 ‫مبلغ‬:
{amount} LIBER\n📍 ‫آدرس‬:
f"

{ton_address}\n\n"
"‫ نتیجه‬،‫به محض بررسی‬

‫‌شود‬
‫برایت ارسال می‬."
)

suspicious_line = (

🚨 <b>‫هشدار‬:

f"\n\n

</b> ‫این مبلغ بیشتر از حد معمول است‬
({SUSPICIOUS_LIBER_GAIN_THRE
SHOLD}+ LIBER) — ،‫قبل از تایید‬

‫ حساب کاربر رو با‬/finduser ‫بررسی‬
‫کن‬."

if is_suspicious
else ""
)
forward_text = (

📤 <b>‫درخواست‬
‫<برداشت جدید‬/b>\n\n"
f"🆔 ‫شماره درخواست‬:
#{request_id}\n"
f"👤 ‫کاربر‬:
"

{update.effective_user.first
_name} (@{u['username'] or

'—'})\n"

🆔 ‫آیدی‬: <code>
{user_id}</code>\n"
f"💰 ‫مبلغ‬:
{amount} LIBER\n"
f"📍 ‫ آدرس‬TON:
f"

{ton_address}"
+

suspicious_line +
f"\n\n‫برای تایید‬:
<code>/approvewithdraw
{request_id}</code>\n"
f"‫برای رد‬:

<code>/rejectwithdraw
{request_id}</code>"
)
for admin_id in
ADMIN_IDS:
try:
await
context.bot.send_message(adm
in_id, forward_text,

parse_mode=ParseMode.HTML)
except Exception
as e:
logger.warning(f"Could not
notify admin {admin_id}
about withdrawal: {e}")
return
# ---------------- ‫فیلتر‬

‫ فحش‬---------------if

contains_banned_word(update.
message.text):
conn = db()
c = conn.cursor()
c.execute("UPDATE
users SET
warn_count=warn_count+1
WHERE user_id=?",
(user_id,))
conn.commit()

c.execute("SELECT
warn_count FROM users WHERE
user_id=?", (user_id,))
warn_count =
c.fetchone()["warn_count"]
conn.close()
if warn_count >=
MAX_WARN_BEFORE_BAN:
set_field(user_id, "banned",
1)
await
update.message.reply_text("

🚫 ‫به دلیل استفاده مکرر از الفاظ‬

‫ حساب شما مسدود شد‬،‫نامناسب‬.")
else:
await
update.message.reply_text(
f"
‫لطفًا از‬

⚠️

‫ اخطار‬.‫الفاظ نامناسب استفاده نکن‬

{warn_count}/{MAX_WARN_BEFOR
E_BAN}"

)

async def
reply_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫ادمین با این دستور به پیام‬

‫‌دهد‬
‫پشتیبانی کاربر پاسخ می‬: /reply
USER_ID ‫"""متن پاسخ‬
admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if len(context.args) <
2:
await
update.message.reply_text("‫سا‬

‫ادهتف‬: /reply USER_ID ‫)"متن پاسخ‬
return
try:
target_id =
int(context.args[0])
except ValueError:
await
update.message.reply_text("

❌ ‫آیدی عددی نامعتبر است‬.")
return

reply_text = "
".join(context.args[1:])
try:
await
context.bot.send_message(tar

📩 <b>‫پاسخ پشتیبانی‬:

get_id, f"

</b>\n\n{reply_text}",

parse_mode=ParseMode.HTML)
await
update.message.reply_text("

✅ ‫پاسخ ارسال شد‬.")

except Exception as e:

await
update.message.reply_text(f"

❌ ‫ارسال پاسخ ناموفق بود‬: {e}")
async def
finduser_command(update:
Update, context:

ContextTypes.DEFAULT_TYPE):
"""‫جزئیات کامل یک کاربر را نشان‬

‫‌دهد‬
‫می‬: /finduser USER_ID"""
admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await

update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:
await
update.message.reply_text("‫سا‬

‫ادهتف‬: /finduser USER_ID")
return
try:
target_id =
int(context.args[0])
except ValueError:
await
update.message.reply_text("

❌ ‫آیدی عددی نامعتبر است‬.")
return

u = get_user(target_id)
if not u:
await
update.message.reply_text("

❌ ‫کاربری با این آیدی پیدا نشد‬.")
return

text = (

👤 <b>

f"

{u['first_name']}</b>
(@{u['username'] or '—'})\n"

🆔 <code>

f"

{target_id}</code>\n"

🪙 LIBER:
{u['liber']} | 💵 Coin:
{u['coin']} | 💎 Diamond:
{u['diamond']}\n"
f"⭐ ‫سطح‬:
f"

{u['level']} | VIP:
{u['vip']} ‫تا‬

{u['vip_expires_at'] or
'—'}\n"

🚫 ‫مسدود‬: {'‫ 'بله‬if
u['banned'] else '‫️⚠ | }'خیر‬
‫اخطار‬: {u['warn_count']}\n"
f"📅 ‫عضویت‬:
{u['joined_at']} | 🔁 ‫ورود‬:
f"

{u['login_count']}"
)
await

update.message.reply_text(te
xt,
parse_mode=ParseMode.HTML)

async def
grantliber_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫ تکمیل دستی خرید‬LIBER

‫توسط ادمین‬: /grantliber
USER_ID AMOUNT"""
admin_id =

update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if len(context.args) <
2:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /grantliber USER_ID
‫)"مقدار‬

return

try:
target_id =
int(context.args[0])
amount =
float(context.args[1])
except ValueError:
await
update.message.reply_text("

❌ ‫مقدار یا آیدی نامعتبر است‬.")
return

add_currency(target_id,
"liber", amount)
await
update.message.reply_text(f"

✅ {amount} LIBER ‫به کاربر‬
{target_id} ‫اضافه شد‬.")
try:
await

context.bot.send_message(tar

🎉 {amount} LIBER

get_id, f"

‫توسط پشتیبانی به کیف پول شما اضافه‬
‫)"!شد‬

except Exception:
pass

async def
grantvip_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫تکمیل دستی خرید اشتراک‬

‫توسط ادمین‬: /grantvip USER_ID
TIER DAYS
TIER ‫یکی از‬: normal,
dragon, dragon_legend"""
admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if len(context.args) <

3:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /grantvip USER_ID TIER
DAYS\nTIER: normal | dragon
| dragon_legend")
return
try:
target_id =
int(context.args[0])
tier_key =
context.args[1]
days =
int(context.args[2])
except ValueError:
await
update.message.reply_text("

❌ ‫ورودی نامعتبر است‬.")
return

if tier_key not in
STAR_SUBSCRIPTIONS:
await

update.message.reply_text("

❌ ‫( نوع اشتراک نامعتبر است‬normal

| dragon | dragon_legend).")
return
plan =
STAR_SUBSCRIPTIONS[tier_key]
start, end =
activate_star_subscription(t
arget_id, tier_key, days)
await
update.message.reply_text(f"

✅ ‫{ اشتراک‬plan['title']} ‫برای‬

{days} ‫{ روز به کاربر‬target_id}
‫داده شد‬.")
try:
await
context.bot.send_message(
target_id,

🎉 <b>‫اشتراک شما‬
‫<!فعال شد‬/b>\n\n🏷 ‫نوع‬:
{plan['title']}\n"
f"📅 ‫از‬:
f"

{start.strftime('%Y-%m-%d')}
‫{ تا‬end.strftime('%Y-%m%d')}\n\n"

🎁 ‫مزایا‬:
{plan['benefits']}\n\n‫مبارک‬
‫ لذت ببرید‬،‫"🐉 !باشه‬,
f"

parse_mode=ParseMode.HTML,
)
except Exception:
pass

async def
createcode_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫ساخت کد هدیه‬:

/createcode CODE FIELD
AMOUNT MAX_USES
FIELD ‫یکی از‬: liber, coin,
diamond, medal"""

admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if len(context.args) <
4:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /createcode CODE FIELD
AMOUNT MAX_USES\nFIELD:

liber | coin | diamond |
medal")
return
code, field, amount_str,
max_uses_str =
context.args[0],
context.args[1],
context.args[2],

context.args[3]
if field not in
("liber", "coin", "diamond",
"medal"):
await
update.message.reply_text("

❌ ‫( نوع جایزه نامعتبر است‬liber |
coin | diamond | medal).")
return
try:
amount =
float(amount_str)
max_uses =
int(max_uses_str)
except ValueError:
await
update.message.reply_text("

❌ ‫مقدار یا تعداد استفاده نامعتبر‬
‫است‬.")

return
success =
create_gift_code(code,

field, amount, max_uses,
admin_id)
if success:
await
update.message.reply_text(f"

✅ ‫{« کد هدیه‬code.upper()}»

‫ساخته شد‬: +{amount} {field} (‫تا‬
{max_uses} ‫)نفر‬.")
else:

await
update.message.reply_text("
‫این کد قبًال ساخته شده — یک کد‬

❌

‫دیگر انتخاب کن‬.")

async def
withdrawals_command(update:
Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫‌های‬
‫نمایش لیست درخواست‬

‫"""برداشت در انتظار تایید‬
admin_id =

update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

pending =
list_pending_withdrawals()
if not pending:
await
update.message.reply_text("

📭 ‫هیچ درخواست برداشتی در انتظار‬
‫نیست‬.")

return
lines = []
for r in pending:
u =
get_user(r["user_id"])
lines.append(
f"#
{r['request_id']} —

{u['first_name'] if u else
'—'} ({r['user_id']}) — "
f"
{r['amount_liber']} LIBER →
{r['ton_address']}"
)

📤 <b>‫درخواست‌های‬

text = "

‫<برداشت در انتظار‬/b>\n\n" +
"\n".join(lines) + (

"\n\n‫برای تایید‬:

/approvewithdraw ID\n‫برای رد‬:
/rejectwithdraw ID"
)
await
update.message.reply_text(te
xt,
parse_mode=ParseMode.HTML)

async def
approvewithdraw_command(upda
te: Update, context:

ContextTypes.DEFAULT_TYPE):
"""‫تایید درخواست برداشت‬:
/approvewithdraw
REQUEST_ID"""
admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /approvewithdraw
REQUEST_ID")
return
try:
request_id =
int(context.args[0])
except ValueError:

await
update.message.reply_text("

❌ ‫شماره درخواست نامعتبر است‬.")
return

success, req =
approve_withdraw_request(req
uest_id)
if not success:
await
update.message.reply_text("
‫این درخواست پیدا نشد یا قبًال‬

❌

‫پردازش شده‬.")

return
net_amount =
round(req["amount_liber"] req["fee_liber"], 2)
await
update.message.reply_text(f"

✅ ‫ درخواست‬#{request_id} ‫تایید‬
‫ مبلغ خالص‬.‫شد‬: {net_amount}

LIBER ‫ معادل‬TON ‫برای واریز دستی‬.")
try:

await
context.bot.send_message(
req["user_id"],

✅ ‫درخواست برداشت‬
#{request_id} ‫\!تو تایید شد‬n"
f"💰 ‫بعد( مبلغ خالص‬
f"

‫{ از‬WITHDRAW_FEE_PERCENT}%
‫)کارمزد‬: {net_amount} LIBER
‫ معادل‬TON\n"

📍 ‫به آدرس‬:

f"

{req['ton_address']}\n\n‫‌زودی‬
‫به‬
TON ‫‌شه‬
‫به کیف پولت واریز می‬.",
)
except Exception:
pass

async def
rejectwithdraw_command(updat
e: Update, context:
ContextTypes.DEFAULT_TYPE):
"""‫رد درخواست برداشت و‬

‫بازگرداندن مبلغ‬: /rejectwithdraw
REQUEST_ID"""
admin_id =
update.effective_user.id
if admin_id not in
ADMIN_IDS:
await
update.message.reply_text("

⛔ ‫شما دسترسی ادمین ندارید‬.")
return

if not context.args:
await
update.message.reply_text("‫سا‬
‫ادهتف‬: /rejectwithdraw
REQUEST_ID")
return
try:
request_id =
int(context.args[0])
except ValueError:
await
update.message.reply_text("

❌ ‫شماره درخواست نامعتبر است‬.")
return

success, req =
reject_withdraw_request(requ
est_id)
if not success:
await
update.message.reply_text("
‫این درخواست پیدا نشد یا قبًال‬

❌

‫پردازش شده‬.")

return
await
update.message.reply_text(f"

↩️ ‫ درخواست‬#{request_id} ‫رد شد‬

‫{ و‬req['amount_liber']} LIBER
‫به کاربر بازگردانده شد‬.")
try:
await
context.bot.send_message(
req["user_id"],

❌ ‫درخواست برداشت‬

f"

#{request_id} ‫تو رد شد و‬

{req['amount_liber']} LIBER
‫به کیف پولت برگشت‬.\n"

"‫برای اطالع بیشتر با‬

‫پشتیبانی صحبت کن‬.",
)

except Exception:
pass

#
============================
============================
====
#

‫( پرداخت با تلگرام استارز‬Telegram

Stars)
#
============================
============================
====
async def
precheckout_callback(update:

Update, context:
ContextTypes.DEFAULT_TYPE):
query =
update.pre_checkout_query
await
query.answer(ok=True)

async def
successful_payment_callback(
update: Update, context:
ContextTypes.DEFAULT_TYPE):
payment =
update.message.successful_pa
yment
user_id =
update.effective_user.id
payload =
payment.invoice_payload
if
payload.startswith("vip:"):

_, tier_key,
days_str =
payload.split(":")
days = int(days_str)
plan =
STAR_SUBSCRIPTIONS.get(tier_
key)
start, end =
activate_star_subscription(u
ser_id, tier_key, days)
title =
plan["title"] if plan else
tier_key
text = (

🎉 <b>‫اشتراک شما‬
‫<!فعال شد‬/b>\n\n"
f"🏷 ‫نوع‬:
{title}\n"
f"📅 ‫از تاریخ‬:
f"

{start.strftime('%Y-%m%d')}\n"

📅 ‫تا تاریخ‬:

f"

{end.strftime('%Y-%m%d')}\n\n"

🎁 ‫مزایا‬:

f"

{plan['benefits'] if plan
else ''}\n\n"
‫!ببرید‬

🐉"

"‫ لذت‬،‫مبارک باشه‬
)
await

update.message.reply_text(te
xt,
parse_mode=ParseMode.HTML)
elif
payload.startswith("liber:")
:
pack_key =
payload.split(":", 1)[1]
amount =
grant_liber_pack(user_id,
pack_key)
await

update.message.reply_text(

✅ ‫!خرید موفق‬
{amount} LIBER ‫به کیف پول شما‬
‫ لذت ببرید‬.‫"🪙 !اضافه شد‬
f"

)

else:
logger.warning(f"Unknown
payment payload: {payload}")

#
============================
============================
====
#

main

#
============================
============================
====

def main():
init_db()
app =
Application.builder().token(
BOT_TOKEN).build()

app.add_handler(CommandHandl
er("start", start))
app.add_handler(CommandHandl
er("admin", admin_command))
app.add_handler(CommandHandl
er("ban", ban_command))
app.add_handler(CommandHandl
er("unban", unban_command))
app.add_handler(CommandHandl
er("broadcast",
broadcast_command))

app.add_handler(CommandHandl
er("setbio",
setbio_command))
app.add_handler(CommandHandl
er("reply", reply_command))
app.add_handler(CommandHandl
er("finduser",
finduser_command))
app.add_handler(CommandHandl
er("grantliber",
grantliber_command))
app.add_handler(CommandHandl
er("grantvip",
grantvip_command))
app.add_handler(CommandHandl
er("createcode",

createcode_command))
app.add_handler(CommandHandl
er("withdrawals",
withdrawals_command))
app.add_handler(CommandHandl
er("approvewithdraw",
approvewithdraw_command))
app.add_handler(CommandHandl
er("rejectwithdraw",
rejectwithdraw_command))
app.add_handler(CallbackQuer
yHandler(button_handler))
app.add_handler(PreCheckoutQ
ueryHandler(precheckout_call
back))
app.add_handler(MessageHandl

er(filters.SUCCESSFUL_PAYMEN
T,
successful_payment_callback)
)
app.add_handler(MessageHandl
er(filters.TEXT &
~filters.COMMAND,
text_message_filter))

‫ساعت‬

# ۱ ‫نوسان خودکار قیمت بازار هر‬

app.job_queue.run_repeating(
hourly_market_job,
interval=MARKET_UPDATE_INTER
VAL_SECONDS,
first=MARKET_UPDATE_INTERVAL
_SECONDS,
)

logger.info("LIBER bot
(all-in-one) started.")
app.run_polling()

if __name__ == "__main__":
main()


