from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repo import MovieRepo, UserRepo
from app.keyboards.common import main_menu_keyboard, movies_list_keyboard, watch_keyboard
from app.utils.formatters import movie_details_text

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def start_handler(
    message: Message, command: CommandObject, session: AsyncSession
) -> None:
    user_repo = UserRepo(session)
    await user_repo.upsert_user(
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
    )

    deep_link_arg = (command.args or "").strip()
    if deep_link_arg.startswith("watch_"):
        movie_number = deep_link_arg.replace("watch_", "", 1)
        if movie_number.isdigit():
            await send_movie_by_number(message, int(movie_number), session)
            return

    await message.answer(
        "Welcome to the Movie Library Bot!\n"
        "Use /movies to browse, /search to find titles, or /movie <number>.",
        reply_markup=main_menu_keyboard(),
    )


@router.message(Command("movies"))
async def movies_handler(message: Message, session: AsyncSession) -> None:
    await send_movies_page(message, session=session, page=1)


@router.message(Command("search"))
async def search_handler(message: Message, command: CommandObject, session: AsyncSession) -> None:
    query = (command.args or "").strip()
    if not query:
        await message.answer("Usage: /search <query>")
        return

    movie_repo = MovieRepo(session)
    results = await movie_repo.search(query, limit=20)
    if not results:
        await message.answer("No movies found.")
        return

    if len(results) == 1:
        movie = results[0]
        await message.answer(movie_details_text(movie), reply_markup=watch_keyboard(movie.movie_number))
        return

    lines = ["🔎 Search results:"]
    for movie in results:
        lines.append(f"#{movie.movie_number} - {movie.title}")
    lines.append("\nSend the movie number or use /movie <number>.")
    await message.answer("\n".join(lines))


@router.message(Command("movie"))
async def movie_command_handler(message: Message, command: CommandObject, session: AsyncSession) -> None:
    value = (command.args or "").strip()
    if not value or not value.isdigit():
        await message.answer("Usage: /movie <number>")
        return
    await send_movie_details(message, int(value), session)


@router.message(F.text.regexp(r"^\d+$"))
async def number_message_handler(message: Message, session: AsyncSession) -> None:
    await send_movie_details(message, int(message.text.strip()), session)


@router.callback_query(F.data.startswith("menu:movies:"))
async def movies_page_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    page_raw = callback.data.rsplit(":", maxsplit=1)[-1]
    page = int(page_raw) if page_raw.isdigit() else 1
    await send_movies_page(callback.message, session=session, page=page, edit=True)
    await callback.answer()


@router.callback_query(F.data == "menu:search")
async def menu_search_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Use /search <query> to find movies by title.")
    await callback.answer()


@router.callback_query(F.data == "menu:about")
async def menu_about_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        "This bot stores and shares a movie library.\n"
        "Use /movies, /search, or /movie <number>."
    )
    await callback.answer()


@router.callback_query(F.data.startswith("movie:"))
async def movie_callback_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    value = callback.data.split(":", maxsplit=1)[-1]
    if not value.isdigit():
        await callback.answer("Invalid movie number", show_alert=True)
        return
    await send_movie_details(callback.message, int(value), session, edit=True)
    await callback.answer()


@router.callback_query(F.data.startswith("watch:"))
async def watch_callback_handler(callback: CallbackQuery, session: AsyncSession) -> None:
    value = callback.data.split(":", maxsplit=1)[-1]
    if not value.isdigit():
        await callback.answer("Invalid movie number", show_alert=True)
        return
    await send_movie_by_number(callback.message, int(value), session)
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


async def send_movies_page(
    message: Message,
    *,
    session: AsyncSession,
    page: int,
    per_page: int = 10,
    edit: bool = False,
) -> None:
    movie_repo = MovieRepo(session)
    total = await movie_repo.get_total_movies()
    if total == 0:
        text = "No movies in the library yet."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    page = max(page, 1)
    offset = (page - 1) * per_page
    movies = await movie_repo.list_movies(limit=per_page, offset=offset)
    kb = movies_list_keyboard(movies, current_page=page, total_count=total, per_page=per_page)
    text = "🎬 Movie list:"
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def send_movie_details(
    message: Message, movie_number: int, session: AsyncSession, edit: bool = False
) -> None:
    movie_repo = MovieRepo(session)
    movie = await movie_repo.get_by_number(movie_number)
    if not movie:
        text = f"Movie #{movie_number} not found."
        if edit:
            await message.edit_text(text)
        else:
            await message.answer(text)
        return

    text = movie_details_text(movie)
    kb = watch_keyboard(movie.movie_number)
    if edit:
        await message.edit_text(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


async def send_movie_by_number(message: Message, movie_number: int, session: AsyncSession) -> None:
    movie_repo = MovieRepo(session)
    movie = await movie_repo.get_by_number(movie_number)
    if not movie:
        await message.answer(f"Movie #{movie_number} not found.")
        return
    try:
        await message.answer_video(
            movie.file_id,
            caption=f"🎬 #{movie.movie_number} - {movie.title}",
        )
        await movie_repo.increment_views(movie_number)
    except Exception:
        logger.exception("Failed to send movie #%s", movie_number)
        await message.answer("Could not send the video right now. Please try again later.")
