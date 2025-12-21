from fastapi import Depends, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.enums.file_meta_type_enum import FileMetaTypeEnum
from app.common.enums.file_type_enum import FileTypeEnum
from app.core.utils.string_utils import StringUtils
from app.modules.cloudinary.service import (
    delete_file_cloudinary,
    upload_file_cloudinary,
)
from app.modules.file.v1.models import File


async def save_file(
    db: AsyncSession,
    file: UploadFile,
    uploaded_by: str,
    file_type: FileTypeEnum,
) -> File:
    try:
        if file.size is not None and file.size > 2 * 1024 * 1024:  # 10 MB limit
            raise HTTPException(
                status_code=400, detail="File size exceeds the 2MB limit"
            )
        url, public_id = await upload_file_cloudinary(file, folder="arogyga_images")
        new_file = File(
            file_id="F" + StringUtils.randomAlphaNumeric(7),
            public_id=public_id,
            file_url=url,
            file_type=file_type,
            user_id=uploaded_by,
        )
        if file.content_type and file.content_type.startswith("image/"):
            new_file.meta_type = FileMetaTypeEnum.image
        elif file.content_type and file.content_type.startswith("video/"):
            new_file.meta_type = FileMetaTypeEnum.video
        elif file.content_type and file.content_type == "application/pdf":
            new_file.meta_type = FileMetaTypeEnum.pdf
        db.add(new_file)
        await db.commit()
        await db.refresh(new_file)
        result = await db.execute(select(File).where(File.file_id == new_file.file_id))
        saved_file = result.scalar_one()
        return saved_file
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))


async def update_file(
    db: AsyncSession,
    file: UploadFile,
    # file_type: FileTypeEnum,
    file_id: str,
):
    try:
        file_query = db.execute(select(File).where(File.file_id == file_id))
        file_obj = (await file_query).scalar_one_or_none()
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")
        new_url, new_public_id = await upload_file_cloudinary(
            file, folder="arogyga_images"
        )
        await delete_file_cloudinary(file_obj.public_id)
        file_obj.public_id = new_public_id
        file_obj.file_url = new_url
        db.add(file_obj)
        await db.commit()
        await db.refresh(file_obj)
        return file_obj
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))


async def delete_file(db: AsyncSession, file_id: str):
    try:
        result = await db.execute(select(File).where(File.file_id == file_id))
        file_obj = result.scalar_one_or_none()
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")
        await delete_file_cloudinary(file_obj.public_id)
        await db.delete(file_obj)
        await db.commit()
        return True
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))
