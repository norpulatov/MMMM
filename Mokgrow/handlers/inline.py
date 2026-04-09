from aiogram import Router, F
from aiogram.types import InlineQuery
from sqlalchemy import select
from database import AsyncSessionLocal, Movie
from utils import build_inline_results

router = Router()

@router.inline_query(F.query == "")
async def empty_inline_query(inline_query: InlineQuery):
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Movie).order_by(Movie.movie_number.desc()).limit(30))
        movies = result.scalars().all()
    if not movies:
        await inline_query.answer([], switch_pm_text="Movie List", switch_pm_parameter="start")
        return
    results = build_inline_results(movies)
    await inline_query.answer(results, cache_time=10)

@router.inline_query()
async def search_inline_query(inline_query: InlineQuery):
    query = inline_query.query.strip()
    async with AsyncSessionLocal() as session:
        if query.isdigit():
            result = await session.execute(select(Movie).where(Movie.movie_number == int(query)))
            movie = result.scalar_one_or_none()
            if movie:
                results = build_inline_results([movie])
                await inline_query.answer(results, cache_time=60)
                return
        result = await session.execute(
            select(Movie).where(Movie.title.ilike(f"%{query}%")).order_by(Movie.movie_number).limit(20)
        )
        movies = result.scalars().all()
    if not movies:
        await inline_query.answer([], switch_pm_text="No results", switch_pm_parameter="search")
        return
    results = build_inline_results(movies)
    await inline_query.answer(results, cache_time=30)