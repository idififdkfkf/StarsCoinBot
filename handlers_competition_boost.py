# -*- coding: utf-8 -*-
"""
handlers_competition_boost.py — پارت ۲ از بسته‌ی توسعه‌ی جدید LIBER
================================================================
این فایل مستقل است، کنار main.py قرار می‌گیرد.

⚙️ فرض‌هایی که چون درخواست مبهم بود خودم گرفتم (اگه فرق داشت فقط بگو
کدوم عدد/قانون رو عوض کنم):

  1) «ارتقای رقابت آنلاین» = درخت تکنیک ۵ سطحی، دائمی (مثل تحقیقات)،
     با LIBER خریداری می‌شه و درصد مشخصی به قدرت کاربر در هر مسابقه
     اضافه می‌کنه (۵٪ تا ۳۰٪). خرید مدال یا رنک مستقیم با پول *نساختم*
     چون این عملاً پرداخت برای رتبه‌ست و رقابت رو بی‌معنی می‌کنه.

  2) «گیفت استارز برای بوست پست» = چون تلگرام API مستقیمی برای این کار
     در دسترس ربات نیست، این یک فرایند ثبت‌سفارش + تاییدِ دستی ادمین
     شده (دقیقاً مثل صف برداشت TON): کاربر لینک پست رو می‌فرسته، لیبرش
     کم می‌شه، سفارش به ادمین می‌ره، ادمین با دکمه «✅ انجام شد» یا
     «❌ رد» جواب می‌ده (رد = لیبر برمی‌گرده).

نحوه‌ی اتصال:

    # main.py → callback_router → زنجیره‌ی fallback:
        if not handled:
            import handlers_competition_boost
            handled = await handlers_competition_boost.boost_callback_router(update, context)

    # main.py → text_message_router → همون زنجیره:
        import handlers_competition_boost
        if await handlers_competition_boost.boost_text_router(update, context):
            return

    # main.py → competition_menu_keyboard() یک ردیف اضافه کن:
        [InlineKeyboardButton("🥋 تکنیک‌های رقابتی", callback_data="technique_menu")],

    # main.py → main_menu_keyboard() یک ردیف اضافه کن (برای گیفت بوست):
        [InlineKeyboardButton("🎁 گیفت استارز (بوست پست)", callback_data="giftboost_menu")],

    # main.py → داخل _player_power(rank_index) در SECTION 4، این تابع رو
    # کمی عوض کن تا user_id هم بگیره و بونوس تکنیک اعمال بشه:
    #
    #     def _player_power(rank_index, user_id=None):
    #         base = 40 + rank_index * 12
    #         power = base + random.randint(-10, 10)
    #         if user_id is not None:
    #             import handlers_competition_boost
    #             bonus_pct = handlers_competition_boost.get_technique_bonus_percent(user_id)
    #             power = round(power * (1 + bonus_pct / 100))
    #         return power
    #
    # و همه‌ی جاهایی که _player_power(profile["rank_index"]) صدا زده می‌شه
    # (داخل _resolve_match) رو به _player_power(profile["rank_index"], user_a)
    # یا user_b تغییر بده تا بونوس واقعاً برای همون کاربر اعمال بشه.

    # admin_panel.py → admin_panel_keyboard() یک ردیف اضافه کن:
        [InlineKeyboardButton("🎁 سفارش‌های گیفت در انتظار", callback_data="admin_pending_giftboost")],
"""
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import (
    get_conn,
    get_user,
    update_balance,
    log_transaction,
    back_keyboard,
    ADMIN_IDS,
)

logger = logging.getLogger("LIBER.competition_boost")

