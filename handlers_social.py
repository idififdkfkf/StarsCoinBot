# -*- coding: utf-8 -*-
"""
handlers_social.py — قابلیت‌های اجتماعی و رقابتی ربات LIBER (فایل جدا)
================================================================
فایل کاملاً جدا. جدول‌های خودش را در اولین استفاده می‌سازد.

⚠️ توجه: قابلیت «⚡ جایزه‌ی برق‌آسا» طبق درخواست کاربر کاملاً حذف شده
(هم جدول/جاب زمان‌بندی‌شده‌اش و هم دکمه‌اش) — دیگر هیچ‌جا وجود ندارد.

شامل ۵ قابلیت باقی‌مانده:
    🔥 جنگ بزرگ سروری        ۵ نفر هم‌رنک هم‌زمان وارد می‌شن، هر چند دقیقه نتیجه‌ی گروهی
    📅 ماموریت هفتگی          چالش ۵ برد در طول هفته، جایزه‌ی بزرگ‌تر از روزانه
    🎨 فروشگاه ظاهری          قاب و لقب کنار اسم (فقط جنبه‌ی نمایشی)
    🎫 قرعه‌کشی روزانه         یک شانس رایگان در روز برای جایزه‌ی بزرگ
    💸 ارسال LIBER به کاربر    انتقال مستقیم بین دو کاربر
    👹 چالش هفتگی باس          فقط یک‌بار در هفته، حریف قوی، جایزه‌ی بزرگ
"""
import time
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import (
    get_conn, get_user, update_balance, log_transaction,
    ADMIN_IDS, RANKS, back_keyboard,
)

logger = logging.getLogger("LIBER.social")

SERVER_WAR_MIN_PLAYERS = 5
SERVER_WAR_CHECK_SECONDS = 180
SERVER_WAR_REWARDS = {1: 300, 2: 220, 3: 160, 4: 100, 5: 60}

WEEKLY_MISSION_WINS_NEEDED = 5
WEEKLY_MISSION_REWARD_LIBER = 300
WEEKLY_MISSION_REWARD_XP = 100

CLUB_TASKS = {
    "win2": {"desc": "🏆 ۲ برد در رقابت آنلاین بگیر", "target": 2, "reward_xp": 30, "reward_liber": 20},
    "chest2": {"desc": "🎁 ۲ صندوق باز کن", "target": 2, "reward_xp": 30, "reward_liber": 20},
    "trade2": {"desc": "💹 ۲ بار تو بازار خرید/فروش کن", "target": 2, "reward_xp": 30, "reward_liber": 20},
    "daily3": {"desc": "🎯 ۳ بار ماموریت روزانه رو بگیر", "target": 3, "reward_xp": 30, "reward_liber": 20},
}

COSMETIC_ITEMS = {
    "frame_gold": {"name": "🖼 قاب طلایی", "type": "frame", "cost": 500, "display": "🟡"},
    "frame_diamond": {"name": "🖼 قاب الماسی", "type": "frame", "cost": 1200, "display": "💠"},
    "frame_dragon": {"name": "🖼 قاب اژدهایی", "type": "frame", "cost": 2000, "display": "🐉"},
    "title_legend": {"name": "🏷 لقب افسانه‌ای", "type": "title", "cost": 800, "display": "افسانه‌ای"},
    "title_champion": {"name": "🏷 لقب قهرمان", "type": "title", "cost": 1500, "display": "قهرمان"},
    "title_mythic": {"name": "🏷 لقب اسطوره‌ای", "type": "title", "cost": 2500, "display": "اسطوره‌ای"},
}

LOTTERY_PRIZES = [
    (40, 20, 60),
    (30, 60, 150),
    (18, 150, 400),
    (9, 400, 900),
    (3, 900, 2500),
]

P2P_MIN_TRANSFER = 10
P2P_MAX_TRANSFER = 100000

WEEKLY_BOSS_ENTRY_FEE = 100
WEEKLY_BOSS_REWARD = 1500
WEEKLY_BOSS_WIN_CHANCE = 0.35


