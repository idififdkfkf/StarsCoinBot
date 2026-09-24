import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler,
)

import database as db
import keyboards as kb
from captcha import build_captcha
from config import (
    FORCE_JOIN_CHANNEL, ADMIN_ID, ADMIN_SECRET_CODE, FREE_BOT_LIMIT,
    PREMIUM_BOT_LIMIT, SUBSCRIPTION_STARS_PRICE, WEBAPP_BASE_URL,
)
from payments import (
    send_subscription_invoice, precheckout_handler, successful_payment_handler,
    list_available_gifts, send_gift,
)
import bot_manager

log = logging.getLogger(__name__)

# conversation states
(WAITING_TOKEN, WAITING_BUTTON_TEXT, WAITING_BUTTON_COLOR, WAITING_BUTTON_REPLY,
 WAITING_BROADCAST, WAITING_FORCEJOIN, WAITING_GIFT_TARGET, WAITING_PHOTO,
 WAITING_UNLOCK_PRICE, WAITING_UNLOCK_TEXT) = range(10)


def _bot_limit(owner_id: int) -> int:
    base = PREMIUM_BOT_LIMIT if db.is_premium(owner_id) else FREE_BOT_LIMIT
    return base + db.get_bonus_slots(owner_id)


# ---------------- join / captcha gate ----------------
async def _is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    if not FORCE_JOIN_CHANNEL:
        return True
    try:
        member = await context.bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


async def _gate_and_show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False):
    user = update.effective_user
    if not await _is_member(context, user.id):
        text = "برای استفاده از ربات، اول باید توی کانال ما عضو بشی 👇"
        markup = kb.force_join_keyboard(FORCE_JOIN_CHANNEL)
        if edit:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.message.reply_text(text, reply_markup=markup)
        return

    row = db.get_user(user.id)
    if not row or not row["captcha_passed"]:
        text, correct, markup = build_captcha()
        context.user_data["captcha_answer"] = correct
        if edit:
            await update.callback_query.edit_message_text(text, reply_markup=markup)
        else:
            await update.message.reply_text(text, reply_markup=markup)
        return

    text = "منوی اصلی 🤖\nاز دکمه‌های زیر یکی رو انتخاب کن:"
    if edit:
        await update.callback_query.edit_message_text(text, reply_markup=kb.main_menu_keyboard())
    else:
        await update.message.reply_text(text, reply_markup=kb.main_menu_keyboard())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    referred_by = None
    if context.args and context.args[0].startswith("ref"):
        try:
            referred_by = int(context.args[0][3:])
        except ValueError:
            pass
    is_new = db.upsert_user(user.id, user.username or "", referred_by)
    if is_new and referred_by and referred_by != user.id:
        db.add_bonus_slot(referred_by, 1)
        try:
            await context.bot.send_message(
                referred_by,
                "🎉 یک نفر با لینک دعوت تو وارد شد! یک ظرفیت ربات رایگان اضافه بهت اضافه شد.",
            )
        except Exception:
            pass
    await _gate_and_show_menu(update, context, edit=False)


async def check_join_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not await _is_member(context, query.from_user.id):
        await query.answer("هنوز عضو نشدی!", show_alert=True)
        return
    await _gate_and_show_menu(update, context, edit=True)


async def captcha_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, chosen, correct = query.data.split(":")
    if chosen != correct:
        await query.answer("❌ غلطه، دوباره امتحان کن", show_alert=True)
        text, correct_new, markup = build_captcha()
        context.user_data["captcha_answer"] = correct_new
        await query.edit_message_text(text, reply_markup=markup)
        return
    db.set_captcha_passed(query.from_user.id)
    await query.answer("✅ تایید شد")
    await query.edit_message_text(
        "منوی اصلی 🤖\nاز دکمه‌های زیر یکی رو انتخاب کن:", reply_markup=kb.main_menu_keyboard()
    )


async def back_main_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "منوی اصلی 🤖\nاز دکمه‌های زیر یکی رو انتخاب کن:", reply_markup=kb.main_menu_keyboard()
    )


async def referral_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    me = await context.bot.get_me()
    uid = query.from_user.id
    link = f"https://t.me/{me.username}?start=ref{uid}"
    invited = db.count_referrals(uid)
    bonus = db.get_bonus_slots(uid)
    await query.edit_message_text(
        f"🔗 لینک دعوت تو:\n{link}\n\n"
        f"👥 تعداد دعوت‌شده‌ها: {invited}\n"
        f"🎁 ظرفیت رایگان اضافه‌شده: {bonus} ربات\n\n"
        "به‌ازای هر نفری که با این لینک وارد بشه، یک ظرفیت ربات رایگان بیشتر می‌گیری.",
        reply_markup=kb.main_menu_keyboard(),
    )


