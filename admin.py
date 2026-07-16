"""
LIBER - Admin Panel Module (standalone, importable)
-----------------------------------------------------
Drop this file next to main.py. It manages its own SQLite connection to the
same database file, so it works independently of main.py's internals.

Integration (add these 2 lines in main.py):

    import admin
    admin.register_admin_handlers(app, admin_ids=ADMIN_IDS, db_path=DB_PATH)

Everything here is entertainment/virtual-economy only — no real payments,
no blockchain transactions. All numbers are in-game currency.
"""

import sqlite3
import logging
from datetime import datetime
from contextlib import closing

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logger = logging.getLogger("liber.admin")

# ---------------------------------------------------------------------------
# Module-level config (set by register_admin_handlers)
# ---------------------------------------------------------------------------

_ADMIN_IDS = []
_DB_PATH = "liber.db"


def _get_conn():
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _is_admin(user_id: int) -> bool:
    return user_id in _ADMIN_IDS


def _log(user_id: int, action: str, detail: str = ""):
    try:
        with closing(_get_conn()) as conn, conn:
            conn.execute(
                "INSERT INTO logs (user_id, action, detail, created_at) VALUES (?, ?, ?, ?)",
                (user_id, action, detail, datetime.utcnow().isoformat()),
            )
    except sqlite3.OperationalError:
        pass  # logs table may not exist yet if main.py hasn't initialized the DB


# ---------------------------------------------------------------------------
# Keyboards
# ---------------------------------------------------------------------------

def admin_panel_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 داشبورد زنده", callback_data="adm_dashboard"),
         InlineKeyboardButton("👥 کاربران", callback_data="adm_users"),
         InlineKeyboardButton("💹 اقتصاد", callback_data="adm_economy")],
        [InlineKeyboardButton("🚫 بن کاربر", callback_data="adm_ban_info"),
         InlineKeyboardButton("✅ آن‌بن کاربر", callback_data="adm_unban_info"),
         InlineKeyboardButton("📢 پیام همگانی", callback_data="adm_broadcast_info")],
        [InlineKeyboardButton("🎁 ساخت کد هدیه", callback_data="adm_gift_info"),
         InlineKeyboardButton("📋 لاگ‌ها", callback_data="adm_logs"),
         InlineKeyboardButton("🔄 بروزرسانی", callback_data="adm_dashboard")],
    ])


# ---------------------------------------------------------------------------
# Dashboard text builders
# ---------------------------------------------------------------------------

def _build_dashboard_text() -> str:
    now = datetime.utcnow()
    server_time = now.strftime("%Y-%m-%d %H:%M:%S UTC")

    with closing(_get_conn()) as conn:
        try:
            total_users = conn.execute("SELECT COUNT(*) c FROM users").fetchone()["c"]
        except sqlite3.OperationalError:
            total_users = 0
        try:
            banned = conn.execute("SELECT COUNT(*) c FROM users WHERE banned = 1").fetchone()["c"]
        except sqlite3.OperationalError:
            banned = 0
        try:
            total_liber = conn.execute("SELECT COALESCE(SUM(liber),0) s FROM users").fetchone()["s"]
            total_coin = conn.execute("SELECT COALESCE(SUM(coin),0) s FROM users").fetchone()["s"]
        except sqlite3.OperationalError:
            total_liber = total_coin = 0
        try:
            price_row = conn.execute("SELECT price FROM market ORDER BY id DESC LIMIT 1").fetchone()
            price = price_row["price"] if price_row else 0
        except sqlite3.OperationalError:
            price = 0
        try:
            countries = conn.execute("SELECT COUNT(*) c FROM countries").fetchone()["c"]
        except sqlite3.OperationalError:
            countries = 0
        try:
            cheat_flags = conn.execute("SELECT COUNT(*) c FROM cheat_flags WHERE flag_count > 0").fetchone()["c"]
        except sqlite3.OperationalError:
            cheat_flags = 0

    return (
        "👑 پنل مدیریت LIBER\n"
        "━━━━━━━━━━━━━━━━\n"
        f"🕒 زمان سرور (لحظه‌ای): {server_time}\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🚫 کاربران مسدود: {banned}\n"
        f"⚠️ کاربران دارای اخطار تقلب: {cheat_flags}\n"
        "━━━━━━━━━━━━━━━━\n"
        f"📈 قیمت بازار فعلی: {price:.4f}\n"
        f"🪙 مجموع LIBER در گردش: {total_liber:.2f}\n"
        f"💵 مجموع Coin در گردش: {total_coin:.2f}\n"
        f"🌍 کشورهای ساخته‌شده: {countries}\n"
        "━━━━━━━━━━━━━━━━\n"
        "این پنل هر بار که «بروزرسانی» رو بزنی، لحظه‌ای رفرش می‌شه."
    )


