from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
import json
import os
from datetime import datetime


# =====================
# SETTINGS
# =====================

TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

CHANNEL = "@Libercoin1"

ADMIN_ID = 6188951798

DATA_FILE = "users.json"



# =====================
# DATABASE
# =====================

users = {}


def load_data():
    global users

    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            users = json.load(file)


def save_data():

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(users, file, ensure_ascii=False, indent=4)


load_data()



# =====================
# USER
# =====================

def get_user(user):

    uid = str(user.id)

    if uid not in users:

        users[uid] = {

            "id": user.id,
            "name": user.first_name,

            "liber": 100,

            "level": 1,

            "xp": 0,

            "vip": "Normal",

            "created": str(datetime.now())

        }

        save_data()


    return users[uid]



# =====================
# MENU
# =====================

MAIN_MENU = ReplyKeyboardMarkup(

    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 بازار LIBER", "🏷 مزایده"],
        ["⚔️ رقابت", "💎 اشتراک"]
    ],

    resize_keyboard=True
)



# =====================
# CHANNEL CHECK
# =====================

async def check_channel(user_id, bot):

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



# =====================
# START
# =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    if not await check_channel(user.id, context.bot):

        await update.message.reply_text(
            f"📢 ابتدا عضو کانال شوید:\n{CHANNEL}"
        )

        return


    get_user(user)


    await update.message.reply_text(
        "🔥 خوش آمدی به Liber Universe\n\n💰 موجودی اولیه: 100 LIBER",
        reply_markup=MAIN_MENU
    )



# =====================
# PROFILE
# =====================

async def profile(update, context):

    data = get_user(
        update.effective_user
    )


    await update.message.reply_text(

f"""
👤 پروفایل

نام:
{data['name']}

💰 موجودی:
{data['liber']} LIBER

⭐ Level:
{data['level']}

✨ XP:
{data['xp']}

💎 VIP:
{data['vip']}
"""
    )



# =====================
# BALANCE
# =====================

async def balance(update, context):

    data = get_user(
        update.effective_user
    )


    await update.message.reply_text(
        f"💰 موجودی شما: {data['liber']} LIBER"
    )



# =====================
# ADMIN TEST
# =====================

async def admin(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ دسترسی ندارید"
        )

        return


    await update.message.reply_text(
        "👑 پنل ادمین فعال است"
    )



# =====================
# BOT
# =====================

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



print("LIBER BOT V1 RUNNING")


# =====================
# VERSION 2 ADDONS
# REFERRAL + MISSION
# =====================


from datetime import date



# ---------------------
# Referral
# ---------------------

async def referral(update, context):

    data = get_user(
        update.effective_user
    )


    if "ref" not in data:

        data["ref"] = 0
        save_data()


    await update.message.reply_text(
f"""
👥 زیرمجموعه Liber

تعداد دعوت:
{data['ref']}

لینک دعوت:

https://t.me/{context.bot.username}?start={update.effective_user.id}
"""
    )



# ---------------------
# Daily Reward
# ---------------------

async def daily(update, context):

    data = get_user(
        update.effective_user
    )


    today = str(date.today())


    if data.get("daily") == today:

        await update.message.reply_text(
            "❌ جایزه امروز را گرفتی"
        )

        return



    data["daily"] = today

    data["liber"] += 10

    data["xp"] += 5


    save_data()


    await update.message.reply_text(
"""
🎁 جایزه روزانه دریافت شد

+10 LIBER
+5 XP
"""
    )



# ---------------------
# Missions
# ---------------------

async def missions(update, context):

    await update.message.reply_text(
"""
🎯 ماموریت‌ها

⚔️ یک رقابت انجام بده
جایزه: 20 LIBER


👥 یک نفر دعوت کن
جایزه: 30 LIBER


⭐ XP جمع کن
جایزه ویژه
"""
    )



# ---------------------
# Add Handlers
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^👥 زیرمجموعه$"),
        referral
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🎁 جایزه روزانه$"),
        daily
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🎯 ماموریت$"),
        missions
    )
)
# =====================
# VERSION 3 ADDONS
# MARKET + AUCTION
# =====================

