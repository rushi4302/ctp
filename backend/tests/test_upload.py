import io
import pytest
from fastapi import HTTPException, UploadFile, status

from app.services.storage_service import StorageService
from app.validators.image_validator import validate_image_file


@pytest.mark.asyncio
async def test_save_valid_image(sample_image_bytes):
    upload = UploadFile(
        filename="test_photo.jpg",
        file=io.BytesIO(sample_image_bytes),
        headers={"content-type": "image/jpeg"},
    )
    result = await StorageService.save_upload(upload)
    assert "file_url" in result
    assert "file_name" in result
    assert result["file_size"] == len(sample_image_bytes)
    assert result["file_type"] == "image/jpeg"

    # Cleanup
    StorageService.delete_file(result["file_name"])


@pytest.mark.asyncio
async def test_reject_oversized_image():
    # 2KB limit for testing
    large_data = b"0" * 3000
    upload = UploadFile(
        filename="large.jpg",
        file=io.BytesIO(large_data),
        headers={"content-type": "image/jpeg"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await StorageService.save_upload(upload, max_size_bytes=2048)
    assert exc_info.value.status_code == status.HTTP_413_REQUEST_ENTITY_TOO_LARGE


@pytest.mark.asyncio
async def test_reject_invalid_mime():
    fake_script = b"#!/bin/bash\necho hello"
    upload = UploadFile(
        filename="script.sh",
        file=io.BytesIO(fake_script),
        headers={"content-type": "application/x-sh"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await StorageService.save_upload(upload)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_rejects_non_image_bytes_with_image_filename():
    upload = UploadFile(
        filename="fake.jpg",
        file=io.BytesIO(b"this is not a jpeg image"),
        headers={"content-type": "image/jpeg"},
    )
    with pytest.raises(HTTPException) as exc_info:
        await StorageService.save_upload(upload)
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST


def test_sanitize_filename_prevents_traversal():
    dangerous = "../../etc/passwd"
    sanitized = StorageService.sanitize_filename(dangerous)
    assert ".." not in sanitized
    assert "/" not in sanitized
