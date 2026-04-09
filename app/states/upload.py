from aiogram.fsm.state import State, StatesGroup


class UploadMovieStates(StatesGroup):
    waiting_title = State()
    waiting_description = State()
    waiting_preview = State()


class EditMovieStates(StatesGroup):
    waiting_payload = State()
