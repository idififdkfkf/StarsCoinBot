# -*- coding: utf-8 -*-
"""
handlers_features2.py — پارت ۳ از بسته‌ی توسعه‌ی LIBER
================================================================
۶ قابلیت جدید، همه در یک فایل مستقل (کنار main.py قرار می‌گیرد):

    🏅 لیگ فصلی کشورها      رتبه‌بندی ماهانه‌ی کشورها بر اساس ساختمان+قدرت نظامی
    📊 نمودار قیمت بازار     اسپارک‌لاین متنی از ۲۴ ساعت اخیر قیمت LIBER
    🎓 منتورشیپ              کاربر باتجربه شاگرد می‌گیرد، هر دو ۷ روز بونوس می‌گیرن
    🗺 همسایگی کشورها        هر کشور ۲ همسایه دارد + تجارت مرزی روزانه
    🏆 پروفایل عمومی         مشاهده‌ی اطلاعات عمومی هر کاربر با آیدی
    🔔 یادآور هوشمند         پیام یادآوری خودکار برای کاربران غایب

⚙️ فرض‌های گرفته‌شده برای جاهای مبهم:
  • بونوس منتورشیپ: مدت ۷ روز، شاگرد +۱۰٪ به پاداش ماموریت روزانه‌ی خودش،
    منتور هر بار که شاگردش ماموریت روزانه می‌گیره ۵ LIBER پاداش می‌گیره.
  • همسایگی: در اولین بازدید از منوی همسایه‌ها، ۲ کشور تصادفیِ دیگر
    (غیر از خودش) به‌عنوان همسایه‌ی دائمی انتخاب می‌شن.
  • تجارت مرزی: فقط با همسایه‌ها، یک‌بار در روز، ۵۰-۱۵۰ سکه‌ی رایگان
    برای هر دو طرف (نمایشی از رونق تجارت مرزی).
  • یادآور هوشمند: هر روز چک می‌شه؛ اگه کاربر بیش از ۲۴ ساعته ماموریت
    روزانه نگرفته و امروز قبلاً یادآوری نگرفته، یک پیام می‌فرستیم.

نحوه‌ی اتصال:

    # main.py → callback_router → آخر زنجیره‌ی fallback:
        if not handled:
            import handlers_features2
            handled = await handlers_features2.features2_callback_router(update, context)

    # main.py → text_message_router → همون زنجیره:
        import handlers_features2
        if await handlers_features2.features2_text_router(update, context):
            return

    # main.py → main_menu_keyboard() چند ردیف اضافه کن:
        [InlineKeyboardButton("🏅 لیگ کشورها", callback_data="league_menu"),
         InlineKeyboardButton("🎓 منتورشیپ", callback_data="mentor_menu")],
        [InlineKeyboardButton("🗺 همسایگی کشورها", callback_data="neighbors_menu"),
         InlineKeyboardButton("🔎 پروفایل عمومی", callback_data="profile_lookup_start")],

    # main.py → market_keyboard() یک ردیف اضافه کن:
        [InlineKeyboardButton("📊 نمودار ۲۴ ساعت اخیر", callback_data="market_chart")],

    # main.py → داخل _fluctuate_market_job (بعد از fluctuate_market)، این خط رو اضافه کن:
        import handlers_features2
        handlers_features2.record_price_history(new_price)

    # main.py → داخل daily_mission_callback، درست قبل از ساخت متن نهایی
    # (بعد از update_balance اصلی)، این دو خط رو اضافه کن تا بونوس/اطلاع‌رسانی
    # منتورشیپ اعمال بشه:
        import handlers_features2
        await handlers_features2.apply_mentorship_daily_bonus(user_id, context.bot)

    # main.py → schedule_jobs() این دو خط رو اضافه کن:
        jq.run_repeating(_league_monthly_job, interval=86400, first=260)
        jq.run_repeating(_reminder_job, interval=86400, first=3600)

    # و این دو تابع کمکی رو هم به main.py اضافه کن:
        async def _league_monthly_job(context):
            import handlers_features2
            await handlers_features2.league_monthly_job(context)

        async def _reminder_job(context):
            import handlers_features2
            await handlers_features2.reminder_job(context)
"""
import time
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import (
    get_conn, get_user, update_balance, log_transaction, back_keyboard,
    get_market_price, RANKS, SUBSCRIPTION_TIERS, get_active_subscription_tier,
    has_done_daily_mission,
)

