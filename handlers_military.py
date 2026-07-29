# -*- coding: utf-8 -*-
"""
handlers_military.py — تسهیلات نظامی (فایل جدا)
================================================================
بخش «ساخت» این سیستم که اعداد دقیقش مشخص بود: انواع سرباز و بدنه‌ی
جنگنده. فایل کاملاً جداست و جدول خودش رو در اولین استفاده می‌سازه.

⚠️ توجه مهم: بخش «حمله‌ی موج‌به‌موج با هدف‌گیری جهت جغرافیایی و شمارش
معکوس ۳دقیقه‌ای» و «بیانه‌ی عمومی با لایک/پاسخ» در این نسخه ساخته نشده
چون این دو تا خودشون معادل دو سیستم بزرگ جدا هستن که برای ساختن درست و
تست‌شده‌شون نیاز به یه دور جداگونه دارن. همین الان که آماده بودید بگید
تا اون‌ها رو هم دقیقاً با همین کیفیت (تست کامل، بدون باگ) بسازم.

شامل:
    🪖 ساخت سرباز (۵ نوع، هرکدوم با قیمت مشخص)
    ✈️ ساخت جنگنده (انتخاب نوع بدنه از ۴ گزینه)
    📊 نمایش قدرت نظامی کلی کشور
"""
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from main import get_conn, get_user, update_balance, log_transaction, back_keyboard

logger = logging.getLogger("LIBER.military")

# ============================================================
#   تنظیمات — قیمت‌ها دقیقاً طبق چیزی که گفته شد
# ============================================================
SOLDIER_TYPES = {
    "normal": {"name": "🪖 سرباز عادی", "batch": 100, "cost": 700},
    "army": {"name": "⚔️ سرباز ارتشی", "batch": 100, "cost": 900},
    "navy": {"name": "⚓ سرباز دریایی", "batch": 100, "cost": 1000},
    "commander": {"name": "🎖 فرمانده", "batch": 1, "cost": 800},
    "special": {"name": "🛡 سرباز ویژه", "batch": 200, "cost": 1400},
    "secret": {"name": "🕶 سرباز مخفی", "batch": 100, "cost": 1500},
}

JET_BODY_TYPES = {
    "light_weak": {"name": "✈️ بدنه سبک ضعیف", "cost": 1300, "power": 10},
    "light_strong": {"name": "✈️ بدنه سبک قوی", "cost": 1500, "power": 16},
    "heavy_stealth": {"name": "🛩 بدنه سنگین غیرردیاب قوی", "cost": 2000, "power": 24},
    "rare_stealth": {"name": "💎 بدنه غیرردیاب کمیاب", "cost": 2500, "power": 34},
}

# ضریب قدرت هر واحد سرباز، برای محاسبه‌ی امتیاز نظامی کلی
SOLDIER_POWER = {"normal": 1, "army": 1.5, "navy": 1.5, "commander": 6, "special": 2.2, "secret": 3}


