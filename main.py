from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

import json
import os


TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

CHANNEL = "@Libercoin1"

ADMIN_ID = 6188951798

FILE = "users.json"



# --------------------
# DATABASE
# --------------------

users = {}


def load_users():

    global users

    if os.path.exists(FILE):

        with open(FILE, "r", encoding="utf-8") as f:
            users = json.load(f)



def save_users():

    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(
            users,
            f,
            ensure_ascii=False,
            indent=4
        )


load_users()



# --------------------
# USER
# --------------------

def create_user(user):

    uid = str(user.id)

    if uid not in users:

        users[uid] = {

            "id": user.id,

            "name": user.first_name,

            "liber": 100,

            "level": 1,

            "xp": 0,

            "vip": "Normal"

        }

        save_users()


    return users[uid]



# --------------------
# MENU
# --------------------

menu = ReplyKeyboardMarkup(

    [
        ["👤 پروفایل", "💰 موجودی"],

        ["🪙 بازار LIBER", "🏷 مزایده"],

        ["⚔️ رقابت", "💎 اشتراک"]

    ],

    resize_keyboard=True

)



# --------------------
# CHANNEL CHECK
# --------------------

async def check_member(user_id, bot):

    try:

        member = await bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in [

            "member",
            "administrator",
            "creator"

        ]

    except:

        return False



# --------------------
# START
# --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    if not await check_member(
        user.id,
        context.bot
    ):

        await update.message.reply_text(

            "📢 اول عضو کانال شو:\n"
            + CHANNEL

        )

        return



    create_user(user)


    await update.message.reply_text(

        "🔥 خوش آمدی به Liber Universe\n\n"
        "💰 جایزه شروع: 100 LIBER",

        reply_markup=menu

    )



# --------------------
# PROFILE
# --------------------

async def profile(update, context):

    data = create_user(
        update.effective_user
    )


    await update.message.reply_text(

f"""
👤 پروفایل

نام:
{data['name']}

💰 LIBER:
{data['liber']}

⭐ Level:
{data['level']}

✨ XP:
{data['xp']}

💎 VIP:
{data['vip']}
"""

    )



# --------------------
# BALANCE
# --------------------

async def balance(update, context):

    data = create_user(
        update.effective_user
    )


    await update.message.reply_text(

        f"💰 موجودی شما: {data['liber']} LIBER"

    )



# --------------------
# ADMIN TEST
# --------------------

async def admin(update, context):

    if update.effective_user.id == ADMIN_ID:

        await update.message.reply_text(
            "👑 ادمین فعال است"
        )

    else:

        await update.message.reply_text(
            "⛔ دسترسی ندارید"
        )



# --------------------
# BOT
# --------------------

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👤 پروفایل$"),
        profile
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^💰 موجودی$"),
        balance
    )
)


app.add_handler(
    CommandHandler(
        "admin",
        admin
    )
)


print("LIBER V1 STARTED")

# =====================
# VERSION 2 ADDON
# MARKET + AUCTION
# =====================

import random
from datetime import datetime, timedelta



# =====================
# MARKET
# =====================

LIBER_MARKET = {

    "price": 100,

    "last_change": datetime.now()

}



def update_market():

    now = datetime.now()


    if now - LIBER_MARKET["last_change"] >= timedelta(hours=1):

        change = random.randint(-15, 20)

        LIBER_MARKET["price"] += change


        if LIBER_MARKET["price"] < 10:

            LIBER_MARKET["price"] = 10


        LIBER_MARKET["last_change"] = now




async def liber_market(update, context):

    update_market()


    await update.message.reply_text(

f"""
🪙 بازار LIBER

💰 قیمت فعلی:

1 LIBER = {LIBER_MARKET['price']}


📈 نوسان:
هر ۱ ساعت تغییر می‌کند

🛒 برای خرید:
دکمه خرید LIBER
"""

    )





async def buy_liber(update, context):

    data = create_user(
        update.effective_user
    )


    amount = 1


    data["liber"] += amount


    save_users()


    await update.message.reply_text(

f"""
✅ خرید موفق

🪙 دریافت:
{amount} LIBER

💰 قیمت:
{LIBER_MARKET['price']}
"""

    )




# =====================
# AUCTION
# =====================


AUCTION = {

    "item": "🎁 جعبه طلایی",

    "price": 50,

    "owner": None

}





async def auction_menu(update, context):


    await update.message.reply_text(

f"""
🏷 مزایده LIBER


آیتم:
{AUCTION['item']}


💰 قیمت فعلی:
{AUCTION['price']} LIBER


برای شرکت:
نوشتن:

شرکت مزایده
"""

    )





async def join_auction(update, context):

    data = create_user(
        update.effective_user
    )


    cost = AUCTION["price"]



    if data["liber"] < cost:


        await update.message.reply_text(

            "❌ LIBER کافی نیست"

        )

        return



    data["liber"] -= cost


    AUCTION["owner"] = data["name"]


    AUCTION["price"] += 10


    save_users()



    await update.message.reply_text(

"""
✅ پیشنهاد شما ثبت شد

🏷 مزایده ادامه دارد

قیمت جدید افزایش یافت
"""

    )





# =====================
# HANDLERS
# =====================


app.add_handler(

    MessageHandler(

        filters.Regex("^🪙 بازار LIBER$"),

        liber_market

    )

)



app.add_handler(

    MessageHandler(

        filters.Regex("^🛒 خرید LIBER$"),

        buy_liber

    )

)



app.add_handler(

    MessageHandler(

        filters.Regex("^🏷 مزایده$"),

        auction_menu

    )

)



app.add_handler(

    MessageHandler(

        filters.Regex("^شرکت مزایده$"),

        join_auction

    )

)


app.run_polling()
