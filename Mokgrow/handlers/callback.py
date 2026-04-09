from aiogram import Router, F
from aiogram.types import CallbackQuery
from .movies import show_movies_page

router = Router()

@router.callback_query(F.data == "movies_list")
async def movies_list_callback(callback: CallbackQuery):
    await show_movies_page(callback, page=1, edit=True)
    await callback.answer()

@router.callback_query(F.data == "search_prompt")
async def search_prompt_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "Send me a movie title or number.\nExample: /search Avatar or just 42",
        reply_markup=None
    )
    await callback.answer()