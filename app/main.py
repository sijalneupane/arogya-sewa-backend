from fastapi import FastAPI

from app.core.app import app_health
from app.core.config import settings
from app.modules.auth.v1 import router as auth_router
from app.modules.user.v1 import router as user_router

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.include_router(app_health.router, prefix=settings.API_V1_STR)
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(user_router.router, prefix=settings.API_V1_STR)