# ---------------- create bot ----------------
async def create_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    owner_id = query.from_user.id
    limit = _bot_limit(owner_id)
    if db.count_user_bots(owner_id) >= limit:
        await query.edit_message_text(
            f"❌ به سقف {limit} ربات رسیدی. برای ساخت بیشتر، اشتراک ویژه بگیر یا دوستاتو با لینک دعوت بیار.",
            reply_markup=kb.subscription_keyboard(SUBSCRIPTION_STARS_PRICE),
        )
        return ConversationHandler.END
    await query.edit_message_text(
        "توکن ربات رو بفرست.\n\n"
        "راهنما: به @BotFather پیام بده، /newbot بزن، بعد توکنی که میده رو اینجا پیست کن."
    )
    return WAITING_TOKEN


async def create_bot_receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    owner_id = update.effective_user.id
    if db.get_bot_by_token(token):
        await update.message.reply_text("این توکن قبلاً ثبت شده. یه توکن دیگه بفرست یا /cancel بزن.")
        return WAITING_TOKEN

    info = await bot_manager.validate_token(token)
    if not info:
        await update.message.reply_text("❌ توکن معتبر نیست. دوباره امتحان کن یا /cancel بزن.")
        return WAITING_TOKEN

    bot_id = db.create_child_bot(owner_id, token, info.username)
    await bot_manager.start_child_bot(bot_id, token)
    panel_url = f"https://t.me/{info.username}?start=panel"
    await update.message.reply_text(
        f"✅ ربات @{info.username} با موفقیت ساخته و روشن شد!\n\n"
        "قدم بعدی — برو به «📂 ربات‌های من» و:\n"
        "۱. چند تا دکمه اضافه کن (➕ افزودن دکمه)\n"
        "۲. نوع کیبورد رو انتخاب کن (شیشه‌ای/پایین صفحه/منو/رنگی)\n"
        "۳. اگه خواستی، عضویت اجباری یا محتوای قفل‌شده هم تنظیم کن\n"
        "همین! ربات‌ت همین الان برای کاربرا فعاله.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⚙️ باز کردن پنل مدیریت همین ربات", url=panel_url)],
            [InlineKeyboardButton("⬅️ منوی اصلی", callback_data="back_main")],
        ]),
    )
    return ConversationHandler.END


# ---------------- my bots / manage ----------------
async def my_bots_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bots = db.get_user_bots(query.from_user.id)
    if not bots:
        await query.edit_message_text(
            "هنوز رباتی نساختی.", reply_markup=kb.main_menu_keyboard()
        )
        return
    await query.edit_message_text("ربات‌های تو:", reply_markup=kb.my_bots_keyboard(query.from_user.id))


async def bot_menu_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    await query.edit_message_text(
        f"مدیریت ربات @{row['username']}",
        reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
    )


async def toggle_active_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    new_state = not bool(row["is_active"])
    db.set_bot_active(bot_id, new_state)
    if new_state:
        await bot_manager.start_child_bot(bot_id, row["token"])
    else:
        await bot_manager.stop_child_bot(bot_id)
    await query.answer("انجام شد")
    row = db.get_bot(bot_id)
    await query.edit_message_text(
        f"مدیریت ربات @{row['username']}",
        reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
    )


async def toggle_reactions_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    db.toggle_reactions(bot_id)
    await query.answer("انجام شد")
    row = db.get_bot(bot_id)
    await query.edit_message_text(
        f"مدیریت ربات @{row['username']}",
        reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
    )


async def delete_bot_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    await bot_manager.stop_child_bot(bot_id)
    db.delete_bot(bot_id)
    await query.answer("ربات حذف شد")
    await query.edit_message_text("ربات‌های تو:", reply_markup=kb.my_bots_keyboard(query.from_user.id))


async def bot_stats_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    count = db.count_bot_subscribers(bot_id)
    await query.answer(f"👤 تعداد کاربران: {count}", show_alert=True)


# ---------------- add button flow ----------------
async def add_button_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["target_bot_id"] = bot_id
    await query.edit_message_text("متن دکمه رو بفرست (چیزی که روی دکمه نوشته میشه):")
    return WAITING_BUTTON_TEXT


async def add_button_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_button_text"] = update.message.text.strip()
    await update.message.reply_text(
        "یک رنگ برای دکمه انتخاب کن (نزدیک‌ترین چیزی که تلگرام اجازه میده — یک ایموجی رنگی کنار متن):",
        reply_markup=kb.color_picker_keyboard(),
    )
    return WAITING_BUTTON_COLOR


