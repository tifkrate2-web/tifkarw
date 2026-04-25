"""/start and /help commands."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes

HELP_TEXT = """\
<b>Group Assistant Bot</b>

<b>Welcome / Goodbye</b>
/setwelcome &lt;text&gt; — set welcome message ({user}, {chat} placeholders)
/setgoodbye &lt;text&gt; — set goodbye message
/clearwelcome, /cleargoodbye

<b>Moderation</b>
/ban [reply|@user|id] [reason] — ban a user
/kick [reply|@user|id] [reason] — kick a user
/mute [reply|@user|id] [duration] — mute (e.g. 10m, 2h, 1d)
/unmute [reply|@user|id]
/warn [reply|@user|id] [reason]
/warns [reply|@user|id]
/resetwarns [reply|@user|id]
/setwarnlimit &lt;n&gt;
/purge — reply to a message to delete from there to now
/pin (reply), /unpin

<b>Anti-spam</b>
/antiflood on|off|&lt;limit&gt; &lt;window_sec&gt;
/blocklinks on|off
/blockforwards on|off

<b>Rules &amp; Notes</b>
/setrules &lt;text&gt;, /rules, /clearrules
/save &lt;name&gt; (reply or with text), /get &lt;name&gt; or #name
/notes — list saved notes
/clear &lt;name&gt; — delete a note

<b>Info</b>
/id — show your/chat IDs
/info [reply|@user] — show user info
/ask &lt;question&gt; — ask the AI (if configured)
"""


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    await msg.reply_text(
        "Hi! I'm a group assistant bot. Add me to a group and promote me to admin "
        "(with rights to delete messages, ban users, and pin messages) to get started.\n\n"
        "Send /help to see all commands."
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    if msg is None:
        return
    await msg.reply_text(HELP_TEXT, parse_mode=ParseMode.HTML, disable_web_page_preview=True)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
