# -*- coding: utf-8 -*-
"""
handlers_clanwar.py — جنگ کلن مستقل با سیستم کاپ و تورنمنت (فایل جدا)
================================================================
این سیستم کاملاً از «رقابت آنلاین» فردی جداست.

اقتصاد:
    🤝 ساخت کلن: ۳۰۰ LIBER (در handlers_extra.py اعمال شده)
    ⚔️ ورود به جنگ کلن: ۵۰ LIBER برای هر عضوی که شرکت می‌کند
    🏆 برد: هر عضو شرکت‌کننده +۷۰ LIBER می‌گیرد
    🏅 کاپ کلن: هر برد +۲۰ کاپ به کلن اضافه می‌شود
    📈 ارتقا: کاپ‌رنک ۱→۲ با ۴ برد (۸۰ کاپ)، بعدش هر رنک بیشتر از قبلی لازم دارد
    📆 تورنمنت ماهانه: ۳ کلن برتر بر اساس کاپ فصلی، جایزه بین همه‌ی اعضای کلن پخش می‌شود
        (۶۰٪ مساوی + ۴۰٪ متناسب با مشارکت در بردها)
"""
import time
import random
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError

from main import get_conn, get_user, update_balance, log_transaction, back_keyboard

logger = logging.getLogger("LIBER.clanwar")

CLAN_WAR_ENTRY_FEE = 50
CLAN_WAR_WIN_REWARD_PER_MEMBER = 70
CLAN_WAR_CUPS_PER_WIN = 20
CLAN_WAR_CHECK_SECONDS = 180
CLAN_WAR_BOT_FALLBACK_SECONDS = 300

CLAN_CUP_RANKS = [
    "🥉 کلن نوپا", "🥈 کلن نقره‌ای", "🥇 کلن طلایی", "💠 کلن پلاتینیومی",
    "💎 کلن الماسی", "🐉 کلن اژدهایی", "👑 کلن افسانه‌ای",
]
MAX_CLAN_RANK_INDEX = len(CLAN_CUP_RANKS) - 1

CLAN_TOURNAMENT_INTERVAL_SECONDS = 30 * 86400
CLAN_TOURNAMENT_REWARDS = {1: 1500, 2: 1000, 3: 800}


def wins_required_for_clan_rank(rank_index: int) -> int:
    return 4 + rank_index * 3


def cups_threshold_for_clan_rank(rank_index: int) -> float:
    return wins_required_for_clan_rank(rank_index) * CLAN_WAR_CUPS_PER_WIN


_tables_ready = False


