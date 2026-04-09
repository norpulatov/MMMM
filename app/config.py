from __future__ import annotations

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(slots=True, frozen=True)
class Settings:
    bot_token: str
    admin_ids: set[int]
    channel_id: int
    database_url: str
    bot_username: str


def _parse_admin_ids(raw_value: str) -> set[int]:
    admin_ids: set[int] = set()
    for chunk in raw_value.split(","):
        piece = chunk.strip()
        if not piece:
            continue
        admin_ids.add(int(piece))
    return admin_ids


def load_settings() -> Settings:
    load_dotenv()
    bot_token = getenv("BOT_TOKEN", "").strip()
    admin_ids_raw = getenv("ADMIN_IDS", "").strip()
    channel_id_raw = getenv("CHANNEL_ID", "").strip()
    database_url = getenv("DATABASE_URL", "").strip()
    bot_username = getenv("BOT_USERNAME", "").strip().lstrip("@")

    if not bot_token:
        raise ValueError("BOT_TOKEN is required")
    if not admin_ids_raw:
        raise ValueError("ADMIN_IDS is required")
    if not channel_id_raw:
        raise ValueError("CHANNEL_ID is required")
    if not bot_username:
        raise ValueError("BOT_USERNAME is required")

    admin_ids = _parse_admin_ids(admin_ids_raw)
    if not admin_ids:
        raise ValueError("ADMIN_IDS must include at least one user id")

    if not database_url:
        database_url = "sqlite+aiosqlite:///./movies.db"

    return Settings(
        bot_token=bot_token,
        admin_ids=admin_ids,
        channel_id=int(channel_id_raw),
        database_url=database_url,
        bot_username=bot_username,
    )
