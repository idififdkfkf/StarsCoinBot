"""
LIBER — admin.py
==================
Separate admin-only control panel. Imports shared state and helpers from
main.py (db, save_data, ADMIN_IDS, etc.) rather than duplicating them.

Nothing in this file is visible or reachable by non-admin users: every
handler checks is_admin() first and silently (or politely) refuses
otherwise. The admin reply-keyboard is only ever sent to an admin chat.

This file is imported lazily from main.py's register_handlers() to avoid
a circular import at module load time — do not import main.py's
register_handlers from here.
"""

from datetime import datetime

from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CommandHandler, MessageHandler, ContextTypes, filters, ApplicationHandlerStop

from main import (
    db,
    save_data,
    log_action,
    u,
    is_admin,
    ADMIN_IDS,
    MAX_WARNINGS,
)


# =====================================================================
# ADMIN KEYBOARD (reply keyboard, not inline — matches the rest of the bot)
# =====================================================================

ADMIN_MENU = ReplyKeyboardMarkup(
    [
        ["📊 داشبورد", "👥 کاربران"],
        ["💹 اقتصاد", "📤 درخواست‌های برداشت"],
        ["📋 لاگ‌ها", "🚫 بن و اخطار"],
        ["📢 پیام همگانی", "🎟 ساخت کد هدیه"],
        ["📰 انتشار خبر", "🏆 برگزاری فوری تورنمنت"],
        ["🌍 ارسال رویداد دستی", "🔙 خروج از پنل ادمین"],
    ],
    resize_keyboard=True,
)


async def _deny(update):
    """Silently-ish refuses — no admin data or menu is ever shown to a non-admin."""
    await update.message.reply_text("⛔ شما دسترسی ادمین ندارید.")


# =====================================================================
# /admin ENTRY POINT
# =====================================================================