_tables_ready = False


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS server_war_queue (
            user_id INTEGER PRIMARY KEY,
            rank_index INTEGER NOT NULL,
            joined_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_mission (
            user_id INTEGER,
            week_key TEXT,
            wins_done INTEGER NOT NULL DEFAULT 0,
            claimed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, week_key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cosmetic_owned (
            user_id INTEGER,
            item_key TEXT,
            purchased_at INTEGER NOT NULL,
            PRIMARY KEY (user_id, item_key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS cosmetic_equipped (
            user_id INTEGER PRIMARY KEY,
            frame_key TEXT,
            title_key TEXT
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_lottery_claims (
            user_id INTEGER,
            claim_date TEXT,
            PRIMARY KEY (user_id, claim_date)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS p2p_transfers (
            transfer_id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER NOT NULL,
            to_user INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS weekly_boss_claims (
            user_id INTEGER,
            week_key TEXT,
            PRIMARY KEY (user_id, week_key)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS club_task_progress (
            user_id INTEGER,
            week_key TEXT,
            task_key TEXT,
            progress INTEGER NOT NULL DEFAULT 0,
            completed INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, week_key, task_key)
        )
        """)
    _tables_ready = True


def _week_key(ts=None):
    ts = ts if ts is not None else time.time()
    return time.strftime("%Y-W%W", time.gmtime(ts))


def _today_key():
    return time.strftime("%Y-%m-%d", time.gmtime())


def _rank_index_of(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT rank_index FROM comp_profile WHERE user_id = ?", (user_id,)).fetchone()
    return row["rank_index"] if row else 0


# ---------------------------------------------------------------
#  جنگ بزرگ سروری
# ---------------------------------------------------------------
def _server_war_menu_keyboard(in_queue):
    rows = []
    if in_queue:
        rows.append([InlineKeyboardButton("🚪 خروج از صف", callback_data="serverwar_leave")])
    else:
        rows.append([InlineKeyboardButton("🔥 ورود به صف جنگ", callback_data="serverwar_join")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def server_war_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    with get_conn() as conn:
        my_entry = conn.execute("SELECT 1 FROM server_war_queue WHERE user_id = ?", (user_id,)).fetchone()
        rank_index = _rank_index_of(user_id)
        queued_same_rank = conn.execute(
            "SELECT COUNT(*) c FROM server_war_queue WHERE rank_index = ?", (rank_index,)
        ).fetchone()["c"]

    r = SERVER_WAR_REWARDS
    text = (
        f"🔥 جنگ بزرگ سروری\n\n"
        f"وقتی {SERVER_WAR_MIN_PLAYERS} نفر هم‌رنک وارد صف بشن، خودکار جنگ شروع می‌شه "
        f"(هر {SERVER_WAR_CHECK_SECONDS // 60} دقیقه چک می‌شه).\n\n"
        f"رنک شما: {RANKS[rank_index]}\n"
        f"نفرات در صف هم‌رنک شما: {queued_same_rank}/{SERVER_WAR_MIN_PLAYERS}\n\n"
        f"🏆 جوایز: ۱ام {r[1]} | ۲ام {r[2]} | ۳ام {r[3]} | ۴ام {r[4]} | ۵ام {r[5]} LIBER"
    )
    await q.edit_message_text(text, reply_markup=_server_war_menu_keyboard(bool(my_entry)))


async def server_war_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id

    with get_conn() as conn:
        already = conn.execute("SELECT 1 FROM server_war_queue WHERE user_id = ?", (user_id,)).fetchone()
    if already:
        await q.answer("⏳ شما همین الان هم در صف هستید.", show_alert=True)
        return

    await q.answer()
    rank_index = _rank_index_of(user_id)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO server_war_queue (user_id, rank_index, joined_at) VALUES (?, ?, ?)",
            (user_id, rank_index, int(time.time())),
        )
    await q.edit_message_text(
        f"🔥 وارد صف جنگ بزرگ شدی! هر {SERVER_WAR_CHECK_SECONDS // 60} دقیقه چک می‌شه.",
        reply_markup=_server_war_menu_keyboard(True),
    )


async def server_war_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        conn.execute("DELETE FROM server_war_queue WHERE user_id = ?", (q.from_user.id,))
    await q.edit_message_text("🚪 از صف جنگ بزرگ خارج شدی.", reply_markup=_server_war_menu_keyboard(False))


async def server_war_matching_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    with get_conn() as conn:
        queued = conn.execute("SELECT * FROM server_war_queue ORDER BY joined_at ASC").fetchall()

    by_rank = {}
    for row in queued:
        by_rank.setdefault(row["rank_index"], []).append(row["user_id"])

    for rank_index, user_ids in by_rank.items():
        while len(user_ids) >= SERVER_WAR_MIN_PLAYERS:
            group = user_ids[:SERVER_WAR_MIN_PLAYERS]
            user_ids = user_ids[SERVER_WAR_MIN_PLAYERS:]
            with get_conn() as conn:
                for uid in group:
                    conn.execute("DELETE FROM server_war_queue WHERE user_id = ?", (uid,))
            await _resolve_server_war(context.bot, group, rank_index)


async def _resolve_server_war(bot, user_ids, rank_index):
    scored = [(uid, rank_index * 10 + random.randint(0, 100)) for uid in user_ids]
    scored.sort(key=lambda x: x[1], reverse=True)

    for placement, (uid, score) in enumerate(scored, start=1):
        reward = SERVER_WAR_REWARDS.get(placement, 0)
        if reward:
            update_balance(uid, liber=reward)
        log_transaction(uid, "SERVER_WAR", f"placement={placement} reward={reward}")
        try:
            await bot.send_message(
                uid,
                f"🔥 جنگ بزرگ سروری تمام شد!\n🏅 رتبه‌ی شما: {placement} از {len(scored)}\n"
                f"🎁 جایزه: {reward} LIBER",
            )
        except TelegramError:
            pass


# ---------------------------------------------------------------
#  ماموریت هفتگی
# ---------------------------------------------------------------
async def weekly_mission_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    week_key = _week_key()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_mission WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchone()

    wins_done = row["wins_done"] if row else 0
    claimed = row["claimed"] if row else 0

    if claimed:
        text = "✅ ماموریت این هفته رو کامل کردی و جایزه رو گرفتی. هفته‌ی بعد دوباره سر بزن!"
        markup = back_keyboard()
    elif wins_done >= WEEKLY_MISSION_WINS_NEEDED:
        text = f"🎉 {WEEKLY_MISSION_WINS_NEEDED} برد این هفته رو کامل کردی! آماده‌ی گرفتن جایزه‌ای:"
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 دریافت جایزه", callback_data="weeklymission_claim")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
        ])
    else:
        text = (
            f"📅 ماموریت هفتگی\n\n"
            f"پیشرفت: {wins_done}/{WEEKLY_MISSION_WINS_NEEDED} برد در رقابت آنلاین\n"
            f"🎁 جایزه: {WEEKLY_MISSION_REWARD_LIBER} LIBER + {WEEKLY_MISSION_REWARD_XP} XP"
        )
        markup = back_keyboard()

    await q.edit_message_text(text, reply_markup=markup)


async def weekly_mission_claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    week_key = _week_key()

    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_mission WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchone()

    if not row or row["wins_done"] < WEEKLY_MISSION_WINS_NEEDED or row["claimed"]:
        await q.answer("هنوز آماده نیست یا قبلاً گرفتی.", show_alert=True)
        return

    await q.answer()
    with get_conn() as conn:
        conn.execute(
            "UPDATE weekly_mission SET claimed = 1 WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        )
    update_balance(user_id, liber=WEEKLY_MISSION_REWARD_LIBER, xp=WEEKLY_MISSION_REWARD_XP)
    log_transaction(user_id, "WEEKLY_MISSION_CLAIM", week_key)
    await q.edit_message_text(
        f"🎉 جایزه‌ی ماموریت هفتگی گرفتی!\n+{WEEKLY_MISSION_REWARD_LIBER} LIBER, +{WEEKLY_MISSION_REWARD_XP} XP",
        reply_markup=back_keyboard(),
    )


def record_weekly_win(user_id):
    _ensure_tables()
    week_key = _week_key()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM weekly_mission WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchone()
        if not row:
            conn.execute(
                "INSERT INTO weekly_mission (user_id, week_key, wins_done) VALUES (?, ?, 1)",
                (user_id, week_key),
            )
        elif row["wins_done"] < WEEKLY_MISSION_WINS_NEEDED:
            conn.execute(
                "UPDATE weekly_mission SET wins_done = wins_done + 1 WHERE user_id = ? AND week_key = ?",
                (user_id, week_key),
            )


def record_club_task_progress(user_id, task_key):
    _ensure_tables()
    task = CLUB_TASKS.get(task_key)
    if not task:
        return None
    week_key = _week_key()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM club_task_progress WHERE user_id = ? AND week_key = ? AND task_key = ?",
            (user_id, week_key, task_key),
        ).fetchone()
        if row and row["completed"]:
            return None

        new_progress = (row["progress"] if row else 0) + 1
        just_completed = new_progress >= task["target"]

        if row:
            conn.execute(
                "UPDATE club_task_progress SET progress = ?, completed = ? WHERE user_id = ? AND week_key = ? AND task_key = ?",
                (new_progress, 1 if just_completed else 0, user_id, week_key, task_key),
            )
        else:
            conn.execute(
                "INSERT INTO club_task_progress (user_id, week_key, task_key, progress, completed) VALUES (?, ?, ?, ?, ?)",
                (user_id, week_key, task_key, new_progress, 1 if just_completed else 0),
            )

    if just_completed:
        update_balance(user_id, liber=task["reward_liber"], xp=task["reward_xp"])
        log_transaction(user_id, "CLUB_TASK_DONE", task_key)
        return task
    return None


async def club_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    week_key = _week_key()

    with get_conn() as conn:
        rows = {r["task_key"]: r for r in conn.execute(
            "SELECT * FROM club_task_progress WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchall()}

    lines = ["🎫 باشگاه مشتریان — ماموریت‌های این هفته\n"]
    done_count = 0
    for key, task in CLUB_TASKS.items():
        row = rows.get(key)
        progress = row["progress"] if row else 0
        completed = bool(row and row["completed"])
        done_count += 1 if completed else 0
        mark = "✅" if completed else "⬜"
        lines.append(f"{mark} {task['desc']} — {min(progress, task['target'])}/{task['target']}  (+{task['reward_xp']}XP, +{task['reward_liber']} LIBER)")

    lines.append(f"\n📊 {done_count}/{len(CLUB_TASKS)} ماموریت این هفته کامل شده.")
    lines.append("هر ماموریت جدا و خودکار وقتی کاملش کنی جایزه می‌گیری — هر ۷ روز ست جدید میاد.")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


def _cosmetic_shop_keyboard(owned_keys):
    rows = []
    for key, item in COSMETIC_ITEMS.items():
        mark = "✅ " if key in owned_keys else ""
        rows.append([InlineKeyboardButton(
            f"{mark}{item['name']} — {item['cost']} LIBER", callback_data=f"cosmetic_buy:{key}"
        )])
    rows.append([InlineKeyboardButton("🎽 ویترین من (انتخاب فعال)", callback_data="cosmetic_equip_menu")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def cosmetic_shop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    with get_conn() as conn:
        owned = {r["item_key"] for r in conn.execute(
            "SELECT item_key FROM cosmetic_owned WHERE user_id = ?", (user_id,)
        ).fetchall()}
    await q.edit_message_text(
        "🎨 فروشگاه ظاهری\n\nفقط جنبه‌ی نمایشی داره، تاثیری در قدرت یا رنک نداره:",
        reply_markup=_cosmetic_shop_keyboard(owned),
    )


async def cosmetic_buy_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    item_key = q.data.split(":", 1)[1]
    item = COSMETIC_ITEMS.get(item_key)
    if not item:
        await q.answer("آیتم نامعتبر است.", show_alert=True)
        return

    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM cosmetic_owned WHERE user_id = ? AND item_key = ?", (user_id, item_key)
        ).fetchone()
    if already:
        await q.answer("✅ این آیتم رو قبلاً داری.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < item["cost"]:
        await q.answer(f"❌ LIBER کافی نیست. هزینه: {item['cost']}", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-item["cost"])
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO cosmetic_owned (user_id, item_key, purchased_at) VALUES (?, ?, ?)",
            (user_id, item_key, int(time.time())),
        )
    log_transaction(user_id, "COSMETIC_BUY", item_key)

    with get_conn() as conn:
        owned = {r["item_key"] for r in conn.execute(
            "SELECT item_key FROM cosmetic_owned WHERE user_id = ?", (user_id,)
        ).fetchall()}
    await q.edit_message_text(f"✅ {item['name']} خریداری شد!", reply_markup=_cosmetic_shop_keyboard(owned))


async def cosmetic_equip_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    with get_conn() as conn:
        owned = conn.execute("SELECT item_key FROM cosmetic_owned WHERE user_id = ?", (user_id,)).fetchall()
    owned_keys = [r["item_key"] for r in owned]

    if not owned_keys:
        await q.edit_message_text("هنوز هیچ آیتم ظاهری نخریدی.", reply_markup=back_keyboard())
        return

    rows = [[InlineKeyboardButton(COSMETIC_ITEMS[k]["name"], callback_data=f"cosmetic_equip:{k}")] for k in owned_keys]
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    await q.edit_message_text("🎽 کدوم رو فعال کنم؟", reply_markup=InlineKeyboardMarkup(rows))


async def cosmetic_equip_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    item_key = q.data.split(":", 1)[1]
    item = COSMETIC_ITEMS.get(item_key)
    if not item:
        await q.answer("آیتم نامعتبر است.", show_alert=True)
        return

    await q.answer()
    field = "frame_key" if item["type"] == "frame" else "title_key"
    with get_conn() as conn:
        exists = conn.execute("SELECT 1 FROM cosmetic_equipped WHERE user_id = ?", (user_id,)).fetchone()
        if exists:
            conn.execute(f"UPDATE cosmetic_equipped SET {field} = ? WHERE user_id = ?", (item_key, user_id))
        else:
            conn.execute(
                f"INSERT INTO cosmetic_equipped (user_id, {field}) VALUES (?, ?)", (user_id, item_key)
            )
    await q.edit_message_text(f"✅ {item['name']} فعال شد و کنار اسمت نشون داده می‌شه!", reply_markup=back_keyboard())


def get_display_badge(user_id):
    _ensure_tables()
    with get_conn() as conn:
        row = conn.execute("SELECT frame_key, title_key FROM cosmetic_equipped WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return ""
    parts = []
    if row["frame_key"] and row["frame_key"] in COSMETIC_ITEMS:
        parts.append(COSMETIC_ITEMS[row["frame_key"]]["display"])
    if row["title_key"] and row["title_key"] in COSMETIC_ITEMS:
        parts.append(f"«{COSMETIC_ITEMS[row['title_key']]['display']}»")
    return " ".join(parts)


async def lottery_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    today = _today_key()

    with get_conn() as conn:
        claimed = conn.execute(
            "SELECT 1 FROM daily_lottery_claims WHERE user_id = ? AND claim_date = ?", (user_id, today)
        ).fetchone()

    if claimed:
        await q.edit_message_text("🎫 قرعه‌کشی امروز رو قبلاً امتحان کردی. فردا دوباره سر بزن!", reply_markup=back_keyboard())
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎫 امتحان کن!", callback_data="lottery_draw")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])
    await q.edit_message_text(
        "🎫 قرعه‌کشی روزانه\n\nهر روز یک شانس رایگان برای جایزه‌ی بزرگ — از ۲۰ تا ۲۵۰۰ LIBER!",
        reply_markup=markup,
    )


async def lottery_draw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    today = _today_key()

    with get_conn() as conn:
        claimed = conn.execute(
            "SELECT 1 FROM daily_lottery_claims WHERE user_id = ? AND claim_date = ?", (user_id, today)
        ).fetchone()
    if claimed:
        await q.answer("قبلاً امروز امتحان کردی.", show_alert=True)
        return

    await q.answer()
    weights = [w for w, _, _ in LOTTERY_PRIZES]
    _, low, high = random.choices(LOTTERY_PRIZES, weights=weights, k=1)[0]
    prize = random.randint(low, high)

    update_balance(user_id, liber=prize)
    with get_conn() as conn:
        conn.execute("INSERT INTO daily_lottery_claims (user_id, claim_date) VALUES (?, ?)", (user_id, today))
    log_transaction(user_id, "DAILY_LOTTERY", str(prize))

    emoji = "🎊" if prize >= 900 else "🎉"
    await q.edit_message_text(f"{emoji} قرعه‌کشی زدی و بردی: +{prize} LIBER!\n\nفردا دوباره امتحان کن.", reply_markup=back_keyboard())


async def transfer_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting"] = "transfer_target_id"
    await q.edit_message_text(
        f"💸 ارسال LIBER\n\nآیدی عددی کاربری که می‌خواهید بهش LIBER بفرستید رو وارد کنید\n"
        f"(حداقل {P2P_MIN_TRANSFER}، حداکثر {P2P_MAX_TRANSFER} در هر تراکنش):"
    )


async def _do_transfer_target(update, context, raw_text):
    try:
        target_id = int(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ آیدی نامعتبر است.")
        return
    if target_id == update.effective_user.id:
        await update.message.reply_text("❌ نمی‌تونی به خودت بفرستی.")
        return
    if not get_user(target_id):
        await update.message.reply_text("❌ کاربری با این آیدی پیدا نشد.")
        return
    context.user_data["transfer_target"] = target_id
    context.user_data["awaiting"] = "transfer_amount"
    await update.message.reply_text("💰 چقدر LIBER می‌خواهید بفرستید؟")


async def _do_transfer_amount(update, context, raw_text):
    user_id = update.effective_user.id
    try:
        amount = float(raw_text.strip())
    except ValueError:
        await update.message.reply_text("❌ عدد معتبر وارد کنید.")
        return
    if amount < P2P_MIN_TRANSFER or amount > P2P_MAX_TRANSFER:
        await update.message.reply_text(f"❌ مقدار باید بین {P2P_MIN_TRANSFER} تا {P2P_MAX_TRANSFER} باشد.")
        return

    user = get_user(user_id)
    if user["liber"] < amount:
        await update.message.reply_text("❌ موجودی LIBER کافی نیست.")
        return

    target_id = context.user_data.pop("transfer_target", None)
    context.user_data["awaiting"] = None
    if not target_id:
        await update.message.reply_text("❌ گیرنده مشخص نیست، دوباره از منو شروع کنید.")
        return

    _ensure_tables()
    update_balance(user_id, liber=-amount)
    update_balance(target_id, liber=amount)
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO p2p_transfers (from_user, to_user, amount, created_at) VALUES (?, ?, ?, ?)",
            (user_id, target_id, amount, int(time.time())),
        )
    log_transaction(user_id, "P2P_SEND", f"to={target_id} amount={amount}")
    log_transaction(target_id, "P2P_RECEIVE", f"from={user_id} amount={amount}")

    await update.message.reply_text(f"✅ {amount} LIBER با موفقیت ارسال شد!", reply_markup=back_keyboard())
    try:
        sender = get_user(user_id)
        sender_name = sender["first_name"] if sender else "یک کاربر"
        await context.bot.send_message(target_id, f"💸 {sender_name} برات {amount} LIBER فرستاد!")
    except TelegramError:
        pass


async def weekly_boss_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    week_key = _week_key()

    with get_conn() as conn:
        done = conn.execute(
            "SELECT 1 FROM weekly_boss_claims WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchone()

    if done:
        await q.edit_message_text(
            "👹 این هفته قبلاً با باس جنگیدی. هفته‌ی بعد دوباره سر بزن!", reply_markup=back_keyboard()
        )
        return

    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⚔️ نبرد با باس ({WEEKLY_BOSS_ENTRY_FEE} LIBER)", callback_data="weeklyboss_fight")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")],
    ])
    await q.edit_message_text(
        f"👹 چالش هفتگی باس\n\nفقط یک‌بار در هفته می‌تونی امتحان کنی.\n"
        f"هزینه‌ی ورود: {WEEKLY_BOSS_ENTRY_FEE} LIBER\n"
        f"شانس برد: {int(WEEKLY_BOSS_WIN_CHANCE*100)}٪\n"
        f"🎁 جایزه‌ی برد: {WEEKLY_BOSS_REWARD} LIBER",
        reply_markup=markup,
    )


async def weekly_boss_fight_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    week_key = _week_key()

    with get_conn() as conn:
        done = conn.execute(
            "SELECT 1 FROM weekly_boss_claims WHERE user_id = ? AND week_key = ?", (user_id, week_key)
        ).fetchone()
    if done:
        await q.answer("قبلاً این هفته امتحان کردی.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < WEEKLY_BOSS_ENTRY_FEE:
        await q.answer(f"❌ برای ورود به {WEEKLY_BOSS_ENTRY_FEE} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    with get_conn() as conn:
        conn.execute("INSERT INTO weekly_boss_claims (user_id, week_key) VALUES (?, ?)", (user_id, week_key))
    update_balance(user_id, liber=-WEEKLY_BOSS_ENTRY_FEE)

    won = random.random() < WEEKLY_BOSS_WIN_CHANCE
    if won:
        update_balance(user_id, liber=WEEKLY_BOSS_REWARD)
        log_transaction(user_id, "WEEKLY_BOSS", "win")
        text = f"🎉 باس رو شکست دادی! +{WEEKLY_BOSS_REWARD} LIBER"
    else:
        log_transaction(user_id, "WEEKLY_BOSS", "loss")
        text = f"😔 این‌بار باس برد. -{WEEKLY_BOSS_ENTRY_FEE} LIBER (هفته‌ی بعد دوباره امتحان کن)"

    await q.edit_message_text(text, reply_markup=back_keyboard())


SOCIAL_CALLBACKS = {
    "menu_serverwar": server_war_menu_callback,
    "serverwar_join": server_war_join_callback,
    "serverwar_leave": server_war_leave_callback,
    "menu_weeklymission": weekly_mission_menu_callback,
    "weeklymission_claim": weekly_mission_claim_callback,
    "menu_club": club_menu_callback,
    "menu_cosmetic": cosmetic_shop_callback,
    "cosmetic_equip_menu": cosmetic_equip_menu_callback,
    "menu_lottery": lottery_menu_callback,
    "lottery_draw": lottery_draw_callback,
    "menu_transfer": transfer_menu_callback,
    "menu_weeklyboss": weekly_boss_menu_callback,
    "weeklyboss_fight": weekly_boss_fight_callback,
}


async def social_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in SOCIAL_CALLBACKS:
        await SOCIAL_CALLBACKS[data](update, context)
        return True
    if data.startswith("cosmetic_buy:"):
        await cosmetic_buy_callback(update, context)
        return True
    if data.startswith("cosmetic_equip:"):
        await cosmetic_equip_callback(update, context)
        return True
    return False


async def social_text_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    awaiting = context.user_data.get("awaiting")
    if not awaiting:
        return False
    raw_text = update.message.text.strip()

    if awaiting == "transfer_target_id":
        context.user_data["awaiting"] = None
        await _do_transfer_target(update, context, raw_text)
        return True
    if awaiting == "transfer_amount":
        await _do_transfer_amount(update, context, raw_text)
        return True
    return False