import random


# قیمت بازار
LIBER_PRICE = {
    "price": 100
}


# ---------------------
# بازار LIBER
# ---------------------

async def liber_market(update, context):

    change = random.randint(-5, 5)

    LIBER_PRICE["price"] += change


    if LIBER_PRICE["price"] < 10:

        LIBER_PRICE["price"] = 10


    await update.message.reply_text(
f"""
🪙 بازار LIBER

قیمت فعلی:

1 LIBER = {LIBER_PRICE['price']}

📈 تغییر:
{change}

قیمت‌ها دوره‌ای تغییر می‌کنند.
"""
    )



# ---------------------
# خرید LIBER
# ---------------------

async def buy_liber(update, context):

    data = get_user(
        update.effective_user
    )


    amount = 5

    cost = (
        LIBER_PRICE["price"]
        *
        amount
    )


    data["liber"] += amount


    save_data()


    await update.message.reply_text(
f"""
🪙 خرید انجام شد

تعداد:
{amount} LIBER

هزینه فرضی:
{cost}
"""
    )



# ---------------------
# مزایده
# ---------------------

async def auction(update, context):

    await update.message.reply_text(
"""
🏷 مزایده Liber

آیتم ویژه:

🔥 جعبه طلایی Liber

قیمت شروع:
50 LIBER

برای شرکت در مزایده:
به زودی فعال می‌شود.
"""
    )



# ---------------------
# HANDLERS
# ---------------------


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
        filters.Regex("^خرید LIBER$"),
        buy_liber
    )
)
# =====================
# VERSION 4 ADDONS
# VIP + LEAGUE SYSTEM
# =====================


# ---------------------
# ساخت اطلاعات VIP
# ---------------------

def init_vip(data):

    if "vip" not in data:
        data["vip"] = "Normal"

    if "league" not in data:
        data["league"] = "Bronze"

    save_data()



# ---------------------
# نمایش VIP
# ---------------------

async def vip_menu(update, context):

    data = get_user(
        update.effective_user
    )

    init_vip(data)


    await update.message.reply_text(
f"""
💎 اشتراک Liber

سطح فعلی:
{data['vip']}

🏆 لیگ:
{data['league']}


گزینه‌ها:

🥉 Premium
🥈 Premium Plus
👑 Liber Pro
"""
    )



# ---------------------
# فعال‌سازی VIP
# ---------------------

async def activate_vip(update, context):

    data = get_user(
        update.effective_user
    )

    init_vip(data)


    plan = update.message.text


    prices = {

        "🥉 Premium": 50,

        "🥈 Premium Plus": 150,

        "👑 Liber Pro": 300

    }


    if plan not in prices:

        return



    if data["liber"] < prices[plan]:

        await update.message.reply_text(
            "❌ LIBER کافی نیست"
        )

        return



    data["liber"] -= prices[plan]

    data["vip"] = plan


    save_data()


    await update.message.reply_text(
f"""
🎉 اشتراک فعال شد

💎 سطح:
{plan}
"""
    )



# ---------------------
# لیگ
# ---------------------

async def league(update, context):

    data = get_user(
        update.effective_user
    )


    level = data.get(
        "level",
        1
    )


    if level >= 50:

        rank = "👑 Liber Legend"

    elif level >= 20:

        rank = "💎 Diamond"

    elif level >= 10:

        rank = "🥇 Gold"

    else:

        rank = "🥉 Bronze"



    data["league"] = rank

    save_data()



    await update.message.reply_text(
f"""
🏆 لیگ شما

{rank}

⭐ Level:
{level}
"""
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^💎 اشتراک$"),
        vip_menu
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex(
            "^(🥉 Premium|🥈 Premium Plus|👑 Liber Pro)$"
        ),
        activate_vip
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🏆 لیگ$"),
        league
    )
)# =====================
# VERSION 5 ADDONS
# FOOTBALL + PLAYER UPGRADES
# =====================

