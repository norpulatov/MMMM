from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import Movie


def main_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Movie List", callback_data="menu:movies:1")
    kb.button(text="🔎 Search", callback_data="menu:search")
    kb.button(text="ℹ️ About", callback_data="menu:about")
    kb.adjust(1)
    return kb.as_markup()


def watch_keyboard(movie_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="▶️ Watch", callback_data=f"watch:{movie_number}")]
        ]
    )


def public_watch_keyboard(bot_username: str, movie_number: int) -> InlineKeyboardMarkup:
    deep_link = f"https://t.me/{bot_username}?start=watch_{movie_number}"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="▶️ Watch", url=deep_link)]]
    )


def movies_list_keyboard(
    movies: list[Movie], current_page: int, total_count: int, per_page: int = 10, admin_mode: bool = False
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for movie in movies:
        suffix = " (admin)" if admin_mode else ""
        kb.button(
            text=f"#{movie.movie_number} - {movie.title[:32]}{suffix}",
            callback_data=f"movie:{movie.movie_number}",
        )

    total_pages = max((total_count + per_page - 1) // per_page, 1)
    nav_row: list[InlineKeyboardButton] = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"menu:movies:{current_page - 1}",
            )
        )
    nav_row.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop",
        )
    )
    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"menu:movies:{current_page + 1}",
            )
        )

    if nav_row:
        kb.row(*nav_row)
    return kb.as_markup()


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🎬 Movie List (admin)", callback_data="admin:movies:1")
    kb.button(text="📈 Statistics", callback_data="admin:stats")
    kb.button(text="👥 Users", callback_data="admin:users")
    kb.button(text="📣 Broadcast", callback_data="admin:broadcast_help")
    kb.adjust(1)
    return kb.as_markup()


def admin_movie_actions(movie_number: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶️ Watch", callback_data=f"watch:{movie_number}"),
                InlineKeyboardButton(text="✏️ Edit", callback_data=f"admin:edit:{movie_number}"),
                InlineKeyboardButton(text="🗑 Delete", callback_data=f"admin:delete:{movie_number}"),
            ]
        ]
    )


def admin_movies_list_keyboard(
    movies: list[Movie], current_page: int, total_count: int, per_page: int = 10
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for movie in movies:
        kb.button(
            text=f"#{movie.movie_number} - {movie.title[:30]}",
            callback_data=f"admin:movie:{movie.movie_number}",
        )

    total_pages = max((total_count + per_page - 1) // per_page, 1)
    nav_row: list[InlineKeyboardButton] = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Prev",
                callback_data=f"admin:movies:{current_page - 1}",
            )
        )
    nav_row.append(InlineKeyboardButton(text=f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Next ➡️",
                callback_data=f"admin:movies:{current_page + 1}",
            )
        )
    if nav_row:
        kb.row(*nav_row)

    return kb.as_markup()
