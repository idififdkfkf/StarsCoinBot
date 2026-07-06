from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"
ADMIN_ID = 6188951798
CHANNEL = "@Hamster20255555"


# 🧠 منوی اصلی (خیلی تمیز)
main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["💎 اشتراک", "🛒 خرید"],
        ["🎮 بازی", "🎁 هدیه"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"],
    ],
    resize_keyboard=True
)


# 🔒 عضویت اجباری
async def check_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# 🚀 شروع
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_member(user.id, context.bot):

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ بررسی عضویت", callback_data="check")]
        ])

        await update.message.reply_text(
            "🔒 برای ورود باید عضو کانال باشید",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"👋 سلام {user.first_name}\nبه ربات خوش آمدید 💎",
        reply_markup=main_menu
    )


# 🎯 کنترل دکمه‌ها
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user

    # بررسی عضویت
    if q.data == "check":
        if await check_member(user.id, context.bot):
            await q.message.delete()
            await q.message.reply_text("✅ خوش آمدید", reply_markup=main_menu)
        else:
            await q.answer("❌ هنوز عضو نیستی", show_alert=True)


    # 👤 پروفایل (خیلی خفن)
    elif q.data == "profile":

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 موجودی", callback_data="balance")],
            [InlineKeyboardButton("💎 اشتراک", callback_data="vip")]
        ])

        await q.message.edit_text(
f"""
👤 پروفایل کاربر

🆔 آیدی: {user.id}
👤 نام: {user.first_name}

💎 اشتراک: عادی
💰 موجودی: 0
⚠️ اخطار: 0
""",
            reply_markup=keyboard
        )


    elif q.data == "balance":
        await q.message.edit_text(
            "💰 موجودی شما: 0",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بستن", callback_data="close")]
            ])
        )


    elif q.data == "vip":
        await q.message.edit_text(
            "💎 اشتراک: عادی",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بستن", callback_data="close")]
            ])
        )


    # ❌ هیچ برگشتی داخل منو نداریم (طبق حرفت)
    elif q.data == "close":
        await q.message.delete()


# 🧠 پیام‌ها
async def text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("از منو استفاده کن 👇", reply_markup=main_menu)


# 🚀 اجرا
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text))

print("Bot Running...")
app.run_polling()
