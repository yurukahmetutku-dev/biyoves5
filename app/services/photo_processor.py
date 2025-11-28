#!/usr/bin/env python3

"""Fotoğraf işleme servis katmanı"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from biyoves import BiyoVes


PHOTO_TYPE_ALIASES = {
    "biometric": "biyometrik",
    "biyometrik": "biyometrik",
    "passport": "vesikalik",
    "vesikalik": "vesikalik",
    "us_visa": "abd_vizesi",
    "abd_vizesi": "abd_vizesi",
    "schengen_visa": "schengen",
    "schengen": "schengen",
}

LAYOUT_ALIASES = {
    "2li": "2li",
    "2lu": "2li",
    "2'li": "2li",
    "4lu": "4lu",
    "4lü": "4lu",
    "4'lü": "4lu",
}


class PhotoProcessingError(Exception):
    """Fotoğraf işleme hatası"""


@dataclass
class PhotoJob:
    input_path: Path
    photo_type: str
    layout_type: str
    output_path: Optional[Path] = None


@dataclass
class PhotoResult:
    job: PhotoJob
    output_path: Path


class PhotoProcessor:
    """BiyoVes tabanlı işleme servis katmanı"""

    def __init__(self, base_output_dir: Optional[Path] = None):
        default_dir = Path.home() / "BiyoVesOutputs"
        self.base_output_dir = Path(base_output_dir) if base_output_dir else default_dir
        self.base_output_dir.mkdir(parents=True, exist_ok=True)

    def process_single(self, job: PhotoJob) -> PhotoResult:
        normalized_job = self._normalize_job(job)
        output_path = self._resolve_output_path(normalized_job)

        try:
            processor = BiyoVes(str(normalized_job.input_path), verbose=False)
            processor.create_image(
                normalized_job.photo_type,
                normalized_job.layout_type,
                str(output_path)
            )
        except Exception as exc:
            raise PhotoProcessingError(str(exc)) from exc

        return PhotoResult(job=normalized_job, output_path=output_path)

    def process_batch(self, jobs: Sequence[PhotoJob]) -> Tuple[List[PhotoResult], List[Tuple[PhotoJob, Exception]]]:
        results: List[PhotoResult] = []
        failures: List[Tuple[PhotoJob, Exception]] = []

        for job in jobs:
            try:
                result = self.process_single(job)
                results.append(result)
            except Exception as exc:  # noqa: BLE001
                failures.append((job, exc))

        return results, failures

    def _normalize_job(self, job: PhotoJob) -> PhotoJob:
        input_path = Path(job.input_path)
        if not input_path.exists():
            raise PhotoProcessingError(f"Dosya bulunamadı: {input_path}")

        photo_type = PHOTO_TYPE_ALIASES.get(job.photo_type.lower())
        if not photo_type:
            raise PhotoProcessingError(f"Geçersiz fotoğraf tipi: {job.photo_type}")

        layout_type = LAYOUT_ALIASES.get(job.layout_type.lower())
        if not layout_type:
            raise PhotoProcessingError(f"Geçersiz düzen tipi: {job.layout_type}")

        output_path = Path(job.output_path) if job.output_path else None
        return PhotoJob(
            input_path=input_path,
            photo_type=photo_type,
            layout_type=layout_type,
            output_path=output_path
        )

    def _resolve_output_path(self, job: PhotoJob) -> Path:
        if job.output_path:
            target = job.output_path
        else:
            target = self.base_output_dir / f"{job.input_path.stem}_{job.photo_type}_{job.layout_type}.jpg"

        target.parent.mkdir(parents=True, exist_ok=True)
        return self._make_unique(target)

    @staticmethod
    def _make_unique(path: Path) -> Path:
        if not path.exists():
            return path

        counter = 1
        stem = path.stem
        suffix = path.suffix or ".jpg"
        while True:
            candidate = path.with_name(f"{stem}_{counter}{suffix}")
            if not candidate.exists():
                return candidate
            counter += 1
