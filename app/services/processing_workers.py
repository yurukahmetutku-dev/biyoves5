#!/usr/bin/env python3

"""Fotoğraf işleme için QThread tabanlı worker'lar"""

from __future__ import annotations

from typing import List, Sequence

from PySide6.QtCore import QThread, Signal

from app.services.photo_processor import PhotoProcessor, PhotoJob, PhotoResult
from app.services.credit_service import credit_service
from app.logger import logger


class SinglePhotoWorker(QThread):
    progress = Signal(int, int)
    finished = Signal(PhotoResult)
    error = Signal(str)
    credit_error = Signal(str)
    credit_updated = Signal(int)

    def __init__(self, processor: PhotoProcessor, job: PhotoJob, user_id: str):
        super().__init__()
        self.processor = processor
        self.job = job
        self.user_id = user_id

    def run(self) -> None:  # noqa: D401
        try:
            success, new_credits, message = credit_service.use_credit(self.user_id)
            if not success:
                self.credit_error.emit(message or "Kredi kullanılamadı")
                return
            self.credit_updated.emit(new_credits)

            total = 1
            self.progress.emit(0, total)
            result = self.processor.process_single(self.job)
            self.progress.emit(1, total)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Tekli işleme hatası: %s", exc)
            refund_success, refund_credits, refund_message = credit_service.refund_credit(
                self.user_id,
                reason="İşlem başarısız - iade",
            )
            if refund_success:
                self.credit_updated.emit(refund_credits)
            else:
                self.credit_error.emit(refund_message)
            self.error.emit(str(exc))


class BatchPhotoWorker(QThread):
    progress = Signal(int, int)
    completed = Signal(list, list)
    credit_updated = Signal(int)
    credit_error = Signal(str)

    def __init__(self, processor: PhotoProcessor, jobs: Sequence[PhotoJob], user_id: str):
        super().__init__()
        self.processor = processor
        self.jobs = list(jobs)
        self.user_id = user_id

    def run(self) -> None:
        results: List[PhotoResult] = []
        failures = []
        total = len(self.jobs)
        processed = 0

        try:
            for job in self.jobs:
                credit_success, new_credits, message = credit_service.use_credit(self.user_id)
                if not credit_success:
                    error = Exception(message or "Yetersiz kredi")
                    failures.append((job, error))
                    self.credit_error.emit(message or "Yetersiz kredi")
                    break
                self.credit_updated.emit(new_credits)

                try:
                    result = self.processor.process_single(job)
                    results.append(result)
                except Exception as exc:  # noqa: BLE001
                    logger.exception("Toplu işleme hatası: %s", exc)
                    refund_success, refund_credits, refund_message = credit_service.refund_credit(
                        self.user_id,
                        reason="İşlem başarısız - iade",
                    )
                    if refund_success:
                        self.credit_updated.emit(refund_credits)
                    else:
                        self.credit_error.emit(refund_message or "Kredi iadesi başarısız")
                    failures.append((job, exc))
                else:
                    processed += 1
                    self.progress.emit(processed, total)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Toplu işleme beklenmeyen hata: %s", exc)
            self.credit_error.emit(str(exc))
        finally:
            self.completed.emit(results, failures)
