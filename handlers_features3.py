# -*- coding: utf-8 -*-
"""
handlers_features3.py — پارت ۴ از بسته‌ی توسعه‌ی LIBER
================================================================
۶ قابلیت جدید (هیچ‌کدوم شانسی/قماری نیستن — همه بر پایه‌ی فعالیت
واقعی و پیش‌بینی‌پذیرن):

    🔥 استریک روزانه          هر چند روز متوالی ماموریت روزانه بگیری، پاداش پلکانی می‌گیری
    🏭 تولید غیرفعال کشور     ساختمان‌ها هر ساعت تولید می‌کنن، جمعش می‌کنی و برداشت می‌کنی
    😊 رضایت کشور             با LIBER رضایت رو بالا ببر، رضایت بالاتر = تولید بیشتر
    🎖 برترین‌های سرور        یک منوی ترکیبی: ثروتمندترین‌ها، بالاترین سطح، بهترین رقابتی
    ⚙️ تنظیمات                خاموش/روشن کردن یادآور روزانه‌ی خودکار
    🧾 تاریخچه‌ی تراکنش‌ها      ۱۰ تراکنش آخر خودت رو می‌بینی

⚙️ فرض‌های گرفته‌شده:
  • استریک: اگه یک روز رو از دست بدی، از صفر شروع می‌شه. سقف‌ها: ۳ روز
    =۳۰ LIBER، ۷ روز=۱۰۰ LIBER، ۱۴ روز=۲۵۰ LIBER، ۳۰ روز=۶۰۰ LIBER
    (فقط یک‌بار در هر چرخه‌ی استریک به هر سقف می‌رسی).
  • تولید: هر ساختمان بر اساس نوع و سطح، در ساعت مقداری سکه تولید می‌کنه؛
    حداکثر ذخیره‌سازی ۱۲ ساعته (بعدش دیگه بیشتر جمع نمی‌شه، باید بیای برداری).
  • رضایت: هر ۱۰٪ رضایت اضافه = ۵۰ LIBER، و رضایت هر ۱۰٪ بالای ۷۰،
    ۵٪ به تولید ساعتی اضافه می‌کنه.

نحوه‌ی اتصال:

    # main.py → callback_router و text_message_router → همون زنجیره‌ی همیشگی:
        import handlers_features3
        handled = await handlers_features3.features3_callback_router(update, context)
        # و
        if await handlers_features3.features3_text_router(update, context): return

    # main.py → main_menu_keyboard() این ردیف‌ها رو اضافه کن:
        [InlineKeyboardButton("🎖 برترین‌های سرور", callback_data="hall_of_fame"),
         InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings_menu")],
        [InlineKeyboardButton("🧾 تاریخچه‌ی تراکنش‌ها", callback_data="tx_history")],

    # main.py → داخل daily_mission_callback، درست بعد از update_balance اصلی
    # (همون‌جایی که هندلرهای دیگه مثل handlers_social صدا زده می‌شن)، اضافه کن:
        import handlers_features3
        streak_note = await handlers_features3.record_daily_streak(user_id, context.bot)
        # و streak_note (اگه خالی نبود) رو به متن پیام نهایی اضافه کن

    # handlers_extra.py → داخل country_view_keyboard() این ردیف‌ها رو اضافه کن:
        [InlineKeyboardButton("🏭 برداشت تولید", callback_data="country_claim_production"),
         InlineKeyboardButton("😊 افزایش رضایت (۵۰ LIBER)", callback_data="country_boost_satisfaction")],

    # handlers_features2.py → داخل reminder_job، قبل از ارسال پیام یادآور، این چک رو اضافه کن:
        if is_reminder_opted_out(user_id):   # از همین فایل import کن
            continue
"""
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import get_conn, get_user, update_balance, log_transaction, back_keyboard, RANKS

logger = logging.getLogger("LIBER.features3")