# ============================================================
#   ۱) درخت تکنیک‌های رقابتی (دائمی، افزایش درصدی قدرت)
# ============================================================
TECHNIQUE_TREE = [
    {"name": "🥋 تکنیک پایه‌ی چابکی", "cost": 200, "effect_percent": 5},
    {"name": "🛡 تکنیک دفاعی پیشرفته", "cost": 500, "effect_percent": 10},
    {"name": "⚡ تکنیک حمله‌ی برق‌آسا", "cost": 1000, "effect_percent": 15},
    {"name": "🎯 تکنیک استادی رقابتی", "cost": 2000, "effect_percent": 20},
    {"name": "👑 تکنیک اسطوره‌ای", "cost": 4000, "effect_percent": 30},
]

# ============================================================
#   ۲) گیفت استارز برای بوست پست (پرداخت با LIBER، تایید دستی ادمین)
# ============================================================
GIFT_BOOST_PACKAGES = {
    "single": {"label": "🎁 گیفت تکی", "cost_liber": 1500, "desc": "یک گیفت استارز برای پست شما"},
    "triple": {"label": "🎁🎁🎁 گیفت سه‌تایی", "cost_liber": 2500, "desc": "سه گیفت استارز برای پست شما"},
}

# 🚀 بوست حمایتی کانال (نه بوست پست شخصی کاربر — حمایت از کانال اصلی LIBER)
CHANNEL_BOOST_PACKAGES = {
    "day": {"label": "🚀 بوست ۱ روزه", "cost_liber": 1400, "duration_text": "۱ روز"},
    "month": {"label": "🚀 بوست ۱ ماهه", "cost_liber": 10000, "duration_text": "۱ ماه"},
}


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
        CREATE TABLE IF NOT EXISTS technique_levels (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS giftboost_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_key TEXT NOT NULL,
            cost_liber REAL NOT NULL,
            post_link TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER,
            resolved_by INTEGER
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS channel_boost_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            package_key TEXT NOT NULL,
            cost_liber REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL,
            resolved_at INTEGER,
            resolved_by INTEGER
        )
        """)
    _ready = True


def get_technique_level(user_id):
    _ensure_tables()
    with get_conn() as conn:
        row = conn.execute("SELECT level FROM technique_levels WHERE user_id = ?", (user_id,)).fetchone()
    return row["level"] if row else 0


def get_technique_bonus_percent(user_id):
    """صدا زده می‌شود از main.py داخل _player_power تا بونوس دائمی تکنیک اعمال شود."""
    level = get_technique_level(user_id)
    if level <= 0:
        return 0
    idx = min(level, len(TECHNIQUE_TREE)) - 1
    return TECHNIQUE_TREE[idx]["effect_percent"]


# ============================================================
#   منوی تکنیک‌ها
# ============================================================
def _technique_keyboard(can_upgrade):
    rows = []
    if can_upgrade:
        rows.append([InlineKeyboardButton("⬆️ ارتقای تکنیک", callback_data="technique_upgrade")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="competition_menu")])
    return InlineKeyboardMarkup(rows)


async def technique_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    level = get_technique_level(user_id)

    if level >= len(TECHNIQUE_TREE):
        current_bonus = TECHNIQUE_TREE[-1]["effect_percent"]
        await q.edit_message_text(
            f"🥋 تکنیک‌های رقابتی\n\nهمه‌ی سطوح رو کامل کردی! 🎉\n"
            f"بونوس دائمی فعلی قدرتت: +{current_bonus}٪",
            reply_markup=_technique_keyboard(False),
        )
        return

    info = TECHNIQUE_TREE[level]
    current_bonus = TECHNIQUE_TREE[level - 1]["effect_percent"] if level > 0 else 0
    text = (
        f"🥋 تکنیک‌های رقابتی\n\n"
        f"سطح فعلی: {level} (بونوس دائمی: +{current_bonus}٪ قدرت در هر مسابقه)\n\n"
        f"تکنیک بعدی: {info['name']}\n"
        f"هزینه: {info['cost']} LIBER\n"
        f"بونوس این سطح: +{info['effect_percent']}٪ قدرت (جایگزین بونوس قبلی می‌شه، تجمعی نیست)"
    )
    await q.edit_message_text(text, reply_markup=_technique_keyboard(True))


async def technique_upgrade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    level = get_technique_level(user_id)

    if level >= len(TECHNIQUE_TREE):
        await q.answer("قبلاً تکمیل شده.", show_alert=True)
        return

    info = TECHNIQUE_TREE[level]
    user = get_user(user_id)
    if user["liber"] < info["cost"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {info['cost']}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-info["cost"])
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO technique_levels (user_id, level) VALUES (?, 1)
               ON CONFLICT(user_id) DO UPDATE SET level = level + 1""",
            (user_id,),
        )
    log_transaction(user_id, "TECHNIQUE_UPGRADE", info["name"])

    await q.edit_message_text(
        f"🎉 تکنیک «{info['name']}» فعال شد!\nاز حالا +{info['effect_percent']}٪ قدرت دائمی در مسابقات داری.",
        reply_markup=back_keyboard("competition_menu"),
    )