logger = logging.getLogger("LIBER.features2")

# ============================================================
#   تنظیمات
# ============================================================
LEAGUE_INTERVAL_SECONDS = 30 * 86400
LEAGUE_REWARDS = {1: 1200, 2: 800, 3: 500}

PRICE_HISTORY_KEEP_HOURS = 48
PRICE_CHART_POINTS = 24
SPARK_CHARS = "▁▂▃▄▅▆▇█"

MENTOR_MIN_LEVEL = 10
MENTORSHIP_DURATION_SECONDS = 7 * 86400
MENTEE_DAILY_BONUS_PERCENT = 10
MENTOR_REWARD_PER_MENTEE_DAILY = 5

NEIGHBOR_COUNT = 2
BORDER_TRADE_MIN = 50
BORDER_TRADE_MAX = 150

REMINDER_AFTER_SECONDS = 24 * 3600
REMINDER_MESSAGES = [
    "👋 دلمون برات تنگ شده! بیا سر بزن، ماموریت روزانه‌ات منتظرته 🎯",
    "💰 لیبرهای رایگان امروزت هنوز منتظرن! فراموش نکن سر بزنی.",
    "🎁 صندوق رایگان امروز رو هنوز باز نکردی — بیا از دستش نده!",
]


# ============================================================
#   جداول محلی
# ============================================================
_ready = False


def _ensure_tables():
    global _ready
    if _ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS league_season (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            season_number INTEGER NOT NULL DEFAULT 1,
            started_at INTEGER NOT NULL
        )
        """)
        row = conn.execute("SELECT 1 FROM league_season WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO league_season (id, season_number, started_at) VALUES (1, 1, ?)",
                (int(time.time()),),
            )

        conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            ts INTEGER NOT NULL,
            price REAL NOT NULL
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS mentorships (
            mentee_id INTEGER PRIMARY KEY,
            mentor_id INTEGER NOT NULL,
            started_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS country_neighbors (
            country_id INTEGER NOT NULL,
            neighbor_country_id INTEGER NOT NULL,
            PRIMARY KEY (country_id, neighbor_country_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS border_trade_claims (
            country_id INTEGER,
            claim_date TEXT,
            PRIMARY KEY (country_id, claim_date)
        )
        """)

        conn.execute("""
        CREATE TABLE IF NOT EXISTS reminder_log (
            user_id INTEGER,
            date_key TEXT,
            PRIMARY KEY (user_id, date_key)
        )
        """)
    _ready = True


def _today_key():
    return time.strftime("%Y-%m-%d", time.gmtime())


# ============================================================
#   ۱) لیگ فصلی کشورها
# ============================================================
def _country_score(country_row):
    """امتیاز کشور = مجموع سطح ساختمان‌ها × ۲۰ + قدرت نظامی صاحب کشور."""
    import handlers_military as hm
    with get_conn() as conn:
        buildings_sum = conn.execute(
            "SELECT COALESCE(SUM(level), 0) s FROM buildings WHERE country_id = ?", (country_row["country_id"],)
        ).fetchone()["s"]
    military = hm.get_military_power(country_row["owner_id"]) if country_row["owner_id"] else 0
    return round(buildings_sum * 20 + military, 1)


def _league_top(limit=10):
    with get_conn() as conn:
        countries = conn.execute("SELECT * FROM countries").fetchall()
    scored = [(c, _country_score(c)) for c in countries]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


