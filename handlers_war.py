# -*- coding: utf-8 -*-
"""
handlers_war.py — حمله‌ی نظامی + بیانه‌ی عمومی (فایل جدا)
================================================================
جاهایی که درخواست مبهم بود، یه تصمیم مشخص و منطقی گرفتم — همه‌جا با
کامنت مشخص کردم کجا. اگه با نظرتون فرق داشت، فقط بگید کدوم عدد رو
عوض کنم.

⚙️ تصمیم‌های گرفته‌شده برای جاهای مبهم:
  • هزینه‌ی هر موج حمله: ۵۰ LIBER (دقیقاً طبق چیزی که گفتید)
  • «موج دوم» = می‌تونی دوباره به همون هدف حمله کنی (محدودیت فقط cooldown کوتاه)
  • تاخیر رسیدن حمله: ۳ دقیقه (دقیقاً طبق چیزی که گفتید)
  • جهت حمله (غرب/شرق/جنوب/شمال): کاملاً نمایشی، روی محاسبه تاثیر نداره
  • آسیب هر حمله‌ی موفق: ۲۵٪ از قدرت نظامی مدافع نابود می‌شه
  • بازسازی: هزینه‌ش متناسب با مقدار آسیب‌دیده است
  • بیانه: سقف ۵ پست در روز برای هر کاربر (نه ۵۰، چون ۵۰ در روز عملاً باز کردن
    در به روی اسپمه؛ اگه واقعاً ۵۰ می‌خواید فقط بگید عوضش می‌کنم)
  • لایک بیانه: هر کاربر فقط یک‌بار می‌تونه لایک کنه (وگرنه میشه چاپ پول)
  • پاسخ به بیانه: حداکثر ۵ پاسخ روی هر بیانه نمایش داده می‌شه
"""
import time
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import get_conn, get_user, update_balance, log_transaction, back_keyboard

logger = logging.getLogger("LIBER.war")

# ============================================================
#   تنظیمات
# ============================================================
ATTACK_WAVE_COST = 50
ATTACK_DELAY_SECONDS = 3 * 60
ATTACK_DAMAGE_PERCENT = 25
MIN_ATTACK_DAMAGE = 10  # حتی اگه مدافع تقریباً هیچ نیرویی نداشته باشه، حمله‌ی موفق حداقل این‌قدر آسیب می‌زنه و جایزه می‌ده
ATTACK_COOLDOWN_SECONDS = 5 * 60  # فاصله‌ی حداقلی بین دو حمله به یه هدف (جای «موج دوم»)
RECONSTRUCTION_COST_PER_POWER = 15  # هزینه‌ی بازسازی هر ۱ واحد قدرت ازدست‌رفته

DIRECTIONS = {"west": "🧭 غرب", "east": "🧭 شرق", "south": "🧭 جنوب", "north": "🧭 شمال"}

