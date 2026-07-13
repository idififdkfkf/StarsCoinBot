# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════╗
║                         🌌 L I B E R   B O T                          ║
║          یک اقتصاد آنلاین زنده داخل تلگرام — نسخهٔ هستهٔ اصلی           ║
╠══════════════════════════════════════════════════════════════════════╣
║  Stack:  Python 3.11+  |  aiogram 3.x  |  SQLite (aiosqlite)          ║
║          APScheduler (جهان زنده / نوسان بازار / سود بانک)             ║
║                                                                        ║
║  این فایل «هستهٔ کامل و واقعاً اجراشدنی» LIBER است. طراحی به شکلی      ║
║  ماژولار انجام شده (هر سیستم = یک Router + یک بخش DB) که بتوان        ║
║  بخش‌های بعدی نقشهٔ کامل (اتحاد، PvP، فصل‌ها، صنعت/معدن پیشرفته،       ║
║  اپلیکیشن، ...) را بدون شکستن هستهٔ فعلی روی همین اضافه کرد.           ║
║                                                                        ║
║  پیاده‌سازی‌شده در این نسخه:                                          ║
║   ✅ ثبت‌نام خودکار + عضویت اجباری کانال                              ║
║   ✅ پروفایل، Level/XP، عنوان‌ها                                      ║
║   ✅ کیف پول چندارزی: LIBER / Coin / Energy / Diamond / Medal         ║
║   ✅ بازار زندهٔ LIBER با موتور نوسان قیمت خودکار (هر ساعت)           ║
║   ✅ خرید/فروش LIBER با قانون «حداقل ۱ واحد باقی بماند»               ║
║   ✅ بانک: سپرده + سود روزانهٔ خودکار                                 ║
║   ✅ صندوق‌های شانسی (رایگان/برنزی/نقره‌ای/طلایی) با احتمال وزن‌دار    ║
║   ✅ مأموریت روزانه با ردیابی پیشرفت خودکار                           ║
║   ✅ کشور من: ساخت کشور، جمعیت، اقتصاد، درآمد خودکار قابل برداشت      ║
║   ✅ لیدربرد جهانی (ثروت)                                             ║
║   ✅ مشاور هوش مصنوعی (تحلیل قانون‌محور، آماده اتصال به LLM واقعی)    ║
║   ✅ پنل مدیریت: داشبورد، مدیریت کاربر، پیام همگانی، کنترل بازار،     ║
║      مسدودسازی، لاگ کامل تراکنش‌ها                                    ║
║   ✅ ضدتقلب پایه (rate-limit روی معاملات) + لاگ‌گیری کامل             ║
║   ✅ زمان‌بند خودکار: نوسان بازار هرساعت، سود بانک هرروز، ریست         ║
║      صندوق/ماموریت روزانه، درآمد کشور، رویداد تصادفی جهانی            ║
║                                                                        ║
║  راهنمای اجرا در پایین فایل (بخش __main__) و در README.md آمده.       ║
╚══════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import aiosqlite
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.exceptions import TelegramBadRequest

# ════════════════════════════════════════════════════════════════════
#  ⚙  CONFIG  —  همه چیزهایی که باید قبل از اجرا تنظیم کنی
# ════════════════════════════════════════════════════════════════════

BOT_TOKEN = "8818731091:AAHD4vNWYdFfDD6C0__60vsd4hCDumRuB-Y" 

# آیدی عددی ادمین‌ها (لیست). با /id در ربات می‌توانی آیدی خودت را بگیری.
# آیدی خودت از قبل اینجا ثبت شده؛ از طریق LIBER_ADMIN_IDS هم می‌توانی ادمین‌های بیشتر اضافه کنی.
_DEFAULT_ADMIN_IDS = "6188951798"
ADMIN_IDS: set[int] = {
    int(x) for x in (os.getenv("LIBER_ADMIN_IDS", "") + "," + _DEFAULT_ADMIN_IDS).split(",")
    if x.strip().isdigit()
}

# کانال‌های عضویت اجباری. ربات باید در این کانال «ادمین» باشد تا بتواند عضویت را چک کند.
# اگر عضویت اجباری نمی‌خواهی، این لیست را خالی بگذار: FORCE_CHANNELS = []
FORCE_CHANNELS: list[dict] = [
    {"title": "📢 کانال LIBER", "username": "Libercoin1"},
]

DB_PATH = os.getenv("LIBER_DB_PATH", "liber.db")

# پارامترهای اقتصاد — همه‌شان قابل تغییر از پنل ادمین هم هستند (جدول economy_config)
DEFAULT_LIBER_PRICE = 100.0          # قیمت اولیهٔ هر LIBER بر حسب Coin
MIN_PRICE_MULT = 0.4                 # کف نوسان نسبت به baseline
MAX_PRICE_MULT = 3.0                 # سقف نوسان نسبت به baseline
HOURLY_VOLATILITY = 0.20             # حداکثر نوسان تصادفی هرساعت (٪)
BANK_DAILY_RATE = 0.01               # سود روزانهٔ بانک (۱٪)
ENERGY_MAX = 100
ENERGY_REGEN_PER_HOUR = 10
STARTING_COIN = 1000
STARTING_ENERGY = 100
STARTING_XP_PER_LEVEL = 100          # XP لازم برای هر Level = 100 * level

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("liber")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

router = Router()
admin_router = Router()
dp.include_router(router)
dp.include_router(admin_router)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def ts() -> str:
    return now_utc().isoformat()


# ════════════════════════════════════════════════════════════════════
#  🗄  DATABASE  —  لایهٔ دیتابیس (SQLite async)
# ════════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id         INTEGER PRIMARY KEY,
    username        TEXT,
    first_name      TEXT,
    joined_at       TEXT,
    level           INTEGER DEFAULT 1,
    xp              INTEGER DEFAULT 0,
    title           TEXT DEFAULT 'تازه‌کار',
    coin            REAL DEFAULT 0,
    liber           REAL DEFAULT 0,
    energy          INTEGER DEFAULT 100,
    diamond         INTEGER DEFAULT 0,
    medal           INTEGER DEFAULT 0,
    vip_level       TEXT DEFAULT 'None',
    vip_expiry      TEXT,
    last_energy_at  TEXT,
    last_daily_box  TEXT,
    trades_count    INTEGER DEFAULT 0,
    is_banned       INTEGER DEFAULT 0,
    is_verified     INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS transactions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    kind        TEXT,      -- buy/sell/bank_deposit/bank_interest/box/mission/admin/country ...
    currency    TEXT,      -- coin/liber/diamond/energy/medal
    amount      REAL,
    reason      TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS market (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    price           REAL,
    baseline        REAL,
    buy_pressure    REAL DEFAULT 0,
    sell_pressure   REAL DEFAULT 0,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS market_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    price       REAL,
    recorded_at TEXT
);

CREATE TABLE IF NOT EXISTS bank_deposits (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER,
    amount      REAL,
    rate        REAL,
    created_at  TEXT,
    last_payout TEXT
);

CREATE TABLE IF NOT EXISTS countries (
    user_id         INTEGER PRIMARY KEY,
    name            TEXT,
    flag            TEXT,
    capital         TEXT,
    population      INTEGER DEFAULT 1000,
    treasury        REAL DEFAULT 5000,
    economy_level   INTEGER DEFAULT 1,
    industry_level  INTEGER DEFAULT 1,
    tech_level      INTEGER DEFAULT 1,
    defense_level   INTEGER DEFAULT 1,
    satisfaction    INTEGER DEFAULT 80,
    created_at      TEXT,
    last_income_at  TEXT
);

CREATE TABLE IF NOT EXISTS missions (
    user_id       INTEGER,
    mission_date  TEXT,
    goal          TEXT,        -- e.g. "trade" / "buy" / "collect_country"
    goal_label    TEXT,
    target        INTEGER,
    progress      INTEGER DEFAULT 0,
    reward_coin   REAL,
    reward_xp     INTEGER,
    claimed       INTEGER DEFAULT 0,
    PRIMARY KEY (user_id, mission_date)
);

CREATE TABLE IF NOT EXISTS p2p_orders (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id       INTEGER,
    amount          REAL,
    price_per_unit  REAL,
    created_at      TEXT,
    status          TEXT DEFAULT 'open'   -- open / filled / cancelled
);

