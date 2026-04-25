"""Ban, kick, mute, warn, purge, pin/unpin, promote/demote."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from telegram import ChatPermissions, Update
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

from ..db import Store
from ..utils.permissions import (
    extract_target_user,
    mention_html,
    parse_duration,
    require_admin,
    require_group,
)


@require_group
@require_admin
async def cmd_ban(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, reason = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    try:
        await chat.ban_member(target.id)
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    text = f"Banned {mention_html(target)}."
    if reason:
        text += f"\nReason: {reason}"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


@require_group
@require_admin
async def cmd_kick(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, reason = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    try:
        await chat.ban_member(target.id)
        await chat.unban_member(target.id, only_if_banned=True)
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    text = f"Kicked {mention_html(target)}."
    if reason:
        text += f"\nReason: {reason}"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


@require_group
@require_admin
async def cmd_mute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, remainder = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return

    until: datetime | None = None
    duration_text = ""
    if remainder:
        first = remainder.split(" ", 1)[0]
        dur = parse_duration(first)
        if dur is not None:
            until = datetime.now(tz=timezone.utc) + dur
            duration_text = f" for {first}"

    permissions = ChatPermissions(
        can_send_messages=False,
        can_send_audios=False,
        can_send_documents=False,
        can_send_photos=False,
        can_send_videos=False,
        can_send_video_notes=False,
        can_send_voice_notes=False,
        can_send_polls=False,
        can_send_other_messages=False,
        can_add_web_page_previews=False,
    )
    try:
        await chat.restrict_member(target.id, permissions=permissions, until_date=until)
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    await msg.reply_text(
        f"Muted {mention_html(target)}{duration_text}.", parse_mode=ParseMode.HTML
    )


@require_group
@require_admin
async def cmd_unmute(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    permissions = ChatPermissions(
        can_send_messages=True,
        can_send_audios=True,
        can_send_documents=True,
        can_send_photos=True,
        can_send_videos=True,
        can_send_video_notes=True,
        can_send_voice_notes=True,
        can_send_polls=True,
        can_send_other_messages=True,
        can_add_web_page_previews=True,
    )
    try:
        await chat.restrict_member(target.id, permissions=permissions)
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    await msg.reply_text(f"Unmuted {mention_html(target)}.", parse_mode=ParseMode.HTML)


@require_group
@require_admin
async def cmd_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, reason = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    store: Store = context.bot_data["store"]
    settings = await store.get_settings(chat.id)
    limit = int(settings.get("warn_limit") or 3)
    count = await store.add_warning(chat.id, target.id)

    if count >= limit:
        try:
            await chat.ban_member(target.id)
            await store.reset_warnings(chat.id, target.id)
            text = (
                f"{mention_html(target)} reached {count}/{limit} warnings — banned."
            )
        except TelegramError as e:
            text = f"Could not ban {mention_html(target)}: {e.message}"
    else:
        text = f"Warned {mention_html(target)} ({count}/{limit})."
        if reason:
            text += f"\nReason: {reason}"
    await msg.reply_text(text, parse_mode=ParseMode.HTML)


@require_group
async def cmd_warns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        target = update.effective_user
    if target is None:
        return
    store: Store = context.bot_data["store"]
    settings = await store.get_settings(chat.id)
    limit = int(settings.get("warn_limit") or 3)
    count = await store.get_warnings(chat.id, target.id)
    await msg.reply_text(
        f"{mention_html(target)}: {count}/{limit} warnings.", parse_mode=ParseMode.HTML
    )


@require_group
@require_admin
async def cmd_resetwarns(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    store: Store = context.bot_data["store"]
    await store.reset_warnings(chat.id, target.id)
    await msg.reply_text(f"Cleared warnings for {mention_html(target)}.", parse_mode=ParseMode.HTML)


@require_group
@require_admin
async def cmd_setwarnlimit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not context.args:
        await msg.reply_text("Usage: /setwarnlimit <n>")
        return
    try:
        n = int(context.args[0])
        if n < 1 or n > 100:
            raise ValueError
    except ValueError:
        await msg.reply_text("Limit must be an integer between 1 and 100.")
        return
    store: Store = context.bot_data["store"]
    await store.update_setting(chat.id, "warn_limit", n)
    await msg.reply_text(f"Warn limit set to {n}.")


@require_group
@require_admin
async def cmd_purge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    if not msg.reply_to_message:
        await msg.reply_text("Reply to the message you want to purge from.")
        return
    start_id = msg.reply_to_message.message_id
    end_id = msg.message_id
    deleted = 0
    failed = 0
    for mid in range(start_id, end_id + 1):
        try:
            await context.bot.delete_message(chat.id, mid)
            deleted += 1
        except TelegramError:
            failed += 1
    notice = await context.bot.send_message(
        chat.id, f"Purged {deleted} messages ({failed} failed)."
    )

    async def _delete_notice(ctx: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            await ctx.bot.delete_message(chat.id, notice.message_id)
        except TelegramError:
            pass

    if context.application.job_queue is not None:
        context.application.job_queue.run_once(_delete_notice, when=5)


@require_group
@require_admin
async def cmd_pin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None or msg.reply_to_message is None:
        if msg:
            await msg.reply_text("Reply to a message to pin it.")
        return
    try:
        await context.bot.pin_chat_message(
            chat.id, msg.reply_to_message.message_id, disable_notification=True
        )
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")


@require_group
@require_admin
async def cmd_unpin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    try:
        if msg.reply_to_message:
            await context.bot.unpin_chat_message(chat.id, msg.reply_to_message.message_id)
        else:
            await context.bot.unpin_chat_message(chat.id)
        await msg.reply_text("Unpinned.")
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")


@require_group
@require_admin
async def cmd_promote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    try:
        await context.bot.promote_chat_member(
            chat.id,
            target.id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False,
            can_manage_chat=True,
            can_manage_video_chats=False,
        )
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    await msg.reply_text(f"Promoted {mention_html(target)}.", parse_mode=ParseMode.HTML)


@require_group
@require_admin
async def cmd_demote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    msg = update.effective_message
    if chat is None or msg is None:
        return
    target, _ = await extract_target_user(update, context)
    if target is None:
        await msg.reply_text("Reply to a user or pass @username / id.")
        return
    try:
        await context.bot.promote_chat_member(
            chat.id,
            target.id,
            can_change_info=False,
            can_post_messages=False,
            can_edit_messages=False,
            can_delete_messages=False,
            can_invite_users=False,
            can_restrict_members=False,
            can_pin_messages=False,
            can_promote_members=False,
            can_manage_chat=False,
            can_manage_video_chats=False,
        )
    except TelegramError as e:
        await msg.reply_text(f"Failed: {e.message}")
        return
    await msg.reply_text(f"Demoted {mention_html(target)}.", parse_mode=ParseMode.HTML)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("ban", cmd_ban))
    application.add_handler(CommandHandler("kick", cmd_kick))
    application.add_handler(CommandHandler("mute", cmd_mute))
    application.add_handler(CommandHandler("unmute", cmd_unmute))
    application.add_handler(CommandHandler("warn", cmd_warn))
    application.add_handler(CommandHandler("warns", cmd_warns))
    application.add_handler(CommandHandler("resetwarns", cmd_resetwarns))
    application.add_handler(CommandHandler("setwarnlimit", cmd_setwarnlimit))
    application.add_handler(CommandHandler("purge", cmd_purge))
    application.add_handler(CommandHandler("pin", cmd_pin))
    application.add_handler(CommandHandler("unpin", cmd_unpin))
    application.add_handler(CommandHandler("promote", cmd_promote))
    application.add_handler(CommandHandler("demote", cmd_demote))

# Used by tests for parse_duration
_ = timedelta  # noqa
