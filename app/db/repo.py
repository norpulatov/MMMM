from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Movie, User


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_user(self, user_id: int, username: str | None, first_name: str | None) -> User:
        query = select(User).where(User.user_id == user_id)
        user = (await self.session.execute(query)).scalar_one_or_none()
        if user:
            user.username = username
            user.first_name = first_name
        else:
            user = User(user_id=user_id, username=username, first_name=first_name)
            self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def get_total_users(self) -> int:
        query = select(func.count()).select_from(User)
        return int((await self.session.execute(query)).scalar_one())

    async def list_users(self, limit: int = 50, offset: int = 0) -> list[User]:
        query = select(User).order_by(User.added_at.desc()).offset(offset).limit(limit)
        return list((await self.session.execute(query)).scalars().all())

    async def list_user_ids(self) -> list[int]:
        query = select(User.user_id)
        return list((await self.session.execute(query)).scalars().all())


class MovieRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_movie(
        self,
        *,
        title: str,
        description: str | None,
        file_id: str,
        preview_file_id: str | None,
        added_by: int,
    ) -> Movie:
        max_number_query = select(func.max(Movie.movie_number))
        current_max = (await self.session.execute(max_number_query)).scalar_one()
        next_number = (current_max or 0) + 1

        movie = Movie(
            movie_number=next_number,
            title=title,
            description=description,
            file_id=file_id,
            preview_file_id=preview_file_id,
            added_by=added_by,
        )
        self.session.add(movie)
        await self.session.commit()
        await self.session.refresh(movie)
        return movie

    async def update_channel_post(self, movie_id: int, channel_chat_id: int, channel_post_id: int) -> None:
        query = select(Movie).where(Movie.id == movie_id)
        movie = (await self.session.execute(query)).scalar_one_or_none()
        if not movie:
            return
        movie.channel_chat_id = channel_chat_id
        movie.channel_post_id = channel_post_id
        await self.session.commit()

    async def increment_views(self, movie_number: int) -> None:
        movie = await self.get_by_number(movie_number)
        if not movie:
            return
        movie.views_count += 1
        await self.session.commit()

    async def get_total_movies(self) -> int:
        query = select(func.count()).select_from(Movie)
        return int((await self.session.execute(query)).scalar_one())

    async def get_by_number(self, movie_number: int) -> Movie | None:
        query = select(Movie).where(Movie.movie_number == movie_number)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_movies(self, limit: int = 10, offset: int = 0) -> list[Movie]:
        query = (
            select(Movie)
            .order_by(Movie.movie_number.asc())
            .offset(offset)
            .limit(limit)
        )
        return list((await self.session.execute(query)).scalars().all())

    async def list_latest(self, limit: int = 30) -> list[Movie]:
        query = select(Movie).order_by(Movie.movie_number.desc()).limit(limit)
        return list((await self.session.execute(query)).scalars().all())

    async def search(self, query_text: str, limit: int = 20) -> list[Movie]:
        pattern = f"%{query_text}%"
        query = (
            select(Movie)
            .where(or_(Movie.title.ilike(pattern), Movie.description.ilike(pattern)))
            .order_by(Movie.movie_number.asc())
            .limit(limit)
        )
        return list((await self.session.execute(query)).scalars().all())

    async def delete(self, movie_number: int) -> bool:
        movie = await self.get_by_number(movie_number)
        if not movie:
            return False
        await self.session.delete(movie)
        await self.session.commit()
        return True

    async def update_details(
        self,
        movie_number: int,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> bool:
        movie = await self.get_by_number(movie_number)
        if not movie:
            return False
        if title is not None:
            movie.title = title
        movie.description = description
        await self.session.commit()
        return True
