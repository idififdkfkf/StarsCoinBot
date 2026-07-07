from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes


TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

ADMIN_ID = 6188951798

CHANNEL = "@Libercoin1"


# منوی اصلی
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 ارز LIBER", "💎 اشتراک"],
        ["🎮 بازی‌ها", "👥 زیرمجموعه"],
        ["🛒 فروشگاه", "📞 پشتیبانی"]
    ],
    resize_keyboard=True
)



# بررسی عضویت
async def check_member(user_id, bot):

    try:
        member = await bot.get_chat_member(
            chat_id=CHANNEL,
            user_id=user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            return True

        return False

    except Exception as e:
        print("CHECK ERROR:", e)
        return False



# شروع
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
🔒 سلام جناب {user.first_name}

برای ورود به Liber Coin
ابتدا عضو کانال شوید.

بعد از عضویت روی
✅ عضو شدم
بزنید.
""",
            reply_markup=keyboard
        )

        return



    await update.message.reply_text(
f"""
🔥 سلام جناب {user.first_name}

به Liber Coin خوش آمدید 🪙

✅ عضویت شما تایید شده است.
""",
        reply_markup=MAIN_MENU
    )



# دکمه عضو شدم
async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    user = query.from_user

    await query.answer()


    if await check_member(
        user.id,
        context.bot
    ):


        await query.edit_message_text(
f"""
✅ عضویت شما با موفقیت تایید شد

🔥 خوش آمدید جناب {user.first_name}

حساب شما فعال شد.
"""
        )


        await query.message.reply_text(
            "🪙 منوی Liber Coin",
            reply_markup=MAIN_MENU
        )


    else:

        await query.answer(
            "❌ شما هنوز عضو نشده‌اید!",
            show_alert=True
        )



# اجرا

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CallbackQueryHandler(
        check_button,
        pattern="^check$"
    )
)


print("Liber Coin Started ✅")

app.run_polling()
