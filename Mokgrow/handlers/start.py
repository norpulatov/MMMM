from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, CommandObject
from sqlalchemy import select
from database import AsyncSessionLocal, User, Movie
from keyboards.inline import start_keyboard, back_to_start_keyboard, movie_detail_keyboard
from utils import logger

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    async with AsyncSessionLocal() as session:
        # Save user
        result = await session.execute(select(User).where(User.user_id == user_id))
        if not result.scalar_one_or_none():
            session.add(User(user_id=user_id, username=username, first_name=first_name))
            await session.commit()

        # Check deep link (e.g., /start watch_123)
        args = command.args
        if args and args.startswith("watch_"):
            try:
                movie_number = int(args.split("_")[1])
                movie_result = await session.execute(select(Movie).where(Movie.movie_number == movie_number))
                movie = movie_result.scalar_one_or_none()
                if movie:
                    # Increment views
                    movie.views_count += 1
                    await session.commit()
                    await message.answer_video(
                        video=movie.file_id,
                        caption=f"🎬 <b>#{movie.movie_number} - {movie.title}</b>\n\n{movie.description or ''}",
                        parse_mode="HTML",
                        reply_markup=movie_detail_keyboard(movie.movie_number)
                    )
                    return
            except (ValueError, IndexError):
                pass

    # Normal start
    await message.answer(
        f"Hello, {first_name}! 🎬\n"
        "I'm a movie bot. You can search movies by number or title.\n"
        "Use the buttons below:",
        reply_markup=start_keyboard()
    )

@router.callback_query(F.data == "start_menu")
async def back_to_start(callback: CallbackQuery):
    await callback.message.edit_text(
        f"Hello, {callback.from_user.first_name}! 🎬\n"
        "I'm a movie bot. You can search movies by number or title.\n"
        "Use the buttons below:",
        reply_markup=start_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "about")
async def about_callback(callback: CallbackQuery):
    text = (
        "ℹ️ <b>About Bot</b>\n\n"
        "This bot allows you to search and watch movies by number or title.\n"
        "Only admins can add new movies.\n"
        "Bot creator: @YourUsername"
    )
    await callback.message.edit_text(text, reply_markup=back_to_start_keyboard())
    await callback.answer()