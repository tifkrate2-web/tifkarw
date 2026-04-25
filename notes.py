"""Saved notes / quick replies."""
from __future__ import annotations

import re

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..db import Store
from ..utils.permissions import require_admin, require_group

_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]{1,32}$")


@require_group
@require_admin
async def cmd_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /save <name> <content> (or reply to a message).")
        return
    name = context.args[0]
    if not _NAME_RE.match(name):
        await msg.reply_text("Note names must be 1-32 chars: letters, digits, _ or -")
        return
    content = " ".join(context.args[1:]).strip()
    if not content and msg.reply_to_message:
        content = msg.reply_to_message.text or msg.reply_to_message.caption or ""
    if not content:
        await msg.reply_text("No content. Provide text or reply to a message.")
        return
    store: Store = context.bot_data["store"]
    await store.save_note(chat.id, name, content)
    await msg.reply_text(f"Saved note `{name.lower()}`.", parse_mode="Markdown")


async def cmd_get(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /get <name>")
        return
    name = context.args[0]
    store: Store = context.bot_data["store"]
    content = await store.get_note(chat.id, name)
    if not content:
        await msg.reply_text(f"No note named `{name.lower()}`.", parse_mode="Markdown")
        return
    await msg.reply_text(content, disable_web_page_preview=True)


async def cmd_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    store: Store = context.bot_data["store"]
    names = await store.list_notes(chat.id)
    if not names:
        await msg.reply_text("No notes saved.")
        return
    listing = "\n".join(f"- {n}" for n in names)
    await msg.reply_text(f"Saved notes:\n{listing}")


@require_group
@require_admin
async def cmd_clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /clear <name>")
        return
    name = context.args[0]
    store: Store = context.bot_data["store"]
    ok = await store.delete_note(chat.id, name)
    if ok:
        await msg.reply_text(f"Deleted note `{name.lower()}`.", parse_mode="Markdown")
    else:
        await msg.reply_text("No such note.")


_HASHTAG_RE = re.compile(r"(?:^|\s)#([A-Za-z0-9_\-]{1,32})\b")


async def on_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None or not msg.text:
        return
    m = _HASHTAG_RE.search(msg.text)
    if not m:
        return
    name = m.group(1)
    store: Store = context.bot_data["store"]
    content = await store.get_note(chat.id, name)
    if content:
        await msg.reply_text(content, disable_web_page_preview=True)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("save", cmd_save))
    application.add_handler(CommandHandler("get", cmd_get))
    application.add_handler(CommandHandler("notes", cmd_notes))
    application.add_handler(CommandHandler("clear", cmd_clear))
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS & filters.Regex(_HASHTAG_RE), on_hashtag),
        group=2,
    )
