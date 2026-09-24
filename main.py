# ============================================================
# 🇮🇷 IRAN GOLF BOT BUILDER — TELEGRAM ULTRA
# One File Edition
# ============================================================
#
# Railway Environment Variables:
#
# MAIN_BOT_TOKEN=توکن_ربات_اصلی
# OWNER_ID=آیدی_عددی_شما
# REQUIRED_CHANNEL=@Iran_Golf1
#
# Optional:
# DB_PATH=data/iran_golf.sqlite3
# FREE_BROADCAST_LIMIT=150
# PORT=8080
#
# Install:
# pip install -r requirements.txt
#
# Run:
# python main.py
#
# ============================================================

import os
import re
import json
import time
import uuid
import sqlite3
import asyncio
import logging
import secrets
from datetime import datetime, timezone

from telegram import (
    Update,
    Bot,
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
    WebAppInfo,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    LabeledPrice,
)
from telegram.constants import ChatMemberStatus
from telegram.error import (
    TelegramError,
    Forbidden,
    BadRequest,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
    ContextTypes,
    filters,
)


# ============================================================
# CONFIG
# ============================================================

MAIN_BOT_TOKEN = os.getenv(
    "MAIN_BOT_TOKEN",
    ""
).strip()

OWNER_ID = int(
    os.getenv(
        "OWNER_ID",
        "0"
    ) or 0
)

REQUIRED_CHANNEL = os.getenv(
    "REQUIRED_CHANNEL",
    "@Iran_Golf1"
).strip()

DB_PATH = os.getenv(
    "DB_PATH",
    "data/iran_golf.sqlite3"
)

FREE_BROADCAST_LIMIT = int(
    os.getenv(
        "FREE_BROADCAST_LIMIT",
        "150"
    ) or 150
)

PORT = int(
    os.getenv(
        "PORT",
        "8080"
    ) or 8080
)

os.makedirs(
    os.path.dirname(DB_PATH) or ".",
    exist_ok=True
)

logging.basicConfig(
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
    level=logging.INFO,
)

log = logging.getLogger(
    "iran-golf-ultra"
)


# ============================================================
# GLOBAL CHILD BOT STORAGE
# ============================================================

CHILD_APPS = {}

CHILD_START_LOCK = asyncio.Lock()


# ============================================================
# DATABASE
# ============================================================

def db():
    con = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    con.row_factory = sqlite3.Row

    con.execute(
        "PRAGMA journal_mode=WAL"
    )

    return con


def now():
    return datetime.now(
        timezone.utc
    ).isoformat()


def init_db():

    con = db()

    con.executescript(
        """

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            last_name TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_seen TEXT NOT NULL,
            blocked INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            username TEXT DEFAULT '',
            name TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS bot_settings (
            bot_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT DEFAULT '',
            PRIMARY KEY(bot_id,key)
        );

        CREATE TABLE IF NOT EXISTS buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            action TEXT NOT NULL,
            value TEXT DEFAULT '',
            row INTEGER DEFAULT 0,
            col INTEGER DEFAULT 0,
            style TEXT DEFAULT 'reply',
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS bot_users (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT DEFAULT '',
            first_name TEXT DEFAULT '',
            joined_at TEXT NOT NULL,
            PRIMARY KEY(bot_id,user_id)
        );

        CREATE TABLE IF NOT EXISTS variables (
            bot_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            value TEXT DEFAULT '',
            PRIMARY KEY(bot_id,name)
        );

        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            answer TEXT DEFAULT '',
            status TEXT DEFAULT 'open',
            created_at TEXT NOT NULL,
            answered_at TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS subscriptions (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            PRIMARY KEY(bot_id,user_id)
        );

        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER,
            user_id INTEGER,
            event TEXT DEFAULT '',
            data TEXT DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS broadcasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            sent INTEGER DEFAULT 0,
            failed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            payload TEXT DEFAULT '',
            currency TEXT DEFAULT '',
            amount INTEGER DEFAULT 0,
            status TEXT DEFAULT 'pending',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bot_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            price INTEGER DEFAULT 0,
            currency TEXT DEFAULT 'XTR',
            payload TEXT DEFAULT '',
            active INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS admins (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT DEFAULT 'admin',
            created_at TEXT NOT NULL,
            PRIMARY KEY(bot_id,user_id)
        );

        CREATE TABLE IF NOT EXISTS banned_users (
            bot_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            reason TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            PRIMARY KEY(bot_id,user_id)
        );

        CREATE TABLE IF NOT EXISTS forced_channels (
            bot_id INTEGER NOT NULL,
            channel TEXT NOT NULL,
            PRIMARY KEY(bot_id,channel)
        );

        """
    )

    con.commit()
    con.close()


# ============================================================
# USER DATABASE
# ============================================================

def add_user(user):

    if not user:
        return

    con = db()

    con.execute(
        """
        INSERT INTO users(
            user_id,
            username,
            first_name,
            last_name,
            created_at,
            last_seen
        )
        VALUES(?,?,?,?,?,?)

        ON CONFLICT(user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            last_seen=excluded.last_seen
        """,
        (
            user.id,
            user.username or "",
            user.first_name or "",
            user.last_name or "",
            now(),
            now(),
        )
    )

    con.commit()
    con.close()


def get_user(user_id):

    con = db()

    row = con.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    con.close()

    return row


def total_users():

    con = db()

    value = con.execute(
        "SELECT COUNT(*) AS n FROM users"
    ).fetchone()["n"]

    con.close()

    return value


# ============================================================
# BOT DATABASE
# ============================================================

