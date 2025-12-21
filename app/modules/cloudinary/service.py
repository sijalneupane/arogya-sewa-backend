import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from fastapi import UploadFile


# Upload image
async def upload_file_cloudinary(file: UploadFile, folder: str):
    """Upload file to Cloudinary"""
    # Read file content
    file_content = await file.read()

    # Upload to Cloudinary
    result = cloudinary.uploader.upload(file_content, folder=folder)

    # Reset file pointer in case it needs to be read again
    await file.seek(0)

    return result.get("secure_url") or result.get("url"), result.get("public_id")


# Delete image using public_id
async def delete_file_cloudinary(public_id: str):
    return cloudinary.uploader.destroy(public_id)


# Generate transformed URL
async def generate_url_cloudinary(public_id, width=None, height=None, crop="fill"):
    url, _ = cloudinary_url(public_id, width=width, height=height, crop=crop)
    return url