def _build_users_text(limit: int = 15) -> str:
    with closing(_get_conn()) as conn:
        try:
            rows = conn.execute(
                "SELECT user_id, first_name, level, liber, banned FROM users ORDER BY joined_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return "جدول کاربران هنوز ساخته نشده."

    if not rows:
        return "هیچ کاربری ثبت نشده."

    text = "👥 آخرین کاربران\n\n"
    for r in rows:
        status = "🚫" if r["banned"] else "✅"
        text += f"{status} {r['first_name']} (ID: {r['user_id']}) — سطح {r['level']} — {r['liber']:.0f} LIBER\n"
    return text


def _build_logs_text(limit: int = 12) -> str:
    with closing(_get_conn()) as conn:
        try:
            rows = conn.execute(
                "SELECT user_id, action, detail, created_at FROM logs ORDER BY log_id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        except sqlite3.OperationalError:
            return "جدول لاگ‌ها هنوز ساخته نشده."

    if not rows:
        return "لاگی ثبت نشده."

    text = "📋 آخرین لاگ‌های سیستم\n\n"
    for r in rows:
        text += f"[{r['created_at'][:16]}] {r['user_id']} — {r['action']} {r['detail']}\n"
    return text


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")
        return
    await update.message.reply_text(_build_dashboard_text(), reply_markup=admin_panel_keyboard())


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /ban USER_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("آیدی نامعتبر.")
        return
    with closing(_get_conn()) as conn, conn:
        conn.execute("UPDATE users SET banned = 1 WHERE user_id = ?", (target_id,))
    _log(user_id, "ADMIN_BAN", f"target={target_id}")
    await update.message.reply_text(f"🚫 کاربر {target_id} مسدود شد.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /unban USER_ID")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("آیدی نامعتبر.")
        return
    with closing(_get_conn()) as conn, conn:
        conn.execute("UPDATE users SET banned = 0 WHERE user_id = ?", (target_id,))
    _log(user_id, "ADMIN_UNBAN", f"target={target_id}")
    await update.message.reply_text(f"✅ کاربر {target_id} آن‌بن شد.")


async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن پیام")
        return
    message_text = " ".join(context.args)

    with closing(_get_conn()) as conn:
        try:
            rows = conn.execute("SELECT user_id FROM users WHERE banned = 0").fetchall()
        except sqlite3.OperationalError:
            rows = []

    sent, failed = 0, 0
    for row in rows:
        try:
            await context.bot.send_message(row["user_id"], f"📢 {message_text}")
            sent += 1
        except Exception:
            failed += 1

    _log(user_id, "ADMIN_BROADCAST", message_text)
    await update.message.reply_text(f"✅ ارسال شد به {sent} کاربر. ({failed} ناموفق)")


async def creategift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin creates a virtual gift code redeemable via /gift in main.py."""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return
    if len(context.args) < 3:
        await update.message.reply_text("استفاده: /creategift کد مقدار_LIBER تعداد_استفاده")
        return

    code = context.args[0].strip().upper()
    try:
        reward = float(context.args[1])
        max_uses = int(context.args[2])
    except ValueError:
        await update.message.reply_text("مقادیر نامعتبر.")
        return

    try:
        with closing(_get_conn()) as conn, conn:
            conn.execute(
                "INSERT INTO gift_codes (code, reward_liber, max_uses, created_at) VALUES (?, ?, ?, ?)",
                (code, reward, max_uses, datetime.utcnow().isoformat()),
            )
    except sqlite3.IntegrityError:
        await update.message.reply_text("این کد قبلاً وجود داره.")
        return
    except sqlite3.OperationalError:
        await update.message.reply_text("جدول کد هدیه هنوز ساخته نشده (main.py رو اول اجرا کن).")
        return

    _log(user_id, "ADMIN_CREATE_GIFT", code)
    await update.message.reply_text(f"✅ کد هدیه «{code}» ساخته شد: {reward} LIBER × {max_uses} استفاده")


async def globalgift_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Instantly gives every non-banned user a virtual LIBER amount — a fun admin perk."""
    user_id = update.effective_user.id
    if not _is_admin(user_id):
        return
    if not context.args:
        await update.message.reply_text("استفاده: /globalgift مقدار_LIBER")
        return
    try:
        amount = float(context.args[0])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر.")
        return

    with closing(_get_conn()) as conn, conn:
        conn.execute("UPDATE users SET liber = liber + ? WHERE banned = 0", (amount,))
        count = conn.execute("SELECT COUNT(*) c FROM users WHERE banned = 0").fetchone()["c"]

    _log(user_id, "ADMIN_GLOBAL_GIFT", f"amount={amount}")

    for row in _get_active_user_ids():
        try:
            await context.bot.send_message(row, f"🎉 هدیه‌ی همگانی از طرف مدیریت: +{amount:.0f} LIBER به حسابت اضافه شد!")
        except Exception:
            pass

    await update.message.reply_text(f"✅ به {count} کاربر فعال، {amount:.0f} LIBER هدیه داده شد.")


def _get_active_user_ids():
    with closing(_get_conn()) as conn:
        try:
            rows = conn.execute("SELECT user_id FROM users WHERE banned = 0").fetchall()
        except sqlite3.OperationalError:
            return []
    return [r["user_id"] for r in rows]


# ---------------------------------------------------------------------------
# Callback handler (buttons)
# ---------------------------------------------------------------------------

async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not _is_admin(user_id):
        await query.answer("⛔ دسترسی غیرمجاز", show_alert=True)
        return

    await query.answer()
    action = query.data

    if action == "adm_dashboard":
        await query.edit_message_text(_build_dashboard_text(), reply_markup=admin_panel_keyboard())
    elif action == "adm_users":
        await query.edit_message_text(_build_users_text(), reply_markup=admin_panel_keyboard())
    elif action == "adm_economy":
        with closing(_get_conn()) as conn:
            try:
                rows = conn.execute(
                    "SELECT price, updated_at FROM market ORDER BY id DESC LIMIT 10"
                ).fetchall()
            except sqlite3.OperationalError:
                rows = []
        text = "💹 آخرین تغییرات قیمت بازار\n\n" + "\n".join(
            f"{r['price']:.4f} — {r['updated_at'][:16]}" for r in rows
        ) if rows else "داده‌ای موجود نیست."
        await query.edit_message_text(text, reply_markup=admin_panel_keyboard())
    elif action == "adm_logs":
        await query.edit_message_text(_build_logs_text(), reply_markup=admin_panel_keyboard())
    elif action == "adm_ban_info":
        await query.edit_message_text(
            "🚫 برای مسدود کردن یک کاربر:\n/ban USER_ID", reply_markup=admin_panel_keyboard()
        )
    elif action == "adm_unban_info":
        await query.edit_message_text(
            "✅ برای رفع مسدودی یک کاربر:\n/unban USER_ID", reply_markup=admin_panel_keyboard()
        )
    elif action == "adm_broadcast_info":
        await query.edit_message_text(
            "📢 برای پیام همگانی:\n/broadcast متن پیام\n\n"
            "🎉 برای هدیه‌ی همگانی LIBER:\n/globalgift مقدار",
            reply_markup=admin_panel_keyboard(),
        )
    elif action == "adm_gift_info":
        await query.edit_message_text(
            "🎁 برای ساخت کد هدیه:\n/creategift کد مقدار_LIBER تعداد_استفاده\n\n"
            "مثال: /creategift WELCOME2026 100 500",
            reply_markup=admin_panel_keyboard(),
        )


# ---------------------------------------------------------------------------
# Registration entrypoint — call this once from main.py
# ---------------------------------------------------------------------------

def register_admin_handlers(app: Application, admin_ids: list, db_path: str = "liber.db"):
    """Wire up the standalone admin panel. Call from main.py after building Application:

        import admin
        admin.register_admin_handlers(app, admin_ids=ADMIN_IDS, db_path=DB_PATH)
    """
    global _ADMIN_IDS, _DB_PATH
    _ADMIN_IDS = admin_ids
    _DB_PATH = db_path

    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("creategift", creategift_command))
    app.add_handler(CommandHandler("globalgift", globalgift_command))
    app.add_handler(CallbackQueryHandler(admin_callback, pattern="^adm_"))

    logger.info("Admin panel registered for %d admin(s).", len(admin_ids))
