ADMIN_ID = 6188951798

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    # فقط مدیر اصلی
    if user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 داشبورد", callback_data="admin_dashboard")],
        [InlineKeyboardButton("👥 کاربران", callback_data="admin_users")],
        [InlineKeyboardButton("🪙 اقتصاد", callback_data="admin_economy")],
        [InlineKeyboardButton("💸 برداشت‌ها", callback_data="admin_withdraw")],
        [InlineKeyboardButton("🛒 فروشگاه", callback_data="admin_shop")],
        [InlineKeyboardButton("🎮 بازی‌ها", callback_data="admin_games")],
        [InlineKeyboardButton("🏛 مزایده", callback_data="admin_auction")],
        [InlineKeyboardButton("📢 پیام همگانی", callback_data="admin_broadcast")],
        [InlineKeyboardButton("📊 آمار", callback_data="admin_stats")],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data="admin_settings")]
    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin",
        reply_markup=keyboard
    )


# ثبت هندلر
app.add_handler(CommandHandler("admin", admin_panel))
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ADMIN_ID = 6188951798


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([

        [InlineKeyboardButton("📊 داشبورد", callback_data="dashboard")],

        [
            InlineKeyboardButton("👥 کاربران", callback_data="users"),
            InlineKeyboardButton("💰 اقتصاد", callback_data="economy")
        ],

        [
            InlineKeyboardButton("🪙 LIBER", callback_data="liber"),
            InlineKeyboardButton("⭐ استارز", callback_data="stars")
        ],

        [
            InlineKeyboardButton("💸 برداشت", callback_data="withdraw"),
            InlineKeyboardButton("🏦 واریز", callback_data="deposit")
        ],

        [
            InlineKeyboardButton("💎 اشتراک", callback_data="vip"),
            InlineKeyboardButton("👥 زیرمجموعه", callback_data="ref")
        ],

        [
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop"),
            InlineKeyboardButton("🏛 مزایده", callback_data="auction")
        ],

        [
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🏆 تورنمنت", callback_data="tournament")
        ],

        [
            InlineKeyboardButton("📈 آمار", callback_data="stats"),
            InlineKeyboardButton("📋 گزارش", callback_data="logs")
        ],

        [
            InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")
        ],

        [
            InlineKeyboardButton("🎁 کد هدیه", callback_data="gift"),
            InlineKeyboardButton("🎟 هدیه روزانه", callback_data="daily")
        ],

        [
            InlineKeyboardButton("📞 تیکت‌ها", callback_data="tickets"),
            InlineKeyboardButton("🚫 کاربران بن", callback_data="banned")
        ],

        [
            InlineKeyboardButton("⚙️ تنظیمات ربات", callback_data="settings")
        ],

        [
            InlineKeyboardButton("💾 بکاپ", callback_data="backup"),
            InlineKeyboardButton("♻️ بازیابی", callback_data="restore")
        ],

        [
            InlineKeyboardButton("🔒 امنیت", callback_data="security")
        ]

    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin V2",
        reply_markup=keyboard
    )
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ADMIN_ID = 6188951798


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([

        [InlineKeyboardButton("📊 داشبورد زنده", callback_data="dashboard")],

        [
            InlineKeyboardButton("👥 کاربران", callback_data="users"),
            InlineKeyboardButton("🟢 آنلاین‌ها", callback_data="online")
        ],

        [
            InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="search"),
            InlineKeyboardButton("📋 اطلاعات کاربر", callback_data="userinfo")
        ],

        [
            InlineKeyboardButton("➕ افزودن LIBER", callback_data="add_liber"),
            InlineKeyboardButton("➖ کم کردن LIBER", callback_data="remove_liber")
        ],

        [
            InlineKeyboardButton("⭐ افزودن استارز", callback_data="add_stars"),
            InlineKeyboardButton("⭐ کم کردن استارز", callback_data="remove_stars")
        ],

        [
            InlineKeyboardButton("💎 مدیریت اشتراک", callback_data="vip"),
            InlineKeyboardButton("👥 زیرمجموعه", callback_data="ref")
        ],

        [
            InlineKeyboardButton("🪙 ارز LIBER", callback_data="coin"),
            InlineKeyboardButton("📈 نوسان", callback_data="market")
        ],

        [
            InlineKeyboardButton("💸 برداشت‌ها", callback_data="withdraw"),
            InlineKeyboardButton("🏦 واریزی‌ها", callback_data="deposit")
        ],

        [
            InlineKeyboardButton("🏛 مزایده", callback_data="auction"),
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")
        ],

        [
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🏆 تورنمنت", callback_data="tournament")
        ],

        [
            InlineKeyboardButton("🎁 هدیه روزانه", callback_data="daily"),
            InlineKeyboardButton("🎫 کد هدیه", callback_data="gift")
        ],

        [
            InlineKeyboardButton("📞 تیکت‌ها", callback_data="tickets"),
            InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")
        ],

        [
            InlineKeyboardButton("🚫 بن", callback_data="ban"),
            InlineKeyboardButton("✅ رفع بن", callback_data="unban")
        ],

        [
            InlineKeyboardButton("⚠️ اخطار", callback_data="warn"),
            InlineKeyboardButton("🗑 حذف اخطار", callback_data="clear_warn")
        ],

        [
            InlineKeyboardButton("📊 آمار", callback_data="stats"),
            InlineKeyboardButton("📋 گزارش‌ها", callback_data="logs")
        ],

        [
            InlineKeyboardButton("💾 بکاپ", callback_data="backup"),
            InlineKeyboardButton("♻️ بازیابی", callback_data="restore")
        ],

        [
            InlineKeyboardButton("🔒 امنیت", callback_data="security"),
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")
        ],

        [
            InlineKeyboardButton("🔄 ریست کش", callback_data="cache"),
            InlineKeyboardButton("📦 نسخه ربات", callback_data="version")
        ]

    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin V3",
        reply_markup=keyboard
    )
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ADMIN_ID = 6188951798

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([

        [InlineKeyboardButton("👑 داشبورد حرفه‌ای", callback_data="dashboard")],

        [
            InlineKeyboardButton("👥 کاربران", callback_data="users"),
            InlineKeyboardButton("🟢 آنلاین‌ها", callback_data="online")
        ],

        [
            InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="search"),
            InlineKeyboardButton("📄 پروفایل کاربر", callback_data="profile")
        ],

        [
            InlineKeyboardButton("🪙 مدیریت LIBER", callback_data="liber"),
            InlineKeyboardButton("⭐ مدیریت استارز", callback_data="stars")
        ],

        [
            InlineKeyboardButton("💎 اشتراک‌ها", callback_data="vip"),
            InlineKeyboardButton("👥 زیرمجموعه‌ها", callback_data="ref")
        ],

        [
            InlineKeyboardButton("💸 برداشت‌ها", callback_data="withdraw"),
            InlineKeyboardButton("🏦 واریزها", callback_data="deposit")
        ],

        [
            InlineKeyboardButton("📈 نوسان ارز", callback_data="market"),
            InlineKeyboardButton("💰 مالیات", callback_data="tax")
        ],

        [
            InlineKeyboardButton("🏛 مزایده", callback_data="auction"),
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")
        ],

        [
            InlineKeyboardButton("🎮 مدیریت بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🏆 تورنمنت", callback_data="tournament")
        ],

        [
            InlineKeyboardButton("⚽ فوتبال", callback_data="football"),
            InlineKeyboardButton("🏀 بسکتبال", callback_data="basketball")
        ],

        [
            InlineKeyboardButton("🎁 هدیه روزانه", callback_data="daily"),
            InlineKeyboardButton("🎫 کد هدیه", callback_data="gift")
        ],

        [
            InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast"),
            InlineKeyboardButton("📩 پیام خصوصی", callback_data="private")
        ],

        [
            InlineKeyboardButton("📞 تیکت‌ها", callback_data="tickets"),
            InlineKeyboardButton("❓ سوالات متداول", callback_data="faq")
        ],

        [
            InlineKeyboardButton("🚫 بن", callback_data="ban"),
            InlineKeyboardButton("✅ رفع بن", callback_data="unban")
        ],

        [
            InlineKeyboardButton("⚠️ اخطار", callback_data="warn"),
            InlineKeyboardButton("🧹 حذف اخطار", callback_data="clearwarn")
        ],

        [
            InlineKeyboardButton("📊 آمار کامل", callback_data="stats"),
            InlineKeyboardButton("📋 گزارش‌ها", callback_data="logs")
        ],

        [
            InlineKeyboardButton("📂 فایل‌ها", callback_data="files"),
            InlineKeyboardButton("🗄 دیتابیس", callback_data="database")
        ],

        [
            InlineKeyboardButton("💾 بکاپ", callback_data="backup"),
            InlineKeyboardButton("♻️ بازیابی", callback_data="restore")
        ],

        [
            InlineKeyboardButton("🔐 امنیت", callback_data="security"),
            InlineKeyboardButton("👮 مدیران", callback_data="admins")
        ],

        [
            InlineKeyboardButton("⚙️ تنظیمات ربات", callback_data="settings"),
            InlineKeyboardButton("🎨 مدیریت منو", callback_data="menu")
        ],

        [
            InlineKeyboardButton("➕ ساخت دکمه", callback_data="create_button"),
            InlineKeyboardButton("✏️ ویرایش دکمه", callback_data="edit_button")
        ],

        [
            InlineKeyboardButton("🗑 حذف دکمه", callback_data="delete_button"),
            InlineKeyboardButton("📦 نسخه ربات", callback_data="version")
        ]

    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin V4",
        reply_markup=keyboard
    )
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

ADMIN_ID = 6188951798

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([

        [InlineKeyboardButton("👑 داشبورد هوشمند", callback_data="dashboard")],

        [
            InlineKeyboardButton("👥 کاربران", callback_data="users"),
            InlineKeyboardButton("🟢 آنلاین‌ها", callback_data="online")
        ],

        [
            InlineKeyboardButton("🆕 کاربران امروز", callback_data="today_users"),
            InlineKeyboardButton("📈 رشد ربات", callback_data="growth")
        ],

        [
            InlineKeyboardButton("🔍 جستجوی کاربر", callback_data="search"),
            InlineKeyboardButton("📄 پروفایل کامل", callback_data="profile")
        ],

        [
            InlineKeyboardButton("🪙 مدیریت LIBER", callback_data="liber"),
            InlineKeyboardButton("⭐ مدیریت استارز", callback_data="stars")
        ],

        [
            InlineKeyboardButton("💎 اشتراک‌ها", callback_data="vip"),
            InlineKeyboardButton("👥 زیرمجموعه‌ها", callback_data="ref")
        ],

        [
            InlineKeyboardButton("💸 برداشت TON", callback_data="withdraw"),
            InlineKeyboardButton("🏦 سفارش‌ها", callback_data="orders")
        ],

        [
            InlineKeyboardButton("📈 قیمت LIBER", callback_data="price"),
            InlineKeyboardButton("📉 نوسان", callback_data="market")
        ],

        [
            InlineKeyboardButton("💰 مالیات", callback_data="tax"),
            InlineKeyboardButton("🏦 خزانه", callback_data="bank")
        ],

        [
            InlineKeyboardButton("🏛 مزایده", callback_data="auction"),
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")
        ],

        [
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🏆 تورنمنت", callback_data="tournament")
        ],

        [
            InlineKeyboardButton("⚽ فوتبال", callback_data="football"),
            InlineKeyboardButton("🏀 بسکتبال", callback_data="basketball")
        ],

        [
            InlineKeyboardButton("🎁 هدیه روزانه", callback_data="daily"),
            InlineKeyboardButton("🎟 کد هدیه", callback_data="gift")
        ],

        [
            InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast"),
            InlineKeyboardButton("📨 پیام خصوصی", callback_data="private")
        ],

        [
            InlineKeyboardButton("📞 تیکت‌ها", callback_data="tickets"),
            InlineKeyboardButton("❓ سوالات", callback_data="faq")
        ],

        [
            InlineKeyboardButton("🚫 بن", callback_data="ban"),
            InlineKeyboardButton("✅ رفع بن", callback_data="unban")
        ],

        [
            InlineKeyboardButton("⚠️ اخطار", callback_data="warn"),
            InlineKeyboardButton("🧹 حذف اخطار", callback_data="clearwarn")
        ],

        [
            InlineKeyboardButton("📊 آمار", callback_data="stats"),
            InlineKeyboardButton("📋 گزارش", callback_data="logs")
        ],

        [
            InlineKeyboardButton("📂 فایل‌ها", callback_data="files"),
            InlineKeyboardButton("🗄 دیتابیس", callback_data="database")
        ],

        [
            InlineKeyboardButton("➕ ساخت دکمه", callback_data="create_button"),
            InlineKeyboardButton("✏️ ویرایش دکمه", callback_data="edit_button")
        ],

        [
            InlineKeyboardButton("🗑 حذف دکمه", callback_data="delete_button"),
            InlineKeyboardButton("📑 مدیریت منو", callback_data="menu")
        ],

        [
            InlineKeyboardButton("👮 مدیران", callback_data="admins"),
            InlineKeyboardButton("🔐 امنیت", callback_data="security")
        ],

        [
            InlineKeyboardButton("💾 بکاپ", callback_data="backup"),
            InlineKeyboardButton("♻️ بازیابی", callback_data="restore")
        ],

        [
            InlineKeyboardButton("🧹 پاکسازی کش", callback_data="cache"),
            InlineKeyboardButton("🔄 ریست ربات", callback_data="restart")
        ],

        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings"),
            InlineKeyboardButton("📦 نسخه ربات", callback_data="version")
        ]

    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin V5",
        reply_markup=keyboard
    )
    from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler
)