# ============================================================
#   جداول محلی
# ============================================================
_tables_ready = False


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS military_soldiers (
            user_id INTEGER,
            soldier_key TEXT,
            quantity INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, soldier_key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS military_jets (
            jet_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            body_key TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """)
    _tables_ready = True


def _get_soldier_counts(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT soldier_key, quantity FROM military_soldiers WHERE user_id = ?", (user_id,)
        ).fetchall()
    return {r["soldier_key"]: r["quantity"] for r in rows}


def _get_jet_counts(user_id):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT body_key, COUNT(*) c FROM military_jets WHERE user_id = ? GROUP BY body_key", (user_id,)
        ).fetchall()
    return {r["body_key"]: r["c"] for r in rows}


def get_military_power(user_id):
    """مجموع امتیاز نظامی: سربازها بر اساس تعداد×ضریب + جنگنده‌ها بر اساس قدرت بدنه‌شون."""
    _ensure_tables()
    soldiers = _get_soldier_counts(user_id)
    jets = _get_jet_counts(user_id)
    power = sum(qty * SOLDIER_POWER.get(key, 1) for key, qty in soldiers.items())
    power += sum(cnt * JET_BODY_TYPES[key]["power"] for key, cnt in jets.items() if key in JET_BODY_TYPES)
    return round(power, 1)


# ============================================================
#   منوی اصلی تسهیلات نظامی
# ============================================================
def _military_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🪖 ساخت سرباز", callback_data="military_soldier_menu"),
         InlineKeyboardButton("✈️ ساخت جنگنده", callback_data="military_jet_menu")],
        [InlineKeyboardButton("⚔️ حمله نظامی", callback_data="menu_war"),
         InlineKeyboardButton("🏗 بازسازی", callback_data="war_reconstruct")],
        [InlineKeyboardButton("🏛 مزایده‌ی نظامی", callback_data="menu_military_market")],
        [InlineKeyboardButton("📜 بیانه‌ی عمومی", callback_data="menu_declaration")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_country")],
    ])


async def military_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    soldiers = _get_soldier_counts(user_id)
    jets = _get_jet_counts(user_id)
    power = get_military_power(user_id)

    lines = ["🪖 تسهیلات نظامی\n"]
    if not soldiers and not jets:
        lines.append("شما هنوز هیچ سرباز یا جنگنده‌ای نساختید.\n")
    else:
        if soldiers:
            lines.append("👥 نیروها:")
            for key, qty in soldiers.items():
                if qty > 0:
                    lines.append(f"  • شما {qty} {SOLDIER_TYPES[key]['name']} دارید")
        if jets:
            lines.append("\n✈️ جنگنده‌ها:")
            for key, cnt in jets.items():
                if key in JET_BODY_TYPES:
                    lines.append(f"  • {cnt} جنگنده از نوع {JET_BODY_TYPES[key]['name']} دارید")
        lines.append("")

    lines.append(f"📊 قدرت نظامی کلی: {power}")
    await q.edit_message_text("\n".join(lines), reply_markup=_military_menu_keyboard())


# ============================================================
#   ساخت سرباز
# ============================================================
def _soldier_type_keyboard():
    rows = [
        [InlineKeyboardButton(f"{s['name']} — {s['cost']} LIBER / {s['batch']} نفر", callback_data=f"military_soldier_pick:{key}")]
        for key, s in SOLDIER_TYPES.items()
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military")])
    return InlineKeyboardMarkup(rows)


async def military_soldier_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("🪖 چه نوع سربازی می‌خواید بسازید؟", reply_markup=_soldier_type_keyboard())


def _soldier_batch_keyboard(soldier_key, batches):
    s = SOLDIER_TYPES[soldier_key]
    total_units = batches * s["batch"]
    total_cost = batches * s["cost"]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➖", callback_data=f"military_soldier_step:{soldier_key}:-1"),
         InlineKeyboardButton(f"{total_units} نفر = {total_cost} LIBER", callback_data="military_noop"),
         InlineKeyboardButton("➕", callback_data=f"military_soldier_step:{soldier_key}:1")],
        [InlineKeyboardButton("✅ تایید ساخت", callback_data=f"military_soldier_confirm:{soldier_key}")],
        [InlineKeyboardButton("❌ لغو", callback_data="menu_military")],
    ])


async def military_soldier_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    soldier_key = q.data.split(":", 1)[1]
    context.user_data["military_soldier_batches"] = 1
    s = SOLDIER_TYPES[soldier_key]
    await q.edit_message_text(
        f"{s['name']}\nهر {s['batch']} نفر = {s['cost']} LIBER\n\nتعداد دسته رو انتخاب کن:",
        reply_markup=_soldier_batch_keyboard(soldier_key, 1),
    )


async def military_soldier_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, soldier_key, delta = q.data.split(":")
    current = context.user_data.get("military_soldier_batches", 1)
    new_batches = max(1, current + int(delta))
    context.user_data["military_soldier_batches"] = new_batches
    await q.edit_message_reply_markup(reply_markup=_soldier_batch_keyboard(soldier_key, new_batches))


async def military_soldier_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    soldier_key = q.data.split(":", 1)[1]
    s = SOLDIER_TYPES[soldier_key]
    batches = context.user_data.get("military_soldier_batches", 1)
    total_units = batches * s["batch"]
    total_cost = batches * s["cost"]

    user = get_user(user_id)
    if user["liber"] < total_cost:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {total_cost}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-total_cost)
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO military_soldiers (user_id, soldier_key, quantity) VALUES (?, ?, ?)
               ON CONFLICT(user_id, soldier_key) DO UPDATE SET quantity = quantity + excluded.quantity""",
            (user_id, soldier_key, total_units),
        )
    log_transaction(user_id, "MILITARY_SOLDIER_BUILD", f"{soldier_key} x{total_units} cost={total_cost}")
    context.user_data["military_soldier_batches"] = 1

    total_now = _get_soldier_counts(user_id).get(soldier_key, 0)
    await q.edit_message_text(
        f"✅ ساخته شد!\nشما در تسهیلات = {total_now} {s['name']} دارید (-{total_cost} LIBER)",
        reply_markup=_military_menu_keyboard(),
    )


# ============================================================
#   ساخت جنگنده (انتخاب بدنه)
# ============================================================
def _jet_body_keyboard():
    rows = [
        [InlineKeyboardButton(f"{j['name']} — {j['cost']} LIBER", callback_data=f"military_jet_pick:{key}")]
        for key, j in JET_BODY_TYPES.items()
    ]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military")])
    return InlineKeyboardMarkup(rows)


async def military_jet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "✈️ ساخت جنگنده\n\nاول نوع بدنه رو انتخاب کنید:", reply_markup=_jet_body_keyboard()
    )


async def military_jet_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    body_key = q.data.split(":", 1)[1]
    body = JET_BODY_TYPES[body_key]

    user = get_user(user_id)
    if user["liber"] < body["cost"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {body['cost']}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-body["cost"])
    import time
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO military_jets (user_id, body_key, created_at) VALUES (?, ?, ?)",
            (user_id, body_key, int(time.time())),
        )
    log_transaction(user_id, "MILITARY_JET_BUILD", body_key)

    total_now = _get_jet_counts(user_id).get(body_key, 0)
    await q.edit_message_text(
        f"✅ ۱ جنگنده از نوع {body['name']} ساخته شد!\nشما در تسهیلات = {total_now} جنگنده از این نوع دارید (-{body['cost']} LIBER)",
        reply_markup=_military_menu_keyboard(),
    )


# ============================================================
#   دیسپچر
# ============================================================
MILITARY_CALLBACKS = {
    "menu_military": military_menu_callback,
    "military_soldier_menu": military_soldier_menu_callback,
    "military_jet_menu": military_jet_menu_callback,
    "military_noop": None,  # فقط برای جلوگیری از کرش روی دکمه‌ی نمایشی وسط استپر
}


async def military_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    q = update.callback_query
    data = q.data

    if data == "military_noop":
        await q.answer()
        return True
    if data in MILITARY_CALLBACKS:
        await MILITARY_CALLBACKS[data](update, context)
        return True
    if data.startswith("military_soldier_pick:"):
        await military_soldier_pick_callback(update, context)
        return True
    if data.startswith("military_soldier_step:"):
        await military_soldier_step_callback(update, context)
        return True
    if data.startswith("military_soldier_confirm:"):
        await military_soldier_confirm_callback(update, context)
        return True
    if data.startswith("military_jet_pick:"):
        await military_jet_pick_callback(update, context)
        return True
    return False
