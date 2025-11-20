from fastapi import FastAPI

from api.v1.routers import auth_route, user_route
from app.api.v1.routers import app_health
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

app.include_router(app_health.router, prefix=settings.API_V1_STR)
app.include_router(auth_route.router, prefix=settings.API_V1_STR)
app.include_router(user_route.router, prefix=settings.API_V1_STR)