# ==========================
# Liber Coin Admin Panel V6
# بخش اول
# ==========================

ADMIN_ID = 6188951798

BOT_VERSION = "Liber Coin V6"

TOTAL_USERS = 0
ONLINE_USERS = 0
TODAY_USERS = 0
TOTAL_LIBER = 0
TOTAL_STARS = 0
PENDING_WITHDRAW = 0
OPEN_TICKETS = 0
ACTIVE_GAMES = 0


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📊 داشبورد",
                callback_data="dashboard"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="users"
            ),
            InlineKeyboardButton(
                "🔎 جستجو",
                callback_data="search"
            )
        ],

        [
            InlineKeyboardButton(
                "🪙 اقتصاد",
                callback_data="economy"
            ),
            InlineKeyboardButton(
                "⭐ استارز",
                callback_data="stars"
            )
        ],

        [
            InlineKeyboardButton(
                "💸 برداشت",
                callback_data="withdraw"
            ),
            InlineKeyboardButton(
                "🏦 سفارش‌ها",
                callback_data="orders"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 اشتراک",
                callback_data="vip"
            ),
            InlineKeyboardButton(
                "🛒 فروشگاه",
                callback_data="shop"
            )
        ],

        [
            InlineKeyboardButton(
                "🎮 بازی‌ها",
                callback_data="games"
            ),
            InlineKeyboardButton(
                "🏛 مزایده",
                callback_data="auction"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 پیام همگانی",
                callback_data="broadcast"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات",
                callback_data="settings"
            )
        ]

    ])

    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin",
        reply_markup=keyboard
    )


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🔄 بروزرسانی",
                callback_data="dashboard"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
