#!/usr/bin/env python3

import os
import sys
import json
from pathlib import Path

from PySide6.QtWidgets import QApplication
import firebase_admin
from firebase_admin import auth as firebase_auth

from app.ui.login_window import LoginWindow
from app.ui.main_window import MainWindow
from app.config import firebase_manager


def initialize_firebase():
    """Firebase SDK'yi tek seferlik başlat"""
    if os.getenv("BIYOVES_SKIP_FIREBASE"):
        return
    if firebase_admin._apps:
        return
    firebase_manager.initialize()


class BiyoVesApp:
    """Ana uygulama sınıfı"""

    SESSION_FILE = Path(__file__).resolve().parent / "session.json"

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("BiyoVes")

        self.login_window = None
        self.main_window = None

        self._ensure_login_window()
        session_user = self._load_session()
        if session_user:
            self._launch_main(session_user)
        else:
            self.login_window.show()

    def _ensure_login_window(self):
        if self.login_window is None:
            self.login_window = LoginWindow()
            self.login_window.login_success.connect(self._on_login_success)
            self.login_window.window_closed.connect(self._exit_application)

    def _on_login_success(self, user):
        """Giriş başarılı olduğunda ana ekrana geç"""
        self._save_session(user)
        self._launch_main(user)

    def _launch_main(self, user):
        if self.login_window:
            self.login_window.hide()
        if self.main_window:
            self.main_window.close_signal.disconnect(self._on_main_window_closed)
            self.main_window.logout_signal.disconnect(self._on_logout_requested)
            self.main_window.close()
        self.main_window = MainWindow(user)
        self.main_window.close_signal.connect(self._on_main_window_closed)
        self.main_window.logout_signal.connect(self._on_logout_requested)
        self.main_window.show()

    def _on_main_window_closed(self):
        """Ana ekran kapatıldığında uygulamayı sonlandır"""
        self.main_window = None
        self._exit_application()

    def _on_logout_requested(self):
        self._clear_session()
        self._ensure_login_window()
        self.login_window.show()

    def _exit_application(self):
        if self.main_window:
            self.main_window.close_signal.disconnect(self._on_main_window_closed)
            self.main_window.logout_signal.disconnect(self._on_logout_requested)
            self.main_window = None
        if self.login_window:
            try:
                self.login_window.window_closed.disconnect(self._exit_application)
            except Exception:
                pass
            self.login_window = None
        self.app.quit()

    def run(self):
        """Uygulamayı başlat"""
        if not self.main_window:
            self._ensure_login_window()
            self.login_window.show()
        sys.exit(self.app.exec())

    def _save_session(self, user):
        uid = getattr(user, "uid", None)
        if not uid:
            return
        data = {
            "uid": uid,
            "email": getattr(user, "email", "")
        }
        try:
            with open(self.SESSION_FILE, "w", encoding="utf-8") as session_file:
                json.dump(data, session_file)
        except Exception as exc:
            print(f"Oturum kaydedilemedi: {exc}")

    def _load_session(self):
        if not self.SESSION_FILE.exists():
            return None
        try:
            with open(self.SESSION_FILE, "r", encoding="utf-8") as session_file:
                data = json.load(session_file)
            uid = data.get("uid")
            if not uid:
                return None
            user = firebase_auth.get_user(uid)
            return user
        except Exception as exc:
            print(f"Oturum yüklenemedi: {exc}")
            self._clear_session()
            return None

    def _clear_session(self):
        try:
            if self.SESSION_FILE.exists():
                self.SESSION_FILE.unlink()
        except Exception as exc:
            print(f"Oturum silinemedi: {exc}")


if __name__ == "__main__":
    try:
        initialize_firebase()
        app = BiyoVesApp()
        app.run()
    except Exception as e:
        print(f"Uygulama başlatılamadı: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
