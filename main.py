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


# =========================
# منوی اصلی Liber Coin
# =========================

main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 کیف پول"],
        ["🪙 ارز LIBER", "💎 اشتراک"],
        ["🎮 بازی‌ها", "🏆 رنک"],
        ["🎁 هدیه روزانه", "👥 زیرمجموعه"],
        ["🛒 فروشگاه", "🏛 مزایده"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"]
    ],
    resize_keyboard=True
)



# =========================
# بررسی عضویت
# =========================

async def check_join(user_id, bot):

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



# =========================
# شروع ربات
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user


    if not await check_join(
        user.id,
        context.bot
    ):

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
                        callback_data="check_join"
                    )
                ]
            ]
        )


        await update.message.reply_text(
            """
🔒 برای ورود به Liber Coin

ابتدا عضو کانال رسمی شوید.

بعد روی «عضو شدم» بزنید.
            """,
            reply_markup=keyboard
        )

        return



    await update.message.reply_text(

f"""
🔥 سلام {user.first_name}

به ربات رسمی Liber Coin خوش آمدید 🪙

🌟 دنیای بازی، ارز، رقابت و جایزه

از منوی زیر انتخاب کنید 👇
""",

        reply_markup=main_menu
    )



# =========================
# اجرا
# =========================

app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


print("Liber Coin Started...")


app.run_polling()
