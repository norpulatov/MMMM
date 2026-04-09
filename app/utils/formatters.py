from __future__ import annotations

from app.db.models import Movie


def movie_details_text(movie: Movie) -> str:
    desc = movie.description or "No description."
    added_at = movie.added_at.strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"🎬 <b>#{movie.movie_number} - {movie.title}</b>\n\n"
        f"{desc}\n\n"
        f"👁 Views: <b>{movie.views_count}</b>\n"
        f"🗓 Added: <b>{added_at}</b>"
    )


def movie_announcement_caption(movie_number: int, title: str, description: str | None) -> str:
    text = f"🎬 <b>#{movie_number} - {title}</b>"
    if description:
        text += f"\n\n{description}"
    return text
