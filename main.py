from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

ADMIN_ID = 6188951798
CHANNEL = "@Hamster20255555"


# 🏠 منوی اصلی (دکمه معمولی)
main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["💎 اشتراک", "🪙 کوین"],
        ["🎁 هدیه", "🎮 بازی"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"],
    ],
    resize_keyboard=True
)


# 🔒 چک عضویت
async def check_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# 🚀 شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_member(user.id, context.bot):

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
        ])

        await update.message.reply_text(
            "🔒 برای ورود باید عضو کانال باشید",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"""🔥 سلام {user.first_name}

به ربات الماس کوین خوش آمدید 💎
""",
        reply_markup=main_menu
    )


# 🎯 دکمه‌ها
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    # عضویت
    if query.data == "check_join":
        if await check_member(user.id, context.bot):
            await query.message.delete()
            await query.message.reply_text("✅ عضویت تایید شد", reply_markup=main_menu)
        else:
            await query.answer("❌ هنوز عضو نیستی", show_alert=True)

    # پروفایل خفن
    elif query.data == "profile":

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 موجودی شیشه‌ای", callback_data="balance")],
            [InlineKeyboardButton("💎 نوع اشتراک", callback_data="vip")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])

        await query.message.edit_text(
            f"""👤 پروفایل کاربر

🆔 آیدی عددی: {user.id}
👤 نام: {user.first_name}
📝 بیو: ندارد

💎 اشتراک: عادی | افسانه‌ای | اختصاصی
💰 موجودی کوین: 0

⏰ ساعت ورود: فعال
⚠️ اخطار: 0

🔥 وضعیت: آنلاین
""",
            reply_markup=keyboard
        )

    # موجودی
    elif query.data == "balance":
        await query.message.edit_text(
            "💰 موجودی شما: 0 کوین 💎",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="profile")]
            ])
        )

    # اشتراک
    elif query.data == "vip":
        await query.message.edit_text(
            "💎 نوع اشتراک: عادی",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="profile")]
            ])
        )

    # بازگشت
    elif query.data == "home":
        await query.message.edit_text("🏠 منو", reply_markup=main_menu)


# 🧠 پیام‌های متنی
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "👤 پروفایل":
        await update.message.reply_text("👆 از دکمه بالا استفاده کن")

    elif text == "💰 موجودی":
        await update.message.reply_text("💰 موجودی: 0")

    else:
        await update.message.reply_text("از منو استفاده کن 👇", reply_markup=main_menu)


# 🚀 اجرا
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot is running...")
app.run_polling()
