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
        ["💎 اشتراک", "👥 زیرمجموعه"],
        ["🎮 بازی‌ها", "🛒 فروشگاه"],
        ["🏆 رتبه‌بندی", "📞 پشتیبانی"]
    ],
    resize_keyboard=True
)


def get_user(user):

    if user.id not in users:

        users[user.id] = {
            "name": user.first_name,
            "liber": 100,
            "stars": 0,
            "vip": "عادی",
            "ref": 0,
            "warn": 0
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


    if not await check_member(user.id, context.bot):

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
                        callback_data="check"
                    )
                ]
            ]
        )


        await update.message.reply_text(
f"""
🔥 سلام {user.first_name}

به Liber Coin خوش آمدید 🪙

برای ورود ابتدا عضو کانال شوید.
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



async def check_button(update, context):

    query = update.callback_query

    user = query.from_user

    await query.answer()


    if await check_member(user.id, context.bot):

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
{user.first_name}

🆔 آیدی:
{user.id}

🪙 LIBER:
{data['liber']}

⭐ Stars:
{data['stars']}

💎 اشتراک:
{data['vip']}

👥 زیرمجموعه:
{data['ref']}

⚠️ اخطار:
{data['warn']}

🕒 ساعت:
{datetime.now().strftime("%H:%M:%S")}

╰━━━━━━━━━━━━╯
"""
    )



async def balance(update, context):

    data = get_user(update.effective_user)

    await update.message.reply_text(
f"""
💰 کیف پول

🪙 LIBER:
{data['liber']}

⭐ Stars:
{data['stars']}
"""
    )



app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler("start", start)
)


app.add_handler(
    CallbackQueryHandler(
        check_button,
        pattern="check"
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



print("🔥 Liber Coin V1 Started")


app.run_polling()