import random


# ---------------------
# ساخت اطلاعات بازیکن
# ---------------------

def init_player(data):

    if "player" not in data:

        data["player"] = {

            "shot": 1,
            "speed": 1,
            "power": 1

        }

        save_data()



# ---------------------
# نمایش بازیکن
# ---------------------

async def player_info(update, context):

    data = get_user(
        update.effective_user
    )

    init_player(data)

    p = data["player"]


    await update.message.reply_text(
f"""
⚽ بازیکن Liber

🎯 شوت:
{p['shot']}

⚡ سرعت:
{p['speed']}

💪 قدرت:
{p['power']}

💰 LIBER:
{data['liber']}
"""
    )



# ---------------------
# ارتقای بازیکن
# ---------------------

async def upgrade_player(update, context):

    data = get_user(
        update.effective_user
    )

    init_player(data)


    cost = 20


    if data["liber"] < cost:

        await update.message.reply_text(
            "❌ LIBER کافی نیست"
        )

        return



    data["liber"] -= cost

    data["player"]["shot"] += 1


    save_data()


    await update.message.reply_text(
"""
🔥 ارتقا انجام شد

🎯 شوت +1

هزینه:
20 LIBER
"""
    )



# ---------------------
# بازی فوتبال
# ---------------------

async def football_game(update, context):

    data = get_user(
        update.effective_user
    )

    init_player(data)


    p = data["player"]


    my_power = (

        p["shot"]

        +

        p["speed"]

        +

        p["power"]

    )


    enemy = random.randint(
        3,
        20
    )



    if my_power >= enemy:


        data["liber"] += 15

        data["xp"] += 10

        data["wins"] = data.get(
            "wins",
            0
        ) + 1


        result = """
⚽ بردی!

🎁 جایزه:

+15 LIBER
+10 XP
"""

    else:


        data["xp"] += 3


        result = """
⚽ باختی!

✨ +3 XP
"""



    save_data()


    await update.message.reply_text(
        result
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^⚽ بازیکن$"),
        player_info
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^⬆️ ارتقا$"),
        upgrade_player
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^⚽ فوتبال$"),
        football_game
    )
)# =====================
# VERSION 6 ADDONS
# TOURNAMENT + RANKING
# =====================


# ---------------------
# ساخت امتیاز
# ---------------------

def get_score(data):

    score = (

        data.get("wins", 0) * 10

        +

        data.get("xp", 0)

    )

    return score



# ---------------------
# تورنمنت
# ---------------------

async def tournament(update, context):

    await update.message.reply_text(
"""
🏆 تورنمنت Liber

🔥 مسابقات ویژه

🥇 نفر اول:
600 LIBER

🥈 نفر دوم:
400 LIBER

🥉 نفر سوم:
250 LIBER


برای شرکت:
⚽ بازی کن
⭐ امتیاز جمع کن
"""
    )



# ---------------------
# رتبه بندی
# ---------------------

async def ranking(update, context):


    players = sorted(

        users.items(),

        key=lambda item:
        get_score(item[1]),

        reverse=True

    )


    text = "🏆 رتبه‌بندی Liber\n\n"


    place = 1


    for uid, data in players[:10]:


        text += f"""
{place} 👤 {data.get('name','کاربر')}

⭐ امتیاز:
{get_score(data)}

💰 LIBER:
{data.get('liber',0)}

"""


        place += 1



    await update.message.reply_text(
        text
    )



# ---------------------
# جایزه تورنمنت
# ---------------------

def tournament_reward(user_id, amount):

    uid = str(user_id)


    if uid in users:

        users[uid]["liber"] += amount

        users[uid]["xp"] += 50

        save_data()



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^🏆 تورنمنت$"),
        tournament
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^📊 رتبه‌بندی$"),
        ranking
    )
)# =====================
# VERSION 7 ADDONS
# WALLET + WITHDRAW
# =====================


# ---------------------
# ساخت کیف پول
# ---------------------

