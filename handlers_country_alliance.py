# -*- coding: utf-8 -*-
"""
handlers_country_alliance.py — فایل جدا (پارت ۱ از بسته‌ی توسعه‌ی جدید LIBER)
================================================================
این فایل کاملاً مستقل است و باید کنار main.py قرار بگیرد. جدول‌ها و
ستون‌های موردنیازش را خودش در اولین اجرا می‌سازد/اضافه می‌کند (ALTER
TABLE با try/except، پس اجرای دوباره هیچ خطایی نمی‌دهد).

شامل ۳ قابلیت که دقیقاً طبق درخواست ساخته شده:

  1) ✏️ تغییر نام کشور
     بار اول: ۵۰ LIBER   |   از بار دوم به بعد: ۱۰۰ LIBER

  2) 🎚 استپر شیشه‌ای خرید/فروش بازار
     دکمه‌های ➖۱۰ ➖۱ [مقدار] ➕۱ ➕۱۰ + دکمه‌ی «✅ انجام معامله».
     قیمت لحظه‌ی تایید (نه لحظه‌ی باز کردن منو) استفاده می‌شود — یعنی اگر
     بین باز کردن منو و زدن تایید، آپدیت ساعتی بازار قیمت را عوض کرده
     باشد، محاسبه‌ی نهایی با قیمت تازه انجام می‌شود؛ همون‌طور که خواستید.

  3) 🤝 اتحاد کامل‌تر: جستجو با اسم یا کد اختصاصی، آگهی عمومی عضوگیری
     (۱۰۰ LIBER برای ۱ ساعت نمایش در لیست عمومی)، و بیوی قابل‌ویرایش.

نحوه‌ی اتصال به main.py (فقط همین چند خط، جایی تغییر ساختاری در بقیه‌ی
فایل‌ها لازم نیست):

    # در main.py، داخل تابع callback_router، در زنجیره‌ی fallback (همون‌جایی
    # که import handlers_extra / handlers_bonus و... هست) این را هم اضافه کن:
        if not handled:
            import handlers_country_alliance
            handled = await handlers_country_alliance.country_alliance_callback_router(update, context)

    # و در تابع text_message_router، در همون زنجیره‌ی importها این را اضافه کن:
        import handlers_country_alliance
        if await handlers_country_alliance.country_alliance_text_router(update, context):
            return

    # برای دیدن دکمه‌های جدید در منوی کشور/اتحاد، در handlers_extra.py:
    #   - در country_view_keyboard(): یک ردیف اضافه کن:
    #         [InlineKeyboardButton("✏️ تغییر نام کشور", callback_data="country_rename_start")]
    #   - در alliance_view_keyboard(): این ردیف‌ها رو اضافه کن:
    #         [InlineKeyboardButton("🔍 جستجو با اسم/کد", callback_data="alliance_search_start")],
    #         [InlineKeyboardButton("🌍 اتحادهای عمومی (آگهی‌دار)", callback_data="alliance_public_list")],
    #         [InlineKeyboardButton("📢 ثبت آگهی عضوگیری (۱۰۰ LIBER/۱ساعت)", callback_data="alliance_ad_post")],
    #         [InlineKeyboardButton("📝 تغییر بیوی اتحاد", callback_data="alliance_bio_start")],

    # برای استپر بازار، در main.py داخل market_keyboard() به‌جای دکمه‌های
    # قبلی (یا کنارشون) این را اضافه کن:
    #         [InlineKeyboardButton("🎚 خرید با استپر", callback_data="market_stepper:buy"),
    #          InlineKeyboardButton("🎚 فروش با استپر", callback_data="market_stepper:sell")],
"""
import time
import random
import string
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
    get_market_price,
    BUY_FEE_PERCENT,
    SELL_FEE_PERCENT,
    get_subscription_perks,
)

logger = logging.getLogger("LIBER.country_alliance")

# ============================================================
#   تنظیمات
# ============================================================
COUNTRY_RENAME_COST_FIRST = 100
COUNTRY_RENAME_COST_NEXT = 200

ALLIANCE_AD_COST = 100
ALLIANCE_AD_DURATION_SECONDS = 3600  # ۱ ساعت

MARKET_STEP_SMALL = 1
MARKET_STEP_BIG = 10
MARKET_MIN_AMOUNT = 1
MARKET_MAX_AMOUNT = 1_000_000