# ============================================================
#   گیفت استارز برای بوست پست
# ============================================================
def _giftboost_package_keyboard():
    rows = [
        [InlineKeyboardButton(f"{pkg['label']} — {pkg['cost_liber']} LIBER", callback_data=f"giftboost_pick:{key}")]
        for key, pkg in GIFT_BOOST_PACKAGES.items()
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def giftboost_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🎁 گیفت استارز برای بوست پست\n\n"
        "بسته‌ی موردنظر رو انتخاب کن. بعد از انتخاب، لینک پستی که می‌خوای گیفت بگیره رو می‌فرستی.\n"
        "⏳ سفارش برای بررسی ادمین ثبت می‌شه و بعد از تایید، برات انجام می‌شه.",
        reply_markup=_giftboost_package_keyboard(),
    )


async def giftboost_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    package_key = q.data.split(":", 1)[1]
    package = GIFT_BOOST_PACKAGES.get(package_key)
    if not package:
        await q.answer("بسته نامعتبر است.", show_alert=True)
        return

    user = get_user(q.from_user.id)
    if user["liber"] < package["cost_liber"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {package['cost_liber']}", show_alert=True)
        return

    await q.answer()
    context.user_data["giftboost_package"] = package_key
    context.user_data["awaiting"] = "giftboost_link_input"
    await q.edit_message_text(
        f"{package['label']} — {package['cost_liber']} LIBER\n\n"
        "لینک پست موردنظرتون رو بفرستید (مثلاً https://t.me/channel/123):"
    )


async def _do_giftboost_link(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    package_key = context.user_data.pop("giftboost_package", None)
    package = GIFT_BOOST_PACKAGES.get(package_key)
    if not package:
        await update.message.reply_text("❌ بسته گم شد، دوباره از منو شروع کن.", reply_markup=back_keyboard())
        return

    link = raw_text.strip()
    if not link.startswith("http"):
        await update.message.reply_text("❌ لطفاً یک لینک معتبر (با http/https) بفرستید.")
        return

    user = get_user(user_id)
    if user["liber"] < package["cost_liber"]:
        await update.message.reply_text("❌ LIBER کافی نیست.", reply_markup=back_keyboard())
        return

    update_balance(user_id, liber=-package["cost_liber"])
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO giftboost_requests (user_id, package_key, cost_liber, post_link, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, package_key, package["cost_liber"], link, now),
        )
        request_id = cur.lastrowid
    log_transaction(user_id, "GIFTBOOST_REQUEST", f"#{request_id} {package_key}")

    await update.message.reply_text(
        f"✅ سفارش شما ثبت شد و برای بررسی ادمین ارسال گردید.\n"
        f"🎫 کد پیگیری: #{request_id}\n"
        f"⏳ وضعیت: در حال بررسی — به محض انجام، پیام موفقیت برایتان ارسال می‌شود.",
        reply_markup=back_keyboard(),
    )

    from main import post_to_orders_channel
    await post_to_orders_channel(
        context.bot,
        f"📥 سفارش جدید — گیفت استارز\n\n"
        f"🎫 کد پیگیری: #{request_id}\n"
        f"نوع: {package['label']}\n"
        f"مقدار: {package['cost_liber']} LIBER\n"
        f"لینک پست: {link}\n"
        f"وضعیت: ⏳ در حال بررسی",
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🎁 سفارش گیفت بوست جدید #{request_id}\n"
                f"کاربر: {user_id}\n"
                f"بسته: {package['label']} ({package['cost_liber']} LIBER)\n"
                f"لینک پست: {link}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ انجام شد", callback_data=f"admin_gb_done:{request_id}"),
                     InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_gb_reject:{request_id}")],
                ]),
            )
        except TelegramError:
            pass


