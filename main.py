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
    ContextTypes
)


# =========================
# تنظیمات Liber Coin
# =========================

TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

ADMIN_ID = 6188951798

CHANNEL = "@Libercoin1"



# =========================
# منوی اصلی
# =========================

MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 ارز LIBER", "💎 اشتراک"],
        ["🎮 بازی‌ها", "🏆 رتبه‌بندی"],
        ["🎁 هدیه روزانه", "👥 زیرمجموعه"],
        ["🛒 فروشگاه", "🏛 مزایده"],
        ["💸 برداشت", "📞 پشتیبانی"],
        ["⚙️ تنظیمات"]
    ],
    resize_keyboard=True
)



# =========================
# بررسی عضویت
# =========================

async def check_member(user_id, bot):

    try:

        member = await bot.get_chat_member(
            CHANNEL,
            user_id
        )

        if member.status in [
            "member",
            "administrator",
            "creator"
        ]:
            return True

        return False

    except:

        return False



# =========================
# دستور شروع
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    joined = await check_member(
        user.id,
        context.bot
    )


    if not joined:


        keyboard = InlineKeyboardMarkup(
            [

                [
                    InlineKeyboardButton(
                        "📢 عضویت در کانال",
                        url="https://t.me/Libercoin1"
                    )
                ],

                [
                    InlineKeyboardButton(
                        "✅ عضو شدم",
                        callback_data="verify"
                    )
                ]

            ]
        )


        await update.message.reply_text(

f"""
🔒 سلام جناب {user.first_name}

برای استفاده از Liber Coin
ابتدا عضو کانال رسمی شوید.

بعد از عضویت روی دکمه
«عضو شدم» بزنید.
""",

            reply_markup=keyboard
        )

        return



    await update.message.reply_text(

f"""
🔥 سلام جناب {user.first_name}

به ربات Liber Coin خوش آمدید 🪙

✅ عضویت شما تایید شده است.

🌍 آماده شروع هستید.
""",

        reply_markup=MAIN_MENU
    )



# =========================
# دکمه عضو شدم
# =========================

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    user = query.from_user


    await query.answer()


    joined = await check_member(
        user.id,
        context.bot
    )


    if joined:


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

            "❌ شما هنوز عضو نشده‌اید. ابتدا عضو کانال شوید.",

            show_alert=True
        )



# =========================
# اجرای ربات
# =========================

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CallbackQueryHandler(
        verify,
        pattern="verify"
    )
)


print("🔥 Liber Coin Started")


app.run_polling()