👑 داشبورد مدیریتی

━━━━━━━━━━━━━━

🤖 نسخه
{BOT_VERSION}

━━━━━━━━━━━━━━

👥 کل کاربران
{TOTAL_USERS}

🟢 کاربران آنلاین
{ONLINE_USERS}

🆕 کاربران امروز
{TODAY_USERS}

━━━━━━━━━━━━━━

🪙 کل LIBER
{TOTAL_LIBER}

⭐ کل Stars
{TOTAL_STARS}

━━━━━━━━━━━━━━

💸 برداشت‌های انتظار
{PENDING_WITHDRAW}

📞 تیکت‌های باز
{OPEN_TICKETS}

🎮 بازی‌های فعال
{ACTIVE_GAMES}

━━━━━━━━━━━━━━

🟢 وضعیت ربات
آنلاین

━━━━━━━━━━━━━━
""",

        reply_markup=keyboard
    )


async def back_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [InlineKeyboardButton("📊 داشبورد", callback_data="dashboard")],

        [
            InlineKeyboardButton("👥 کاربران", callback_data="users"),
            InlineKeyboardButton("🔎 جستجو", callback_data="search")
        ],

        [
            InlineKeyboardButton("🪙 اقتصاد", callback_data="economy"),
            InlineKeyboardButton("⭐ استارز", callback_data="stars")
        ],

        [
            InlineKeyboardButton("💸 برداشت", callback_data="withdraw"),
            InlineKeyboardButton("🏦 سفارش‌ها", callback_data="orders")
        ],

        [
            InlineKeyboardButton("💎 اشتراک", callback_data="vip"),
            InlineKeyboardButton("🛒 فروشگاه", callback_data="shop")
        ],

        [
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="games"),
            InlineKeyboardButton("🏛 مزایده", callback_data="auction")
        ],

        [
            InlineKeyboardButton("📢 پیام همگانی", callback_data="broadcast")
        ],

        [
            InlineKeyboardButton("⚙️ تنظیمات", callback_data="settings")
        ]

    ])

    await query.edit_message_text(
        "👑 پنل مدیریت Liber Coin",
        reply_markup=keyboard
    )


admin_handler = CommandHandler("admin", admin_panel)

dashboard_handler = CallbackQueryHandler(
    dashboard,
    pattern="^dashboard$"
)

back_handler = CallbackQueryHandler(
    back_admin,
    pattern="^back_admin$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش دوم - مدیریت کاربران
# ==========================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

USER_COUNT = 0
BANNED_USERS = 0
VIP_USERS = 0


async def admin_users(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="search_user")
        ],

        [
            InlineKeyboardButton("👤 اطلاعات کاربر", callback_data="user_info")
        ],

        [
            InlineKeyboardButton("➕ افزودن LIBER", callback_data="add_liber")
        ],

        [
            InlineKeyboardButton("➖ کم کردن LIBER", callback_data="remove_liber")
        ],

        [
            InlineKeyboardButton("⭐ افزودن استارز", callback_data="add_star")
        ],

        [
            InlineKeyboardButton("⭐ کم کردن استارز", callback_data="remove_star")
        ],

        [
            InlineKeyboardButton("💎 فعال کردن اشتراک", callback_data="vip_on")
        ],

        [
            InlineKeyboardButton("❌ حذف اشتراک", callback_data="vip_off")
        ],

        [
            InlineKeyboardButton("🚫 بن کاربر", callback_data="ban")
        ],

        [
            InlineKeyboardButton("✅ رفع بن", callback_data="unban")
        ],

        [
            InlineKeyboardButton("⚠️ ثبت اخطار", callback_data="warn")
        ],

        [
            InlineKeyboardButton("🧹 حذف اخطار", callback_data="clear_warn")
        ],

        [
            InlineKeyboardButton("📩 پیام خصوصی", callback_data="private_message")
        ],

        [
            InlineKeyboardButton("🗑 حذف حساب", callback_data="delete_user")
        ],

        [
            InlineKeyboardButton("📜 تاریخچه فعالیت", callback_data="history")
        ],

        [
            InlineKeyboardButton("⬅️ بازگشت", callback_data="back_admin")
        ]

    ])

    await query.edit_message_text(
f"""
👥 مدیریت کاربران

