# ===== تنظیمات =====

TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

BOT_NAME = "💎 لیبر کوین"

CHANNEL_USERNAME = "@Libercoin1"

ADMIN_ID = 6188951798

BOT_VERSION = "1.0"


# ===== منوی اصلی =====

MAIN_MENU = ReplyKeyboardMarkup(
[
["👤 پروفایل", "💰 موجودی"],
["💸 برداشت استارز", "💎 خرید اشتراک"],
["🪙 کوین", "👥 زیرمجموعه"],
["🎁 هدیه روزانه", "📊 وضعیت"],
["📞 پشتیبانی", "⚙️ تنظیمات"],
],
resize_keyboard=True,
input_field_placeholder="یکی از گزینه‌ها را انتخاب کنید..."
)


# ===== پیام شروع =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    if not await check_member(user.id, context.bot):

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
f"""
🔒 برای استفاده از {BOT_NAME}

ابتدا در کانال رسمی عضو شوید.

بعد روی «✅ عضو شدم» بزنید.
""",
reply_markup=keyboard
)

        return

    await update.message.reply_text(
f"""
💎 سلام {user.first_name}

به ربات {BOT_NAME} خوش آمدید.

🚀 نسخه : {BOT_VERSION}

🟢 وضعیت ربات : آنلاین

یکی از گزینه‌های زیر را انتخاب کنید.
""",
reply_markup=MAIN_MENU
)