# ============================================================
#   جداول/ستون‌های محلی (idempotent)
# ============================================================
_ready = False


def _ensure_tables():
    global _ready
    if _ready:
        return
    with get_conn() as conn:
        for ddl in (
            "ALTER TABLE countries ADD COLUMN rename_count INTEGER NOT NULL DEFAULT 0",
            "ALTER TABLE alliances ADD COLUMN bio TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE alliances ADD COLUMN join_code TEXT",
        ):
            try:
                conn.execute(ddl)
            except Exception:
                pass

        conn.execute("""
        CREATE TABLE IF NOT EXISTS alliance_ads (
            ad_id INTEGER PRIMARY KEY AUTOINCREMENT,
            alliance_id INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS country_rename_log (
            country_id INTEGER,
            month_key TEXT,
            count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (country_id, month_key)
        )
        """)
    _ready = True


# ============================================================
#   کمکی‌های محلی کشور/اتحاد (به جداول اصلی handlers_extra.py وصل می‌شوند)
# ============================================================
def _get_country_by_owner(owner_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM countries WHERE owner_id = ?", (owner_id,)).fetchone()


def _get_membership(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)).fetchone()


def _get_alliance(alliance_id):
    """_ensure_tables() اینجا لازمه چون caller های مختلف (مثل _do_alliance_search)
    ممکنه به ستون‌های bio/join_code این نتیجه دسترسی پیدا کنن که فقط با
    ALTER TABLE داخل _ensure_tables ساخته می‌شن."""
    _ensure_tables()
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE alliance_id = ?", (alliance_id,)).fetchone()


def _get_alliance_by_name(name):
    _ensure_tables()
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE name = ?", (name,)).fetchone()


def _get_alliance_by_code(code):
    """بدون _ensure_tables، اگه ستون join_code هنوز با ALTER TABLE ساخته نشده باشه،
    این کوئری مستقیماً با OperationalError کرش می‌کنه (نه فقط None برمی‌گردونه)."""
    _ensure_tables()
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE join_code = ?", (code,)).fetchone()


def _gen_join_code():
    _ensure_tables()
    alphabet = string.ascii_uppercase + string.digits
    with get_conn() as conn:
        while True:
            code = "".join(random.choices(alphabet, k=6))
            exists = conn.execute("SELECT 1 FROM alliances WHERE join_code = ?", (code,)).fetchone()
            if not exists:
                return code


def _ensure_join_code(alliance_id):
    """اگر اتحادی از قبل ساخته شده و کد نداره (چون قبل از این آپدیت ساخته شده)، الان یکی می‌سازیم.
    باگ رفع‌شده: قبلاً اگه این تابع اولین چیزی بود که از این فایل صدا زده می‌شد (مثلاً مستقیم بعد
    از ساخت اتحاد در handlers_extra.py)، ستون join_code هنوز با ALTER TABLE اضافه نشده بود و
    کرش می‌کرد. حالا _ensure_tables() همیشه اول اجرا می‌شه."""
    _ensure_tables()
    alliance = _get_alliance(alliance_id)
    if alliance and not alliance["join_code"]:
        code = _gen_join_code()
        with get_conn() as conn:
            conn.execute("UPDATE alliances SET join_code = ? WHERE alliance_id = ?", (code, alliance_id))
        return code
    return alliance["join_code"] if alliance else None


def _join_alliance(user_id, alliance_id):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alliance_members (user_id, alliance_id, joined_at) VALUES (?, ?, ?)",
            (user_id, alliance_id, int(time.time())),
        )


def _member_count(alliance_id):
    with get_conn() as conn:
        return conn.execute(
            "SELECT COUNT(*) c FROM alliance_members WHERE alliance_id = ?", (alliance_id,)
        ).fetchone()["c"]


# ============================================================
#   ۱) تغییر نام کشور
# ============================================================
COUNTRY_RENAME_MAX_PER_MONTH = 2


def _rename_month_key(ts=None):
    ts = ts if ts is not None else time.time()
    return time.strftime("%Y-%m", time.gmtime(ts))


def _rename_count_this_month(country_id):
    _ensure_tables()
    month_key = _rename_month_key()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT count FROM country_rename_log WHERE country_id = ? AND month_key = ?",
            (country_id, month_key),
        ).fetchone()
    return row["count"] if row else 0


