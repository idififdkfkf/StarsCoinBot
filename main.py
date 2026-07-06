from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

ADMIN_ID = 6188951798
CHANNEL_USERNAME = "@Hamster20255555"


MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🛒 خرید استارز"), KeyboardButton("💸 برداشت استارز")],
        [KeyboardButton("💎 اشتراک"), KeyboardButton("👤 حساب کاربری")],
        [KeyboardButton("💰 کیف پول"), KeyboardButton("🎁 هدیه روزانه")],
        [KeyboardButton("🎮 بازی"), KeyboardButton("🏆 مأموریت‌ها")],
        [KeyboardButton("🤝 دعوت دوستان"), KeyboardButton("📞 پشتیبانی")],
        [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("ℹ️ درباره ربات")],
    ],
    resize_keyboard=True,
)


async def check_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_member(update.effective_user.id, context.bot):

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📢 عضویت در کانال",
                        url=f"https://t.me/{CHANNEL_USERNAME.replace('@','')}",
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
            "🔒 برای استفاده از ربات ابتدا در کانال عضو شوید.",
            reply_markup=keyboard,
        )
        return

    await update.message.reply_text(
        "🌟 به ربات خوش آمدید.",
        reply_markup=MAIN_MENU,
    )


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "check_join":

        if await check_member(query.from_user.id, context.bot):

            await query.message.delete()

            await query.message.reply_text(
                "✅ عضویت شما تایید شد.",
                reply_markup=MAIN_MENU,
            )

        else:

            await query.answer(
                "❌ هنوز عضو کانال نیستید.",
                show_alert=True,
            )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "🛒 خرید استارز":
        await update.message.reply_text(
            "⭐ بخش خرید استارز\n\nبه زودی فعال می‌شود."
        )

    elif text == "💸 برداشت استارز":
        await update.message.reply_text(
            "🔒 برداشت استارز\n\nدر حال موجودی‌سازی می‌باشد."
        )

    elif text == "💎 اشتراک":
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⭐ اشتراک عادی", callback_data="vip1")],
                [InlineKeyboardButton("💎 اشتراک پرمیوم", callback_data="vip2")],
                [InlineKeyboardButton("👑 اشتراک اختصاصی", callback_data="vip3")],
            ]
        )

        await update.message.reply_text(
            "💎 انتخاب اشتراک",
            reply_markup=keyboard,
        )

    elif text == "👤 حساب کاربری":
        await update.message.reply_text(
            f"""
👤 نام:
{update.effective_user.first_name}

🆔 آیدی:
{update.effective_user.id}

💰 موجودی:
0

⭐ استار:
0
"""
        )

    elif text == "💰 کیف پول":
        await update.message.reply_text("💰 موجودی کیف پول: 0")

    elif text == "🎁 هدیه روزانه":
        await update.message.reply_text("🎁 بزودی فعال می‌شود.")

    elif text == "🎮 بازی":
        await update.message.reply_text("🎮 بزودی اضافه می‌شود.")

    elif text == "🏆 مأموریت‌ها":
        await update.message.reply_text("🏆 بزودی اضافه می‌شود.")

    elif text == "🤝 دعوت دوستان":
        await update.message.reply_text("🤝 بزودی اضافه می‌شود.")

    elif text == "📞 پشتیبانی":
        await update.message.reply_text("📞 بزودی اضافه می‌شود.")

    elif text == "⚙️ تنظیمات":
        await update.message.reply_text("⚙️ بزودی اضافه می‌شود.")

    elif text == "ℹ️ درباره ربات":
        await update.message.reply_text(
            "🤖 نسخه 1.0\nStarsCoinBot"
        )


app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(callback))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))

print("Bot Started...")

app.run_polling()