def init_wallet(data):

    if "wallet" not in data:

        data["wallet"] = {

            "history": []

        }

        save_data()



# ---------------------
# نمایش کیف پول
# ---------------------

async def wallet(update, context):

    data = get_user(
        update.effective_user
    )

    init_wallet(data)


    await update.message.reply_text(
f"""
💳 کیف پول Liber

💰 موجودی:
{data['liber']} LIBER

📜 تراکنش‌ها:
{len(data['wallet']['history'])}
"""
    )



# ---------------------
# برداشت
# ---------------------

async def withdraw(update, context):

    data = get_user(
        update.effective_user
    )

    init_wallet(data)


    amount = 50


    if data["liber"] < amount:

        await update.message.reply_text(
"""
❌ موجودی کافی نیست

حداقل برداشت:
50 LIBER
"""
        )

        return



    data["liber"] -= amount


    data["wallet"]["history"].append(

        {

            "type": "withdraw",

            "amount": amount

        }

    )


    save_data()


    await update.message.reply_text(
"""
📤 درخواست برداشت ثبت شد

مقدار:
50 LIBER

⏳ وضعیت:
در انتظار بررسی
"""
    )



# ---------------------
# تاریخچه
# ---------------------

async def history(update, context):

    data = get_user(
        update.effective_user
    )

    init_wallet(data)


    if not data["wallet"]["history"]:

        await update.message.reply_text(
            "📜 هنوز تراکنشی نداری"
        )

        return



    text = "📜 تاریخچه:\n\n"


    for item in data["wallet"]["history"]:

        text += (
            f"نوع: {item['type']}\n"
            f"مقدار: {item['amount']} LIBER\n\n"
        )


    await update.message.reply_text(
        text
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^💳 کیف پول$"),
        wallet
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^📤 برداشت$"),
        withdraw
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^📜 تاریخچه$"),
        history
    )
    # =========================
# VERSION 8
# SUBSCRIPTION SYSTEM
# =========================

from datetime import datetime, timedelta


PLANS = {

    "premium": {
        "name": "🥉 Premium",
        "days": 30,
        "price": 100
    },

    "premium_plus": {
        "name": "🥈 Premium Plus",
        "days": 90,
        "price": 250
    },

    "liber_pro": {
        "name": "👑 Liber Pro",
        "days": 180,
        "price": 500
    }

}



def add_subscription(data, plan):

    if plan not in PLANS:
        return False


    item = PLANS[plan]


    end = datetime.now() + timedelta(
        days=item["days"]
    )


    data["subscription"] = {

        "name": item["name"],

        "end": end.strftime(
            "%Y-%m-%d"
        )

    }


    return True



def subscription_text(data):

    sub = data.get(
        "subscription",
        {}
    )


    return f"""
💎 اشتراک Liber

سطح:
{sub.get('name','Normal')}

پایان:
{sub.get('end','ندارد')}
"""



async def subscription_menu(update, context):

    await update.message.reply_text(
"""
💎 فروشگاه اشتراک Liber

🥉 Premium
30 روز
100 LIBER

🥈 Premium Plus
90 روز
250 LIBER

👑 Liber Pro
180 روز
500 LIBER

برای خرید:
خرید Premium
خرید Premium Plus
خرید Liber Pro
"""
    )



