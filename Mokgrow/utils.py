import logging
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineQueryResultArticle, InputTextMessageContent
from config import BOT_USERNAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_watch_deep_link(movie_number: int) -> str:
    """Generate deep link that starts bot and sends video."""
    return f"https://t.me/{BOT_USERNAME}?start=watch_{movie_number}"

def build_movies_keyboard(movies, page: int, total_pages: int):
    builder = InlineKeyboardBuilder()
    for movie in movies:
        builder.button(
            text=f"#{movie.movie_number} - {movie.title[:30]}",
            callback_data=f"view_{movie.movie_number}"
        )
    builder.adjust(1)
    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton(text="⬅️ Previous", callback_data=f"page_{page-1}"))
    if page < total_pages:
        nav.append(InlineKeyboardButton(text="Next ➡️", callback_data=f"page_{page+1}"))
    if nav:
        builder.row(*nav)
    return builder.as_markup()

def build_inline_results(movies):
    results = []
    for movie in movies:
        results.append(
            InlineQueryResultArticle(
                id=str(movie.movie_number),
                title=f"#{movie.movie_number} - {movie.title}",
                description=movie.description[:100] if movie.description else None,
                input_message_content=InputTextMessageContent(
                    message_text=f"🎬 <b>#{movie.movie_number} - {movie.title}</b>\n\n{movie.description or ''}\n\n👁 Views: {movie.views_count}",
                    parse_mode="HTML"
                ),
                reply_markup=InlineKeyboardBuilder().button(
                    text="▶️ Watch", url=get_watch_deep_link(movie.movie_number)
                ).as_markup()
            )
        )
    return results