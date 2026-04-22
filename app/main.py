from contextlib import asynccontextmanager
from logging import config
from os import error

from fastapi import FastAPI, status
from fastapi.exceptions import RequestValidationError, ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.app import app_health
from app.core.config import settings
from app.core.configuration.cloudinary_config import configure_cloudinary
from app.core.configuration.firebase_config import init_firebase
from app.core.configuration.khalti_config import init_khalti
from app.core.configuration.mailgun_config import init_mailgun
from app.core.scheduler.manager import shutdown_app_scheduler, start_app_scheduler
from app.modules.appointment.v1 import changed_time_router
from app.modules.appointment.v1 import router as appointment_router
from app.modules.auth.v1 import router as auth_router
from app.modules.availability.v1 import router as availability_router
from app.modules.department.v1 import router as department_router
from app.modules.dashboard.v1 import router as dashboard_router
from app.modules.doctor.v1 import router as doctor_router
from app.modules.file.v1 import router as file_router
from app.modules.hospital.v1 import router as hospital_router
from app.modules.email.v1 import router as email_router
from app.modules.notification.v1 import router as notification_router
from app.modules.patient.v1 import router as patient_router
from app.modules.payment.v1 import router as payment_router
from app.modules.user.v1 import router as user_router


def startup_event():
    init_firebase()
    configure_cloudinary()
    init_khalti()
    init_mailgun()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code
    startup_event()
    start_app_scheduler()
    yield
    # Shutdown code (if any)
    shutdown_app_scheduler()


app = FastAPI(title=settings.APP_NAME, version=settings.VERSION, lifespan=lifespan)

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
app.include_router(patient_router.router, prefix=settings.API_V1_STR)
app.include_router(availability_router.router, prefix=settings.API_V1_STR)
app.include_router(department_router.router, prefix=settings.API_V1_STR)
app.include_router(appointment_router.router, prefix=settings.API_V1_STR)
app.include_router(changed_time_router.router, prefix=settings.API_V1_STR)
app.include_router(payment_router.router, prefix=settings.API_V1_STR)
app.include_router(file_router.router, prefix=settings.API_V1_STR)
app.include_router(email_router.router, prefix=settings.API_V1_STR)
app.include_router(notification_router.router, prefix=settings.API_V1_STR)
app.include_router(dashboard_router.router, prefix=settings.API_V1_STR)
