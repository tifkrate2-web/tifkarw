"""Welcome / goodbye messages and configuration."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ChatMemberHandler,
    CommandHandler,
    ContextTypes,
)

from ..db import Store
from ..utils.permissions import mention_html, require_admin, require_group


def _format(template: str, update: Update) -> str:
    user = update.effective_user
    chat = update.effective_chat
    user_html = mention_html(user) if user else ""
    chat_title = (chat.title if chat and chat.title else "this chat")
    return template.replace("{user}", user_html).replace("{chat}", chat_title)


@require_group
@require_admin
async def cmd_setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    text = msg.text.partition(" ")[2].strip() if msg.text else ""
    if not text and msg.reply_to_message and msg.reply_to_message.text:
        text = msg.reply_to_message.text
    if not text:
        await msg.reply_text("Usage: /setwelcome <text>. Use {user} and {chat} as placeholders.")
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "welcome_text", text)
    await msg.reply_text("Welcome message saved.")


@require_group
@require_admin
async def cmd_setgoodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    text = msg.text.partition(" ")[2].strip() if msg.text else ""
    if not text and msg.reply_to_message and msg.reply_to_message.text:
        text = msg.reply_to_message.text
    if not text:
        await msg.reply_text("Usage: /setgoodbye <text>.")
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "goodbye_text", text)
    await msg.reply_text("Goodbye message saved.")


@require_group
@require_admin
async def cmd_clearwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "welcome_text", None)
    await update.effective_message.reply_text("Welcome message cleared.")


@require_group
@require_admin
async def cmd_cleargoodbye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "goodbye_text", None)
    await update.effective_message.reply_text("Goodbye message cleared.")


async def on_chat_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Detect joins/leaves via chat_member updates and send welcome/goodbye."""
    cmu = update.chat_member
    if cmu is None:
        return
    chat = cmu.chat
    old_status = cmu.old_chat_member.status
    new_status = cmu.new_chat_member.status
    user = cmu.new_chat_member.user
    if user.is_bot and user.id == context.bot.id:
        return

    store: Store = context.bot_data["store"]
    settings = await store.get_settings(chat.id)

    joined = old_status in ("left", "kicked") and new_status in ("member", "restricted")
    left = old_status in ("member", "restricted", "administrator", "creator") and new_status in (
        "left",
        "kicked",
    )

    if joined and settings.get("welcome_text"):
        text = settings["welcome_text"]
        text = text.replace("{user}", mention_html(user))
        text = text.replace("{chat}", chat.title or "this chat")
        try:
            await context.bot.send_message(
                chat.id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            pass
    elif left and settings.get("goodbye_text"):
        text = settings["goodbye_text"]
        text = text.replace("{user}", mention_html(user))
        text = text.replace("{chat}", chat.title or "this chat")
        try:
            await context.bot.send_message(
                chat.id, text, parse_mode=ParseMode.HTML, disable_web_page_preview=True
            )
        except Exception:
            pass


def register(application: Application) -> None:
    application.add_handler(CommandHandler("setwelcome", cmd_setwelcome))
    application.add_handler(CommandHandler("setgoodbye", cmd_setgoodbye))
    application.add_handler(CommandHandler("clearwelcome", cmd_clearwelcome))
    application.add_handler(CommandHandler("cleargoodbye", cmd_cleargoodbye))
    application.add_handler(
        ChatMemberHandler(on_chat_member, ChatMemberHandler.CHAT_MEMBER)
    )