def create_bot(
    owner_id,
    token,
    username,
    name
):

    con = db()

    cur = con.execute(
        """
        INSERT INTO bots(
            owner_id,
            token,
            username,
            name,
            created_at
        )
        VALUES(?,?,?,?,?)
        """,
        (
            owner_id,
            token,
            username or "",
            name or "",
            now()
        )
    )

    bot_id = cur.lastrowid

    defaults = {
        "welcome":
            "سلام 👋\n"
            "به ربات خوش آمدی.",

        "about":
            "این ربات توسط "
            "Iran Golf Bot Builder "
            "ساخته شده است.",

        "contact":
            "برای ارتباط با مدیریت پیام ارسال کنید.",

        "support":
            "🎫 پیام خود را برای پشتیبانی ارسال کنید.",

        "join_required":
            "false",
    }

    for key, value in defaults.items():

        con.execute(
            """
            INSERT OR REPLACE INTO
            bot_settings(
                bot_id,
                key,
                value
            )
            VALUES(?,?,?)
            """,
            (
                bot_id,
                key,
                value
            )
        )

    con.commit()
    con.close()

    return bot_id


def get_bot(bot_id):

    con = db()

    row = con.execute(
        "SELECT * FROM bots WHERE id=?",
        (bot_id,)
    ).fetchone()

    con.close()

    return row


def get_bot_by_token(token):

    con = db()

    row = con.execute(
        "SELECT * FROM bots WHERE token=?",
        (token,)
    ).fetchone()

    con.close()

    return row


def get_owner_bots(owner_id):

    con = db()

    rows = con.execute(
        """
        SELECT *
        FROM bots
        WHERE owner_id=?
        ORDER BY id DESC
        """,
        (owner_id,)
    ).fetchall()

    con.close()

    return rows


def total_bots():

    con = db()

    n = con.execute(
        """
        SELECT COUNT(*) AS n
        FROM bots
        WHERE active=1
        """
    ).fetchone()["n"]

    con.close()

    return n


# ============================================================
# SETTINGS
# ============================================================

def get_setting(
    bot_id,
    key,
    default=""
):

    con = db()

    row = con.execute(
        """
        SELECT value
        FROM bot_settings
        WHERE bot_id=? AND key=?
        """,
        (
            bot_id,
            key
        )
    ).fetchone()

    con.close()

    if row:
        return row["value"]

    return default


def set_setting(
    bot_id,
    key,
    value
):

    con = db()

    con.execute(
        """
        INSERT INTO bot_settings(
            bot_id,
            key,
            value
        )
        VALUES(?,?,?)

        ON CONFLICT(bot_id,key)
        DO UPDATE SET
            value=excluded.value
        """,
        (
            bot_id,
            key,
            value
        )
    )

    con.commit()
    con.close()


# ============================================================
# BOT USERS
# ============================================================

def add_bot_user(
    bot_id,
    user
):

    con = db()

    con.execute(
        """
        INSERT INTO bot_users(
            bot_id,
            user_id,
            username,
            first_name,
            joined_at
        )
        VALUES(?,?,?,?,?)

        ON CONFLICT(bot_id,user_id)
        DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name
        """,
        (
            bot_id,
            user.id,
            user.username or "",
            user.first_name or "",
            now()
        )
    )

    con.commit()
    con.close()


def bot_user_ids(bot_id):

    con = db()

    rows = con.execute(
        """
        SELECT user_id
        FROM bot_users
        WHERE bot_id=?
        """,
        (bot_id,)
    ).fetchall()

    con.close()

    return [
        int(row["user_id"])
        for row in rows
    ]


def bot_user_count(bot_id):

    con = db()

    n = con.execute(
        """
        SELECT COUNT(*) AS n
        FROM bot_users
        WHERE bot_id=?
        """,
        (bot_id,)
    ).fetchone()["n"]

    con.close()

    return n


# ============================================================
# BUTTON SYSTEM
# ============================================================

