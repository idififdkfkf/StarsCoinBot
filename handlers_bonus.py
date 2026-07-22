# -*- coding: utf-8 -*-
"""
handlers_bonus.py — قابلیت‌های پاداشی و ویژه‌ی ربات LIBER (فایل جدا)
================================================================
این فایل کاملاً جداست و باید کنار main.py قرار بگیرد. جدول‌های خودش را
در اولین استفاده خودکار می‌سازد (نیازی به تغییر database.py نیست).

شامل ۶ قابلیت:
    👑 دکمه‌ی مخفی VIP        فقط در پروفایل کاربران دارای اشتراک دیده می‌شود؛
                             یک پاداش روزانه‌ی اضافی (جدا از ماموریت اجباری) می‌دهد.
    🎰 گردونه‌ی شانس بزرگ      شرط LIBER، ۷ نتیجه‌ی ممکن با احتمال‌های متفاوت.
    🏆 رتبه‌بندی دعوت ماهانه   هر ماه خودکار به پردعوت‌کننده‌ی برتر جایزه می‌دهد.
    🎁 کد هدیه                ادمین می‌سازد، کاربران با کد یک‌بار جایزه می‌گیرند.
    🎖 دستاوردها               مدال برای کارهای خاص (اولین اشتراک، ۱۰ برد پیاپی و...).
    🕵️ VIP مخفی برای خریداران بزرگ   بعد از عبور از آستانه‌ی خرید استارز، خودکار
                             پیام دعوت ویژه دریافت می‌کنند (بدون دکمه — کاملاً خودکار).
"""
import time
import calendar
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import (
    get_conn, get_user, update_balance, log_transaction,
    get_active_subscription_tier, SUBSCRIPTION_TIERS, ADMIN_IDS,
    back_keyboard,
)

logger = logging.getLogger("LIBER.bonus")

# ============================================================
#   تنظیمات محلی
# ============================================================
VIP_DAILY_BONUS_LIBER = {"normal": 15, "dragon": 35, "liberi": 70}

WHEEL_MIN_BET = 10
WHEEL_OUTCOMES = [0, 0.5, 1, 1.5, 2, 5, 10]
WHEEL_WEIGHTS = [20, 20, 20, 15, 15, 7, 3]

WHALE_STARS_THRESHOLD = 150   # مجموع استارز خرج‌شده برای فعال‌شدن VIP مخفی
WHALE_INVITE_TEXT = (
    "🕵️ یک پیام ویژه برای شما!\n\n"
    "شما جزو بزرگ‌ترین حامیان LIBER هستید 🙏 به همین‌خاطر به کانال خصوصی VIP دعوت شدید.\n"
    "به‌زودی ادمین باهاتون در ارتباط می‌شه."
)

ACHIEVEMENTS = {
    "first_subscription": {"name": "🎫 اولین اشتراک", "desc": "اولین بار اشتراک ویژه خریدی"},
    "win_streak_10": {"name": "🔥 ۱۰ برد پیاپی", "desc": "در رقابت آنلاین ۱۰ برد پشت‌سرهم گرفتی"},
    "whale": {"name": "🕵️ حامی ویژه", "desc": f"مجموع بیش از {WHALE_STARS_THRESHOLD}⭐ خرج کردی"},
    "first_withdraw": {"name": "📤 اولین برداشت", "desc": "اولین درخواست برداشت TON رو ثبت کردی"},
}