async def add_button_color_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    color_name = query.data.split(":", 1)[1]
    emoji, hex_color = kb.BUTTON_COLORS.get(color_name, ("", "#2AABEE"))
    context.user_data["new_button_color"] = emoji
    context.user_data["new_button_hex"] = hex_color
    await query.edit_message_text("حالا متن پاسخی که وقتی کاربر دکمه رو زد نشون داده بشه رو بفرست:")
    return WAITING_BUTTON_REPLY


async def add_button_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.user_data["target_bot_id"]
    raw_text = context.user_data.pop("new_button_text")
    emoji = context.user_data.pop("new_button_color", "")
    hex_color = context.user_data.pop("new_button_hex", "#2AABEE")
    text = f"{emoji} {raw_text}".strip() if emoji else raw_text
    reply_text = update.message.text.strip()
    db.add_button(bot_id, text, reply_text, hex_color)
    await bot_manager.refresh_child_keyboard(bot_id)
    await update.message.reply_text("✅ دکمه اضافه شد.")
    return ConversationHandler.END


async def list_buttons_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    buttons = db.get_buttons(bot_id)
    if not buttons:
        await query.answer("هنوز دکمه‌ای اضافه نکردی", show_alert=True)
        return
    text = "\n".join(f"• {b['text']}" for b in buttons)
    await query.answer()
    await query.message.reply_text(f"دکمه‌های این ربات:\n{text}")


# ---------------- broadcast flow ----------------
async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["broadcast_bot_id"] = bot_id
    await query.edit_message_text("متن پیام همگانی رو بفرست تا برای همه‌ی کاربرای این ربات ارسال بشه:")
    return WAITING_BROADCAST


async def broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.user_data.pop("broadcast_bot_id")
    text = update.message.text
    sent, failed = await bot_manager.broadcast(bot_id, text)
    await update.message.reply_text(f"📣 ارسال شد به {sent} نفر (ناموفق: {failed})")
    return ConversationHandler.END


# ---------------- force join config flow ----------------
async def set_forcejoin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["forcejoin_bot_id"] = bot_id
    await query.edit_message_text(
        "یوزرنیم کانالی که کاربرا باید عضوش باشن رو بفرست (مثلا @mychannel).\n"
        "برای غیرفعال کردن، کلمه‌ی «خاموش» رو بفرست."
    )
    return WAITING_FORCEJOIN


async def set_forcejoin_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.user_data.pop("forcejoin_bot_id")
    text = update.message.text.strip()
    channel = "" if text in ("خاموش", "off", "-") else text
    db.set_force_join(bot_id, channel)
    await update.message.reply_text("✅ تنظیم شد.")
    return ConversationHandler.END


# ---------------- send gift flow ----------------
async def send_gift_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["gift_bot_id"] = bot_id
    await query.edit_message_text(
        "آیدی عددی کاربری که می‌خوای بهش هدیه بدی رو بفرست (نه یوزرنیم، آیدی عددیش رو — "
        "کاربر باید قبلاً /start ربات تو رو زده باشه).\n\n"
        "⚠️ هدیه از موجودی استارز خودِ این ربات کم میشه، نه از حساب تو."
    )
    return WAITING_GIFT_TARGET


async def send_gift_receive_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.user_data["gift_bot_id"]
    try:
        target_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("آیدی باید عدد باشه. دوباره بفرست یا /cancel بزن.")
        return WAITING_GIFT_TARGET

    context.user_data["gift_target_id"] = target_id
    bot_instance = await bot_manager.get_bot_instance(bot_id)
    if not bot_instance:
        await update.message.reply_text("ربات پیدا نشد.")
        return ConversationHandler.END

    try:
        gifts = await list_available_gifts(bot_instance)
    except Exception as e:
        await update.message.reply_text(f"❌ نشد لیست هدیه‌ها رو بگیرم: {e}")
        return ConversationHandler.END

    if not gifts:
        await update.message.reply_text("در حال حاضر هدیه‌ای برای ارسال موجود نیست.")
        return ConversationHandler.END

    await update.message.reply_text(
        "یکی از هدیه‌های زیر رو انتخاب کن (بر اساس تعداد استارز):",
        reply_markup=kb.gift_pick_keyboard(bot_id, gifts),
    )
    return ConversationHandler.END


