# -*- coding: utf-8 -*-
"""
handlers_extra.py — قابلیت‌های اضافه‌ی ربات LIBER (فایل جدا)
================================================================
این فایل کاملاً جداست و باید کنار main.py قرار بگیرد. main.py در
لحظه‌ی نیاز (وقتی کاربر روی یکی از دکمه‌های این بخش‌ها بزند) این فایل
را import می‌کند — نیازی به تغییر main.py برای فعال‌سازی نیست.

شامل ۱۰ قابلیت:
    🌍 کشور و ساختمان        🤝 اتحاد/کلن + جنگ کلن
    💼 شغل                   🏷 مزایده
    🔬 تحقیقات شخصی          🛡 دفاع شخصی
    🌌 اکتشاف                🤖 مشاور هوشمند
    📰 اخبار جهان            🎟 پیش‌بینی قیمت (شرط روی صعود/نزول)
"""
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from main import (
    MARKET_BASE_PRICE,
    back_keyboard,
    get_active_subscription_tier,
    get_market_price,
    get_stats,
    get_user,
    has_done_daily_mission,
    log_transaction,
    update_balance,
)
from main import get_conn
import time


# ============================================================
#  تنظیمات محلی این ماژول (خودکفا، بدون وابستگی به config.py اصلی)
# ============================================================
# ============================================================
#   کشور و ساختمان‌ها
# ============================================================
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

# ============================================================
#   شغل
# ============================================================
JOBS = {
    "miner": {"name": "⛏ معدنچی", "income": 15, "cost": 0},
    "trader": {"name": "💼 تاجر", "income": 25, "cost": 300},
    "programmer": {"name": "💻 برنامه‌نویس", "income": 40, "cost": 800},
    "scientist": {"name": "🔬 دانشمند", "income": 60, "cost": 1500},
    "investor": {"name": "📈 سرمایه‌گذار", "income": 90, "cost": 3000},
    "athlete": {"name": "⚽ فوتبالیست", "income": 130, "cost": 6000},
}
WORK_COOLDOWN_SECONDS = 20 * 3600

# ============================================================
#   جنگ کلن
# ============================================================
CLAN_WAR_MIN_REWARD = 100
CLAN_WAR_MAX_REWARD = 400

# ============================================================
#   مزایده
# ============================================================
AUCTION_INCREMENT = 10
AUCTION_START_PRICE = 50
AUCTION_DURATION_SECONDS = 12 * 3600
AUCTION_ITEMS = [
    "🎁 جعبه طلایی", "🖼 قاب کهکشانی", "🏷 لقب افسانه‌ای",
    "💎 آواتار الماسی", "🎖 مدال ویژه فصل",
]

# ============================================================
#   تحقیقات
# ============================================================
RESEARCH_TREE = [
    {"name": "کشاورزی مدرن", "cost": 300, "effect": "تولید +۱۰٪"},
    {"name": "معدن‌کاری پیشرفته", "cost": 700, "effect": "تولید +۲۰٪"},
    {"name": "انرژی خورشیدی", "cost": 1500, "effect": "تولید +۳۵٪"},
    {"name": "هوش مصنوعی صنعتی", "cost": 3000, "effect": "تولید +۵۰٪"},
    {"name": "فناوری کوانتومی", "cost": 6000, "effect": "تولید +۷۵٪"},
]

# ============================================================
#   دفاع شخصی
# ============================================================
DEFENSE_BASE_COST = 250
DEFENSE_GROWTH = 1.6

# ============================================================
#   اکتشاف
# ============================================================
EXPLORATION_MIN_LEVEL = 3
EXPLORATION_COST_LIBER = 25
EXPLORATION_REWARD_RANGE = (20, 150)
EXPLORATION_RARE_CHANCE = 0.15

# ============================================================
#   پیش‌بینی قیمت
# ============================================================
PREDICTION_BET = 30
PREDICTION_MULTIPLIER = 1.8


# ============================================================
#  توابع دیتابیس محلی این ماژول (روی جداول خودشان کار می‌کنند)
# ============================================================
# ---------------------------------------------------------------
#  کشور و ساختمان‌ها
# ---------------------------------------------------------------
def get_country_by_owner(owner_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM countries WHERE owner_id = ?", (owner_id,)).fetchone()


def found_country(owner_id, name):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO countries (owner_id, name, created_at) VALUES (?, ?, ?)",
            (owner_id, name, int(time.time())),
        )
        country_id = cur.lastrowid
        conn.execute("UPDATE users SET country_id = ? WHERE user_id = ?", (country_id, owner_id))
        return country_id