# ============================================================
#   جداول محلی (idempotent، فقط یک‌بار ساخته می‌شوند)
# ============================================================
_tables_ready = False


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS vip_bonus_claims (
            user_id INTEGER,
            claim_date TEXT,
            PRIMARY KEY (user_id, claim_date)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS gift_codes (
            code TEXT PRIMARY KEY,
            reward_liber REAL NOT NULL,
            max_uses INTEGER NOT NULL,
            used_count INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS gift_redemptions (
            code TEXT,
            user_id INTEGER,
            redeemed_at INTEGER,
            PRIMARY KEY (code, user_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            achievement_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            achieved_at INTEGER NOT NULL,
            UNIQUE(user_id, key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS referral_reward_log (
            month_key TEXT PRIMARY KEY,
            winner_id INTEGER,
            reward REAL,
            paid_at INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS whale_status (
            user_id INTEGER PRIMARY KEY,
            notified_at INTEGER NOT NULL
        )
        """)
    _tables_ready = True


# ============================================================
#   دستاوردها (توابع کمکی مشترک)
# ============================================================
def _grant_achievement(user_id, key):
    _ensure_tables()
    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM user_achievements WHERE user_id = ? AND key = ?", (user_id, key)
        ).fetchone()
        if already:
            return False
        conn.execute(
            "INSERT INTO user_achievements (user_id, key, achieved_at) VALUES (?, ?, ?)",
            (user_id, key, int(time.time())),
        )
        return True


async def _notify_achievement(bot, user_id, key):
    info = ACHIEVEMENTS[key]
    try:
        await bot.send_message(user_id, f"🎖 دستاورد جدید: {info['name']}\n{info['desc']}")
    except TelegramError:
        pass


# ============================================================
#   ۱) دکمه‌ی مخفی VIP — فقط در پروفایل کاربران مشترک دیده می‌شود
# ============================================================
def vip_bonus_button_row(user_id):
    """اگر کاربر اشتراک فعال دارد و امروز هنوز پاداش VIP رو نگرفته، یک ردیف دکمه برمی‌گرداند؛
    در غیر این صورت None (یعنی این دکمه اصلاً برای بقیه دیده نمی‌شود)."""
    tier_key = get_active_subscription_tier(user_id)
    if not tier_key:
        return None
    return [InlineKeyboardButton("👑 پاداش ویژه‌ی VIP امروز", callback_data="vip_secret_bonus")]


async def vip_secret_bonus_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    tier_key = get_active_subscription_tier(user_id)

    if not tier_key:
        await q.answer("این پاداش فقط برای مشترکین فعاله.", show_alert=True)
        return

    today = time.strftime("%Y-%m-%d", time.gmtime())
    with get_conn() as conn:
        claimed = conn.execute(
            "SELECT 1 FROM vip_bonus_claims WHERE user_id = ? AND claim_date = ?", (user_id, today)
        ).fetchone()
    if claimed:
        await q.answer("✅ پاداش VIP امروز رو قبلاً گرفتی. فردا دوباره سر بزن!", show_alert=True)
        return

    await q.answer()
    reward = VIP_DAILY_BONUS_LIBER.get(tier_key, 15)
    update_balance(user_id, liber=reward)
    with get_conn() as conn:
        conn.execute("INSERT INTO vip_bonus_claims (user_id, claim_date) VALUES (?, ?)", (user_id, today))
    log_transaction(user_id, "VIP_DAILY_BONUS", str(reward))

    tier_title = SUBSCRIPTION_TIERS[tier_key]["title"]
    await q.edit_message_text(
        f"👑 پاداش ویژه‌ی VIP گرفتی!\n{tier_title}\n+{reward} LIBER\n\nفردا دوباره سر بزن 🥂",
        reply_markup=back_keyboard(),
    )


# ============================================================
#   ۲) گردونه‌ی شانس بزرگ
# ============================================================
def _wheel_stepper_keyboard(amount):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("-10", callback_data="wheel_bet:-10"),
         InlineKeyboardButton("-50", callback_data="wheel_bet:-50"),
         InlineKeyboardButton(f"💰 {amount}", callback_data="wheel_noop"),
         InlineKeyboardButton("+50", callback_data="wheel_bet:50"),
         InlineKeyboardButton("+10", callback_data="wheel_bet:10")],
        [InlineKeyboardButton("🎰 بچرخون!", callback_data="wheel_spin")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])


async def wheel_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["wheel_bet"] = WHEEL_MIN_BET
    await q.edit_message_text(
        f"🎰 گردونه‌ی شانس بزرگ\n\nمبلغ شرط رو تنظیم کن (حداقل {WHEEL_MIN_BET} LIBER)، بعد بچرخون:",
        reply_markup=_wheel_stepper_keyboard(WHEEL_MIN_BET),
    )


async def wheel_bet_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    delta = int(q.data.split(":", 1)[1])
    current = context.user_data.get("wheel_bet", WHEEL_MIN_BET)
    new_amount = max(WHEEL_MIN_BET, current + delta)
    context.user_data["wheel_bet"] = new_amount
    await q.edit_message_reply_markup(reply_markup=_wheel_stepper_keyboard(new_amount))


async def wheel_spin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    bet = context.user_data.get("wheel_bet", WHEEL_MIN_BET)
    user = get_user(user_id)

    if user["liber"] < bet:
        await q.answer("❌ LIBER کافی نیست.", show_alert=True)
        return

    await q.answer()
    multiplier = random.choices(WHEEL_OUTCOMES, weights=WHEEL_WEIGHTS, k=1)[0]
    result = round(bet * multiplier, 2)
    net = round(result - bet, 2)
    update_balance(user_id, liber=net)
    log_transaction(user_id, "WHEEL_SPIN", f"bet={bet} x{multiplier} result={result}")

    emoji = "🎉" if multiplier >= 2 else ("🙂" if multiplier >= 1 else "😔")
    text = f"🎰 گردونه چرخید!\nضریب: x{multiplier}\nشرط: {bet} LIBER\nنتیجه: {result} LIBER {emoji}"
    context.user_data["wheel_bet"] = WHEEL_MIN_BET
    await q.edit_message_text(text, reply_markup=_wheel_stepper_keyboard(WHEEL_MIN_BET))


# ============================================================
#   ۳) رتبه‌بندی دعوت ماهانه
# ============================================================
REFERRAL_MONTHLY_REWARD = 500


def _month_key(ts=None):
    ts = ts if ts is not None else time.time()
    return time.strftime("%Y-%m", time.gmtime(ts))


def _month_bounds(month_key):
    """(start_ts, end_ts) نیمه‌بازِ یک ماه تقویمی میلادی (UTC) بر اساس month_key='YYYY-MM'."""
    year, month = map(int, month_key.split("-"))
    start = calendar.timegm((year, month, 1, 0, 0, 0, 0, 0, 0))
    if month == 12:
        end = calendar.timegm((year + 1, 1, 1, 0, 0, 0, 0, 0, 0))
    else:
        end = calendar.timegm((year, month + 1, 1, 0, 0, 0, 0, 0, 0))
    return start, end


async def referral_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    month_key = _month_key()
    start, end = _month_bounds(month_key)

    with get_conn() as conn:
        rows = conn.execute(
            """SELECT inviter_id, COUNT(*) c FROM referrals
               WHERE created_at >= ? AND created_at < ?
               GROUP BY inviter_id ORDER BY c DESC LIMIT 10""",
            (start, end),
        ).fetchall()

    lines = [f"🏆 رتبه‌بندی دعوت این ماه ({month_key})\n"]
    if not rows:
        lines.append("هنوز کسی امسال دعوت نکرده.")
    for i, r in enumerate(rows, start=1):
        u = get_user(r["inviter_id"])
        name = u["first_name"] if u else str(r["inviter_id"])
        lines.append(f"{i}. {name} — {r['c']} دعوت")
    lines.append(f"\n🎁 جایزه‌ی نفر اول ماه: {REFERRAL_MONTHLY_REWARD} LIBER (خودکار در پایان ماه)")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


async def referral_monthly_reward_job(context: ContextTypes.DEFAULT_TYPE):
    """باید هر روز صدا زده شود؛ خودش تشخیص می‌دهد ماه قبل هنوز جایزه نگرفته یا نه."""
    _ensure_tables()
    prev_month_key = _month_key(time.time() - 86400 * 2)  # ماه قبل (بی‌خطر نسبت به لبه‌ی ماه)
    current_month_key = _month_key()
    if prev_month_key == current_month_key:
        return  # هنوز داخل همون ماهیم، چیزی برای تسویه نیست

    with get_conn() as conn:
        already_paid = conn.execute(
            "SELECT 1 FROM referral_reward_log WHERE month_key = ?", (prev_month_key,)
        ).fetchone()
    if already_paid:
        return

    start, end = _month_bounds(prev_month_key)
    with get_conn() as conn:
        top = conn.execute(
            """SELECT inviter_id, COUNT(*) c FROM referrals
               WHERE created_at >= ? AND created_at < ?
               GROUP BY inviter_id ORDER BY c DESC LIMIT 1""",
            (start, end),
        ).fetchone()

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO referral_reward_log (month_key, winner_id, reward, paid_at) VALUES (?, ?, ?, ?)",
            (prev_month_key, top["inviter_id"] if top else None, REFERRAL_MONTHLY_REWARD if top else 0, int(time.time())),
        )

    if top:
        update_balance(top["inviter_id"], liber=REFERRAL_MONTHLY_REWARD)
        log_transaction(top["inviter_id"], "REFERRAL_MONTHLY_WIN", prev_month_key)
        try:
            await context.bot.send_message(
                top["inviter_id"],
                f"🏆 تبریک! تو ماه {prev_month_key} بیشترین دعوت رو داشتی و {REFERRAL_MONTHLY_REWARD} LIBER جایزه گرفتی! 🎉",
            )
        except TelegramError:
            pass


# ============================================================
#   ۴) کد هدیه
# ============================================================
async def giftcode_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "giftcode_redeem_input"
    await q.edit_message_text("🎁 کد هدیه‌ات رو بفرست:")


async def _do_redeem_giftcode(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    code = raw_text.strip().upper()

    with get_conn() as conn:
        gift = conn.execute("SELECT * FROM gift_codes WHERE code = ?", (code,)).fetchone()

    if not gift:
        await update.message.reply_text("❌ این کد معتبر نیست.")
        return
    if gift["used_count"] >= gift["max_uses"]:
        await update.message.reply_text("❌ ظرفیت این کد تمام شده.")
        return

    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM gift_redemptions WHERE code = ? AND user_id = ?", (code, user_id)
        ).fetchone()
    if already:
        await update.message.reply_text("❌ قبلاً این کد رو استفاده کردی.")
        return

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO gift_redemptions (code, user_id, redeemed_at) VALUES (?, ?, ?)",
            (code, user_id, int(time.time())),
        )
        conn.execute("UPDATE gift_codes SET used_count = used_count + 1 WHERE code = ?", (code,))

    update_balance(user_id, liber=gift["reward_liber"])
    log_transaction(user_id, "GIFT_CODE_REDEEM", code)
    await update.message.reply_text(f"🎉 کد فعال شد! +{gift['reward_liber']} LIBER گرفتی.", reply_markup=back_keyboard())


async def admin_create_giftcode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برای پنل ادمین: شروع مراحل ساخت کد هدیه."""
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS:
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting"] = "admin_giftcode_input"
    await q.edit_message_text(
        "🎁 ساخت کد هدیه\n\nبه این شکل بفرست: کد مقدار_LIBER تعداد_استفاده\nمثال: WELCOME100 100 50"
    )


async def _do_admin_create_giftcode(update, context, raw_text):
    _ensure_tables()
    if update.effective_user.id not in ADMIN_IDS:
        return
    parts = raw_text.split()
    if len(parts) != 3:
        await update.message.reply_text("❌ فرمت اشتباه. مثال: WELCOME100 100 50")
        return
    code = parts[0].strip().upper()
    try:
        reward = float(parts[1])
        max_uses = int(parts[2])
    except ValueError:
        await update.message.reply_text("❌ مقادیر باید عددی باشند.")
        return

    with get_conn() as conn:
        try:
            conn.execute(
                "INSERT INTO gift_codes (code, reward_liber, max_uses, created_at) VALUES (?, ?, ?, ?)",
                (code, reward, max_uses, int(time.time())),
            )
        except Exception:
            await update.message.reply_text("❌ این کد قبلاً وجود دارد.")
            return

    await update.message.reply_text(f"✅ کد «{code}» ساخته شد: {reward} LIBER × {max_uses} استفاده")


# ============================================================
#   ۵) دستاوردها
# ============================================================
async def achievements_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    with get_conn() as conn:
        rows = conn.execute(
            "SELECT key, achieved_at FROM user_achievements WHERE user_id = ?", (user_id,)
        ).fetchall()
    earned_keys = {r["key"] for r in rows}

    lines = ["🎖 دستاوردهای شما\n"]
    for key, info in ACHIEVEMENTS.items():
        mark = "✅" if key in earned_keys else "🔒"
        lines.append(f"{mark} {info['name']} — {info['desc']}")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


async def check_first_subscription_achievement(user_id, bot):
    """صدا زده می‌شود بعد از هر خرید موفق اشتراک (توسط main.py). bot: context.bot یا هر آبجکت مشابه با send_message."""
    if _grant_achievement(user_id, "first_subscription"):
        await _notify_achievement(bot, user_id, "first_subscription")


async def check_win_streak_achievement(user_id, streak, bot):
    """صدا زده می‌شود بعد از هر برد در رقابت آنلاین (توسط handlers_competition.py)."""
    if streak >= 10 and _grant_achievement(user_id, "win_streak_10"):
        await _notify_achievement(bot, user_id, "win_streak_10")


async def check_first_withdraw_achievement(user_id, bot):
    if _grant_achievement(user_id, "first_withdraw"):
        await _notify_achievement(bot, user_id, "first_withdraw")


# ============================================================
#   ۶) VIP مخفی برای خریداران بزرگ (کاملاً خودکار، بدون دکمه)
# ============================================================
async def check_whale_status(user_id, bot):
    """صدا زده می‌شود بعد از هر خرید موفق اشتراک. کاملاً پنهانه — هیچ دکمه‌ای نداره. bot: context.bot."""
    _ensure_tables()
    with get_conn() as conn:
        already = conn.execute("SELECT 1 FROM whale_status WHERE user_id = ?", (user_id,)).fetchone()
        if already:
            return
        total_stars = conn.execute(
            "SELECT COALESCE(SUM(stars_amount), 0) s FROM star_payments WHERE user_id = ?", (user_id,)
        ).fetchone()["s"]

    if total_stars < WHALE_STARS_THRESHOLD:
        return

    with get_conn() as conn:
        conn.execute("INSERT INTO whale_status (user_id, notified_at) VALUES (?, ?)", (user_id, int(time.time())))

    _grant_achievement(user_id, "whale")
    try:
        await bot.send_message(user_id, WHALE_INVITE_TEXT)
    except TelegramError:
        pass
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🕵️ کاربر {user_id} به VIP مخفی رسید (مجموع {total_stars}⭐).")
        except TelegramError:
            pass


# ============================================================
#   دیسپچر
# ============================================================
BONUS_CALLBACKS = {
    "vip_secret_bonus": vip_secret_bonus_callback,
    "menu_wheel": wheel_menu_callback,
    "wheel_spin": wheel_spin_callback,
    "wheel_noop": lambda u, c: _noop(u, c),
    "menu_referral_top": referral_top_callback,
    "menu_giftcode": giftcode_menu_callback,
    "menu_achievements": achievements_menu_callback,
    "giftcode_admin_create": admin_create_giftcode_callback,
}


async def _noop(update, context):
    await update.callback_query.answer()


async def bonus_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in BONUS_CALLBACKS:
        await BONUS_CALLBACKS[data](update, context)
        return True
    if data.startswith("wheel_bet:"):
        await wheel_bet_step_callback(update, context)
        return True
    return False


async def bonus_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "giftcode_redeem_input":
        context.user_data["awaiting"] = None
        await _do_redeem_giftcode(update, context, raw_text)
        return True
    if awaiting == "admin_giftcode_input":
        context.user_data["awaiting"] = None
        await _do_admin_create_giftcode(update, context, raw_text)
        return True
    return False