━━━━━━━━━━━━━━

👥 کل کاربران : {USER_COUNT}

💎 کاربران VIP : {VIP_USERS}

🚫 کاربران بن شده : {BANNED_USERS}

━━━━━━━━━━━━━━

یکی از گزینه‌های زیر را انتخاب کنید.
""",
        reply_markup=keyboard
    )


users_handler = CallbackQueryHandler(
    admin_users,
    pattern="^users$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش سوم - مدیریت اقتصاد
# ==========================

LIBER_PRICE = 140
MARKET_CHANGE = "+7%"
TRANSFER_TAX = 5
WITHDRAW_TAX = 3
SHOP_STATUS = "🟢 فعال"


async def economy_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "💵 قیمت LIBER",
                callback_data="price"
            )
        ],

        [
            InlineKeyboardButton(
                "📈 افزایش قیمت",
                callback_data="price_up"
            ),
            InlineKeyboardButton(
                "📉 کاهش قیمت",
                callback_data="price_down"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 نوسان بازار",
                callback_data="market"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 مالیات انتقال",
                callback_data="transfer_tax"
            )
        ],

        [
            InlineKeyboardButton(
                "💸 مالیات برداشت",
                callback_data="withdraw_tax"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ مدیریت استارز",
                callback_data="stars"
            )
        ],

        [
            InlineKeyboardButton(
                "🏦 خزانه",
                callback_data="bank"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 موجودی فروشگاه",
                callback_data="stock"
            )
        ],

        [
            InlineKeyboardButton(
                "🛒 وضعیت فروشگاه",
                callback_data="shop_status"
            )
        ],

        [
            InlineKeyboardButton(
                "🎁 جایزه روزانه",
                callback_data="daily_reward"
            )
        ],

        [
            InlineKeyboardButton(
                "👥 پاداش زیرمجموعه",
                callback_data="ref_reward"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
🪙 مدیریت اقتصاد Liber Coin

━━━━━━━━━━━━━━

💵 قیمت هر LIBER
{LIBER_PRICE}

📈 نوسان بازار
{MARKET_CHANGE}

💰 مالیات انتقال
{TRANSFER_TAX}%

💸 مالیات برداشت
{WITHDRAW_TAX}%

🛒 فروشگاه
{SHOP_STATUS}

━━━━━━━━━━━━━━

یکی از گزینه‌های زیر را انتخاب کنید.
""",

        reply_markup=keyboard
    )