# ---------------------------------------------------------------
#  تصمیم‌گیری ادمین روی سفارش گیفت
# ---------------------------------------------------------------
async def admin_giftboost_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    admin_id = q.from_user.id
    if admin_id not in ADMIN_IDS:
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return

    action, request_id_str = q.data.split(":")
    request_id = int(request_id_str)
    with get_conn() as conn:
        req = conn.execute("SELECT * FROM giftboost_requests WHERE request_id = ?", (request_id,)).fetchone()

    if not req:
        await q.answer("این سفارش پیدا نشد.", show_alert=True)
        return
    if req["status"] != "pending":
        await q.answer(f"قبلاً «{req['status']}» شده.", show_alert=True)
        return

    await q.answer()
    now = int(time.time())

    if action == "admin_gb_done":
        with get_conn() as conn:
            conn.execute(
                "UPDATE giftboost_requests SET status = 'done', resolved_at = ?, resolved_by = ? WHERE request_id = ?",
                (now, admin_id, request_id),
            )
        await q.edit_message_text(f"✅ سفارش #{request_id} به‌عنوان انجام‌شده ثبت شد.")
        from main import post_to_orders_channel
        await post_to_orders_channel(context.bot, f"✅ سفارش #{request_id} با موفقیت انجام شد.\nنوع: گیفت استارز")
        try:
            await context.bot.send_message(
                req["user_id"], f"🎉 سفارش گیفت شما (#{request_id}) با موفقیت انجام شد! از خرید شما ممنونیم 🙏"
            )
        except TelegramError:
            pass
    else:
        with get_conn() as conn:
            conn.execute(
                "UPDATE giftboost_requests SET status = 'rejected', resolved_at = ?, resolved_by = ? WHERE request_id = ?",
                (now, admin_id, request_id),
            )
        update_balance(req["user_id"], liber=req["cost_liber"])
        await q.edit_message_text(f"❌ سفارش #{request_id} رد شد و {req['cost_liber']} LIBER به کاربر برگشت.")
        from main import post_to_orders_channel
        await post_to_orders_channel(context.bot, f"❌ سفارش #{request_id} لغو شد.\nنوع: گیفت استارز\nمبلغ برگشت داده شد.")
        try:
            await context.bot.send_message(
                req["user_id"],
                f"❌ سفارش گیفت شما (#{request_id}) رد شد و {req['cost_liber']} LIBER به حسابتون برگشت.",
            )
        except TelegramError:
            pass


