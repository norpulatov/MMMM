from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.repo import MovieRepo, UserRepo
from app.keyboards.common import (
    admin_menu_keyboard,
    admin_movie_actions,
    admin_movies_list_keyboard,
    public_watch_keyboard,
)
from app.states.upload import EditMovieStates, UploadMovieStates
from app.utils.formatters import movie_announcement_caption, movie_details_text

router = Router()
logger = logging.getLogger(__name__)


def _is_admin(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    await message.answer("Admin panel:", reply_markup=admin_menu_keyboard())


@router.message(Command("stats"))
async def stats_command(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    movie_repo = MovieRepo(session)
    user_repo = UserRepo(session)
    total_movies = await movie_repo.get_total_movies()
    total_users = await user_repo.get_total_users()
    await message.answer(f"📈 Movies: {total_movies}\n👥 Users: {total_users}")


@router.message(Command("users"))
async def users_command(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    user_repo = UserRepo(session)
    users = await user_repo.list_users(limit=50)
    if not users:
        await message.answer("No users found.")
        return
    lines = ["👥 First 50 users:"]
    for user in users:
        name = user.first_name or "-"
        username = f"@{user.username}" if user.username else "-"
        lines.append(f"{user.user_id} | {name} | {username}")
    await message.answer("\n".join(lines))


@router.message(Command("broadcast"))
async def broadcast_command(
    message: Message,
    bot: Bot,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    if not message.reply_to_message:
        await message.answer("Reply to a message with /broadcast to send it to all users.")
        return

    user_repo = UserRepo(session)
    user_ids = await user_repo.list_user_ids()
    success = 0
    failed = 0
    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.reply_to_message.message_id,
            )
            success += 1
        except Exception:
            failed += 1
    await message.answer(f"Broadcast finished.\n✅ Sent: {success}\n❌ Failed: {failed}")


@router.message(F.video)
async def admin_upload_video_start(
    message: Message,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    if not message.forward_origin:
        await message.answer("Please forward a video from another chat/channel.")
        return

    await state.set_state(UploadMovieStates.waiting_title)
    await state.update_data(video_file_id=message.video.file_id)
    await message.answer("Enter movie title:")


@router.message(UploadMovieStates.waiting_title)
async def upload_title_step(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    title = (message.text or "").strip()
    if not title:
        await message.answer("Title cannot be empty. Enter movie title:")
        return
    await state.update_data(title=title)
    await state.set_state(UploadMovieStates.waiting_description)
    await message.answer("Send description or /skip.")


@router.message(UploadMovieStates.waiting_description, Command("skip"))
async def upload_skip_description(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    await state.update_data(description=None)
    await state.set_state(UploadMovieStates.waiting_preview)
    await message.answer("Send preview image or /skip.")


@router.message(UploadMovieStates.waiting_description)
async def upload_description_step(message: Message, state: FSMContext, settings: Settings) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    description = (message.text or "").strip()
    if not description:
        await message.answer("Send description text or /skip.")
        return
    await state.update_data(description=description)
    await state.set_state(UploadMovieStates.waiting_preview)
    await message.answer("Send preview image or /skip.")


@router.message(UploadMovieStates.waiting_preview, Command("skip"))
async def upload_skip_preview(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    await finish_upload(
        message=message,
        state=state,
        session=session,
        bot=bot,
        settings=settings,
        preview_file_id=None,
    )


@router.message(UploadMovieStates.waiting_preview, F.photo)
async def upload_preview_step(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    preview_file_id = message.photo[-1].file_id
    await finish_upload(
        message=message,
        state=state,
        session=session,
        bot=bot,
        settings=settings,
        preview_file_id=preview_file_id,
    )


async def finish_upload(
    *,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    bot: Bot,
    settings: Settings,
    preview_file_id: str | None,
) -> None:
    payload = await state.get_data()
    await state.clear()

    title = payload.get("title")
    description = payload.get("description")
    video_file_id = payload.get("video_file_id")

    if not title or not video_file_id:
        await message.answer("Upload session is invalid. Please start again.")
        return

    movie_repo = MovieRepo(session)
    movie = await movie_repo.create_movie(
        title=title,
        description=description,
        file_id=video_file_id,
        preview_file_id=preview_file_id,
        added_by=message.from_user.id,
    )

    caption = movie_announcement_caption(movie.movie_number, movie.title, movie.description)
    keyboard = public_watch_keyboard(settings.bot_username, movie.movie_number)

    try:
        if preview_file_id:
            posted = await bot.send_photo(
                chat_id=settings.channel_id,
                photo=preview_file_id,
                caption=caption,
                reply_markup=keyboard,
            )
        else:
            posted = await bot.send_message(
                chat_id=settings.channel_id,
                text=caption,
                reply_markup=keyboard,
            )
    except Exception:
        logger.exception("Failed to publish channel announcement for #%s", movie.movie_number)
        await message.answer(
            f"Movie #{movie.movie_number} saved, but channel post failed. Check channel permissions."
        )
        return

    await movie_repo.update_channel_post(
        movie_id=movie.id,
        channel_chat_id=posted.chat.id,
        channel_post_id=posted.message_id,
    )

    post_link = f"https://t.me/c/{str(abs(posted.chat.id)).replace('100', '', 1)}/{posted.message_id}"
    await message.answer(f"✅ Movie #{movie.movie_number} saved.\nChannel post: {post_link}")


@router.callback_query(F.data == "admin:stats")
async def admin_stats_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    movie_repo = MovieRepo(session)
    user_repo = UserRepo(session)
    total_movies = await movie_repo.get_total_movies()
    total_users = await user_repo.get_total_users()
    await callback.message.edit_text(f"📈 Movies: {total_movies}\n👥 Users: {total_users}")
    await callback.answer()


@router.callback_query(F.data == "admin:users")
async def admin_users_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    user_repo = UserRepo(session)
    users = await user_repo.list_users(limit=20)
    if not users:
        await callback.message.edit_text("No users found.")
    else:
        lines = ["👥 Recent users:"]
        for user in users:
            username = f"@{user.username}" if user.username else "-"
            lines.append(f"{user.user_id} | {user.first_name or '-'} | {username}")
        await callback.message.edit_text("\n".join(lines))
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast_help")
async def admin_broadcast_help(callback: CallbackQuery, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    await callback.message.edit_text("Reply to any message with /broadcast to send it to all users.")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:movies:"))
async def admin_movies_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    page_raw = callback.data.rsplit(":", maxsplit=1)[-1]
    page = int(page_raw) if page_raw.isdigit() else 1
    per_page = 10
    movie_repo = MovieRepo(session)
    total = await movie_repo.get_total_movies()
    offset = (max(page, 1) - 1) * per_page
    movies = await movie_repo.list_movies(limit=per_page, offset=offset)
    if not movies:
        await callback.message.edit_text("No movies found.")
        await callback.answer()
        return

    await callback.message.edit_text(
        "🎬 Admin movie list:",
        reply_markup=admin_movies_list_keyboard(
            movies,
            current_page=max(page, 1),
            total_count=total,
            per_page=per_page,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_movie(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    value = callback.data.rsplit(":", maxsplit=1)[-1]
    if not value.isdigit():
        await callback.answer("Invalid movie number", show_alert=True)
        return
    movie_number = int(value)
    movie_repo = MovieRepo(session)
    deleted = await movie_repo.delete(movie_number)
    if deleted:
        await callback.message.edit_text(f"🗑 Movie #{movie_number} deleted.")
    else:
        await callback.message.edit_text(f"Movie #{movie_number} not found.")
    await callback.answer()


@router.callback_query(F.data.startswith("admin:edit:"))
async def admin_edit_movie_start(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    value = callback.data.rsplit(":", maxsplit=1)[-1]
    if not value.isdigit():
        await callback.answer("Invalid movie number", show_alert=True)
        return
    movie_number = int(value)
    await state.set_state(EditMovieStates.waiting_payload)
    await state.update_data(edit_movie_number=movie_number)
    await callback.message.answer(
        f"Editing movie #{movie_number}.\n"
        "Send: <new title> | <new description>\n"
        "Use /skip as description to clear it."
    )
    await callback.answer()


@router.message(EditMovieStates.waiting_payload)
async def admin_edit_movie_finish(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not _is_admin(message.from_user.id, settings):
        return
    payload = (message.text or "").strip()
    if "|" not in payload:
        await message.answer("Invalid format. Send: <new title> | <new description>")
        return
    title, description = [part.strip() for part in payload.split("|", maxsplit=1)]
    if not title:
        await message.answer("Title cannot be empty.")
        return
    if description.lower() == "/skip":
        description = None

    data = await state.get_data()
    movie_number = data.get("edit_movie_number")
    await state.clear()
    if not isinstance(movie_number, int):
        await message.answer("Edit session expired. Try again.")
        return

    movie_repo = MovieRepo(session)
    updated = await movie_repo.update_details(movie_number, title=title, description=description)
    if not updated:
        await message.answer(f"Movie #{movie_number} not found.")
        return
    movie = await movie_repo.get_by_number(movie_number)
    if not movie:
        await message.answer(f"Movie #{movie_number} not found after update.")
        return
    await message.answer(
        f"✅ Movie #{movie_number} updated.",
        reply_markup=admin_movie_actions(movie_number),
    )
    await message.answer(movie_details_text(movie))


@router.callback_query(F.data.startswith("admin:movie:"))
async def admin_movie_details_callback(callback: CallbackQuery, session: AsyncSession, settings: Settings) -> None:
    if not _is_admin(callback.from_user.id, settings):
        return
    value = callback.data.rsplit(":", maxsplit=1)[-1]
    if not value.isdigit():
        return
    movie_repo = MovieRepo(session)
    movie = await movie_repo.get_by_number(int(value))
    if not movie:
        await callback.answer("Movie not found", show_alert=True)
        return
    await callback.message.edit_text(
        movie_details_text(movie),
        reply_markup=admin_movie_actions(movie.movie_number),
    )
    await callback.answer()
