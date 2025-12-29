from logging import config
from os import error
from fastapi import FastAPI, HTTPException, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.responses import JSONResponse

from app.core.app import app_health
from app.core.config import settings
from app.core.configuration.cloudinary_config import configure_cloudinary
from app.modules.auth.v1 import router as auth_router
from app.modules.availability.v1 import router as availability_router
from app.modules.appointment.v1 import router as appointment_router
from app.modules.appointment.v1 import changed_time_router
from app.modules.doctor.v1 import router as doctor_router
from app.modules.hospital.v1 import router as hospital_router
from app.modules.user.v1 import router as user_router
from app.modules.file.v1 import router as file_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title=settings.APP_NAME, version=settings.VERSION)

configure_cloudinary()

allowed_origins = [
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
    "https://your-production-domain.com.sijal.com",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    print("+++Error occurred:", exc.args)
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
app.include_router(availability_router.router, prefix=settings.API_V1_STR)
app.include_router(appointment_router.router, prefix=settings.API_V1_STR)
app.include_router(changed_time_router.router, prefix=settings.API_V1_STR)
app.include_router(file_router.router, prefix=settings.API_V1_STR)