async def admin_pending_giftboost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برای دکمه‌ی «🎁 سفارش‌های گیفت در انتظار» در پنل ادمین."""
    _ensure_tables()
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS:
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()

    with get_conn() as conn:
        pending = conn.execute(
            "SELECT * FROM giftboost_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT 20"
        ).fetchall()

    if not pending:
        await q.edit_message_text("🎁 هیچ سفارش گیفت در انتظاری نیست.", reply_markup=back_keyboard("admin_panel"))
        return

    await q.edit_message_text(f"🎁 {len(pending)} سفارش در انتظار پیدا شد. یکی‌یکی ارسال می‌شوند...")
    for req in pending:
        package = GIFT_BOOST_PACKAGES.get(req["package_key"], {"label": req["package_key"]})
        text = (
            f"🎁 سفارش گیفت #{req['request_id']}\n\n"
            f"کاربر: {req['user_id']}\n"
            f"بسته: {package['label']} ({req['cost_liber']} LIBER)\n"
            f"لینک: {req['post_link']}"
        )
        try:
            await context.bot.send_message(
                q.from_user.id, text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ انجام شد", callback_data=f"admin_gb_done:{req['request_id']}"),
                     InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_gb_reject:{req['request_id']}")],
                ]),
            )
        except TelegramError:
            pass


# ============================================================
#   🚀 بوست حمایتی کانال (جدا از گیفت‌بوستِ پستِ شخصی کاربر)
# ============================================================
def _channel_boost_keyboard():
    rows = [
        [InlineKeyboardButton(f"{pkg['label']} — {pkg['cost_liber']} LIBER ({pkg['duration_text']})",
                               callback_data=f"channelboost_pick:{key}")]
        for key, pkg in CHANNEL_BOOST_PACKAGES.items()
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def channel_boost_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🚀 حمایت از کانال (بوست)\n\n"
        "با خرید بوست، از کانال اصلی LIBER حمایت می‌کنید و دیده‌شدنش بیشتر می‌شه.\n"
        "یکی از مدت‌ها رو انتخاب کنید:",
        reply_markup=_channel_boost_keyboard(),
    )


async def channel_boost_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    package_key = q.data.split(":", 1)[1]
    package = CHANNEL_BOOST_PACKAGES.get(package_key)
    if not package:
        await q.answer("بسته نامعتبر است.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < package["cost_liber"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {package['cost_liber']}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-package["cost_liber"])
    now = int(time.time())
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO channel_boost_requests (user_id, package_key, cost_liber, created_at)
               VALUES (?, ?, ?, ?)""",
            (user_id, package_key, package["cost_liber"], now),
        )
        request_id = cur.lastrowid
    log_transaction(user_id, "CHANNEL_BOOST_REQUEST", f"#{request_id} {package_key}")

    from main import FORCE_JOIN_CHANNELS, post_to_orders_channel
    channel_link = FORCE_JOIN_CHANNELS[0]["url"] if FORCE_JOIN_CHANNELS else ""

    await q.edit_message_text(
        f"✅ سفارش بوست {package['duration_text']} ثبت شد!\n"
        f"🎫 کد پیگیری: #{request_id}\n\n"
        f"🔗 لینک کانال برای حمایت: {channel_link}\n"
        f"⏳ وضعیت: در حال انجام — به محض فعال شدن بوست، بهتون خبر می‌دیم.",
        reply_markup=back_keyboard(),
    )

    await post_to_orders_channel(
        context.bot,
        f"📥 سفارش جدید — بوست کانال\n\n"
        f"🎫 کد پیگیری: #{request_id}\n"
        f"نوع: {package['label']} ({package['duration_text']})\n"
        f"مقدار: {package['cost_liber']} LIBER\n"
        f"وضعیت: ⏳ در حال انجام",
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"🚀 سفارش بوست کانال جدید #{request_id}\n"
                f"کاربر: {user_id}\n"
                f"بسته: {package['label']} ({package['cost_liber']} LIBER)",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ انجام شد", callback_data=f"admin_cb_done:{request_id}"),
                     InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_cb_reject:{request_id}")],
                ]),
            )
        except TelegramError:
            pass