def list_buildings(country_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM buildings WHERE country_id = ?", (country_id,)).fetchall()


def build_or_upgrade(country_id, building_type):
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT * FROM buildings WHERE country_id = ? AND type = ?", (country_id, building_type)
        ).fetchone()
        if existing:
            conn.execute("UPDATE buildings SET level = level + 1 WHERE building_id = ?", (existing["building_id"],))
            return existing["level"] + 1
        conn.execute(
            "INSERT INTO buildings (country_id, type, level) VALUES (?, ?, 1)", (country_id, building_type)
        )
        return 1


# ---------------------------------------------------------------
#  اتحاد / کلن
# ---------------------------------------------------------------
def get_alliance_membership(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)).fetchone()


def get_alliance(alliance_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE alliance_id = ?", (alliance_id,)).fetchone()


def get_alliance_by_name(name):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE name = ?", (name,)).fetchone()


def create_alliance(name, leader_id):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO alliances (name, leader_id, created_at) VALUES (?, ?, ?)",
            (name, leader_id, int(time.time())),
        )
        alliance_id = cur.lastrowid
        conn.execute(
            "INSERT INTO alliance_members (user_id, alliance_id, joined_at) VALUES (?, ?, ?)",
            (leader_id, alliance_id, int(time.time())),
        )
        return alliance_id


def join_alliance(user_id, alliance_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alliance_members (user_id, alliance_id, joined_at) VALUES (?, ?, ?)",
            (user_id, alliance_id, int(time.time())),
        )


def alliance_members(alliance_id):
    with get_conn() as conn:
        return conn.execute(
            """SELECT u.first_name FROM alliance_members am
               JOIN users u ON u.user_id = am.user_id
               WHERE am.alliance_id = ?""",
            (alliance_id,),
        ).fetchall()


def add_alliance_treasury(alliance_id, amount):
    with get_conn() as conn:
        conn.execute("UPDATE alliances SET treasury = treasury + ? WHERE alliance_id = ?", (amount, alliance_id))


# ---------------------------------------------------------------
#  شغل
# ---------------------------------------------------------------
def set_job(user_id, job_key, job_title):
    with get_conn() as conn:
        conn.execute("UPDATE users SET job_key = ?, job_title = ? WHERE user_id = ?", (job_key, job_title, user_id))


def do_work(user_id, income):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET liber = liber + ?, xp = xp + 8, last_work = ? WHERE user_id = ?",
            (income, now, user_id),
        )


# ---------------------------------------------------------------
#  مزایده
# ---------------------------------------------------------------
def get_active_auction():
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM auctions WHERE active = 1 ORDER BY auction_id DESC LIMIT 1"
        ).fetchone()


def create_auction(item_name, start_price, duration_seconds):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO auctions (item_name, current_price, current_winner, active, created_at, ends_at)
               VALUES (?, ?, NULL, 1, ?, ?)""",
            (item_name, start_price, now, now + duration_seconds),
        )
    return get_active_auction()


def close_auction(auction_id):
    with get_conn() as conn:
        conn.execute("UPDATE auctions SET active = 0 WHERE auction_id = ?", (auction_id,))


def place_bid(auction_id, user_id, new_price, previous_winner):
    with get_conn() as conn:
        if previous_winner and previous_winner != user_id:
            conn.execute("UPDATE users SET liber = liber + ? WHERE user_id = ?",
                         (get_auction_price(conn, auction_id), previous_winner))
        conn.execute("UPDATE users SET liber = liber - ? WHERE user_id = ?", (new_price, user_id))
        conn.execute(
            "UPDATE auctions SET current_price = ?, current_winner = ? WHERE auction_id = ?",
            (new_price, user_id, auction_id),
        )


def get_auction_price(conn, auction_id):
    row = conn.execute("SELECT current_price FROM auctions WHERE auction_id = ?", (auction_id,)).fetchone()
    return row["current_price"] if row else 0


# ---------------------------------------------------------------
#  تحقیقات و دفاع شخصی
# ---------------------------------------------------------------
def upgrade_research(user_id, cost):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, research_level = research_level + 1, xp = xp + 20 WHERE user_id = ?",
            (cost, user_id),
        )


def upgrade_personal_defense(user_id, cost):
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET liber = liber - ?, personal_defense_level = personal_defense_level + 1 WHERE user_id = ?",
            (cost, user_id),
        )


# ---------------------------------------------------------------
#  اکتشاف
# ---------------------------------------------------------------
def do_exploration(user_id, cost, reward):
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET liber = liber - ? + ?, xp = xp + 15, last_explore = ? WHERE user_id = ?",
            (cost, reward, now, user_id),
        )


# ---------------------------------------------------------------
#  پیش‌بینی قیمت
# ---------------------------------------------------------------
def place_prediction(user_id, direction, start_price, bet_amount):
    with get_conn() as conn:
        conn.execute("UPDATE users SET coin = coin - ? WHERE user_id = ?", (bet_amount, user_id))
        conn.execute(
            """INSERT INTO predictions (user_id, direction, start_price, bet_amount, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, direction, start_price, bet_amount, int(time.time())),
        )


