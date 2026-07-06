from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید استارز", callback_data="stars")],
        [InlineKeyboardButton("💎 خرید اشتراک", callback_data="vip")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="profile")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("🎁 هدیه روزانه", callback_data="gift")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]

    await update.message.reply_text(
        "🌟 به ربات خوش آمدید.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    messages = {
        "stars": "🛒 بخش خرید استارز",
        "vip": "💎 بخش خرید اشتراک",
        "profile": "👤 حساب کاربری",
        "wallet": "💰 کیف پول",
        "gift": "🎁 هدیه روزانه",
        "game": "🎮 بازی",
        "support": "📞 پشتیبانی",
        "settings": "⚙️ تنظیمات",
    }

    await query.edit_message_text(messages.get(query.data, "گزینه نامعتبر"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

print("Bot Started...")
app.run_polling()
elif query.data == "profile":
    await query.edit_message_text(
        text=f"""
👤 اطلاعات حساب

🆔 آیدی: {query.from_user.id}
👤 نام: {query.from_user.first_name}

💎 اشتراک: رایگان
💰 موجودی: 0 تومان
⭐ استار: 0

به ربات خوش آمدید 🌟
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 خرید اشتراک", callback_data="vip")],
            [InlineKeyboardButton("💰 شارژ کیف پول", callback_data="wallet")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])
    )elif query.data == "home":
    keyboard = [
        [InlineKeyboardButton("🛒 خرید استارز", callback_data="stars")],
        [InlineKeyboardButton("💎 خرید اشتراک", callback_data="vip")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="profile")],
        [InlineKeyboardButton("💰 کیف پول", callback_data="wallet")],
        [InlineKeyboardButton("🎁 هدیه روزانه", callback_data="gift")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")]
    ]

    await query.edit_message_text(
        "🌟 منوی اصلی",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
