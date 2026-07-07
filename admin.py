ADMIN_ID = 6188951798


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user = update.effective_user

    # فقط مدیر اصلی
    if user.id != ADMIN_ID:
        await update.message.reply_text(
            "❌ شما دسترسی به پنل مدیریت ندارید."
        )
        return


    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "📊 داشبورد",
                callback_data="admin_dashboard"
            )
        ],
        [
            InlineKeyboardButton(
                "👥 کاربران",
                callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                "🪙 مدیریت LIBER",
                callback_data="admin_liber"
            )
        ],
        [
            InlineKeyboardButton(
                "💸 برداشت‌ها",
                callback_data="admin_withdraw"
            )
        ]
    ])


    await update.message.reply_text(
        "👑 پنل مدیریت Liber Coin\n\nفقط برای مدیر اصلی فعال است.",
        reply_markup=keyboard
    )# =========================
# بخش مدیریت کاربران
# =========================

users_db = {}


async def admin_users_menu(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 جستجوی کاربر",
                callback_data="search_user"
            )
        ],
        [
            InlineKeyboardButton(
                "➕ افزودن LIBER",
                callback_data="add_liber"
            )
        ],
        [
            InlineKeyboardButton(
                "➖ کم کردن LIBER",
                callback_data="remove_liber"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ مدیریت استارز",
                callback_data="manage_stars"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_admin"
            )
        ]
    ])

    await query.edit_message_text(
        """
👥 مدیریت کاربران

یک گزینه را انتخاب کنید:
""",
        reply_markup=keyboard
    )



# =========================
# مدیریت LIBER
# =========================


async def liber_manager(update, context):

    query = update.callback_query

    await query.answer()


    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📈 قیمت LIBER",
                callback_data="liber_price"
            )
        ],

        [
            InlineKeyboardButton(
                "📊 نوسان ارز",
                callback_data="liber_change"
            )
        ],

        [
            InlineKeyboardButton(
                "💰 مالیات",
                callback_data="tax_settings"
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_admin"
            )
        ]

    ])


    await query.edit_message_text(
        """
🪙 مدیریت ارز LIBER

تنظیمات ارز:
""",
        reply_markup=keyboard
    )



# =========================
# مدیریت برداشت
# =========================


async def withdraw_manager(update, context):

    query = update.callback_query

    await query.answer()


    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "⏳ درخواست‌های جدید",
                callback_data="pending_withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "✅ تایید برداشت",
                callback_data="accept_withdraw"
            )
        ],

        [
            InlineKeyboardButton(
                "❌ رد برداشت",
    # =========================
# بخش مدیریت کاربران
# =========================

users_db = {}


async def admin_users_menu(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "🔎 جستجوی کاربر",
                callback_data="search_user"
            )
        ],
        [
            InlineKeyboardButton(
                "➕ افزودن LIBER",
                callback_data="add_liber"
            )
        ],
        [
            InlineKeyboardButton(
                "➖ کم کردن LIBER",
                callback_data="remove_liber"
            )
        ],
        [
            InlineKeyboardButton(
                "⭐ مدیریت استارز",
                callback_data="manage_stars"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_admin"
            )
        ]
    ])

    await query.edit_message_text(
        """
👥 مدیریت کاربران

یک گزینه را انتخاب کنید:
""",
        reply_markup=keyboard
    )



# =========================
# مدیریت LIBER
# =========================


async def liber_manager(update, context):

    query = update.callback_query

    await query.answer()


    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📈 قیمت LIBER",
                callback_data="liber_price"
            )
        ],

        [
            Inline
    # =========================
# فروشگاه مدیریت
# =========================

async def shop_manager(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "➕ افزودن محصول",
                callback_data="add_product"
            )
        ],
        [
            InlineKeyboardButton(
                "✏️ ویرایش محصول",
                callback_data="edit_product"
            )
        ],
        [
            InlineKeyboardButton(
                "🗑 حذف محصول",
                callback_data="delete_product"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_admin"
            )
        ]
    ])

    await query.edit_message_text(
"""
🛒 مدیریت فروشگاه

محصولات:
💎 اشتراک
⭐ استارز
🪙 بسته‌های LIBER
🎁 آیتم‌ها
""",
        reply_markup=keyboard
    )



# =========================
# مدیریت اشتراک
# =========================

async def vip_manager(update, context):

    query = update.callback_query
    await query.answer()

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "💎 فعال‌سازی اشتراک",
                callback_data="vip_on"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ حذف اشتراک",
                callback_data="vip_off"
            )
        ],
        [
            InlineKeyboardButton(
                "📋 لیست VIP ها",
                callback_data="vip_list"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگشت",
                callback_data="back_admin"
            )
        ]
    ])

    await query.edit_message_text(
"""
💎 مدیریت اشتراک‌ها

Premium
Liber Premium
Exclusive
""",
        reply_markup=keyboard
    )



# =========================
# پیام همگانی
# =========================

async def broadcast_manager(update, context):

    query = update.callback_query
    await query.answer()


    await query.edit_message_text(
"""
📢 پیام همگانی

وضعیت:
آماده ارسال

فرمت:
متن پیام را وارد کنید.
سپس برای همه کاربران ارسال می‌شود.
"""
    )



# =========================
# مدیریت بازی‌ها
# =========================

async def game_manager(update, context):

    query = update.callback_query
    await query.answer()


    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "⚽ فوتبال",
                callback_data="football_settings"
            )
        ],
        [
            InlineKeyboardButton(
                "🏀 بسکتبال",
                callback_data="basket_settings"
            )
        ],
        [
            InlineKeyboardButton(
                "🏆 تورنمنت",
                callback_data="tournament_settings"
            )
        ],
        [
            InlineKeyboardButton(
                "🔙 برگ
    
