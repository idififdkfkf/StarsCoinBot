# -*- coding: utf-8 -*-
"""
handlers_market.py — مزایده‌ی نظامی بین کاربران (فایل جدا)
================================================================
  • مزایده‌ی صعودی واقعی (نه فروش فوری)
  • کارمزد لیست کردن: ۲۴س=۵۰ | ۴۸س=۱۰۰ | ۷۲س=۱۵۰ | ۹۶س=۲۰۰ LIBER
  • حداقل افزایش هر پیشنهاد: ۲۰ LIBER
  • آیتم لحظه‌ی ثبت مزایده امانت پیش ربات می‌مونه
  • بدون پیشنهاد → آیتم بدون کارمزد اضافه برمی‌گرده
"""
import time
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import get_conn, get_user, update_balance, log_transaction, back_keyboard

logger = logging.getLogger("LIBER.market")

LISTING_DURATIONS = {24: 50, 48: 100, 72: 150, 96: 200}
MIN_BID_INCREMENT = 20
MARKET_SWEEP_INTERVAL_SECONDS = 300


_tables_ready = False


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS market_listings (
            listing_id INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            item_key TEXT NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            start_price REAL NOT NULL,
            current_price REAL NOT NULL,
            current_bidder INTEGER,
            duration_hours INTEGER NOT NULL,
            fee_paid REAL NOT NULL,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'active'
        )
        """)
    _tables_ready = True


def get_listing(listing_id):
    _ensure_tables()
    with get_conn() as conn:
        return conn.execute("SELECT * FROM market_listings WHERE listing_id = ?", (listing_id,)).fetchone()


def list_active_listings(limit=10):
    _ensure_tables()
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM market_listings WHERE status = 'active' ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()


def _item_label(listing):
    import handlers_military as hm
    if listing["item_type"] == "soldier":
        name = hm.SOLDIER_TYPES.get(listing["item_key"], {}).get("name", listing["item_key"])
        return f"{listing['quantity']} {name}"
    else:
        name = hm.JET_BODY_TYPES.get(listing["item_key"], {}).get("name", listing["item_key"])
        return f"۱ جنگنده ({name})"


def _market_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 لیست کردن سرباز برای فروش", callback_data="market_sell_soldier_menu"),
         InlineKeyboardButton("✈️ لیست کردن جنگنده برای فروش", callback_data="market_sell_jet_menu")],
        [InlineKeyboardButton("🛒 مشاهده‌ی مزایده‌های فعال", callback_data="market_browse")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military")],
    ])


async def market_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🏛 مزایده‌ی نظامی\n\n"
        "می‌تونی سرباز یا جنگنده‌ی خودت رو بذاری مزایده، یا رو مزایده‌ی بقیه پیشنهاد بدی:",
        reply_markup=_market_menu_keyboard(),
    )


def _sell_soldier_type_keyboard():
    import handlers_military as hm
    rows = [[InlineKeyboardButton(s["name"], callback_data=f"market_sell_soldier_pick:{key}")]
            for key, s in hm.SOLDIER_TYPES.items()]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military_market")])
    return InlineKeyboardMarkup(rows)


async def market_sell_soldier_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text("📦 کدوم نوع سرباز رو می‌خوای بفروشی؟", reply_markup=_sell_soldier_type_keyboard())


async def market_sell_soldier_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user_id = q.from_user.id
    soldier_key = q.data.split(":", 1)[1]

    import handlers_military as hm
    owned = hm._get_soldier_counts(user_id).get(soldier_key, 0)
    if owned <= 0:
        await q.answer("از این نوع سرباز چیزی نداری.", show_alert=True)
        return

    await q.answer()
    context.user_data["market_item_type"] = "soldier"
    context.user_data["market_item_key"] = soldier_key
    context.user_data["market_owned"] = owned
    context.user_data["awaiting"] = "market_quantity_input"
    await q.edit_message_text(f"چند تا از این سرباز رو می‌خوای بفروشی؟ (حداکثر {owned})")


async def _do_market_quantity(update, context, raw_text):
    try:
        qty = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return
    owned = context.user_data.get("market_owned", 0)
    if qty <= 0 or qty > owned:
        await update.message.reply_text(f"❌ تعداد باید بین ۱ تا {owned} باشه.")
        return
    context.user_data["market_quantity"] = qty
    context.user_data["awaiting"] = "market_price_input"
    await update.message.reply_text("قیمت شروع مزایده رو به LIBER بفرست:")


async def _do_market_price(update, context, raw_text):
    try:
        price = float(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return
    if price <= 0:
        await update.message.reply_text("❌ قیمت باید مثبت باشه.")
        return
    context.user_data["market_price"] = price
    await update.message.reply_text(
        "مدت مزایده رو انتخاب کن:", reply_markup=_duration_keyboard()
    )


def _duration_keyboard():
    rows = [[InlineKeyboardButton(f"{hrs} ساعت — کارمزد {fee} LIBER", callback_data=f"market_duration:{hrs}")]
            for hrs, fee in LISTING_DURATIONS.items()]
    rows.append([InlineKeyboardButton("❌ لغو", callback_data="menu_military_market")])
    return InlineKeyboardMarkup(rows)


async def market_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    hours = int(q.data.split(":", 1)[1])
    fee = LISTING_DURATIONS[hours]

    item_type = context.user_data.get("market_item_type")
    item_key = context.user_data.get("market_item_key")
    price = context.user_data.get("market_price")
    quantity = context.user_data.get("market_quantity", 1)

    if not item_type or not item_key or not price:
        await q.answer("اطلاعات مزایده گم شده، دوباره شروع کن.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < fee:
        await q.answer(f"❌ برای کارمزد {hours} ساعته به {fee} LIBER نیاز داری.", show_alert=True)
        return

    import handlers_military as hm
    if item_type == "soldier":
        owned = hm._get_soldier_counts(user_id).get(item_key, 0)
        if owned < quantity:
            await q.answer("❌ دیگه به این تعداد سرباز نداری.", show_alert=True)
            return
        with get_conn() as conn:
            conn.execute(
                "UPDATE military_soldiers SET quantity = quantity - ? WHERE user_id = ? AND soldier_key = ?",
                (quantity, user_id, item_key),
            )
    else:
        with get_conn() as conn:
            jet_row = conn.execute(
                "SELECT jet_id FROM military_jets WHERE user_id = ? AND body_key = ? LIMIT 1", (user_id, item_key)
            ).fetchone()
        if not jet_row:
            await q.answer("❌ دیگه این جنگنده رو نداری.", show_alert=True)
            return
        with get_conn() as conn:
            conn.execute("DELETE FROM military_jets WHERE jet_id = ?", (jet_row["jet_id"],))

    await q.answer()
    update_balance(user_id, liber=-fee)
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO market_listings
               (seller_id, item_type, item_key, quantity, start_price, current_price, duration_hours, fee_paid, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, item_type, item_key, quantity, price, price, hours, fee, now, now + hours * 3600),
        )
    log_transaction(user_id, "MARKET_LISTING_CREATED", f"{item_type}:{item_key} x{quantity} @ {price}")

    for key in ("market_item_type", "market_item_key", "market_owned", "market_quantity", "market_price"):
        context.user_data.pop(key, None)

    await q.edit_message_text(
        f"✅ مزایده با موفقیت ثبت شد!\nقیمت شروع: {price} LIBER — مدت: {hours} ساعت (-{fee} LIBER کارمزد)",
        reply_markup=back_keyboard(),
    )


def _sell_jet_type_keyboard(user_id):
    import handlers_military as hm
    owned = hm._get_jet_counts(user_id)
    rows = []
    for key, cnt in owned.items():
        if cnt > 0 and key in hm.JET_BODY_TYPES:
            rows.append([InlineKeyboardButton(
                f"{hm.JET_BODY_TYPES[key]['name']} ({cnt} تا)", callback_data=f"market_sell_jet_pick:{key}"
            )])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military_market")])
    return InlineKeyboardMarkup(rows)


async def market_sell_jet_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    rows = _sell_jet_type_keyboard(user_id)
    if len(rows.keyboard) <= 1:
        await q.edit_message_text("هیچ جنگنده‌ای برای فروش نداری.", reply_markup=back_keyboard())
        return
    await q.edit_message_text("✈️ کدوم جنگنده رو می‌خوای بفروشی؟", reply_markup=rows)


async def market_sell_jet_pick_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    body_key = q.data.split(":", 1)[1]
    context.user_data["market_item_type"] = "jet"
    context.user_data["market_item_key"] = body_key
    context.user_data["market_quantity"] = 1
    context.user_data["awaiting"] = "market_price_input"
    await q.edit_message_text("قیمت شروع مزایده رو به LIBER بفرست:")


def _listing_view_keyboard(listing_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 پیشنهاد بده", callback_data=f"market_bid:{listing_id}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military_market")],
    ])


async def market_browse_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    listings = list_active_listings(10)
    if not listings:
        await q.edit_message_text("فعلاً هیچ مزایده‌ی فعالی نیست.", reply_markup=back_keyboard())
        return

    rows = []
    for lst in listings:
        label = f"{_item_label(lst)} — {lst['current_price']} LIBER"
        rows.append([InlineKeyboardButton(label, callback_data=f"market_view:{lst['listing_id']}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu_military_market")])
    await q.edit_message_text("🛒 مزایده‌های فعال:", reply_markup=InlineKeyboardMarkup(rows))


async def market_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    listing_id = int(q.data.split(":", 1)[1])
    listing = get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await q.edit_message_text("این مزایده دیگه فعال نیست.", reply_markup=back_keyboard())
        return

    seller = get_user(listing["seller_id"])
    seller_name = seller["first_name"] if seller else str(listing["seller_id"])
    bidder_text = "هنوز کسی پیشنهاد نداده"
    if listing["current_bidder"]:
        b = get_user(listing["current_bidder"])
        bidder_text = f"{b['first_name'] if b else listing['current_bidder']} با {listing['current_price']} LIBER"

    remaining_min = max(0, (listing["expires_at"] - int(time.time())) // 60)
    text = (
        f"🏷 {_item_label(listing)}\n\n"
        f"فروشنده: {seller_name}\n"
        f"قیمت فعلی: {listing['current_price']} LIBER\n"
        f"بالاترین پیشنهاد: {bidder_text}\n"
        f"⏳ {remaining_min} دقیقه تا پایان مزایده"
    )
    await q.edit_message_text(text, reply_markup=_listing_view_keyboard(listing_id))


async def market_bid_start_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    listing_id = int(q.data.split(":", 1)[1])
    listing = get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await q.answer("این مزایده دیگه فعال نیست.", show_alert=True)
        return
    if listing["seller_id"] == q.from_user.id:
        await q.answer("نمی‌تونی رو مزایده‌ی خودت پیشنهاد بدی.", show_alert=True)
        return

    await q.answer()
    min_bid = listing["current_price"] + MIN_BID_INCREMENT
    context.user_data["market_bid_listing"] = listing_id
    context.user_data["awaiting"] = "market_bid_amount"
    await q.edit_message_text(f"💰 حداقل پیشنهاد: {min_bid} LIBER\nمبلغ پیشنهادت رو بفرست:")


async def _do_market_bid(update, context, raw_text):
    _ensure_tables()
    user_id = update.effective_user.id
    listing_id = context.user_data.pop("market_bid_listing", None)
    if not listing_id:
        await update.message.reply_text("❌ مزایده‌ی مقصد گم شده.")
        return

    try:
        amount = float(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کن.")
        return

    listing = get_listing(listing_id)
    if not listing or listing["status"] != "active":
        await update.message.reply_text("❌ این مزایده دیگه فعال نیست.")
        return

    min_bid = listing["current_price"] + MIN_BID_INCREMENT
    if amount < min_bid:
        await update.message.reply_text(f"❌ پیشنهادت باید حداقل {min_bid} LIBER باشه.")
        return

    user = get_user(user_id)
    if user["liber"] < amount:
        await update.message.reply_text("❌ LIBER کافی نداری.")
        return

    if listing["current_bidder"]:
        update_balance(listing["current_bidder"], liber=listing["current_price"])
        try:
            await context.bot.send_message(
                listing["current_bidder"], f"😔 پیشنهادت رو کسی رد کرد. {_item_label(listing)} — پیشنهاد جدید: {amount} LIBER"
            )
        except TelegramError:
            pass

    update_balance(user_id, liber=-amount)
    with get_conn() as conn:
        conn.execute(
            "UPDATE market_listings SET current_price = ?, current_bidder = ? WHERE listing_id = ?",
            (amount, user_id, listing_id),
        )
    log_transaction(user_id, "MARKET_BID", f"listing={listing_id} amount={amount}")
    await update.message.reply_text(f"✅ پیشنهادت ({amount} LIBER) ثبت شد!", reply_markup=back_keyboard())


async def market_sweep_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    now = int(time.time())
    with get_conn() as conn:
        expired = conn.execute(
            "SELECT * FROM market_listings WHERE status = 'active' AND expires_at <= ?", (now,)
        ).fetchall()

    for listing in expired:
        await _resolve_listing(listing, context.bot)


async def _resolve_listing(listing, bot):
    with get_conn() as conn:
        conn.execute("UPDATE market_listings SET status = 'sold' WHERE listing_id = ?", (listing["listing_id"],))

    if not listing["current_bidder"]:
        _return_item_to(listing["seller_id"], listing)
        try:
            await bot.send_message(
                listing["seller_id"], f"📦 مزایده‌ی {_item_label(listing)} بدون پیشنهاد تموم شد و آیتم بهت برگشت."
            )
        except TelegramError:
            pass
        return

    _give_item_to(listing["current_bidder"], listing)
    update_balance(listing["seller_id"], liber=listing["current_price"])
    log_transaction(listing["seller_id"], "MARKET_SOLD", f"listing={listing['listing_id']} price={listing['current_price']}")
    log_transaction(listing["current_bidder"], "MARKET_WON", f"listing={listing['listing_id']}")

    try:
        await bot.send_message(
            listing["seller_id"],
            f"🎉 مزایده‌ی {_item_label(listing)} فروخته شد! +{listing['current_price']} LIBER",
        )
    except TelegramError:
        pass
    try:
        await bot.send_message(
            listing["current_bidder"],
            f"🎉 برنده‌ی مزایده‌ی {_item_label(listing)} شدی! به تسهیلات نظامی‌ت اضافه شد.",
        )
    except TelegramError:
        pass


def _return_item_to(user_id, listing):
    if listing["item_type"] == "soldier":
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO military_soldiers (user_id, soldier_key, quantity) VALUES (?, ?, ?)
                   ON CONFLICT(user_id, soldier_key) DO UPDATE SET quantity = quantity + excluded.quantity""",
                (user_id, listing["item_key"], listing["quantity"]),
            )
    else:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO military_jets (user_id, body_key, created_at) VALUES (?, ?, ?)",
                (user_id, listing["item_key"], int(time.time())),
            )


