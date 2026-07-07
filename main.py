from telegram import (
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


TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

ADMIN_ID = 6188951798

CHANNEL = "@Libercoin1"


users = {}


MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 LIBER", "⭐ Stars"],
        ["💎 اشتراک", "👥 زیرمجموعه"],
        ["🎮 بازی‌ها", "🏆 رتبه‌بندی"],
        ["🛒 فروشگاه", "📞 پشتیبانی"],
        ["⚙️ تنظیمات"]
    ],
    resize_keyboard=True
)


def get_user(user):

    if user.id not in users:

        users[user.id] = {

            "name": user.first_name,
            "liber": 100,
            "stars": 0,
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
                        url="https://t.me/Libercoin1"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "✅ عضو شدم",
                        callback_data="check_join"
                    )
                ]

            ]
        )


        await update.message.reply_text(

f"""
🔥 سلام {user.first_name}

به ربات Liber Coin خوش آمدید 🪙

برای شروع ابتدا عضو کانال شوید.

بعد از عضویت روی دکمه عضو شدم بزنید.
""",

reply_markup=keyboard

        )

        return



    get_user(user)


    await update.message.reply_text(

f"""
🎉 خوش آمدید {user.first_name}

به دنیای Liber Coin وارد شدید 🪙

💰 اقتصاد
🎮 بازی
🏆 رقابت
💎 اشتراک

همه آماده است!
""",

reply_markup=MAIN_MENU

    )




async def check_join(update, context):

    query = update.callback_query

    user = query.from_user


    await query.answer()


    if await check_member(
        user.id,
        context.bot
    ):


        get_user(user)


        await query.edit_message_text(

f"""
✅ عضویت شما تایید شد

🔥 خوش آمدید {user.first_name}

حساب شما فعال شد.
"""
        )


        await query.message.reply_text(
            "🪙 منوی اصلی Liber Coin",
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


    now = datetime.now().strftime(
        "%H:%M:%S"
    )


    await update.message.reply_text(

f"""
╭━━ 🪙 Liber Coin ━━╮

👤 نام:
{user.first_name}

🆔 آیدی:
{user.id}

🪙 LIBER:
{data['liber']}

⭐ Stars:
{data['stars']}

👥 زیرمجموعه:
{data['ref']}

⚠️ اخطار:
{data['warn']}

💎 اشتراک:
{data['vip']}

🤖 وضعیت:
فعال

🕒 ساعت:
{now}

╰━━━━━━━━━━━━╯
"""
    )



async def balance(update, context):

    user = update.effective_user

    data = get_user(user)


    await update.message.reply_text(

f"""
💰 کیف پول شما

🪙 LIBER:
{data['liber']}

⭐ Stars:
{data['stars']}
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
        check_join,
        pattern="check_join"
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



print(
"🔥 Liber Coin V1 Started"
)


app.run_polling()
# =========================
# Liber Coin V2
# سیستم اشتراک
# =========================


from datetime import timedelta


VIP_PLANS = {

    "premium_3": {
        "name": "💎 Premium",
        "time": "3 ماه",
        "price": 70
    },

    "premium_6": {
        "name": "💎 Premium",
        "time": "6 ماه",
        "price": 130
    },

    "premium_12": {
        "name": "💎 Premium",
        "time": "12 ماه",
        "price": 160
    },


    "liber_3": {
        "name": "👑 Liber Premium",
        "time": "3 ماه",
        "price": 150
    },

    "liber_6": {
        "name": "👑 Liber Premium",
        "time": "6 ماه",
        "price": 200
    },

    "liber_12": {
        "name": "👑 Liber Premium",
        "time": "12 ماه",
        "price": 250
    }

}




async def vip_menu(update, context):

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 Liber Premium",
                callback_data="liber_premium"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ برگشت",
                callback_data="back"
            )
        ]

    ])


    await update.message.reply_text(

"""
💎 خرید اشتراک Liber Coin

نوع اشتراک را انتخاب کنید:
""",

reply_markup=keyboard

    )# =========================
# Liber Coin V3
# سیستم زیرمجموعه
# =========================


REF_REWARD_NORMAL = 100
REF_REWARD_VIP = 150



async def referral(update, context):

    user = update.effective_user

    data = get_user(user)


    bot_username = (await context.bot.get_me()).username


    link = (
        f"https://t.me/{bot_username}"
        f"?start={user.id}"
    )


    await update.message.reply_text(

f"""app.add_handler(
    MessageHandler(
        filters.Regex("^👥 زیرمجموعه$"),
        referral
    )
)

👥