async def admin_panel(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await _deny(update)
        return
    await update.message.reply_text(
        "👑 پنل مدیریت LIBER\n\nفقط شما (ادمین) این منو رو می‌بینید.", reply_markup=ADMIN_MENU
    )


async def admin_exit(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    from main import MAIN_MENU
    await update.message.reply_text("خارج شدی از پنل ادمین.", reply_markup=MAIN_MENU)


# =====================================================================
# DASHBOARD
# =====================================================================

async def dashboard(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return

    total_users = len(db["users"])
    banned_users = sum(1 for d in db["users"].values() if d["banned"])
    warned_users = sum(1 for d in db["users"].values() if d["warn_count"] > 0)
    total_liber = sum(d["liber"] for d in db["users"].values())
    total_coin = sum(d["coin"] for d in db["users"].values())
    pending_withdrawals = sum(1 for w in db["withdrawals"] if w["status"] == "pending")
    total_clans = len(db["clans"])
    top_rank = max(db["users"].values(), key=lambda d: d["rank_points"], default=None)

    started = datetime.fromisoformat(db["tournament"]["started_at"])
    days_passed = (datetime.utcnow() - started).days
    days_left = max(0, db["tournament"]["length_days"] - days_passed)

    text = (
        "📊 داشبورد مدیریت LIBER\n"
        "━━━━━━━━━━━━━━━\n"
        f"🕒 زمان سرور (UTC): {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👥 کل کاربران: {total_users}\n"
        f"🚫 کاربران مسدود: {banned_users}\n"
        f"⚠️ کاربران دارای اخطار: {warned_users}\n"
        "━━━━━━━━━━━━━━━\n"
        f"💹 قیمت لحظه‌ای بازار: {db['market']['price']} Coin\n"
        f"🪙 مجموع LIBER در گردش: {total_liber:.2f}\n"
        f"💵 مجموع Coin در گردش: {total_coin:.2f}\n"
        "━━━━━━━━━━━━━━━\n"
        f"👑 کلن‌های ثبت‌شده: {total_clans}\n"
        f"📤 درخواست برداشت در انتظار: {pending_withdrawals}\n"
        f"🏆 برترین رقابت‌گر: {top_rank['name'] if top_rank else '—'} "
        f"({top_rank['rank_points'] if top_rank else 0} امتیاز)\n"
        f"⏳ تا پایان تورنمنت فصلی: {days_left} روز"
    )
    await update.message.reply_text(text)


# =====================================================================
# USERS
# =====================================================================

async def users_list(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    rows = list(db["users"].values())[-20:]
    if not rows:
        await update.message.reply_text("هنوز کاربری ثبت‌نام نکرده.")
        return
    text = "👥 آخرین ۲۰ کاربر\n\n"
    for r in rows:
        status = "🚫" if r["banned"] else ("⚠️" if r["warn_count"] > 0 else "✅")
        text += (
            f"{status} {r['name']} (@{r['username'] or '—'}) — ID:{r['id']} — "
            f"سطح {r['level']} — {r['liber']:.0f} LIBER — اخطار {r['warn_count']}/{MAX_WARNINGS}\n"
        )
    text += "\nبرای جزئیات یک کاربر: /userinfo آیدی_عددی"
    await update.message.reply_text(text)


async def user_info(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /userinfo آیدی_عددی")
        return
    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("آیدی نامعتبر است.")
        return
    d = u(target_id)
    if not d:
        await update.message.reply_text("کاربری با این آیدی پیدا نشد.")
        return

    await update.message.reply_text(
f"""👤 جزئیات کاربر {target_id}

نام: {d['name']}   یوزرنیم: @{d['username'] or '—'}
بیو: {d['bio'] or '—'}
⭐ سطح: {d['level']}   ✨ XP: {d['xp']}
🪙 LIBER: {d['liber']:.2f}   💵 Coin: {d['coin']:.2f}   💎 Diamond: {d['diamond']}
👑 اشتراک: {d['sub_tier'] or 'ندارد'}
👥 کلن: {d['clan_id'] or '—'}   👥 زیرمجموعه: {d['ref_count']}
⚔ امتیاز رقابتی: {d['rank_points']}   🎮 مسابقات: {d['matches_played']} (برد {d['matches_won']})
⚠️ اخطار: {d['warn_count']}/{MAX_WARNINGS}   🚫 مسدود: {'بله' if d['banned'] else 'خیر'}
📅 عضویت: {d['created'][:10]}

/ban {target_id}   /unban {target_id}
/warn {target_id} دلیل   /resetwarn {target_id}
/addliber {target_id} مقدار   /removeliber {target_id} مقدار"""
    )


async def ban_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /ban آیدی_عددی")
        return
    target = u(int(context.args[0])) if context.args[0].isdigit() else None
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return
    target["banned"] = True
    save_data()
    log_action(update.effective_user.id, "ADMIN_BAN", str(target["id"]))
    await update.message.reply_text(f"🚫 کاربر {target['id']} مسدود شد.")
    try:
        await context.bot.send_message(target["id"], "🚫 حساب شما توسط ادمین مسدود شد.")
    except Exception:
        pass


async def unban_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /unban آیدی_عددی")
        return
    target = u(int(context.args[0])) if context.args[0].isdigit() else None
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return
    target["banned"] = False
    target["warn_count"] = 0
    save_data()
    log_action(update.effective_user.id, "ADMIN_UNBAN", str(target["id"]))
    await update.message.reply_text(f"✅ کاربر {target['id']} آزاد شد و اخطارهاش صفر شد.")
    try:
        await context.bot.send_message(target["id"], "✅ حساب شما توسط ادمین آزاد شد.")
    except Exception:
        pass


async def warn_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /warn آیدی_عددی دلیل")
        return
    target_id_str = context.args[0]
    reason = " ".join(context.args[1:])
    if not target_id_str.isdigit():
        await update.message.reply_text("آیدی نامعتبر است.")
        return
    target = u(int(target_id_str))
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return

    from main import warn_user
    await warn_user(context, target["id"], reason)
    await update.message.reply_text(f"⚠️ اخطار برای {target['id']} ثبت شد. ({target['warn_count']}/{MAX_WARNINGS})")


async def resetwarn_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /resetwarn آیدی_عددی")
        return
    target = u(int(context.args[0])) if context.args[0].isdigit() else None
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return
    target["warn_count"] = 0
    save_data()
    await update.message.reply_text(f"✅ اخطارهای کاربر {target['id']} صفر شد.")


async def add_liber_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /addliber آیدی_عددی مقدار")
        return
    target = u(int(context.args[0])) if context.args[0].isdigit() else None
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.")
        return
    target["liber"] += amount
    save_data()
    log_action(update.effective_user.id, "ADMIN_ADD_LIBER", f"{target['id']} +{amount}")
    await update.message.reply_text(f"✅ {amount} LIBER به کاربر {target['id']} اضافه شد.")


async def remove_liber_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if len(context.args) < 2:
        await update.message.reply_text("استفاده: /removeliber آیدی_عددی مقدار")
        return
    target = u(int(context.args[0])) if context.args[0].isdigit() else None
    if not target:
        await update.message.reply_text("کاربر پیدا نشد.")
        return
    try:
        amount = float(context.args[1])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.")
        return
    target["liber"] = max(0, target["liber"] - amount)
    save_data()
    log_action(update.effective_user.id, "ADMIN_REMOVE_LIBER", f"{target['id']} -{amount}")
    await update.message.reply_text(f"✅ {amount} LIBER از کاربر {target['id']} کم شد.")


# =====================================================================
# ECONOMY
# =====================================================================

async def economy_view(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    hist = db["market"]["history"][-15:]
    text = f"💹 اقتصاد LIBER\n\nقیمت فعلی: {db['market']['price']} Coin\n\nتاریخچه اخیر:\n"
    text += "\n".join(f"{h['price']} — {h['at'][:16]}" for h in hist) if hist else "داده‌ای نیست."
    text += (
        "\n\nبرای تنظیم دستی قیمت: /setprice مقدار\n"
        "برای دیدن پیشنهادهای باز بازار کاربران: /p2p_admin"
    )
    await update.message.reply_text(text)


async def set_price_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /setprice مقدار")
        return
    try:
        price = float(context.args[0])
    except ValueError:
        await update.message.reply_text("مقدار نامعتبر است.")
        return
    db["market"]["price"] = max(1, price)
    db["market"]["updated"] = str(datetime.utcnow())
    db["market"]["history"].append({"price": db["market"]["price"], "at": str(datetime.utcnow())})
    save_data()
    await update.message.reply_text(f"✅ قیمت بازار روی {price} تنظیم شد.")


async def p2p_admin_view(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    offers = [o for o in db["p2p_offers"] if o["open"]]
    if not offers:
        await update.message.reply_text("پیشنهاد باز فعالی نیست.")
        return
    text = "📦 پیشنهادهای باز بازار کاربران\n\n"
    for o in offers[-20:]:
        text += f"#{o['id']} — فروشنده {o['seller']} — {o['amount']} LIBER به {o['price']} Coin\n"
    await update.message.reply_text(text)


# =====================================================================
# WITHDRAWALS
# =====================================================================

async def withdrawals_admin_view(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    pending = [w for w in db["withdrawals"] if w["status"] == "pending"]
    if not pending:
        await update.message.reply_text("درخواست برداشت در انتظاری نیست.")
        return
    text = "📤 درخواست‌های برداشت در انتظار\n\n"
    for w in pending[-15:]:
        text += (
            f"کاربر {w['user_id']} — {w['amount']:.2f} LIBER — آدرس: {w['wallet']}\n"
            f"  /approve {w['user_id']}   /reject {w['user_id']}\n\n"
        )
    await update.message.reply_text(text)


async def approve_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /approve آیدی_عددی")
        return
    target_id = int(context.args[0]) if context.args[0].isdigit() else None
    if target_id is None:
        await update.message.reply_text("آیدی نامعتبر است.")
        return

    for w in db["withdrawals"]:
        if w["user_id"] == target_id and w["status"] == "pending":
            w["status"] = "approved"
            save_data()
            log_action(update.effective_user.id, "ADMIN_APPROVE_WITHDRAW", str(target_id))
            await update.message.reply_text(
                "✅ تایید شد. پرداخت واقعی TON باید توسط شما، دستی و خارج از ربات، به آدرس اعلام‌شده انجام شود."
            )
            try:
                await context.bot.send_message(target_id, f"✅ درخواست برداشت {w['amount']:.2f} LIBER تایید شد.")
            except Exception:
                pass
            return
    await update.message.reply_text("درخواست در انتظاری برای این کاربر پیدا نشد.")


async def reject_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /reject آیدی_عددی")
        return
    target_id = int(context.args[0]) if context.args[0].isdigit() else None
    if target_id is None:
        await update.message.reply_text("آیدی نامعتبر است.")
        return

    for w in db["withdrawals"]:
        if w["user_id"] == target_id and w["status"] == "pending":
            w["status"] = "rejected"
            target = u(target_id)
            if target:
                target["liber"] += w["amount"]
            save_data()
            log_action(update.effective_user.id, "ADMIN_REJECT_WITHDRAW", str(target_id))
            await update.message.reply_text("❌ رد شد و مبلغ به کاربر بازگردانده شد.")
            try:
                await context.bot.send_message(
                    target_id, f"❌ درخواست برداشت شما رد شد و {w['amount']:.2f} LIBER بازگشت."
                )
            except Exception:
                pass
            return
    await update.message.reply_text("درخواست در انتظاری برای این کاربر پیدا نشد.")


# =====================================================================
# LOGS
# =====================================================================

async def logs_view(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    rows = db["logs"][-20:]
    if not rows:
        await update.message.reply_text("لاگی ثبت نشده.")
        return
    text = "📋 آخرین لاگ‌ها\n\n" + "\n".join(
        f"[{r['at'][:16]}] {r['user_id']} — {r['action']} {r['detail']}" for r in rows
    )
    await update.message.reply_text(text)


# =====================================================================
# BROADCAST
# =====================================================================

async def broadcast_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /broadcast متن پیام")
        return
    msg = " ".join(context.args)
    sent, failed = 0, 0
    for uid_str, d in db["users"].items():
        if d["banned"]:
            continue
        try:
            await context.bot.send_message(int(uid_str), f"📢 {msg}")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ پیام همگانی ارسال شد به {sent} کاربر ({failed} ناموفق).")


# =====================================================================
# GIFT CODES
# =====================================================================

async def addcode_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if len(context.args) < 3:
        await update.message.reply_text("استفاده: /addcode کد مقدار تعداد_استفاده")
        return
    code = context.args[0].upper()
    try:
        reward = float(context.args[1])
        uses = int(context.args[2])
    except ValueError:
        await update.message.reply_text("مقادیر نامعتبرند.")
        return
    db["gift_codes"][code] = {"reward": reward, "uses_left": uses, "redeemed_by": []}
    save_data()
    log_action(update.effective_user.id, "ADMIN_ADD_CODE", code)
    await update.message.reply_text(f"✅ کد «{code}» ساخته شد: {reward} LIBER، {uses} بار قابل استفاده.")


# =====================================================================
# NEWS
# =====================================================================

async def addnews_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text("استفاده: /addnews متن خبر")
        return
    text = " ".join(context.args)
    db["news"].append({"text": text, "at": str(datetime.utcnow())})
    db["news"] = db["news"][-100:]
    save_data()
    await update.message.reply_text("✅ خبر منتشر شد.")


# =====================================================================
# FORCE TOURNAMENT / EVENT
# =====================================================================

async def force_tournament_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    ranked = sorted(db["users"].values(), key=lambda d: d["rank_points"], reverse=True)[:3]
    rewards = {0: 700, 1: 500, 2: 300}
    winners_text = []
    for i, d in enumerate(ranked):
        if d["rank_points"] <= 0:
            continue
        d["liber"] += rewards.get(i, 0)
        winners_text.append(f"{i+1}. {d['name']} +{rewards.get(i,0)} LIBER")
        try:
            await context.bot.send_message(
                d["id"], f"🏆 تورنمنت فصلی به‌صورت دستی توسط ادمین بسته شد. رتبه {i+1} شدی و {rewards.get(i,0)} LIBER گرفتی!"
            )
        except Exception:
            pass
    for d in db["users"].values():
        d["rank_points"] = 0
    db["tournament"]["started_at"] = str(datetime.utcnow())
    save_data()
    log_action(update.effective_user.id, "ADMIN_FORCE_TOURNAMENT", "")
    await update.message.reply_text("🏆 تورنمنت به‌صورت دستی بسته شد.\n\n" + ("\n".join(winners_text) or "برنده‌ای با امتیاز مثبت نبود."))


async def force_event_cmd(update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text(
            "استفاده: /forceevent متن_رویداد\n"
            "مثال: /forceevent جشنواره ویژه آخر هفته شروع شد!"
        )
        return
    text = " ".join(context.args)
    db["events"].append({"name": "📅 رویداد ویژه ادمین", "desc": text, "at": str(datetime.utcnow())})
    db["events"] = db["events"][-30:]
    save_data()

    sent = 0
    for uid_str, d in db["users"].items():
        if d["banned"]:
            continue
        try:
            await context.bot.send_message(int(uid_str), f"🌍 رویداد جهانی: 📅 رویداد ویژه ادمین\n{text}")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ رویداد دستی ارسال شد به {sent} کاربر.")


# =====================================================================
# ADMIN REPLY-KEYBOARD ROUTER
# =====================================================================

ADMIN_ROUTES = {
    "📊 داشبورد": dashboard,
    "👥 کاربران": users_list,
    "💹 اقتصاد": economy_view,
    "📤 درخواست‌های برداشت": withdrawals_admin_view,
    "📋 لاگ‌ها": logs_view,
    "🔙 خروج از پنل ادمین": admin_exit,
}


async def admin_menu_router(update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # Only intercept text that matches an admin-menu button, and only for admins.
    # Any other text falls through untouched to main.py's own menu_router.
    if text not in ADMIN_ROUTES and text not in (
        "🚫 بن و اخطار", "📢 پیام همگانی", "🎟 ساخت کد هدیه", "📰 انتشار خبر",
        "🏆 برگزاری فوری تورنمنت", "🌍 ارسال رویداد دستی",
    ):
        return  # not an admin-menu button — let main.py's router handle it

    if not is_admin(user_id):
        return  # never reveal admin menu items exist, to anyone else

    if text in ADMIN_ROUTES:
        await ADMIN_ROUTES[text](update, context)
    elif text == "🚫 بن و اخطار":
        await update.message.reply_text(
            "🚫 مدیریت بن و اخطار\n\n"
            "/userinfo آیدی — جزئیات کاربر\n"
            "/ban آیدی — مسدود کردن\n"
            "/unban آیدی — آزاد کردن (اخطارها هم صفر می‌شود)\n"
            "/warn آیدی دلیل — ثبت اخطار (۳ اخطار = بن خودکار)\n"
            "/resetwarn آیدی — صفر کردن اخطارها بدون آزاد کردن"
        )
    elif text == "📢 پیام همگانی":
        await update.message.reply_text("استفاده: /broadcast متن پیام")
    elif text == "🎟 ساخت کد هدیه":
        await update.message.reply_text("استفاده: /addcode کد مقدار تعداد_استفاده\nمثال: /addcode WELCOME100 100 500")
    elif text == "📰 انتشار خبر":
        await update.message.reply_text("استفاده: /addnews متن خبر")
    elif text == "🏆 برگزاری فوری تورنمنت":
        await force_tournament_cmd(update, context)
    elif text == "🌍 ارسال رویداد دستی":
        await update.message.reply_text("استفاده: /forceevent متن رویداد")

    # This update was a recognized admin-menu button for a real admin and has
    # already been fully handled above — stop it from also falling through
    # to main.py's generic menu_router, which would otherwise reply with an
    # unrelated "coming soon" fallback message for the same tap.
    raise ApplicationHandlerStop


# =====================================================================
# REGISTRATION (called from main.py's register_handlers)
# =====================================================================

def register_admin_handlers(app):
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("userinfo", user_info))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("warn", warn_cmd))
    app.add_handler(CommandHandler("resetwarn", resetwarn_cmd))
    app.add_handler(CommandHandler("addliber", add_liber_cmd))
    app.add_handler(CommandHandler("removeliber", remove_liber_cmd))
    app.add_handler(CommandHandler("setprice", set_price_cmd))
    app.add_handler(CommandHandler("p2p_admin", p2p_admin_view))
    app.add_handler(CommandHandler("approve", approve_cmd))
    app.add_handler(CommandHandler("reject", reject_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("addcode", addcode_cmd))
    app.add_handler(CommandHandler("addnews", addnews_cmd))
    app.add_handler(CommandHandler("forcetournament", force_tournament_cmd))
    app.add_handler(CommandHandler("forceevent", force_event_cmd))

    # This must be registered BEFORE main.py's generic menu_router text handler,
    # so admin.py's register_admin_handlers() is called first inside
    # main.py.register_handlers(), and admin_menu_router simply no-ops
    # (returns without consuming the update) for anything that isn't an
    # admin-menu button, letting main.py's own handler process it next.
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu_router), group=-1)
