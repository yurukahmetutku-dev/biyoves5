#!/usr/bin/env python3

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QScrollArea, QButtonGroup,
    QFileDialog, QMessageBox, QSizePolicy, QGridLayout, QDialog, QLineEdit, QStackedWidget
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QCloseEvent

import webbrowser
from pathlib import Path
from typing import Optional

from app.config import firebase_manager, modern_theme
from app.ui.widgets import (
    ModernButton,
    ModernCard,
    ChoiceButton,
    PreviewLabel,
    show_styled_message
)
from app.ui.batch_window import BatchProcessingPage
from app.services.photo_processor import PhotoProcessor, PhotoJob
from app.services.processing_workers import SinglePhotoWorker
from app.utils.file_validation import validate_image_file
from app.logger import logger
from app.ui.components import WelcomeInfo


class CodeInputDialog(QDialog):
    """Kod girişi için özel dialog"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kod Gir")
        self.setModal(True)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        label = QLabel("Lütfen kodunuzu girin:")
        label.setStyleSheet(f"color: {modern_theme.TEXT_PRIMARY}; font-size: {modern_theme.FONT_SIZE_BODY}px;")
        layout.addWidget(label)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Kod")
        self.input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {modern_theme.BACKGROUND_SECONDARY};
                color: {modern_theme.TEXT_PRIMARY};
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_MD}px;
                padding: 8px 12px;
                font-size: {modern_theme.FONT_SIZE_BODY}px;
            }}
            QLineEdit:focus {{
                border: 1px solid {modern_theme.PRIMARY};
            }}
        """)
        layout.addWidget(self.input_field)

        button_row = QHBoxLayout()
        button_row.setSpacing(modern_theme.SPACING_SM)
        button_row.addStretch()

        self.cancel_btn = ModernButton("İptal", variant="secondary", size="sm")
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self.reject)
        button_row.addWidget(self.cancel_btn)

        self.ok_btn = ModernButton("Onayla", variant="primary", size="sm")
        self.ok_btn.setMinimumWidth(120)
        button_row.addWidget(self.ok_btn)

        button_row.addStretch()
        layout.addLayout(button_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        self.status_label.setVisible(False)
        layout.addWidget(self.status_label)

        self.setStyleSheet(f"background-color: {modern_theme.BACKGROUND};")

    def get_code(self) -> str:
        return self.input_field.text().strip()

    def set_status(self, message: str, *, is_error: bool = False):
        if not message:
            self.status_label.setVisible(False)
            return
        color = modern_theme.DANGER if is_error else modern_theme.TEXT_SECONDARY
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(message)
        self.status_label.setVisible(True)

    def set_busy(self, busy: bool):
        self.input_field.setEnabled(not busy)
        self.ok_btn.setEnabled(not busy)
        self.cancel_btn.setEnabled(not busy)


class CreditCodeThread(QThread):
    success = Signal(int)
    error = Signal(str)

    def __init__(self, code: str, user_id: str):
        super().__init__()
        self.code = code.strip().upper()
        self.user_id = user_id

    def run(self):
        try:
            success, message, credits_added = firebase_manager.verify_credit_code(self.code, self.user_id)
            if success:
                self.success.emit(credits_added)
            else:
                self.error.emit(message or "Kod kullanılmadı")
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))