def add_button(
    bot_id,
    text,
    action,
    value="",
    row=0,
    col=0,
    style="reply"
):

    con = db()

    con.execute(
        """
        INSERT INTO buttons(
            bot_id,
            text,
            action,
            value,
            row,
            col,
            style
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            bot_id,
            text,
            action,
            value,
            row,
            col,
            style
        )
    )

    con.commit()
    con.close()


def get_buttons(
    bot_id,
    style=None
):

    con = db()

    if style:

        rows = con.execute(
            """
            SELECT *
            FROM buttons
            WHERE bot_id=?
            AND style=?
            AND active=1
            ORDER BY row,col,id
            """,
            (
                bot_id,
                style
            )
        ).fetchall()

    else:

        rows = con.execute(
            """
            SELECT *
            FROM buttons
            WHERE bot_id=?
            AND active=1
            ORDER BY row,col,id
            """,
            (bot_id,)
        ).fetchall()

    con.close()

    return rows


def delete_button(
    button_id,
    bot_id
):

    con = db()

    con.execute(
        """
        UPDATE buttons
        SET active=0
        WHERE id=? AND bot_id=?
        """,
        (
            button_id,
            bot_id
        )
    )

    con.commit()
    con.close()


# ============================================================
# LOGGING
# ============================================================

def log_event(
    bot_id,
    user_id,
    event,
    data=""
):

    con = db()

    con.execute(
        """
        INSERT INTO logs(
            bot_id,
            user_id,
            event,
            data,
            created_at
        )
        VALUES(?,?,?,?,?)
        """,
        (
            bot_id,
            user_id,
            event,
            data,
            now()
        )
    )

    con.commit()
    con.close()


# ============================================================
# VARIABLES
# ============================================================

def set_variable(
    bot_id,
    name,
    value
):

    con = db()

    con.execute(
        """
        INSERT INTO variables(
            bot_id,
            name,
            value
        )
        VALUES(?,?,?)

        ON CONFLICT(bot_id,name)
        DO UPDATE SET
            value=excluded.value
        """,
        (
            bot_id,
            name,
            value
        )
    )

    con.commit()
    con.close()


def get_variable(
    bot_id,
    name,
    default=""
):

    con = db()

    row = con.execute(
        """
        SELECT value
        FROM variables
        WHERE bot_id=? AND name=?
        """,
        (
            bot_id,
            name
        )
    ).fetchone()

    con.close()

    return row["value"] if row else default


# ============================================================
# MEMBERSHIP
# ============================================================

async def is_member(
    bot,
    user_id,
    channel
):

    try:

        member = await bot.get_chat_member(
            channel,
            user_id
        )

        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }

    except TelegramError:

        return False


async def check_required_join(
    bot,
    user_id
):

    if not REQUIRED_CHANNEL:
        return True

    return await is_member(
        bot,
        user_id,
        REQUIRED_CHANNEL
    )


def join_keyboard():

    username = REQUIRED_CHANNEL.lstrip("@")

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📢 عضویت در کانال",
                url=f"https://t.me/{username}"
            )
        ],
        [
            InlineKeyboardButton(
                "✅ بررسی عضویت",
                callback_data="join:check"
            )
        ]
    ])


# ============================================================
# CAPTCHA
# ============================================================

def make_captcha():

    a = secrets.randbelow(9) + 1
    b = secrets.randbelow(9) + 1

    return a, b, a + b


# ============================================================
# MAIN KEYBOARD
# ============================================================

def main_keyboard():

    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("🤖 ساخت ربات"),
                KeyboardButton("📦 ربات‌های من"),
            ],
            [
                KeyboardButton("👤 حساب کاربری"),
                KeyboardButton("🎫 پشتیبانی"),
            ],
            [
                KeyboardButton("⭐ امکانات"),
                KeyboardButton("📚 راهنما"),
            ],
        ],
        resize_keyboard=True,
        is_persistent=True
    )


# ============================================================
# OWNER PANEL
# ============================================================

def owner_keyboard():

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 آمار",
                callback_data="owner:stats"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="owner:users"
            ),
            InlineKeyboardButton(
                "🤖 ربات‌ها",
                callback_data="owner:bots"
            )
        ],
        [
            InlineKeyboardButton(
                "📣 Broadcast",
                callback_data="owner:broadcast"
            ),
            InlineKeyboardButton(
                "🎫 تیکت‌ها",
                callback_data="owner:tickets"
            )
        ],
    ])


# ============================================================
# BOT PANEL
# ============================================================

def bot_panel(bot_id):

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data=f"bot:users:{bot_id}"
            ),
            InlineKeyboardButton(
                "🎨 دکمه‌ها",
                callback_data=f"bot:buttons:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "👋 خوش‌آمد",
                callback_data=f"bot:welcome:{bot_id}"
            ),
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data=f"bot:settings:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "📣 Broadcast",
                callback_data=f"bot:broadcast:{bot_id}"
            )
        ],
        [
            InlineKeyboardButton(
                "⛔ توقف",
                callback_data=f"bot:stop:{bot_id}"
            ),
            InlineKeyboardButton(
                "▶️ اجرا",
                callback_data=f"bot:start:{bot_id}"
            )
        ],
    ])


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    user = update.effective_user

    add_user(user)

    if not context.user_data.get(
        "captcha_ok"
    ):

        a, b, answer = make_captcha()

        context.user_data[
            "captcha_answer"
        ] = answer

        await update.message.reply_text(
            "🛡️ تأیید امنیتی\n\n"
            f"➕ {a} + {b} = ؟\n\n"
            "جواب را فقط به صورت عدد بفرست."
        )

        return

    if not await check_required_join(
        context.bot,
        user.id
    ):

        await update.message.reply_text(
            "🔒 برای استفاده از ربات ابتدا "
            "عضو کانال شوید:",
            reply_markup=join_keyboard()
        )

        return

    await update.message.reply_text(
        "🔥 به Iran Golf Bot Builder خوش آمدی!\n\n"
        "با این ربات می‌توانی ربات تلگرامی خودت "
        "را بسازی و مدیریت کنی.",
        reply_markup=main_keyboard()
    )


# ============================================================
# CREATE BOT
# ============================================================

async def begin_create_bot(
    update,
    context
):

    context.user_data[
        "state"
    ] = "bot_name"

    await update.message.reply_text(
        "🚀 ساخت ربات جدید\n\n"
        "اسم ربات را بفرست:"
    )


async def process_create_bot(
    update,
    context
):

    text = (
        update.message.text or ""
    ).strip()

    state = context.user_data.get(
        "state"
    )

    if state == "bot_name":

        context.user_data[
            "new_bot_name"
        ] = text

        context.user_data[
            "state"
        ] = "bot_token"

        await update.message.reply_text(
            "✅ نام ذخیره شد.\n\n"
            "حالا توکن ربات را که از "
            "@BotFather گرفته‌ای بفرست."
        )

        return True

    if state == "bot_token":

        token = text

        if not re.fullmatch(
            r"\d{5,12}:[A-Za-z0-9_-]{20,}",
            token
        ):

            await update.message.reply_text(
                "❌ فرمت توکن درست نیست."
            )

            return True

        await update.message.reply_text(
            "⏳ در حال بررسی توکن..."
        )

        try:

            test_bot = Bot(
                token=token
            )

            me = await test_bot.get_me()

            await test_bot.close()

        except Exception:

            await update.message.reply_text(
                "❌ توکن معتبر نیست."
            )

            return True

        if get_bot_by_token(token):

            await update.message.reply_text(
                "⚠️ این ربات قبلاً ثبت شده."
            )

            return True

        name = context.user_data.get(
            "new_bot_name",
            me.first_name or "Bot"
        )

        bot_id = create_bot(
            update.effective_user.id,
            token,
            me.username,
            name
        )

        add_button(
            bot_id,
            "🏠 خانه",
            "home",
            row=0,
            col=0,
            style="reply"
        )

        add_button(
            bot_id,
            "ℹ️ درباره ما",
            "about",
            row=0,
            col=1,
            style="reply"
        )

        add_button(
            bot_id,
            "🎫 پشتیبانی",
            "support",
            row=1,
            col=0,
            style="reply"
        )

        add_button(
            bot_id,
            "📞 تماس",
            "contact",
            row=1,
            col=1,
            style="reply"
        )

        context.user_data.pop(
            "state",
            None
        )

        context.user_data.pop(
            "new_bot_name",
            None
        )

        await start_child_bot(
            bot_id,
            token
        )

        link = (
            f"https://t.me/{me.username}"
            if me.username
            else "-"
        )

        await update.message.reply_text(
            "🎉 ربات ساخته شد!\n\n"
            f"🤖 نام: {me.first_name}\n"
            f"🔗 @{me.username or '-'}\n"
            f"🆔 ID: {me.id}\n\n"
            f"🚀 لینک:\n{link}",
            reply_markup=main_keyboard()
        )

        return True

    return False


# ============================================================
# MAIN TEXT HANDLER
# ============================================================

async def main_text(
    update,
    context
):

    if not update.message:
        return

    user = update.effective_user

    add_user(user)

    text = (
        update.message.text or ""
    ).strip()

    # CAPTCHA
    if "captcha_answer" in context.user_data:

        answer = context.user_data[
            "captcha_answer"
        ]

        if text.isdigit() and int(text) == answer:

            context.user_data[
                "captcha_ok"
            ] = True

            context.user_data.pop(
                "captcha_answer",
                None
            )

            await update.message.reply_text(
                "✅ تأیید شد!\n\n"
                "حالا عضویت کانال را بررسی کن.",
                reply_markup=join_keyboard()
            )

        else:

            await update.message.reply_text(
                "❌ جواب اشتباه است."
            )

        return

    if not context.user_data.get(
        "captcha_ok"
    ):

        await start(
            update,
            context
        )

        return

    if not await check_required_join(
        context.bot,
        user.id
    ):

        await update.message.reply_text(
            "🔒 ابتدا عضو کانال شوید.",
            reply_markup=join_keyboard()
        )

        return

    # CREATE
    if text == "🤖 ساخت ربات":

        await begin_create_bot(
            update,
            context
        )

        return

    # MY BOTS
    if text == "📦 ربات‌های من":

        rows = get_owner_bots(
            user.id
        )

        if not rows:

            await update.message.reply_text(
                "📦 هنوز رباتی نساخته‌ای."
            )

            return

        keyboard = []

        for row in rows:

            keyboard.append([
                InlineKeyboardButton(
                    (
                        "🤖 " +
                        (
                            row["name"]
                            or row["username"]
                            or "Bot"
                        )
                    ),
                    callback_data=(
                        f"openbot:{row['id']}"
                    )
                )
            ])

        await update.message.reply_text(
            "📦 ربات‌های شما:",
            reply_markup=InlineKeyboardMarkup(
                keyboard
            )
        )

        return

    # PROFILE
    if text == "👤 حساب کاربری":

        await update.message.reply_text(
            "👤 حساب کاربری\n\n"
            f"🆔 ID: `{user.id}`\n"
            f"👤 نام: {user.full_name}\n"
            f"🔗 Username: "
            f"@{user.username or '-'}",
            parse_mode="Markdown"
        )

        return

    # SUPPORT
    if text == "🎫 پشتیبانی":

        context.user_data[
            "state"
        ] = "support"

        await update.message.reply_text(
            "🎫 پیام خود را بفرست."
        )

        return

    # FEATURES
    if text == "⭐ امکانات":

        await update.message.reply_text(
            "⭐ امکانات سیستم\n\n"
            "🤖 ساخت چند ربات\n"
            "🎨 Reply Keyboard\n"
            "🔘 Inline Keyboard\n"
            "🌐 WebApp\n"
            "📣 Broadcast\n"
            "👥 مدیریت کاربران\n"
            "🎫 پشتیبانی\n"
            "📊 آمار\n"
            "🔐 عضویت اجباری\n"
            "👮 ادمین\n"
            "🚫 Ban / Unban\n"
            "📌 Pin / Unpin\n"
            "📊 Poll\n"
            "💎 Stars / Payments\n"
            "🎁 Gifts\n"
            "📱 Mini App\n"
            "🧩 Variables"
        )

        return

    # HELP
    if text == "📚 راهنما":

        await update.message.reply_text(
            "📚 راهنما\n\n"
            "۱. ساخت ربات را بزن.\n"
            "۲. نام را وارد کن.\n"
            "۳. توکن BotFather را بفرست.\n"
            "۴. ربات اجرا می‌شود.\n"
            "۵. از پنل مدیریت استفاده کن."
        )

        return

    # CREATE STATES
    if await process_create_bot(
        update,
        context
    ):

        return

    # SUPPORT STATE
    if context.user_data.get(
        "state"
    ) == "support":

        context.user_data.pop(
            "state",
            None
        )

        if OWNER_ID:

            try:

                await context.bot.send_message(
                    OWNER_ID,
                    "🎫 تیکت جدید\n\n"
                    f"👤 {user.full_name}\n"
                    f"🆔 {user.id}\n\n"
                    f"💬 {text}"
                )

            except TelegramError:
                pass

        await update.message.reply_text(
            "✅ پیام شما برای پشتیبانی ارسال شد.",
            reply_markup=main_keyboard()
        )

        return

    # BROADCAST
    if context.user_data.get(
        "state"
    ) == "global_broadcast":

        if user.id != OWNER_ID:
            return

        await global_broadcast(
            update,
            context,
            text
        )

        return

    await update.message.reply_text(
        "از منوی پایین استفاده کن 👇",
        reply_markup=main_keyboard()
    )


# ============================================================
# MAIN CALLBACK
# ============================================================

async def main_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    # JOIN
    if data == "join:check":

        if await check_required_join(
            context.bot,
            query.from_user.id
        ):

            context.user_data[
                "captcha_ok"
            ] = True

            await query.message.reply_text(
                "✅ عضویت تأیید شد!",
                reply_markup=main_keyboard()
            )

        else:

            await query.answer(
                "❌ هنوز عضو کانال نیستید.",
                show_alert=True
            )

        return

    # OPEN BOT
    if data.startswith(
        "openbot:"
    ):

        bot_id = int(
            data.split(":")[1]
        )

        row = get_bot(bot_id)

        if not row:
            return

        if row["owner_id"] != query.from_user.id:
            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )
            return

        await query.message.reply_text(
            "⚙️ پنل مدیریت ربات\n\n"
            f"🤖 {row['name']}\n"
            f"🔗 @{row['username'] or '-'}\n"
            f"👥 کاربران: "
            f"{bot_user_count(bot_id)}",
            reply_markup=bot_panel(bot_id)
        )

        return

    # BOT PANEL
    if data.startswith(
        "bot:"
    ):

        parts = data.split(":")

        if len(parts) != 3:
            return

        action = parts[1]
        bot_id = int(parts[2])

        row = get_bot(bot_id)

        if not row:
            return

        if row["owner_id"] != query.from_user.id:

            await query.answer(
                "⛔ دسترسی ندارید.",
                show_alert=True
            )

            return

        if action == "users":

            await query.message.reply_text(
                "👥 کاربران ربات:\n\n"
                f"{bot_user_count(bot_id)} نفر"
            )

        elif action == "welcome":

            await query.message.reply_text(
                "👋 پیام خوش‌آمد:\n\n"
                + get_setting(
                    bot_id,
                    "welcome"
                )
            )

        elif action == "settings":

            await query.message.reply_text(
                "⚙️ تنظیمات ربات\n\n"
                "از ساختار تنظیمات این پنل "
                "برای توسعه قابلیت‌ها استفاده کن."
            )

        elif action == "buttons":

            buttons = get_buttons(
                bot_id
            )

            if not buttons:

                await query.message.reply_text(
                    "هنوز دکمه‌ای وجود ندارد."
                )

                return

            text = "🎨 دکمه‌های فعال:\n\n"

            for b in buttons:

                text += (
                    f"• {b['text']} "
                    f"→ {b['action']}\n"
                )

            await query.message.reply_text(
                text
            )

        elif action == "broadcast":

            context.user_data[
                "state"
            ] = "bot_broadcast"

            context.user_data[
                "broadcast_bot"
            ] = bot_id

            await query.message.reply_text(
                "📣 متن Broadcast را بفرست."
            )

        elif action == "stop":

            con = db()

            con.execute(
                """
                UPDATE bots
                SET active=0
                WHERE id=?
                """,
                (bot_id,)
            )

            con.commit()
            con.close()

            await stop_child_bot(
                row["token"]
            )

            await query.message.reply_text(
                "⛔ ربات متوقف شد."
            )

        elif action == "start":

            con = db()

            con.execute(
                """
                UPDATE bots
                SET active=1
                WHERE id=?
                """,
                (bot_id,)
            )

            con.commit()
            con.close()

            await start_child_bot(
                bot_id,
                row["token"]
            )

            await query.message.reply_text(
                "▶️ ربات فعال شد."
            )

        return

    # OWNER
    if data.startswith(
        "owner:"
    ):

        if query.from_user.id != OWNER_ID:

            await query.answer(
                "⛔ فقط مدیر اصلی.",
                show_alert=True
            )

            return

        action = data.split(":")[1]

        if action == "stats":

            await query.message.reply_text(
                "📊 آمار\n\n"
                f"👥 کاربران: {total_users()}\n"
                f"🤖 ربات‌ها: {total_bots()}"
            )

        elif action == "users":

            await query.message.reply_text(
                f"👥 تعداد کاربران:\n"
                f"{total_users()}"
            )

        elif action == "bots":

            await query.message.reply_text(
                f"🤖 تعداد ربات‌های فعال:\n"
                f"{total_bots()}"
            )

        elif action == "broadcast":

            context.user_data[
                "state"
            ] = "global_broadcast"

            await query.message.reply_text(
                "📣 متن Broadcast را بفرست."
            )

        return


# ============================================================
# BROADCAST
# ============================================================

async def broadcast_to_users(
    bot,
    user_ids,
    text,
    limit=None
):

    sent = 0
    failed = 0

    if limit:
        user_ids = user_ids[:limit]

    for user_id in user_ids:

        try:

            await bot.send_message(
                user_id,
                text
            )

            sent += 1

        except (
            TelegramError,
            Forbidden,
            BadRequest
        ):

            failed += 1

        await asyncio.sleep(
            0.05
        )

    return sent, failed


async def global_broadcast(
    update,
    context,
    text
):

    con = db()

    rows = con.execute(
        """
        SELECT user_id
        FROM users
        WHERE blocked=0
        """
    ).fetchall()

    con.close()

    ids = [
        int(row["user_id"])
        for row in rows
    ]

    sent, failed = await broadcast_to_users(
        context.bot,
        ids,
        text,
        FREE_BROADCAST_LIMIT
    )

    context.user_data.pop(
        "state",
        None
    )

    await update.message.reply_text(
        "📣 Broadcast تمام شد.\n\n"
        f"✅ ارسال: {sent}\n"
        f"❌ خطا: {failed}"
    )


# ============================================================
# CHILD KEYBOARDS
# ============================================================

def child_reply_keyboard(
    bot_id
):

    buttons = get_buttons(
        bot_id,
        "reply"
    )

    rows = {}

    for button in buttons:

        row = int(
            button["row"]
        )

        rows.setdefault(
            row,
            []
        ).append(
            KeyboardButton(
                button["text"]
            )
        )

    if not rows:
        return None

    return ReplyKeyboardMarkup(
        [
            rows[key]
            for key in sorted(rows)
        ],
        resize_keyboard=True,
        is_persistent=True
    )


def child_inline_keyboard(
    bot_id
):

    buttons = get_buttons(
        bot_id,
        "inline"
    )

    rows = {}

    for button in buttons:

        row = int(
            button["row"]
        )

        rows.setdefault(
            row,
            []
        ).append(
            InlineKeyboardButton(
                button["text"],
                callback_data=(
                    f"button:{button['id']}"
                )
            )
        )

    if not rows:
        return None

    return InlineKeyboardMarkup(
        [
            rows[key]
            for key in sorted(rows)
        ]
    )


# ============================================================
# VARIABLE RENDER
# ============================================================

def render_text(
    text,
    user,
    bot_id
):

    replacements = {

        "{{user_id}}":
            str(user.id),

        "{{username}}":
            user.username or "",

        "{{first_name}}":
            user.first_name or "",

        "{{last_name}}":
            user.last_name or "",

        "{{name}}":
            user.full_name or "",
    }

    for key, value in replacements.items():

        text = text.replace(
            key,
            value
        )

    return text


# ============================================================
# CHILD START
# ============================================================

async def child_start(
    update,
    context
):

    bot_id = context.bot_data[
        "bot_id"
    ]

    user = update.effective_user

    add_bot_user(
        bot_id,
        user
    )

    add_user(
        user
    )

    if await is_banned(
        bot_id,
        user.id
    ):

        await update.message.reply_text(
            "🚫 شما از این ربات مسدود شده‌اید."
        )

        return

    log_event(
        bot_id,
        user.id,
        "start"
    )

    welcome = render_text(
        get_setting(
            bot_id,
            "welcome",
            "سلام 👋"
        ),
        user,
        bot_id
    )

    inline = child_inline_keyboard(
        bot_id
    )

    await update.message.reply_text(
        welcome,
        reply_markup=inline
        or child_reply_keyboard(bot_id)
    )


# ============================================================
# CHILD TEXT
# ============================================================

async def child_text(
    update,
    context
):

    bot_id = context.bot_data[
        "bot_id"
    ]

    user = update.effective_user

    add_bot_user(
        bot_id,
        user
    )

    text = (
        update.message.text or ""
    ).strip()

    if await is_banned(
        bot_id,
        user.id
    ):

        await update.message.reply_text(
            "🚫 دسترسی شما مسدود است."
        )

        return

    con = db()

    button = con.execute(
        """
        SELECT *
        FROM buttons
        WHERE bot_id=?
        AND text=?
        AND style='reply'
        AND active=1
        LIMIT 1
        """,
        (
            bot_id,
            text
        )
    ).fetchone()

    con.close()

    if button:

        await execute_action(
            update.message,
            user,
            bot_id,
            button["action"],
            button["value"]
        )

        return

    await update.message.reply_text(
        "پیامت دریافت شد.",
        reply_markup=child_reply_keyboard(
            bot_id
        )
    )


# ============================================================
# CHILD CALLBACK
# ============================================================

async def child_callback(
    update,
    context
):

    query = update.callback_query

    await query.answer()

    bot_id = context.bot_data[
        "bot_id"
    ]

    user = query.from_user

    if query.data.startswith(
        "button:"
    ):

        button_id = int(
            query.data.split(":")[1]
        )

        con = db()

        button = con.execute(
            """
            SELECT *
            FROM buttons
            WHERE id=? AND bot_id=?
            """,
            (
                button_id,
                bot_id
            )
        ).fetchone()

        con.close()

        if not button:
            return

        await execute_action(
            query.message,
            user,
            bot_id,
            button["action"],
            button["value"]
        )


# ============================================================
# CHILD ACTIONS
# ============================================================

async def execute_action(
    message,
    user,
    bot_id,
    action,
    value
):

    value = render_text(
        value or "",
        user,
        bot_id
    )

    if action == "home":

        await message.reply_text(
            render_text(
                get_setting(
                    bot_id,
                    "welcome",
                    "سلام 👋"
                ),
                user,
                bot_id
            ),
            reply_markup=child_reply_keyboard(
                bot_id
            )
        )

    elif action == "about":

        await message.reply_text(
            render_text(
                get_setting(
                    bot_id,
                    "about",
                    "درباره ما"
                ),
                user,
                bot_id
            )
        )

    elif action == "contact":

        await message.reply_text(
            render_text(
                get_setting(
                    bot_id,
                    "contact",
                    "تماس با ما"
                ),
                user,
                bot_id
            )
        )

    elif action == "support":

        await message.reply_text(
            render_text(
                get_setting(
                    bot_id,
                    "support",
                    "پیام خود را بفرست."
                ),
                user,
                bot_id
            )
        )

    elif action == "message":

        await message.reply_text(
            value or "پیام تنظیم نشده."
        )

    elif action == "url":

        await message.reply_text(
            value or "لینک تنظیم نشده."
        )

    elif action == "channel":

        await message.reply_text(
            "📢 کانال:\n"
            + (
                value
                or REQUIRED_CHANNEL
            )
        )

    elif action == "variable":

        await message.reply_text(
            value
        )

    elif action == "id":

        await message.reply_text(
            f"🆔 ID شما:\n{user.id}"
        )

    elif action == "username":

        await message.reply_text(
            f"🔗 Username:\n"
            f"@{user.username or '-'}"
        )

    else:

        await message.reply_text(
            value or
            "✅ عملیات انجام شد."
        )


# ============================================================
# BAN SYSTEM
# ============================================================

def is_banned(
    bot_id,
    user_id
):

    con = db()

    row = con.execute(
        """
        SELECT user_id
        FROM banned_users
        WHERE bot_id=? AND user_id=?
        """,
        (
            bot_id,
            user_id
        )
    ).fetchone()

    con.close()

    return bool(row)


def ban_user(
    bot_id,
    user_id,
    reason=""
):

    con = db()

    con.execute(
        """
        INSERT OR REPLACE INTO banned_users(
            bot_id,
            user_id,
            reason,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            bot_id,
            user_id,
            reason,
            now()
        )
    )

    con.commit()
    con.close()


