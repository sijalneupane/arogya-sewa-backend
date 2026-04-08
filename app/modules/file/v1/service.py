from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.common.enums.file_meta_type_enum import FileMetaTypeEnum
from app.common.enums.file_type_enum import FileTypeEnum
from app.core import logging_config
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
        if file_type == FileTypeEnum.PROFILE:
            duplicate_profile_query = await db.execute(
                select(File).where(
                    File.user_id == uploaded_by, File.file_type == FileTypeEnum.PROFILE
                )
            )
            duplicate_profile = duplicate_profile_query.scalar_one_or_none()
            if duplicate_profile:
                raise HTTPException(
                    status_code=400, detail="Profile file already exists for user"
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
    current_user_id: str,
    target_user_id: str,
):
    logging_config.logger.info(
        f"Updating file with ID: {file_id} for user: {current_user_id}"
    )
    try:
        file_query = db.execute(select(File).where(File.file_id == file_id))
        file_obj = (await file_query).scalar_one_or_none()
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")

        if file_obj.file_type == FileTypeEnum.PROFILE:
            profile_query = await db.execute(
                select(File).where(
                    File.user_id == target_user_id,  # ✅ FIXED
                    File.file_type == FileTypeEnum.PROFILE,
                )
            )
            existing_profile = profile_query.scalar_one_or_none()

            if not existing_profile:
                raise HTTPException(
                    status_code=400,
                    detail="Cannot update profile image. First upload profile image.",
                )

            # Always replace the user's existing profile image.
            if existing_profile.file_id != file_obj.file_id:
                file_obj = existing_profile

        new_url, new_public_id = await upload_file_cloudinary(
            file, folder="arogyga_images"
        )
        logging_config.logger.info(f"Deleting file with ID: {file_obj.public_id}")
        await delete_file_cloudinary(file_obj.public_id)
        file_obj.public_id = new_public_id
        file_obj.file_url = new_url
        logging_config.logger.info(f"Saving updated file with ID: {file_obj.file_id}")
        db.add(file_obj)
        await db.commit()
        await db.refresh(file_obj)
        return file_obj
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))


async def delete_file(
    db: AsyncSession, file_ids: str | list[str], auto_commit: bool = True
):
    try:
        ids = file_ids if isinstance(file_ids, list) else [file_ids]

        result = await db.execute(select(File).where(File.file_id.in_(ids)))
        files = result.scalars().all()

        if not files:
            raise HTTPException(status_code=404, detail="File(s) not found")

        found_ids = {file.file_id for file in files}
        missing_ids = set(ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=404,
                detail=f"File(s) not found for ID(s): {', '.join(missing_ids)}",
            )

        # Delete from Cloudinary first
        for file in files:
            try:
                await delete_file_cloudinary(file.public_id)
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to delete image from Cloudinary" + str(e),
                )

        # Delete from DB
        for file in files:
            await db.delete(file)

        if auto_commit:
            await db.commit()

        return {"message": "File(s) deleted successfully", "deletedIds": ids}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error: " + str(e))
