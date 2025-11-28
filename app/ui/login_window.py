#!/usr/bin/env python3

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont, QCloseEvent

import re
import string
import secrets
from app.config import firebase_manager
from app.ui.widgets import show_styled_message
from app.services.email_service import email_sender
from firebase_admin import auth as firebase_auth
from app.logger import logger


# Mod sabitleri
MODE_LOGIN = "login"
MODE_REGISTER = "register"
MODE_VERIFY = "verify"
MODE_RESET_PASSWORD = "reset_password"
MODE_RESET_CODE = "reset_code"
MODE_RESET_NEW_PASSWORD = "reset_new_password"


class LoginThread(QThread):
    """Giriş işlemini arka planda yapar"""
    success = Signal(object)
    error = Signal(str)

    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        try:
            user = firebase_manager.sign_in_user(self.email, self.password)
            self.success.emit(user)
        except Exception as e:
            error_msg = str(e).lower()
            if "user not found" in error_msg or "kullanıcı bulunamadı" in error_msg:
                self.error.emit("Bu email ile kayıtlı kullanıcı bulunamadı")
            elif "email_not_verified" in error_msg or "email not verified" in error_msg:
                self.error.emit("EMAIL_NOT_VERIFIED")
            elif "password" in error_msg or "şifre" in error_msg:
                self.error.emit("Email veya şifre hatalı")
            elif "network" in error_msg or "connection" in error_msg:
                self.error.emit("İnternet bağlantısı yok")
            else:
                self.error.emit("Giriş başarısız")


class RegisterThread(QThread):
    """Kayıt işlemini arka planda yapar"""
    success = Signal(object)
    error = Signal(str)

    def __init__(self, email, password):
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        try:
            user = firebase_manager.create_user(self.email, self.password)
            self.success.emit(user)
        except Exception as e:
            error_msg = str(e).lower()
            if "email-already-in-use" in error_msg or "emailalreadyexists" in error_msg:
                self.error.emit("Bu email adresi zaten kayıtlı")
            elif "weak-password" in error_msg or "weak password" in error_msg:
                self.error.emit("Şifre en az 6 karakter olmalı")
            elif "invalid-email" in error_msg or "invalid email" in error_msg:
                self.error.emit("Geçersiz email adresi")
            else:
                self.error.emit(f"Kayıt başarısız: {str(e)}")


class VerifyCodeThread(QThread):
    """Email doğrulama kodunu arka planda doğrular"""
    success = Signal()
    error = Signal(str)

    def __init__(self, code, email):
        super().__init__()
        self.code = code
        self.email = email

    def run(self):
        try:
            success, message = firebase_manager.verify_code(self.code, self.email)
            if success:
                self.success.emit()
            else:
                self.error.emit(message)
        except Exception as e:
            self.error.emit(str(e))


class SendResetCodeThread(QThread):
    """Şifre sıfırlama kodunu arka planda gönderir"""
    success = Signal()
    error = Signal(str)

    def __init__(self, email):
        super().__init__()
        self.email = email

    def run(self):
        try:
            reset_code, code_id = firebase_manager.create_password_reset_code(self.email)
            email_sent = email_sender.send_password_reset_email(self.email, reset_code)
            if email_sent:
                self.success.emit()
            else:
                self.error.emit("Email gönderilemedi. Lütfen tekrar deneyin.")
        except Exception as e:
            error_msg = str(e).lower()
            if "user not found" in error_msg or "kullanıcı bulunamadı" in error_msg:
                self.error.emit("Bu email ile kayıtlı kullanıcı bulunamadı")
            else:
                self.error.emit(f"Hata: {str(e)}")


class VerifyResetCodeThread(QThread):
    """Şifre sıfırlama kodunu arka planda doğrular"""
    success = Signal()
    error = Signal(str)

    def __init__(self, code, email):
        super().__init__()
        self.code = code
        self.email = email

    def run(self):
        try:
            success, message = firebase_manager.verify_password_reset_code(self.code, self.email)
            if success:
                self.success.emit()
            else:
                self.error.emit(message)
        except Exception as e:
            self.error.emit(str(e))