async def country_rename_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    country = _get_country_by_owner(user_id)

    if not country:
        await q.answer("اول باید یک کشور بسازی.", show_alert=True)
        return

    used_this_month = _rename_count_this_month(country["country_id"])
    if used_this_month >= COUNTRY_RENAME_MAX_PER_MONTH:
        await q.answer(
            f"❌ این ماه دیگه نمی‌تونی اسم رو عوض کنی — سقف {COUNTRY_RENAME_MAX_PER_MONTH} بار در ماهه.",
            show_alert=True,
        )
        return

    cost = COUNTRY_RENAME_COST_FIRST if country["rename_count"] == 0 else COUNTRY_RENAME_COST_NEXT
    user = get_user(user_id)
    if user["liber"] < cost:
        await q.answer(f"❌ برای تغییر اسم به {cost} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    context.user_data["country_rename_cost"] = cost
    context.user_data["awaiting"] = "country_rename_input"
    remaining = COUNTRY_RENAME_MAX_PER_MONTH - used_this_month
    await q.edit_message_text(
        f"✏️ اسم جدید کشورت رو بفرست.\n💰 هزینه‌ی این تغییر: {cost} LIBER\n"
        f"📅 {remaining} بار دیگه می‌تونی این ماه اسم رو عوض کنی.\n\n"
        "فرمت: با | شروع کن، بعدش کامل فارسی یا کامل انگلیسی بنویس.\n"
        "مثال فارسی: |ایران\nExample English: |Persia",
        reply_markup=back_keyboard("menu_country"),
    )


async def _do_country_rename(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    country = _get_country_by_owner(user_id)
    if not country:
        await update.message.reply_text("❌ کشوری نداری.", reply_markup=back_keyboard())
        return

    used_this_month = _rename_count_this_month(country["country_id"])
    if used_this_month >= COUNTRY_RENAME_MAX_PER_MONTH:
        await update.message.reply_text(
            f"❌ این ماه دیگه نمی‌تونی اسم رو عوض کنی — سقف {COUNTRY_RENAME_MAX_PER_MONTH} بار در ماهه.",
            reply_markup=back_keyboard("menu_country"),
        )
        return

    import handlers_extra
    ok, new_name, error_text = handlers_extra._validate_named_input(raw_text)
    if not ok:
        await update.message.reply_text(error_text)
        return

    existing = handlers_extra.get_country_by_name(new_name)
    if existing and existing["country_id"] != country["country_id"]:
        await update.message.reply_text("❌ یکی قبلاً این اسم رو برای کشورش انتخاب کرده — یه اسم دیگه بگو.")
        return

    context.user_data.pop("country_rename_cost", None)
    real_cost = COUNTRY_RENAME_COST_FIRST if country["rename_count"] == 0 else COUNTRY_RENAME_COST_NEXT

    user = get_user(user_id)
    if user["liber"] < real_cost:
        await update.message.reply_text(f"❌ LIBER کافی نیست. هزینه: {real_cost}")
        return

    update_balance(user_id, liber=-real_cost)
    month_key = _rename_month_key()
    with get_conn() as conn:
        conn.execute(
            "UPDATE countries SET name = ?, rename_count = rename_count + 1 WHERE country_id = ?",
            (new_name, country["country_id"]),
        )
        conn.execute(
            """INSERT INTO country_rename_log (country_id, month_key, count) VALUES (?, ?, 1)
               ON CONFLICT(country_id, month_key) DO UPDATE SET count = count + 1""",
            (country["country_id"], month_key),
        )
    log_transaction(user_id, "COUNTRY_RENAME", f"{new_name} cost={real_cost}")

    remaining = COUNTRY_RENAME_MAX_PER_MONTH - (used_this_month + 1)
    await update.message.reply_text(
        f"✅ اسم کشورت به «{new_name}» تغییر کرد! (-{real_cost} LIBER)\n"
        f"ℹ️ {remaining} بار دیگه می‌تونی این ماه عوضش کنی. تغییر بعدی (اگه بار اولت باشه) "
        f"{COUNTRY_RENAME_COST_NEXT} LIBER هزینه داره.",
        reply_markup=back_keyboard("menu_country"),
    )


# ============================================================
#   ۲) استپر شیشه‌ای خرید/فروش بازار
# ============================================================
def _market_stepper_keyboard(mode, amount, price, fee_pct):
    if mode == "buy":
        estimate = round(amount * price * (1 + fee_pct / 100), 2)
        confirm_label = f"✅ خرید {amount} LIBER ≈ {estimate} سکه"
    else:
        estimate = round(amount * price * (1 - fee_pct / 100), 2)
        confirm_label = f"✅ فروش {amount} LIBER ≈ {estimate} سکه"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("−10", callback_data=f"market_step:{mode}:-10"),
         InlineKeyboardButton("−1", callback_data=f"market_step:{mode}:-1"),
         InlineKeyboardButton(f"📦 {amount}", callback_data="market_step_noop"),
         InlineKeyboardButton("+1", callback_data=f"market_step:{mode}:1"),
         InlineKeyboardButton("+10", callback_data=f"market_step:{mode}:10")],
        [InlineKeyboardButton(confirm_label, callback_data=f"market_confirm:{mode}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_market")],
    ])


