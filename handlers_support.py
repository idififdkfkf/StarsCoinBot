# -*- coding: utf-8 -*-
"""
handlers_support.py — پارت ۵ از بسته‌ی توسعه‌ی LIBER
================================================================
شامل:

    🔎 پیگیری سفارش با کد     کاربر کد پیگیری (شماره‌ی درخواست) رو می‌ده،
                             وضعیت (در حال بررسی / انجام‌شده / رد‌شده) رو می‌بینه.
    📞 تماس با پشتیبانی       پیام آزاد کاربر مستقیم به ادمین فوروارد می‌شه.
    🔗 تکمیل جریان تایید برداشت  وقتی ادمین «✅ قبول» رو می‌زنه، ازش لینک تراکنش
                             TON خواسته می‌شه؛ بعد این لینک تو پیام موفقیت کاربر
                             (همراه با کد پیگیری) نشون داده می‌شه.

⚙️ فرض‌های گرفته‌شده:
  • «کد پیگیری» دقیقاً همون شماره‌ی #request_id درخواست برداشت/گیفت‌بوسته —
    چیز جدیدی ساخته نشده، فقط بهش این اسم داده شده چون قابل‌فهم‌تره.
  • اگه ادمین به‌جای لینک، فقط عبارت «رد کن» یا «-» بفرسته، برداشت بدون لینک
    (فقط با تایید متنی) نهایی می‌شه — یعنی گذاشتن لینک اجباری نیست.

نحوه‌ی اتصال:

    # main.py → callback_router و text_message_router → همون زنجیره‌ی همیشگی:
        import handlers_support
        handled = await handlers_support.support_callback_router(update, context)
        # و
        if await handlers_support.support_text_router(update, context): return

    # main.py → main_menu_keyboard() این ردیف رو اضافه کن:
        [InlineKeyboardButton("🔎 پیگیری سفارش", callback_data="track_order_start"),
         InlineKeyboardButton("📞 تماس با پشتیبانی", callback_data="support_contact_start")],

    # admin_panel.py → admin_withdraw_decision_callback باید جایگزین بشه با نسخه‌ی
    # زیر (که در همین فایل به‌عنوان admin_withdraw_decision_callback_v2 هست) —
    # یا ساده‌تر: در admin_panel.py داخل admin_text_router، این را اضافه کن تا
    # مرحله‌ی «لینک تراکنش» رو بگیره:
        if awaiting.startswith("withdraw_tx_link:"):
            import handlers_support
            request_id = int(awaiting.split(":", 1)[1])
            await handlers_support.finalize_withdraw_approval(update, context, request_id)
            return True
"""
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import get_conn, get_user, ADMIN_IDS, back_keyboard, approve_withdraw_request, get_withdraw_request

