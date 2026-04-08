from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.common.enums.file_type_enum import FileTypeEnum
from app.common.enums.role_enum import RoleEnum
from app.core.security import get_current_user
from app.db.db import get_db
from app.modules.auth.v1.schemas import JwtPayload
from app.modules.file.v1.service import delete_file, save_file, update_file
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


@router.patch("/update/{file_id}")
async def update_route(
    file_id: str,
    target_user_id: str,  # 👈 from query/body
    file: UploadFile = File(...),
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a file and return its new URL.
    """
    if (
        current_user.role not in [RoleEnum.SUPER_ADMIN, RoleEnum.HOSPITAL_ADMIN]
        and current_user.sub != target_user_id
    ):
        raise HTTPException(status_code=403, detail="Not authorized")
    updated_file = await update_file(
        db=db,
        file=file,
        file_id=file_id,
        current_user_id=current_user.sub,
        target_user_id=target_user_id,
    )
    return updated_file


@router.delete("/delete/{file_id}", summary="Delete a file")
async def delete_route(
    file_id: str,
    current_user: JwtPayload = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a file.
    """
    await delete_file(db=db, file_ids=file_id)
    return {"detail": "File deleted successfully"}


# @router.post("/upload/profile", summary="Upload a profile file")
# async def upload_profile_route(
#     file: UploadFile = File(...),
#     file_type: FileTypeEnum = Form(FileTypeEnum.HOSPITAL),  # 👈 now body (form-data)
#     current_user: JwtPayload = Depends(get_current_user),
#     db: AsyncSession = Depends(get_db),
# ):
#     """
#     Upload a file and return its URL.
#     """
#     file_info = await save_file(
#         db=db, file=file, uploaded_by=current_user.sub, file_type=file_type
#     )
#     return file_info
