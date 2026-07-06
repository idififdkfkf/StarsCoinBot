from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
import os

TOKEN = os.getenv("7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🛒 خرید استارز", callback_data="stars")],
        [InlineKeyboardButton("💎 خرید اشتراک", callback_data="vip")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="profile")],
        [InlineKeyboardButton("💰 موجودی", callback_data="wallet")],
        [InlineKeyboardButton("🎁 هدیه روزانه", callback_data="gift")],
        [InlineKeyboardButton("🎮 بازی", callback_data="game")],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "🌟 به ربات خوش آمدید.\n\nیکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup,
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    texts = {
        "stars": "🛒 بخش خرید استارز (به‌زودی)",
        "vip": "💎 خرید اشتراک (به‌زودی)",
        "profile": "👤 حساب کاربری (به‌زودی)",
        "wallet": "💰 موجودی (به‌زودی)",
        "gift": "🎁 هدیه روزانه (به‌زودی)",
        "game": "🎮 بازی (به‌زودی)",
        "support": "📞 پشتیبانی (به‌زودی)",
        "settings": "⚙️ تنظیمات (به‌زودی)",
    }

    await query.edit_message_text(texts.get(query.data, "گزینه نامعتبر"))

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))

print("Bot Started...")
app.run_polling()
