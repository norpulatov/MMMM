from __future__ import annotations

from aiogram import Router
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models import Movie
from app.db.repo import MovieRepo

router = Router()


def _result_for_movie(movie: Movie, bot_username: str) -> InlineQueryResultArticle:
    deep_link = f"https://t.me/{bot_username}?start=watch_{movie.movie_number}"
    snippet = (movie.description or "No description.").strip()
    if len(snippet) > 120:
        snippet = f"{snippet[:117]}..."
    return InlineQueryResultArticle(
        id=f"movie-{movie.movie_number}",
        title=f"#{movie.movie_number} - {movie.title}",
        description=snippet,
        input_message_content=InputTextMessageContent(
            message_text=(
                f"🎬 <b>#{movie.movie_number} - {movie.title}</b>\n"
                f"{snippet}"
            )
        ),
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="▶️ Watch", url=deep_link)]]
        ),
    )


@router.inline_query()
async def inline_query_handler(
    inline_query: InlineQuery,
    session: AsyncSession,
    settings: Settings,
) -> None:
    q = (inline_query.query or "").strip()
    movie_repo = MovieRepo(session)

    if not q:
        movies = await movie_repo.list_latest(limit=30)
    elif q.isdigit():
        movie = await movie_repo.get_by_number(int(q))
        movies = [movie] if movie else []
    else:
        movies = await movie_repo.search(q, limit=30)

    results = [_result_for_movie(movie, settings.bot_username) for movie in movies]
    await inline_query.answer(results=results, cache_time=1, is_personal=True)