async def market_stepper_open_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    mode = q.data.split(":", 1)[1]  # "buy" | "sell"
    user_id = q.from_user.id

    amount = MARKET_MIN_AMOUNT
    context.user_data["market_step_amount"] = amount
    context.user_data["market_step_mode"] = mode

    price = get_market_price()
    perks = get_subscription_perks(user_id)
    fee_pct = BUY_FEE_PERCENT if mode == "buy" else SELL_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["market_fee_discount_percent"] / 100), 4)

    title = "🟢 خرید LIBER با استپر" if mode == "buy" else "🔴 فروش LIBER با استپر"
    await q.edit_message_text(
        f"{title}\n\nقیمت لحظه‌ای هر ۱ LIBER: {price} سکه\nکارمزد: {fee_pct}٪\n\n"
        "با دکمه‌های زیر مقدار رو تنظیم کن، قیمت نهایی لحظه‌ی تایید محاسبه می‌شه:",
        reply_markup=_market_stepper_keyboard(mode, amount, price, fee_pct),
    )


async def market_step_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    _, mode, delta = q.data.split(":")
    delta = int(delta)
    current = context.user_data.get("market_step_amount", MARKET_MIN_AMOUNT)
    new_amount = max(MARKET_MIN_AMOUNT, min(MARKET_MAX_AMOUNT, current + delta))
    context.user_data["market_step_amount"] = new_amount

    price = get_market_price()
    perks = get_subscription_perks(q.from_user.id)
    fee_pct = BUY_FEE_PERCENT if mode == "buy" else SELL_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["market_fee_discount_percent"] / 100), 4)

    await q.edit_message_reply_markup(reply_markup=_market_stepper_keyboard(mode, new_amount, price, fee_pct))


async def market_step_noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


async def market_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """اینجا دقیقاً همون لحظه‌ای که کاربر تایید نهایی رو می‌زنه، قیمت تازه از دیتابیس خونده می‌شه —
    یعنی اگه بین بازکردن منو و الان بازار آپدیت شده باشه (نوسان ساعتی)، محاسبه با قیمت جدید انجام می‌شه."""
    q = update.callback_query
    user_id = q.from_user.id
    mode = q.data.split(":", 1)[1]
    amount = context.user_data.get("market_step_amount", MARKET_MIN_AMOUNT)

    price = get_market_price()  # قیمت تازه، نه قیمت لحظه‌ی باز شدن منو
    perks = get_subscription_perks(user_id)
    fee_pct = BUY_FEE_PERCENT if mode == "buy" else SELL_FEE_PERCENT
    if perks:
        fee_pct = round(fee_pct * (1 - perks["market_fee_discount_percent"] / 100), 4)

    user = get_user(user_id)

    if mode == "buy":
        cost = round(amount * price * (1 + fee_pct / 100), 2)
        if user["coin"] < cost:
            await q.answer(f"❌ سکه کافی نداری. نیاز: {cost}، موجودی: {user['coin']}", show_alert=True)
            return
        await q.answer()
        update_balance(user_id, coin=-cost, liber=amount)
        log_transaction(user_id, "market_buy", f"{amount} LIBER @ {price} (stepper)")
        try:
            import handlers_social
            handlers_social.record_club_task_progress(user_id, "trade2")
        except Exception:
            pass
        result_text = f"✅ خرید موفق: {amount} LIBER با {cost} سکه (قیمت لحظه‌ی تایید: {price})."
    else:
        if user["liber"] < amount:
            await q.answer(f"❌ LIBER کافی نداری. موجودی: {round(user['liber'], 2)}", show_alert=True)
            return
        await q.answer()
        gain = round(amount * price * (1 - fee_pct / 100), 2)
        update_balance(user_id, coin=gain, liber=-amount)
        log_transaction(user_id, "market_sell", f"{amount} LIBER @ {price} (stepper)")
        try:
            import handlers_social
            handlers_social.record_club_task_progress(user_id, "trade2")
        except Exception:
            pass
        result_text = f"✅ فروش موفق: {amount} LIBER به ازای {gain} سکه (قیمت لحظه‌ی تایید: {price})."

    context.user_data["market_step_amount"] = MARKET_MIN_AMOUNT
    await q.edit_message_text(result_text, reply_markup=back_keyboard("menu_market"))


