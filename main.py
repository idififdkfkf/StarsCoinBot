# -*- coding: utf-8 -*-
"""
admin_panel.py — پنل مدیریت مستقل ربات LIBER
================================================================
این فایل کاملاً جداست و باید کنار main.py قرار بگیرد. main.py در
لحظه‌ی نیاز (وقتی کاربری با آیدی ادمین وارد بخش مدیریت می‌شود) این
فایل را import می‌کند — نیازی به تغییر main.py برای فعال‌سازی نیست.

شامل:
    • تایید/رد درخواست‌های برداشت TON
    • آمار کلی ربات (کاربران، LIBER در گردش، فصل رقابت)
    • پیام همگانی به همه‌ی کاربران فعال
    • مدیریت بن/رفع‌بن کاربر با آیدی عددی

فعال‌سازی: از دستور مخفی تنظیم‌شده در config.py (ADMIN_SECRET_COMMAND)
یا از دکمه‌ی «👑 پنل مدیریت» که فقط برای ADMIN_IDS در منوی اصلی دیده
می‌شود.
"""
# -*- coding: utf-8 -*-
"""
هندلرهای پنل مدیریت ربات LIBER
شامل: تایید/رد برداشت TON، آمار ربات، پیام همگانی، مدیریت بن کاربر
"""
import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

# همه‌ی این نام‌ها از main.py می‌آیند — چون همان چیزهایی هستند که ربات
# اصلی هم برای دیتابیس، دکمه‌ها و تنظیمات استفاده می‌کند. هیچ کد یا
# جدولی دوباره اینجا تعریف نمی‌شود؛ فقط استفاده از همان چیزهای موجود.
from main import (
    ADMIN_IDS,
    SUBSCRIPTION_TIERS,
    get_user,
    get_market_price,
    get_comp_season,
    get_stats,
    all_user_ids,
    set_ban,
    update_balance,
    log_transaction,
    grant_subscription,
    list_pending_withdrawals,
    get_withdraw_request,
    approve_withdraw_request,
    reject_withdraw_request,
    admin_panel_keyboard,
    admin_withdraw_review_keyboard,
    admin_grant_sub_tier_keyboard,
    admin_grant_sub_months_keyboard,
    admin_grant_sub_target_keyboard,
    back_keyboard,
)

logger = logging.getLogger("LIBER.admin")


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ---------------------------------------------------------------
#  ورود به پنل
# ---------------------------------------------------------------
async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    await q.edit_message_text("👑 پنل مدیریت LIBER", reply_markup=admin_panel_keyboard())


# ---------------------------------------------------------------
#  درخواست‌های برداشت در انتظار
# ---------------------------------------------------------------
async def admin_pending_withdraws_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()

    pending = list_pending_withdrawals(20)
    if not pending:
        await q.edit_message_text("📤 هیچ درخواست برداشت در انتظاری وجود ندارد.", reply_markup=admin_panel_keyboard())
        return

    await q.edit_message_text(f"📤 {len(pending)} درخواست در انتظار پیدا شد. یکی‌یکی ارسال می‌شوند...")
    for req in pending:
        u = get_user(req["user_id"])
        name = u["first_name"] if u else str(req["user_id"])
        text = (
            f"📥 درخواست برداشت #{req['request_id']}\n\n"
            f"👤 کاربر: {name} (ID: {req['user_id']})\n"
            f"📦 مقدار: {req['liber_amount']} LIBER\n"
            f"💰 کارمزد: {req['fee']} LIBER\n"
            f"💎 معادل: {req['ton_amount']} TON\n"
            f"👛 آدرس: {req['wallet_address']}"
        )
        try:
            await context.bot.send_message(
                q.from_user.id, text, reply_markup=admin_withdraw_review_keyboard(req["request_id"])
            )
        except TelegramError:
            pass