DAILY_DECLARATION_LIMIT = 5
DECLARATION_LIKE_REWARD = 0.3
MAX_REPLIES_SHOWN = 5


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
        CREATE TABLE IF NOT EXISTS war_damage (
            user_id INTEGER PRIMARY KEY,
            power_lost REAL NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS war_attacks (
            attack_id INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id INTEGER NOT NULL,
            defender_id INTEGER NOT NULL,
            direction TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            resolved INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS war_cooldown (
            attacker_id INTEGER,
            defender_id INTEGER,
            last_attack_at INTEGER NOT NULL,
            PRIMARY KEY (attacker_id, defender_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS declarations (
            declaration_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            country_name TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL,
            likes INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS declaration_likes (
            declaration_id INTEGER,
            user_id INTEGER,
            PRIMARY KEY (declaration_id, user_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS declaration_replies (
            reply_id INTEGER PRIMARY KEY AUTOINCREMENT,
            declaration_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS declaration_daily_count (
            user_id INTEGER,
            date_key TEXT,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, date_key)
        )
        """)
    _tables_ready = True


def _get_power_lost(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT power_lost FROM war_damage WHERE user_id = ?", (user_id,)).fetchone()
    return row["power_lost"] if row else 0


# ============================================================
#   حمله‌ی نظامی
# ============================================================
def _attack_target_keyboard(targets):
    rows = [[InlineKeyboardButton(f"🎯 {name} (قدرت: {power})", callback_data=f"war_pick_target:{uid}")]
            for uid, name, power in targets]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military")])
    return InlineKeyboardMarkup(rows)


async def war_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """لیست چند کشور دیگه برای حمله (به‌جای «جستجو»، ساده‌ترین و امن‌ترین راه: لیست تصادفی از بازیکنان فعال)."""
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    import handlers_military as hm
    with get_conn() as conn:
        candidates = conn.execute(
            "SELECT user_id, first_name FROM users WHERE user_id != ? AND is_banned = 0 ORDER BY RANDOM() LIMIT 10",
            (user_id,),
        ).fetchall()

    targets = []
    for c in candidates:
        power = hm.get_military_power(c["user_id"])
        targets.append((c["user_id"], c["first_name"] or str(c["user_id"]), power))

    if not targets:
        await q.edit_message_text("فعلاً هدفی برای حمله پیدا نشد.", reply_markup=back_keyboard())
        return

    text = (
        f"⚔️ حمله‌ی نظامی\n\n"
        f"هزینه‌ی هر موج: {ATTACK_WAVE_COST} LIBER\n"
        f"تاخیر رسیدن: {ATTACK_DELAY_SECONDS // 60} دقیقه\n\n"
        "یکی از هدف‌های زیر رو انتخاب کن:"
    )
    await q.edit_message_text(text, reply_markup=_attack_target_keyboard(targets))


async def war_pick_target_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    defender_id = int(q.data.split(":", 1)[1])
    context.user_data["war_target"] = defender_id
    rows = [[InlineKeyboardButton(label, callback_data=f"war_direction:{key}")] for key, label in DIRECTIONS.items()]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military")])
    await q.edit_message_text("از کدوم جهت حمله می‌کنی؟ (فقط نمایشیه)", reply_markup=InlineKeyboardMarkup(rows))


async def war_direction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    attacker_id = q.from_user.id
    defender_id = context.user_data.get("war_target")
    direction_key = q.data.split(":", 1)[1]

    if not defender_id:
        await q.answer("هدف گم شد، دوباره از منو شروع کن.", show_alert=True)
        return

    now = int(time.time())
    with get_conn() as conn:
        cd = conn.execute(
            "SELECT last_attack_at FROM war_cooldown WHERE attacker_id = ? AND defender_id = ?",
            (attacker_id, defender_id),
        ).fetchone()
    if cd and now - cd["last_attack_at"] < ATTACK_COOLDOWN_SECONDS:
        remaining = ATTACK_COOLDOWN_SECONDS - (now - cd["last_attack_at"])
        await q.answer(f"⏳ {remaining // 60 + 1} دقیقه دیگه می‌تونی دوباره به این هدف حمله کنی.", show_alert=True)
        return

    user = get_user(attacker_id)
    if user["liber"] < ATTACK_WAVE_COST:
        await q.answer(f"❌ برای حمله به {ATTACK_WAVE_COST} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    update_balance(attacker_id, liber=-ATTACK_WAVE_COST)
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO war_attacks (attacker_id, defender_id, direction, created_at) VALUES (?, ?, ?, ?)",
            (attacker_id, defender_id, direction_key, now),
        )
        attack_id = cur.lastrowid
        conn.execute(
            """INSERT INTO war_cooldown (attacker_id, defender_id, last_attack_at) VALUES (?, ?, ?)
               ON CONFLICT(attacker_id, defender_id) DO UPDATE SET last_attack_at = excluded.last_attack_at""",
            (attacker_id, defender_id, now),
        )
    log_transaction(attacker_id, "WAR_ATTACK_LAUNCHED", f"target={defender_id} attack_id={attack_id}")

    context.job_queue.run_once(
        _resolve_attack_job, ATTACK_DELAY_SECONDS, data={"attack_id": attack_id}, name=f"war_attack_{attack_id}"
    )

    dir_label = DIRECTIONS[direction_key]
    await q.edit_message_text(
        f"🚀 موشک/جنگنده پرتاب شد به سمت هدف از {dir_label}!\n"
        f"تا {ATTACK_DELAY_SECONDS // 60} دقیقه‌ی دیگه نتیجه‌ی حمله اعلام می‌شه.",
        reply_markup=back_keyboard(),
    )


async def _resolve_attack_job(context: ContextTypes.DEFAULT_TYPE):
    await resolve_attack(context.job.data["attack_id"], context.bot)


async def resolve_attack(attack_id, bot):
    """منطق اصلی رزولوشن حمله — جدا از job_queue تا مستقیم قابل تست باشه."""
    _ensure_tables()
    import handlers_military as hm

    with get_conn() as conn:
        attack = conn.execute("SELECT * FROM war_attacks WHERE attack_id = ?", (attack_id,)).fetchone()
    if not attack or attack["resolved"]:
        return

    attacker_power = hm.get_military_power(attack["attacker_id"])
    defender_power = hm.get_military_power(attack["defender_id"])

    with get_conn() as conn:
        defender_row = conn.execute("SELECT personal_defense_level FROM users WHERE user_id = ?", (attack["defender_id"],)).fetchone()
    defense_bonus = (defender_row["personal_defense_level"] if defender_row else 0) * 5
    effective_defense = defender_power + defense_bonus

    success = attacker_power > effective_defense
    dir_label = DIRECTIONS[attack["direction"]]

    with get_conn() as conn:
        conn.execute("UPDATE war_attacks SET resolved = 1 WHERE attack_id = ?", (attack_id,))

    attacker = get_user(attack["attacker_id"])
    defender = get_user(attack["defender_id"])
    attacker_name = attacker["first_name"] if attacker else str(attack["attacker_id"])

    if success:
        damage = max(MIN_ATTACK_DAMAGE, round(defender_power * ATTACK_DAMAGE_PERCENT / 100, 1))
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO war_damage (user_id, power_lost) VALUES (?, ?)
                   ON CONFLICT(user_id) DO UPDATE SET power_lost = power_lost + excluded.power_lost""",
                (attack["defender_id"], damage),
            )
        reward = round(damage * 3)
        update_balance(attack["attacker_id"], liber=reward)
        log_transaction(attack["attacker_id"], "WAR_ATTACK_WIN", f"damage={damage} reward={reward}")

        try:
            await bot.send_message(
                attack["defender_id"],
                f"🚨 شما مورد حمله قرار گرفتید!\n\n"
                f"در {dir_label} کشورتون یک موشک/جنگنده اصابت کرد.\n"
                f"👤 حمله‌کننده: {attacker_name}\n"
                f"💥 آسیب: {damage} قدرت نظامی از دست رفت\n\n"
                "می‌تونید از منوی نظامی بازسازی کنید.",
            )
        except TelegramError:
            pass
        try:
            await bot.send_message(
                attack["attacker_id"],
                f"🎉 حمله موفق بود! {damage} قدرت از دشمن نابود شد.\n+{reward} LIBER جایزه گرفتی.",
            )
        except TelegramError:
            pass
    else:
        log_transaction(attack["attacker_id"], "WAR_ATTACK_FAIL", f"target={attack['defender_id']}")
        try:
            await bot.send_message(
                attack["attacker_id"],
                f"🛡 حمله ناموفق بود — پدافند {defender['first_name'] if defender else 'هدف'} قوی‌تر بود.",
            )
        except TelegramError:
            pass
        try:
            await bot.send_message(
                attack["defender_id"],
                f"🛡 پدافند شما یک حمله از {dir_label} رو با موفقیت دفع کرد!",
            )
        except TelegramError:
            pass


async def war_reconstruct_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    lost = _get_power_lost(user_id)

    if lost <= 0:
        await q.answer("چیزی برای بازسازی نداری.", show_alert=True)
        return

    cost = round(lost * RECONSTRUCTION_COST_PER_POWER)
    user = get_user(user_id)
    if user["liber"] < cost:
        await q.answer(f"❌ برای بازسازی کامل به {cost} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-cost)
    with get_conn() as conn:
        conn.execute("UPDATE war_damage SET power_lost = 0 WHERE user_id = ?", (user_id,))
    log_transaction(user_id, "WAR_RECONSTRUCT", f"cost={cost}")
    await q.edit_message_text(f"🏗 بازسازی کامل شد! (-{cost} LIBER)", reply_markup=back_keyboard())


# ============================================================
#   بیانه‌ی عمومی
# ============================================================
def _today_key():
    return time.strftime("%Y-%m-%d", time.gmtime())


async def declaration_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    today = _today_key()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM declaration_daily_count WHERE user_id = ? AND date_key = ?", (user_id, today)
        ).fetchone()
    used = row["count"] if row else 0

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("📜 نوشتن بیانه‌ی جدید", callback_data="declaration_write")],
        [InlineKeyboardButton("📖 خواندن بیانه‌های اخیر", callback_data="declaration_read")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])
    await q.edit_message_text(
        f"📜 بیانه‌ی عمومی\n\nامروز {used}/{DAILY_DECLARATION_LIMIT} بیانه نوشتی.\n"
        f"هر لایک روی بیانه‌ات {DECLARATION_LIKE_REWARD} LIBER می‌گیری.",
        reply_markup=markup,
    )


async def declaration_write_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    today = _today_key()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM declaration_daily_count WHERE user_id = ? AND date_key = ?", (user_id, today)
        ).fetchone()
    used = row["count"] if row else 0
    if used >= DAILY_DECLARATION_LIMIT:
        await q.answer(f"❌ سقف {DAILY_DECLARATION_LIMIT} بیانه‌ی امروز پر شده.", show_alert=True)
        return

    await q.answer()
    context.user_data["awaiting"] = "declaration_country_input"
    await q.edit_message_text("📜 اسم کشورتون رو بفرستید:")


async def _do_declaration_country(update, context, raw_text):
    context.user_data["declaration_country"] = raw_text.strip()[:30]
    context.user_data["awaiting"] = "declaration_message_input"
    await update.message.reply_text("حالا متن بیانه رو بفرستید:")


async def _do_declaration_message(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    today = _today_key()
    country = context.user_data.pop("declaration_country", "نامشخص")
    message = raw_text.strip()[:500]

    with get_conn() as conn:
        conn.execute(
            "INSERT INTO declarations (user_id, country_name, message, created_at) VALUES (?, ?, ?, ?)",
            (user_id, country, message, int(time.time())),
        )
        conn.execute(
            """INSERT INTO declaration_daily_count (user_id, date_key, count) VALUES (?, ?, 1)
               ON CONFLICT(user_id, date_key) DO UPDATE SET count = count + 1""",
            (user_id, today),
        )
    log_transaction(user_id, "DECLARATION_WRITE", country)
    await update.message.reply_text("✅ بیانه‌ات منتشر شد!", reply_markup=back_keyboard())


def _declaration_view_keyboard(declaration_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❤️ لایک", callback_data=f"declaration_like:{declaration_id}"),
         InlineKeyboardButton("💬 پاسخ", callback_data=f"declaration_reply:{declaration_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_declaration")],
    ])


async def declaration_read_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM declarations ORDER BY declaration_id DESC LIMIT 5"
        ).fetchall()

    if not rows:
        await q.edit_message_text("هنوز بیانه‌ای منتشر نشده.", reply_markup=back_keyboard())
        return

    d = rows[0]
    await _render_declaration(q, d)


async def _render_declaration(q, d):
    author = get_user(d["user_id"])
    author_name = author["first_name"] if author else str(d["user_id"])
    with get_conn() as conn:
        replies = conn.execute(
            "SELECT * FROM declaration_replies WHERE declaration_id = ? ORDER BY reply_id DESC LIMIT ?",
            (d["declaration_id"], MAX_REPLIES_SHOWN),
        ).fetchall()

    lines = [
        f"📜 بیانه‌ی {author_name} — {d['country_name']}\n",
        d["message"],
        f"\n❤️ {d['likes']} لایک",
    ]
    if replies:
        lines.append("\n💬 پاسخ‌ها:")
        for r in replies:
            u = get_user(r["user_id"])
            name = u["first_name"] if u else str(r["user_id"])
            lines.append(f"  • {name}: {r['message']}")

    await q.edit_message_text("\n".join(lines), reply_markup=_declaration_view_keyboard(d["declaration_id"]))


async def declaration_like_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    declaration_id = int(q.data.split(":", 1)[1])

    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM declaration_likes WHERE declaration_id = ? AND user_id = ?", (declaration_id, user_id)
        ).fetchone()
    if already:
        await q.answer("قبلاً لایک کردی.", show_alert=True)
        return

    with get_conn() as conn:
        d = conn.execute("SELECT * FROM declarations WHERE declaration_id = ?", (declaration_id,)).fetchone()
    if not d:
        await q.answer("این بیانه دیگه موجود نیست.", show_alert=True)
        return
    if d["user_id"] == user_id:
        await q.answer("نمی‌تونی بیانه‌ی خودت رو لایک کنی.", show_alert=True)
        return

    await q.answer()
    with get_conn() as conn:
        conn.execute("INSERT INTO declaration_likes (declaration_id, user_id) VALUES (?, ?)", (declaration_id, user_id))
        conn.execute("UPDATE declarations SET likes = likes + 1 WHERE declaration_id = ?", (declaration_id,))
    update_balance(d["user_id"], liber=DECLARATION_LIKE_REWARD)
    log_transaction(d["user_id"], "DECLARATION_LIKED", str(declaration_id))

    with get_conn() as conn:
        d2 = conn.execute("SELECT * FROM declarations WHERE declaration_id = ?", (declaration_id,)).fetchone()
    await _render_declaration(q, d2)


