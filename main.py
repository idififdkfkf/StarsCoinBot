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
# ===== پنل مدیریت =====

ADMIN_ID = 6188951798

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ شما دسترسی به پنل مدیریت ندارید.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🎁 هدیه همگانی", callback_data="admin_gift")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")],
        [InlineKeyboardButton("🔙 برگشت", callback_data="home")]
    ])

    await update.message.reply_text(
        "👑 پنل مدیریت الماس‌کوین",
        reply_markup=keyboard
    )


# ===== دکمه‌های پنل مدیریت =====

elif q.data == "admin_stats":
    await q.message.edit_text(
        """📊 آمار ربات

👥 کاربران: 0
🟢 آنلاین: 0
💎 کل کوین: 0
⭐ کل استار: 0
⚠️ اخطارها: 0
""",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )

elif q.data == "admin_users":
    await q.message.edit_text(
        "👥 لیست کاربران\n\nفعلاً کاربری ثبت نشده است.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )

elif q.data == "admin_broadcast":
    await q.message.edit_text(
        "📢 سیستم پیام همگانی\n\n🚧 به‌زودی فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )

elif q.data == "admin_gift":
    await q.message.edit_text(
        "🎁 هدیه همگانی\n\n🚧 به‌زودی فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )

elif q.data == "admin_settings":
    await q.message.edit_text(
        "⚙️ تنظیمات مدیریت\n\n🚧 به‌زودی فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 برگشت", callback_data="admin_back")]
        ])
    )

elif q.data == "admin_back":
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار ربات", callback_data="admin_stats")
         app.add_handler(CommandHandler("admin", admin))