async def admin_withdraw_decision_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    admin_id = q.from_user.id
    if not is_admin(admin_id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()

    action, request_id_str = q.data.split(":")
    request_id = int(request_id_str)
    req = get_withdraw_request(request_id)

    if not req:
        await q.edit_message_text("این درخواست پیدا نشد.")
        return
    if req["status"] != "pending":
        await q.edit_message_text(f"این درخواست قبلاً «{req['status']}» شده است.")
        return

    if action == "admin_wd_approve":
        approve_withdraw_request(request_id, admin_id)
        await q.edit_message_text(f"✅ درخواست #{request_id} تایید شد.")
        try:
            await context.bot.send_message(
                req["user_id"],
                "🎉 برداشت شما با موفقیت انجام شد!\n"
                f"💎 مبلغ {req['ton_amount']} TON به آدرس شما ارسال گردید.\nممنون از استفاده‌ی شما 🙏",
            )
        except TelegramError:
            pass

    elif action == "admin_wd_reject":
        reject_withdraw_request(request_id, admin_id)
        await q.edit_message_text(f"❌ درخواست #{request_id} رد شد و LIBER به کاربر برگشت.")
        try:
            await context.bot.send_message(
                req["user_id"],
                f"❌ درخواست برداشت شما (#{request_id}) رد شد و {req['liber_amount']} LIBER به حساب شما بازگشت.",
            )
        except TelegramError:
            pass


# ---------------------------------------------------------------
#  آمار
# ---------------------------------------------------------------
async def admin_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    stats = get_stats()
    price = get_market_price()
    season = get_comp_season()
    text = (
        f"📊 آمار ربات\n\n"
        f"👥 کل کاربران: {stats['total_users']}\n"
        f"🚫 مسدودشده: {stats['banned']}\n"
        f"🔷 مجموع LIBER در گردش: {stats['total_liber']}\n"
        f"📤 درخواست برداشت در انتظار: {stats['pending_withdraws']}\n"
        f"💹 قیمت بازار: {price}\n"
        f"📆 فصل رقابت: {season['season_number']}"
    )
    await q.edit_message_text(text, reply_markup=admin_panel_keyboard())


# ---------------------------------------------------------------
#  پیام همگانی
# ---------------------------------------------------------------
async def admin_broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting_admin"] = "broadcast_text"
    await q.edit_message_text(
        "📢 متن پیام همگانی را ارسال کنید (به همه‌ی کاربران فعال ارسال می‌شود):",
        reply_markup=back_keyboard("admin_panel"),
    )


async def _do_broadcast(update, context, text):
    admin_id = update.effective_user.id
    ids = all_user_ids()
    sent, failed = 0, 0
    for uid in ids:
        try:
            await context.bot.send_message(uid, f"📢 {text}")
            sent += 1
        except TelegramError:
            failed += 1
    await update.message.reply_text(f"✅ ارسال شد به {sent} کاربر. ({failed} ناموفق)", reply_markup=admin_panel_keyboard())


# ---------------------------------------------------------------
#  مدیریت بن
# ---------------------------------------------------------------
# ---------------------------------------------------------------
#  افزودن سکه/لیبر به کاربر
# ---------------------------------------------------------------
async def admin_give_currency_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting_admin"] = "give_currency_input"
    await q.edit_message_text(
        "💰 افزودن سکه/لیبر به کاربر\n\n"
        "به این شکل ارسال کنید (فاصله‌جدا):\n"
        "آیدی_عددی مقدار_سکه مقدار_لیبر\n\n"
        "مثال: 123456789 500 20\n"
        "(اگر نخواستید یکی رو اضافه کنید، عدد 0 بذارید)",
        reply_markup=back_keyboard("admin_panel"),
    )


async def _do_give_currency(update, context, raw_text):
    parts = raw_text.split()
    if len(parts) != 3:
        await update.message.reply_text("❌ فرمت اشتباه. مثال: 123456789 500 20")
        return
    try:
        target_id, coin_amount, liber_amount = int(parts[0]), float(parts[1]), float(parts[2])
    except ValueError:
        await update.message.reply_text("❌ مقادیر باید عددی باشند.")
        return

    user = get_user(target_id)
    if not user:
        await update.message.reply_text("❌ کاربری با این آیدی پیدا نشد.")
        return

    update_balance(target_id, coin=coin_amount, liber=liber_amount)
    log_transaction(target_id, "ADMIN_GIVE_CURRENCY", f"coin={coin_amount} liber={liber_amount}")
    await update.message.reply_text(
        f"✅ به کاربر {target_id} اضافه شد: +{coin_amount} سکه, +{liber_amount} LIBER",
        reply_markup=admin_panel_keyboard(),
    )
    try:
        await context.bot.send_message(
            target_id, f"🎁 ادمین به حساب شما اضافه کرد: +{coin_amount} سکه, +{liber_amount} LIBER"
        )
    except TelegramError:
        pass


# ---------------------------------------------------------------
#  فعال‌سازی دستی اشتراک
# ---------------------------------------------------------------
async def admin_grant_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    await q.edit_message_text(
        "🎫 فعال‌سازی دستی اشتراک — اول تعرفه رو انتخاب کن:",
        reply_markup=admin_grant_sub_tier_keyboard(),
    )


async def admin_grant_sub_tier_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    tier_key = q.data.split(":", 1)[1]
    await q.edit_message_text(
        "⏳ حالا مدت اشتراک رو انتخاب کن:",
        reply_markup=admin_grant_sub_months_keyboard(tier_key),
    )


async def admin_grant_sub_months_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    _, tier_key, months = q.data.split(":")
    context.user_data["grant_sub_tier"] = tier_key
    context.user_data["grant_sub_months"] = int(months)
    await q.edit_message_text(
        "برای چه کسی فعال بشه؟",
        reply_markup=admin_grant_sub_target_keyboard(),
    )


async def admin_grant_sub_self_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    await _apply_grant_subscription(update, context, q.from_user.id, notify=False, via_callback=True)


async def admin_grant_sub_other_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting_admin"] = "grant_sub_user_id"
    await q.edit_message_text("آیدی عددی کاربری که می‌خواهید اشتراکش رو فعال کنید را ارسال کنید:")


async def _apply_grant_subscription(update, context, target_id, notify=True, via_callback=False):
    user = get_user(target_id)
    if not user:
        text = "❌ کاربری با این آیدی پیدا نشد."
        if via_callback:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    tier_key = context.user_data.pop("grant_sub_tier", None)
    months = context.user_data.pop("grant_sub_months", None)
    if not tier_key or not months:
        text = "❌ اطلاعات تعرفه گم شده، دوباره از منو شروع کنید."
        if via_callback:
            await update.callback_query.edit_message_text(text)
        else:
            await update.message.reply_text(text)
        return

    tier = SUBSCRIPTION_TIERS[tier_key]
    grant_subscription(target_id, tier_key, months, 0, "ADMIN_MANUAL_GRANT")
    success_text = f"✅ {tier['title']} برای کاربر {target_id} به مدت {months} ماه فعال شد."

    if via_callback:
        await update.callback_query.edit_message_text(success_text, reply_markup=admin_panel_keyboard())
    else:
        await update.message.reply_text(success_text, reply_markup=admin_panel_keyboard())

    if notify:
        try:
            await context.bot.send_message(
                target_id,
                f"🎉 ادمین برای شما {tier['title']} به مدت {months} ماه فعال کرد!\nاز منو لذت ببرید 🥂",
            )
        except TelegramError:
            pass


async def _do_grant_subscription(update, context, raw_text):
    try:
        target_id = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return
    await _apply_grant_subscription(update, context, target_id, notify=True, via_callback=False)


async def admin_user_manage_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not is_admin(q.from_user.id):
        await q.answer("⛔ دسترسی غیرمجاز.", show_alert=True)
        return
    await q.answer()
    context.user_data["awaiting_admin"] = "ban_toggle_id"
    await q.edit_message_text(
        "🚫 آیدی عددی کاربری که می‌خواهید بن/رفع‌بن کنید را ارسال کنید:",
        reply_markup=back_keyboard("admin_panel"),
    )


async def _do_ban_toggle(update, context, raw_text):
    try:
        target_id = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return
    user = get_user(target_id)
    if not user:
        await update.message.reply_text("❌ کاربری با این آیدی پیدا نشد.")
        return
    new_status = not bool(user["is_banned"])
    set_ban(target_id, new_status)
    status_text = "مسدود" if new_status else "رفع مسدودیت"
    await update.message.reply_text(f"✅ کاربر {target_id} {status_text} شد.", reply_markup=admin_panel_keyboard())


# ---------------------------------------------------------------
#  روتر پیام‌های متنی ادمین (broadcast / ban)
# ---------------------------------------------------------------
async def admin_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """اگر پیام متنی مربوط به یک مرحله‌ی ادمین باشد پردازش می‌کند و True برمی‌گرداند."""
    if not is_admin(update.effective_user.id):
        return False

    awaiting = context.user_data.get("awaiting_admin")
    if not awaiting:
        return False

    context.user_data["awaiting_admin"] = None
    raw_text = update.message.text.strip()

    if awaiting == "broadcast_text":
        await _do_broadcast(update, context, raw_text)
        return True
    if awaiting == "ban_toggle_id":
        await _do_ban_toggle(update, context, raw_text)
        return True
    if awaiting == "give_currency_input":
        await _do_give_currency(update, context, raw_text)
        return True
    if awaiting == "grant_sub_user_id":
        await _do_grant_subscription(update, context, raw_text)
        return True
    return False


# ---------------------------------------------------------------
#  دیسپچر کال‌بک‌های ادمین
# ---------------------------------------------------------------
ADMIN_CALLBACKS = {
    "admin_panel": admin_panel_callback,
    "admin_pending_withdraws": admin_pending_withdraws_callback,
    "admin_stats": admin_stats_callback,
    "admin_broadcast": admin_broadcast_callback,
    "admin_user_manage": admin_user_manage_callback,
    "admin_give_currency": admin_give_currency_callback,
    "admin_grant_sub": admin_grant_sub_callback,
}


async def admin_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data

    if data in ADMIN_CALLBACKS:
        await ADMIN_CALLBACKS[data](update, context)
        return

    if data.startswith("admin_wd_approve:") or data.startswith("admin_wd_reject:"):
        await admin_withdraw_decision_callback(update, context)
        return

    if data.startswith("admin_gsub_tier:"):
        await admin_grant_sub_tier_callback(update, context)
        return

    if data.startswith("admin_gsub_months:"):
        await admin_grant_sub_months_callback(update, context)
        return

    if data == "admin_gsub_self":
        await admin_grant_sub_self_callback(update, context)
        return

    if data == "admin_gsub_other":
        await admin_grant_sub_other_callback(update, context)
        return
