import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from fastapi import UploadFile


# Upload image
async def upload_image(file: UploadFile, folder: str):
    """Upload file to Cloudinary"""
    # Read file content
    file_content = await file.read()

    # Upload to Cloudinary
    result = cloudinary.uploader.upload(file_content, folder=folder)

    # Reset file pointer in case it needs to be read again
    await file.seek(0)

    return result.get("secure_url") or result.get("url"), result.get("public_id")


# Delete image using public_id
def delete_image(public_id: str):
    return cloudinary.uploader.destroy(public_id)


# Generate transformed URL
def generate_url(public_id, width=None, height=None, crop="fill"):
    url, _ = cloudinary_url(public_id, width=width, height=height, crop=crop)
    return url