def unban_user(
    bot_id,
    user_id
):

    con = db()

    con.execute(
        """
        DELETE FROM banned_users
        WHERE bot_id=? AND user_id=?
        """,
        (
            bot_id,
            user_id
        )
    )

    con.commit()
    con.close()


# ============================================================
# ADMIN SYSTEM
# ============================================================

def is_admin(
    bot_id,
    user_id
):

    bot = get_bot(
        bot_id
    )

    if bot and bot["owner_id"] == user_id:
        return True

    con = db()

    row = con.execute(
        """
        SELECT user_id
        FROM admins
        WHERE bot_id=? AND user_id=?
        """,
        (
            bot_id,
            user_id
        )
    ).fetchone()

    con.close()

    return bool(row)


def add_admin(
    bot_id,
    user_id,
    role="admin"
):

    con = db()

    con.execute(
        """
        INSERT OR REPLACE INTO admins(
            bot_id,
            user_id,
            role,
            created_at
        )
        VALUES(?,?,?,?)
        """,
        (
            bot_id,
            user_id,
            role,
            now()
        )
    )

    con.commit()
    con.close()


def remove_admin(
    bot_id,
    user_id
):

    con = db()

    con.execute(
        """
        DELETE FROM admins
        WHERE bot_id=? AND user_id=?
        """,
        (
            bot_id,
            user_id
        )
    )

    con.commit()
    con.close()


