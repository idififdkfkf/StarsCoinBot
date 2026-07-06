from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

TOKEN = "7357995901:AAHqGAaiDIG1esP8Z59cBGuDhZmju7KG8ts"

# --- منوی اصلی ---
main_menu = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["💎 اشتراک", "🪙 کوین"],
        ["🎁 هدیه روزانه", "🎮 بازی"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"],
    ],
    resize_keyboard=True
)

# --- شروع ربات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 مشاهده پروفایل", callback_data="profile")]
    ])

    await update.message.reply_text(
        f"""سلام {user.first_name} 👋

به ربات الماس کوین خوش آمدید 💎
""",
        reply_markup=keyboard
    )

# --- دکمه‌ها ---
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if query.data == "profile":

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 موجودی", callback_data="balance")],
            [InlineKeyboardButton("💎 نوع اشتراک", callback_data="vip")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
        ])

        await query.message.edit_text(
            f"""👤 اطلاعات کاربر

🆔 آیدی عددی: {user.id}
👤 نام: {user.first_name}
📝 یوزرنیم: @{user.username if user.username else "ندارد"}

💎 اشتراک: عادی
🪙 موجودی کوین: 0

⏰ ساعت: فعال
📍 وضعیت: آنلاین
""",
            reply_markup=keyboard
        )

    elif query.data == "balance":
        await query.message.edit_text(
            "💰 موجودی شما: 0 کوین 💎",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="profile")]
            ])
        )

    elif query.data == "vip":
        await query.message.edit_text(
            "💎 نوع اشتراک شما: عادی",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔙 بازگشت", callback_data="profile")]
            ])
        )

    elif query.data == "home":
        await query.message.edit_text(
            "🏠 بازگشت به پروفایل",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👤 مشاهده پروفایل", callback_data="profile")]
            ])
        )

# --- پیام‌های متنی ---
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if text == "👤 پروفایل":
        await update.message.reply_text("از دکمه بالا استفاده کن 👆")

    elif text == "💰 موجودی":
        await update.message.reply_text("💰 موجودی: 0 کوین")

    elif text == "💎 اشتراک":
        await update.message.reply_text("💎 اشتراک: عادی")

    else:
        await update.message.reply_text("از منو استفاده کن 👇", reply_markup=main_menu)

# --- اجرای ربات ---
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(buttons))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

print("Bot is running...")
app.run_polling()
CHANNEL = "@Hamster20255555"
ADMIN_ID = 6188951798


# --- چک عضویت ---
async def check_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


# --- /start با عضویت اجباری ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_member(user.id, context.bot):

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{CHANNEL.replace('@','')}")],
            [InlineKeyboardButton("✅ عضو شدم", callback_data="check_join")]
        ])

        await update.message.reply_text(
            "🔒 برای استفاده از ربات باید عضو کانال شوید",
            reply_markup=keyboard
        )
        return

    await update.message.reply_text(
        f"سلام {user.first_name} 👋\nبه ربات الماس کوین خوش آمدید 💎",
        reply_markup=main_menu
    )


# --- بررسی عضویت ---
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
            await query.answer("❌ هنوز عضو نشدی", show_alert=True)

    # پنل مدیریت
    elif query.data == "admin_panel":
        if user.id == ADMIN_ID:
            await query.message.edit_text(
                "👑 پنل مدیریت",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 آمار", callback_data="stats")],
                    [InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")],
                    [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
                ])
            )
        else:
            await query.answer("⛔ دسترسی نداری", show_alert=True)

    # بازگشت
    elif query.data == "home":
        await query.message.edit_text("🏠 منوی اصلی", reply_markup=main_menu)
