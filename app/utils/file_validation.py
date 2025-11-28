#!/usr/bin/env python3

"""Common file validation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Tuple

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def validate_image_file(path: Path) -> Tuple[bool, str]:
    """Validate extension and size for image processing."""
    if not path.exists():
        return False, "Dosya bulunamadı."
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False, f"Desteklenmeyen format: {path.suffix}. İzin verilen: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    try:
        file_size = path.stat().st_size
    except OSError:
        return False, "Dosya okunamadı."
    if file_size > MAX_FILE_SIZE:
        return False, "Dosya boyutu 10 MB limitini aşıyor."
    return True, ""