economy_handler = CallbackQueryHandler(
    economy_panel,
    pattern="^economy$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش چهارم - مدیریت برداشت‌ها
# ==========================

PENDING_WITHDRAW = 0
SUCCESS_WITHDRAW = 0
REJECT_WITHDRAW = 0
MIN_WITHDRAW = 2000
TON_RATE = 0.04


async def withdraw_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📋 درخواست‌های جدید",
                callback_data="withdraw_list"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data="withdraw_accept"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ رد برداشت",
                callback_data="withdraw_reject"
            )
        ],

        [
            InlineKeyboardButton(
                "🔍 جستجوی سفارش",
                callback_data="withdraw_search"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 سفارش‌های انجام شده",
                callback_data="withdraw_done"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 حداقل برداشت",
                callback_data="min_withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 نرخ TON",
                callback_data="ton_rate"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار برداشت",
                callback_data="withdraw_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📨 ارسال کد پیگیری",
                callback_data="tracking_code"
            )
        ],

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات برداشت",
                callback_data="withdraw_setting"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
💸 مدیریت برداشت‌ها

━━━━━━━━━━━━━━

📋 درخواست‌های جدید
{PENDING_WITHDRAW}

✅ برداشت‌های انجام شده
{SUCCESS_WITHDRAW}

