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

برای شروع ابتدا عضو کانال شوید.
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

🕒 ساعت:
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

    data = get_user(
        update.effective_user
    )


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
👥 زیرمجموعه Liber Coin

لینک دعوت شما:

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


app.run_polling()
