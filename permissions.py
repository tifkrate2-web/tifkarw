"""Permission and helper utilities."""
from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import timedelta
from functools import wraps

from telegram import Chat, Update, User
from telegram.constants import ChatType
from telegram.ext import ContextTypes


async def is_admin(update: Update, user_id: int) -> bool:
    """Return True if user is an admin/owner of the chat or a global owner."""
    chat = update.effective_chat
    if chat is None:
        return False

    cfg = getattr(update.get_bot(), "_assistant_config", None)
    if cfg is not None and user_id in cfg.owner_ids:
        return True

    if chat.type == ChatType.PRIVATE:
        return True

    try:
        member = await chat.get_member(user_id)
    except Exception:
        return False
    return member.status in ("administrator", "creator")


def require_group(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat = update.effective_chat
        if chat is None or chat.type not in (ChatType.GROUP, ChatType.SUPERGROUP):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "This command only works in groups."
                )
            return
        await func(update, context)

    return wrapper


def require_admin(func: Callable[..., Awaitable[None]]) -> Callable[..., Awaitable[None]]:
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if user is None:
            return
        if not await is_admin(update, user.id):
            if update.effective_message:
                await update.effective_message.reply_text(
                    "This command is for admins only."
                )
            return
        await func(update, context)

    return wrapper


async def extract_target_user(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> tuple[User | None, str | None]:
    """Extract target user from a reply, @mention, or numeric ID.

    Returns (user, reason_text_remainder). reason_text_remainder is the rest of the
    command arguments after consuming the user reference (used as ban/warn reason).
    """
    msg = update.effective_message
    if msg is None:
        return None, None

    if msg.reply_to_message and msg.reply_to_message.from_user:
        reason = " ".join(context.args) if context.args else None
        return msg.reply_to_message.from_user, reason

    if not context.args:
        return None, None

    target_arg = context.args[0]
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else None

    chat = update.effective_chat
    if chat is None:
        return None, reason

    if target_arg.startswith("@"):
        username = target_arg.lstrip("@")
        if msg.entities:
            for ent in msg.entities:
                if ent.user and ent.type == "text_mention":
                    return ent.user, reason
        try:
            member = await chat.get_member(username)
            return member.user, reason
        except Exception:
            return None, reason

    try:
        uid = int(target_arg)
    except ValueError:
        return None, reason

    try:
        member = await chat.get_member(uid)
        return member.user, reason
    except Exception:
        return User(id=uid, first_name=str(uid), is_bot=False), reason


_DURATION_RE = re.compile(r"^(\d+)\s*([smhd]?)$", re.IGNORECASE)


def parse_duration(text: str) -> timedelta | None:
    """Parse a duration like '10m', '2h', '1d', '30s' (default seconds if no unit)."""
    if not text:
        return None
    m = _DURATION_RE.match(text.strip())
    if not m:
        return None
    value = int(m.group(1))
    unit = (m.group(2) or "s").lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400}
    return timedelta(seconds=value * multipliers[unit])


def mention_html(user: User | Chat) -> str:
    name = getattr(user, "full_name", None) or getattr(user, "title", None) or str(user.id)
    safe = name.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<a href="tg://user?id={user.id}">{safe}</a>'
