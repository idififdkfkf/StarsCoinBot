from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from datetime import datetime


TOKEN = "8818731091:AAHYaM4Wf9gZipqKJfXSwQhFx4qzKgnzFPQ"

ADMIN_ID = 6188951798

CHANNEL = "@Libercoin1"


# اطلاعات موقت کاربران
users = {}


# منوی اصلی
MAIN_MENU = ReplyKeyboardMarkup(
    [
        ["👤 پروفایل", "💰 موجودی"],
        ["🪙 ارز LIBER", "💎 اشتراک"],
        ["🎮 بازی‌ها", "👥 زیرمجموعه"],
        ["🛒 فروشگاه", "🏛 مزایده"],
        ["📞 پشتیبانی", "⚙️ تنظیمات"]
    ],
    resize_keyboard=True
)



def get_user(user):

    if user.id not in users:
        users[user.id] = {
            "liber": 100,
            "stars": 0,
            "vip": "عادی",
            "ref": 0,
            "warn": 0
        }

    return users[user.id]



# بررسی عضویت
async def check_member(user_id, bot):

    try:

        member = await bot.get_chat_member(
            CHANNEL,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:

        print("CHECK ERROR:", e)

        return False



# استارت
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
                        callback_data="check"
                    )
                ]
            ]
        )


        await update.message.reply_text(
f"""
🔒 سلام جناب {user.first_name}

به Liber Coin خوش آمدید 🪙

برای ورود ابتدا عضو کانال رسمی شوید.

بعد از عضویت روی «عضو شدم» بزنید.
""",
            reply_markup=keyboard
        )

        return



    await update.message.reply_text(
f"""
🔥 سلام جناب {user.first_name}

به ربات Liber Coin خوش آمدید 🪙

✅ حساب شما فعال است.
""",
        reply_markup=MAIN_MENU
    )



# تایید عضویت
async def check_button(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    user = query.from_user

    await query.answer()


    if await check_member(user.id, context.bot):

        await query.edit_message_text(
f"""
✅ عضویت شما با موفقیت تایید شد

🔥 خوش آمدید جناب {user.first_name}

حساب شما فعال شد.
"""
        )

        await query.message.reply_text(
            "🪙 منوی Liber Coin",
            reply_markup=MAIN_MENU
        )


    else:

        await query.answer(
            "❌ شما هنوز عضو کانال نشده‌اید.",
            show_alert=True
        )



# پروفایل
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    data = get_user(user)

    now = datetime.now().strftime(
        "%Y/%m/%d %H:%M"
    )


    await update.message.reply_text(
f"""
╭━━ 💎 Liber Coin ━━╮

👤 نام:
{user.first_name}

🆔 آیدی عددی:
{user.id}

🪙 لیبر:
{data['liber']}

⭐ استارز:
{data['stars']}

💎 اشتراک:
{data['vip']}

👥 زیرمجموعه:
{data['ref']}

⚠️ اخطار:
{data['warn']}

🕒 زمان:
{now}

╰━━━━━━━━━━━━╯
"""
    )



app = ApplicationBuilder().token(TOKEN).build()


app.add_handler(
    CommandHandler(
        "start",
        start
    )
)


app.add_handler(
    CallbackQueryHandler(
        check_button,
        pattern="check"
    )
)


app.add_handler(
    MessageHandler(
        filters.Regex("^👤 پروفایل$"),
        profile
    )
)


print("🔥 Liber Coin Version 1 Started")


app.run_polling()
