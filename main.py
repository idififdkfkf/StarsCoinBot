from telegram import (from datetime import timedelta
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from datetime import datetime


TOKEN = "توکن_ربات_خودت"

CHANNEL = "@Libercoin1"

ADMIN_ID = 6188951798


users = {}


MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 LIBER", "📊 آمار"],
        ["👥 زیرمجموعه", "🎮 بازی‌ها"],
        ["🛒 فروشگاه", "📞 پشتیبانی"]
    ],
    resize_keyboard=True
)



def get_user(user):

    if user.id not in users:

        users[user.id] = {

            "name": user.first_name,
            "liber": 100,
            "ref": 0,
            "warn": 0,
            "vip": "عادی",
            "join": datetime.now()

        }

    return users[user.id]



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



async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    if not await check_member(
        user.id,
        context.bot
    ):

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📢 عضویت کانال",
                        url=f"https://t.me/{CHANNEL.replace('@','')}"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "✅ عضو شدم",
                        callback_data="join"
                    )
                ]
            ]
        )


        await update.message.reply_text(

f"""
🔥 سلام {user.first_name}

به ربات Liber Coin خوش آمدید 🪙

برای شروع عضو کانال شوید.
""",

reply_markup=keyboard

        )

        return



    get_user(user)


    await update.message.reply_text(

f"""
🎉 خوش آمدید {user.first_name}

حساب شما فعال شد ✅

به دنیای Liber Coin وارد شدید 🪙
""",

reply_markup=MAIN_MENU

    )



async def join_check(update, context):

    query = update.callback_query

    user = query.from_user

    await query.answer()


    if await check_member(
        user.id,
        context.bot
    ):

        get_user(user)


        await query.edit_message_text(
"""
✅ عضویت شما تایید شد

🔥 خوش آمدید به Liber Coin
"""
        )


        await query.message.reply_text(
            "🪙 منوی اصلی",
            reply_markup=MAIN_MENU
        )


    else:

        await query.answer(
            "❌ هنوز عضو کانال نیستید",
            show_alert=True
        )



async def profile(update, context):

    user = update.effective_user

    data = get_user(user)


    await update.message.reply_text(

f"""
╭━━ 🪙 Liber Coin ━━╮

👤 نام:
{data['name']}

🆔 آیدی:
{user.id}

🪙 LIBER:
{data['liber']}

👥 زیرمجموعه:
{data['ref']}

⚠️ اخطار:
{data['warn']}

💎 اشتراک:
{data['vip']}

🕒 زمان:
{datetime.now().strftime("%H:%M:%S")}

╰━━━━━━━━━━━━╯
"""
    )



async def balance(update, context):

    data = get_user(
        update.effective_user
    )


    await update.message.reply_text(

f"""
💰 موجودی شما

🪙 LIBER:
{data['liber']}
"""
    )



async def stats(update, context):

    user = update.effective_user

    data = get_user(user)


    await update.message.reply_text(

f"""
📊 آمار شما

🪙 LIBER:
{data['liber']}

👥 زیرمجموعه:
{data['ref']}

⚠️ اخطار:
{data['warn']}
"""
    )



async def referral(update, context):

    user = update.effective_user

    data = get_user(user)


    bot = await context.bot.get_me()

    link = f"https://t.me/{bot.username}?start={user.id}"


    await update.message.reply_text(

f"""
👥 سیستم زیرمجموعه

لینک شما:

{link}

تعداد دعوت:
{data['ref']}
"""
    )



app = ApplicationBuilder().token(TOKEN).build()



app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CallbackQueryHandler(
        join_check,
        pattern="join"
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
    MessageHandler(
        filters.Regex("^📊 آمار$"),
        stats
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👥 زیرمجموعه$"),
        referral
    )
)


print("🔥 Liber Coin V1 Started")

# =========================
# Liber Coin V2
# VIP System
# =========================


VIP_PLANS = {

    "p3": {
        "name": "💎 Premium",
        "month": 3,
        "price": 70
    },

    "p6": {
        "name": "💎 Premium",
        "month": 6,
        "price": 130
    },

    "p12": {
        "name": "💎 Premium",
        "month": 12,
        "price": 160
    },


    "l3": {
        "name": "👑 Liber Premium",
        "month": 3,
        "price": 150
    },

    "l6": {
        "name": "👑 Liber Premium",
        "month": 6,
        "price": 200
    },

    "l12": {
        "name": "👑 Liber Premium",
        "month": 12,
        "price": 250
    }

}



async def vip_menu(update, context):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "💎 Premium",
                    callback_data="premium"
                )
            ],

            [
                InlineKeyboardButton(
                    "👑 Liber Premium",
                    callback_data="liber"
                )
            ]
        ]
    )


    await update.message.reply_text(

"""
💎 خرید اشتراک Liber Coin

نوع اشتراک را انتخاب کنید:
""",

reply_markup=keyboard

    )



async def vip_select(update, context):

    query = update.callback_query

    await query.answer()


    if query.data == "premium":

        buttons = [

            ("3 ماه ⭐70", "p3"),

            ("6 ماه ⭐130", "p6"),

            ("12 ماه ⭐160", "p12")

        ]

    else:

        buttons = [

            ("3 ماه ⭐150", "l3"),

            ("6 ماه ⭐200", "l6"),

            ("12 ماه ⭐250", "l12")

        ]



    keyboard = InlineKeyboardMarkup(

        [

            [

                InlineKeyboardButton(
                    text,
                    callback_data=data
                )

            ]

            for text,data in buttons

        ]

    )


    await query.edit_message_text(

        "⏳ مدت اشتراک را انتخاب کنید:",

        reply_markup=keyboard

    )




async def buy_vip(update, context):

    query = update.callback_query

    user = query.from_user


    data = get_user(user)


    plan = VIP_PLANS.get(
        query.data
    )


    if not plan:
        return



    end = datetime.now() + timedelta(

        days=plan["month"] * 30

    )



    data["vip"] = plan["name"]

    data["vip_end"] = end.strftime(
        "%Y/%m/%d"
    )



    await query.answer()



    await query.edit_message_text(

f"""
🎉 تبریک {user.first_name}

اشتراک شما فعال شد ✅


💎 نوع:
{plan['name']}


⏳ مدت:
{plan['month']} ماه


⭐ هزینه:
{plan['price']} Stars


📅 پایان:
{data['vip_end']}


🚀 از امکانات ویژه Liber Coin لذت ببرید
"""
    )
app.run_polling()
