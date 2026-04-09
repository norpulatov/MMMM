from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_settings
from app.db.session import Database
from app.handlers import register_handlers
from app.logging_setup import configure_logging
from app.middlewares import DbSessionMiddleware, SettingsMiddleware


async def main() -> None:
    configure_logging()
    settings = load_settings()

    db = Database(settings.database_url)
    await db.init_models()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    dp.update.middleware(SettingsMiddleware(settings))
    dp.update.middleware(DbSessionMiddleware(db))
    register_handlers(dp)

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