async def buy_subscription(update, context):

    from main import get_user, save_data


    data = get_user(
        update.effective_user
    )


    text = update.message.text


    plans = {

        "خرید Premium":
        "premium",

        "خرید Premium Plus":
        "premium_plus",

        "خرید Liber Pro":
        "liber_pro"

    }


    if text not in plans:
        return


    plan = PLANS[
        plans[text]
    ]


    if data["liber"] < plan["price"]:

        await update.message.reply_text(
            "❌ موجودی LIBER کافی نیست"
        )

        return


    data["liber"] -= plan["price"]


    add_subscription(
        data,
        plans[text]
    )


    save_data()


    await update.message.reply_text(
        "🎉 اشتراک با موفقیت فعال شد"
        # =====================
# VERSION 9 ADDONS
# ADMIN PANEL BASIC
# =====================


# ---------------------
# بررسی ادمین
# ---------------------

def is_admin(user_id):

    return user_id == ADMIN_ID



# ---------------------
# آمار ربات
# ---------------------

async def admin_stats(update, context):

    if not is_admin(
        update.effective_user.id
    ):

        await update.message.reply_text(
            "⛔ دسترسی ندارید"
        )

        return



    total = len(users)


    total_liber = 0


    for user in users.values():

        total_liber += user.get(
            "liber",
            0
        )



    await update.message.reply_text(
f"""
👑 پنل مدیریت

👥 کاربران:
{total}

💰 کل LIBER:
{total_liber}
"""
    )



# ---------------------
# اضافه کردن LIBER
# استفاده:
# /addliber user_id amount
# ---------------------

async def add_liber(update, context):

    if not is_admin(
        update.effective_user.id
    ):

        return



    if len(context.args) < 2:

        await update.message.reply_text(
            "فرمت:\n/addliber id amount"
        )

        return



    uid = str(
        context.args[0]
    )


    amount = int(
        context.args[1]
    )


    if uid in users:

        users[uid]["liber"] += amount

        save_data()


        await update.message.reply_text(
            "✅ موجودی اضافه شد"
        )

    else:

        await update.message.reply_text(
            "❌ کاربر پیدا نشد"
        )



# ---------------------
# پیام ادمین
# /adminmsg متن
# ---------------------

async def admin_message(update, context):

    if not is_admin(
        update.effective_user.id
    ):

        return



    text = " ".join(
        context.args
    )


    if not text:

        return



    for uid in users:

        try:

            await context.bot.send_message(
                int(uid),
                text
            )

        except:

            pass



    await update.message.reply_text(
        "📢 پیام ارسال شد"
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^📊 آمار$"),
        admin_stats
    )
)


app.add_handler(
    CommandHandler(
        "addliber",
        add_liber
    )
)


app.add_handler(
    CommandHandler(
        "adminmsg",
        admin_message
    )
)# =====================
# VERSION 10 ADDONS
# PAYMENT + CONFIRM
# =====================


payments = {}



# ---------------------
# ساخت پرداخت
# ---------------------

async def create_payment(update, context):

    user = update.effective_user

    payment_id = (
        str(user.id)
        +
        str(len(payments) + 1)
    )


    payments[payment_id] = {

        "user_id": user.id,

        "status": "pending",

        "plan": "Liber Pro"

    }


    await update.message.reply_text(
f"""
🧾 فاکتور پرداخت

شناسه:
{payment_id}

💎 پلن:
Liber Pro

⏳ وضعیت:
در انتظار تایید
"""
    )



# ---------------------
# تایید پرداخت ادمین
# استفاده:
# /payconfirm شناسه
# ---------------------

async def confirm_payment(update, context):

    if update.effective_user.id != ADMIN_ID:

        await update.message.reply_text(
            "⛔ دسترسی ندارید"
        )

        return



    if not context.args:

        await update.message.reply_text(
            "فرمت:\n/payconfirm ID"
        )

        return



    pid = context.args[0]


    if pid not in payments:

        await update.message.reply_text(
            "❌ پرداخت پیدا نشد"
        )

        return



    payments[pid]["status"] = "paid"


    uid = str(
        payments[pid]["user_id"]
    )


    if uid in users:

        users[uid]["vip"] = "Liber Pro"

        save_data()



    await update.message.reply_text(
        "✅ پرداخت تایید شد"
    )



# ---------------------
# وضعیت پرداخت
# ---------------------

async def payment_history(update, context):

    uid = update.effective_user.id


    text = "📋 پرداخت‌ها:\n\n"


    found = False


    for pid, item in payments.items():

        if item["user_id"] == uid:

            found = True

            text += (
                f"🧾 {pid}\n"
                f"وضعیت: {item['status']}\n\n"
            )


    if not found:

        text = "پرداختی نداری"



    await update.message.reply_text(
        text
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^⭐ پرداخت$"),
        create_payment
    )
)