# ============================================================
#   ۳) اتحاد: جستجو با کد، آگهی عمومی، بیو
# ============================================================
async def alliance_search_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if _get_membership(q.from_user.id):
        await q.edit_message_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return
    context.user_data["awaiting"] = "alliance_search_input"
    await q.edit_message_text("🔍 اسم دقیق اتحاد یا کد ۶ حرفی‌اش رو بفرست:")


async def _do_alliance_search(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    if _get_membership(user_id):
        await update.message.reply_text("شما قبلاً عضو یک اتحاد هستید.", reply_markup=back_keyboard())
        return

    query = raw_text.strip()
    alliance = _get_alliance_by_name(query) or _get_alliance_by_code(query.upper())
    if not alliance:
        await update.message.reply_text("❌ اتحادی با این اسم/کد پیدا نشد.")
        return

    join_code = _ensure_join_code(alliance["alliance_id"])
    members_count = _member_count(alliance["alliance_id"])
    bio = alliance["bio"] or "بدون توضیحات"
    text = (
        f"🤝 {alliance['name']}\n"
        f"🔑 کد: {join_code}\n"
        f"👥 اعضا: {members_count}\n"
        f"💰 خزانه: {round(alliance['treasury'], 2)} LIBER\n\n"
        f"📝 بیو: {bio}"
    )
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ پیوستن به این اتحاد", callback_data=f"alliance_join_direct:{alliance['alliance_id']}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_alliance")],
    ])
    await update.message.reply_text(text, reply_markup=markup)


async def alliance_join_direct_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    if _get_membership(user_id):
        await q.answer("شما قبلاً عضو یک اتحاد هستید.", show_alert=True)
        return

    alliance_id = int(q.data.split(":", 1)[1])
    alliance = _get_alliance(alliance_id)
    if not alliance:
        await q.answer("این اتحاد دیگه وجود نداره.", show_alert=True)
        return

    await q.answer()
    _join_alliance(user_id, alliance_id)
    log_transaction(user_id, "JOIN_ALLIANCE", alliance["name"])
    await q.edit_message_text(f"🤝 با موفقیت به اتحاد «{alliance['name']}» پیوستی!", reply_markup=back_keyboard())


