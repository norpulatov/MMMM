from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, func
from database import AsyncSessionLocal, Movie
from utils import build_movies_keyboard
from keyboards.inline import movie_detail_keyboard, back_to_start_keyboard
import math

router = Router()

async def show_movies_page(target, page: int = 1, edit: bool = True):
    per_page = 10
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Movie).order_by(Movie.movie_number).offset((page-1)*per_page).limit(per_page)
        )
        movies = result.scalars().all()
        total = await session.scalar(select(func.count()).select_from(Movie))
        total_pages = math.ceil(total / per_page) if total else 1

    if not movies:
        text = "No movies added yet."
        if edit:
            if isinstance(target, CallbackQuery):
                await target.message.edit_text(text, reply_markup=back_to_start_keyboard())
            else:
                await target.edit_text(text, reply_markup=back_to_start_keyboard())
        else:
            await target.answer(text, reply_markup=back_to_start_keyboard())
        return

    text = f"🎬 <b>Movie List</b> (page {page}/{total_pages}):\n\n"
    for m in movies:
        text += f"#{m.movie_number} - {m.title}\n"

    keyboard = build_movies_keyboard(movies, page, total_pages)
    if edit:
        if isinstance(target, CallbackQuery):
            await target.message.edit_text(text, reply_markup=keyboard)
        else:
            await target.edit_text(text, reply_markup=keyboard)
    else:
        await target.answer(text, reply_markup=keyboard)

@router.message(Command("movies"))
async def cmd_movies(message: Message):
    await show_movies_page(message, page=1, edit=False)

@router.callback_query(F.data.startswith("page_"))
async def pagination_callback(callback: CallbackQuery):
    page = int(callback.data.split("_")[1])
    await show_movies_page(callback, page=page, edit=True)
    await callback.answer()

@router.message(Command("movie"))
async def cmd_movie(message: Message):
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Usage: /movie 123")
        return
    try:
        num = int(args[1])
    except ValueError:
        await message.answer("Movie number must be integer.")
        return
    await show_movie_details(message, num)

@router.message(F.text.regexp(r"^\d+$"))
async def number_search_handler(message: Message):
    num = int(message.text.strip())
    await show_movie_details(message, num)

async def show_movie_details(target, movie_number: int):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).where(Movie.movie_number == movie_number))
        movie = result.scalar_one_or_none()
        if not movie:
            text = f"❌ Movie #{movie_number} not found."
            if isinstance(target, Message):
                await target.answer(text)
            else:
                await target.message.edit_text(text, reply_markup=back_to_start_keyboard())
            return
        movie.views_count += 1
        await session.commit()
        text = (
            f"🎬 <b>#{movie.movie_number} - {movie.title}</b>\n\n"
            f"📝 {movie.description or 'No description'}\n\n"
            f"👁 Views: {movie.views_count}\n"
            f"📅 Added: {movie.added_at.strftime('%Y-%m-%d')}"
        )
        keyboard = movie_detail_keyboard(movie_number)
        if isinstance(target, Message):
            await target.answer(text, reply_markup=keyboard, disable_web_page_preview=True)
        else:
            await target.message.edit_text(text, reply_markup=keyboard, disable_web_page_preview=True)

@router.callback_query(F.data.startswith("view_"))
async def view_callback(callback: CallbackQuery):
    movie_number = int(callback.data.split("_")[1])
    await show_movie_details(callback, movie_number)
    await callback.answer()

@router.callback_query(F.data.startswith("refresh_"))
async def refresh_callback(callback: CallbackQuery):
    movie_number = int(callback.data.split("_")[1])
    await show_movie_details(callback, movie_number)
    await callback.answer()

@router.message(Command("search"))
async def cmd_search(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        await message.answer("Usage: /search Avatar")
        return
    query = args[1].strip()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Movie).where(Movie.title.ilike(f"%{query}%")).order_by(Movie.movie_number).limit(20)
        )
        movies = result.scalars().all()
        if not movies:
            await message.answer(f"❌ No movies found for '{query}'.")
            return
        if len(movies) == 1:
            await show_movie_details(message, movies[0].movie_number)
            return
        text = f"🔍 Search results for '{query}':\n\n"
        for m in movies:
            text += f"#{m.movie_number} - {m.title}\n"
        text += "\nSend the number or use /movie command."
        await message.answer(text)