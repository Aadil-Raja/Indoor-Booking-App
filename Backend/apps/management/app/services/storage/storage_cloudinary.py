"""
Shared Cloudinary Service
Reusable functions for uploading and deleting images and videos to Cloudinary.
"""

import io
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url
from fastapi import UploadFile
import os


def configure_cloudinary(cloud_name: str, api_key: str, api_secret: str):
    """Configure Cloudinary with credentials."""
    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
        secure=True,
    )


# Auto-configure on import
configure_cloudinary(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
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


async def upload_file(file: UploadFile, folder: str = "indoor", resource_type: str = "auto") -> dict:
    """
    Upload file from FastAPI UploadFile to Cloudinary.
    
    Args:
        file: UploadFile from FastAPI
        folder: Cloudinary folder path
        resource_type: "image", "video", or "auto"
    
    Returns:
        Dictionary with url, thumbnail_url, public_id, format, resource_type
    """
    if not is_cloudinary_configured():
        raise RuntimeError("Cloudinary is not configured")
    
    try:
        # Read file content
        contents = await file.read()
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            contents,
            folder=folder,
            resource_type=resource_type
        )
        
        # Generate thumbnail for videos
        thumbnail_url = None
        if result.get("resource_type") == "video":
            # Cloudinary automatically generates video thumbnails
            thumbnail_url = result["url"].replace("/upload/", "/upload/c_thumb,w_300/")
        
        return {
            "url": result["secure_url"],
            "thumbnail_url": thumbnail_url,
            "public_id": result["public_id"],
            "format": result.get("format"),
            "resource_type": result.get("resource_type")
        }
    except Exception as e:
        raise Exception(f"Failed to upload to Cloudinary: {str(e)}")


def delete_file_by_public_id(public_id: str, resource_type: str = "image") -> dict:
    """Delete a file from Cloudinary by its public ID."""
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        return result
    except Exception as e:
        print(f"[delete_file_by_public_id] Failed to delete {public_id}: {e}")
        return {"result": "error", "error": str(e)}


async def delete_file(url: str) -> dict:
    """
    Delete file from Cloudinary using URL.
    
    Args:
        url: Cloudinary URL
    
    Returns:
        Result dictionary from Cloudinary
    """
    try:
        # Extract public_id from URL
        # URL format: https://res.cloudinary.com/{cloud_name}/{resource_type}/upload/v{version}/{public_id}.{format}
        parts = url.split("/upload/")
        if len(parts) < 2:
            raise ValueError("Invalid Cloudinary URL")
        
        # Get public_id (remove version and extension)
        public_id_with_ext = parts[1].split("/", 1)[-1]
        public_id = public_id_with_ext.rsplit(".", 1)[0]
        
        # Determine resource type from URL
        resource_type = "image"
        if "/video/" in url:
            resource_type = "video"
        elif "/raw/" in url:
            resource_type = "raw"
        
        # Delete from Cloudinary
        result = cloudinary.uploader.destroy(public_id, resource_type=resource_type)
        
        return result
    except Exception as e:
        raise Exception(f"Failed to delete from Cloudinary: {str(e)}")


def delete_with_thumbnail(public_id: str, resource_type: str) -> dict:
    """Delete a file from Cloudinary with CDN cache invalidation."""
    result = cloudinary.uploader.destroy(
        public_id,
        resource_type=resource_type,
        invalidate=True
    )
    return result
