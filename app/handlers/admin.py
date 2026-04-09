import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from app.keyboards.inline import admin_edit_fields_keyboard, admin_menu_keyboard, admin_movie_actions, admin_movies_page_keyboard, confirm_delete_keyboard
from app.utils.helpers import format_movie_details

logger = logging.getLogger(__name__)
router = Router()


class EditState(StatesGroup):
    waiting_value = State()


@router.message(Command("admin"))
async def admin_menu(message: Message, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("Siz admin emassiz.")
        return
    await message.answer("Admin paneli:", reply_markup=admin_menu_keyboard())


@router.message(Command("stats"))
async def stats_cmd(message: Message, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    await message.answer(f"📊 Statistika\nKinolar: {await crud.count_movies(session)}\nFoydalanuvchilar: {await crud.count_users(session)}")


@router.message(Command("users"))
async def users_cmd(message: Message, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    users = await crud.list_first_users(session, 50)
    if not users:
        await message.answer("Foydalanuvchilar topilmadi.")
        return
    await message.answer("👥 Dastlabki 50 foydalanuvchi:\n" + "\n".join(f"ID: {u.user_id} | {'@' + u.username if u.username else '-'} | {u.first_name}" for u in users))


@router.callback_query(F.data == "admin:stats")
async def stats_callback(call: CallbackQuery, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.message.answer(f"📊 Statistika\nKinolar: {await crud.count_movies(session)}\nFoydalanuvchilar: {await crud.count_users(session)}")
    await call.answer()


@router.callback_query(F.data == "admin:users")
async def users_callback(call: CallbackQuery, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await users_cmd(call.message, session, True)
    await call.answer()


@router.callback_query(F.data.startswith("admin:list:"))
async def admin_list_movies(call: CallbackQuery, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    page = int(call.data.split(":")[2])
    movies = await crud.list_movies(session, page=page, per_page=10)
    if not movies:
        await call.answer("Kino yo'q", show_alert=True)
        return
    await call.message.edit_text("Admin kinolar ro'yxati:", reply_markup=admin_movies_page_keyboard([(m.movie_number, m.title) for m in movies], page, (await crud.count_movies(session)) > page * 10))
    await call.answer()


@router.callback_query(F.data.startswith("admin:movie:"))
async def admin_movie_item(call: CallbackQuery, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    movie = await crud.get_movie_by_number(session, int(call.data.split(":")[2]))
    if not movie:
        await call.answer("Kino topilmadi", show_alert=True)
        return
    await call.message.answer(format_movie_details(movie.movie_number, movie.title, movie.description, movie.views_count, movie.added_at), reply_markup=admin_movie_actions(movie.movie_number))
    await call.answer()


@router.callback_query(F.data.startswith("admin:delete:"))
async def admin_delete_ask(call: CallbackQuery, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    n = int(call.data.split(":")[2])
    await call.message.answer("Haqiqatan ham o'chirmoqchimisiz?", reply_markup=confirm_delete_keyboard(n))
    await call.answer()


@router.callback_query(F.data.startswith("admin:delete_confirm:"))
async def admin_delete_confirm(call: CallbackQuery, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    ok = await crud.delete_movie_by_number(session, int(call.data.split(":")[2]))
    await call.message.answer("✅ Kino o'chirildi va raqamlar qayta tartiblandi." if ok else "Kino topilmadi.")
    await call.answer()


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(call: CallbackQuery) -> None:
    await call.message.answer("Bekor qilindi.")
    await call.answer()


@router.callback_query(F.data.startswith("admin:edit:"))
async def admin_edit_menu(call: CallbackQuery, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    n = int(call.data.split(":")[2])
    await call.message.answer(f"#{n} kino uchun qaysi maydonni tahrirlaysiz?", reply_markup=admin_edit_fields_keyboard(n))
    await call.answer()


@router.callback_query(F.data.startswith("admin:editfield:"))
async def admin_edit_field_pick(call: CallbackQuery, state: FSMContext, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    _, _, field, number = call.data.split(":")
    await state.set_state(EditState.waiting_value)
    await state.update_data(field=field, number=int(number))
    await call.message.answer("Yangi media yuboring (video yoki rasm)." if field in {"file_id", "preview_file_id"} else "Yangi qiymatni yuboring. Tavsif uchun /skip mumkin.")
    await call.answer()


@router.message(EditState.waiting_value, Command("skip"))
async def admin_skip_description(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        return
    data = await state.get_data()
    if data["field"] != "description":
        await message.answer("Bu maydon uchun /skip ishlamaydi.")
        return
    await crud.update_movie_field(session, data["number"], "description", None)
    await message.answer("Tavsif yangilandi.")
    await state.clear()


@router.message(EditState.waiting_value, F.video)
async def admin_edit_video(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        return
    data = await state.get_data()
    if data["field"] != "file_id":
        await message.answer("Bu yerda video kutilmagan.")
        return
    await crud.update_movie_field(session, data["number"], "file_id", message.video.file_id)
    await message.answer("Video yangilandi.")
    await state.clear()


@router.message(EditState.waiting_value, F.photo)
async def admin_edit_preview(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        return
    data = await state.get_data()
    if data["field"] != "preview_file_id":
        await message.answer("Bu yerda rasm kutilmagan.")
        return
    await crud.update_movie_field(session, data["number"], "preview_file_id", message.photo[-1].file_id)
    await message.answer("Preview yangilandi.")
    await state.clear()


@router.message(EditState.waiting_value, F.text)
async def admin_edit_text(message: Message, state: FSMContext, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        return
    data = await state.get_data()
    if data["field"] not in {"title", "description"}:
        await message.answer("Iltimos, to'g'ri media yuboring.")
        return
    await crud.update_movie_field(session, data["number"], data["field"], message.text.strip())
    await message.answer("Maydon yangilandi.")
    await state.clear()


@router.message(Command("broadcast"))
async def broadcast_cmd(message: Message, session: AsyncSession, is_admin: bool) -> None:
    if not is_admin:
        await message.answer("Bu buyruq faqat adminlar uchun.")
        return
    if not message.reply_to_message:
        await message.answer("Yuboriladigan xabarga reply qilib /broadcast yozing.")
        return
    users = await crud.list_first_users(session, limit=1_000_000)
    sent = 0
    failed = 0
    for user in users:
        try:
            await message.reply_to_message.copy_to(chat_id=user.user_id)
            sent += 1
        except Exception:
            failed += 1
    logger.info("Broadcast yakuni: sent=%s failed=%s", sent, failed)
    await message.answer(f"📢 Xabar yuborildi.\nMuvaffaqiyatli: {sent}\nXato: {failed}")


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_help_callback(call: CallbackQuery, is_admin: bool) -> None:
    if not is_admin:
        await call.answer("Ruxsat yo'q", show_alert=True)
        return
    await call.message.answer("Xabar yuborish uchun kerakli xabarga reply qiling va /broadcast yuboring.")
    await call.answer()
