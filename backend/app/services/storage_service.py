import os
import re
import uuid
from pathlib import Path
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings
from app.validators.image_validator import validate_image_content, validate_image_file


class StorageService:
    @staticmethod
    def get_upload_path() -> Path:
        upload_path = Path(settings.upload_dir).resolve()
        upload_path.mkdir(parents=True, exist_ok=True)
        return upload_path

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        base = os.path.basename(filename)
        base = re.sub(r"\.{2,}", "_", base)
        sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
        return sanitized

    @classmethod
    async def save_upload(
        cls,
        file: UploadFile,
        max_size_bytes: int | None = None,
    ) -> dict:
        """
        Validates, saves the uploaded file locally, and returns metadata.
        Prevents directory traversal attacks.
        """
        max_size = max_size_bytes or settings.max_upload_size_bytes
        validate_image_file(file, max_size)

        # Read content
        content = await file.read()
        if len(content) > max_size:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum allowed size of {max_size / (1024 * 1024):.1f} MB.",
            )
        if len(content) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty.",
            )
        validate_image_content(file, content)

        # Generate unique and safe filename
        original_sanitized = cls.sanitize_filename(file.filename or "upload.jpg")
        _, ext = os.path.splitext(original_sanitized.lower())
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        upload_dir = cls.get_upload_path()
        target_path = (upload_dir / unique_filename).resolve()

        # Security check: Ensure target path remains within upload_dir (prevents traversal)
        if not str(target_path).startswith(str(upload_dir)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file path detected.",
            )

        try:
            with open(target_path, "wb") as f:
                f.write(content)
        except OSError as exc:
            try:
                target_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Uploaded image could not be stored.",
            ) from exc

        file_url = f"/uploads/{unique_filename}"

        return {
            "file_url": file_url,
            "file_name": unique_filename,
            "original_filename": original_sanitized,
            "file_path": str(target_path),
            "file_type": file.content_type or f"image/{ext.lstrip('.')}",
            "file_size": len(content),
            "content_bytes": content,
        }

    @classmethod
    def delete_file(cls, filename: str) -> bool:
        upload_dir = cls.get_upload_path()
        target_path = (upload_dir / filename).resolve()
        if str(target_path).startswith(str(upload_dir)) and target_path.exists():
            try:
                target_path.unlink()
                return True
            except OSError:
                return False
        return False