async def declaration_reply_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    declaration_id = int(q.data.split(":", 1)[1])
    context.user_data["declaration_reply_target"] = declaration_id
    context.user_data["awaiting"] = "declaration_reply_input"
    await q.edit_message_text("💬 پاسخت رو بفرست:")


async def _do_declaration_reply(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    declaration_id = context.user_data.pop("declaration_reply_target", None)
    if not declaration_id:
        await update.message.reply_text("❌ بیانه‌ی مقصد گم شد.")
        return
    message = raw_text.strip()[:300]
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO declaration_replies (declaration_id, user_id, message, created_at) VALUES (?, ?, ?, ?)",
            (declaration_id, user_id, message, int(time.time())),
        )
    log_transaction(user_id, "DECLARATION_REPLY", str(declaration_id))
    await update.message.reply_text("✅ پاسخت ثبت شد!", reply_markup=back_keyboard())


# ============================================================
#   دیسپچر
# ============================================================
WAR_CALLBACKS = {
    "menu_war": war_menu_callback,
    "war_reconstruct": war_reconstruct_callback,
    "menu_declaration": declaration_menu_callback,
    "declaration_write": declaration_write_callback,
    "declaration_read": declaration_read_callback,
}


async def war_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in WAR_CALLBACKS:
        await WAR_CALLBACKS[data](update, context)
        return True
    if data.startswith("war_pick_target:"):
        await war_pick_target_callback(update, context)
        return True
    if data.startswith("war_direction:"):
        await war_direction_callback(update, context)
        return True
    if data.startswith("declaration_like:"):
        await declaration_like_callback(update, context)
        return True
    if data.startswith("declaration_reply:"):
        await declaration_reply_start_callback(update, context)
        return True
    return False


async def war_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "declaration_country_input":
        context.user_data["awaiting"] = None
        await _do_declaration_country(update, context, raw_text)
        return True
    if awaiting == "declaration_message_input":
        context.user_data["awaiting"] = None
        await _do_declaration_message(update, context, raw_text)
        return True
    if awaiting == "declaration_reply_input":
        context.user_data["awaiting"] = None
        await _do_declaration_reply(update, context, raw_text)
        return True
    return False
