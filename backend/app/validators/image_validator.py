import os
from fastapi import HTTPException, UploadFile, status

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/heic": [".heic"],
}

ALLOWED_EXTENSIONS = {ext for exts in ALLOWED_MIME_TYPES.values() for ext in exts}


def validate_image_file(file: UploadFile, max_size_bytes: int = 10 * 1024 * 1024) -> None:
    """Validates the uploaded file MIME type, extension, and content size."""
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty.",
        )

    _, ext = os.path.splitext(file.filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content_type = file.content_type
    if content_type and content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{content_type}'. Allowed: {', '.join(ALLOWED_MIME_TYPES.keys())}",
        )
