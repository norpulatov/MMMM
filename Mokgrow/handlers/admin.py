from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select, func, update, delete
from database import AsyncSessionLocal, User, Movie
from config import ADMIN_IDS, CHANNEL_ID, BOT_USERNAME
from keyboards.inline import admin_panel_keyboard, back_to_start_keyboard, admin_movie_actions
from utils import logger
import asyncio

router = Router()

class MovieUpload(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_preview = State()

def admin_filter(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS

# ========== ADMIN PANEL ==========
@router.message(Command("admin"), admin_filter)
async def cmd_admin(message: Message):
    await message.answer("👑 Admin Panel\nChoose an action:", reply_markup=admin_panel_keyboard())

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    await callback.message.edit_text("👑 Admin Panel\nChoose an action:", reply_markup=admin_panel_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats_callback(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        movie_count = await session.scalar(select(func.count()).select_from(Movie))
        user_count = await session.scalar(select(func.count()).select_from(User))
    await callback.message.edit_text(
        f"📊 Statistics:\n\n🎬 Movies: {movie_count}\n👥 Users: {user_count}",
        reply_markup=back_to_start_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users_callback(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).order_by(User.added_at.desc()).limit(30))
        users = result.scalars().all()
    if not users:
        text = "No users found."
    else:
        text = "👥 Recent 30 users:\n\n"
        for u in users:
            text += f"• {u.user_id} - {u.first_name or 'Unknown'} (@{u.username or 'none'})\n"
    await callback.message.edit_text(text, reply_markup=back_to_start_keyboard())
    await callback.answer()

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_prompt(callback: CallbackQuery):
    await callback.message.edit_text(
        "📢 To broadcast, reply to a message with /broadcast",
        reply_markup=back_to_start_keyboard()
    )
    await callback.answer()

@router.message(Command("broadcast"), admin_filter)
async def cmd_broadcast(message: Message):
    if not message.reply_to_message:
        await message.answer("Reply to a message to broadcast.")
        return
    text = message.reply_to_message.text or message.reply_to_message.caption
    if not text:
        await message.answer("Reply to a text message.")
        return
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User.user_id))
        user_ids = [row[0] for row in result.all()]
    success = 0
    for uid in user_ids:
        try:
            await message.bot.send_message(uid, text)
            success += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Failed to send to {uid}: {e}")
    await message.answer(f"✅ Message sent to {success}/{len(user_ids)} users.")

# ========== MOVIE UPLOAD (admin forwards video) ==========
@router.message(F.video | (F.document & F.document.mime_type.startswith("video/")), admin_filter)
async def admin_video_received(message: Message, state: FSMContext):
    if message.video:
        file_id = message.video.file_id
    else:
        file_id = message.document.file_id

    await state.update_data(file_id=file_id)
    await state.set_state(MovieUpload.waiting_for_title)
    await message.answer("🎬 Send movie title:")

@router.message(MovieUpload.waiting_for_title, admin_filter)
async def process_title(message: Message, state: FSMContext):
    title = message.text.strip()
    if len(title) > 200:
        await message.answer("Title too long. Max 200 characters.")
        return
    await state.update_data(title=title)
    await state.set_state(MovieUpload.waiting_for_description)
    await message.answer("📝 Send description (or /skip):")

@router.message(MovieUpload.waiting_for_description, admin_filter)
async def process_description(message: Message, state: FSMContext):
    if message.text == "/skip":
        description = ""
    else:
        description = message.text.strip()
    await state.update_data(description=description)
    await state.set_state(MovieUpload.waiting_for_preview)
    await message.answer("🖼 Send optional preview image (or /skip):")

@router.message(MovieUpload.waiting_for_preview, admin_filter, F.photo | F.text)
async def process_preview(message: Message, state: FSMContext):
    if message.photo:
        preview_file_id = message.photo[-1].file_id
    else:
        preview_file_id = None

    data = await state.get_data()
    file_id = data["file_id"]
    title = data["title"]
    description = data["description"]

    async with AsyncSessionLocal() as session:
        # Get next movie number
        result = await session.execute(select(func.max(Movie.movie_number)))
        max_num = result.scalar() or 0
        next_number = max_num + 1

        # Create announcement post in channel
        watch_url = f"https://t.me/{BOT_USERNAME}?start=watch_{next_number}"
        caption = f"🎬 <b>#{next_number} - {title}</b>\n\n{description or ''}"
        keyboard = InlineKeyboardBuilder().button(text="▶️ Watch", url=watch_url).as_markup()

        try:
            if preview_file_id:
                post_msg = await message.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=preview_file_id,
                    caption=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                post_msg = await message.bot.send_message(
                    chat_id=CHANNEL_ID,
                    text=caption,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            post_id = post_msg.message_id
        except Exception as e:
            logger.error(f"Failed to post to channel: {e}")
            await message.answer("❌ Failed to post to channel.")
            await state.clear()
            return

        movie = Movie(
            movie_number=next_number,
            title=title,
            description=description,
            file_id=file_id,
            preview_file_id=preview_file_id,
            channel_post_id=post_id,
            channel_chat_id=CHANNEL_ID,
            added_by=message.from_user.id
        )
        session.add(movie)
        await session.commit()

        await message.answer(f"✅ Movie #{next_number} added successfully!\n📎 Channel post: https://t.me/c/{CHANNEL_ID[4:]}/{post_id}")
    await state.clear()

# ========== ADMIN MOVIE LIST & ACTIONS ==========
@router.callback_query(F.data == "admin_movies")
async def admin_movies_list(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).order_by(Movie.movie_number.desc()).limit(20))
        movies = result.scalars().all()
    if not movies:
        await callback.message.edit_text("No movies found.", reply_markup=back_to_start_keyboard())
        await callback.answer()
        return
    text = "📋 Admin Movie List (last 20):\n\n"
    for m in movies:
        text += f"#{m.movie_number} - {m.title}\n"
    await callback.message.edit_text(text, reply_markup=back_to_start_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_"))
async def edit_movie_callback(callback: CallbackQuery):
    # Simplified: you can expand with state for editing
    await callback.answer("Edit feature coming soon.", show_alert=True)

@router.callback_query(F.data.startswith("delete_"))
async def delete_movie_callback(callback: CallbackQuery):
    movie_id = int(callback.data.split("_")[1])
    async with AsyncSessionLocal() as session:
        movie = await session.get(Movie, movie_id)
        if movie:
            await session.delete(movie)
            await session.commit()
            await callback.message.edit_text("✅ Movie deleted.", reply_markup=back_to_start_keyboard())
        else:
            await callback.answer("Movie not found.", show_alert=True)
    await callback.answer()