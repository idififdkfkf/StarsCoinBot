import json

from telegram import Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler,
    PreCheckoutQueryHandler, filters, ContextTypes,
)

import database as db
import keyboards as kb
from config import WEBAPP_BASE_URL


async def _is_member(context: ContextTypes.DEFAULT_TYPE, channel: str, user_id: int) -> bool:
    if not channel:
        return True
    try:
        member = await context.bot.get_chat_member(channel, user_id)
        return member.status in (
            ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER,
        )
    except Exception:
        return False


def make_start_handler(bot_id: int):
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        row = db.get_bot(bot_id)
        if not row:
            return
        user = update.effective_user

        # Deep-link shortcut (t.me/<bot>?start=panel) straight into the
        # owner's admin panel — only works for the actual owner.
        if context.args and context.args[0] == "panel":
            if user.id == row["owner_id"]:
                await update.message.reply_text(
                    f"پنل مدیریت @{row['username']}",
                    reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
                )
            return

        if db.is_blocked(bot_id, user.id):
            return  # silently ignore blocked users

        db.add_bot_subscriber(bot_id, user.id)

        if row["force_join_channel"] and not await _is_member(context, row["force_join_channel"], user.id):
            await update.message.reply_text(
                "برای استفاده از این ربات، اول باید عضو کانال بشی 👇",
                reply_markup=kb.force_join_keyboard(row["force_join_channel"]),
            )
            return

        if row["keyboard_style"] == "reply":
            markup = kb.child_main_reply_keyboard(bot_id)
        elif row["keyboard_style"] == "menu":
            markup = None  # options live in the ☰ menu button next to the text box
        elif row["keyboard_style"] == "webapp" and WEBAPP_BASE_URL:
            markup = InlineKeyboardMarkup([[InlineKeyboardButton(
                "🎨 باز کردن منو", web_app=WebAppInfo(url=f"{WEBAPP_BASE_URL}/app/{bot_id}")
            )]])
        else:
            markup = kb.child_main_keyboard(bot_id)

        text = row["welcome_text"]
        if row["keyboard_style"] == "menu":
            text += "\n\nℹ️ گزینه‌ها رو از دکمه‌ی ☰ کنار جعبه‌ی تایپ ببین."

        if row["welcome_photo"]:
            await update.message.reply_photo(row["welcome_photo"], caption=text, reply_markup=markup)
        else:
            await update.message.reply_text(text, reply_markup=markup)
    return start


def make_menu_button_command_handler(bot_id: int, button_id: int):
    """Each button becomes a real Telegram slash-command (Bot API commands
    can't contain Persian letters, so we use btn<id> and put the actual
    Persian label in the command's *description*, which is what shows up
    next to it in the ☰ menu)."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.is_blocked(bot_id, update.effective_user.id):
            return
        await _send_button_reply(bot_id, button_id, update.message)
    return handler


async def apply_menu_commands(bot, bot_id: int):
    """Pushes the bot's buttons as commands into Telegram's native ☰ menu
    button (setChatMenuButton + setMyCommands) — the real Bot API feature
    for a menu next to the text box, as opposed to a keyboard under a message."""
    from telegram import BotCommand, MenuButtonCommands
    buttons = db.get_buttons(bot_id)
    commands = [BotCommand("start", "شروع")]
    for b in buttons[:99]:  # Telegram allows at most 100 bot commands
        commands.append(BotCommand(f"btn{b['id']}", (b["text"] or "گزینه")[:256]))
    try:
        await bot.set_my_commands(commands)
        await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    except Exception:
        pass


async def reset_menu_button(bot):
    """Restores Telegram's default ☰ menu button — used when an owner
    switches a bot away from the 'menu' keyboard style."""
    from telegram import MenuButtonDefault
    try:
        await bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    except Exception:
        pass


def register_menu_button_commands(app, bot_id: int):
    """Adds a CommandHandler for every button not yet registered on this
    running Application — safe to call again after new buttons are added."""
    registered = app.bot_data.setdefault("registered_btn_ids", set())
    for b in db.get_buttons(bot_id):
        if b["id"] in registered:
            continue
        app.add_handler(CommandHandler(f"btn{b['id']}", make_menu_button_command_handler(bot_id, b["id"])))
        registered.add(b["id"])


def make_button_handler(bot_id: int):
    """Handles inline-keyboard button presses (callback_data based)."""
    async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        button_id = int(query.data.split(":")[1])
        await _send_button_reply(bot_id, button_id, query.message)
    return on_button


def make_reply_text_handler(bot_id: int):
    """Handles taps on a persistent bottom (reply) keyboard — these arrive
    as plain text messages matching a button's label, not callback_data."""
    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        row = db.get_bot(bot_id)
        if not row or row["keyboard_style"] != "reply":
            return
        if db.is_blocked(bot_id, update.effective_user.id):
            return
        text = update.message.text
        buttons = db.get_buttons(bot_id)
        match = next((b for b in buttons if b["text"] == text), None)
        if not match:
            return
        await _send_button_reply(bot_id, match["id"], update.message)
    return on_text