# ============================================================
# STARS / PAYMENTS
# ============================================================

def add_payment(
    bot_id,
    user_id,
    payload,
    currency,
    amount,
    status
):

    con = db()

    con.execute(
        """
        INSERT INTO payments(
            bot_id,
            user_id,
            payload,
            currency,
            amount,
            status,
            created_at
        )
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            bot_id,
            user_id,
            payload,
            currency,
            amount,
            status,
            now()
        )
    )

    con.commit()
    con.close()


async def send_stars_invoice(
    bot,
    chat_id,
    title,
    description,
    payload,
    stars
):

    prices = [
        LabeledPrice(
            "⭐ Stars",
            int(stars)
        )
    ]

    await bot.send_invoice(
        chat_id=chat_id,
        title=title,
        description=description,
        payload=payload,
        provider_token="",
        currency="XTR",
        prices=prices
    )


async def precheckout_handler(
    update,
    context
):

    query = update.pre_checkout_query

    await query.answer(
        ok=True
    )


async def successful_payment(
    update,
    context
):

    payment = (
        update.message.successful_payment
    )

    if not payment:
        return

    bot_id = context.bot_data.get(
        "bot_id",
        0
    )

    add_payment(
        bot_id,
        update.effective_user.id,
        payment.invoice_payload,
        payment.currency,
        payment.total_amount,
        "paid"
    )

    await update.message.reply_text(
        "✅ پرداخت با موفقیت انجام شد.\n"
        "⭐ موجودی/محصول شما ثبت شد."
    )


# ============================================================
# GIFTS / STARS RAW API HELPERS
# ============================================================

async def telegram_api(
    bot_token,
    method,
    data=None
):

    import urllib.request
    import urllib.parse

    url = (
        "https://api.telegram.org/bot"
        + bot_token
        + "/"
        + method
    )

    payload = urllib.parse.urlencode(
        data or {}
    ).encode()

    def request():

        req = urllib.request.Request(
            url,
            data=payload,
            method="POST"
        )

        with urllib.request.urlopen(
            req,
            timeout=30
        ) as response:

            return response.read().decode()

    return await asyncio.to_thread(
        request
    )


async def get_available_gifts(
    bot_token
):

    try:

        return await telegram_api(
            bot_token,
            "getAvailableGifts"
        )

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc)
        }


# ============================================================
# PIN MESSAGE
# ============================================================

async def pin_message(
    bot,
    chat_id,
    message_id
):

    try:

        await bot.pin_chat_message(
            chat_id=chat_id,
            message_id=message_id,
            disable_notification=True
        )

        return True

    except TelegramError:

        return False


async def unpin_message(
    bot,
    chat_id,
    message_id
):

    try:

        await bot.unpin_chat_message(
            chat_id=chat_id,
            message_id=message_id
        )

        return True

    except TelegramError:

        return False


# ============================================================
# POLL
# ============================================================

async def send_poll(
    bot,
    chat_id,
    question,
    options,
    anonymous=True
):

    try:

        await bot.send_poll(
            chat_id=chat_id,
            question=question,
            options=options,
            is_anonymous=anonymous
        )

        return True

    except TelegramError:

        return False


# ============================================================
# MEDIA HELPERS
# ============================================================

async def send_photo(
    bot,
    chat_id,
    photo,
    caption=""
):

    return await bot.send_photo(
        chat_id=chat_id,
        photo=photo,
        caption=caption
    )


async def send_video(
    bot,
    chat_id,
    video,
    caption=""
):

    return await bot.send_video(
        chat_id=chat_id,
        video=video,
        caption=caption
    )


async def send_document(
    bot,
    chat_id,
    document,
    caption=""
):

    return await bot.send_document(
        chat_id=chat_id,
        document=document,
        caption=caption
    )


# ============================================================
# CHILD APPLICATION
# ============================================================

async def start_child_bot(
    bot_id,
    token
):

    async with CHILD_START_LOCK:

        if token in CHILD_APPS:
            return

        row = get_bot(
            bot_id
        )

        if not row:
            return

        if not row["active"]:
            return

        try:

            application = (
                Application
                .builder()
                .token(token)
                .build()
            )

            application.bot_data[
                "bot_id"
            ] = bot_id

            application.add_handler(
                CommandHandler(
                    "start",
                    child_start
                )
            )

            application.add_handler(
                CallbackQueryHandler(
                    child_callback
                )
            )

            application.add_handler(
                PreCheckoutQueryHandler(
                    precheckout_handler
                )
            )

            application.add_handler(
                MessageHandler(
                    filters.SUCCESSFUL_PAYMENT,
                    successful_payment
                )
            )

            application.add_handler(
                MessageHandler(
                    filters.TEXT
                    & ~filters.COMMAND,
                    child_text
                )
            )

            await application.initialize()

            await application.start()

            await application.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True
            )

            CHILD_APPS[
                token
            ] = application

            log.info(
                "Child bot started: %s",
                row["username"]
            )

        except Exception:

            log.exception(
                "Could not start child bot"
            )


async def stop_child_bot(
    token
):

    application = CHILD_APPS.pop(
        token,
        None
    )

    if not application:
        return

    try:

        if (
            application.updater
            and application.updater.running
        ):

            await application.updater.stop()

        await application.stop()

        await application.shutdown()

    except Exception:

        log.exception(
            "Could not stop child bot"
        )


async def load_child_bots():

    con = db()

    rows = con.execute(
        """
        SELECT id, token
        FROM bots
        WHERE active=1
        """
    ).fetchall()

    con.close()

    for row in rows:

        await start_child_bot(
            row["id"],
            row["token"]
        )

        await asyncio.sleep(
            0.3
        )


# ============================================================
# OWNER COMMANDS
# ============================================================

async def panel(
    update,
    context
):

    if update.effective_user.id != OWNER_ID:

        await update.message.reply_text(
            "⛔ دسترسی ندارید."
        )

        return

    await update.message.reply_text(
        "👑 پنل مدیریت اصلی\n\n"
        "Iran Golf Bot Builder",
        reply_markup=owner_keyboard()
    )


async def my_id(
    update,
    context
):

    await update.message.reply_text(
        "🆔 آیدی عددی شما:\n\n"
        f"`{update.effective_user.id}`",
        parse_mode="Markdown"
    )


# ============================================================
# BOTFATHER-LIKE HELP
# ============================================================

async def botfather_help(
    update,
    context
):

    await update.message.reply_text(
        "🤖 راهنمای ساخت ربات\n\n"
        "۱️⃣ وارد @BotFather شو.\n"
        "۲️⃣ /newbot را بزن.\n"
        "۳️⃣ نام ربات را انتخاب کن.\n"
        "۴️⃣ username را انتخاب کن.\n"
        "۵️⃣ Token را دریافت کن.\n"
        "۶️⃣ Token را فقط داخل پنل خودت وارد کن.\n\n"
        "⚠️ Token را عمومی منتشر نکن."
    )


# ============================================================
# POST INIT
# ============================================================

async def post_init(
    application
):

    init_db()

    try:

        await application.bot.set_my_commands([
            BotCommand(
                "start",
                "شروع"
            ),
            BotCommand(
                "panel",
                "پنل مدیریت"
            ),
            BotCommand(
                "id",
                "آیدی من"
            ),
            BotCommand(
                "botfather",
                "راهنمای ساخت ربات"
            ),
        ])

    except TelegramError:

        pass

    await load_child_bots()


# ============================================================
# POST SHUTDOWN
# ============================================================

async def post_shutdown(
    application
):

    tokens = list(
        CHILD_APPS.keys()
    )

    for token in tokens:

        await stop_child_bot(
            token
        )


# ============================================================
# BUILD MAIN APPLICATION
# ============================================================

def build_application():

    if not MAIN_BOT_TOKEN:

        raise RuntimeError(
            "MAIN_BOT_TOKEN is missing."
        )

    application = (
        Application
        .builder()
        .token(
            MAIN_BOT_TOKEN
        )
        .post_init(
            post_init
        )
        .post_shutdown(
            post_shutdown
        )
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    application.add_handler(
        CommandHandler(
            "panel",
            panel
        )
    )

    application.add_handler(
        CommandHandler(
            "id",
            my_id
        )
    )

    application.add_handler(
        CommandHandler(
            "botfather",
            botfather_help
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            main_callback
        )
    )

    application.add_handler(
        MessageHandler(
            filters.TEXT
            & ~filters.COMMAND,
            main_text
        )
    )

    return application


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    init_db()

    log.info(
        "🇮🇷 Iran Golf Telegram ULTRA starting..."
    )

    application = (
        build_application()
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True
    )