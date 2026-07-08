from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)
import json
import os

TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"
CHANNEL = "@Libercoin1"
ADMIN_ID = 6188951798
FILE = "users.json"

users = {}

if os.path.exists(FILE):
    with open(FILE, "r", encoding="utf-8") as f:
        users = json.load(f)

def save_users():
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def create_user(user):
    uid = str(user.id)

    if uid not in users:
        users[uid] = {
            "id": user.id,
            "name": user.first_name,
            "liber": 100,
            "liber_token": 0,
            "level": 1,
            "xp": 0
        }
        save_users()

    return users[uid]

menu = ReplyKeyboardMarkup(
    [
        ["🪙 بازار LIBER", "🏷 مزایده"],
        ["⚔️ رقابت", "💎 اشتراک"]
    ],
    resize_keyboard=True
)

async def check_member(bot, user_id):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in [
            "member",
            "administrator",
            "creator"
        ]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not await check_member(
        context.bot,
        update.effective_user.id
    ):
        await update.message.reply_text(
            f"اول عضو کانال شو:\n{CHANNEL}"
        )
        return

    data = create_user(update.effective_user)

    await update.message.reply_text(
f"""🔥 به Liber خوش آمدی

💰 موجودی:
{data['liber']} LIBER

🪙 توکن:
{data['liber_token']}

از دکمه‌های پایین استفاده کن.""",
        reply_markup=menu
    )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))

# ==========================
# VERSION 2 (ADDON)
# این قسمت را بعد از نسخه ۱
# و قبل از app.run_polling() قرار بده
# ==========================

import random
from datetime import datetime, timedelta

# -------- بازار LIBER --------

MARKET = {
    "price": 100,
    "last_update": datetime.now()
}

def update_market():
    if datetime.now() - MARKET["last_update"] >= timedelta(hours=1):

        MARKET["price"] += random.randint(-10, 15)

        if MARKET["price"] < 10:
            MARKET["price"] = 10

        MARKET["last_update"] = datetime.now()


async def liber_market(update: Update, context: ContextTypes.DEFAULT_TYPE):

    update_market()

    await update.message.reply_text(
f"""🪙 بازار LIBER

💰 قیمت فعلی:
{MARKET['price']}

📈 قیمت هر یک ساعت تغییر می‌کند.

🏷 برای شرکت در مزایده روی دکمه «🏷 مزایده» بزن.
"""
    )


# -------- مزایده --------

AUCTION = {
    "item": "🎁 جعبه طلایی",
    "price": 50
}

async def auction(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
f"""🏷 مزایده LIBER

🎁 آیتم:
{AUCTION['item']}

💰 قیمت شروع:
{AUCTION['price']} LIBER

برای شرکت:
دکمه «شرکت مزایده» را بزن.
"""
    )


async def join_auction(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = create_user(update.effective_user)

    if data["liber"] < AUCTION["price"]:

        await update.message.reply_text(
            "❌ موجودی LIBER کافی نیست."
        )
        return

    data["liber"] -= AUCTION["price"]
    save_users()

    AUCTION["price"] += 10

    await update.message.reply_text(
f"""✅ در مزایده شرکت کردی.

💰 قیمت جدید:
{AUCTION['price']} LIBER
"""
    )


# -------- Handler ها --------

app.add_handler(
    MessageHandler(
        filters.Regex("^🪙 بازار LIBER$"),
        liber_market
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^🏷 مزایده$"),
        auction
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^شرکت مزایده$"),
        join_auction
    )
)# ==========================
# VERSION 3 (ADDON)
# بعد از نسخه ۲ و قبل از app.run_polling()
# ==========================

# ---------- جایزه روزانه ----------

from datetime import datetime

async def daily_reward(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = create_user(update.effective_user)

    today = datetime.now().strftime("%Y-%m-%d")

    if data.get("daily_reward") == today:
        await update.message.reply_text(
            "🎁 جایزه امروزت را قبلاً دریافت کرده‌ای."
        )
        return

    reward = 20

    data["daily_reward"] = today
    data["liber"] += reward

    save_users()

    await update.message.reply_text(
f"""🎉 جایزه روزانه دریافت شد

💰 +{reward} LIBER
"""
    )


# ---------- مأموریت روزانه ----------

async def daily_mission(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
"""📋 مأموریت امروز

✅ ورود به ربات
🎁 جایزه: 10 LIBER

✅ شرکت در مزایده
🎁 جایزه: 20 LIBER

✅ دعوت یک زیرمجموعه
🎁 جایزه: 50 LIBER
"""
    )


# ---------- هندلرها ----------

app.add_handler(
    MessageHandler(
        filters.Regex("^🎁 جایزه روزانه$"),
        daily_reward
    )
)

app.add_handler(
    MessageHandler(
        filters.Regex("^📋 مأموریت روزانه$"),
        daily_mission
    )
)# ==========================
# VERSION 4 (ADDON)
# REFERRAL SYSTEM
# بعد از نسخه ۳ و قبل از app.run_polling()
# ==========================

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = create_user(update.effective_user)

    bot = await context.bot.get_me()

    invite_link = (
        f"https://t.me/{bot.username}"
        f"?start={user['id']}"
    )

    text = f"""
👥 سیستم زیرمجموعه LIBER

دوستانت را دعوت کن و جایزه بگیر!

🎁 پاداش هر دعوت موفق:
50 LIBER

💎 اگر زیرمجموعه‌هایت فعال باشند،
هر روز پاداش بیشتری دریافت می‌کنی.

━━━━━━━━━━━━━━

🔗 لینک دعوت اختصاصی تو:

{invite_link}

━━━━━━━━━━━━━━

🚀 چرا همه وارد LIBER می‌شوند؟

🎮 بازی‌های جذاب
🏆 رقابت آنلاین
🪙 کسب LIBER
🎁 جوایز روزانه
💎 اشتراک ویژه
👥 درآمد از دعوت دوستان

🔥 همین حالا لینکت را برای دوستانت بفرست.
"""

    await update.message.reply_text(text)


# ------------------
# HANDLER
# ------------------

app.add_handler(
    MessageHandler(
        filters.Regex("^👥 زیرمجموعه$"),
        referral
    )
)


app.run_polling()