def resolve_predictions(new_price, multiplier):
    with get_conn() as conn:
        open_bets = conn.execute("SELECT * FROM predictions WHERE status = 'open'").fetchall()
        results = []
        for bet in open_bets:
            won = (bet["direction"] == "up" and new_price > bet["start_price"]) or (
                bet["direction"] == "down" and new_price < bet["start_price"]
            )
            if won:
                payout = round(bet["bet_amount"] * multiplier, 2)
                conn.execute("UPDATE users SET coin = coin + ? WHERE user_id = ?", (payout, bet["user_id"]))
                results.append((bet["user_id"], True, payout))
            else:
                results.append((bet["user_id"], False, 0))
            conn.execute("UPDATE predictions SET status = 'closed' WHERE pred_id = ?", (bet["pred_id"],))
        return results


# ---------------------------------------------------------------
#  آمار جهانی (برای اخبار جهان / مشاور هوشمند)
# ---------------------------------------------------------------
def get_richest_user():
    with get_conn() as conn:
        return conn.execute("SELECT first_name, liber FROM users ORDER BY liber DESC LIMIT 1").fetchone()


def count_countries():
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) c FROM countries").fetchone()["c"]


# ============================================================
#  دکمه‌های محلی این ماژول
# ============================================================
# ---------------------------------------------------------------
#  کشور و ساختمان
# ---------------------------------------------------------------
def country_no_country_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌍 ساخت کشور جدید", callback_data="country_found")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


def country_view_keyboard():
    rows = [[InlineKeyboardButton(f"🏗 {name} ({BUILDING_COSTS[key]} LIBER)", callback_data=f"country_build:{key}")]
            for key, name in BUILDING_NAMES.items()]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------
