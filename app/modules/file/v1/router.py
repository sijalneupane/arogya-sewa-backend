from fastapi import APIRouter, Depends, File, UploadFile
from app.common.enums.file_type_enum import FileTypeEnum
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.file.v1.service import saveFile
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/file",
    tags=["Files"],
)
@router.post("/upload", summary="Upload a file")
async def upload_route(
    file: UploadFile = File(...),
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    file_type: FileTypeEnum = FileTypeEnum.HOSPITAL,
):
    """
    Upload a file and return its URL.
    """
    file_info = await saveFile(
        db=db, file=file, uploaded_by=current_user.sub, file_type=file_type
    )
    return file_info
