from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.common.enums.file_type_enum import FileTypeEnum
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.file.v1.service import save_file, update_file
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/file",
    tags=["Files"],
)


@router.post("/upload", summary="Upload a file")
async def upload_route(
    file: UploadFile = File(...),
    file_type: FileTypeEnum = Form(FileTypeEnum.HOSPITAL),  # 👈 now body (form-data)
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload a file and return its URL.
    """
    file_info = await save_file(
        db=db, file=file, uploaded_by=current_user.sub, file_type=file_type
    )
    return file_info


@router.patch("/update/{file_id}", summary="Update a file")
async def update_route(
    file_id: str,
    file: UploadFile = File(...),
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a file and return its new URL.
    """
    updated_file = await update_file(db=db, file=file, file_id=file_id)
    return updated_file
