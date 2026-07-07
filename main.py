from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

CHANNEL = "@Hamster20255555"
ADMIN_ID = 6188951798


# منوی اصلی
main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💎 اشتراک"],
        ["🛍 فروشگاه", "💸 برداشت استارز"],
        ["🎮 رقابت آنلاین", "🏆 تورنمنت"],
        ["👥 زیرمجموعه", "🎁 هدیه روزانه"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"],
    ],
    resize_keyboard=True,
)


# بررسی عضویت
async def check_join(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    joined = await check_join(user.id, context.bot)

    if not joined:

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📢 عضویت در کانال",
                        url="https://t.me/Hamster20255555",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✅ عضو شدم",
                        callback_data="check_join",
                    )
                ],
            ]
        )

        await update.message.reply_text(
            "🔒 لطفاً ابتدا در کانال زیر عضو شوید.",
            reply_markup=keyboard,
        )
        return

    text = (
        f"👋 سلام جناب {user.first_name}\n\n"
        "🌟 به ربات الماس همستر خوش آمدید.\n\n"
        "از منوی زیر استفاده کنید."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu,
    )


# بررسی عضویت
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "check_join":

        ok = await check_join(query.from_user.id, context.bot)

        if ok:

            await query.edit_message_text(
                "✅ عضویت شما تأیید شد."
            )

            await query.message.reply_text(
                f"👋 سلام جناب {query.from_user.first_name}\n"
                "به ربات الماس همستر خوش آمدید.",
                reply_markup=main_menu,
            )

        else:

            await query.answer(
                "❌ هنوز عضو کانال نیستید.",
                show_alert=True,
            )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

print("Bot Started...")

app.run_polling()