def _ensure_tables():
    global _tables_ready
    if _tables_ready:
        return
    with get_conn() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_profile (
            alliance_id INTEGER PRIMARY KEY,
            rank_index INTEGER NOT NULL DEFAULT 0,
            cups REAL NOT NULL DEFAULT 0,
            season_cups REAL NOT NULL DEFAULT 0,
            wins INTEGER NOT NULL DEFAULT 0,
            losses INTEGER NOT NULL DEFAULT 0
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_war_participants (
            alliance_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at INTEGER NOT NULL,
            PRIMARY KEY (alliance_id, user_id)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_war_pool_created (
            alliance_id INTEGER PRIMARY KEY,
            first_joined_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_season (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            season_number INTEGER NOT NULL DEFAULT 1,
            started_at INTEGER NOT NULL
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS clan_member_contribution (
            alliance_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            wins_count INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (alliance_id, user_id)
        )
        """)
        row = conn.execute("SELECT 1 FROM clan_season WHERE id = 1").fetchone()
        if not row:
            conn.execute(
                "INSERT INTO clan_season (id, season_number, started_at) VALUES (1, 1, ?)", (int(time.time()),)
            )
    _tables_ready = True


def _get_clan_profile(alliance_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM clan_profile WHERE alliance_id = ?", (alliance_id,)).fetchone()
        if row:
            return row
        conn.execute("INSERT INTO clan_profile (alliance_id) VALUES (?)", (alliance_id,))
        return conn.execute("SELECT * FROM clan_profile WHERE alliance_id = ?", (alliance_id,)).fetchone()


def _get_membership(user_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliance_members WHERE user_id = ?", (user_id,)).fetchone()


def _get_alliance(alliance_id):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM alliances WHERE alliance_id = ?", (alliance_id,)).fetchone()


def _clan_war_keyboard(in_pool):
    rows = []
    if in_pool:
        rows.append([InlineKeyboardButton("🚪 انصراف از این جنگ", callback_data="clanwar_leave")])
    else:
        rows.append([InlineKeyboardButton(
            f"⚔️ ورود به جنگ کلن ({CLAN_WAR_ENTRY_FEE} LIBER)", callback_data="clanwar_join"
        )])
    rows.append([InlineKeyboardButton("🏆 برترین کلن‌ها", callback_data="clanwar_top")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def clanwar_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id

    membership = _get_membership(user_id)
    if not membership:
        await q.edit_message_text(
            "⚔️ جنگ کلن\n\nابتدا باید عضو یک کلن باشی (از منوی 🤝 اتحاد).", reply_markup=back_keyboard()
        )
        return

    alliance_id = membership["alliance_id"]
    alliance = _get_alliance(alliance_id)
    profile = _get_clan_profile(alliance_id)

    with get_conn() as conn:
        in_pool = conn.execute(
            "SELECT 1 FROM clan_war_participants WHERE alliance_id = ? AND user_id = ?", (alliance_id, user_id)
        ).fetchone()
        pool_count = conn.execute(
            "SELECT COUNT(*) c FROM clan_war_participants WHERE alliance_id = ?", (alliance_id,)
        ).fetchone()["c"]

    needed_wins = wins_required_for_clan_rank(profile["rank_index"])
    threshold = cups_threshold_for_clan_rank(profile["rank_index"])

    text = (
        f"⚔️ جنگ کلن — {alliance['name']}\n\n"
        f"رتبه: {CLAN_CUP_RANKS[profile['rank_index']]}\n"
        f"کاپ فعلی: {profile['cups']:.0f} / {threshold:.0f} (تا رتبه‌ی بعد)\n"
        f"🏆 برد کلن: {profile['wins']}  😔 باخت: {profile['losses']}\n"
        f"👥 نفرات آماده‌ی جنگ بعدی از کلن شما: {pool_count}\n\n"
        f"هزینه‌ی ورود: {CLAN_WAR_ENTRY_FEE} LIBER — اگه کلن برد، +{CLAN_WAR_WIN_REWARD_PER_MEMBER} LIBER به هر شرکت‌کننده می‌رسه."
    )
    await q.edit_message_text(text, reply_markup=_clan_war_keyboard(bool(in_pool)))


async def clanwar_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    user_id = q.from_user.id
    membership = _get_membership(user_id)
    if not membership:
        await q.answer("ابتدا باید عضو یک کلن باشی.", show_alert=True)
        return

    alliance_id = membership["alliance_id"]
    with get_conn() as conn:
        already = conn.execute(
            "SELECT 1 FROM clan_war_participants WHERE alliance_id = ? AND user_id = ?", (alliance_id, user_id)
        ).fetchone()
    if already:
        await q.answer("همین الان هم تو صف این جنگ هستی.", show_alert=True)
        return

    user = get_user(user_id)
    if user["liber"] < CLAN_WAR_ENTRY_FEE:
        await q.answer(f"❌ برای ورود به {CLAN_WAR_ENTRY_FEE} LIBER نیاز داری.", show_alert=True)
        return

    await q.answer()
    update_balance(user_id, liber=-CLAN_WAR_ENTRY_FEE)
    now = int(time.time())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO clan_war_participants (alliance_id, user_id, joined_at) VALUES (?, ?, ?)",
            (alliance_id, user_id, now),
        )
        exists = conn.execute(
            "SELECT 1 FROM clan_war_pool_created WHERE alliance_id = ?", (alliance_id,)
        ).fetchone()
        if not exists:
            conn.execute(
                "INSERT INTO clan_war_pool_created (alliance_id, first_joined_at) VALUES (?, ?)", (alliance_id, now)
            )

    await q.edit_message_text(
        "⚔️ وارد جنگ کلن شدی! منتظر بقیه‌ی اعضا یا حریف باش.", reply_markup=_clan_war_keyboard(True)
    )


async def clanwar_leave_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    membership = _get_membership(user_id)
    if not membership:
        return
    alliance_id = membership["alliance_id"]
    with get_conn() as conn:
        conn.execute(
            "DELETE FROM clan_war_participants WHERE alliance_id = ? AND user_id = ?", (alliance_id, user_id)
        )
    update_balance(user_id, liber=CLAN_WAR_ENTRY_FEE)
    await q.edit_message_text("🚪 از جنگ کلن انصراف دادی و ورودی برگشت.", reply_markup=_clan_war_keyboard(False))


async def clanwar_top_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    q = update.callback_query
    await q.answer()
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT alliance_id, rank_index, season_cups FROM clan_profile ORDER BY season_cups DESC LIMIT 10"
        ).fetchall()

    lines = ["🏆 برترین کلن‌های فصل\n"]
    if not rows:
        lines.append("هنوز هیچ کلنی جنگ نکرده.")
    for i, r in enumerate(rows, start=1):
        alliance = _get_alliance(r["alliance_id"])
        name = alliance["name"] if alliance else str(r["alliance_id"])
        lines.append(f"{i}. {name} — {CLAN_CUP_RANKS[r['rank_index']]} ({r['season_cups']:.0f} کاپ)")

    await q.edit_message_text("\n".join(lines), reply_markup=back_keyboard())


async def _resolve_clan_war(bot, alliance_a, participants_a, alliance_b, participants_b):
    profile_a = _get_clan_profile(alliance_a)
    power_a = len(participants_a) * 30 + profile_a["rank_index"] * 15 + random.randint(-20, 20)

    if alliance_b is None:
        power_b = max(20, power_a + random.randint(-25, 25))
        clan_b_name = "کلن رقیب (شبیه‌سازی‌شده)"
    else:
        profile_b = _get_clan_profile(alliance_b)
        power_b = len(participants_b) * 30 + profile_b["rank_index"] * 15 + random.randint(-20, 20)
        alliance_b_row = _get_alliance(alliance_b)
        clan_b_name = alliance_b_row["name"] if alliance_b_row else "کلن رقیب"

    a_wins = power_a >= power_b
    alliance_a_row = _get_alliance(alliance_a)
    clan_a_name = alliance_a_row["name"] if alliance_a_row else "کلن شما"

    await _apply_clan_result(bot, alliance_a, participants_a, won=a_wins, opponent_name=clan_b_name)
    if alliance_b is not None:
        await _apply_clan_result(bot, alliance_b, participants_b, won=not a_wins, opponent_name=clan_a_name)


async def _apply_clan_result(bot, alliance_id, participants, won, opponent_name):
    profile = _get_clan_profile(alliance_id)
    alliance = _get_alliance(alliance_id)
    clan_name = alliance["name"] if alliance else str(alliance_id)

    if won:
        with get_conn() as conn:
            conn.execute(
                "UPDATE clan_profile SET wins = wins + 1, cups = cups + ?, season_cups = season_cups + ? WHERE alliance_id = ?",
                (CLAN_WAR_CUPS_PER_WIN, CLAN_WAR_CUPS_PER_WIN, alliance_id),
            )
        for uid in participants:
            update_balance(uid, liber=CLAN_WAR_WIN_REWARD_PER_MEMBER)
            log_transaction(uid, "CLAN_WAR_WIN", f"clan={alliance_id}")
            with get_conn() as conn:
                conn.execute(
                    """INSERT INTO clan_member_contribution (alliance_id, user_id, wins_count) VALUES (?, ?, 1)
                       ON CONFLICT(alliance_id, user_id) DO UPDATE SET wins_count = wins_count + 1""",
                    (alliance_id, uid),
                )

        profile = _get_clan_profile(alliance_id)
        promote_text = ""
        if profile["rank_index"] < MAX_CLAN_RANK_INDEX:
            threshold = cups_threshold_for_clan_rank(profile["rank_index"])
            if profile["cups"] >= threshold:
                new_rank = profile["rank_index"] + 1
                with get_conn() as conn:
                    conn.execute(
                        "UPDATE clan_profile SET rank_index = ?, cups = 0 WHERE alliance_id = ?",
                        (new_rank, alliance_id),
                    )
                promote_text = f"\n\n🎉 کلن ارتقا یافت! رتبه‌ی جدید: {CLAN_CUP_RANKS[new_rank]}"

        for uid in participants:
            try:
                await bot.send_message(
                    uid,
                    f"⚔️ جنگ کلن «{clan_name}» در برابر {opponent_name}\n\n"
                    f"🏆 بردید! +{CLAN_WAR_WIN_REWARD_PER_MEMBER} LIBER برای شما، +{CLAN_WAR_CUPS_PER_WIN} کاپ برای کلن.{promote_text}",
                )
            except TelegramError:
                pass
    else:
        with get_conn() as conn:
            conn.execute("UPDATE clan_profile SET losses = losses + 1 WHERE alliance_id = ?", (alliance_id,))
        for uid in participants:
            log_transaction(uid, "CLAN_WAR_LOSS", f"clan={alliance_id}")
            try:
                await bot.send_message(
                    uid,
                    f"⚔️ جنگ کلن «{clan_name}» در برابر {opponent_name}\n\n"
                    f"😔 این‌بار باختید. فقط ورودی از دست رفت، کاپ کم نشد.",
                )
            except TelegramError:
                pass


async def clan_war_matching_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    now = int(time.time())

    with get_conn() as conn:
        pools = conn.execute(
            "SELECT DISTINCT alliance_id FROM clan_war_participants"
        ).fetchall()

    clan_ids = [p["alliance_id"] for p in pools]
    by_rank = {}
    for cid in clan_ids:
        rank_index = _get_clan_profile(cid)["rank_index"]
        by_rank.setdefault(rank_index, []).append(cid)

    matched = set()
    for rank_index, cids in by_rank.items():
        while len(cids) >= 2:
            clan_a = cids.pop(0)
            clan_b = cids.pop(0)
            with get_conn() as conn:
                participants_a = [r["user_id"] for r in conn.execute(
                    "SELECT user_id FROM clan_war_participants WHERE alliance_id = ?", (clan_a,)
                ).fetchall()]
                participants_b = [r["user_id"] for r in conn.execute(
                    "SELECT user_id FROM clan_war_participants WHERE alliance_id = ?", (clan_b,)
                ).fetchall()]
                conn.execute("DELETE FROM clan_war_participants WHERE alliance_id IN (?, ?)", (clan_a, clan_b))
                conn.execute("DELETE FROM clan_war_pool_created WHERE alliance_id IN (?, ?)", (clan_a, clan_b))
            matched.add(clan_a)
            matched.add(clan_b)
            await _resolve_clan_war(context.bot, clan_a, participants_a, clan_b, participants_b)

    with get_conn() as conn:
        pool_starts = conn.execute("SELECT * FROM clan_war_pool_created").fetchall()
    for row in pool_starts:
        cid = row["alliance_id"]
        if cid in matched:
            continue
        if now - row["first_joined_at"] >= CLAN_WAR_BOT_FALLBACK_SECONDS:
            with get_conn() as conn:
                participants = [r["user_id"] for r in conn.execute(
                    "SELECT user_id FROM clan_war_participants WHERE alliance_id = ?", (cid,)
                ).fetchall()]
                conn.execute("DELETE FROM clan_war_participants WHERE alliance_id = ?", (cid,))
                conn.execute("DELETE FROM clan_war_pool_created WHERE alliance_id = ?", (cid,))
            if participants:
                await _resolve_clan_war(context.bot, cid, participants, None, None)


async def clan_tournament_job(context: ContextTypes.DEFAULT_TYPE):
    _ensure_tables()
    with get_conn() as conn:
        season = conn.execute("SELECT * FROM clan_season WHERE id = 1").fetchone()
    now = int(time.time())
    if now - season["started_at"] < CLAN_TOURNAMENT_INTERVAL_SECONDS:
        return

    with get_conn() as conn:
        top3 = conn.execute(
            "SELECT alliance_id, season_cups FROM clan_profile ORDER BY season_cups DESC LIMIT 3"
        ).fetchall()

    for i, row in enumerate(top3, start=1):
        if row["season_cups"] <= 0:
            continue
        alliance_id = row["alliance_id"]
        alliance = _get_alliance(alliance_id)
        if not alliance:
            continue
        total_reward = CLAN_TOURNAMENT_REWARDS.get(i, 0)
        if not total_reward:
            continue

        with get_conn() as conn:
            members = [r["user_id"] for r in conn.execute(
                "SELECT user_id FROM alliance_members WHERE alliance_id = ?", (alliance_id,)
            ).fetchall()]
        if not members:
            continue

        with get_conn() as conn:
            contributions = {
                r["user_id"]: r["wins_count"] for r in conn.execute(
                    "SELECT user_id, wins_count FROM clan_member_contribution WHERE alliance_id = ?", (alliance_id,)
                ).fetchall()
            }
        total_contribution = sum(contributions.get(uid, 0) for uid in members)

        equal_pool = total_reward * 0.6
        weighted_pool = total_reward * 0.4
        equal_share = equal_pool / len(members)

        payouts = {}
        for uid in members:
            share = equal_share
            if total_contribution > 0:
                share += weighted_pool * (contributions.get(uid, 0) / total_contribution)
            payouts[uid] = round(share, 2)

        diff = round(total_reward - sum(payouts.values()), 2)
        if diff and payouts:
            top_contributor = max(members, key=lambda uid: contributions.get(uid, 0))
            payouts[top_contributor] = round(payouts[top_contributor] + diff, 2)

        for uid, amount in payouts.items():
            if amount <= 0:
                continue
            update_balance(uid, liber=amount)
            log_transaction(uid, "CLAN_TOURNAMENT_REWARD", f"rank={i} clan={alliance_id} share={amount}")
            try:
                await context.bot.send_message(
                    uid,
                    f"🏆 تبریک! کلن «{alliance['name']}» در تورنمنت ماهانه رتبه‌ی {i} شد!\n"
                    f"سهم شما از {total_reward} LIBER کلن: {amount} LIBER 🎉",
                )
            except TelegramError:
                pass

        with get_conn() as conn:
            conn.execute("DELETE FROM clan_member_contribution WHERE alliance_id = ?", (alliance_id,))

    new_season = season["season_number"] + 1
    with get_conn() as conn:
        conn.execute("UPDATE clan_profile SET season_cups = 0")
        conn.execute(
            "UPDATE clan_season SET season_number = ?, started_at = ? WHERE id = 1", (new_season, now)
        )
    logger.info(f"تورنمنت ماهانه‌ی کلن‌ها برگزار شد. فصل جدید: {new_season}")


CLANWAR_CALLBACKS = {
    "menu_clanwar2": clanwar_menu_callback,
    "clanwar_join": clanwar_join_callback,
    "clanwar_leave": clanwar_leave_callback,
    "clanwar_top": clanwar_top_callback,
}


async def clanwar_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    data = update.callback_query.data
    if data in CLANWAR_CALLBACKS:
        await CLANWAR_CALLBACKS[data](update, context)
        return True
    return False
