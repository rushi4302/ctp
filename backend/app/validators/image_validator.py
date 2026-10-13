import os
from fastapi import HTTPException, UploadFile, status

ALLOWED_MIME_TYPES = {
    "image/jpeg": [".jpg", ".jpeg"],
    "image/png": [".png"],
    "image/webp": [".webp"],
    "image/heic": [".heic"],
    "image/heif": [".heif"],
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


def validate_image_content(file: UploadFile, content: bytes) -> None:
    """Validate the actual image signature, not only client supplied metadata."""
    _, ext = os.path.splitext((file.filename or "").lower())
    valid_content = False
    if ext in {".jpg", ".jpeg"}:
        valid_content = content.startswith(b"\xff\xd8\xff")
    elif ext == ".png":
        valid_content = content.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext == ".webp":
        valid_content = len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    elif ext in {".heic", ".heif"}:
        valid_content = len(content) >= 12 and content[4:8] == b"ftyp" and content[8:12] in {
            b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1",
        }
    if not valid_content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file content is not a supported image.",
        )

    expected_mime = {
        ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
        ".webp": "image/webp", ".heic": "image/heic", ".heif": "image/heif",
    }[ext]
    if file.content_type and file.content_type != expected_mime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image content type does not match its file extension.",
        )