async def league_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()

    with get_conn() as conn:
        season = conn.execute("SELECT * FROM league_season WHERE id = 1").fetchone()
    now = int(time.time())
    days_left = max(0, (LEAGUE_INTERVAL_SECONDS - (now - season["started_at"])) // 86400)

    top = _league_top(10)
    lines = [f"🏅 لیگ فصلی کشورها — فصل {season['season_number']}\n", f"⏳ {days_left} روز تا پایان فصل\n"]
    if not top:
        lines.append("هنوز هیچ کشوری ساخته نشده.")
    else:
        for i, (country, score) in enumerate(top, start=1):
            owner = get_user(country["owner_id"]) if country["owner_id"] else None
            owner_name = owner["first_name"] if owner else "؟"
            lines.append(f"{i}. {country['name']} ({owner_name}) — امتیاز {score}")
    r = LEAGUE_REWARDS
    lines.append(f"\n🎁 جوایز پایان فصل: ۱ام {r[1]} | ۲ام {r[2]} | ۳ام {r[3]} LIBER")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


async def league_monthly_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    with get_conn() as conn:
        season = conn.execute("SELECT * FROM league_season WHERE id = 1").fetchone()
    now = int(time.time())
    if now - season["started_at"] < LEAGUE_INTERVAL_SECONDS:
        return

    top3 = _league_top(3)
    for i, (country, score) in enumerate(top3, start=1):
        if score <= 0 or not country["owner_id"]:
            continue
        reward = LEAGUE_REWARDS.get(i, 0)
        if not reward:
            continue
        update_balance(country["owner_id"], liber=reward)
        log_transaction(country["owner_id"], "LEAGUE_REWARD", f"rank={i} country={country['name']}")
        try:
            await context.bot.send_message(
                country["owner_id"],
                f"🏅 تبریک! کشور «{country['name']}» تو لیگ فصلی رتبه‌ی {i} شد و {reward} LIBER جایزه گرفتی! 🎉",
            )
        except TelegramError:
            pass

    new_season = season["season_number"] + 1
    with get_conn() as conn:
        conn.execute(
            "UPDATE league_season SET season_number = ?, started_at = ? WHERE id = 1", (new_season, now)
        )
    logger.info(f"لیگ فصلی کشورها برگزار شد. فصل جدید: {new_season}")


# ============================================================
#   ۲) نمودار قیمت بازار (اسپارک‌لاین متنی)
# ============================================================
def record_price_history(price):
    """صدا زده می‌شود از main.py بعد از هر آپدیت ساعتی بازار."""
    _ensure_tables()
    now = int(time.time())
    with get_conn() as conn:
        conn.execute("INSERT INTO price_history (ts, price) VALUES (?, ?)", (now, price))
        cutoff = now - PRICE_HISTORY_KEEP_HOURS * 3600
        conn.execute("DELETE FROM price_history WHERE ts < ?", (cutoff,))


def _sparkline(values):
    if not values:
        return ""
    lo, hi = min(values), max(values)
    if hi == lo:
        return SPARK_CHARS[len(SPARK_CHARS) // 2] * len(values)
    span = hi - lo
    out = []
    for v in values:
        idx = int((v - lo) / span * (len(SPARK_CHARS) - 1))
        out.append(SPARK_CHARS[idx])
    return "".join(out)


async def market_chart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT price FROM price_history ORDER BY ts DESC LIMIT ?", (PRICE_CHART_POINTS,)
        ).fetchall()
    prices = [r["price"] for r in reversed(rows)]
    current = get_market_price()

    if len(prices) < 2:
        text = (
            "📊 نمودار قیمت LIBER\n\n"
            "هنوز داده‌ی کافی جمع نشده — بعد از چند تا آپدیت ساعتی بازار، نمودار اینجا نمایش داده می‌شه.\n"
            f"قیمت فعلی: {current}"
        )
    else:
        spark = _sparkline(prices)
        change_pct = round((prices[-1] - prices[0]) / prices[0] * 100, 2) if prices[0] else 0
        arrow = "📈" if change_pct >= 0 else "📉"
        text = (
            f"📊 نمودار قیمت LIBER (آخرین {len(prices)} آپدیت ساعتی)\n\n"
            f"{spark}\n\n"
            f"کمترین: {min(prices)}   بیشترین: {max(prices)}\n"
            f"{arrow} تغییر در این بازه: {change_pct:+.2f}٪\n"
            f"قیمت فعلی: {current}"
        )

    await q.edit_message_text(text, reply_markup=back_keyboard("menu_market"))


# ============================================================
#   ۳) منتورشیپ
# ============================================================
def _get_active_mentorship_as_mentee(user_id):
    _ensure_tables()
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM mentorships WHERE mentee_id = ?", (user_id,)).fetchone()
    if not row:
        return None
    if row["expires_at"] <= int(time.time()):
        return None
    return row


def _mentees_of(mentor_id):
    _ensure_tables()
    now = int(time.time())
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM mentorships WHERE mentor_id = ? AND expires_at > ?", (mentor_id, now)
        ).fetchall()


