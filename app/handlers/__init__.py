from aiogram import Dispatcher

from app.handlers import admin, inline_mode, user


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(admin.router)
    dp.include_router(user.router)
    dp.include_router(inline_mode.router)
