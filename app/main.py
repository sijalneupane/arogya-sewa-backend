from os import error
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse

from app.core.app import app_health
from app.core.config import settings
from app.modules.auth.v1 import router as auth_router
from app.modules.doctor.v1 import router as doctor_router
from app.modules.hospital.v1 import router as hospital_router
from app.modules.user.v1 import router as user_router

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(
    RequestValidationError,
)
async def validation_exception_handler(request, exc: RequestValidationError):
    error_list = []
    for err in exc.errors():
        error_list.append(err["msg"])
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "detail": error_list,
            "status": status.HTTP_400_BAD_REQUEST,
        },
    )


@app.exception_handler(ResponseValidationError)
async def response_validation_exception_handler(request, exc: ResponseValidationError):
    error_list = []
    for err in exc.errors():
        error_list.append(err["msg"])
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": error_list,
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )


app.include_router(app_health.router, prefix=settings.API_V1_STR)
app.include_router(auth_router.router, prefix=settings.API_V1_STR)
app.include_router(user_router.router, prefix=settings.API_V1_STR)
app.include_router(hospital_router.router, prefix=settings.API_V1_STR)
app.include_router(doctor_router.router, prefix=settings.API_V1_STR)