async def pick_gift_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, bot_id_s, gift_id = query.data.split(":", 2)
    bot_id = int(bot_id_s)
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    target_id = context.user_data.get("gift_target_id")
    if not target_id:
        await query.answer("این درخواست منقضی شده، دوباره از اول شروع کن.", show_alert=True)
        return
    bot_instance = await bot_manager.get_bot_instance(bot_id)
    try:
        await send_gift(bot_instance, gift_id, target_id)
        await query.answer("🎁 هدیه ارسال شد!", show_alert=True)
        await query.edit_message_text("✅ هدیه با موفقیت ارسال شد.")
    except Exception as e:
        await query.answer("ناموفق", show_alert=True)
        await query.edit_message_text(
            f"❌ ارسال هدیه ناموفق بود — احتمالاً موجودی استارز ربات کافی نیست.\n{e}"
        )


# ---------------- keyboard style ----------------
async def kbstyle_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    await query.edit_message_text(
        "نوع کیبورد این ربات رو انتخاب کن:", reply_markup=kb.keyboard_style_pick_keyboard(bot_id)
    )


async def setkb_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    _, bot_id_s, style = query.data.split(":")
    bot_id = int(bot_id_s)
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return
    if style == "webapp" and not WEBAPP_BASE_URL:
        await query.answer(
            "اول باید WEBAPP_BASE_URL رو توی تنظیمات Railway ست کنی (README رو ببین).",
            show_alert=True,
        )
        return
    was_menu = row["keyboard_style"] == "menu"
    db.set_keyboard_style(bot_id, style)
    if style == "menu":
        await bot_manager.refresh_child_keyboard(bot_id)
    elif was_menu:
        bot_instance = await bot_manager.get_bot_instance(bot_id)
        if bot_instance:
            import child_bot
            await child_bot.reset_menu_button(bot_instance)
    await query.answer("✅ ذخیره شد")
    row = db.get_bot(bot_id)
    await query.edit_message_text(
        f"مدیریت ربات @{row['username']}",
        reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
    )


# ---------------- welcome photo ----------------
async def set_photo_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["photo_bot_id"] = bot_id
    await query.edit_message_text("یک عکس بفرست تا به‌عنوان عکس خوش‌آمدگویی ذخیره بشه:")
    return WAITING_PHOTO


async def set_photo_receive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("لطفاً یک عکس بفرست، یا /cancel بزن.")
        return WAITING_PHOTO
    bot_id = context.user_data.pop("photo_bot_id")
    file_id = update.message.photo[-1].file_id
    db.set_welcome_photo(bot_id, file_id)
    await update.message.reply_text("✅ عکس خوش‌آمد ذخیره شد.")
    return ConversationHandler.END


# ---------------- paid unlock content ----------------
async def set_unlock_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bot_id = int(query.data.split(":")[1])
    row = db.get_bot(bot_id)
    if not row or row["owner_id"] != query.from_user.id:
        await query.answer("دسترسی نداری", show_alert=True)
        return ConversationHandler.END
    context.user_data["unlock_bot_id"] = bot_id
    await query.edit_message_text(
        "قیمت محتوای قفل‌شده رو به تعداد استارز بفرست (فقط عدد، مثلاً 50):"
    )
    return WAITING_UNLOCK_PRICE


async def set_unlock_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = int(update.message.text.strip())
        if price < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("باید یک عدد مثبت باشه. دوباره بفرست یا /cancel بزن.")
        return WAITING_UNLOCK_PRICE
    context.user_data["unlock_price"] = price
    await update.message.reply_text(
        "حالا متنی که بعد از پرداخت برای کاربر ارسال بشه رو بفرست:"
    )
    return WAITING_UNLOCK_TEXT


async def set_unlock_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.user_data.pop("unlock_bot_id")
    price = context.user_data.pop("unlock_price")
    text = update.message.text
    db.set_unlock(bot_id, price, text)
    await update.message.reply_text(
        f"✅ فعال شد. کاربرا با زدن /unlock توی ربات، با {price} استارز بازش می‌کنن."
    )
    return ConversationHandler.END


async def cancel_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("لغو شد.")
    return ConversationHandler.END


# ---------------- subscription ----------------
async def subscription_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💎 با اشتراک ویژه:\n"
        f"• تا {PREMIUM_BOT_LIMIT} ربات بساز (به‌جای {FREE_BOT_LIMIT} تا)\n"
        "• یک ماه اعتبار\n",
        reply_markup=kb.subscription_keyboard(SUBSCRIPTION_STARS_PRICE),
    )


async def buy_subscription_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_subscription_invoice(query.from_user.id, context)


# ---------------- hidden admin panel (first-claim) ----------------
def is_admin(user_id: int) -> bool:
    if ADMIN_ID and user_id == ADMIN_ID:
        return True
    claimed = db.get_setting("admin_user_id")
    return claimed is not None and int(claimed) == user_id