def _give_item_to(user_id, listing):
    _return_item_to(user_id, listing)


MARKET_CALLBACKS = {
    "menu_military_market": market_menu_callback,
    "market_sell_soldier_menu": market_sell_soldier_menu_callback,
    "market_sell_jet_menu": market_sell_jet_menu_callback,
    "market_browse": market_browse_callback,
}


async def market_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in MARKET_CALLBACKS:
        await MARKET_CALLBACKS[data](update, context)
        return True
    if data.startswith("market_sell_soldier_pick:"):
        await market_sell_soldier_pick_callback(update, context)
        return True
    if data.startswith("market_sell_jet_pick:"):
        await market_sell_jet_pick_callback(update, context)
        return True
    if data.startswith("market_duration:"):
        await market_duration_callback(update, context)
        return True
    if data.startswith("market_view:"):
        await market_view_callback(update, context)
        return True
    if data.startswith("market_bid:"):
        await market_bid_start_callback(update, context)
        return True
    return False


async def market_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "market_quantity_input":
        context.user_data["awaiting"] = None
        await _do_market_quantity(update, context, raw_text)
        return True
    if awaiting == "market_price_input":
        context.user_data["awaiting"] = None
        await _do_market_price(update, context, raw_text)
        return True
    if awaiting == "market_bid_amount":
        context.user_data["awaiting"] = None
        await _do_market_bid(update, context, raw_text)
        return True
    return False
