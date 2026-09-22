"""
PRAVAH — Community Photo Security & Storage Service
Handles secure image verification, MIME validation, magic-byte inspection,
UUID filename randomization, and static upload storage.
"""

from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path
from typing import Optional, Set
from fastapi import HTTPException, UploadFile

logger = logging.getLogger("pravah.community.photo_service")

# Resolve repository upload directory
REPO_ROOT = Path(__file__).resolve().parents[3]
COMMUNITY_UPLOADS_DIR = REPO_ROOT / "data" / "uploads" / "community_photos"
COMMUNITY_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Configurable limits
MAX_REPORT_IMAGE_SIZE: int = int(os.environ.get("MAX_REPORT_IMAGE_SIZE", 10 * 1024 * 1024))  # 10 MB default
ALLOWED_IMAGE_EXTENSIONS: Set[str] = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIMES: Set[str] = {"image/jpeg", "image/png", "image/webp"}


def verify_image_magic_bytes(header: bytes, ext: str) -> bool:
    """
    Inspect raw binary file header to verify authentic image formats
    and block disguised executables or scripts.
    """
    if not header:
        return False

    # JPEG header check: FF D8 FF
    if ext in (".jpg", ".jpeg"):
        return header.startswith(b"\xff\xd8\xff")

    # PNG header check: 89 50 4E 47 0D 0A 1A 0A
    if ext == ".png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")

    # WebP check: RIFF .... WEBP
    if ext == ".webp":
        return header.startswith(b"RIFF") and len(header) >= 12 and header[8:12] == b"WEBP"

    return False


async def process_and_save_photo(file: Optional[UploadFile]) -> Optional[str]:
    """
    Validates and securely stores an uploaded community incident photo.
    Returns the relative public URL path (e.g. '/uploads/community_photos/abcd123.jpg')
    or None if no file was uploaded.
    """
    if file is None or not file.filename:
        return None

    filename = Path(file.filename).name
    ext = Path(filename).suffix.lower()

    # 1. Extension Whitelist Check
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Only JPG, JPEG, PNG, and WebP are allowed."
        )

    # 2. Content-Type Check
    content_type = (file.content_type or "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIMES:
        # Fallback map for common user-agent variations
        ext_to_mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        if ext not in ext_to_mime:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid MIME type '{content_type}'. Image must be JPEG, PNG, or WebP."
            )

    # 3. Read bytes & Size Guard
    file_bytes = await file.read()
    if len(file_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded image file is empty (0 bytes).")

    if len(file_bytes) > MAX_REPORT_IMAGE_SIZE:
        max_mb = MAX_REPORT_IMAGE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded photo exceeds the maximum size limit of {max_mb:.1f} MB."
        )

    # 4. Binary Magic Byte Verification
    if not verify_image_magic_bytes(file_bytes[:32], ext):
        raise HTTPException(
            status_code=400,
            detail="File content does not match genuine image header signatures. Executable payloads are forbidden."
        )

    # 5. Generate Safe, Non-predictable UUID Filename
    unique_filename = f"{uuid.uuid4().hex}{ext}"
    dest_path = COMMUNITY_UPLOADS_DIR / unique_filename

    # 6. Save image to disk
    dest_path.write_bytes(file_bytes)

    # 7. Construct Public Relative URL
    public_url = f"/uploads/community_photos/{unique_filename}"
    logger.info("📸 Saved community incident photo: %s (%d bytes)", unique_filename, len(file_bytes))

    return public_url