async def admin_channelboost_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    admin_id = q.from_user.id
    if admin_id not in ADMIN_IDS:
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return

    action, request_id_str = q.data.split(":")
    request_id = int(request_id_str)
    with get_conn() as conn:
        req = conn.execute("SELECT * FROM channel_boost_requests WHERE request_id = ?", (request_id,)).fetchone()

    if not req:
        await q.answer("این سفارش پیدا نشد.", show_alert=True)
        return
    if req["status"] != "pending":
        await q.answer(f"قبلاً «{req['status']}» شده.", show_alert=True)
        return

    await q.answer()
    now = int(time.time())
    from main import post_to_orders_channel

    if action == "admin_cb_done":
        with get_conn() as conn:
            conn.execute(
                "UPDATE channel_boost_requests SET status = 'done', resolved_at = ?, resolved_by = ? WHERE request_id = ?",
                (now, admin_id, request_id),
            )
        await q.edit_message_text(f"✅ سفارش بوست #{request_id} فعال شد.")
        await post_to_orders_channel(context.bot, f"✅ سفارش #{request_id} با موفقیت انجام شد.\nنوع: بوست کانال")
        try:
            await context.bot.send_message(req["user_id"], f"🎉 بوست شما (#{request_id}) فعال شد! ممنون از حمایتتون 🙏")
        except TelegramError:
            pass
    else:
        with get_conn() as conn:
            conn.execute(
                "UPDATE channel_boost_requests SET status = 'rejected', resolved_at = ?, resolved_by = ? WHERE request_id = ?",
                (now, admin_id, request_id),
            )
        update_balance(req["user_id"], liber=req["cost_liber"])
        await q.edit_message_text(f"❌ سفارش بوست #{request_id} رد شد و {req['cost_liber']} LIBER برگشت.")
        await post_to_orders_channel(context.bot, f"❌ سفارش #{request_id} لغو شد.\nنوع: بوست کانال\nمبلغ برگشت داده شد.")
        try:
            await context.bot.send_message(
                req["user_id"], f"❌ سفارش بوست شما (#{request_id}) رد شد و {req['cost_liber']} LIBER برگشت."
            )
        except TelegramError:
            pass


async def admin_pending_channelboost_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """برای دکمه‌ی «🚀 سفارش‌های بوست کانال در انتظار» در پنل ادمین."""
    _ensure_tables()
    q = update.callback_query
    if q.from_user.id not in ADMIN_IDS:
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()

    with get_conn() as conn:
        pending = conn.execute(
            "SELECT * FROM channel_boost_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT 20"
        ).fetchall()

    if not pending:
        await q.edit_message_text("🚀 هیچ سفارش بوست کانالی در انتظار نیست.", reply_markup=back_keyboard("admin_panel"))
        return

    await q.edit_message_text(f"🚀 {len(pending)} سفارش بوست در انتظار پیدا شد. یکی‌یکی ارسال می‌شوند...")
    for req in pending:
        package = CHANNEL_BOOST_PACKAGES.get(req["package_key"], {"label": req["package_key"]})
        text = f"🚀 سفارش بوست #{req['request_id']}\n\nکاربر: {req['user_id']}\nبسته: {package['label']} ({req['cost_liber']} LIBER)"
        try:
            await context.bot.send_message(
                q.from_user.id, text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ انجام شد", callback_data=f"admin_cb_done:{req['request_id']}"),
                     InlineKeyboardButton("❌ رد کردن", callback_data=f"admin_cb_reject:{req['request_id']}")],
                ]),
            )
        except TelegramError:
            pass


# ============================================================
#   دیسپچر
# ============================================================
SIMPLE_CALLBACKS = {
    "channel_boost_menu": channel_boost_menu_callback,
    "admin_pending_channelboost": admin_pending_channelboost_callback,
    "technique_menu": technique_menu_callback,
    "technique_upgrade": technique_upgrade_callback,
    "giftboost_menu": giftboost_menu_callback,
    "admin_pending_giftboost": admin_pending_giftboost_callback,
}


async def boost_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return True
    if data.startswith("giftboost_pick:"):
        await giftboost_pick_callback(update, context)
        return True
    if data.startswith("admin_gb_done:") or data.startswith("admin_gb_reject:"):
        await admin_giftboost_decision_callback(update, context)
        return True
    if data.startswith("channelboost_pick:"):
        await channel_boost_pick_callback(update, context)
        return True
    if data.startswith("admin_cb_done:") or data.startswith("admin_cb_reject:"):
        await admin_channelboost_decision_callback(update, context)
        return True
    return False


async def boost_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "giftboost_link_input":
        context.user_data["awaiting"] = None
        await _do_giftboost_link(update, context, raw_text)
        return True
    return False
