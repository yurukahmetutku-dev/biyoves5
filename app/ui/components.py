#!/usr/bin/env python3

"""Shared UI components."""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.config import modern_theme


class WelcomeInfo(QWidget):
    """Reusable welcome header with title and subtitle."""

    def __init__(self, title: str, subtitle: Optional[str] = None, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._title = title
        self._subtitle = subtitle or ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(modern_theme.SPACING_SM)

        self.title_label = QLabel(self._title)
        title_font = QFont()
        title_font.setPointSize(modern_theme.FONT_SIZE_DISPLAY)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet(f"color: {modern_theme.PRIMARY};")
        layout.addWidget(self.title_label)

        self.welcome_label = QLabel(self._subtitle)
        welcome_font = QFont()
        welcome_font.setPointSize(modern_theme.FONT_SIZE_SUBHEADING)
        self.welcome_label.setFont(welcome_font)
        self.welcome_label.setAlignment(Qt.AlignCenter)
        self.welcome_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
        layout.addWidget(self.welcome_label)

    def set_welcome_text(self, text: str) -> None:
        self.welcome_label.setText(text)