app.add_handler(
    CommandHandler(
        "payconfirm",
        confirm_payment
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^📋 پرداخت‌های من$"),
        payment_history
    )
)# =====================
# VERSION 11 ADDONS
# ONLINE BATTLE SYSTEM
# =====================

import random



# ---------------------
# ساخت اطلاعات رقابت
# ---------------------

def init_battle(data):

    if "battle" not in data:

        data["battle"] = {

            "wins": 0,

            "losses": 0,

            "score": 0

        }

        save_data()



# ---------------------
# قدرت بازیکن
# ---------------------

def player_power(data):

    return (

        data.get("level", 1) * 10

        +

        data.get("xp", 0)

        +

        data.get("battle", {}).get(
            "wins",
            0
        ) * 5

    )



# ---------------------
# رقابت آنلاین
# ---------------------

async def online_battle(update, context):

    data = get_user(
        update.effective_user
    )


    init_battle(data)


    enemy = random.randint(
        20,
        200
    )


    power = player_power(data)



    if power >= enemy:


        data["battle"]["wins"] += 1

        data["battle"]["score"] += 10

        data["liber"] += 25

        data["xp"] += 10


        result = """
🏆 پیروزی!

🎁 جایزه:

+25 LIBER
+10 XP
+10 امتیاز
"""


    else:


        data["battle"]["losses"] += 1

        data["battle"]["score"] += 2

        data["xp"] += 2


        result = """
❌ شکست

✨ +2 XP
"""



    save_data()


    await update.message.reply_text(
        result
    )



# ---------------------
# نمایش رتبه جنگ
# ---------------------

async def battle_rank(update, context):

    data = get_user(
        update.effective_user
    )


    init_battle(data)


    b = data["battle"]


    await update.message.reply_text(
f"""
⚔️ رتبه رقابت

🏆 برد:
{b['wins']}

❌ باخت:
{b['losses']}

⭐ امتیاز:
{b['score']}

💪 قدرت:
{player_power(data)}
"""
    )



# ---------------------
# HANDLERS
# ---------------------


app.add_handler(
    MessageHandler(
        filters.Regex("^⚔️ رقابت آنلاین$"),
        online_battle
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🏆 رتبه جنگ$"),
        battle_rank
    )
)# =====================
# VERSION 12 ADDONS
# FINAL AUTOMATION
# =====================


# ---------------------
# سیستم رویداد خودکار
# ---------------------

def init_events(data):

    if "events" not in data:

        data["events"] = {

            "points": 0,

            "claims": 0

        }

        save_data()



# ---------------------
# جایزه رویداد
# ---------------------

async def event_reward(update, context):

    data = get_user(
        update.effective_user
    )

    init_events(data)


    reward = 20


    data["liber"] += reward

    data["events"]["claims"] += 1

    data["xp"] += 5


    save_data()


    await update.message.reply_text(
f"""
🔥 جایزه رویداد دریافت شد

+{reward} LIBER

✨ +5 XP

تعداد دریافت:
{data['events']['claims']}
"""
    )



# ---------------------
# وضعیت کامل کاربر
# ---------------------

async def full_status(update, context):

    data = get_user(
        update.effective_user
    )


    await update.message.reply_text(
f"""
🌍 Liber Universe

👤 {data.get('name')}

💰 LIBER:
{data.get('liber',0)}

⭐ Level:
{data.get('level',1)}

✨ XP:
{data.get('xp',0)}

💎 VIP:
{data.get('vip','Normal')}

🏆 برد:
{data.get('wins',0)}
"""
    )



# ---------------------
# HANDLERS
# ---------------------

app.add_handler(
    MessageHandler(
        filters.Regex("^🔥 جایزه رویداد$"),
        event_reward
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^🌍 وضعیت کامل$"),
        full_status
    )
)
    )