class ResetPasswordThread(QThread):
    """Şifre sıfırlama işlemini arka planda yapar"""
    success = Signal()
    error = Signal(str)

    def __init__(self, email, new_password, reset_code):
        super().__init__()
        self.email = email
        self.new_password = new_password
        self.reset_code = reset_code

    def run(self):
        try:
            success, message = firebase_manager.reset_user_password(self.email, self.new_password, self.reset_code)
            if success:
                self.success.emit()
            else:
                self.error.emit(message)
        except Exception as e:
            self.error.emit(str(e))


class ResendCodeThread(QThread):
    """Doğrulama kodunu yeniden gönderir"""
    success = Signal()
    error = Signal(str)

    def __init__(self, user_id, email):
        super().__init__()
        self.user_id = user_id
        self.email = email

    def run(self):
        try:
            code, code_id = firebase_manager.create_verification_code(self.user_id, self.email)
            email_sent = email_sender.send_verification_email(self.email, code)
            if email_sent:
                self.success.emit()
            else:
                self.error.emit("Email gönderilemedi")
        except Exception as e:
            self.error.emit(str(e))


class LoginWindow(QWidget):
    """Modern ve sade giriş ekranı - tüm özelliklerle"""
    
    login_success = Signal(object)
    window_closed = Signal()

    # Validasyon sabitleri
    EMAIL_MAX_LENGTH = 254
    PASSWORD_MIN_LENGTH = 6
    PASSWORD_MAX_LENGTH = 128
    _EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    COMMON_PASSWORDS = {
        '123456', 'password', '123456789', '12345678', '12345',
        '1234567', '1234567890', 'qwerty', 'abc123', 'password123'
    }

    def __init__(self):
        super().__init__()
        self.current_mode = MODE_LOGIN
        self.pending_email = None
        self.reset_code = None
        self.current_user = None
        
        # Thread'ler
        self.login_thread = None
        self.register_thread = None
        self.verify_thread = None
        self.send_reset_thread = None
        self.verify_reset_thread = None
        self.reset_password_thread = None
        self.resend_thread = None
        
        self.setObjectName("loginWindow")
        self._setup_ui()

    def _setup_ui(self):
        self.setWindowTitle("BiyoVes - Giriş")
        self.setMinimumSize(420, 600)
        self.resize(520, 700)
        self.setStyleSheet("background-color: #fafafa;")
        self._center_window()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 32, 32, 32)
        main_layout.setSpacing(16)
        main_layout.setObjectName("mainLayout")
        
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        header_layout.setAlignment(Qt.AlignHCenter)
        header_layout.setObjectName("headerLayout")
        
        self.title = QLabel("BiyoVes")
        self.title.setObjectName("titleLabel")
        self.title.setFont(QFont("", 28, QFont.Bold))
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("color: #1a73e8;")
        self.title.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header_layout.addWidget(self.title)
        
        self.subtitle = QLabel("Hesabınıza giriş yapın")
        self.subtitle.setObjectName("subtitleLabel")
        self.subtitle.setFont(QFont("", 13))
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setStyleSheet("color: #5f6368;")
        self.subtitle.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        header_layout.addWidget(self.subtitle)
        
        main_layout.addLayout(header_layout)
        
        self.card = QFrame()
        self.card.setObjectName("formCard")
        self.card.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
                border: none;
            }
        """)
        self.card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.card.setMinimumHeight(360)
        
        self.card_layout = QGridLayout(self.card)
        self.card_layout.setObjectName("formGridLayout")
        self.card_layout.setSpacing(10)
        self.card_layout.setContentsMargins(28, 28, 28, 28)
        self.card_layout.setColumnStretch(0, 1)
        
        main_layout.addWidget(self.card)
        
        self._error_style = """
            color: #d32f2f;
            font-size: 13px;
            background-color: #fdecea;
            padding: 10px;
            border-radius: 6px;
        """
        
        self.error_label = QLabel()
        self.error_label.setObjectName("errorLabel")
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.error_label.setMinimumHeight(56)
        self._hide_error_message()
        
        self.error_container = QFrame()
        self.error_container.setObjectName("errorContainer")
        self.error_container.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.error_container.setMinimumHeight(56)
        error_layout = QVBoxLayout(self.error_container)
        error_layout.setContentsMargins(0, 0, 0, 0)
        error_layout.setSpacing(0)
        error_layout.setObjectName("errorLayout")
        error_layout.addWidget(self.error_label)
        
        main_layout.addWidget(self.error_container)
        main_layout.addStretch(1)
        
        self._create_login_form()

    def _center_window(self):
        screen = self.screen().availableGeometry()
        frame = self.frameGeometry()
        frame.moveCenter(screen.center())
        self.move(frame.topLeft())

    def _clear_card(self):
        """Form kartını temizler"""
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.spacerItem():
                self.card_layout.removeItem(item)

    def _create_form_field(self, row, label_text, placeholder, is_password=False, attr_name=None):
        """Form alanı oluşturur - Grid layout için"""
        # Label
        label = QLabel(label_text)
        label.setObjectName(f"{attr_name}_label" if attr_name else f"formLabel_{row}")
        label.setStyleSheet("font-weight: 500; color: #202124; font-size: 13px;")
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        label.setMinimumHeight(24)
        self.card_layout.addWidget(label, row, 0, 1, 1)
        
        # Entry
        entry = QLineEdit()
        entry.setObjectName(attr_name if attr_name else f"formField_{row}")
        entry.setPlaceholderText(placeholder)
        if is_password:
            entry.setEchoMode(QLineEdit.Password)
        entry.setMinimumHeight(42)
        entry.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        entry.setStyleSheet("""
            QLineEdit {
                border: none;
                outline: none;
                border-radius: 6px;
                padding: 0 14px;
                font-size: 14px;
                color: #202124;
                background-color: #f5f5f5;
            }
            QLineEdit:focus {
                border: none;
                outline: none;
                background-color: #f0f0f0;
            }
        """)
        self.card_layout.addWidget(entry, row + 1, 0, 1, 1)
        
        # Boşluk için spacer
        spacer = QSpacerItem(20, 8, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.card_layout.addItem(spacer, row + 2, 0, 1, 1)
        
        if attr_name:
            setattr(self, attr_name, entry)
        
        return entry, row + 3  # Sonraki satır numarasını döndür (label + entry + spacer)

    def _create_button(self, row, text, command, is_primary=True):
        """Buton oluşturur - Grid layout için"""
        btn = QPushButton(text)
        sanitized = ''.join(ch if (ch.isalnum() and ch.isascii()) else '_' for ch in text.lower())
        sanitized = '_'.join(filter(None, sanitized.split('_')))
        btn.setObjectName(f"formButton_{sanitized or 'action'}")
        btn.setMinimumHeight(48)
        btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if is_primary:
            btn.setStyleSheet("""
            QPushButton {
                background-color: #1a73e8;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1765cc;
            }
            QPushButton:pressed {
                background-color: #1557b0;
            }
            QPushButton:disabled {
                background-color: #e0e0e0;
                color: #9e9e9e;
            }
        """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #1a73e8;
                    border: none;
                    border-radius: 6px;
                    font-size: 13px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #e8f0fe;
                }
                QPushButton:pressed {
                    background-color: #d2e3fc;
                }
            """)
        btn.clicked.connect(command)
        self.card_layout.addWidget(btn, row, 0, 1, 1)
        
        # Butonlar arası boşluk için spacer
        spacer = QSpacerItem(20, 6, QSizePolicy.Minimum, QSizePolicy.Fixed)
        self.card_layout.addItem(spacer, row + 1, 0, 1, 1)
        
        return btn, row + 2  # Sonraki satır numarasını döndür (buton + spacer)

    def _create_login_form(self):
        """Giriş formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_LOGIN
        self.subtitle.setText("Hesabınıza giriş yapın")
        
        row = 0
        _, row = self._create_form_field(row, "E-posta", "ornek@email.com", False, "email_entry")
        _, row = self._create_form_field(row, "Şifre", "********", True, "password_entry")
        
        self.main_button, row = self._create_button(row, "Giriş Yap", self._handle_main_action)
        _, row = self._create_button(row, "Şifremi Unuttum", self._show_forgot_password_ui, False)
        
        switch_text = "Hesabınız yok mu? Kayıt olun"
        self._create_button(row, switch_text, self._toggle_mode, False)
        
        if hasattr(self, 'email_entry') and hasattr(self, 'password_entry'):
            self.email_entry.returnPressed.connect(lambda: self.password_entry.setFocus())
            self.password_entry.returnPressed.connect(self._handle_main_action)

    def _create_register_form(self):
        """Kayıt formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_REGISTER
        self.subtitle.setText("Yeni hesap oluşturun")
        
        row = 0
        _, row = self._create_form_field(row, "E-posta", "ornek@email.com", False, "email_entry")
        _, row = self._create_form_field(row, "Şifre", "********", True, "password_entry")
        _, row = self._create_form_field(row, "Şifre Tekrar", "********", True, "password_confirm_entry")
        
        self.main_button, row = self._create_button(row, "Kayıt Ol", self._handle_main_action)
        
        switch_text = "Zaten hesabınız var mı? Giriş yapın"
        self._create_button(row, switch_text, self._toggle_mode, False)
        
        if hasattr(self, 'email_entry') and hasattr(self, 'password_entry') and hasattr(self, 'password_confirm_entry'):
            self.email_entry.returnPressed.connect(lambda: self.password_entry.setFocus())
            self.password_entry.returnPressed.connect(lambda: self.password_confirm_entry.setFocus())
            self.password_confirm_entry.returnPressed.connect(self._handle_main_action)

    def _create_verification_form(self):
        """Email doğrulama formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_VERIFY
        self.subtitle.setText("Email doğrulama kodu girin")
        
        row = 0
        _, row = self._create_form_field(row, "Doğrulama Kodu", "6 haneli kodu girin", False, "code_entry")
        
        self.main_button, row = self._create_button(row, "Doğrula", self._verify_code)
        _, row = self._create_button(row, "Kodu Yeniden Gönder", self._resend_code, False)
        self._create_button(row, "Geri Dön", self._back_to_login, False)
        
        if hasattr(self, 'code_entry'):
            self.code_entry.returnPressed.connect(self._verify_code)

    def _create_forgot_password_form(self):
        """Şifre sıfırlama formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_RESET_PASSWORD
        self.subtitle.setText("Şifre sıfırlama")
        
        row = 0
        _, row = self._create_form_field(row, "E-posta Adresiniz", "ornek@email.com", False, "reset_email_entry")
        
        self.main_button, row = self._create_button(row, "Sıfırlama Kodu Gönder", self._send_reset_code)
        self._create_button(row, "Geri Dön", self._back_to_login, False)
        
        if hasattr(self, 'reset_email_entry'):
            self.reset_email_entry.returnPressed.connect(self._send_reset_code)

    def _create_reset_code_form(self):
        """Şifre sıfırlama kodu formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_RESET_CODE
        self.subtitle.setText("Şifre sıfırlama kodu")
        
        row = 0
        _, row = self._create_form_field(row, "6 Haneli Kod", "123456", False, "reset_code_entry")
        
        self.main_button, row = self._create_button(row, "Kodu Doğrula", self._verify_reset_code)
        _, row = self._create_button(row, "Kodu Yeniden Gönder", self._resend_reset_code, False)
        self._create_button(row, "Geri Dön", self._back_to_login, False)
        
        if hasattr(self, 'reset_code_entry'):
            self.reset_code_entry.returnPressed.connect(self._verify_reset_code)

    def _create_new_password_form(self):
        """Yeni şifre formunu oluşturur"""
        self._clear_card()
        self.current_mode = MODE_RESET_NEW_PASSWORD
        self.subtitle.setText("Yeni şifre belirleyin")
        
        row = 0
        _, row = self._create_form_field(row, "Yeni Şifre", "********", True, "new_password_entry")
        _, row = self._create_form_field(row, "Şifre Tekrar", "********", True, "new_password_confirm_entry")
        
        self.main_button, row = self._create_button(row, "Şifreyi Sıfırla", self._reset_password)
        self._create_button(row, "Geri Dön", self._back_to_login, False)
        
        if hasattr(self, 'new_password_entry') and hasattr(self, 'new_password_confirm_entry'):
            self.new_password_entry.returnPressed.connect(lambda: self.new_password_confirm_entry.setFocus())
            self.new_password_confirm_entry.returnPressed.connect(self._reset_password)

    def _validate_email(self, email):
        """Email validasyonu"""
        if not email or not isinstance(email, str):
            return False
        
        email = email.strip().lower()
        
        if not self._EMAIL_REGEX.match(email):
            return False
        
        if len(email) > self.EMAIL_MAX_LENGTH:
            return False
        
        dangerous_chars = {'<', '>', '"', "'", '&', ';', '(', ')', '`'}
        if any(char in email for char in dangerous_chars):
            return False
        
        return True

    def _validate_password(self, password):
        """Şifre validasyonu"""
        if not password or not isinstance(password, str):
            return False, "Şifre boş olamaz"
        
        if len(password) < self.PASSWORD_MIN_LENGTH:
            return False, f"Şifre en az {self.PASSWORD_MIN_LENGTH} karakter olmalı"
        
        if len(password) > self.PASSWORD_MAX_LENGTH:
            return False, f"Şifre çok uzun (max {self.PASSWORD_MAX_LENGTH} karakter)"
        
        if password.strip() != password:
            return False, "Şifre başında/sonunda boşluk olamaz"
        
        if password.lower() in self.COMMON_PASSWORDS:
            return False, "Bu şifre çok yaygın, lütfen daha güvenli bir şifre seçin"
        
        return True, "Geçerli"

    def _get_user_friendly_error(self, error):
        """Kullanıcı dostu hata mesajı döndürür"""
        error_lower = str(error).lower()
        
        if "password mismatch" in error_lower:
            return "Şifre hatalı"
        if "invalid credentials" in error_lower:
            return "Email veya şifre hatalı"
        if "user not found" in error_lower or "kullanıcı bulunamadı" in error_lower:
            return "Bu email adresi ile kayıtlı kullanıcı bulunamadı"
        if "email-already-in-use" in error_lower or "emailalreadyexists" in error_lower:
            return "Bu email adresi zaten kayıtlı"
        if "email_not_verified" in error_lower or "email not verified" in error_lower:
            return "Email adresiniz doğrulanmamış"
        if "weak-password" in error_lower or "weak password" in error_lower:
            return f"Şifre en az {self.PASSWORD_MIN_LENGTH} karakter olmalı"
        if "invalid-email" in error_lower or "invalid email" in error_lower:
            return "Geçersiz email adresi"
        if "invalid-verification-code" in error_lower or "invalid code" in error_lower:
            return "Geçersiz doğrulama kodu"
        if "expired" in error_lower or "timeout" in error_lower:
            return "Kod süresi dolmuş, yeni kod isteyin"
        if "network" in error_lower or "connection" in error_lower:
            return "İnternet bağlantınızı kontrol edin"
        
        return "Bir hata oluştu. Lütfen tekrar deneyin"

    def _handle_main_action(self):
        """Ana buton tıklandığında (giriş veya kayıt)"""
        if self.current_mode == MODE_LOGIN:
            self._login()
        elif self.current_mode == MODE_REGISTER:
            self._register()

    def _login(self):
        """Giriş işlemi"""
        email = self.email_entry.text().strip()
        password = self.password_entry.text()
        
        if not email or not password:
            self._show_error("Tüm alanları doldurun")
            return
        
        if not self._validate_email(email):
            self._show_error("Geçerli bir email adresi girin")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Giriş yapılıyor...")
        self._hide_error_message()
        
        self.login_thread = LoginThread(email, password)
        self.login_thread.success.connect(self._on_login_success)
        self.login_thread.error.connect(self._on_login_error)
        self.login_thread.finished.connect(lambda: setattr(self, 'login_thread', None))
        self.login_thread.start()

    def _on_login_success(self, user):
        """Giriş başarılı"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Giriş Yap")
        self.login_success.emit(user)

    def _on_login_error(self, error_msg):
        """Giriş hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Giriş Yap")
        
        if error_msg == "EMAIL_NOT_VERIFIED":
            # Email doğrulanmamış, doğrulama ekranına yönlendir
            self.pending_email = self.email_entry.text().strip()
            try:
                self.current_user = firebase_auth.get_user_by_email(self.pending_email)
                self._create_verification_form()
                # Otomatik olarak kod gönder (form oluşturulduktan sonra)
                if self.current_user and self.pending_email:
                    self.resend_thread = ResendCodeThread(self.current_user.uid, self.pending_email)
                    self.resend_thread.success.connect(self._on_resend_success)
                    self.resend_thread.error.connect(lambda msg: None)  # Sessizce hata yoksay
                    self.resend_thread.finished.connect(lambda: setattr(self, 'resend_thread', None))
                    self.resend_thread.start()
            except Exception as e:
                self._show_error("Kullanıcı bilgisi alınamadı")
        else:
            self._show_error(error_msg)

    def _register(self):
        """Kayıt işlemi"""
        email = self.email_entry.text().strip()
        password = self.password_entry.text()
        password_confirm = self.password_confirm_entry.text()
        
        if not email or not password or not password_confirm:
            self._show_error("Tüm alanları doldurun")
            return
        
        if not self._validate_email(email):
            self._show_error("Geçerli bir email adresi girin")
            return
        
        is_valid, msg = self._validate_password(password)
        if not is_valid:
            self._show_error(msg)
            return
        
        if password != password_confirm:
            self._show_error("Şifreler eşleşmiyor")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Kayıt ediliyor...")
        self._hide_error_message()
        
        self.register_thread = RegisterThread(email, password)
        self.register_thread.success.connect(self._on_register_success)
        self.register_thread.error.connect(self._on_register_error)
        self.register_thread.finished.connect(lambda: setattr(self, 'register_thread', None))
        self.register_thread.start()

    def _on_register_success(self, user):
        """Kayıt başarılı - email doğrulama ekranına yönlendir"""
        self.current_user = user
        self.pending_email = user.email
        
        # Doğrulama kodu oluştur ve gönder
        try:
            code, code_id = firebase_manager.create_verification_code(user.uid, user.email)
            email_sender.send_verification_email(user.email, code)
        except Exception as e:
            logger.exception("Kod gönderme hatası: %s", e)
        
        self._create_verification_form()

    def _on_register_error(self, error_msg):
        """Kayıt hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Kayıt Ol")
        self._show_error(error_msg)

    def _verify_code(self):
        """Email doğrulama kodu doğrulama"""
        code = self.code_entry.text().strip()
        
        if not code:
            self._show_error("Lütfen doğrulama kodunu girin")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Doğrulanıyor...")
        self._hide_error_message()
        
        self.verify_thread = VerifyCodeThread(code, self.pending_email)
        self.verify_thread.success.connect(self._on_verify_success)
        self.verify_thread.error.connect(self._on_verify_error)
        self.verify_thread.finished.connect(lambda: setattr(self, 'verify_thread', None))
        self.verify_thread.start()

    def _on_verify_success(self):
        """Kod doğrulama başarılı"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Doğrula")
        
        # Kullanıcıyı tekrar al (email doğrulandı)
        try:
            user = firebase_auth.get_user_by_email(self.pending_email)
            self.login_success.emit(user)
        except Exception as e:
            self._show_error("Kullanıcı bilgisi alınamadı")

    def _on_verify_error(self, error_msg):
        """Kod doğrulama hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Doğrula")
        self._show_error(error_msg)

    def _resend_code(self):
        """Doğrulama kodunu yeniden gönder"""
        if not self.pending_email or not self.current_user:
            self._show_error("Kullanıcı bilgisi bulunamadı!")
            return
        
        self.resend_thread = ResendCodeThread(self.current_user.uid, self.pending_email)
        self.resend_thread.success.connect(self._on_resend_success)
        self.resend_thread.error.connect(self._on_resend_error)
        self.resend_thread.finished.connect(lambda: setattr(self, 'resend_thread', None))
        self.resend_thread.start()

    def _on_resend_success(self):
        """Kod yeniden gönderme başarılı"""
        show_styled_message(self, "Başarılı", "Doğrulama kodu yeniden gönderildi!")

    def _on_resend_error(self, error_msg):
        """Kod yeniden gönderme hatası"""
        self._show_error(f"Kod gönderilemedi: {error_msg}")

    def _send_reset_code(self):
        """Şifre sıfırlama kodu gönder"""
        email = self.reset_email_entry.text().strip()
        
        if not email:
            self._show_error("Lütfen email adresinizi girin")
            return
        
        if not self._validate_email(email):
            self._show_error("Geçerli bir email adresi girin")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Kod gönderiliyor...")
        self._hide_error_message()
        
        self.send_reset_thread = SendResetCodeThread(email)
        self.send_reset_thread.success.connect(self._on_send_reset_success)
        self.send_reset_thread.error.connect(self._on_send_reset_error)
        self.send_reset_thread.finished.connect(lambda: setattr(self, 'send_reset_thread', None))
        self.send_reset_thread.start()

    def _on_send_reset_success(self):
        """Şifre sıfırlama kodu gönderme başarılı"""
        self.pending_email = self.reset_email_entry.text().strip()
        self._create_reset_code_form()

    def _on_send_reset_error(self, error_msg):
        """Şifre sıfırlama kodu gönderme hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Sıfırlama Kodu Gönder")
        self._show_error(error_msg)

    def _verify_reset_code(self):
        """Şifre sıfırlama kodunu doğrula"""
        code = self.reset_code_entry.text().strip()
        
        if not code:
            self._show_error("Lütfen kodu girin")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Doğrulanıyor...")
        self._hide_error_message()
        
        self.verify_reset_thread = VerifyResetCodeThread(code, self.pending_email)
        self.verify_reset_thread.success.connect(self._on_verify_reset_success)
        self.verify_reset_thread.error.connect(self._on_verify_reset_error)
        self.verify_reset_thread.finished.connect(lambda: setattr(self, 'verify_reset_thread', None))
        self.verify_reset_thread.start()

    def _on_verify_reset_success(self):
        """Şifre sıfırlama kodu doğrulama başarılı"""
        self.reset_code = self.reset_code_entry.text().strip()
        self._create_new_password_form()

    def _on_verify_reset_error(self, error_msg):
        """Şifre sıfırlama kodu doğrulama hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Kodu Doğrula")
        self._show_error(error_msg)

    def _reset_password(self):
        """Yeni şifre belirle"""
        new_password = self.new_password_entry.text()
        confirm_password = self.new_password_confirm_entry.text()
        
        if not new_password or not confirm_password:
            self._show_error("Tüm alanları doldurun")
            return
        
        is_valid, msg = self._validate_password(new_password)
        if not is_valid:
            self._show_error(msg)
            return
        
        if new_password != confirm_password:
            self._show_error("Şifreler eşleşmiyor")
            return
        
        self.main_button.setEnabled(False)
        self.main_button.setText("Şifre sıfırlanıyor...")
        self._hide_error_message()
        
        self.reset_password_thread = ResetPasswordThread(self.pending_email, new_password, self.reset_code)
        self.reset_password_thread.success.connect(self._on_reset_password_success)
        self.reset_password_thread.error.connect(self._on_reset_password_error)
        self.reset_password_thread.finished.connect(lambda: setattr(self, 'reset_password_thread', None))
        self.reset_password_thread.start()

    def _on_reset_password_success(self):
        """Şifre sıfırlama başarılı"""
        show_styled_message(
            self,
            "Başarılı",
            "Şifreniz başarıyla sıfırlandı! Yeni şifrenizle giriş yapabilirsiniz."
        )
        self._back_to_login()

    def _on_reset_password_error(self, error_msg):
        """Şifre sıfırlama hatası"""
        self.main_button.setEnabled(True)
        self.main_button.setText("Şifreyi Sıfırla")
        self._show_error(error_msg)

    def _resend_reset_code(self):
        """Şifre sıfırlama kodunu yeniden gönder"""
        if not self.pending_email:
            self._show_error("Email bilgisi bulunamadı!")
            return
        
        # Doğrudan email ile kod gönder (form widget'ına güvenme)
        self.send_reset_thread = SendResetCodeThread(self.pending_email)
        self.send_reset_thread.success.connect(self._on_resend_reset_success)
        self.send_reset_thread.error.connect(self._on_resend_reset_error)
        self.send_reset_thread.finished.connect(lambda: setattr(self, 'send_reset_thread', None))
        self.send_reset_thread.start()
    
    def _on_resend_reset_success(self):
        """Şifre sıfırlama kodunu yeniden gönderme başarılı"""
        show_styled_message(self, "Başarılı", "Şifre sıfırlama kodu yeniden gönderildi!")
    
    def _on_resend_reset_error(self, error_msg):
        """Şifre sıfırlama kodunu yeniden gönderme hatası"""
        self._show_error(f"Kod gönderilemedi: {error_msg}")

    def _show_forgot_password_ui(self):
        """Şifremi unuttum ekranını göster"""
        self._create_forgot_password_form()

    def _toggle_mode(self):
        """Login/Register modları arasında geçiş"""
        if self.current_mode == MODE_LOGIN:
            self._create_register_form()
        else:
            self._create_login_form()

    def _back_to_login(self):
        """Giriş ekranına dön"""
        self.current_mode = MODE_LOGIN
        self.pending_email = None
        self.reset_code = None
        self.current_user = None
        self._create_login_form()

    def _show_error(self, msg):
        """Hata mesajı göster"""
        self.error_label.setText(msg)
        self.error_label.setStyleSheet(self._error_style)
        self.error_label.show()
    
    def _hide_error_message(self):
        """Hata mesajını gizle"""
        self.error_label.clear()
        self.error_label.hide()
    
    def _cleanup_threads(self):
        """Tüm aktif thread'leri temizle"""
        threads = [
            self.login_thread,
            self.register_thread,
            self.verify_thread,
            self.send_reset_thread,
            self.verify_reset_thread,
            self.reset_password_thread,
            self.resend_thread
        ]
        
        for thread in threads:
            if thread and thread.isRunning():
                thread.terminate()
                thread.wait(1000)  # 1 saniye bekle
                if thread.isRunning():
                    thread.terminate()
    
    def closeEvent(self, event: QCloseEvent):
        """Pencere kapatıldığında thread'leri temizle"""
        self._cleanup_threads()
        self.window_closed.emit()
        event.accept()
