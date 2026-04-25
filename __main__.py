"""Entry point: `python -m bot`."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import AIORateLimiter, ApplicationBuilder

from .config import Config
from .db import Store
from .handlers import register_all


def main() -> None:
    cfg = Config.from_env()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    application = (
        ApplicationBuilder()
        .token(cfg.bot_token)
        .rate_limiter(AIORateLimiter())
        .build()
    )

    store = Store(cfg.db_path)
    application.bot_data["store"] = store
    application.bot_data["config"] = cfg
    # Stash config on the bot for permission checks that don't have context.
    application.bot._assistant_config = cfg

    register_all(application)

    logging.info("Bot starting…")
    application.run_polling(
        allowed_updates=[
            Update.MESSAGE,
            Update.EDITED_MESSAGE,
            Update.CALLBACK_QUERY,
            Update.CHAT_MEMBER,
            Update.MY_CHAT_MEMBER,
        ],
    )


if __name__ == "__main__":
    main()