async def _send_button_reply(bot_id: int, button_id: int, message):
    buttons = db.get_buttons(bot_id)
    match = next((b for b in buttons if b["id"] == button_id), None)
    if not match:
        return
    row = db.get_bot(bot_id)
    msg = await message.reply_text(match["reply_text"])
    if row and row["reactions_enabled"]:
        await msg.edit_reply_markup(kb.child_reaction_keyboard(bot_id, msg.message_id, {}))


def make_reaction_handler(bot_id: int):
    async def on_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        _, _bid, message_id, emoji = query.data.split(":")
        message_id = int(message_id)
        db.bump_reaction(bot_id, query.message.chat_id, message_id, emoji)
        await query.answer(f"{emoji} +1")
        # re-read all emoji counts for this message so the row shows totals
        counts = {}
        with db.cursor() as cur:
            cur.execute(
                "SELECT emoji, count FROM reactions WHERE bot_id=? AND chat_id=? AND message_id=?",
                (bot_id, query.message.chat_id, message_id),
            )
            for r in cur.fetchall():
                counts[r["emoji"]] = r["count"]
        await query.edit_message_reply_markup(kb.child_reaction_keyboard(bot_id, message_id, counts))
    return on_reaction


def make_panel_handler(bot_id: int):
    """Owner-only /panel command inside their own child bot — reuses the
    factory bot's management keyboard so owners don't need to leave the
    child bot to manage it."""
    async def panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        row = db.get_bot(bot_id)
        if not row or update.effective_user.id != row["owner_id"]:
            return
        await update.message.reply_text(
            f"پنل مدیریت @{row['username']}",
            reply_markup=kb.bot_manage_keyboard(bot_id, bool(row["is_active"]), bool(row["reactions_enabled"])),
        )
    return panel


def make_block_handler(bot_id: int, block: bool):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        row = db.get_bot(bot_id)
        if not row or update.effective_user.id != row["owner_id"]:
            return
        if not context.args:
            await update.message.reply_text("استفاده: /block آیدی_عددی  یا  /unblock آیدی_عددی")
            return
        try:
            target = int(context.args[0])
        except ValueError:
            await update.message.reply_text("آیدی باید عدد باشه.")
            return
        if block:
            db.block_user(bot_id, target)
            await update.message.reply_text(f"🚫 کاربر {target} مسدود شد.")
        else:
            db.unblock_user(bot_id, target)
            await update.message.reply_text(f"✅ کاربر {target} آزاد شد.")
    return handler


def make_unlock_handler(bot_id: int):
    """/unlock — lets any user buy this child bot's paid content with Stars."""
    async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
        row = db.get_bot(bot_id)
        if not row or not row["unlock_price_stars"]:
            await update.message.reply_text("محتوای قفل‌شده‌ای برای این ربات تعریف نشده.")
            return
        user_id = update.effective_user.id
        if db.has_unlocked(bot_id, user_id):
            await update.message.reply_text(row["unlock_text"])
            return
        await context.bot.send_invoice(
            chat_id=update.effective_chat.id,
            title="باز کردن محتوای ویژه",
            description="با پرداخت زیر، محتوای ویژه این ربات برات باز میشه.",
            payload=f"unlock:{bot_id}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice("محتوای ویژه", row["unlock_price_stars"])],
        )
    return unlock


async def _precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


def make_successful_payment_handler(bot_id: int):
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        payload = update.message.successful_payment.invoice_payload
        if payload != f"unlock:{bot_id}":
            return
        row = db.get_bot(bot_id)
        db.mark_unlocked(bot_id, update.effective_user.id)
        await update.message.reply_text(f"✅ باز شد!\n\n{row['unlock_text']}")
    return handler


def make_webapp_data_handler(bot_id: int):
    """Handles the payload sent back by the Mini App (webapp keyboard style)
    when the user taps one of the real colored buttons."""
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if db.is_blocked(bot_id, update.effective_user.id):
            return
        try:
            payload = json.loads(update.effective_message.web_app_data.data)
            button_id = int(payload["button_id"])
        except (ValueError, KeyError, AttributeError, TypeError):
            return
        await _send_button_reply(bot_id, button_id, update.effective_message)
    return handler


def build_child_application(token: str, bot_id: int) -> Application:
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", make_start_handler(bot_id)))
    app.add_handler(CommandHandler("panel", make_panel_handler(bot_id)))
    app.add_handler(CommandHandler("unlock", make_unlock_handler(bot_id)))
    app.add_handler(CommandHandler("block", make_block_handler(bot_id, block=True)))
    app.add_handler(CommandHandler("unblock", make_block_handler(bot_id, block=False)))
    app.add_handler(CallbackQueryHandler(make_button_handler(bot_id), pattern=r"^cbtn:\d+$"))
    app.add_handler(CallbackQueryHandler(make_reaction_handler(bot_id), pattern=r"^react:"))
    app.add_handler(PreCheckoutQueryHandler(_precheckout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, make_successful_payment_handler(bot_id)))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, make_webapp_data_handler(bot_id)))
    register_menu_button_commands(app, bot_id)
    # generic reply-keyboard text catcher must come after the fixed commands
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, make_reply_text_handler(bot_id)))
    return app
