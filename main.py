from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from datetime import datetime

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

ADMIN_ID = 6188951798
CHANNEL = "@Hamster20255555"


# 🏠 منوی اصلی (تمیز)
main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["💎 اشتراک", "🪙 کوین"],
        ["🎁 هدیه", "🎮 بازی"],
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


# 🚀 شروع ربات
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_member(user.id, context.bot):

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check")]
        ])

        await update.message.reply_text(
            "🔒 برای ورود باید عضو کانال باشید",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"👋 سلام {user.first_name}\nبه ربات الماس کوین خوش آمدید 💎",
        reply_markup=main_menu
    )


# 🎯 دکمه‌ها
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    user = q.from_user

    now = datetime.now().strftime("%Y-%m-%d | %H:%M")

    # بررسی عضویت
    if q.data == "check":
        if await check_member(user.id, context.bot):
            await q.message.delete()
            await q.message.reply_text("✅ خوش آمدید", reply_markup=main_menu)
        else:
            await q.answer("❌ هنوز عضو نیستی", show_alert=True)


    # 👤 پروفایل خفن
    elif q.data == "profile":

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 موجودی شیشه‌ای", callback_data="balance")],
            [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
        ])

        await q.message.edit_text(
f"""
👤 پروفایل کاربر

🆔 آیدی عددی: {user.id}
👤 نام: {user.first_name}
📝 بیو: ندارد

💎 نوع اشتراک: عادی
🪙 موجودی کوین: 0
👥 زیرمجموعه: 0

⏰ تاریخ و ساعت: {now}
⚠️ اخطار: 0

🔥 وضعیت: آنلاین
""",
            reply_markup=keyboard
        )


    # 💰 موجودی شیشه‌ای
    elif q.data == "balance":
        await q.message.edit_text(
            "💰 موجودی شما:\n\n🟩 10 کوین (شیشه‌ای)\n\n⛔ هنوز سیستم شارژ فعال نشده",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 برگشت", callback_data="profile")]
            ])
        )


    # 🏠 برگشت
    elif q.data == "home":
        await q.message.edit_text("🏠 منوی اصلی")
        await q.message.reply_text("👇", reply_markup=main_menu)


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
