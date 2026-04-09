from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils import get_watch_deep_link

def start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Movie List", callback_data="movies_list")
    builder.button(text="🔍 Search", callback_data="search_prompt")
    builder.button(text="ℹ️ About", callback_data="about")
    builder.adjust(1)
    return builder.as_markup()

def movie_detail_keyboard(movie_number: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="▶️ Watch", url=get_watch_deep_link(movie_number))
    builder.button(text="🔄 Refresh", callback_data=f"refresh_{movie_number}")
    builder.button(text="🏠 Main Menu", callback_data="start_menu")
    builder.adjust(1)
    return builder.as_markup()

def back_to_start_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🏠 Main Menu", callback_data="start_menu")
    return builder.as_markup()

def admin_panel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="📋 Movie List (Admin)", callback_data="admin_movies")
    builder.button(text="📊 Statistics", callback_data="admin_stats")
    builder.button(text="👥 Users", callback_data="admin_users")
    builder.button(text="📢 Broadcast", callback_data="admin_broadcast")
    builder.button(text="❌ Close", callback_data="start_menu")
    builder.adjust(1)
    return builder.as_markup()

def admin_movie_actions(movie_id: int, movie_number: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="✏️ Edit", callback_data=f"edit_{movie_id}")
    builder.button(text="🗑 Delete", callback_data=f"delete_{movie_id}")
    builder.button(text="◀️ Back", callback_data="admin_movies")
    return builder.as_markup()