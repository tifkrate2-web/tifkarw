"""Info commands: /id, /info."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

from ..utils.permissions import extract_target_user, mention_html


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    if msg is None:
        return
    parts = []
    if user:
        parts.append(f"User ID: <code>{user.id}</code>")
    if chat:
        parts.append(f"Chat ID: <code>{chat.id}</code>")
    if msg.reply_to_message and msg.reply_to_message.from_user:
        ru = msg.reply_to_message.from_user
        parts.append(f"Replied user: {mention_html(ru)} <code>{ru.id}</code>")
    await msg.reply_text("\n".join(parts), parse_mode=ParseMode.HTML)


async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        target = update.effective_user
    if target is None:
        return
    lines = [
        f"<b>{mention_html(target)}</b>",
        f"ID: <code>{target.id}</code>",
    ]
    if target.username:
        lines.append(f"Username: @{target.username}")
    if getattr(target, "language_code", None):
        lines.append(f"Language: {target.language_code}")
    if target.is_bot:
        lines.append("Type: bot")
    await msg.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("id", cmd_id))
    application.add_handler(CommandHandler("info", cmd_info))
