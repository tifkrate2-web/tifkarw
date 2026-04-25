"""Group rules."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..db import Store
from ..utils.permissions import require_admin, require_group


@require_group
@require_admin
async def cmd_setrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    text = msg.text.partition(" ")[2].strip() if msg.text else ""
    if not text and msg.reply_to_message and msg.reply_to_message.text:
        text = msg.reply_to_message.text
    if not text:
        await msg.reply_text("Usage: /setrules <text> (or reply to a message).")
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "rules_text", text)
    await msg.reply_text("Rules saved.")


async def cmd_rules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    store: Store = context.bot_data["store"]
    settings = await store.get_settings(chat.id)
    text = settings.get("rules_text")
    if not text:
        await msg.reply_text("No rules set. An admin can set them with /setrules.")
        return
    await msg.reply_text(
        f"<b>Rules</b>\n\n{text}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


@require_group
@require_admin
async def cmd_clearrules(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "rules_text", None)
    await msg.reply_text("Rules cleared.")


def register(application: Application) -> None:
    application.add_handler(CommandHandler("setrules", cmd_setrules))
    application.add_handler(CommandHandler("rules", cmd_rules))
    application.add_handler(CommandHandler("clearrules", cmd_clearrules))