logger = logging.getLogger("LIBER.support")

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
        CREATE TABLE IF NOT EXISTS withdraw_tx_links (
            request_id INTEGER PRIMARY KEY,
            tx_link TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS support_messages (
            message_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """)
    _ready = True


# ============================================================
#   ۱) پیگیری سفارش با کد پیگیری
# ============================================================
STATUS_LABELS = {
    "pending": "⏳ در حال بررسی توسط ادمین",
    "approved": "✅ با موفقیت انجام شد",
    "done": "✅ با موفقیت انجام شد",
    "rejected": "❌ رد شد (مبلغ به حسابتون برگشت داده شده)",
}


async def track_order_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "track_order_code_input"
    await q.edit_message_text("🔎 کد پیگیری سفارشت (فقط شماره، مثلاً 12) رو بفرست:")


async def _do_track_order(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    try:
        request_id = int(raw_text.strip().lstrip("#"))
    except ValueError:
        await update.message.reply_text("❌ کد پیگیری باید یک عدد باشه (مثلاً 12).")
        return

    # اول تو درخواست‌های برداشت TON می‌گردیم
    wd = get_withdraw_request(request_id)
    if wd and wd["user_id"] == user_id:
        status_label = STATUS_LABELS.get(wd["status"], wd["status"])
        with get_conn() as conn:
            link_row = conn.execute(
                "SELECT tx_link FROM withdraw_tx_links WHERE request_id = ?", (request_id,)
            ).fetchone()
        link_note = f"\n🔗 لینک تراکنش: {link_row['tx_link']}" if link_row and link_row["tx_link"] else ""
        text = (
            f"🎫 کد پیگیری #{request_id} — برداشت TON\n\n"
            f"وضعیت: {status_label}\n"
            f"مقدار: {wd['liber_amount']} LIBER (≈ {wd['ton_amount']} TON)\n"
            f"آدرس: {wd['wallet_address']}{link_note}"
        )
        await update.message.reply_text(text, reply_markup=back_keyboard())
        return

    # بعد تو سفارش‌های گیفت‌بوست می‌گردیم
    try:
        import handlers_competition_boost as hcb
        with get_conn() as conn:
            gb = conn.execute(
                "SELECT * FROM giftboost_requests WHERE request_id = ?", (request_id,)
            ).fetchone()
        if gb and gb["user_id"] == user_id:
            status_map = {"pending": "pending", "done": "done", "rejected": "rejected"}
            status_label = STATUS_LABELS.get(status_map.get(gb["status"], gb["status"]), gb["status"])
            package = hcb.GIFT_BOOST_PACKAGES.get(gb["package_key"], {"label": gb["package_key"]})
            text = (
                f"🎫 کد پیگیری #{request_id} — گیفت استارز\n\n"
                f"وضعیت: {status_label}\n"
                f"بسته: {package['label']}\n"
                f"لینک پست: {gb['post_link']}"
            )
            await update.message.reply_text(text, reply_markup=back_keyboard())
            return
    except Exception:
        pass

    await update.message.reply_text(
        "❌ سفارشی با این کد پیگیری برای شما پیدا نشد. لطفاً شماره رو دوباره چک کن.",
        reply_markup=back_keyboard(),
    )


# ============================================================
#   ۲) تماس با پشتیبانی
# ============================================================
async def support_contact_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "support_message_input"
    await q.edit_message_text("📞 پیام خودتون رو برای پشتیبانی بفرستید:")


async def _do_support_message(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    message = raw_text.strip()[:1000]
    if not message:
        await update.message.reply_text("❌ پیام خالیه، دوباره بفرست.")
        return

    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO support_messages (user_id, message, created_at) VALUES (?, ?, ?)",
            (user_id, message, now),
        )

    user = get_user(user_id)
    user_name = user["first_name"] if user else str(user_id)

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                admin_id,
                f"📞 پیام پشتیبانی جدید\n\n👤 از: {user_name} (ID: {user_id})\n\n💬 {message}",
            )
        except TelegramError:
            pass

    await update.message.reply_text("✅ پیام شما ارسال شد، ممنون از همراهی شما 🙏", reply_markup=back_keyboard())


# ============================================================
#   ۳) تکمیل جریان تایید برداشت (لینک تراکنش)
# ============================================================
async def start_withdraw_tx_link_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, request_id: int):
    """صدا زده می‌شود از admin_panel.py وقتی ادمین دکمه‌ی «✅ قبول» رو می‌زنه —
    به‌جای نهایی‌کردن فوری، اول لینک تراکنش رو می‌خواد.
    توجه: q.answer() اینجا صدا زده نمی‌شه چون caller (admin_withdraw_decision_callback)
    از قبل یک‌بار q.answer() رو صدا زده — صدا زدن دوباره باعث خطای BadRequest می‌شه."""
    q = update.callback_query
    context.user_data["awaiting_admin"] = f"withdraw_tx_link:{request_id}"
    await q.edit_message_text(
        f"🔗 لینک تراکنش TON برای درخواست #{request_id} رو بفرست\n"
        "(یا فقط بنویس «-» اگه نمی‌خوای لینکی بذاری، فقط تایید می‌شه):"
    )


async def finalize_withdraw_approval(update, context, request_id):
    """صدا زده می‌شود از admin_panel.py بعد از اینکه ادمین لینک تراکنش رو فرستاد."""
    _ensure_tables()
    admin_id = update.effective_user.id
    raw_text = update.message.text.strip()
    tx_link = None if raw_text in ("-", "رد کن", "بدون لینک") else raw_text

    req = get_withdraw_request(request_id)
    if not req:
        await update.message.reply_text("❌ این درخواست دیگه پیدا نشد.")
        return
    if req["status"] != "pending":
        await update.message.reply_text(f"این درخواست قبلاً «{req['status']}» شده.")
        return

    approve_withdraw_request(request_id, admin_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO withdraw_tx_links (request_id, tx_link) VALUES (?, ?)",
            (request_id, tx_link),
        )

    link_note = f"\n🔗 لینک تراکنش: {tx_link}" if tx_link else ""
    await update.message.reply_text(f"✅ درخواست #{request_id} تایید و نهایی شد.")

    from main import post_to_orders_channel
    await post_to_orders_channel(
        context.bot,
        f"✅ سفارش #{request_id} با موفقیت انجام شد.\n"
        f"نوع: برداشت TON{link_note}",
    )

    try:
        await context.bot.send_message(
            req["user_id"],
            f"🎉 برداشت شما با موفقیت انجام شد!\n"
            f"💎 مبلغ {req['ton_amount']} TON ارسال گردید.{link_note}\n"
            f"🎫 کد پیگیری: #{request_id}\n\n"
            "اگه سوالی داشتید، از «🔎 پیگیری سفارش» یا «📞 تماس با پشتیبانی» استفاده کنید.\n"
            "ممنون از همراهی شما 🙏",
        )
    except TelegramError:
        pass


# ============================================================
#   دیسپچر
# ============================================================
SIMPLE_CALLBACKS = {
    "track_order_start": track_order_start_callback,
    "support_contact_start": support_contact_start_callback,
}


async def support_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return True
    return False


async def support_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "track_order_code_input":
        context.user_data["awaiting"] = None
        await _do_track_order(update, context, raw_text)
        return True
    if awaiting == "support_message_input":
        context.user_data["awaiting"] = None
        await _do_support_message(update, context, raw_text)
        return True
    return False
