from .start import router as start_router
from .admin import router as admin_router
from .movies import router as movies_router
from .callback import router as callback_router
from .inline import router as inline_router

routers = [start_router, admin_router, movies_router, callback_router, inline_router]