#  اتحاد / کلن
# ---------------------------------------------------------------
def alliance_no_alliance_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🤝 ساخت اتحاد جدید", callback_data="alliance_create")],
        [InlineKeyboardButton("🔍 پیوستن به اتحاد (با نام)", callback_data="alliance_join")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


def alliance_view_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚔️ جنگ کلن", callback_data="menu_clanwar")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


# ---------------------------------------------------------------
#  شغل
# ---------------------------------------------------------------
def jobs_keyboard(current_job_key):
    rows = []
    for key, job in JOBS.items():
        marker = "✅ " if key == current_job_key else ""
        cost_text = f" ({job['cost']} LIBER)" if job["cost"] > 0 else " (رایگان)"
        rows.append([InlineKeyboardButton(f"{marker}{job['name']}{cost_text}", callback_data=f"job_set:{key}")])
    rows.append([InlineKeyboardButton("💼 کار کن (درآمد روزانه)", callback_data="job_work")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------
#  مزایده
# ---------------------------------------------------------------
def auction_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پیشنهاد بده", callback_data="auction_bid")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


# ---------------------------------------------------------------
#  تحقیقات / دفاع / اکتشاف
# ---------------------------------------------------------------
def research_keyboard(can_upgrade):
    rows = []
    if can_upgrade:
        rows.append([InlineKeyboardButton("🔬 ارتقا بده", callback_data="research_upgrade")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def defense_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛡 ارتقا بده", callback_data="defense_upgrade")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


def explore_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌌 برو به اکتشاف", callback_data="explore_go")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


# ---------------------------------------------------------------
#  پیش‌بینی قیمت
# ---------------------------------------------------------------
def predict_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 صعودی", callback_data="predict_up"),
         InlineKeyboardButton("📉 نزولی", callback_data="predict_down")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])




logger = logging.getLogger("LIBER.extra")


# ---------------------------------------------------------------
#  کشور و ساختمان
# ---------------------------------------------------------------
async def country_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    country = get_country_by_owner(user_id)

    if not country:
        await q.edit_message_text(
            "🌍 شما هنوز کشوری ندارید.\nبا ساخت کشور، جمعیت اولیه و امکان ساختن ساختمان می‌گیرید:",
            reply_markup=country_no_country_keyboard(),
        )
        return

    buildings = list_buildings(country["country_id"])
    buildings_text = "\n".join(
        f"  {BUILDING_NAMES.get(b['type'], b['type'])}: سطح {b['level']}" for b in buildings
    ) or "  هنوز ساختمانی ساخته نشده."

    text = (
        f"🌍 {country['name']} {country['flag']}\n\n"
        f"👥 جمعیت: {country['population']}\n"
        f"😊 رضایت: {country['satisfaction']}٪\n\n"
        f"🏗 ساختمان‌ها:\n{buildings_text}\n\n"
        "برای ساخت/ارتقای ساختمان روی دکمه بزن:"
    )
    await q.edit_message_text(text, reply_markup=country_view_keyboard())


async def country_found_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "country_name_input"
    await q.edit_message_text("🌍 اسم کشورتون رو بفرستید (حداکثر ۳۰ حرف):")


async def _do_found_country(update, context, raw_text):
    user_id = update.effective_user.id
    if get_country_by_owner(user_id):
        await update.message.reply_text("شما قبلاً یک کشور ساخته‌اید.", reply_markup=back_keyboard())
        return
    name = raw_text.strip()[:30]
    if not name:
        await update.message.reply_text("❌ اسم نامعتبر است.")
        return
    found_country(user_id, name)
    log_transaction(user_id, "FOUND_COUNTRY", name)
    await update.message.reply_text(f"🎉 کشور «{name}» با موفقیت تاسیس شد!", reply_markup=back_keyboard())


async def country_build_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    building_type = q.data.split(":", 1)[1]
    country = get_country_by_owner(user_id)
    if not country:
        await q.answer("ابتدا یک کشور بساز.", show_alert=True)
        return

    cost = BUILDING_COSTS.get(building_type)
    if cost is None:
        await q.answer("نوع ساختمان نامعتبر است.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < cost:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {cost}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-cost, xp=15)
    new_level = build_or_upgrade(country["country_id"], building_type)
    log_transaction(user_id, "BUILD", f"{building_type} lvl={new_level}")

    name = BUILDING_NAMES.get(building_type, building_type)
    await q.edit_message_text(
        f"🏗 {name} به سطح {new_level} ساخته/ارتقا یافت! (-{cost} LIBER)",
        reply_markup=country_view_keyboard(),
    )


# ---------------------------------------------------------------
#  اتحاد / کلن
# ---------------------------------------------------------------
async def alliance_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    membership = get_alliance_membership(user_id)

    if not membership:
        await q.edit_message_text(
            "🤝 شما عضو هیچ اتحادی نیستید.",
            reply_markup=alliance_no_alliance_keyboard(),
        )
        return

    alliance = get_alliance(membership["alliance_id"])
    members = alliance_members(membership["alliance_id"])
    members_text = "\n".join(f"  • {m['first_name']}" for m in members)

    text = (
        f"🤝 اتحاد: {alliance['name']}\n"
        f"💰 خزانه: {round(alliance['treasury'], 2)} LIBER\n"
        f"👥 اعضا ({len(members)}):\n{members_text}"
    )
    await q.edit_message_text(text, reply_markup=alliance_view_keyboard())


async def alliance_create_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if get_alliance_membership(q.from_user.id):
        await q.edit_message_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return
    context.user_data["awaiting"] = "alliance_create_name"
    await q.edit_message_text("🤝 اسم اتحاد جدید رو بفرستید (حداکثر ۳۰ حرف):")


async def _do_create_alliance(update, context, raw_text):
    user_id = update.effective_user.id
    if get_alliance_membership(user_id):
        await update.message.reply_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return
    name = raw_text.strip()[:30]
    if not name:
        await update.message.reply_text("❌ اسم نامعتبر است.")
        return
    if get_alliance_by_name(name):
        await update.message.reply_text("❌ این اسم قبلاً استفاده شده.")
        return
    create_alliance(name, user_id)
    log_transaction(user_id, "CREATE_ALLIANCE", name)
    await update.message.reply_text(f"🤝 اتحاد «{name}» ساخته شد!", reply_markup=back_keyboard())


async def alliance_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if get_alliance_membership(q.from_user.id):
        await q.edit_message_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return
    context.user_data["awaiting"] = "alliance_join_name"
    await q.edit_message_text("🔍 اسم اتحادی که می‌خواهید بهش بپیوندید رو بفرستید:")


async def _do_join_alliance(update, context, raw_text):
    user_id = update.effective_user.id
    if get_alliance_membership(user_id):
        await update.message.reply_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return
    name = raw_text.strip()
    alliance = get_alliance_by_name(name)
    if not alliance:
        await update.message.reply_text("❌ اتحادی با این اسم پیدا نشد.")
        return
    join_alliance(user_id, alliance["alliance_id"])
    log_transaction(user_id, "JOIN_ALLIANCE", name)
    await update.message.reply_text(f"🤝 با موفقیت به اتحاد «{name}» پیوستی!", reply_markup=back_keyboard())


async def clan_war_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    membership = get_alliance_membership(user_id)
    if not membership:
        await q.edit_message_text("ابتدا باید عضو یک اتحاد باشی.", reply_markup=back_keyboard())
        return

    alliance = get_alliance(membership["alliance_id"])
    our_power = alliance["treasury"] + random.randint(0, 200)
    rival_power = random.randint(100, 1500)
    won = our_power >= rival_power

    if won:
        reward = random.randint(CLAN_WAR_MIN_REWARD, CLAN_WAR_MAX_REWARD)
        add_alliance_treasury(alliance["alliance_id"], reward)
        text = (
            f"⚔️ جنگ کلن!\nقدرت شما: {round(our_power)} — قدرت حریف: {rival_power}\n"
            f"🏆 بردید! +{reward} به خزانه‌ی کلن اضافه شد."
        )
    else:
        text = f"⚔️ جنگ کلن!\nقدرت شما: {round(our_power)} — قدرت حریف: {rival_power}\n😔 این بار باختید."

    log_transaction(user_id, "CLAN_WAR", "win" if won else "loss")
    await q.edit_message_text(text, reply_markup=back_keyboard())


# ---------------------------------------------------------------
#  شغل
# ---------------------------------------------------------------
async def job_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = get_user(q.from_user.id)
    text = f"💼 شغل فعلی: {user['job_title']}\n\nروی شغل جدید بزن تا استخدام بشی، یا کار کن تا درآمد بگیری:"
    await q.edit_message_text(text, reply_markup=jobs_keyboard(user["job_key"]))


async def job_set_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    job_key = q.data.split(":", 1)[1]
    job = JOBS.get(job_key)
    if not job:
        await q.answer("شغل نامعتبر است.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < job["cost"]:
        await q.answer(f"❌ برای استخدام به {job['cost']} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    if job["cost"] > 0:
        update_balance(user_id, liber=-job["cost"])
    set_job(user_id, job_key, job["name"])
    log_transaction(user_id, "SET_JOB", job_key)
    await q.edit_message_text(f"✅ شغل شما به {job['name']} تغییر کرد!", reply_markup=jobs_keyboard(job_key))


async def job_work_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    user = get_user(user_id)

    if not user["job_key"]:
        await q.answer("هنوز شغلی انتخاب نکردی!", show_alert=True)
        return

    import time as _time
    now = int(_time.time())
    if now - user["last_work"] < WORK_COOLDOWN_SECONDS:
        remaining_hrs = (WORK_COOLDOWN_SECONDS - (now - user["last_work"])) // 3600
        await q.answer(f"⏳ {remaining_hrs} ساعت دیگر دوباره کار کن.", show_alert=True)
        return

    await q.answer()
    job = JOBS[user["job_key"]]
    income = max(1, job["income"] + random.randint(-3, 10))
    do_work(user_id, income)
    log_transaction(user_id, "WORK", f"income={income}")
    await q.edit_message_text(
        f"💼 یک روز کاری به‌عنوان {user['job_title']} تموم شد!\n+{income} LIBER, +8 XP",
        reply_markup=jobs_keyboard(user["job_key"]),
    )


# ---------------------------------------------------------------
#  مزایده
# ---------------------------------------------------------------
def _ensure_active_auction():
    import time as _time
    auction = get_active_auction()
    now = int(_time.time())
    if not auction or auction["ends_at"] <= now:
        if auction and auction["ends_at"] <= now:
            close_auction(auction["auction_id"])
            if auction["current_winner"]:
                pass  # برنده‌ی نهایی، آیتم رو می‌گیرد (فقط جنبه‌ی نمایشی/فان دارد)
        item = random.choice(AUCTION_ITEMS)
        auction = create_auction(item, AUCTION_START_PRICE, AUCTION_DURATION_SECONDS)
    return auction


async def auction_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    auction = _ensure_active_auction()

    winner_text = "هنوز کسی شرکت نکرده"
    if auction["current_winner"]:
        w = get_user(auction["current_winner"])
        if w:
            winner_text = w["first_name"]

    import time as _time
    hrs_left = max(0, (auction["ends_at"] - int(_time.time())) // 3600)
    text = (
        f"🏷 مزایده LIBER\n\n"
        f"🎁 آیتم: {auction['item_name']}\n"
        f"💰 قیمت فعلی: {auction['current_price']} LIBER\n"
        f"🏆 برنده‌ی فعلی: {winner_text}\n"
        f"⏳ زمان باقی‌مانده: {hrs_left} ساعت"
    )
    await q.edit_message_text(text, reply_markup=auction_keyboard())


async def auction_bid_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    auction = _ensure_active_auction()
    next_price = auction["current_price"] + AUCTION_INCREMENT

    user = get_user(user_id)
    if user["liber"] < next_price:
        await q.answer(f"❌ برای پیشنهاد بعدی به {next_price} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    place_bid(auction["auction_id"], user_id, next_price, auction["current_winner"])
    log_transaction(user_id, "AUCTION_BID", f"price={next_price}")

    await q.edit_message_text(
        f"✅ پیشنهاد ثبت شد! الان برنده‌ی فعلی «{auction['item_name']}» هستی.\nقیمت فعلی: {next_price} LIBER",
        reply_markup=auction_keyboard(),
    )


# ---------------------------------------------------------------
#  تحقیقات شخصی
# ---------------------------------------------------------------
async def research_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = get_user(q.from_user.id)
    level = user["research_level"]

    if level >= len(RESEARCH_TREE):
        await q.edit_message_text("🔬 تمام سطوح تحقیقاتی رو کامل کردی! 🎉", reply_markup=research_keyboard(False))
        return

    info = RESEARCH_TREE[level]
    text = (
        f"🔬 تحقیقات\n\nسطح فعلی: {level}\nتحقیق بعدی: {info['name']}\n"
        f"هزینه: {info['cost']} LIBER\nاثر: {info['effect']}"
    )
    await q.edit_message_text(text, reply_markup=research_keyboard(True))


async def research_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    user = get_user(user_id)
    level = user["research_level"]
    if level >= len(RESEARCH_TREE):
        await q.answer("قبلاً تکمیل شده.", show_alert=True)
        return

    info = RESEARCH_TREE[level]
    if user["liber"] < info["cost"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {info['cost']}", show_alert=True)
        return

    await q.answer()
    upgrade_research(user_id, info["cost"])
    log_transaction(user_id, "RESEARCH", info["name"])
    await q.edit_message_text(
        f"🔬 تحقیق «{info['name']}» تکمیل شد! ({info['effect']})", reply_markup=back_keyboard()
    )


# ---------------------------------------------------------------
#  دفاع شخصی
# ---------------------------------------------------------------
async def defense_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user = get_user(q.from_user.id)
    cost = round(DEFENSE_BASE_COST * (DEFENSE_GROWTH ** user["personal_defense_level"]), 2)
    text = f"🛡 دفاع شخصی\n\nسطح فعلی: {user['personal_defense_level']}\nهزینه‌ی ارتقای بعدی: {cost} LIBER"
    await q.edit_message_text(text, reply_markup=defense_keyboard())


async def defense_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    user = get_user(user_id)
    cost = round(DEFENSE_BASE_COST * (DEFENSE_GROWTH ** user["personal_defense_level"]), 2)
    if user["liber"] < cost:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {cost}", show_alert=True)
        return

    await q.answer()
    upgrade_personal_defense(user_id, cost)
    new_level = user["personal_defense_level"] + 1
    log_transaction(user_id, "DEFENSE_UPGRADE", str(new_level))
    await q.edit_message_text(
        f"🛡 دفاعت به سطح {new_level} ارتقا یافت! (-{cost} LIBER)", reply_markup=back_keyboard()
    )


# ---------------------------------------------------------------
#  اکتشاف
# ---------------------------------------------------------------
async def explore_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    text = (
        f"🌌 اکتشاف\n\n"
        f"حداقل سطح لازم: {EXPLORATION_MIN_LEVEL}\n"
        f"هزینه: {EXPLORATION_COST_LIBER} LIBER\n"
        f"جایزه: بین {EXPLORATION_REWARD_RANGE[0]} تا {EXPLORATION_REWARD_RANGE[1]} LIBER\n"
        f"شانس {int(EXPLORATION_RARE_CHANCE*100)}٪ پیدا کردن یک آیتم کمیاب!"
    )
    await q.edit_message_text(text, reply_markup=explore_keyboard())


async def explore_go_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    user = get_user(user_id)

    if user["level"] < EXPLORATION_MIN_LEVEL:
        await q.answer(f"🌌 اکتشاف فقط برای سطح {EXPLORATION_MIN_LEVEL} به بالا باز است.", show_alert=True)
        return
    if user["liber"] < EXPLORATION_COST_LIBER:
        await q.answer(f"❌ برای اکتشاف به {EXPLORATION_COST_LIBER} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    low, high = EXPLORATION_REWARD_RANGE
    reward = random.randint(low, high)
    do_exploration(user_id, EXPLORATION_COST_LIBER, reward)
    log_transaction(user_id, "EXPLORE", f"reward={reward}")

    text = f"🌌 اکتشاف موفق!\n+{reward} LIBER (-{EXPLORATION_COST_LIBER} هزینه)"
    if random.random() < EXPLORATION_RARE_CHANCE:
        text += "\n💎 یک آیتم کمیاب هم پیدا کردی!"
    await q.edit_message_text(text, reply_markup=explore_keyboard())


# ---------------------------------------------------------------
#  مشاور هوشمند
# ---------------------------------------------------------------
async def advisor_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    user = get_user(user_id)
    price = get_market_price()
    tips = []

    if price < MARKET_BASE_PRICE * 0.9:
        tips.append("📉 قیمت LIBER پایین‌تر از حد معموله — الان زمان خوبی برای خریدنه.")
    elif price > MARKET_BASE_PRICE * 1.15:
        tips.append("📈 قیمت LIBER بالاست — شاید بخوای بفروشی و سود کنی.")

    if not get_country_by_owner(user_id):
        tips.append("🌍 هنوز کشوری نساختی! رایگانه و بهت جمعیت اولیه می‌ده.")

    if user["research_level"] < len(RESEARCH_TREE):
        info = RESEARCH_TREE[user["research_level"]]
        if user["liber"] >= info["cost"]:
            tips.append(f"🔬 می‌تونی همین الان «{info['name']}» رو با {info['cost']} LIBER تحقیق کنی.")

    if not has_done_daily_mission(user_id):
        tips.append("🎯 ماموریت روزانه‌ات رو هنوز نگرفتی! بدون اون، صندوق رایگان و رقابت هم قفله.")

    if not get_active_subscription_tier(user_id):
        tips.append("⭐ با خرید اشتراک، کارمزد بازار و برداشت کمتر می‌شه و پاداش روزانه بیشتر.")

    if not tips:
        tips.append("👍 وضعیتت خیلی خوبه! همینطور با ماموریت و بازار پیش برو.")

    text = "🤖 مشاور هوشمند LIBER\n\n" + "\n\n".join(f"• {t}" for t in tips)
    await q.edit_message_text(text, reply_markup=back_keyboard())


# ---------------------------------------------------------------
#  اخبار جهان
# ---------------------------------------------------------------
async def news_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    price = get_market_price()
    stats = get_stats()
    richest = get_richest_user()
    total_countries = count_countries()

    lines = [
        f"💹 قیمت لحظه‌ای LIBER: {price}",
        f"👥 کل بازیکنان: {stats['total_users']}",
        f"🌍 کشورهای ساخته‌شده: {total_countries}",
    ]
    if richest:
        lines.append(f"👑 ثروتمندترین بازیکن: {richest['first_name']} با {round(richest['liber'])} LIBER")

    await q.edit_message_text("📰 اخبار جهان LIBER\n\n" + "\n".join(lines), reply_markup=back_keyboard())


# ---------------------------------------------------------------
#  پیش‌بینی قیمت
# ---------------------------------------------------------------
async def predict_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    price = get_market_price()
    text = (
        f"🎟 پیش‌بینی قیمت LIBER\n\n"
        f"قیمت فعلی: {price}\n"
        f"مبلغ شرط: {PREDICTION_BET} سکه\n"
        f"ضریب برد: {PREDICTION_MULTIPLIER}x\n\n"
        "پیش‌بینی می‌کنی قیمت تا آپدیت بعدی (۱ ساعت دیگر) بره بالا یا پایین؟"
    )
    await q.edit_message_text(text, reply_markup=predict_keyboard())


async def _place_prediction(update, context, direction):
    q = update.callback_query
    user_id = q.from_user.id
    user = get_user(user_id)
    if user["coin"] < PREDICTION_BET:
        await q.answer("❌ سکه کافی نداری.", show_alert=True)
        return
    await q.answer()
    price = get_market_price()
    place_prediction(user_id, direction, price, PREDICTION_BET)
    log_transaction(user_id, "PREDICTION", f"{direction}@{price}")
    dir_text = "صعودی 📈" if direction == "up" else "نزولی 📉"
    await q.edit_message_text(
        f"🎟 شرط ثبت شد: پیش‌بینی {dir_text} روی قیمت {price}\nنتیجه بعد از آپدیت ساعتی بازار اعلام می‌شود.",
        reply_markup=back_keyboard(),
    )


async def predict_up_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _place_prediction(update, context, "up")


async def predict_down_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _place_prediction(update, context, "down")


async def resolve_predictions_job(context: ContextTypes.DEFAULT_TYPE):
    """هر بار که بازار نوسان می‌کند صدا زده می‌شود (همراه با fluctuate_market)."""
    new_price = get_market_price()
    results = resolve_predictions(new_price, PREDICTION_MULTIPLIER)
    for user_id, won, payout in results:
        try:
            if won:
                await context.bot.send_message(user_id, f"🎉 پیش‌بینی‌ات درست بود! +{payout} سکه")
            else:
                await context.bot.send_message(user_id, "😔 پیش‌بینی‌ات این‌بار درست نبود.")
        except Exception:
            pass


# ---------------------------------------------------------------
#  دیسپچر اصلی
# ---------------------------------------------------------------
EXTRA_CALLBACKS = {
    "menu_country": country_menu_callback,
    "country_found": country_found_callback,
    "menu_alliance": alliance_menu_callback,
    "alliance_create": alliance_create_callback,
    "alliance_join": alliance_join_callback,
    "menu_clanwar": clan_war_callback,
    "menu_job": job_menu_callback,
    "job_work": job_work_callback,
    "menu_auction": auction_menu_callback,
    "auction_bid": auction_bid_callback,
    "menu_research": research_menu_callback,
    "research_upgrade": research_upgrade_callback,
    "menu_defense": defense_menu_callback,
    "defense_upgrade": defense_upgrade_callback,
    "menu_explore": explore_menu_callback,
    "explore_go": explore_go_callback,
    "menu_advisor": advisor_menu_callback,
    "menu_news": news_menu_callback,
    "menu_predict": predict_menu_callback,
    "predict_up": predict_up_callback,
    "predict_down": predict_down_callback,
}


async def extra_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر callback مربوط به یکی از قابلیت‌های اضافه باشد آن را پردازش می‌کند و True برمی‌گرداند."""
    data = update.callback_query.data
    if data in EXTRA_CALLBACKS:
        await EXTRA_CALLBACKS[data](update, context)
        return True
    if data.startswith("country_build:"):
        await country_build_callback(update, context)
        return True
    if data.startswith("job_set:"):
        await job_set_callback(update, context)
        return True
    return False


async def extra_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر پیام متنی مربوط به یک مرحله‌ی چندقسمتیِ قابلیت‌های اضافه باشد پردازش می‌کند."""
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "country_name_input":
        context.user_data["awaiting"] = None
        await _do_found_country(update, context, raw_text)
        return True
    if awaiting == "alliance_create_name":
        context.user_data["awaiting"] = None
        await _do_create_alliance(update, context, raw_text)
        return True
    if awaiting == "alliance_join_name":
        context.user_data["awaiting"] = None
        await _do_join_alliance(update, context, raw_text)
        return True
    return False
