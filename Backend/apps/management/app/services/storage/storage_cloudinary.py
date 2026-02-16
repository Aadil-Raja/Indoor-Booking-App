"""
Shared Cloudinary Service
Reusable functions for uploading and deleting images and videos to Cloudinary.
"""

import io
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


def configure_cloudinary(cloud_name: str, api_key: str, api_secret: str):
    """Configure Cloudinary with credentials."""
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


def is_cloudinary_configured() -> bool:
    """Check if Cloudinary is configured."""
    config = cloudinary.config()
    return bool(config.cloud_name and config.api_key and config.api_secret)


def upload_image_bytes(file_bytes: bytes, folder: str, public_id: str | None = None) -> dict:
    """
    Upload image bytes (PNG/JPG) to Cloudinary.
    
    Args:
        file_bytes: Image file content as bytes
        folder: Cloudinary folder path
        public_id: Optional custom public ID
    
    Returns:
        Dictionary with secure_url and public_id
    """
    if not is_cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured")
    
    result = cloudinary.uploader.upload(
        io.BytesIO(file_bytes),
        resource_type="image",
        folder=folder,
        public_id=public_id,
        overwrite=True,
        unique_filename=True,
    )
    
    return {
        "secure_url": result.get("secure_url"),
        "public_id": result.get("public_id"),
    }


def upload_video_bytes(file_bytes: bytes, folder: str, filename: str | None = None) -> dict:
    """
    Upload video (MP4) to Cloudinary and return metadata with thumbnail.
    
    Args:
        file_bytes: Video file content as bytes
        folder: Cloudinary folder path
        filename: Original filename (optional)
    
    Returns:
        Dictionary with public_id, secure_url, thumbnail_url, duration_sec, size_bytes
    """
    if not is_cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured")
    
    res = cloudinary.uploader.upload(
        io.BytesIO(file_bytes),
        resource_type="video",
        folder=folder,
        overwrite=True,
        unique_filename=True,
        type="upload",
    )
    
    public_id = res["public_id"]
    secure_url = res["secure_url"]
    duration_sec = int(res.get("duration", 0))
    size_bytes = int(res.get("bytes", 0))
    
    # Create thumbnail from 1s mark
    thumb_url, _ = cloudinary_url(
        public_id,
        resource_type="video",
        format="jpg",
        start_offset="1",
        transformation={"width": 480},
        secure=True,
    )
    
    return {
        "public_id": public_id,
        "secure_url": secure_url,
        "thumbnail_url": thumb_url,
        "duration_sec": duration_sec,
        "size_bytes": size_bytes,
    }


def delete_file_by_public_id(public_id: str, resource_type: str = "image") -> dict:
    """Delete a file from Cloudinary by its public ID."""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result
    except Exception as e:
        print(f"[delete_file_by_public_id] Failed to delete {public_id}: {e}")
        return {"result": "error", "error": str(e)}


def delete_with_thumbnail(public_id: str, resource_type: str) -> dict:
    """Delete a file from Cloudinary with CDN cache invalidation."""
    result = cloudinary.uploader.destroy(
        public_id,
        resource_type=resource_type,
        invalidate=True
    )
    return result