class MainWindow(QMainWindow):
    """Ana ekran - biyoves4-main ile aynı yapıda"""
    
    close_signal = Signal()
    logout_signal = Signal()
    
    def __init__(self, user):
        super().__init__()
        self.user = user
        self.user_credits = 0
        self.input_path: Optional[str] = None
        self.photo_type = "biyometrik"
        self.layout_type = "2li"
        self.photo_processor = PhotoProcessor()
        self.output_dir: Optional[Path] = None
        self.single_worker: Optional[SinglePhotoWorker] = None
        self.single_controls_enabled = True
        self._credit_code_thread: Optional[CreditCodeThread] = None
        
        # Kullanıcı kredilerini al
        self._load_user_credits()
        
        self._setup_ui()
    
    def _load_user_credits(self):
        """Kullanıcı kredilerini yükle"""
        try:
            self.user_credits = firebase_manager.get_user_credits(self.user.uid)
        except Exception as e:
            logger.exception("Kredi yükleme hatası: %s", e)
            self.user_credits = 0
    
    def _setup_ui(self):
        self.setWindowTitle("BiyoVes")
        self.setMinimumSize(modern_theme.WINDOW_MIN_WIDTH, modern_theme.WINDOW_MIN_HEIGHT)
        
        # Ekran boyutuna göre başlangıç boyutu
        screen = self.screen().availableGeometry()
        ideal_w = max(modern_theme.WINDOW_MIN_WIDTH, int(screen.width() * 0.8))
        ideal_h = max(modern_theme.WINDOW_MIN_HEIGHT, int(screen.height() * 0.85))
        base_w = min(ideal_w, screen.width() - 40)
        base_h = min(ideal_h, screen.height() - 60)
        self.resize(base_w, base_h)
        
        self.setStyleSheet(f"background-color: {modern_theme.BACKGROUND};")
        self._center_window()
        
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        central_widget.setStyleSheet(f"background-color: {modern_theme.BACKGROUND};")
        self.setCentralWidget(central_widget)

        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.setObjectName("rootLayout")

        self.page_stack = QStackedWidget()
        self.page_stack.setObjectName("mainStack")
        root_layout.addWidget(self.page_stack)

        self.main_page = self._build_main_page()
        self.page_stack.addWidget(self.main_page)

        self.batch_page = BatchProcessingPage(
            self.user,
            self.photo_processor,
            credit_balance_getter=lambda: self.user_credits,
            parent=self,
        )
        self.batch_page.return_to_main.connect(self._return_to_main_page)
        self.batch_page.credits_updated.connect(self._on_batch_credits_updated)
        self.batch_page.set_credit_balance(self.user_credits)
        self.page_stack.addWidget(self.batch_page)

        self.page_stack.setCurrentWidget(self.main_page)
    
    def _center_window(self):
        """Pencereyi ekranın ortasına yerleştirir"""
        screen = self.screen().availableGeometry()
        window = self.frameGeometry()
        center_point = screen.center()
        window.moveCenter(center_point)
        self.move(window.topLeft())
    
    def _build_main_page(self):
        page = QWidget()
        page.setObjectName("mainPage")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        self._create_header(page_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setStyleSheet("border: none; background-color: transparent;")
        scroll_area.setObjectName("contentScrollArea")

        content_widget = QWidget()
        content_widget.setObjectName("contentContainer")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(
            modern_theme.SPACING_XL, 0,
            modern_theme.SPACING_XL, modern_theme.SPACING_XL
        )
        content_layout.setSpacing(0)
        content_layout.setObjectName("contentLayout")

        self._create_content(content_layout)

        scroll_area.setWidget(content_widget)
        page_layout.addWidget(scroll_area, 1)
        return page

    def _create_header(self, parent_layout):
        """Header bölümünü oluşturur"""
        header_frame = QFrame()
        header_frame.setObjectName("headerFrame")
        header_frame.setStyleSheet("background-color: transparent;")
        header_frame.setMinimumHeight(160)
        header_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        header_frame.setSizePolicy(header_policy)

        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(
            modern_theme.SPACING_XL, modern_theme.SPACING_XXL,
            modern_theme.SPACING_XL, modern_theme.SPACING_XL
        )
        header_layout.setSpacing(modern_theme.SPACING_MD)
        header_layout.setObjectName("headerLayout")

        username = self.user.email.split("@")[0].capitalize() if self.user.email else "Kullanıcı"
        welcome_text = f"Hoş geldin, {username}. {self.user_credits} Adet Hakkınız Kaldı."
        self.welcome_info = WelcomeInfo("BiyoVes", welcome_text, self)
        self.welcome_label = self.welcome_info.welcome_label
        header_layout.addWidget(self.welcome_info)
        
        # Butonlar
        button_container = QWidget()
        button_container.setObjectName("headerButtonContainer")
        button_layout = QHBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(modern_theme.SPACING_SM)
        button_layout.addStretch()
        button_layout.setObjectName("headerButtonLayout")
        
        buttons = [
            ("Hak Satın Al", self._open_shop, "success"),
            ("Kod Gir", self._show_code_dialog, "info"),
            ("Çoklu İşlem", self._open_multi_process, "secondary"),
            ("Çıkış", self._logout, "danger")
        ]
        
        for text, command, variant in buttons:
            btn = ModernButton(text, variant=variant, size="md")
            btn.setObjectName(f"headerButton_{variant}")
            btn.clicked.connect(command)
            button_layout.addWidget(btn)
        
        button_layout.addStretch()
        header_layout.addWidget(button_container)
        
        parent_layout.addWidget(header_frame)
        self._update_credit_display()
    
    def _create_content(self, parent_layout):
        """İçerik bölümünü oluşturur"""
        content_widget = QWidget()
        content_widget.setObjectName("panelContainer")
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(modern_theme.SPACING_LG)
        content_layout.setObjectName("panelLayout")

        # Sol panel - Fotoğraf Seçimi
        self._create_left_panel(content_layout)

        # Sağ panel - İşlem Ayarları
        self._create_right_panel(content_layout)

        parent_layout.addWidget(content_widget)
    
    def _create_left_panel(self, parent_layout):
        """Sol paneli oluşturur"""
        container = QFrame()
        container.setObjectName("photoSelectionGroup")
        container.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_LG}px;
                background-color: transparent;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG
        )
        container_layout.setSpacing(modern_theme.SPACING_MD)

        left_card = ModernCard(
            title="Fotoğraf Seçimi",
            subtitle="İşlemek istediğiniz fotoğrafı seçin",
            show_frame=False
        )
        left_card.setObjectName("photoSelectionCard")
        left_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        content_layout = left_card.get_content_layout()
        content_layout.setObjectName("photoSelectionLayout")

        # Fotoğraf seç butonu
        select_btn = ModernButton("Fotoğraf Seç", variant="primary", size="lg")
        select_btn.setObjectName("selectPhotoButton")
        select_btn.clicked.connect(self._select_file)
        content_layout.addWidget(select_btn)

        # Dosya etiketi
        self.file_label = QLabel("Dosya seçilmedi")
        self.file_label.setObjectName("selectedFileLabel")
        self.file_label.setFont(QFont("", modern_theme.FONT_SIZE_BODY_SMALL))
        self.file_label.setStyleSheet(f"color: {modern_theme.TEXT_TERTIARY};")
        content_layout.addWidget(self.file_label)
        
        content_layout.addSpacing(modern_theme.SPACING_LG)
        
        # Önizleme başlığı
        preview_title = QLabel("Önizleme")
        preview_title.setObjectName("previewTitleLabel")
        preview_title_font = QFont()
        preview_title_font.setPointSize(modern_theme.FONT_SIZE_BODY)
        preview_title_font.setBold(True)
        preview_title.setFont(preview_title_font)
        preview_title.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        content_layout.addWidget(preview_title)
        
        # Önizleme alanı
        preview_frame = QFrame()
        preview_frame.setObjectName("previewFrame")
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {modern_theme.BACKGROUND_SECONDARY};
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_MD}px;
                min-height: 300px;
            }}
        """)
        preview_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(
            modern_theme.SPACING_MD, modern_theme.SPACING_MD,
            modern_theme.SPACING_MD, modern_theme.SPACING_MD
        )
        preview_layout.setObjectName("previewLayout")

        self.preview_label = PreviewLabel("Önizleme burada görünecek")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setMinimumHeight(220)
        preview_layout.addWidget(self.preview_label)
        
        content_layout.addWidget(preview_frame)
        
        container_layout.addWidget(left_card)
        parent_layout.addWidget(container, 1)
    
    def _create_right_panel(self, parent_layout):
        """Sağ paneli oluşturur"""
        container = QFrame()
        container.setObjectName("processingOptionsGroup")
        container.setStyleSheet(f"""
            QFrame {{
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_LG}px;
                background-color: transparent;
            }}
        """)
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG,
            modern_theme.SPACING_LG
        )
        container_layout.setSpacing(modern_theme.SPACING_MD)

        right_card = ModernCard(
            title="İşlem Ayarları",
            subtitle="Fotoğraf tipi ve düzen seçeneklerini belirleyin",
            show_frame=False
        )
        right_card.setObjectName("processingOptionsCard")
        right_card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        content_layout = right_card.get_content_layout()
        content_layout.setObjectName("processingOptionsLayout")

        output_section = QWidget()
        output_section.setObjectName("outputSection")
        output_layout = QHBoxLayout(output_section)
        output_layout.setContentsMargins(0, 0, 0, 0)
        output_layout.setSpacing(modern_theme.SPACING_SM)

        self.output_dir_btn = ModernButton("Çıkış Klasörü Seç", variant="secondary", size="md")
        self.output_dir_btn.setObjectName("selectOutputDirButton")
        self.output_dir_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(self.output_dir_btn)

        self.output_dir_label = QLabel("Çıkış klasörü seçilmedi")
        self.output_dir_label.setObjectName("outputDirLabel")
        self.output_dir_label.setStyleSheet(f"color: {modern_theme.TEXT_TERTIARY};")
        output_layout.addWidget(self.output_dir_label)
        output_layout.addStretch()

        content_layout.addWidget(output_section)
        
        # Fotoğraf Tipi
        self._create_photo_type_selector(content_layout)
        
        content_layout.addSpacing(modern_theme.SPACING_XL)
        
        # Sayfa Düzeni
        self._create_layout_selector(content_layout)
        
        content_layout.addStretch()
        
        # İşle butonu
        button_text = "İşlemi Başlat" if self.user_credits > 0 else "Hak Yok"
        self.process_btn = ModernButton(button_text, variant="primary", size="lg")
        self.process_btn.setObjectName("startProcessingButton")
        self.process_btn.clicked.connect(self._start_processing)
        content_layout.addWidget(self.process_btn)

        self.single_progress_label = QLabel()
        self.single_progress_label.setAlignment(Qt.AlignCenter)
        self.single_progress_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        self.single_progress_label.setVisible(False)
        content_layout.addWidget(self.single_progress_label)

        container_layout.addWidget(right_card)
        parent_layout.addWidget(container, 1)
        self._update_process_button_state()
    
    def _create_photo_type_selector(self, parent_layout):
        """Fotoğraf tipi seçici oluşturur"""
        section = QWidget()
        section.setObjectName("photoTypeSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(modern_theme.SPACING_SM)
        section_layout.setObjectName("photoTypeLayout")

        title = QLabel("Fotoğraf Tipi")
        title.setObjectName("photoTypeHeader")
        title.setFont(QFont("", modern_theme.FONT_SIZE_BODY, QFont.Bold))
        title.setStyleSheet(f"color: {modern_theme.TEXT_PRIMARY};")
        section_layout.addWidget(title)

        self.photo_type_group = QButtonGroup(self)
        self.photo_type_group.setExclusive(True)
        self.photo_type_group.setObjectName("photoTypeButtonGroup")

        photo_types = [
            ("Biyometrik 50x60 mm\n(Pasaport ve T.C. Kimlik Kartı için)", "biyometrik"),
            ("Vesikalık 45x60 mm\n(CV, Öğrenci Belgesi, Okul için)", "vesikalik"),
            ("ABD Vizesi 50x50 mm\n(Green Card ve ABD Vizesi için)", "abd_vizesi"),
            ("Schengen Vizesi 35x45 mm\n(Avrupa Ülkeleri Vizesi için)", "schengen")
        ]

        options_layout = QGridLayout()
        options_layout.setObjectName("photoTypeOptionsLayout")
        options_layout.setSpacing(modern_theme.SPACING_SM)
        options_layout.setColumnStretch(0, 1)
        options_layout.setColumnStretch(1, 1)

        for idx, (text, value) in enumerate(photo_types):
            option_btn = ChoiceButton(text)
            option_btn.setObjectName(f"photoTypeOption_{value}")
            option_btn.setChecked(value == self.photo_type)
            self.photo_type_group.addButton(option_btn, idx)
            option_btn.toggled.connect(lambda checked, v=value: self._on_photo_type_changed(v) if checked else None)
            row = idx // 2
            col = idx % 2
            options_layout.addWidget(option_btn, row, col)

        section_layout.addLayout(options_layout)
        parent_layout.addWidget(section)

    def _create_layout_selector(self, parent_layout):
        """Sayfa düzeni seçici oluşturur"""
        section = QWidget()
        section.setObjectName("pageLayoutSection")
        section_layout = QVBoxLayout(section)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(modern_theme.SPACING_SM)
        section_layout.setObjectName("pageLayoutOptions")

        title = QLabel("Sayfa Düzeni")
        title.setObjectName("pageLayoutHeader")
        title.setFont(QFont("", modern_theme.FONT_SIZE_BODY, QFont.Bold))
        title.setStyleSheet(f"color: {modern_theme.TEXT_PRIMARY};")
        section_layout.addWidget(title)

        self.layout_type_group = QButtonGroup(self)
        self.layout_type_group.setExclusive(True)
        self.layout_type_group.setObjectName("pageLayoutButtonGroup")

        layouts = [
            ("2'li Düzen", "2li"),
            ("4'lü Düzen", "4lu")
        ]

        options_layout = QGridLayout()
        options_layout.setObjectName("pageLayoutOptionsGrid")
        options_layout.setSpacing(modern_theme.SPACING_SM)
        options_layout.setColumnStretch(0, 1)
        options_layout.setColumnStretch(1, 1)

        for idx, (text, value) in enumerate(layouts):
            option_btn = ChoiceButton(text)
            option_btn.setObjectName(f"pageLayoutOption_{value}")
            option_btn.setChecked(value == self.layout_type)
            self.layout_type_group.addButton(option_btn, idx)
            option_btn.toggled.connect(lambda checked, v=value: self._on_layout_type_changed(v) if checked else None)
            options_layout.addWidget(option_btn, 0, idx)

        section_layout.addLayout(options_layout)
        parent_layout.addWidget(section)
    
    def _on_photo_type_changed(self, value):
        """Fotoğraf tipi değiştiğinde"""
        self.photo_type = value
    
    def _on_layout_type_changed(self, value):
        """Düzen tipi değiştiğinde"""
        self.layout_type = value
    
    def _select_file(self):
        """Dosya seçme dialogu"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Fotoğraf Seç",
            "",
            "Resim Dosyaları (*.jpg *.jpeg *.png *.bmp);;Tüm Dosyalar (*)"
        )
        
        if file_path:
            path = Path(file_path)
            is_valid, message = validate_image_file(path)
            if not is_valid:
                show_styled_message(self, "Dosya", message, QMessageBox.Warning)
                return
            self.input_path = str(path)
            file_name = path.name
            self.file_label.setText(f"Seçilen: {file_name}")
            if not self.preview_label.set_image_from_path(str(path)):
                show_styled_message(self, "Önizleme", "Seçtiğiniz fotoğraf yüklenemedi.", QMessageBox.Warning)
            self._update_process_button_state()

    def _select_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Çıkış klasörü seç")
        if folder:
            self.output_dir = Path(folder)
            display_name = self.output_dir.name or str(self.output_dir)
            self.output_dir_label.setText(f"Çıkış: {display_name}")
            self._update_process_button_state()

    def _open_shop(self):
        """Mağaza sayfasını açar"""
        try:
            webbrowser.open(modern_theme.SHOP_URL)
        except Exception as e:
            show_styled_message(self, "Hata", f"Tarayıcı açılamadı: {e}", QMessageBox.Warning)
    
    def _show_code_dialog(self):
        """Kredi kodu dialogunu gösterir ve işlemi arka planda yürütür"""
        if not getattr(self.user, "uid", None):
            show_styled_message(self, "Kod", "Kullanıcı bilgisi bulunamadı.", QMessageBox.Warning)
            return

        dialog = CodeInputDialog(self)

        def _clear_thread():
            self._credit_code_thread = None

        def _on_success(credits_added: int):
            dialog.set_busy(False)
            dialog.accept()
            if credits_added:
                self.user_credits += credits_added
                self._update_credit_display()
            show_styled_message(
                self,
                "Hak Eklendi",
                f"Kod başarıyla kullanıldı!\n"
                f"+{credits_added} hak eklendi.\n"
                f"Toplam hak: {self.user_credits}",
            )

        def _on_error(message: str):
            dialog.set_busy(False)
            dialog.set_status(message or "Kod doğrulanamadı", is_error=True)

        def _start_redeem():
            code = dialog.get_code().upper()
            if not code:
                dialog.set_status("Kod alanı boş bırakılamaz.", is_error=True)
                return
            if self._credit_code_thread and self._credit_code_thread.isRunning():
                return
            dialog.set_status("Kod doğrulanıyor...", is_error=False)
            dialog.set_busy(True)
            self._credit_code_thread = CreditCodeThread(code, self.user.uid)
            self._credit_code_thread.success.connect(_on_success)
            self._credit_code_thread.error.connect(_on_error)
            self._credit_code_thread.finished.connect(_clear_thread)
            self._credit_code_thread.start()

        dialog.ok_btn.clicked.connect(_start_redeem)
        dialog.input_field.returnPressed.connect(_start_redeem)
        dialog.exec()
    
    def _open_multi_process(self):
        """Çoklu işlem sayfasına geçiş"""
        self.page_stack.setCurrentWidget(self.batch_page)

    def _return_to_main_page(self):
        self.page_stack.setCurrentWidget(self.main_page)

    def _logout(self):
        """Çıkış yapar"""
        self.logout_signal.emit()
        self.close()
    
    def _start_processing(self):
        """İşlemi başlatır"""
        if not self.input_path:
            show_styled_message(self, "Uyarı", "Lütfen önce bir fotoğraf seçin.", QMessageBox.Warning)
            return
        
        if self.user_credits <= 0:
            show_styled_message(self, "Uyarı", "Yeterli hakkınız bulunmamaktadır.", QMessageBox.Warning)
            return

        if not self.output_dir:
            show_styled_message(self, "Çıkış Klasörü", "Lütfen bir çıkış klasörü seçin.", QMessageBox.Warning)
            return

        if self.single_worker and self.single_worker.isRunning():
            show_styled_message(self, "İşlem", "Devam eden bir işlem var.", QMessageBox.Warning)
            return

        job = PhotoJob(
            input_path=Path(self.input_path),
            photo_type=self.photo_type,
            layout_type=self.layout_type,
            output_path=self._build_single_output_path(Path(self.input_path))
        )

        self._set_single_controls_enabled(False)
        self.single_progress_label.setText("0/1 photos processed")
        self.single_progress_label.setVisible(True)
        self._start_single_worker(job)

    def _build_single_output_path(self, input_path: Path) -> Path:
        assert self.output_dir is not None
        self.output_dir.mkdir(parents=True, exist_ok=True)
        return self.output_dir / f"{input_path.stem}_{self.photo_type}_{self.layout_type}.jpg"

    def _start_single_worker(self, job: PhotoJob):
        self.single_worker = SinglePhotoWorker(self.photo_processor, job, self.user.uid)
        self.single_worker.progress.connect(self._update_single_progress)
        self.single_worker.finished.connect(self._on_single_finished)
        self.single_worker.error.connect(self._on_single_error)
        self.single_worker.credit_error.connect(self._on_single_credit_error)
        self.single_worker.credit_updated.connect(self._on_credit_balance_updated)
        self.single_worker.finished.connect(self._reset_single_worker)
        self.single_worker.error.connect(lambda _: self._reset_single_worker())
        self.single_worker.start()

    def _update_single_progress(self, processed: int, total: int):
        self.single_progress_label.setText(f"{processed}/{total} photos processed")

    def _on_single_finished(self, result):
        self._set_single_controls_enabled(True)
        show_styled_message(self, "", "İşlem başarıyla tamamlandı.", QMessageBox.NoIcon)

    def _on_single_error(self, message: str):
        show_styled_message(self, "İşlem Hatası", message, QMessageBox.Warning)
        self._set_single_controls_enabled(True)

    def _on_single_credit_error(self, message: str):
        self.single_progress_label.setVisible(False)
        show_styled_message(self, "Kredi", message or "Kredi kullanılamadı", QMessageBox.Warning)
        self._set_single_controls_enabled(True)

    def _reset_single_worker(self):
        if self.single_worker:
            self.single_worker.deleteLater()
            self.single_worker = None
        self.single_progress_label.setVisible(False)

    def _set_single_controls_enabled(self, enabled: bool):
        self.single_controls_enabled = enabled
        if hasattr(self, "output_dir_btn"):
            self.output_dir_btn.setEnabled(enabled)
        self._update_process_button_state()

    def _update_credit_display(self):
        if hasattr(self, "welcome_info"):
            username = self.user.email.split("@")[0].capitalize() if self.user.email else "Kullanıcı"
            self.welcome_info.set_welcome_text(f"Hoş geldin, {username}. {self.user_credits} Adet Hakkınız Kaldı.")
        self._update_process_button_state()

    def _update_process_button_state(self):
        if not hasattr(self, "process_btn"):
            return
        worker_running = bool(self.single_worker and self.single_worker.isRunning())
        can_process = bool(
            self.single_controls_enabled and not worker_running and self.input_path and self.output_dir and self.user_credits > 0
        )
        self.process_btn.setEnabled(can_process)
        self.process_btn.setText("Hak Yok" if self.user_credits <= 0 else "İşlemi Başlat")

    def _on_credit_balance_updated(self, new_credits: int):
        self.user_credits = new_credits
        self._update_credit_display()
        if hasattr(self, "batch_page") and self.batch_page:
            self.batch_page.set_credit_balance(new_credits)

    def _on_batch_credits_updated(self, new_credits: int):
        self._on_credit_balance_updated(new_credits)
    
    def closeEvent(self, event: QCloseEvent):
        """Pencere kapatıldığında sinyal gönder"""
        self.close_signal.emit()
        event.accept()
