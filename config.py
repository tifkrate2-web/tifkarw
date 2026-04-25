"""Configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str | None) -> list[int]:
    if not raw:
        return []
    out: list[int] = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        try:
            out.append(int(chunk))
        except ValueError:
            continue
    return out


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_ids: list[int] = field(default_factory=list)
    db_path: str = "bot.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        token = os.getenv("BOT_TOKEN", "").strip()
        if not token:
            raise RuntimeError(
                "BOT_TOKEN is not set. Copy .env.example to .env and fill in your token."
            )
        return cls(
            bot_token=token,
            owner_ids=_parse_ids(os.getenv("OWNER_IDS")),
            db_path=os.getenv("DB_PATH", "bot.db").strip() or "bot.db",
            openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip() or None,
            openai_model=(os.getenv("OPENAI_MODEL") or "gpt-4o-mini").strip(),
            log_level=(os.getenv("LOG_LEVEL") or "INFO").strip().upper(),
        )
