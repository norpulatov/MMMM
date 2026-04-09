import logging
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


logger = logging.getLogger(__name__)
settings = get_settings()


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, future=True, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def _ensure_missing_columns() -> None:
    check_queries = {
        "users": {
            "username": "ALTER TABLE users ADD COLUMN username VARCHAR(255)",
            "first_name": "ALTER TABLE users ADD COLUMN first_name VARCHAR(255)",
            "added_at": "ALTER TABLE users ADD COLUMN added_at TIMESTAMP",
        },
        "movies": {
            "description": "ALTER TABLE movies ADD COLUMN description TEXT",
            "preview_file_id": "ALTER TABLE movies ADD COLUMN preview_file_id VARCHAR(512)",
            "channel_post_id": "ALTER TABLE movies ADD COLUMN channel_post_id BIGINT",
            "channel_chat_id": "ALTER TABLE movies ADD COLUMN channel_chat_id BIGINT",
            "views_count": "ALTER TABLE movies ADD COLUMN views_count INTEGER DEFAULT 0",
        },
    }

    async with engine.begin() as conn:
        for table_name, columns in check_queries.items():
            if settings.database_url.startswith("postgresql"):
                result = await conn.execute(
                    text(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = :table_name
                        """
                    ),
                    {"table_name": table_name},
                )
                existing = {row[0] for row in result.fetchall()}
            else:
                result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
                rows = result.fetchall()
                existing = {row[1] for row in rows}

            for column_name, alter_sql in columns.items():
                if column_name in existing:
                    continue
                try:
                    await conn.execute(text(alter_sql))
                    logger.info("Ustun qo'shildi: %s.%s", table_name, column_name)
                except Exception:
                    logger.exception("Ustun qo'shilmadi: %s.%s", table_name, column_name)


async def init_db() -> None:
    # Local import avoids circular import: models -> database -> models
    from app.db import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _ensure_missing_columns()
