"""Optional AI Q&A via OpenAI Chat Completions API."""
from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes

log = logging.getLogger(__name__)

OPENAI_URL = "https://api.openai.com/v1/chat/completions"


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    msg = update.effective_message
    chat = update.effective_chat
    if msg is None or chat is None:
        return

    cfg = context.bot_data.get("config")
    if cfg is None or not cfg.openai_api_key:
        await msg.reply_text(
            "AI is not configured. Set OPENAI_API_KEY in your environment to enable /ask."
        )
        return

    question = " ".join(context.args).strip() if context.args else ""
    if not question and msg.reply_to_message and msg.reply_to_message.text:
        question = msg.reply_to_message.text
    if not question:
        await msg.reply_text("Usage: /ask <question> (or reply to a message).")
        return

    await chat.send_action(ChatAction.TYPING)
    headers = {
        "Authorization": f"Bearer {cfg.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": cfg.openai_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a concise, friendly assistant in a Telegram group. "
                    "Answer in 1-3 short paragraphs unless asked for detail."
                ),
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(OPENAI_URL, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
            answer = data["choices"][0]["message"]["content"].strip()
    except httpx.HTTPStatusError as e:
        log.warning("OpenAI HTTP error: %s", e.response.text[:200])
        await msg.reply_text(f"AI error: {e.response.status_code}")
        return
    except Exception as e:
        log.exception("OpenAI call failed")
        await msg.reply_text(f"AI request failed: {e}")
        return

    # Telegram limits messages to 4096 chars
    if len(answer) > 4000:
        answer = answer[:4000] + "\n\n…(truncated)"
    await msg.reply_text(answer, disable_web_page_preview=True)


def register(application: Application) -> None:
    application.add_handler(CommandHandler("ask", cmd_ask))