❌ برداشت‌های رد شده
{REJECT_WITHDRAW}

━━━━━━━━━━━━━━

💰 حداقل برداشت
{MIN_WITHDRAW} LIBER

💎 هر برداشت
{TON_RATE} TON

━━━━━━━━━━━━━━

یکی از گزینه‌ها را انتخاب کنید.
""",

        reply_markup=keyboard
    )


withdraw_handler = CallbackQueryHandler(
    withdraw_panel,
    pattern="^withdraw$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش پنجم - مدیریت فروشگاه
# ==========================

SHOP_PRODUCTS = 0
SHOP_ENABLE = "🟢 فعال"
SHOP_ORDERS = 0


async def shop_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="shop_add"
            )
        ],

        [
            InlineKeyboardButton(
                "✏️ ویرایش محصول",
                callback_data="shop_edit"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 حذف محصول",
                callback_data="shop_delete"
            )
        ],

        [
            InlineKeyboardButton(
                "📦 لیست محصولات",
                callback_data="shop_list"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 اشتراک‌ها",
                callback_data="shop_vip"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ استارز",
                callback_data="shop_stars"
            )
        ],

        [
            InlineKeyboardButton(
                "🪙 بسته‌های LIBER",
                callback_data="shop_liber"
            )
        ],

        [
            InlineKeyboardButton(
                "🎁 کد هدیه",
                callback_data="shop_gift"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 سفارش‌ها",
                callback_data="shop_orders"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار فروش",
                callback_data="shop_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢 فعال",
                callback_data="shop_on"
            ),
            InlineKeyboardButton(
                "🔴 غیرفعال",
                callback_data="shop_off"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
🛒 مدیریت فروشگاه

━━━━━━━━━━━━━━

📦 تعداد محصولات
{SHOP_PRODUCTS}

💰 سفارش‌های امروز
{SHOP_ORDERS}

🟢 وضعیت فروشگاه
{SHOP_ENABLE}

━━━━━━━━━━━━━━

مدیریت کامل فروشگاه
Liber Coin
""",

        reply_markup=keyboard
    )


