#!/usr/bin/env python3

from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFileDialog, QScrollArea, QFrame, QSizePolicy, QComboBox, QMessageBox
)
from PySide6.QtGui import QFont

from app.config import modern_theme
from app.ui.widgets import ModernButton, ModernCard, PreviewLabel, show_styled_message
from app.services.photo_processor import PhotoProcessor, PhotoJob
from app.services.processing_workers import BatchPhotoWorker
from app.utils.file_validation import validate_image_file
from app.ui.components import WelcomeInfo


class BatchProcessingPage(QWidget):
    """Çoklu işlem sayfası (widget)"""

    return_to_main = Signal()
    credits_updated = Signal(int)

    def __init__(
        self,
        user,
        processor: PhotoProcessor,
        credit_balance_getter: Callable[[], int],
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.user = user
        self.processor = processor
        self.photo_entries: List[Dict[str, Any]] = []
        self.output_folder: Optional[Path] = None
        self.batch_worker: Optional[BatchPhotoWorker] = None
        self.get_credit_balance = credit_balance_getter
        self._current_credits = 0
        self._current_credits = self._safe_get_balance()

        self.setObjectName("batchProcessingPage")
        self.setStyleSheet(f"background-color: {modern_theme.BACKGROUND};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._create_header(main_layout)
        self._create_content(main_layout)

    def _create_header(self, parent_layout):
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: transparent;")
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(
            modern_theme.SPACING_XL, modern_theme.SPACING_XXL,
            modern_theme.SPACING_XL, modern_theme.SPACING_XL
        )
        header_layout.setSpacing(modern_theme.SPACING_MD)

        username = self.user.email.split("@")[0].capitalize() if self.user.email else "Kullanıcı"
        welcome_text = f"Hoş geldin, {username}. {self._current_credits} Adet Hakkınız Kaldı."
        self.welcome_info = WelcomeInfo("BiyoVes", welcome_text, self)
        header_layout.addWidget(self.welcome_info)

        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(modern_theme.SPACING_SM)
        button_layout.addStretch()

        self.action_buttons = []
        buttons = [
            ("Fotoğraf Ekle", self._add_photos, "primary"),
            ("Çıkış Klasörü Seç", self._select_output_folder, "secondary"),
            ("İşlemi Başlat", self._start_batch_processing, "success"),
            ("Ana Sayfaya Dön", self._return_to_main_page, "danger"),
        ]

        for text, handler, variant in buttons:
            btn = ModernButton(text, variant=variant, size="md")
            btn.clicked.connect(handler)
            button_layout.addWidget(btn)
            self.action_buttons.append(btn)

        button_layout.addStretch()
        header_layout.addWidget(button_container)

        self.output_label = QLabel("Çıkış klasörü seçilmedi.")
        self.output_label.setStyleSheet(f"color: {modern_theme.TEXT_TERTIARY};")
        self.output_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.output_label)

        parent_layout.addWidget(header_frame)

    def _create_content(self, parent_layout):
        panel_frame = QFrame()
        panel_frame.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_LG}px;
                background-color: transparent;
            }}
        """)
        panel_layout = QVBoxLayout(panel_frame)
        panel_layout.setContentsMargins(
            modern_theme.SPACING_XL,
            modern_theme.SPACING_LG,
            modern_theme.SPACING_XL,
            modern_theme.SPACING_LG
        )
        panel_layout.setSpacing(modern_theme.SPACING_MD)

        list_card = ModernCard(
            title="Toplu İşlem Listesi",
            subtitle="Eklediğiniz fotoğraflar ve ayarları",
            show_frame=False
        )
        list_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        card_layout = list_card.get_content_layout()
        card_layout.setSpacing(modern_theme.SPACING_MD)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)

        scroll_content = QWidget()
        self.photo_list_layout = QVBoxLayout(scroll_content)
        self.photo_list_layout.setContentsMargins(0, 0, 0, 0)
        self.photo_list_layout.setSpacing(modern_theme.SPACING_MD)
        self.photo_list_layout.setAlignment(Qt.AlignTop)

        self.empty_label = QLabel("Henüz fotoğraf eklenmedi.")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {modern_theme.TEXT_TERTIARY};")
        self.photo_list_layout.addWidget(self.empty_label)

        scroll_area.setWidget(scroll_content)
        card_layout.addWidget(scroll_area)
        panel_layout.addWidget(list_card)

        self.progress_label = QLabel()
        self.progress_label.setAlignment(Qt.AlignCenter)
        self.progress_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        self.progress_label.setVisible(False)
        panel_layout.addWidget(self.progress_label)

        parent_layout.addWidget(panel_frame, 1)

    def _add_photos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Fotoğrafları Seç",
            "",
            "Resim Dosyaları (*.jpg *.jpeg *.png *.bmp);;Tüm Dosyalar (*)"
        )
        if not files:
            return
        for file_path in files:
            if not file_path:
                continue
            path = Path(file_path)
            is_valid, message = validate_image_file(path)
            if not is_valid:
                show_styled_message(self, "Dosya", f"{path.name}: {message}", QMessageBox.Warning)
                continue
            self._create_photo_row(file_path)
        self._update_placeholder()

    def _select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Çıkış klasörü seç")
        if folder:
            self.output_folder = Path(folder)
            display_name = self.output_folder.name or str(self.output_folder)
            self.output_label.setText(f"Çıkış klasörü: {display_name}")

    def _start_batch_processing(self):
        if not self.photo_entries:
            show_styled_message(self, "Toplu İşlem", "Lütfen önce fotoğraf ekleyin.", QMessageBox.Warning)
            return

        if not self.output_folder:
            show_styled_message(self, "Çıkış Klasörü", "Lütfen bir çıkış klasörü seçin.", QMessageBox.Warning)
            return

        if self.batch_worker and self.batch_worker.isRunning():
            show_styled_message(self, "İşlem", "Devam eden bir işlem var.", QMessageBox.Warning)
            return

        available_credits = self._safe_get_balance()
        self.set_credit_balance(available_credits)
        if available_credits <= 0:
            show_styled_message(
                self,
                "Yetersiz Kredi",
                "Kalan hakkınız yok. Lütfen hak satın alın veya kod girin.",
                QMessageBox.Warning,
            )
            return

        jobs: List[PhotoJob] = []
        for entry in self.photo_entries:
            photo_type = entry["type_combo"].currentData()
            layout_type = entry["layout_combo"].currentData()
            input_path = Path(entry["path"])
            output_path = self._build_output_path(input_path, photo_type, layout_type)
            jobs.append(PhotoJob(input_path=input_path, photo_type=photo_type, layout_type=layout_type, output_path=output_path))

        self._set_processing_state(True)
        self.progress_label.setText(f"0/{len(jobs)} photos processed")
        self.progress_label.setVisible(True)

        self.batch_worker = BatchPhotoWorker(self.processor, jobs, self.user.uid)
        self.batch_worker.progress.connect(self._update_batch_progress)
        self.batch_worker.completed.connect(self._on_batch_completed)
        self.batch_worker.credit_updated.connect(self.credits_updated.emit)
        self.batch_worker.credit_error.connect(self._on_batch_credit_error)
        self.batch_worker.start()

    def _return_to_main_page(self):
        if self.batch_worker and self.batch_worker.isRunning():
            show_styled_message(self, "İşlem", "Lütfen işlem tamamlanana kadar bekleyin.", QMessageBox.Warning)
            return
        self.return_to_main.emit()

    def _create_photo_row(self, file_path: str):
        row_frame = QFrame()
        row_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {modern_theme.BACKGROUND};
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_MD}px;
            }}
        """)
        row_layout = QHBoxLayout(row_frame)
        row_layout.setContentsMargins(
            modern_theme.SPACING_MD,
            modern_theme.SPACING_MD,
            modern_theme.SPACING_MD,
            modern_theme.SPACING_MD
        )
        row_layout.setSpacing(modern_theme.SPACING_MD)

        thumb = PreviewLabel("Önizleme")
        thumb.setFixedSize(96, 96)
        thumb.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        if not thumb.set_image_from_path(file_path):
            show_styled_message(self, "Önizleme", f"{Path(file_path).name} yüklenemedi.", QMessageBox.Warning)
            row_frame.deleteLater()
            return
        row_layout.addWidget(thumb)

        info_widget = QWidget()
        info_layout = QVBoxLayout(info_widget)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(modern_theme.SPACING_XS)

        name_label = QLabel(Path(file_path).name)
        name_label.setStyleSheet(f"color: {modern_theme.TEXT_PRIMARY}; font-weight: 600;")
        info_layout.addWidget(name_label)

        combo_style = f"""
            QComboBox {{
                background-color: {modern_theme.BACKGROUND};
                color: {modern_theme.TEXT_PRIMARY};
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_MD}px;
                padding: 4px 32px 4px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {modern_theme.BACKGROUND_SECONDARY};
                color: {modern_theme.TEXT_PRIMARY};
                selection-background-color: {modern_theme.PRIMARY};
                selection-color: #ffffff;
                border: 1px solid {modern_theme.BORDER_LIGHT};
            }}
        """

        type_layout = QHBoxLayout()
        type_label = QLabel("Fotoğraf Tipi:")
        type_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        type_combo = QComboBox()
        type_combo.setStyleSheet(combo_style)
        type_combo.addItem("Biyometrik 50x60 mm", "biyometrik")
        type_combo.addItem("Vesikalık 45x60 mm", "vesikalik")
        type_combo.addItem("ABD Vizesi 50x50 mm", "abd_vizesi")
        type_combo.addItem("Schengen 35x45 mm", "schengen")
        type_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        type_layout.addWidget(type_label)
        type_layout.addWidget(type_combo)
        info_layout.addLayout(type_layout)

        layout_layout = QHBoxLayout()
        layout_label = QLabel("Sayfa Düzeni:")
        layout_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        layout_combo = QComboBox()
        layout_combo.setStyleSheet(combo_style)
        layout_combo.addItem("2'li Düzen", "2li")
        layout_combo.addItem("4'lü Düzen", "4lu")
        layout_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout_layout.addWidget(layout_label)
        layout_layout.addWidget(layout_combo)
        info_layout.addLayout(layout_layout)

        row_layout.addWidget(info_widget, 1)

        remove_btn = ModernButton("Fotoğrafı Kaldır", variant="danger", size="sm")
        remove_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        remove_btn.setMinimumWidth(180)
        row_layout.addWidget(remove_btn)

        entry = {
            "path": file_path,
            "frame": row_frame,
            "type_combo": type_combo,
            "layout_combo": layout_combo,
        }
        remove_btn.clicked.connect(lambda _: self._remove_photo(entry))

        self.photo_entries.append(entry)
        self.photo_list_layout.addWidget(row_frame)

    def _remove_photo(self, entry):
        if entry in self.photo_entries:
            self.photo_entries.remove(entry)
            entry["frame"].deleteLater()
            self._update_placeholder()

    def _update_placeholder(self):
        has_items = bool(self.photo_entries)
        self.empty_label.setVisible(not has_items)

    def _build_output_path(self, input_path: Path, photo_type: str, layout_type: str) -> Optional[Path]:
        if not self.output_folder:
            return None
        self.output_folder.mkdir(parents=True, exist_ok=True)
        return self.output_folder / f"{input_path.stem}_{photo_type}_{layout_type}.jpg"

    def _set_processing_state(self, processing: bool):
        for btn in self.action_buttons:
            btn.setEnabled(not processing)

    def _on_batch_completed(self, results, failures):
        self._cleanup_batch_worker()
        if failures:
            summary_text = self._build_summary_text(results, failures)
            show_styled_message(self, "Toplu İşlem", summary_text)
        else:
            show_styled_message(self, "", "İşlem başarıyla tamamlandı.", QMessageBox.NoIcon)
        self._set_processing_state(False)

    def _cleanup_batch_worker(self):
        if self.batch_worker:
            self.batch_worker.deleteLater()
            self.batch_worker = None
        self.progress_label.setVisible(False)
        self.progress_label.clear()

    def _update_batch_progress(self, processed: int, total: int):
        self.progress_label.setText(f"{processed}/{total} photos processed")

    def _build_summary_text(self, results, failures) -> str:
        summary_lines = [f"{len(results)} fotoğraf başarıyla işlendi."]
        if failures:
            summary_lines.append(f"{len(failures)} fotoğraf başarısız oldu:")
            for failed_job, error in failures[:5]:
                summary_lines.append(f"- {failed_job.input_path.name}: {error}")
            if len(failures) > 5:
                summary_lines.append("...")
        return "\n".join(summary_lines)

    def _on_batch_credit_error(self, message: str):
        self._cleanup_batch_worker()
        detail = message or "Yetersiz kredi nedeniyle kalan işlemler durduruldu."
        show_styled_message(self, "Kredi", detail, QMessageBox.Warning)
        self._set_processing_state(False)

    def set_credit_balance(self, value: int) -> None:
        self._current_credits = max(0, int(value or 0))
        username = self.user.email.split("@")[0].capitalize() if self.user.email else "Kullanıcı"
        self._update_welcome_text(username)

    def _update_welcome_text(self, username: str) -> None:
        welcome_text = f"Hoş geldin, {username}. {self._current_credits} Adet Hakkınız Kaldı."
        if hasattr(self, "welcome_info"):
            self.welcome_info.set_welcome_text(welcome_text)

    def _safe_get_balance(self) -> int:
        if callable(self.get_credit_balance):
            try:
                return max(0, int(self.get_credit_balance()))
            except Exception:
                return 0
        return self._current_credits