def _mentor_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ شاگرد بگیر (با آیدی)", callback_data="mentor_add_start")],
        [InlineKeyboardButton("📋 وضعیت من", callback_data="mentor_status")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


async def mentor_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    text = (
        "🎓 منتورشیپ\n\n"
        f"اگه سطح {MENTOR_MIN_LEVEL} یا بالاتر داری، می‌تونی یک شاگرد بگیری.\n"
        f"مدت منتورشیپ: ۷ روز\n"
        f"🎁 شاگرد: +{MENTEE_DAILY_BONUS_PERCENT}٪ به پاداش ماموریت روزانه‌ی خودش\n"
        f"🎁 منتور: هر بار شاگردش ماموریت روزانه بگیره، {MENTOR_REWARD_PER_MENTEE_DAILY} LIBER می‌گیره"
    )
    await q.edit_message_text(text, reply_markup=_mentor_menu_keyboard())


async def mentor_status_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    now = int(time.time())

    lines = ["📋 وضعیت منتورشیپ شما\n"]

    as_mentee = _get_active_mentorship_as_mentee(user_id)
    if as_mentee:
        mentor = get_user(as_mentee["mentor_id"])
        mentor_name = mentor["first_name"] if mentor else str(as_mentee["mentor_id"])
        days_left = max(0, (as_mentee["expires_at"] - now) // 86400)
        lines.append(f"👨‍🏫 منتور شما: {mentor_name} ({days_left} روز مونده)")
    else:
        lines.append("شما الان شاگرد کسی نیستید.")

    mentees = _mentees_of(user_id)
    if mentees:
        lines.append("\n👥 شاگردهای فعال شما:")
        for m in mentees:
            mentee = get_user(m["mentee_id"])
            name = mentee["first_name"] if mentee else str(m["mentee_id"])
            days_left = max(0, (m["expires_at"] - now) // 86400)
            lines.append(f"  • {name} ({days_left} روز مونده)")
    else:
        lines.append("\nشما الان شاگردی ندارید.")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard("mentor_menu"))


async def mentor_add_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = get_user(q.from_user.id)
    if user["level"] < MENTOR_MIN_LEVEL:
        await q.answer(f"❌ برای منتور شدن باید سطح {MENTOR_MIN_LEVEL} یا بالاتر داشته باشی.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting"] = "mentor_add_id_input"
    await q.edit_message_text("🎓 آیدی عددی کسی که می‌خوای شاگردت بشه رو بفرست:")


async def _do_mentor_add(update, context, raw_text):
    _ensure_tables()
    mentor_id = update.effective_user.id
    try:
        mentee_id = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return

    if mentee_id == mentor_id:
        await update.message.reply_text("❌ نمی‌تونی شاگرد خودت باشی.")
        return
    if not get_user(mentee_id):
        await update.message.reply_text("❌ کاربری با این آیدی پیدا نشد.")
        return
    if _get_active_mentorship_as_mentee(mentee_id):
        await update.message.reply_text("❌ این کاربر همین الان هم شاگرد یک نفر دیگه‌ست.")
        return

    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO mentorships (mentee_id, mentor_id, started_at, expires_at) VALUES (?, ?, ?, ?)",
            (mentee_id, mentor_id, now, now + MENTORSHIP_DURATION_SECONDS),
        )
    log_transaction(mentor_id, "MENTOR_ADD", str(mentee_id))
    await update.message.reply_text(
        f"🎉 از این به بعد منتور این کاربر هستی! (۷ روز فعاله)", reply_markup=back_keyboard("mentor_menu")
    )
    try:
        mentor = get_user(mentor_id)
        mentor_name = mentor["first_name"] if mentor else "یک کاربر"
        await context.bot.send_message(
            mentee_id,
            f"🎓 {mentor_name} منتور شما شد! تا ۷ روز آینده +{MENTEE_DAILY_BONUS_PERCENT}٪ "
            "به پاداش ماموریت روزانه‌ات اضافه می‌شه.",
        )
    except TelegramError:
        pass


def get_mentee_bonus_percent(user_id):
    """صدا زده می‌شود از main.py داخل daily_mission_callback."""
    row = _get_active_mentorship_as_mentee(user_id)
    return MENTEE_DAILY_BONUS_PERCENT if row else 0


async def apply_mentorship_daily_bonus(user_id, bot):
    """صدا زده می‌شود از main.py بعد از claim موفق ماموریت روزانه — فقط به منتور خبر و پاداش می‌ده
    (بونوس خود شاگرد از قبل با get_mentee_bonus_percent روی مبلغ اصلی اعمال شده)."""
    row = _get_active_mentorship_as_mentee(user_id)
    if not row:
        return
    update_balance(row["mentor_id"], liber=MENTOR_REWARD_PER_MENTEE_DAILY)
    log_transaction(row["mentor_id"], "MENTOR_DAILY_REWARD", str(user_id))
    try:
        mentee = get_user(user_id)
        mentee_name = mentee["first_name"] if mentee else "شاگردت"
        await bot.send_message(
            row["mentor_id"],
            f"🎓 {mentee_name} ماموریت روزانه‌اش رو گرفت! +{MENTOR_REWARD_PER_MENTEE_DAILY} LIBER بابت منتورشیپ گرفتی.",
        )
    except TelegramError:
        pass


# ============================================================
#   ۴) همسایگی کشورها + تجارت مرزی
# ============================================================
def _get_country_by_owner(owner_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM countries WHERE owner_id = ?", (owner_id,)).fetchone()


def _get_country(country_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM countries WHERE country_id = ?", (country_id,)).fetchone()


def _ensure_neighbors(country_id):
    _ensure_tables()
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT neighbor_country_id FROM country_neighbors WHERE country_id = ?", (country_id,)
        ).fetchall()
    if existing:
        return [r["neighbor_country_id"] for r in existing]

    with get_conn() as conn:
        candidates = conn.execute(
            "SELECT country_id FROM countries WHERE country_id != ? ORDER BY RANDOM() LIMIT ?",
            (country_id, NEIGHBOR_COUNT),
        ).fetchall()
    neighbor_ids = [r["country_id"] for r in candidates]

    with get_conn() as conn:
        for nid in neighbor_ids:
            conn.execute(
                "INSERT OR IGNORE INTO country_neighbors (country_id, neighbor_country_id) VALUES (?, ?)",
                (country_id, nid),
            )
            # همسایگی دوطرفه‌ست
            conn.execute(
                "INSERT OR IGNORE INTO country_neighbors (country_id, neighbor_country_id) VALUES (?, ?)",
                (nid, country_id),
            )
    return neighbor_ids


def _neighbors_keyboard(neighbor_countries, can_trade):
    rows = []
    if can_trade:
        rows.append([InlineKeyboardButton("🤝 تجارت مرزی امروز", callback_data="border_trade")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def neighbors_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    country = _get_country_by_owner(user_id)
    if not country:
        await q.edit_message_text("🗺 اول باید یک کشور بسازی (از منوی 🌍 کشور).", reply_markup=back_keyboard())
        return

    neighbor_ids = _ensure_neighbors(country["country_id"])
    neighbor_countries = [_get_country(nid) for nid in neighbor_ids]
    neighbor_countries = [c for c in neighbor_countries if c]

    today = _today_key()
    with get_conn() as conn:
        claimed = conn.execute(
            "SELECT 1 FROM border_trade_claims WHERE country_id = ? AND claim_date = ?",
            (country["country_id"], today),
        ).fetchone()

    lines = [f"🗺 همسایگان کشور {country['name']}\n"]
    if not neighbor_countries:
        lines.append("هنوز همسایه‌ای پیدا نشده (کشورهای دیگه‌ای وجود نداره).")
    else:
        for nc in neighbor_countries:
            owner = get_user(nc["owner_id"]) if nc["owner_id"] else None
            owner_name = owner["first_name"] if owner else "؟"
            lines.append(f"  • {nc['name']} (صاحب: {owner_name})")
    lines.append(
        f"\n🤝 تجارت مرزی امروز: {'✅ قبلاً انجام دادی' if claimed else 'هنوز انجام ندادی'} "
        f"— بین {BORDER_TRADE_MIN} تا {BORDER_TRADE_MAX} سکه‌ی رایگان برای هر دو طرف!"
    )

    can_trade = bool(neighbor_countries) and not claimed
    await q.edit_message_text("\n".join(lines), reply_markup=_neighbors_keyboard(neighbor_countries, can_trade))


async def border_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    country = _get_country_by_owner(user_id)
    if not country:
        await q.answer("اول باید کشور بسازی.", show_alert=True)
        return

    neighbor_ids = _ensure_neighbors(country["country_id"])
    if not neighbor_ids:
        await q.answer("همسایه‌ای پیدا نشد.", show_alert=True)
        return

    today = _today_key()
    with get_conn() as conn:
        claimed = conn.execute(
            "SELECT 1 FROM border_trade_claims WHERE country_id = ? AND claim_date = ?",
            (country["country_id"], today),
        ).fetchone()
    if claimed:
        await q.answer("امروز قبلاً تجارت مرزی انجام دادی.", show_alert=True)
        return

    await q.answer()
    partner_id = random.choice(neighbor_ids)
    partner = _get_country(partner_id)

    bonus_me = random.randint(BORDER_TRADE_MIN, BORDER_TRADE_MAX)
    update_balance(user_id, coin=bonus_me)
    log_transaction(user_id, "BORDER_TRADE", f"with_country={partner_id} bonus={bonus_me}")

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO border_trade_claims (country_id, claim_date) VALUES (?, ?)",
            (country["country_id"], today),
        )

    partner_note = ""
    if partner and partner["owner_id"]:
        bonus_partner = random.randint(BORDER_TRADE_MIN, BORDER_TRADE_MAX)
        update_balance(partner["owner_id"], coin=bonus_partner)
        log_transaction(partner["owner_id"], "BORDER_TRADE", f"with_country={country['country_id']} bonus={bonus_partner}")
        partner_note = f" (کشور {partner['name']} هم {bonus_partner} سکه گرفت)"
        try:
            await context.bot.send_message(
                partner["owner_id"],
                f"🤝 تجارت مرزی با کشور {country['name']}! +{bonus_partner} سکه گرفتی.",
            )
        except TelegramError:
            pass

    await q.edit_message_text(
        f"🤝 تجارت مرزی با کشور {partner['name'] if partner else 'همسایه'} انجام شد!\n"
        f"+{bonus_me} سکه گرفتی.{partner_note}",
        reply_markup=back_keyboard("neighbors_menu"),
    )


# ============================================================
#   ۵) پروفایل عمومی
# ============================================================
async def profile_lookup_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "profile_lookup_id_input"
    await q.edit_message_text("🔎 آیدی عددی کاربری که می‌خوای پروفایلش رو ببینی رو بفرست:")


async def _do_profile_lookup(update, context, raw_text):
    _ensure_tables()
    try:
        target_id = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return

    target = get_user(target_id)
    if not target:
        await update.message.reply_text("❌ کاربری با این آیدی پیدا نشد.")
        return

    with get_conn() as conn:
        comp = conn.execute("SELECT * FROM comp_profile WHERE user_id = ?", (target_id,)).fetchone()
        country = conn.execute("SELECT name FROM countries WHERE owner_id = ?", (target_id,)).fetchone()

    rank_text = RANKS[comp["rank_index"]] if comp else RANKS[0]
    wins = comp["wins"] if comp else 0
    country_name = country["name"] if country else "بدون کشور"

    badge = ""
    try:
        import handlers_social
        badge = handlers_social.get_display_badge(target_id)
    except Exception:
        pass

    sub_tier_key = get_active_subscription_tier(target_id)
    sub_text = SUBSCRIPTION_TIERS[sub_tier_key]["badge"] + " " + SUBSCRIPTION_TIERS[sub_tier_key]["title"] if sub_tier_key else "بدون اشتراک"

    technique_level = 0
    try:
        import handlers_competition_boost
        technique_level = handlers_competition_boost.get_technique_level(target_id)
    except Exception:
        pass

    text = (
        f"🏆 پروفایل عمومی\n\n"
        f"👤 نام: {target['first_name']} {badge}\n"
        f"⭐ سطح: {target['level']}\n"
        f"⚔️ رنک رقابتی: {rank_text} ({wins} برد)\n"
        f"🥋 سطح تکنیک: {technique_level}\n"
        f"🌍 کشور: {country_name}\n"
        f"🎫 اشتراک: {sub_text}"
    )
    await update.message.reply_text(text, reply_markup=back_keyboard())


# ============================================================
#   ۶) یادآور هوشمند
# ============================================================
async def reminder_job(context: ContextTypes.DEFAULT_TYPE):
    """هر روز صدا زده می‌شود؛ به کاربرانی که بیش از ۲۴ ساعته ماموریت روزانه نگرفتن
    و امروز قبلاً یادآوری نگرفتن، یک پیام انگیزشی می‌فرسته."""
    _ensure_tables()
    today = _today_key()
    with get_conn() as conn:
        users = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()

    for row in users:
        user_id = row["user_id"]
        if has_done_daily_mission(user_id):
            continue
        try:
            import handlers_features3
            if handlers_features3.is_reminder_opted_out(user_id):
                continue
        except Exception:
            pass
        with get_conn() as conn:
            already_reminded = conn.execute(
                "SELECT 1 FROM reminder_log WHERE user_id = ? AND date_key = ?", (user_id, today)
            ).fetchone()
        if already_reminded:
            continue
        with get_conn() as conn:
            conn.execute("INSERT INTO reminder_log (user_id, date_key) VALUES (?, ?)", (user_id, today))
        try:
            await context.bot.send_message(user_id, random.choice(REMINDER_MESSAGES))
        except TelegramError:
            pass


# ============================================================
#   دیسپچر
# ============================================================
SIMPLE_CALLBACKS = {
    "league_menu": league_menu_callback,
    "market_chart": market_chart_callback,
    "mentor_menu": mentor_menu_callback,
    "mentor_status": mentor_status_callback,
    "mentor_add_start": mentor_add_start_callback,
    "neighbors_menu": neighbors_menu_callback,
    "border_trade": border_trade_callback,
    "profile_lookup_start": profile_lookup_start_callback,
}


async def features2_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return True
    return False


async def features2_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "mentor_add_id_input":
        context.user_data["awaiting"] = None
        await _do_mentor_add(update, context, raw_text)
        return True
    if awaiting == "profile_lookup_id_input":
        context.user_data["awaiting"] = None
        await _do_profile_lookup(update, context, raw_text)
        return True
    return False
