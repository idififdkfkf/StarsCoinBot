from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
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

CHANNEL = "@Hamster20255555"
ADMIN_ID = 6188951798

MAIN_MENU = ReplyKeyboardMarkup(
    [
        [KeyboardButton("👤 پروفایل"), KeyboardButton("🛒 خرید استارز")],
        [KeyboardButton("💸 برداشت استارز"), KeyboardButton("💰 کیف پول")],
        [KeyboardButton("💎 اشتراک"), KeyboardButton("🎁 هدیه روزانه")],
        [KeyboardButton("🎮 بازی"), KeyboardButton("🏆 مأموریت‌ها")],
        [KeyboardButton("👥 دعوت دوستان"), KeyboardButton("📞 پشتیبانی")],
        [KeyboardButton("⚙️ تنظیمات"), KeyboardButton("ℹ️ درباره ربات")],
    ],
    resize_keyboard=True,
)


async def check_member(user_id, bot):
    try:
        member = await bot.get_chat_member(CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    if not await check_member(user.id, context.bot):

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
                        "✅ بررسی عضویت",
                        callback_data="join",
                    )
                ],
            ]
        )

        await update.message.reply_text(
            "🔒 برای استفاده از ربات ابتدا عضو کانال شوید.",
            reply_markup=keyboard,
        )
        return

    await update.message.reply_text(
        f"""👋 سلام {user.first_name}

💎 به ربات الماس کوین خوش آمدید.

از منوی زیر استفاده کنید.
""",
        reply_markup=MAIN_MENU,
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user

    if query.data == "join":

        if await check_member(user.id, context.bot):

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

    elif query.data == "profile":

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "💰 موجودی",
                        callback_data="balance",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "💎 نوع اشتراک",
                        callback_data="vip",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "⚠️ اخطارها",
                        callback_data="warn",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🔙 برگشت",
                        callback_data="home",
                    )
                ],
            ]
        )

        await query.edit_message_text(
            f"""
👤 پروفایل

🆔 آیدی عددی:
{user.id}

👤 نام:
{user.first_name}

📛 یوزرنیم:
@{user.username if user.username else "ندارد"}

💎 اشتراک:
عادی

🪙 موجودی کوین:
0

⭐ موجودی استار:
0

⚠️ اخطار:
0

🟢 وضعیت:
فعال
""",
            reply_markup=keyboard,
        )

    elif query.data == "balance":

        await query.edit_message_text(
            """
💰 کیف پول

🪙 کوین: 0

⭐ استار: 0

💳 موجودی ریالی:
0 تومان
""",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 برگشت",
                            callback_data="profile",
                        )
                    ]
                ]
            ),
        )