async def admin_claim(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Triggered by the literal command /<ADMIN_SECRET_CODE> (default
    /kd7d7). First person ever to send it claims the admin panel forever;
    anyone else sending it later gets no visible reaction at all — the bot
    just looks like it ignored an unknown command."""
    user_id = update.effective_user.id
    claimed = db.get_setting("admin_user_id")

    if claimed is None:
        db.set_setting("admin_user_id", str(user_id))
        await update.message.reply_text(
            "✅ این آیدی برای همیشه به‌عنوان ادمین اصلی این ربات ثبت شد.\n"
            "از این به بعد فقط با همین کد، از همین آیدی، پنل مدیریت رو می‌بینی."
        )
    elif int(claimed) != user_id and not (ADMIN_ID and user_id == ADMIN_ID):
        return  # someone else trying the code — pretend nothing happened

    total_users = len(db.all_user_ids())
    await update.message.reply_text(
        "🛠 پنل مدیریت\n"
        f"👤 کاربران کل: {total_users}\n\n"
        "برای پیام همگانی به همه‌ی کاربران فکتوری، دستور زیر رو بزن:\n"
        "/broadcastall <متن پیام>"
    )


async def broadcast_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    text = update.message.text.partition(" ")[2]
    if not text:
        await update.message.reply_text("استفاده: /broadcastall متن پیام")
        return
    ids = db.all_user_ids()
    sent = 0
    for uid in ids:
        try:
            await context.bot.send_message(uid, text)
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"ارسال شد به {sent} کاربر.")


def build_application(token: str) -> Application:
    app = Application.builder().token(token).build()

    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_bot_start, pattern="^create_bot$"),
            CallbackQueryHandler(add_button_start, pattern=r"^add_button:\d+$"),
            CallbackQueryHandler(broadcast_start, pattern=r"^broadcast:\d+$"),
            CallbackQueryHandler(set_forcejoin_start, pattern=r"^set_forcejoin:\d+$"),
            CallbackQueryHandler(send_gift_start, pattern=r"^send_gift:\d+$"),
            CallbackQueryHandler(set_photo_start, pattern=r"^set_photo:\d+$"),
            CallbackQueryHandler(set_unlock_start, pattern=r"^set_unlock:\d+$"),
        ],
        states={
            WAITING_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_bot_receive_token)],
            WAITING_BUTTON_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_text)],
            WAITING_BUTTON_COLOR: [CallbackQueryHandler(add_button_color_cb, pattern=r"^pickcolor:")],
            WAITING_BUTTON_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_button_reply)],
            WAITING_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_send)],
            WAITING_FORCEJOIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_forcejoin_receive)],
            WAITING_GIFT_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_gift_receive_target)],
            WAITING_PHOTO: [MessageHandler(filters.PHOTO, set_photo_receive)],
            WAITING_UNLOCK_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_unlock_price)],
            WAITING_UNLOCK_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_unlock_text)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conv)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcastall", broadcast_all_cmd))
    app.add_handler(CommandHandler(ADMIN_SECRET_CODE, admin_claim))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(check_join_cb, pattern="^check_join$"))
    app.add_handler(CallbackQueryHandler(captcha_cb, pattern=r"^captcha:"))
    app.add_handler(CallbackQueryHandler(back_main_cb, pattern="^back_main$"))
    app.add_handler(CallbackQueryHandler(my_bots_cb, pattern="^my_bots$"))
    app.add_handler(CallbackQueryHandler(referral_cb, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(bot_menu_cb, pattern=r"^bot_menu:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_active_cb, pattern=r"^toggle_active:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_reactions_cb, pattern=r"^toggle_reactions:\d+$"))
    app.add_handler(CallbackQueryHandler(delete_bot_cb, pattern=r"^delete_bot:\d+$"))
    app.add_handler(CallbackQueryHandler(bot_stats_cb, pattern=r"^bot_stats:\d+$"))
    app.add_handler(CallbackQueryHandler(kbstyle_cb, pattern=r"^kbstyle:\d+$"))
    app.add_handler(CallbackQueryHandler(setkb_cb, pattern=r"^setkb:"))
    app.add_handler(CallbackQueryHandler(list_buttons_cb, pattern=r"^list_buttons:\d+$"))
    app.add_handler(CallbackQueryHandler(pick_gift_cb, pattern=r"^pickgift:"))
    app.add_handler(CallbackQueryHandler(subscription_cb, pattern="^subscription$"))
    app.add_handler(CallbackQueryHandler(buy_subscription_cb, pattern="^buy_subscription$"))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    from telegram.ext import PreCheckoutQueryHandler
    app.add_handler(PreCheckoutQueryHandler(precheckout_handler))

    return app