async def alliance_public_list_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    now = int(time.time())

    with get_conn() as conn:
        ads = conn.execute(
            "SELECT * FROM alliance_ads WHERE expires_at > ? ORDER BY created_at DESC LIMIT 15", (now,)
        ).fetchall()

    if not ads:
        await q.edit_message_text(
            "🌍 فعلاً هیچ اتحادی آگهی فعال نداره.\nاگه رهبر یک اتحادی، می‌تونی از دکمه‌ی «ثبت آگهی» یکی بسازی.",
            reply_markup=back_keyboard("menu_alliance"),
        )
        return

    seen = set()
    rows = []
    for ad in ads:
        if ad["alliance_id"] in seen:
            continue
        seen.add(ad["alliance_id"])
        alliance = _get_alliance(ad["alliance_id"])
        if not alliance:
            continue
        members_count = _member_count(ad["alliance_id"])
        minutes_left = max(0, (ad["expires_at"] - now) // 60)
        label = f"🤝 {alliance['name']} — {members_count} عضو — {minutes_left} دقیقه مونده"
        rows.append([InlineKeyboardButton(label, callback_data=f"alliance_join_direct:{ad['alliance_id']}")])

    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_alliance")])
    await q.edit_message_text("🌍 اتحادهایی که الان آگهی عضوگیری فعال دارن:", reply_markup=InlineKeyboardMarkup(rows))


async def alliance_ad_post_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    membership = _get_membership(user_id)
    if not membership:
        await q.answer("اول باید عضو یک اتحاد باشی.", show_alert=True)
        return

    alliance = _get_alliance(membership["alliance_id"])
    if alliance["leader_id"] != user_id:
        await q.answer("فقط رهبر اتحاد می‌تونه آگهی ثبت کنه.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < ALLIANCE_AD_COST:
        await q.answer(f"❌ برای ثبت آگهی به {ALLIANCE_AD_COST} LIBER نیاز داری.", show_alert=True)
        return

    now = int(time.time())
    with get_conn() as conn:
        active = conn.execute(
            "SELECT 1 FROM alliance_ads WHERE alliance_id = ? AND expires_at > ?",
            (membership["alliance_id"], now),
        ).fetchone()
    if active:
        await q.answer("همین الان هم یک آگهی فعال داری.", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-ALLIANCE_AD_COST)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO alliance_ads (alliance_id, created_at, expires_at) VALUES (?, ?, ?)",
            (membership["alliance_id"], now, now + ALLIANCE_AD_DURATION_SECONDS),
        )
    log_transaction(user_id, "ALLIANCE_AD_POST", str(membership["alliance_id"]))
    _ensure_join_code(membership["alliance_id"])

    await q.edit_message_text(
        f"📢 آگهی عضوگیری اتحادت برای {ALLIANCE_AD_DURATION_SECONDS // 60} دقیقه در لیست عمومی فعال شد! "
        f"(-{ALLIANCE_AD_COST} LIBER)",
        reply_markup=back_keyboard("menu_alliance"),
    )


async def alliance_bio_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    membership = _get_membership(user_id)
    if not membership:
        await q.answer("اول باید عضو یک اتحاد باشی.", show_alert=True)
        return
    alliance = _get_alliance(membership["alliance_id"])
    if alliance["leader_id"] != user_id:
        await q.answer("فقط رهبر اتحاد می‌تونه بیو رو عوض کنه.", show_alert=True)
        return

    await q.answer()
    context.user_data["awaiting"] = "alliance_bio_input"
    await q.edit_message_text("📝 متن بیوی جدید اتحاد رو بفرست (حداکثر ۲۰۰ حرف):")


async def _do_alliance_bio(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    membership = _get_membership(user_id)
    if not membership:
        await update.message.reply_text("❌ عضو اتحادی نیستی.", reply_markup=back_keyboard())
        return
    alliance = _get_alliance(membership["alliance_id"])
    if alliance["leader_id"] != user_id:
        await update.message.reply_text("❌ فقط رهبر می‌تونه بیو رو عوض کنه.", reply_markup=back_keyboard())
        return

    bio = raw_text.strip()[:200]
    with get_conn() as conn:
        conn.execute("UPDATE alliances SET bio = ? WHERE alliance_id = ?", (bio, membership["alliance_id"]))
    log_transaction(user_id, "ALLIANCE_BIO_UPDATE", "")
    await update.message.reply_text("✅ بیوی اتحاد بروزرسانی شد!", reply_markup=back_keyboard("menu_alliance"))


# ============================================================
#   دیسپچر
# ============================================================
SIMPLE_CALLBACKS = {
    "country_rename_start": country_rename_start_callback,
    "alliance_search_start": alliance_search_start_callback,
    "alliance_public_list": alliance_public_list_callback,
    "alliance_ad_post": alliance_ad_post_callback,
    "alliance_bio_start": alliance_bio_start_callback,
    "market_step_noop": market_step_noop_callback,
}


async def country_alliance_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SIMPLE_CALLBACKS:
        await SIMPLE_CALLBACKS[data](update, context)
        return True
    if data.startswith("market_stepper:"):
        await market_stepper_open_callback(update, context)
        return True
    if data.startswith("market_step:"):
        await market_step_callback(update, context)
        return True
    if data.startswith("market_confirm:"):
        await market_confirm_callback(update, context)
        return True
    if data.startswith("alliance_join_direct:"):
        await alliance_join_direct_callback(update, context)
        return True
    return False


async def country_alliance_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "country_rename_input":
        context.user_data["awaiting"] = None
        await _do_country_rename(update, context, raw_text)
        return True
    if awaiting == "alliance_search_input":
        context.user_data["awaiting"] = None
        await _do_alliance_search(update, context, raw_text)
        return True
    if awaiting == "alliance_bio_input":
        context.user_data["awaiting"] = None
        await _do_alliance_bio(update, context, raw_text)
        return True
    return False