CREATE TABLE IF NOT EXISTS economy_config (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS broadcasts_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id    INTEGER,
    text        TEXT,
    sent_at     TEXT,
    total_sent  INTEGER
);
"""

_db: Optional[aiosqlite.Connection] = None


async def db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.executescript(SCHEMA)
        await _db.commit()
        await _init_market()
    return _db


async def _init_market():
    conn = _db
    cur = await conn.execute("SELECT * FROM market WHERE id = 1")
    row = await cur.fetchone()
    if row is None:
        await conn.execute(
            "INSERT INTO market (id, price, baseline, updated_at) VALUES (1, ?, ?, ?)",
            (DEFAULT_LIBER_PRICE, DEFAULT_LIBER_PRICE, ts()),
        )
        await conn.commit()


async def log_tx(user_id: int, kind: str, currency: str, amount: float, reason: str):
    conn = await db()
    await conn.execute(
        "INSERT INTO transactions (user_id, kind, currency, amount, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, kind, currency, amount, reason, ts()),
    )
    await conn.commit()


# ════════════════════════════════════════════════════════════════════
#  👤  USER HELPERS
# ════════════════════════════════════════════════════════════════════

async def get_user(user_id: int) -> Optional[aiosqlite.Row]:
    conn = await db()
    cur = await conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    return await cur.fetchone()


async def ensure_user(user_id: int, username: str, first_name: str) -> tuple[aiosqlite.Row, bool]:
    """برمی‌گرداند (user_row, is_new)."""
    row = await get_user(user_id)
    if row:
        return row, False
    conn = await db()
    await conn.execute(
        "INSERT INTO users (user_id, username, first_name, joined_at, coin, energy, "
        "last_energy_at, last_daily_box) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, username or "", first_name or "", ts(), STARTING_COIN, STARTING_ENERGY, ts(), ""),
    )
    await conn.commit()
    await log_tx(user_id, "signup_bonus", "coin", STARTING_COIN, "جایزه ورود")
    row = await get_user(user_id)
    return row, True


async def update_balance(user_id: int, **deltas: float):
    """deltas مثل coin=+100, liber=-5 ... مقداری که اضافه/کم می‌شود."""
    conn = await db()
    row = await get_user(user_id)
    if row is None:
        return
    sets = []
    params = []
    for field, delta in deltas.items():
        new_val = (row[field] or 0) + delta
        if field in ("energy", "diamond", "medal", "level", "xp"):
            new_val = max(0, int(new_val))
        else:
            new_val = max(0.0, round(new_val, 4))
        sets.append(f"{field} = ?")
        params.append(new_val)
    params.append(user_id)
    await conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = ?", params)
    await conn.commit()


VIP_TIERS = {
    "Silver":  {"label": "⭐ VIP Silver",  "cost_diamond": 50,  "days": 30, "xp_mult": 1.10, "energy_mult": 1.25},
    "Gold":    {"label": "🥇 VIP Gold",    "cost_diamond": 150, "days": 30, "xp_mult": 1.25, "energy_mult": 1.50},
    "Diamond": {"label": "💎 VIP Diamond", "cost_diamond": 400, "days": 30, "xp_mult": 1.50, "energy_mult": 2.00},
    "Titan":   {"label": "👑 VIP Titan",   "cost_diamond": 1000, "days": 30, "xp_mult": 2.00, "energy_mult": 3.00},
}


def get_vip_multipliers(row: aiosqlite.Row) -> tuple[float, float]:
    """برمی‌گرداند (xp_mult, energy_mult) در صورتی که VIP هنوز منقضی نشده باشد."""
    if row["vip_level"] in (None, "None", "") or not row["vip_expiry"]:
        return 1.0, 1.0
    try:
        if datetime.fromisoformat(row["vip_expiry"]) < now_utc():
            return 1.0, 1.0
    except ValueError:
        return 1.0, 1.0
    tier = VIP_TIERS.get(row["vip_level"])
    if not tier:
        return 1.0, 1.0
    return tier["xp_mult"], tier["energy_mult"]


async def add_xp(user_id: int, amount: int):
    row = await get_user(user_id)
    if not row:
        return
    xp_mult, _ = get_vip_multipliers(row)
    amount = int(round(amount * xp_mult))
    xp = row["xp"] + amount
    level = row["level"]
    leveled_up = False
    needed = level * STARTING_XP_PER_LEVEL
    while xp >= needed:
        xp -= needed
        level += 1
        leveled_up = True
        needed = level * STARTING_XP_PER_LEVEL
    conn = await db()
    await conn.execute(
        "UPDATE users SET xp = ?, level = ? WHERE user_id = ?", (xp, level, user_id)
    )
    await conn.commit()
    if leveled_up:
        title = title_for_level(level)
        await conn.execute("UPDATE users SET title = ? WHERE user_id = ?", (title, user_id))
        await conn.commit()
    return leveled_up, level


def title_for_level(level: int) -> str:
    if level >= 50:
        return "👑 افسانه‌ای"
    if level >= 30:
        return "💎 فرمانروای اقتصاد"
    if level >= 15:
        return "🏆 سرمایه‌دار بزرگ"
    if level >= 5:
        return "💼 تاجر"
    return "🌱 تازه‌کار"


# ════════════════════════════════════════════════════════════════════
#  📈  MARKET ENGINE  —  موتور نوسان قیمت LIBER
# ════════════════════════════════════════════════════════════════════

async def get_market() -> aiosqlite.Row:
    conn = await db()
    cur = await conn.execute("SELECT * FROM market WHERE id = 1")
    return await cur.fetchone()


async def record_pressure(is_buy: bool, amount: float):
    conn = await db()
    field = "buy_pressure" if is_buy else "sell_pressure"
    await conn.execute(f"UPDATE market SET {field} = {field} + ? WHERE id = 1", (amount,))
    await conn.commit()


async def market_tick():
    """اجرای خودکار هرساعت: قیمت را بر اساس فشار خرید/فروش + نوسان تصادفی تغییر می‌دهد."""
    conn = await db()
    m = await get_market()
    price = m["price"]
    baseline = m["baseline"]
    buy_p = m["buy_pressure"] or 0
    sell_p = m["sell_pressure"] or 0

    net = buy_p - sell_p
    demand_effect = max(-0.25, min(0.25, net / 5000.0))  # حداکثر ۲۵٪ اثر تقاضا
    random_drift = random.uniform(-HOURLY_VOLATILITY, HOURLY_VOLATILITY)
    change = demand_effect + random_drift

    new_price = price * (1 + change)
    new_price = max(baseline * MIN_PRICE_MULT, min(baseline * MAX_PRICE_MULT, new_price))
    new_price = round(new_price, 2)

    await conn.execute(
        "UPDATE market SET price = ?, buy_pressure = 0, sell_pressure = 0, updated_at = ? WHERE id = 1",
        (new_price, ts()),
    )
    await conn.execute(
        "INSERT INTO market_history (price, recorded_at) VALUES (?, ?)", (new_price, ts())
    )
    await conn.commit()
    log.info(f"📈 Market tick: {price:.2f} -> {new_price:.2f} (Δ{change*100:+.1f}%)")


# ════════════════════════════════════════════════════════════════════
#  🎹  KEYBOARDS  —  دکمه‌های شیشه‌ای، ۳ تا در هر ردیف
# ════════════════════════════════════════════════════════════════════

def kb(rows: list[list[tuple[str, str]]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=cb) for t, cb in row] for row in rows
        ]
    )


def chunk3(buttons: list[tuple[str, str]]) -> list[list[tuple[str, str]]]:
    return [buttons[i : i + 3] for i in range(0, len(buttons), 3)]


def main_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        ("👤 پروفایل", "profile"),
        ("💰 کیف پول", "wallet"),
        ("📈 بازار", "market"),
        ("🏪 بازار کاربران", "p2p"),
        ("🌍 کشور من", "country"),
        ("🏦 بانک", "bank"),
        ("🎯 ماموریت", "missions"),
        ("🎁 صندوق‌ها", "boxes"),
        ("🛒 فروشگاه", "shop"),
        ("⭐ VIP", "vip"),
        ("🏆 رتبه‌بندی", "leaderboard"),
        ("🧠 مشاور AI", "advisor"),
    ]
    return kb(chunk3(buttons))


def back_kb(target: str = "menu") -> InlineKeyboardMarkup:
    return kb([[("🔙 برگشت", target)]])


def force_join_kb() -> InlineKeyboardMarkup:
    rows = [[(ch["title"], f"noop")] for ch in FORCE_CHANNELS]
    # دکمه‌های عضویت باید لینک باشند نه callback؛ برای سادگی از url استفاده می‌کنیم
    kb_rows = []
    for ch in FORCE_CHANNELS:
        kb_rows.append(
            [InlineKeyboardButton(text=ch["title"], url=f"https://t.me/{ch['username']}")]
        )
    kb_rows.append([InlineKeyboardButton(text="✅ بررسی عضویت", callback_data="check_join")])
    return InlineKeyboardMarkup(inline_keyboard=kb_rows)


# ════════════════════════════════════════════════════════════════════
#  🔒  FORCED JOIN MIDDLEWARE-STYLE CHECK
# ════════════════════════════════════════════════════════════════════

async def is_member_of_all(user_id: int) -> bool:
    if not FORCE_CHANNELS:
        return True
    for ch in FORCE_CHANNELS:
        try:
            member = await bot.get_chat_member(f"@{ch['username']}", user_id)
            if member.status in ("left", "kicked"):
                return False
        except TelegramBadRequest:
            # اگر ربات ادمین کانال نیست یا خطای دیگر، برای امنیت عبور نده
            return False
    return True


# ════════════════════════════════════════════════════════════════════
#  🚀  START / REGISTRATION
# ════════════════════════════════════════════════════════════════════

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    if not await is_member_of_all(user_id):
        await message.answer(
            "🔒 <b>برای ورود به LIBER عضو کانال‌های زیر شوید:</b>",
            reply_markup=force_join_kb(),
        )
        return

    row, is_new = await ensure_user(user_id, message.from_user.username, message.from_user.first_name)
    name = message.from_user.first_name or "کاربر"

    if is_new:
        text = (
            f"سلام 👋 جناب <b>{name}</b>\n\n"
            f"به دنیای <b>LIBER</b> خوش آمدید 🌍\n"
            f"حساب شما با موفقیت ساخته شد.\n\n"
            f"🎁 <b>جایزه ورود:</b>\n"
            f"💰 {STARTING_COIN} Coin\n"
            f"⚡ {STARTING_ENERGY} Energy\n"
        )
    else:
        await regen_energy(user_id)
        text = f"سلام 👑 <b>{name}</b>\nبه دنیای LIBER خوش برگشتی 🌌"

    await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "check_join")
async def cb_check_join(call: CallbackQuery):
    if await is_member_of_all(call.from_user.id):
        await ensure_user(call.from_user.id, call.from_user.username, call.from_user.first_name)
        await call.message.edit_text(
            "✅ عضویت تایید شد! به LIBER خوش آمدید 🌍", reply_markup=main_menu_kb()
        )
    else:
        await call.answer("❌ هنوز عضو همهٔ کانال‌ها نشده‌اید.", show_alert=True)


@router.callback_query(F.data == "menu")
async def cb_menu(call: CallbackQuery):
    await call.message.edit_text("🏠 <b>منوی اصلی LIBER</b>", reply_markup=main_menu_kb())


@router.callback_query(F.data == "noop")
async def cb_noop(call: CallbackQuery):
    await call.answer()


async def regen_energy(user_id: int):
    row = await get_user(user_id)
    if not row:
        return
    last = row["last_energy_at"]
    if not last:
        return
    last_dt = datetime.fromisoformat(last)
    hours = (now_utc() - last_dt).total_seconds() / 3600
    _, energy_mult = get_vip_multipliers(row)
    regen = int(hours * ENERGY_REGEN_PER_HOUR * energy_mult)
    if regen > 0:
        new_energy = min(ENERGY_MAX, row["energy"] + regen)
        conn = await db()
        await conn.execute(
            "UPDATE users SET energy = ?, last_energy_at = ? WHERE user_id = ?",
            (new_energy, ts(), user_id),
        )
        await conn.commit()


# ════════════════════════════════════════════════════════════════════
#  👤  PROFILE
# ════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "profile")
async def cb_profile(call: CallbackQuery):
    row = await get_user(call.from_user.id)
    if not row:
        return await call.answer("ابتدا /start را بزنید", show_alert=True)
    needed_xp = row["level"] * STARTING_XP_PER_LEVEL
    text = (
        f"👤 <b>پروفایل شما</b>\n\n"
        f"🆔 آیدی: <code>{row['user_id']}</code>\n"
        f"🎖 عنوان: {row['title']}\n"
        f"⭐ Level: {row['level']}\n"
        f"✨ XP: {row['xp']}/{needed_xp}\n"
        f"⭐ VIP: {row['vip_level']}\n"
        f"📊 معاملات انجام‌شده: {row['trades_count']}\n\n"
        f"🪙 LIBER: {row['liber']:.2f}\n"
        f"💰 Coin: {row['coin']:.0f}\n"
        f"⚡ Energy: {row['energy']}/{ENERGY_MAX}\n"
        f"💎 Diamond: {row['diamond']}\n"
        f"🏅 Medal: {row['medal']}\n"
    )
    await call.message.edit_text(text, reply_markup=back_kb())


# ════════════════════════════════════════════════════════════════════
#  💼  WALLET
# ════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "wallet")
async def cb_wallet(call: CallbackQuery):
    row = await get_user(call.from_user.id)
    text = (
        f"💼 <b>کیف پول شما</b>\n\n"
        f"🪙 LIBER: {row['liber']:.2f}\n"
        f"💰 Coin: {row['coin']:.0f}\n"
        f"⚡ Energy: {row['energy']}/{ENERGY_MAX}\n"
        f"💎 Diamond: {row['diamond']}\n"
        f"🏅 Medal: {row['medal']}\n"
    )
    buttons = [("📈 بازار", "market"), ("📜 تاریخچه", "wallet_history"), ("🔙 برگشت", "menu")]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data == "wallet_history")
async def cb_wallet_history(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 10",
        (call.from_user.id,),
    )
    rows = await cur.fetchall()
    if not rows:
        text = "📜 هنوز تراکنشی ثبت نشده."
    else:
        lines = ["📜 <b>۱۰ تراکنش اخیر</b>\n"]
        for r in rows:
            sign = "+" if r["amount"] >= 0 else ""
            lines.append(f"{sign}{r['amount']:.2f} {r['currency']} — {r['reason']}")
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=back_kb("wallet"))


# ════════════════════════════════════════════════════════════════════
#  📈  MARKET  —  خرید/فروش LIBER
# ════════════════════════════════════════════════════════════════════

class TradeStates(StatesGroup):
    waiting_buy_amount = State()
    waiting_sell_amount = State()
    waiting_deposit_amount = State()


@router.callback_query(F.data == "market")
async def cb_market(call: CallbackQuery):
    m = await get_market()
    conn = await db()
    cur = await conn.execute(
        "SELECT price FROM market_history ORDER BY id DESC LIMIT 24"
    )
    hist = [r["price"] for r in await cur.fetchall()]
    change_24h = 0.0
    if len(hist) >= 2:
        change_24h = (hist[0] - hist[-1]) / hist[-1] * 100

    text = (
        f"📈 <b>بازار LIBER</b>\n\n"
        f"1 LIBER = <b>{m['price']:.2f} Coin</b>\n"
        f"تغییر اخیر: {change_24h:+.1f}%\n"
        f"نوسان: هر ساعت خودکار (تقاضا/عرضه + رویداد جهانی)\n"
    )
    buttons = [
        ("🟢 خرید", "buy_start"),
        ("🔴 فروش", "sell_start"),
        ("📊 نمودار", "market_chart"),
        ("🔙 برگشت", "menu"),
    ]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data == "market_chart")
async def cb_market_chart(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute("SELECT price, recorded_at FROM market_history ORDER BY id DESC LIMIT 12")
    rows = list(reversed(await cur.fetchall()))
    if not rows:
        text = "📊 هنوز داده‌ای برای نمودار ثبت نشده."
    else:
        lines = ["📊 <b>روند اخیر قیمت LIBER</b>\n"]
        for r in rows:
            hhmm = datetime.fromisoformat(r["recorded_at"]).strftime("%H:%M")
            lines.append(f"{hhmm} → {r['price']:.2f} Coin")
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=back_kb("market"))


@router.callback_query(F.data == "buy_start")
async def cb_buy_start(call: CallbackQuery, state: FSMContext):
    m = await get_market()
    row = await get_user(call.from_user.id)
    await call.message.edit_text(
        f"🟢 <b>خرید LIBER</b>\n\n"
        f"قیمت فعلی: {m['price']:.2f} Coin\n"
        f"موجودی شما: {row['coin']:.0f} Coin\n\n"
        f"چند LIBER می‌خواهید بخرید؟ (عدد را بفرستید)",
        reply_markup=back_kb("market"),
    )
    await state.set_state(TradeStates.waiting_buy_amount)


@router.message(TradeStates.waiting_buy_amount)
async def msg_buy_amount(message: Message, state: FSMContext):
    await state.clear()
    try:
        qty = float(message.text.strip())
        assert qty > 0
    except (ValueError, AssertionError):
        return await message.answer("❌ لطفاً یک عدد معتبر بزرگ‌تر از صفر بفرستید.")

    if not await anti_cheat_ok(message.from_user.id, "trade"):
        return await message.answer("🛡 معاملات شما بیش از حد سریع است. کمی صبر کنید.")

    m = await get_market()
    row = await get_user(message.from_user.id)
    cost = round(qty * m["price"], 2)
    if row["coin"] < cost:
        return await message.answer(
            f"❌ موجودی کافی نیست.\nهزینهٔ خرید {qty:g} LIBER: {cost:.2f} Coin\nموجودی شما: {row['coin']:.0f} Coin",
            reply_markup=back_kb("market"),
        )

    await update_balance(message.from_user.id, coin=-cost, liber=qty)
    await log_tx(message.from_user.id, "buy", "liber", qty, f"خرید LIBER به قیمت {m['price']:.2f}")
    await log_tx(message.from_user.id, "buy", "coin", -cost, "پرداخت خرید LIBER")
    await record_pressure(is_buy=True, amount=cost)
    await bump_trade_counters(message.from_user.id)

    await message.answer(
        f"✅ <b>خرید موفق</b>\n\n{qty:g} LIBER دریافت کردید.\nهزینه: {cost:.2f} Coin",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "sell_start")
async def cb_sell_start(call: CallbackQuery, state: FSMContext):
    m = await get_market()
    row = await get_user(call.from_user.id)
    await call.message.edit_text(
        f"🔴 <b>فروش LIBER</b>\n\n"
        f"قیمت فعلی: {m['price']:.2f} Coin\n"
        f"موجودی LIBER شما: {row['liber']:.2f}\n"
        f"⚠️ حداقل ۱ LIBER باید در کیف پول باقی بماند.\n\n"
        f"چند LIBER می‌خواهید بفروشید؟",
        reply_markup=back_kb("market"),
    )
    await state.set_state(TradeStates.waiting_sell_amount)


@router.message(TradeStates.waiting_sell_amount)
async def msg_sell_amount(message: Message, state: FSMContext):
    await state.clear()
    try:
        qty = float(message.text.strip())
        assert qty > 0
    except (ValueError, AssertionError):
        return await message.answer("❌ لطفاً یک عدد معتبر بزرگ‌تر از صفر بفرستید.")

    if not await anti_cheat_ok(message.from_user.id, "trade"):
        return await message.answer("🛡 معاملات شما بیش از حد سریع است. کمی صبر کنید.")

    row = await get_user(message.from_user.id)
    max_sell = row["liber"] - 1
    if row["liber"] <= 0:
        return await message.answer("❌ شما LIBER ندارید.")
    if qty > max_sell:
        return await message.answer(
            f"⚠️ باید حداقل ۱ LIBER در کیف پول باقی بماند.\nحداکثر قابل فروش: {max_sell:.2f}",
        )

    m = await get_market()
    revenue = round(qty * m["price"], 2)
    await update_balance(message.from_user.id, liber=-qty, coin=revenue)
    await log_tx(message.from_user.id, "sell", "liber", -qty, f"فروش LIBER به قیمت {m['price']:.2f}")
    await log_tx(message.from_user.id, "sell", "coin", revenue, "دریافت وجه فروش LIBER")
    await record_pressure(is_buy=False, amount=revenue)
    await bump_trade_counters(message.from_user.id)

    await message.answer(
        f"✅ <b>فروش موفق</b>\n\n{qty:g} LIBER فروخته شد.\nدریافتی: {revenue:.2f} Coin",
        reply_markup=main_menu_kb(),
    )


async def bump_trade_counters(user_id: int):
    conn = await db()
    await conn.execute(
        "UPDATE users SET trades_count = trades_count + 1 WHERE user_id = ?", (user_id,)
    )
    await conn.commit()
    await add_xp(user_id, 5)
    await update_mission_progress(user_id, "trade", 1)


# ────── ضدتقلب سادهٔ Rate-limit ──────
_last_action: dict[tuple[int, str], float] = {}
RATE_LIMIT_SECONDS = 2.0


async def anti_cheat_ok(user_id: int, action: str) -> bool:
    key = (user_id, action)
    last = _last_action.get(key, 0)
    now = time.time()
    if now - last < RATE_LIMIT_SECONDS:
        return False
    _last_action[key] = now
    return True


# ════════════════════════════════════════════════════════════════════
#  🏦  BANK
# ════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "bank")
async def cb_bank(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute(
        "SELECT COALESCE(SUM(amount),0) as total FROM bank_deposits WHERE user_id = ?",
        (call.from_user.id,),
    )
    total = (await cur.fetchone())["total"]
    row = await get_user(call.from_user.id)
    text = (
        f"🏦 <b>بانک LIBER</b>\n\n"
        f"💰 موجودی نقدی: {row['coin']:.0f} Coin\n"
        f"🏛 سپردهٔ فعلی: {total:.0f} Coin\n"
        f"📈 سود روزانه: {BANK_DAILY_RATE*100:.1f}%\n"
    )
    buttons = [("➕ سپرده‌گذاری", "deposit_start"), ("➖ برداشت سپرده", "withdraw_deposit"), ("🔙 برگشت", "menu")]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data == "deposit_start")
async def cb_deposit_start(call: CallbackQuery, state: FSMContext):
    row = await get_user(call.from_user.id)
    await call.message.edit_text(
        f"➕ <b>سپرده‌گذاری</b>\nموجودی شما: {row['coin']:.0f} Coin\nچقدر می‌خواهید سپرده بگذارید؟",
        reply_markup=back_kb("bank"),
    )
    await state.set_state(TradeStates.waiting_deposit_amount)


@router.message(TradeStates.waiting_deposit_amount)
async def msg_deposit_amount(message: Message, state: FSMContext):
    await state.clear()
    try:
        amount = float(message.text.strip())
        assert amount > 0
    except (ValueError, AssertionError):
        return await message.answer("❌ عدد معتبر بفرستید.")

    row = await get_user(message.from_user.id)
    if row["coin"] < amount:
        return await message.answer("❌ موجودی کافی نیست.")

    await update_balance(message.from_user.id, coin=-amount)
    conn = await db()
    await conn.execute(
        "INSERT INTO bank_deposits (user_id, amount, rate, created_at, last_payout) VALUES (?, ?, ?, ?, ?)",
        (message.from_user.id, amount, BANK_DAILY_RATE, ts(), ts()),
    )
    await conn.commit()
    await log_tx(message.from_user.id, "bank_deposit", "coin", -amount, "سپرده‌گذاری در بانک")
    await message.answer(f"✅ {amount:.0f} Coin سپرده‌گذاری شد. سود روزانه: {BANK_DAILY_RATE*100:.1f}%", reply_markup=main_menu_kb())


@router.callback_query(F.data == "withdraw_deposit")
async def cb_withdraw_deposit(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute("SELECT * FROM bank_deposits WHERE user_id = ?", (call.from_user.id,))
    deposits = await cur.fetchall()
    if not deposits:
        return await call.answer("سپرده‌ای ندارید.", show_alert=True)
    total = sum(d["amount"] for d in deposits)
    await conn.execute("DELETE FROM bank_deposits WHERE user_id = ?", (call.from_user.id,))
    await conn.commit()
    await update_balance(call.from_user.id, coin=total)
    await log_tx(call.from_user.id, "bank_withdraw", "coin", total, "برداشت کامل سپرده")
    await call.message.edit_text(f"✅ {total:.0f} Coin به کیف پول شما بازگشت.", reply_markup=main_menu_kb())


async def bank_daily_interest_job():
    conn = await db()
    cur = await conn.execute("SELECT * FROM bank_deposits")
    deposits = await cur.fetchall()
    for d in deposits:
        interest = round(d["amount"] * d["rate"], 2)
        await conn.execute(
            "UPDATE bank_deposits SET amount = amount + ?, last_payout = ? WHERE id = ?",
            (interest, ts(), d["id"]),
        )
        await log_tx(d["user_id"], "bank_interest", "coin", interest, "سود روزانه بانک")
    await conn.commit()
    log.info(f"🏦 Bank interest paid for {len(deposits)} deposits")


# ════════════════════════════════════════════════════════════════════
#  🎁  LOOT BOXES
# ════════════════════════════════════════════════════════════════════

BOX_TIERS = {
    "free": {"label": "📦 صندوق رایگان", "cost": 0, "currency": "coin",
              "rewards": [("coin", 100, 500, 0.70), ("xp", 5, 20, 0.20), ("energy", 5, 15, 0.09), ("diamond", 1, 1, 0.01)]},
    "bronze": {"label": "🥉 صندوق برنزی", "cost": 350, "currency": "coin",
               "rewards": [("coin", 200, 800, 0.55), ("liber", 1, 3, 0.30), ("xp", 20, 50, 0.15)]},
    "silver": {"label": "🥈 صندوق نقره‌ای", "cost": 2000, "currency": "coin",
               "rewards": [("liber", 3, 8, 0.45), ("diamond", 2, 5, 0.30), ("coin", 500, 2000, 0.25)]},
    "gold": {"label": "🥇 صندوق طلایی", "cost": 10000, "currency": "coin",
             "rewards": [("liber", 10, 30, 0.50), ("diamond", 5, 15, 0.35), ("medal", 1, 3, 0.15)]},
}


@router.callback_query(F.data == "boxes")
async def cb_boxes(call: CallbackQuery):
    text = "🎁 <b>صندوق‌های شانسی</b>\n\nصندوق رایگان هر ۲۴ ساعت یک بار قابل دریافت است."
    buttons = [(v["label"], f"box_{k}") for k, v in BOX_TIERS.items()]
    buttons.append(("🔙 برگشت", "menu"))
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data.startswith("box_"))
async def cb_open_box(call: CallbackQuery):
    tier = call.data.split("_", 1)[1]
    conf = BOX_TIERS[tier]
    row = await get_user(call.from_user.id)

    if tier == "free":
        last = row["last_daily_box"]
        if last:
            elapsed = now_utc() - datetime.fromisoformat(last)
            if elapsed < timedelta(hours=24):
                remain = timedelta(hours=24) - elapsed
                h, m = divmod(int(remain.total_seconds() // 60), 60)
                return await call.answer(f"⏳ {h} ساعت و {m} دقیقه دیگر صبر کنید.", show_alert=True)
        conn = await db()
        await conn.execute("UPDATE users SET last_daily_box = ? WHERE user_id = ?", (ts(), call.from_user.id))
        await conn.commit()
    else:
        if row["coin"] < conf["cost"]:
            return await call.answer("❌ موجودی کافی نیست.", show_alert=True)
        await update_balance(call.from_user.id, coin=-conf["cost"])
        await log_tx(call.from_user.id, "box_open", "coin", -conf["cost"], f"خرید {conf['label']}")

    currency, lo, hi, _ = _weighted_choice(conf["rewards"])
    amount = random.randint(lo, hi) if currency != "coin" else random.randint(lo, hi)

    if currency == "xp":
        await add_xp(call.from_user.id, amount)
    else:
        await update_balance(call.from_user.id, **{currency: amount})
        await log_tx(call.from_user.id, "box_reward", currency, amount, f"جایزهٔ {conf['label']}")

    label_map = {"coin": "Coin", "liber": "LIBER", "diamond": "Diamond", "energy": "Energy", "xp": "XP", "medal": "Medal"}
    await call.message.edit_text(
        f"🎉 <b>{conf['label']} باز شد!</b>\n\nجایزهٔ شما: +{amount} {label_map[currency]}",
        reply_markup=back_kb("boxes"),
    )


def _weighted_choice(rewards: list[tuple]):
    r = random.random()
    acc = 0.0
    for reward in rewards:
        acc += reward[3]
        if r <= acc:
            return reward
    return rewards[-1]


# ════════════════════════════════════════════════════════════════════
#  🎯  MISSIONS  —  مأموریت روزانه
# ════════════════════════════════════════════════════════════════════

DAILY_MISSION_POOL = [
    {"goal": "trade", "goal_label": "انجام ۳ معامله (خرید یا فروش)", "target": 3, "reward_coin": 500, "reward_xp": 50},
    {"goal": "box", "goal_label": "باز کردن یک صندوق", "target": 1, "reward_coin": 200, "reward_xp": 20},
    {"goal": "collect_country", "goal_label": "برداشت درآمد کشور", "target": 1, "reward_coin": 300, "reward_xp": 30},
]


async def get_or_create_daily_mission(user_id: int) -> aiosqlite.Row:
    today = now_utc().strftime("%Y-%m-%d")
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM missions WHERE user_id = ? AND mission_date = ?", (user_id, today)
    )
    row = await cur.fetchone()
    if row:
        return row
    m = random.choice(DAILY_MISSION_POOL)
    await conn.execute(
        "INSERT INTO missions (user_id, mission_date, goal, goal_label, target, reward_coin, reward_xp) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (user_id, today, m["goal"], m["goal_label"], m["target"], m["reward_coin"], m["reward_xp"]),
    )
    await conn.commit()
    cur = await conn.execute(
        "SELECT * FROM missions WHERE user_id = ? AND mission_date = ?", (user_id, today)
    )
    return await cur.fetchone()


async def update_mission_progress(user_id: int, goal: str, amount: int):
    today = now_utc().strftime("%Y-%m-%d")
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM missions WHERE user_id = ? AND mission_date = ? AND goal = ?",
        (user_id, today, goal),
    )
    row = await cur.fetchone()
    if not row or row["claimed"]:
        return
    new_progress = min(row["target"], row["progress"] + amount)
    await conn.execute(
        "UPDATE missions SET progress = ? WHERE user_id = ? AND mission_date = ?",
        (new_progress, user_id, today),
    )
    await conn.commit()


@router.callback_query(F.data == "missions")
async def cb_missions(call: CallbackQuery):
    m = await get_or_create_daily_mission(call.from_user.id)
    status = "✅ تکمیل شده" if m["progress"] >= m["target"] else f"{m['progress']}/{m['target']}"
    text = (
        f"🎯 <b>مأموریت امروز</b>\n\n"
        f"{m['goal_label']}\n"
        f"پیشرفت: {status}\n\n"
        f"🎁 جایزه: {m['reward_coin']:.0f} Coin + {m['reward_xp']} XP\n"
    )
    buttons = []
    if m["progress"] >= m["target"] and not m["claimed"]:
        buttons.append(("🎁 دریافت جایزه", "claim_mission"))
    buttons.append(("🔙 برگشت", "menu"))
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data == "claim_mission")
async def cb_claim_mission(call: CallbackQuery):
    today = now_utc().strftime("%Y-%m-%d")
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM missions WHERE user_id = ? AND mission_date = ?", (call.from_user.id, today)
    )
    m = await cur.fetchone()
    if not m or m["progress"] < m["target"] or m["claimed"]:
        return await call.answer("قابل دریافت نیست.", show_alert=True)
    await conn.execute(
        "UPDATE missions SET claimed = 1 WHERE user_id = ? AND mission_date = ?",
        (call.from_user.id, today),
    )
    await conn.commit()
    await update_balance(call.from_user.id, coin=m["reward_coin"])
    await add_xp(call.from_user.id, m["reward_xp"])
    await log_tx(call.from_user.id, "mission_reward", "coin", m["reward_coin"], "جایزه ماموریت روزانه")
    await call.message.edit_text("🎉 جایزه دریافت شد!", reply_markup=back_kb("missions"))


# ════════════════════════════════════════════════════════════════════
#  🌍  COUNTRY
# ════════════════════════════════════════════════════════════════════

COUNTRY_COST = 1000
COUNTRY_INCOME_INTERVAL_HOURS = 4


class CountryStates(StatesGroup):
    waiting_name = State()


@router.callback_query(F.data == "country")
async def cb_country(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute("SELECT * FROM countries WHERE user_id = ?", (call.from_user.id,))
    c = await cur.fetchone()
    if not c:
        text = (
            f"🏳 <b>کشور: هنوز ساخته نشده</b>\n\n"
            f"برای ساخت کشور آماده‌اید؟\nهزینه: {COUNTRY_COST} Coin"
        )
        return await call.message.edit_text(text, reply_markup=kb([[("🏗 ساخت کشور", "country_build")], [("🔙 برگشت", "menu")]]))

    income = calc_country_income(c)
    text = (
        f"🌍 <b>کشور: {c['name']}</b> {c['flag']}\n\n"
        f"👥 جمعیت: {c['population']}\n"
        f"💰 خزانه: {c['treasury']:.0f} Coin\n"
        f"📈 اقتصاد: Level {c['economy_level']}\n"
        f"🏭 صنعت: Level {c['industry_level']}\n"
        f"🔬 فناوری: Level {c['tech_level']}\n"
        f"🛡 دفاع: Level {c['defense_level']}\n"
        f"😊 رضایت: {c['satisfaction']}%\n\n"
        f"💵 درآمد قابل برداشت: {income:.0f} Coin\n"
    )
    buttons = [
        ("💵 برداشت درآمد", "country_collect"),
        ("⬆ ارتقای اقتصاد", "country_upgrade"),
        ("🔙 برگشت", "menu"),
    ]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


def calc_country_income(c: aiosqlite.Row) -> float:
    last = c["last_income_at"]
    if not last:
        return 0
    hours = (now_utc() - datetime.fromisoformat(last)).total_seconds() / 3600
    hours = min(hours, 48)  # سقف ذخیره برای جلوگیری از تجمع بی‌نهایت
    rate_per_hour = c["economy_level"] * 50 + c["industry_level"] * 30
    return hours * rate_per_hour


@router.callback_query(F.data == "country_build")
async def cb_country_build(call: CallbackQuery, state: FSMContext):
    row = await get_user(call.from_user.id)
    if row["coin"] < COUNTRY_COST:
        return await call.answer("❌ موجودی کافی نیست.", show_alert=True)
    await call.message.edit_text("🏳 نام کشور خود را بفرستید (مثلاً LIBERIA):")
    await state.set_state(CountryStates.waiting_name)


@router.message(CountryStates.waiting_name)
async def msg_country_name(message: Message, state: FSMContext):
    await state.clear()
    name = message.text.strip()[:24]
    row = await get_user(message.from_user.id)
    if row["coin"] < COUNTRY_COST:
        return await message.answer("❌ موجودی کافی نیست.")
    await update_balance(message.from_user.id, coin=-COUNTRY_COST)
    conn = await db()
    await conn.execute(
        "INSERT INTO countries (user_id, name, flag, capital, created_at, last_income_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (message.from_user.id, name, "🏳", f"{name} City", ts(), ts()),
    )
    await conn.commit()
    await log_tx(message.from_user.id, "country_build", "coin", -COUNTRY_COST, "ساخت کشور")
    await message.answer(f"🎉 کشور <b>{name}</b> ساخته شد!", reply_markup=main_menu_kb())


@router.callback_query(F.data == "country_collect")
async def cb_country_collect(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute("SELECT * FROM countries WHERE user_id = ?", (call.from_user.id,))
    c = await cur.fetchone()
    if not c:
        return await call.answer("ابتدا کشور بسازید.", show_alert=True)
    income = calc_country_income(c)
    if income <= 0:
        return await call.answer("درآمدی برای برداشت نیست.", show_alert=True)
    await conn.execute(
        "UPDATE countries SET last_income_at = ? WHERE user_id = ?", (ts(), call.from_user.id)
    )
    await conn.commit()
    await update_balance(call.from_user.id, coin=income)
    await log_tx(call.from_user.id, "country_income", "coin", income, "برداشت درآمد کشور")
    await update_mission_progress(call.from_user.id, "collect_country", 1)
    await call.message.edit_text(f"✅ {income:.0f} Coin به کیف پول اضافه شد.", reply_markup=back_kb("country"))


@router.callback_query(F.data == "country_upgrade")
async def cb_country_upgrade(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute("SELECT * FROM countries WHERE user_id = ?", (call.from_user.id,))
    c = await cur.fetchone()
    if not c:
        return await call.answer("ابتدا کشور بسازید.", show_alert=True)
    cost = c["economy_level"] * 2000
    row = await get_user(call.from_user.id)
    if row["coin"] < cost:
        return await call.answer(f"❌ برای ارتقا {cost:.0f} Coin نیاز دارید.", show_alert=True)
    await update_balance(call.from_user.id, coin=-cost)
    await conn.execute(
        "UPDATE countries SET economy_level = economy_level + 1, population = population + 500 "
        "WHERE user_id = ?",
        (call.from_user.id,),
    )
    await conn.commit()
    await log_tx(call.from_user.id, "country_upgrade", "coin", -cost, "ارتقای اقتصاد کشور")
    await call.message.edit_text("⬆ اقتصاد کشور شما ارتقا یافت!", reply_markup=back_kb("country"))


# ════════════════════════════════════════════════════════════════════
#  🏆  LEADERBOARD
# ════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "leaderboard")
async def cb_leaderboard(call: CallbackQuery):
    conn = await db()
    m = await get_market()
    cur = await conn.execute(
        "SELECT user_id, first_name, coin, liber FROM users WHERE is_banned = 0"
    )
    rows = await cur.fetchall()
    ranked = sorted(rows, key=lambda r: r["coin"] + r["liber"] * m["price"], reverse=True)[:10]
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🏆 <b>لیدربرد جهانی LIBER (ثروت کل)</b>\n"]
    for i, r in enumerate(ranked):
        wealth = r["coin"] + r["liber"] * m["price"]
        name = r["first_name"] or "کاربر"
        lines.append(f"{medals[i]} {name} — {wealth:,.0f} Coin")
    await call.message.edit_text("\n".join(lines), reply_markup=back_kb())


# ════════════════════════════════════════════════════════════════════
#  🧠  AI ADVISOR  —  آماده اتصال به یک LLM واقعی (اختیاری)
# ════════════════════════════════════════════════════════════════════

async def generate_ai_advice(user_id: int) -> str:
    """
    این تابع فعلاً قانون‌محور (rule-based) است تا بدون کلید API هم کار کند.
    برای اتصال به Claude/GPT واقعی کافی‌ست اینجا یک فراخوانی API اضافه کنی
    (مثلاً anthropic.Anthropic().messages.create(...)) و خروجی متنی را
    برگردانی — بقیهٔ ربات بدون تغییر کار می‌کند.
    """
    row = await get_user(user_id)
    m = await get_market()
    conn = await db()
    cur = await conn.execute("SELECT * FROM countries WHERE user_id = ?", (user_id,))
    country = await cur.fetchone()

    tips = []
    if row["coin"] > 5000 and row["liber"] < 5:
        tips.append("💡 موجودی Coin زیادی دارید ولی LIBER کم؛ بخشی را در بازار سرمایه‌گذاری کنید.")
    if row["energy"] < 30:
        tips.append("⚡ انرژی شما کم است؛ صبر کنید تا بازیابی شود یا VIP بگیرید.")
    if country is None:
        tips.append("🌍 هنوز کشوری نساخته‌اید؛ کشورسازی منبع درآمد پایدار می‌دهد.")
    elif country and calc_country_income(country) > 200:
        tips.append("🏦 درآمد کشور شما آماده برداشت است، فراموش نکنید جمعش کنید.")
    m_row = await get_market()
    conn2 = await db()
    cur2 = await conn2.execute("SELECT price FROM market_history ORDER BY id DESC LIMIT 2")
    last2 = await cur2.fetchall()
    if len(last2) == 2 and last2[0]["price"] > last2[1]["price"]:
        tips.append("📈 بازار در روند صعودی است؛ زمان مناسبی برای نگه‌داشتن LIBER است.")
    elif len(last2) == 2:
        tips.append("📉 بازار در روند نزولی است؛ احتیاط در خرید زیاد توصیه می‌شود.")

    if not tips:
        tips.append("✅ وضعیت اقتصادی شما متعادل است. به همین مسیر ادامه دهید.")

    header = f"🧠 <b>تحلیل امروز برای شما</b>\n\nقیمت فعلی LIBER: {m['price']:.2f} Coin\n\n"
    return header + "\n".join(tips)


@router.callback_query(F.data == "advisor")
async def cb_advisor(call: CallbackQuery):
    text = await generate_ai_advice(call.from_user.id)
    await call.message.edit_text(text, reply_markup=back_kb())


# ════════════════════════════════════════════════════════════════════
#  ⭐  VIP  &  🛒  SHOP
# ════════════════════════════════════════════════════════════════════

@router.callback_query(F.data == "vip")
async def cb_vip(call: CallbackQuery):
    row = await get_user(call.from_user.id)
    xp_mult, energy_mult = get_vip_multipliers(row)
    active = row["vip_level"] not in (None, "None", "") and xp_mult != 1.0 or energy_mult != 1.0
    status = f"فعال تا {row['vip_expiry'][:10]}" if row["vip_expiry"] and active else "غیرفعال"
    text = (
        f"⭐ <b>سطح VIP شما:</b> {row['vip_level']} ({status})\n"
        f"💎 Diamond شما: {row['diamond']}\n\n"
        f"هر سطح VIP: XP بیشتر از فعالیت‌ها + بازیابی سریع‌تر Energy\n"
    )
    buttons = [(v["label"] + f" ({v['cost_diamond']}💎)", f"buy_vip_{k}") for k, v in VIP_TIERS.items()]
    buttons.append(("🔙 برگشت", "menu"))
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@router.callback_query(F.data.startswith("buy_vip_"))
async def cb_buy_vip(call: CallbackQuery):
    tier_key = call.data.split("_", 2)[2]
    tier = VIP_TIERS.get(tier_key)
    if not tier:
        return await call.answer("نامعتبر", show_alert=True)
    row = await get_user(call.from_user.id)
    if row["diamond"] < tier["cost_diamond"]:
        return await call.answer("❌ Diamond کافی نیست.", show_alert=True)

    await update_balance(call.from_user.id, diamond=-tier["cost_diamond"])
    expiry = now_utc() + timedelta(days=tier["days"])
    conn = await db()
    await conn.execute(
        "UPDATE users SET vip_level = ?, vip_expiry = ? WHERE user_id = ?",
        (tier_key, expiry.isoformat(), call.from_user.id),
    )
    await conn.commit()
    await log_tx(call.from_user.id, "vip_purchase", "diamond", -tier["cost_diamond"], f"خرید {tier['label']}")
    await call.message.edit_text(
        f"🎉 {tier['label']} فعال شد تا {expiry.strftime('%Y-%m-%d')}!", reply_markup=back_kb("vip")
    )


@router.callback_query(F.data == "shop")
async def cb_shop(call: CallbackQuery):
    text = (
        "🛒 <b>فروشگاه LIBER</b>\n\n"
        "🪙 ارزها و بسته‌های ویژه (Diamond/Coin) از طریق درگاه پرداخت "
        "(TON / کارت) در نسخهٔ بعدی متصل می‌شود.\n\n"
        "همین الان می‌توانی:\n"
    )
    buttons = [
        ("⭐ خرید VIP", "vip"),
        ("🎁 صندوق‌ها", "boxes"),
        ("🔙 برگشت", "menu"),
    ]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


# ════════════════════════════════════════════════════════════════════
#  🏪  P2P PLAYER MARKET  —  معاملهٔ مستقیم بین بازیکنان
# ════════════════════════════════════════════════════════════════════

P2P_FEE_RATE = 0.02  # کارمزد بازار از فروشنده کسر می‌شود


class P2PStates(StatesGroup):
    waiting_order = State()


@router.callback_query(F.data == "p2p")
async def cb_p2p(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM p2p_orders WHERE status = 'open' ORDER BY price_per_unit ASC LIMIT 8"
    )
    orders = await cur.fetchall()
    lines = ["🏪 <b>بازار مستقیم بازیکنان</b>\n"]
    kb_rows = []
    if not orders:
        lines.append("در حال حاضر سفارش فروشی ثبت نشده.")
    else:
        for o in orders:
            seller = await get_user(o["seller_id"])
            sname = (seller["first_name"] if seller else "کاربر") or "کاربر"
            lines.append(f"👤 {sname} — {o['amount']:.2f} LIBER @ {o['price_per_unit']:.2f} Coin")
            kb_rows.append([InlineKeyboardButton(
                text=f"🟢 خرید از {sname} ({o['amount']:.2f}@{o['price_per_unit']:.2f})",
                callback_data=f"p2p_buy_{o['id']}",
            )])
    kb_rows.append([
        InlineKeyboardButton(text="➕ ثبت سفارش فروش", callback_data="p2p_sell_start"),
        InlineKeyboardButton(text="📋 سفارش‌های من", callback_data="p2p_myorders"),
    ])
    kb_rows.append([InlineKeyboardButton(text="🔙 برگشت", callback_data="menu")])
    await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data == "p2p_sell_start")
async def cb_p2p_sell_start(call: CallbackQuery, state: FSMContext):
    row = await get_user(call.from_user.id)
    await call.message.edit_text(
        f"➕ <b>ثبت سفارش فروش</b>\n\n"
        f"موجودی LIBER شما: {row['liber']:.2f} (حداقل ۱ باید باقی بماند)\n"
        f"کارمزد بازار: {P2P_FEE_RATE*100:.0f}٪ از فروشنده\n\n"
        f"مقدار و قیمت واحد را با فاصله بفرست، مثلاً:\n<code>100 95</code>\n"
        f"(یعنی فروش ۱۰۰ LIBER به قیمت ۹۵ Coin هرکدام)",
        reply_markup=back_kb("p2p"),
    )
    await state.set_state(P2PStates.waiting_order)


@router.message(P2PStates.waiting_order)
async def msg_p2p_sell_order(message: Message, state: FSMContext):
    await state.clear()
    parts = message.text.strip().split()
    if len(parts) != 2:
        return await message.answer("❌ فرمت اشتباه است. مثال: <code>100 95</code>")
    try:
        amount = float(parts[0])
        price = float(parts[1])
        assert amount > 0 and price > 0
    except (ValueError, AssertionError):
        return await message.answer("❌ اعداد نامعتبر است.")

    row = await get_user(message.from_user.id)
    if row["liber"] - amount < 1:
        return await message.answer(
            f"⚠️ باید حداقل ۱ LIBER در کیف پول باقی بماند.\nحداکثر قابل فروش: {row['liber']-1:.2f}"
        )

    # LIBER بلافاصله از کیف پول کسر و در سفارش قفل می‌شود (escrow)
    await update_balance(message.from_user.id, liber=-amount)
    conn = await db()
    await conn.execute(
        "INSERT INTO p2p_orders (seller_id, amount, price_per_unit, created_at, status) "
        "VALUES (?, ?, ?, ?, 'open')",
        (message.from_user.id, amount, price, ts()),
    )
    await conn.commit()
    await log_tx(message.from_user.id, "p2p_list", "liber", -amount, "ثبت سفارش فروش در بازار کاربران")
    await message.answer(
        f"✅ سفارش ثبت شد: {amount:.2f} LIBER @ {price:.2f} Coin", reply_markup=main_menu_kb()
    )


@router.callback_query(F.data.startswith("p2p_buy_"))
async def cb_p2p_buy(call: CallbackQuery):
    order_id = int(call.data.split("_")[-1])
    conn = await db()
    cur = await conn.execute("SELECT * FROM p2p_orders WHERE id = ? AND status = 'open'", (order_id,))
    order = await cur.fetchone()
    if not order:
        return await call.answer("❌ این سفارش دیگر در دسترس نیست.", show_alert=True)
    if order["seller_id"] == call.from_user.id:
        return await call.answer("❌ نمی‌توانید سفارش خودتان را بخرید.", show_alert=True)

    buyer = await get_user(call.from_user.id)
    total_cost = round(order["amount"] * order["price_per_unit"], 2)
    if buyer["coin"] < total_cost:
        return await call.answer("❌ موجودی Coin کافی نیست.", show_alert=True)

    if not await anti_cheat_ok(call.from_user.id, "trade"):
        return await call.answer("🛡 کمی صبر کنید.", show_alert=True)

    fee = round(total_cost * P2P_FEE_RATE, 2)
    seller_gets = total_cost - fee

    await conn.execute("UPDATE p2p_orders SET status = 'filled' WHERE id = ?", (order_id,))
    await conn.commit()

    await update_balance(call.from_user.id, coin=-total_cost, liber=order["amount"])
    await update_balance(order["seller_id"], coin=seller_gets)

    await log_tx(call.from_user.id, "p2p_buy", "liber", order["amount"], "خرید از بازار کاربران")
    await log_tx(call.from_user.id, "p2p_buy", "coin", -total_cost, "پرداخت خرید P2P")
    await log_tx(order["seller_id"], "p2p_sell", "coin", seller_gets, f"فروش P2P (کارمزد {fee:.2f})")
    await bump_trade_counters(call.from_user.id)

    try:
        await bot.send_message(
            order["seller_id"],
            f"🏪 سفارش شما فروخته شد!\n{order['amount']:.2f} LIBER @ {order['price_per_unit']:.2f}\n"
            f"دریافتی: {seller_gets:.2f} Coin (کارمزد {fee:.2f})",
        )
    except Exception:
        pass

    await call.message.edit_text(
        f"✅ خرید موفق: {order['amount']:.2f} LIBER دریافت شد.", reply_markup=back_kb("p2p")
    )


@router.callback_query(F.data == "p2p_myorders")
async def cb_p2p_myorders(call: CallbackQuery):
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM p2p_orders WHERE seller_id = ? AND status = 'open'", (call.from_user.id,)
    )
    orders = await cur.fetchall()
    if not orders:
        return await call.answer("سفارش بازی ندارید.", show_alert=True)
    kb_rows = []
    lines = ["📋 <b>سفارش‌های باز شما</b>\n"]
    for o in orders:
        lines.append(f"{o['amount']:.2f} LIBER @ {o['price_per_unit']:.2f} Coin")
        kb_rows.append([InlineKeyboardButton(text=f"❌ لغو سفارش #{o['id']}", callback_data=f"p2p_cancel_{o['id']}")])
    kb_rows.append([InlineKeyboardButton(text="🔙 برگشت", callback_data="p2p")])
    await call.message.edit_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))


@router.callback_query(F.data.startswith("p2p_cancel_"))
async def cb_p2p_cancel(call: CallbackQuery):
    order_id = int(call.data.split("_")[-1])
    conn = await db()
    cur = await conn.execute(
        "SELECT * FROM p2p_orders WHERE id = ? AND seller_id = ? AND status = 'open'",
        (order_id, call.from_user.id),
    )
    order = await cur.fetchone()
    if not order:
        return await call.answer("یافت نشد.", show_alert=True)
    await conn.execute("UPDATE p2p_orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    await conn.commit()
    await update_balance(call.from_user.id, liber=order["amount"])
    await log_tx(call.from_user.id, "p2p_cancel", "liber", order["amount"], "لغو سفارش بازار کاربران")
    await call.answer("✅ سفارش لغو و LIBER بازگردانده شد.", show_alert=True)


# ════════════════════════════════════════════════════════════════════
#  👑  ADMIN PANEL
# ════════════════════════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


class AdminStates(StatesGroup):
    waiting_broadcast = State()
    waiting_user_lookup = State()
    waiting_balance_edit = State()


@admin_router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("👑 <b>پنل مدیریت LIBER</b>", reply_markup=admin_menu_kb())


@admin_router.message(Command("id"))
async def cmd_id(message: Message):
    await message.answer(f"🆔 آیدی عددی شما: <code>{message.from_user.id}</code>")


def admin_menu_kb() -> InlineKeyboardMarkup:
    buttons = [
        ("📊 داشبورد", "adm_dashboard"),
        ("👥 جستجوی کاربر", "adm_lookup"),
        ("📈 مدیریت بازار", "adm_market"),
        ("📢 پیام همگانی", "adm_broadcast"),
        ("🔙 برگشت", "menu"),
    ]
    return kb(chunk3(buttons))


@admin_router.callback_query(F.data == "adm_dashboard")
async def cb_adm_dashboard(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    conn = await db()
    total_users = (await (await conn.execute("SELECT COUNT(*) c FROM users")).fetchone())["c"]
    total_coin = (await (await conn.execute("SELECT COALESCE(SUM(coin),0) s FROM users")).fetchone())["s"]
    total_liber = (await (await conn.execute("SELECT COALESCE(SUM(liber),0) s FROM users")).fetchone())["s"]
    banned = (await (await conn.execute("SELECT COUNT(*) c FROM users WHERE is_banned=1")).fetchone())["c"]
    m = await get_market()
    text = (
        f"📊 <b>داشبورد LIBER</b>\n\n"
        f"👥 کاربران: {total_users:,}\n"
        f"🚫 مسدود: {banned}\n"
        f"💰 کل Coin: {total_coin:,.0f}\n"
        f"🪙 کل LIBER: {total_liber:,.2f}\n"
        f"📈 قیمت LIBER: {m['price']:.2f} Coin\n"
    )
    await call.message.edit_text(text, reply_markup=back_kb("adm_menu"))


@admin_router.callback_query(F.data == "adm_menu")
async def cb_adm_menu(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("👑 <b>پنل مدیریت LIBER</b>", reply_markup=admin_menu_kb())


@admin_router.callback_query(F.data == "adm_lookup")
async def cb_adm_lookup(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("🆔 آیدی عددی کاربر را بفرستید:", reply_markup=back_kb("adm_menu"))
    await state.set_state(AdminStates.waiting_user_lookup)


@admin_router.message(AdminStates.waiting_user_lookup)
async def msg_adm_lookup(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    try:
        target_id = int(message.text.strip())
    except ValueError:
        return await message.answer("❌ آیدی نامعتبر.")
    row = await get_user(target_id)
    if not row:
        return await message.answer("کاربری یافت نشد.")
    text = (
        f"👤 <b>{row['first_name']}</b> (@{row['username']})\n"
        f"🆔 {row['user_id']}\n"
        f"Level {row['level']} | VIP {row['vip_level']}\n"
        f"💰 {row['coin']:.0f} Coin | 🪙 {row['liber']:.2f} LIBER\n"
        f"🚫 مسدود: {'بله' if row['is_banned'] else 'خیر'}\n"
    )
    buttons = [
        ("➕ افزودن ۱۰۰۰ Coin", f"adm_addcoin_{target_id}"),
        ("🚫 مسدود/آزاد", f"adm_toggleban_{target_id}"),
        ("🔙 برگشت", "adm_menu"),
    ]
    await message.answer(text, reply_markup=kb(chunk3(buttons)))


@admin_router.callback_query(F.data.startswith("adm_addcoin_"))
async def cb_adm_addcoin(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    target_id = int(call.data.split("_")[-1])
    await update_balance(target_id, coin=1000)
    await log_tx(target_id, "admin_grant", "coin", 1000, f"افزوده شده توسط ادمین {call.from_user.id}")
    await call.answer("✅ ۱۰۰۰ Coin اضافه شد.", show_alert=True)


@admin_router.callback_query(F.data.startswith("adm_toggleban_"))
async def cb_adm_toggleban(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    target_id = int(call.data.split("_")[-1])
    row = await get_user(target_id)
    new_state = 0 if row["is_banned"] else 1
    conn = await db()
    await conn.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (new_state, target_id))
    await conn.commit()
    await call.answer("✅ وضعیت تغییر کرد.", show_alert=True)


@admin_router.callback_query(F.data == "adm_market")
async def cb_adm_market(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    m = await get_market()
    text = f"📈 قیمت فعلی: {m['price']:.2f} Coin\nBaseline: {m['baseline']:.2f}"
    buttons = [
        ("🔥 رونق (+20%)", "adm_boom"),
        ("⚠️ بحران (-20%)", "adm_crisis"),
        ("🔙 برگشت", "adm_menu"),
    ]
    await call.message.edit_text(text, reply_markup=kb(chunk3(buttons)))


@admin_router.callback_query(F.data.in_(["adm_boom", "adm_crisis"]))
async def cb_adm_event(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return await call.answer()
    conn = await db()
    factor = 1.2 if call.data == "adm_boom" else 0.8
    m = await get_market()
    new_price = round(m["price"] * factor, 2)
    await conn.execute("UPDATE market SET price = ?, updated_at = ? WHERE id = 1", (new_price, ts()))
    await conn.commit()
    label = "🔥 رونق اقتصادی" if factor > 1 else "⚠️ بحران اقتصادی"
    await broadcast_all(f"{label}!\n\nقیمت جدید LIBER: {new_price:.2f} Coin")
    await call.answer("✅ رویداد اعمال شد و به همه اطلاع‌رسانی شد.", show_alert=True)


@admin_router.callback_query(F.data == "adm_broadcast")
async def cb_adm_broadcast(call: CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        return await call.answer()
    await call.message.edit_text("📢 متن پیام همگانی را بفرستید:", reply_markup=back_kb("adm_menu"))
    await state.set_state(AdminStates.waiting_broadcast)


@admin_router.message(AdminStates.waiting_broadcast)
async def msg_adm_broadcast(message: Message, state: FSMContext):
    await state.clear()
    if not is_admin(message.from_user.id):
        return
    count = await broadcast_all(message.text)
    conn = await db()
    await conn.execute(
        "INSERT INTO broadcasts_log (admin_id, text, sent_at, total_sent) VALUES (?, ?, ?, ?)",
        (message.from_user.id, message.text, ts(), count),
    )
    await conn.commit()
    await message.answer(f"✅ پیام به {count} کاربر ارسال شد.")


async def broadcast_all(text: str) -> int:
    conn = await db()
    cur = await conn.execute("SELECT user_id FROM users WHERE is_banned = 0")
    rows = await cur.fetchall()
    sent = 0
    for r in rows:
        try:
            await bot.send_message(r["user_id"], f"📢 <b>اطلاعیه LIBER</b>\n\n{text}")
            sent += 1
            await asyncio.sleep(0.05)  # جلوگیری از rate-limit تلگرام
        except Exception:
            continue
    return sent


# ════════════════════════════════════════════════════════════════════
#  ⏱  SCHEDULER  —  جهان زندهٔ خودکار
# ════════════════════════════════════════════════════════════════════

WORLD_EVENTS = [
    "🌅 یک معدن بزرگ LIBER کشف شد! تولید معدن‌ها افزایش یافت.",
    "⚠️ بحران انرژی جهانی؛ هزینهٔ کارخانه‌ها موقتاً بالا رفت.",
    "🎉 جشن جهانی LIBER آغاز شد؛ امروز XP دو برابر است.",
    "📉 نوسان شدید بازار؛ مراقب معاملات پرریسک باشید.",
]


async def random_world_event_job():
    if random.random() < 0.3:  # ۳۰٪ احتمال هر اجرا
        event = random.choice(WORLD_EVENTS)
        await broadcast_all(event)
        log.info(f"🌍 World event fired: {event}")


def setup_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(market_tick, "interval", hours=1, id="market_tick")
    scheduler.add_job(bank_daily_interest_job, "interval", hours=24, id="bank_interest")
    scheduler.add_job(random_world_event_job, "interval", hours=6, id="world_event")
    return scheduler


# ════════════════════════════════════════════════════════════════════
#  ▶️  ENTRYPOINT
# ════════════════════════════════════════════════════════════════════

async def main():
    await db()  # اطمینان از ساخته‌شدن جداول قبل از استارت
    scheduler = setup_scheduler()
    scheduler.start()
    log.info("🌌 LIBER bot is starting...")
    try:
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        if _db:
            await _db.close()


if __name__ == "__main__":
    if BOT_TOKEN == "PUT_YOUR_BOT_TOKEN_HERE":
        raise SystemExit(
            "❌ ابتدا متغیر محیطی LIBER_BOT_TOKEN را با توکن ربات خودت ست کن "
            "(یا مقدار BOT_TOKEN را در بالای فایل تغییر بده)."
        )
    asyncio.run(main())