# ============================================================
#   تنظیمات
# ============================================================
STREAK_MILESTONES = {3: 30, 7: 100, 14: 250, 30: 600}

PRODUCTION_PER_LEVEL_PER_HOUR = {
    "mine": 5, "factory": 8, "power_plant": 6, "farm": 4, "lab": 3,
}
PRODUCTION_MAX_HOURS = 12

SATISFACTION_BOOST_COST = 50
SATISFACTION_BOOST_AMOUNT = 10
SATISFACTION_PRODUCTION_BONUS_PER_10_OVER_70 = 5  # درصد


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
        CREATE TABLE IF NOT EXISTS daily_streak (
            user_id INTEGER PRIMARY KEY,
            streak INTEGER NOT NULL DEFAULT 0,
            last_date TEXT,
            claimed_milestones TEXT NOT NULL DEFAULT ''
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS country_production (
            country_id INTEGER PRIMARY KEY,
            last_claim_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS notif_prefs (
            user_id INTEGER PRIMARY KEY,
            reminders_enabled INTEGER NOT NULL DEFAULT 1
        )
        """)
    _ready = True


def _today_key(ts=None):
    ts = ts if ts is not None else time.time()
    return time.strftime("%Y-%m-%d", time.gmtime(ts))


def _yesterday_key():
    return _today_key(time.time() - 86400)


# ============================================================
#   ۱) استریک روزانه
# ============================================================
async def record_daily_streak(user_id, bot):
    """صدا زده می‌شود از main.py بلافاصله بعد از claim موفق ماموریت روزانه.
    خروجی: متنی که باید به پیام موفقیت اضافه بشه (یا رشته‌ی خالی)."""
    _ensure_tables()
    today = _today_key()
    yesterday = _yesterday_key()

    with get_conn() as conn:
        row = conn.execute("SELECT * FROM daily_streak WHERE user_id = ?", (user_id,)).fetchone()

    if not row:
        new_streak = 1
        claimed = ""
    elif row["last_date"] == today:
        # همون روز دوباره صدا زده شده (نباید بشه، ولی برای اطمینان idempotent می‌کنیم)
        return ""
    elif row["last_date"] == yesterday:
        new_streak = row["streak"] + 1
        claimed = row["claimed_milestones"]
    else:
        new_streak = 1
        claimed = ""

    with get_conn() as conn:
        conn.execute(
            """INSERT INTO daily_streak (user_id, streak, last_date, claimed_milestones)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(user_id) DO UPDATE SET streak = ?, last_date = ?, claimed_milestones = ?""",
            (user_id, new_streak, today, claimed, new_streak, today, claimed),
        )

    note = f"\n\n🔥 استریک روزانه: {new_streak} روز متوالی"

    claimed_set = set(claimed.split(",")) if claimed else set()
    milestone_key = str(new_streak)
    if new_streak in STREAK_MILESTONES and milestone_key not in claimed_set:
        reward = STREAK_MILESTONES[new_streak]
        update_balance(user_id, liber=reward)
        log_transaction(user_id, "STREAK_MILESTONE", f"{new_streak} days -> {reward} LIBER")
        claimed_set.add(milestone_key)
        with get_conn() as conn:
            conn.execute(
                "UPDATE daily_streak SET claimed_milestones = ? WHERE user_id = ?",
                (",".join(sorted(claimed_set)), user_id),
            )
        note += f"\n🎉 به مرز {new_streak} روز رسیدی! +{reward} LIBER پاداش استریک گرفتی."

    return note


# ============================================================
#   ۲) تولید غیرفعال کشور
# ============================================================
def _get_country_by_owner(owner_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM countries WHERE owner_id = ?", (owner_id,)).fetchone()


def _get_country_buildings(country_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM buildings WHERE country_id = ?", (country_id,)).fetchall()


def _hourly_production(country):
    buildings = _get_country_buildings(country["country_id"])
    base = sum(
        b["level"] * PRODUCTION_PER_LEVEL_PER_HOUR.get(b["type"], 0) for b in buildings
    )
    satisfaction = country["satisfaction"] or 0
    bonus_pct = max(0, (satisfaction - 70) // 10) * SATISFACTION_PRODUCTION_BONUS_PER_10_OVER_70
    return round(base * (1 + bonus_pct / 100), 1)


async def country_claim_production_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    country = _get_country_by_owner(user_id)
    if not country:
        await q.answer("اول باید کشور بسازی.", show_alert=True)
        return

    now = int(time.time())
    with get_conn() as conn:
        row = conn.execute(
            "SELECT last_claim_at FROM country_production WHERE country_id = ?", (country["country_id"],)
        ).fetchone()
    last_claim = row["last_claim_at"] if row else country["created_at"]

    elapsed_hours = min(PRODUCTION_MAX_HOURS, (now - last_claim) / 3600)
    hourly = _hourly_production(country)
    total = round(hourly * elapsed_hours)

    if total <= 0:
        await q.answer("هنوز چیزی برای برداشت جمع نشده — یکم صبر کن.", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, coin=total)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO country_production (country_id, last_claim_at) VALUES (?, ?)
               ON CONFLICT(country_id) DO UPDATE SET last_claim_at = ?""",
            (country["country_id"], now, now),
        )
    log_transaction(user_id, "COUNTRY_PRODUCTION_CLAIM", f"coin={total}")

    capped_note = " (به سقف ۱۲ ساعته رسیده بود)" if elapsed_hours >= PRODUCTION_MAX_HOURS else ""
    await q.edit_message_text(
        f"🏭 تولید کشورت رو برداشت کردی!\n+{total} سکه{capped_note}\n"
        f"(تولید ساعتی فعلی: {hourly} سکه/ساعت)",
        reply_markup=back_keyboard("menu_country"),
    )


# ============================================================
#   ۳) رضایت کشور
# ============================================================
async def country_boost_satisfaction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    country = _get_country_by_owner(user_id)
    if not country:
        await q.answer("اول باید کشور بسازی.", show_alert=True)
        return
    if country["satisfaction"] >= 100:
        await q.answer("رضایت کشورت همین الان هم ماکزیممه (۱۰۰٪).", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < SATISFACTION_BOOST_COST:
        await q.answer(f"❌ برای این کار به {SATISFACTION_BOOST_COST} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-SATISFACTION_BOOST_COST)
    new_satisfaction = min(100, country["satisfaction"] + SATISFACTION_BOOST_AMOUNT)
    with get_conn() as conn:
        conn.execute(
            "UPDATE countries SET satisfaction = ? WHERE country_id = ?",
            (new_satisfaction, country["country_id"]),
        )
    log_transaction(user_id, "SATISFACTION_BOOST", f"new={new_satisfaction}")

    await q.edit_message_text(
        f"😊 رضایت کشورت به {new_satisfaction}٪ رسید! (-{SATISFACTION_BOOST_COST} LIBER)\n"
        "رضایت بالاتر از ۷۰٪ به تولید ساعتی کشورت بونوس می‌ده.",
        reply_markup=back_keyboard("menu_country"),
    )


# ============================================================
#   ۴) برترین‌های سرور
# ============================================================
async def hall_of_fame_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    with get_conn() as conn:
        richest = conn.execute(
            "SELECT first_name, liber FROM users WHERE is_banned = 0 ORDER BY liber DESC LIMIT 5"
        ).fetchall()
        top_level = conn.execute(
            "SELECT first_name, level, xp FROM users WHERE is_banned = 0 ORDER BY level DESC, xp DESC LIMIT 5"
        ).fetchall()
        top_comp = conn.execute(
            """SELECT u.first_name, c.rank_index, c.wins FROM comp_profile c
               JOIN users u ON u.user_id = c.user_id
               ORDER BY c.rank_index DESC, c.wins DESC LIMIT 5"""
        ).fetchall()

    lines = ["🎖 برترین‌های سرور LIBER\n"]

    lines.append("💰 ثروتمندترین‌ها:")
    for i, r in enumerate(richest, start=1):
        lines.append(f"  {i}. {r['first_name']} — {round(r['liber'])} LIBER")

    lines.append("\n⭐ بالاترین سطح:")
    for i, r in enumerate(top_level, start=1):
        lines.append(f"  {i}. {r['first_name']} — سطح {r['level']}")

    lines.append("\n⚔️ بهترین‌های رقابتی:")
    for i, r in enumerate(top_comp, start=1):
        lines.append(f"  {i}. {r['first_name']} — {RANKS[r['rank_index']]} ({r['wins']} برد)")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


# ============================================================
#   ۵) تنظیمات (یادآور روزانه)
# ============================================================
def is_reminder_opted_out(user_id):
    """صدا زده می‌شود از handlers_features2.reminder_job."""
    _ensure_tables()
    with get_conn() as conn:
        row = conn.execute("SELECT reminders_enabled FROM notif_prefs WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return False
    return row["reminders_enabled"] == 0


def _settings_keyboard(enabled):
    toggle_label = "🔕 خاموش کردن یادآور روزانه" if enabled else "🔔 روشن کردن یادآور روزانه"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(toggle_label, callback_data="settings_toggle_reminders")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


async def settings_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    with get_conn() as conn:
        row = conn.execute("SELECT reminders_enabled FROM notif_prefs WHERE user_id = ?", (user_id,)).fetchone()
    enabled = True if not row else bool(row["reminders_enabled"])

    text = (
        "⚙️ تنظیمات\n\n"
        f"یادآور روزانه‌ی خودکار (وقتی ۲۴ ساعت سر نزنی): {'فعال ✅' if enabled else 'غیرفعال ❌'}"
    )
    await q.edit_message_text(text, reply_markup=_settings_keyboard(enabled))


async def settings_toggle_reminders_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    with get_conn() as conn:
        row = conn.execute("SELECT reminders_enabled FROM notif_prefs WHERE user_id = ?", (user_id,)).fetchone()
    new_value = 0 if (not row or row["reminders_enabled"]) else 1

    await q.answer()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO notif_prefs (user_id, reminders_enabled) VALUES (?, ?)
               ON CONFLICT(user_id) DO UPDATE SET reminders_enabled = ?""",
            (user_id, new_value, new_value),
        )
    await settings_menu_callback(update, context)


# ============================================================
#   ۶) تاریخچه‌ی تراکنش‌ها
# ============================================================
async def tx_history_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT kind, detail, created_at FROM transactions WHERE user_id = ? ORDER BY tx_id DESC LIMIT 10",
            (user_id,),
        ).fetchall()

    if not rows:
        await q.edit_message_text("🧾 هنوز هیچ تراکنشی ثبت نشده.", reply_markup=back_keyboard())
        return

    lines = ["🧾 ۱۰ تراکنش آخر شما\n"]
    for r in rows:
        ts_text = time.strftime("%m/%d %H:%M", time.gmtime(r["created_at"]))
        detail = f" — {r['detail']}" if r["detail"] else ""
        lines.append(f"• [{ts_text}] {r['kind']}{detail}")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


# ============================================================
#   دیسپچر
# ============================================================
SIMPLE_CALLBACKS = {
    "country_claim_production": country_claim_production_callback,
    "country_boost_satisfaction": country_boost_satisfaction_callback,
    "hall_of_fame": hall_of_fame_callback,
    "settings_menu": settings_menu_callback,
    "settings_toggle_reminders": settings_toggle_reminders_callback,
    "tx_history": tx_history_callback,
}


async def features3_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return True
    return False


async def features3_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    # این ماژول در حال حاضر هیچ ورودی متنی چندمرحله‌ای نداره (همه‌چیز دکمه‌ایه)
    return False