shop_handler = CallbackQueryHandler(
    shop_panel,
    pattern="^shop$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش ششم - مدیریت اشتراک‌ها
# ==========================

VIP_USERS = 0
PREMIUM_USERS = 0
LIBER_USERS = 0
EXCLUSIVE_USERS = 0


async def vip_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ فعال کردن اشتراک",
                callback_data="vip_add"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ حذف اشتراک",
                callback_data="vip_remove"
            )
        ],

        [
            InlineKeyboardButton(
                "💎 اشتراک Premium",
                callback_data="premium_manage"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 Liber Premium",
                callback_data="liber_manage"
            )
        ],

        [
            InlineKeyboardButton(
                "🔥 Exclusive",
                callback_data="exclusive_manage"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 تغییر قیمت اشتراک",
                callback_data="vip_price"
            )
        ],

        [
            InlineKeyboardButton(
                "📅 تغییر مدت اشتراک",
                callback_data="vip_time"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 لیست کاربران VIP",
                callback_data="vip_list"
            )
        ],

        [
            InlineKeyboardButton(
                "🔍 جستجوی اشتراک",
                callback_data="vip_search"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار اشتراک‌ها",
                callback_data="vip_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 پیام به کاربران VIP",
                callback_data="vip_message"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
💎 مدیریت اشتراک‌ها

━━━━━━━━━━━━━━

👤 کل کاربران VIP
{VIP_USERS}

⭐ Premium
{PREMIUM_USERS}

👑 Liber Premium
{LIBER_USERS}

🔥 Exclusive
{EXCLUSIVE_USERS}

━━━━━━━━━━━━━━

مدیریت کامل اشتراک‌ها
Liber Coin
""",

        reply_markup=keyboard
    )


vip_handler = CallbackQueryHandler(
    vip_panel,
    pattern="^vip$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش هفتم - مدیریت بازی‌ها
# ==========================

FOOTBALL_STATUS = "🟢 فعال"
BASKETBALL_STATUS = "🟢 فعال"
TOURNAMENT_STATUS = "🟢 فعال"

TOTAL_MATCHES = 0
ONLINE_MATCHES = 0
TOURNAMENTS = 0


async def games_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "⚽ مدیریت فوتبال",
                callback_data="football_panel"
            )
        ],

        [
            InlineKeyboardButton(
                "🏀 مدیریت بسکتبال",
                callback_data="basketball_panel"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 مدیریت تورنمنت",
                callback_data="tournament_panel"
            )
        ],

        [
            InlineKeyboardButton(
                "🎖 مدیریت رنک‌ها",
                callback_data="rank_panel"
            )
        ],

        [
            InlineKeyboardButton(
                "🪙 هزینه ورود بازی",
                callback_data="game_price"
            )
        ],

        [
            InlineKeyboardButton(
                "🎁 جایزه برد",
                callback_data="game_reward"
            )
        ],

        [
            InlineKeyboardButton(
                "📈 قدرت بازیکنان",
                callback_data="player_power"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار مسابقات",
                callback_data="game_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢 فعال کردن بازی",
                callback_data="game_enable"
            )
        ],

        [
            InlineKeyboardButton(
                "🔴 غیرفعال کردن بازی",
                callback_data="game_disable"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 پیام به بازیکنان",
                callback_data="game_message"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
🎮 مدیریت بازی‌ها

━━━━━━━━━━━━━━

⚽ فوتبال
{FOOTBALL_STATUS}

🏀 بسکتبال
{BASKETBALL_STATUS}

🏆 تورنمنت
{TOURNAMENT_STATUS}

━━━━━━━━━━━━━━

🎮 کل مسابقات
{TOTAL_MATCHES}

🟢 مسابقات آنلاین
{ONLINE_MATCHES}

🏆 تورنمنت‌های فعال
{TOURNAMENTS}

━━━━━━━━━━━━━━

پنل مدیریت بازی‌های Liber Coin
""",

        reply_markup=keyboard
    )


games_handler = CallbackQueryHandler(
    games_panel,
    pattern="^games$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش هشتم - مدیریت مزایده
# ==========================

ACTIVE_AUCTIONS = 0
FINISHED_AUCTIONS = 0
TOTAL_BIDS = 0
TOTAL_VOLUME = 0


async def auction_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "➕ ایجاد مزایده",
                callback_data="auction_create"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 مزایده‌های فعال",
                callback_data="auction_active"
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 پایان مزایده",
                callback_data="auction_finish"
            )
        ],

        [
            InlineKeyboardButton(
                "✏️ ویرایش مزایده",
                callback_data="auction_edit"
            )
        ],

        [
            InlineKeyboardButton(
                "🗑 حذف مزایده",
                callback_data="auction_delete"
            )
        ],

        [
            InlineKeyboardButton(
                "👑 انتخاب برنده",
                callback_data="auction_winner"
            )
        ],

        [
            InlineKeyboardButton(
                "🪙 مزایده LIBER",
                callback_data="auction_liber"
            )
        ],

        [
            InlineKeyboardButton(
                "⭐ مزایده Stars",
                callback_data="auction_star"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار مزایده",
                callback_data="auction_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "📜 تاریخچه",
                callback_data="auction_history"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 پیام به شرکت‌کنندگان",
                callback_data="auction_message"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢 فعال",
                callback_data="auction_enable"
            ),
            InlineKeyboardButton(
                "🔴 غیرفعال",
                callback_data="auction_disable"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
🏛 مدیریت مزایده

━━━━━━━━━━━━━━

🏛 مزایده فعال
{ACTIVE_AUCTIONS}

🏁 مزایده پایان یافته
{FINISHED_AUCTIONS}

📈 تعداد پیشنهادها
{TOTAL_BIDS}

🪙 حجم معاملات
{TOTAL_VOLUME}

━━━━━━━━━━━━━━

پنل مدیریت مزایده Liber Coin
""",

        reply_markup=keyboard
    )


auction_handler = CallbackQueryHandler(
    auction_panel,
    pattern="^auction$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش نهم - مدیریت پیام‌ها و پشتیبانی
# ==========================

OPEN_TICKETS = 0
CLOSED_TICKETS = 0
BROADCAST_COUNT = 0
PRIVATE_MESSAGES = 0


async def support_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📨 تیکت‌های جدید",
                callback_data="ticket_new"
            )
        ],

        [
            InlineKeyboardButton(
                "📂 تیکت‌های باز",
                callback_data="ticket_open"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ بستن تیکت",
                callback_data="ticket_close"
            )
        ],

        [
            InlineKeyboardButton(
                "🔍 جستجوی تیکت",
                callback_data="ticket_search"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 پیام همگانی",
                callback_data="broadcast"
            )
        ],

        [
            InlineKeyboardButton(
                "📩 پیام خصوصی",
                callback_data="private_message"
            )
        ],

        [
            InlineKeyboardButton(
                "📷 ارسال عکس",
                callback_data="photo_message"
            )
        ],

        [
            InlineKeyboardButton(
                "🎥 ارسال ویدیو",
                callback_data="video_message"
            )
        ],

        [
            InlineKeyboardButton(
                "📄 ارسال فایل",
                callback_data="file_message"
            )
        ],

        [
            InlineKeyboardButton(
                "📌 ارسال اطلاعیه",
                callback_data="notice"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 تاریخچه پیام‌ها",
                callback_data="message_logs"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 آمار پشتیبانی",
                callback_data="support_stats"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
📞 مدیریت پشتیبانی

━━━━━━━━━━━━━━

📨 تیکت‌های باز
{OPEN_TICKETS}

✅ تیکت‌های بسته
{CLOSED_TICKETS}

📢 پیام همگانی
{BROADCAST_COUNT}

📩 پیام خصوصی
{PRIVATE_MESSAGES}

━━━━━━━━━━━━━━

Liber Coin Support Center
""",

        reply_markup=keyboard
    )


support_handler = CallbackQueryHandler(
    support_panel,
    pattern="^support$"
)
# ==========================
# Liber Coin Admin Panel V6
# بخش دهم - تنظیمات، امنیت و سیستم
# ==========================

BOT_STATUS = "🟢 آنلاین"
MAINTENANCE = "🔴 خاموش"
JOIN_CHANNEL = "@Libercoin1"
BACKUP_STATUS = "✅ آخرین بکاپ موفق"
BOT_VERSION = "V6.0"


async def system_panel(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "⚙️ تنظیمات ربات",
                callback_data="bot_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "📢 کانال عضویت اجباری",
                callback_data="force_join"
            )
        ],

        [
            InlineKeyboardButton(
                "👮 مدیریت مدیران",
                callback_data="admins"
            )
        ],

        [
            InlineKeyboardButton(
                "🔐 امنیت ربات",
                callback_data="security"
            )
        ],

        [
            InlineKeyboardButton(
                "🚫 لیست کاربران بن",
                callback_data="ban_list"
            )
        ],

        [
            InlineKeyboardButton(
                "⚠️ لیست اخطارها",
                callback_data="warn_list"
            )
        ],

        [
            InlineKeyboardButton(
                "💾 ساخت بکاپ",
                callback_data="backup"
            )
        ],

        [
            InlineKeyboardButton(
                "♻️ بازیابی بکاپ",
                callback_data="restore"
            )
        ],

        [
            InlineKeyboardButton(
                "📂 مدیریت فایل‌ها",
                callback_data="files"
            )
        ],

        [
            InlineKeyboardButton(
                "🗄 مدیریت دیتابیس",
                callback_data="database"
            )
        ],

        [
            InlineKeyboardButton(
                "📋 لاگ مدیران",
                callback_data="admin_logs"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 وضعیت سرور",
                callback_data="server"
            )
        ],

        [
            InlineKeyboardButton(
                "🟢 روشن کردن ربات",
                callback_data="bot_on"
            ),
            InlineKeyboardButton(
                "🔴 خاموش کردن ربات",
                callback_data="bot_off"
            )
        ],

        [
            InlineKeyboardButton(
                "🧹 پاکسازی کش",
                callback_data="clear_cache"
            )
        ],

        [
            InlineKeyboardButton(
                "🔄 ریست ربات",
                callback_data="restart"
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ بازگشت",
                callback_data="back_admin"
            )
        ]

    ])

    await query.edit_message_text(

f"""
⚙️ مدیریت سیستم

━━━━━━━━━━━━━━

🤖 نسخه ربات
{BOT_VERSION}

🟢 وضعیت ربات
{BOT_STATUS}

🛠 حالت تعمیرات
{MAINTENANCE}

📢 کانال اجباری
{JOIN_CHANNEL}

💾 وضعیت بکاپ
{BACKUP_STATUS}

━━━━━━━━━━━━━━

پنل مدیریت سیستم Liber Coin
""",

        reply_markup=keyboard
    )


system_handler = CallbackQueryHandler(
    system_panel,
    pattern="^settings$"
)
