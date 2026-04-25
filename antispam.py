"""Anti-flood and link/forward filtering."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from telegram import Update
from telegram.constants import MessageEntityType
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from ..db import Store
from ..utils.permissions import is_admin, require_admin, require_group

# (chat_id, user_id) -> timestamps of recent messages
_message_log: dict[tuple[int, int], deque[float]] = defaultdict(lambda: deque(maxlen=50))


@require_group
@require_admin
async def cmd_antiflood(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not context.args:
        store: Store = context.bot_data["store"]
        s = await store.get_settings(chat.id)
        state = "on" if s.get("antiflood_enabled") else "off"
        await msg.reply_text(
            f"Anti-flood is {state} (limit={s.get('antiflood_limit')}, "
            f"window={s.get('antiflood_window')}s).\n"
            "Usage: /antiflood on | off | <limit> <window_sec>"
        )
        return

    store = context.bot_data["store"]
    arg = context.args[0].lower()
    if arg in ("on", "enable"):
        await store.update_setting(chat.id, "antiflood_enabled", 1)
        await msg.reply_text("Anti-flood enabled.")
        return
    if arg in ("off", "disable"):
        await store.update_setting(chat.id, "antiflood_enabled", 0)
        await msg.reply_text("Anti-flood disabled.")
        return
    try:
        limit = int(context.args[0])
        window = int(context.args[1]) if len(context.args) > 1 else 8
        if limit < 2 or window < 1:
            raise ValueError
    except (ValueError, IndexError):
        await msg.reply_text("Usage: /antiflood on | off | <limit:int>=2..> <window_sec>")
        return
    await store.update_setting(chat.id, "antiflood_enabled", 1)
    await store.update_setting(chat.id, "antiflood_limit", limit)
    await store.update_setting(chat.id, "antiflood_window", window)
    await msg.reply_text(f"Anti-flood: limit={limit} per {window}s, enabled.")


def _make_toggle(setting_key: str, label: str):
    @require_group
    @require_admin
    async def handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        msg = update.effective_message
        if chat is None or msg is None:
            return
        store: Store = context.bot_data["store"]
        if not context.args:
            s = await store.get_settings(chat.id)
            state = "on" if s.get(setting_key) else "off"
            await msg.reply_text(f"{label} is {state}.")
            return
        arg = context.args[0].lower()
        if arg in ("on", "enable"):
            await store.update_setting(chat.id, setting_key, 1)
            await msg.reply_text(f"{label} enabled.")
        elif arg in ("off", "disable"):
            await store.update_setting(chat.id, setting_key, 0)
            await msg.reply_text(f"{label} disabled.")
        else:
            await msg.reply_text(f"Usage: /{handler.__name__} on | off")

    return handler


cmd_blocklinks = _make_toggle("block_links", "Link blocking")
cmd_blocklinks.__name__ = "blocklinks"
cmd_blockforwards = _make_toggle("block_forwards", "Forward blocking")
cmd_blockforwards.__name__ = "blockforwards"


def _has_link(message) -> bool:
    if message.entities:
        for ent in message.entities:
            if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                return True
    if message.caption_entities:
        for ent in message.caption_entities:
            if ent.type in (MessageEntityType.URL, MessageEntityType.TEXT_LINK):
                return True
    return False


def _is_forwarded(message) -> bool:
    return bool(getattr(message, "forward_origin", None) or getattr(message, "forward_date", None))


async def on_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if msg is None or chat is None or user is None:
        return
    if user.is_bot:
        return
    if await is_admin(update, user.id):
        return

    store: Store = context.bot_data["store"]
    settings = await store.get_settings(chat.id)

    # Anti-flood
    if settings.get("antiflood_enabled"):
        limit = int(settings.get("antiflood_limit") or 6)
        window = int(settings.get("antiflood_window") or 8)
        key = (chat.id, user.id)
        now = time.monotonic()
        log = _message_log[key]
        log.append(now)
        while log and now - log[0] > window:
            log.popleft()
        if len(log) > limit:
            try:
                await msg.delete()
            except TelegramError:
                pass
            try:
                from datetime import datetime, timedelta, timezone

                from telegram import ChatPermissions

                until = datetime.now(tz=timezone.utc) + timedelta(seconds=60)
                await chat.restrict_member(
                    user.id,
                    permissions=ChatPermissions(can_send_messages=False),
                    until_date=until,
                )
                await context.bot.send_message(
                    chat.id, f"Muted user {user.id} for flooding (60s)."
                )
            except TelegramError:
                pass
            log.clear()
            return

    # Block links
    if settings.get("block_links") and _has_link(msg):
        try:
            await msg.delete()
        except TelegramError:
            pass
        return

    # Block forwards
    if settings.get("block_forwards") and _is_forwarded(msg):
        try:
            await msg.delete()
        except TelegramError:
            pass
        return


def register(application: Application) -> None:
    application.add_handler(CommandHandler("antiflood", cmd_antiflood))
    application.add_handler(CommandHandler("blocklinks", cmd_blocklinks))
    application.add_handler(CommandHandler("blockforwards", cmd_blockforwards))
    # group=1 so it runs after command handlers in group=0
    application.add_handler(
        MessageHandler(
            filters.ChatType.GROUPS & ~filters.COMMAND & ~filters.StatusUpdate.ALL,
            on_group_message,
        ),
        group=1,
    )
