# -*- coding: utf-8 -*-
"""
handlers_bonus.py — قابلیت‌های پاداشی و ویژه‌ی ربات LIBER (فایل جدا)
================================================================
شامل ۶ قابلیت:
    👑 دکمه‌ی مخفی VIP، 🎰 گردونه‌ی شانس بزرگ، 🏆 رتبه‌بندی دعوت ماهانه،
    🎁 کد هدیه، 🎖 دستاوردها، 🕵️ VIP مخفی برای خریداران بزرگ.
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

VIP_DAILY_BONUS_LIBER = {"normal": 15, "dragon": 35, "liberi": 70}

VIP_TOURNAMENT_INTERVAL_SECONDS = 30 * 86400
VIP_TOURNAMENT_REWARDS = {1: 1000, 2: 600, 3: 400}

WHEEL_MIN_BET = 10
WHEEL_OUTCOMES = [0, 0.5, 1, 1.5, 2, 5, 10]
WHEEL_WEIGHTS = [20, 20, 20, 15, 15, 7, 3]

WHALE_STARS_THRESHOLD = 150
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
        conn.execute("""
        CREATE TABLE IF NOT EXISTS vip_tournament_points (
            user_id INTEGER PRIMARY KEY,
            points INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS vip_tournament_season (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            season_number INTEGER NOT NULL DEFAULT 1,
            started_at INTEGER NOT NULL
        )
        """)
        row = conn.execute("SELECT 1 FROM vip_tournament_season WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO vip_tournament_season (id, season_number, started_at) VALUES (1, 1, ?)",
                (int(time.time()),),
            )
    _tables_ready = True


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


def vip_bonus_button_rows(user_id):
    tier_key = get_active_subscription_tier(user_id)
    if not tier_key:
        return None
    return [
        [InlineKeyboardButton("👑 پاداش ویژه‌ی VIP امروز", callback_data="vip_secret_bonus")],
        [InlineKeyboardButton("🕵️ تورنمنت مخفی VIP", callback_data="vip_tournament_secret")],
    ]


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
        conn.execute(
            """INSERT INTO vip_tournament_points (user_id, points) VALUES (?, 1)
               ON CONFLICT(user_id) DO UPDATE SET points = points + 1""",
            (user_id,),
        )
    log_transaction(user_id, "VIP_DAILY_BONUS", str(reward))

    tier_title = SUBSCRIPTION_TIERS[tier_key]["title"]
    await q.edit_message_text(
        f"👑 پاداش ویژه‌ی VIP گرفتی!\n{tier_title}\n+{reward} LIBER\n\n"
        f"🏆 امتیازت تو تورنمنت مخفی VIP هم بالا رفت (هر روز که سر بزنی +۱ امتیاز)!\nفردا دوباره سر بزن 🥂",
        reply_markup=back_keyboard(),
    )


async def vip_tournament_secret_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    tier_key = get_active_subscription_tier(user_id)
    if not tier_key:
        await q.answer("این بخش فقط برای مشترکینه.", show_alert=True)
        return

    await q.answer()
    with get_conn() as conn:
        my_points_row = conn.execute("SELECT points FROM vip_tournament_points WHERE user_id = ?", (user_id,)).fetchone()
        top5 = conn.execute("SELECT user_id, points FROM vip_tournament_points ORDER BY points DESC LIMIT 5").fetchall()
        season = conn.execute("SELECT * FROM vip_tournament_season WHERE id = 1").fetchone()

    my_points = my_points_row["points"] if my_points_row else 0
    days_left = max(0, (VIP_TOURNAMENT_INTERVAL_SECONDS - (int(time.time()) - season["started_at"])) // 86400)

    lines = [
        "🕵️ تورنمنت مخفی VIP\n",
        "این بخش فقط برای مشترکینه و هیچ‌جای دیگه‌ای تبلیغ نمی‌شه 🤫\n",
        f"امتیاز شما: {my_points}",
        f"⏳ {days_left} روز تا پایان این دوره\n",
        "🏆 برترین‌ها:",
    ]
    for i, row in enumerate(top5, start=1):
        u = get_user(row["user_id"])
        name = u["first_name"] if u else str(row["user_id"])
        lines.append(f"  {i}. {name} — {row['points']} امتیاز")
    r = VIP_TOURNAMENT_REWARDS
    lines.append(f"\n🎁 جوایز پایان دوره: ۱ام {r[1]} | ۲ام {r[2]} | ۳ام {r[3]} LIBER")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


async def vip_tournament_reward_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    with get_conn() as conn:
        season = conn.execute("SELECT * FROM vip_tournament_season WHERE id = 1").fetchone()
    now = int(time.time())
    if now - season["started_at"] < VIP_TOURNAMENT_INTERVAL_SECONDS:
        return

    with get_conn() as conn:
        top3 = conn.execute("SELECT user_id, points FROM vip_tournament_points ORDER BY points DESC LIMIT 3").fetchall()

    for i, row in enumerate(top3, start=1):
        if row["points"] <= 0:
            continue
        reward = VIP_TOURNAMENT_REWARDS.get(i, 0)
        update_balance(row["user_id"], liber=reward)
        log_transaction(row["user_id"], "VIP_TOURNAMENT_REWARD", f"rank={i}")
        try:
            await context.bot.send_message(
                row["user_id"],
                f"🕵️ تبریک! تو تورنمنت مخفی VIP رتبه‌ی {i} شدی و {reward} LIBER جایزه گرفتی 🎉\n"
                "این یه جایزه‌ی کاملاً ویژه بود، فقط برای بهترین مشترکین 👑",
            )
        except TelegramError:
            pass

    new_season = season["season_number"] + 1
    with get_conn() as conn:
        conn.execute("DELETE FROM vip_tournament_points")
        conn.execute(
            "UPDATE vip_tournament_season SET season_number = ?, started_at = ? WHERE id = 1", (new_season, now)
        )
    logger.info(f"تورنمنت مخفی VIP برگزار شد. فصل جدید: {new_season}")


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


REFERRAL_MONTHLY_REWARD = 500


def _month_key(ts=None):
    ts = ts if ts is not None else time.time()
    return time.strftime("%Y-%m", time.gmtime(ts))


def _month_bounds(month_key):
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
    _ensure_tables()
    prev_month_key = _month_key(time.time() - 86400 * 2)
    current_month_key = _month_key()
    if prev_month_key == current_month_key:
        return

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
    if _grant_achievement(user_id, "first_subscription"):
        await _notify_achievement(bot, user_id, "first_subscription")


async def check_win_streak_achievement(user_id, streak, bot):
    if streak >= 10 and _grant_achievement(user_id, "win_streak_10"):
        await _notify_achievement(bot, user_id, "win_streak_10")


async def check_first_withdraw_achievement(user_id, bot):
    if _grant_achievement(user_id, "first_withdraw"):
        await _notify_achievement(bot, user_id, "first_withdraw")


async def check_whale_status(user_id, bot):
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


async def _noop(update, context):
    await update.callback_query.answer()


BONUS_CALLBACKS = {
    "vip_secret_bonus": vip_secret_bonus_callback,
    "vip_tournament_secret": vip_tournament_secret_callback,
    "menu_wheel": wheel_menu_callback,
    "wheel_spin": wheel_spin_callback,
    "wheel_noop": _noop,
    "menu_referral_top": referral_top_callback,
    "menu_giftcode": giftcode_menu_callback,
    "menu_achievements": achievements_menu_callback,
    "giftcode_admin_create": admin_create_giftcode_callback,
}


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
