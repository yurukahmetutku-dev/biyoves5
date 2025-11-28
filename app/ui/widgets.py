#!/usr/bin/env python3

from typing import Optional

from PySide6.QtWidgets import (
    QPushButton,
    QFrame,
    QVBoxLayout,
    QLabel,
    QSizePolicy,
    QWidget,
    QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from app.config import modern_theme


class ModernButton(QPushButton):
    """Modern buton widget'ı"""

    VARIANTS = {
        "primary": {
            "bg": modern_theme.PRIMARY,
            "hover": modern_theme.PRIMARY_HOVER,
            "text": "#ffffff"
        },
        "success": {
            "bg": modern_theme.SUCCESS,
            "hover": modern_theme.SUCCESS_HOVER,
            "text": "#ffffff"
        },
        "danger": {
            "bg": modern_theme.DANGER,
            "hover": modern_theme.DANGER_HOVER,
            "text": "#ffffff"
        },
        "secondary": {
            "bg": modern_theme.BACKGROUND_SECONDARY,
            "hover": modern_theme.BORDER_LIGHT,
            "text": modern_theme.TEXT_PRIMARY,
            "border": modern_theme.BORDER
        },
        "info": {
            "bg": modern_theme.INFO,
            "hover": modern_theme.PRIMARY_HOVER,
            "text": "#ffffff"
        }
    }

    def __init__(self, text="", variant="primary", size="md", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.size = size

        height_map = {
            "sm": modern_theme.BUTTON_HEIGHT_SM,
            "md": modern_theme.BUTTON_HEIGHT_MD,
            "lg": modern_theme.BUTTON_HEIGHT_LG
        }
        height = height_map.get(size, modern_theme.BUTTON_HEIGHT_MD)
        self.setMinimumHeight(height)
        self.setMinimumWidth(modern_theme.BUTTON_MIN_WIDTH)
        button_policy = QSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Preferred)
        self.setSizePolicy(button_policy)

        variant_styles = self.VARIANTS.get(variant, self.VARIANTS["primary"])
        border_style = (
            f"border: 1px solid {variant_styles.get('border', variant_styles['bg'])};"
            if variant == "secondary"
            else ""
        )

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {variant_styles['bg']};
                color: {variant_styles['text']};
                border: none;
                border-radius: {modern_theme.RADIUS_MD}px;
                font-size: {modern_theme.FONT_SIZE_BODY}px;
                font-weight: 500;
                padding: 0 {modern_theme.SPACING_LG}px;
                {border_style}
            }}
            QPushButton:hover {{
                background-color: {variant_styles['hover']};
            }}
            QPushButton:pressed {{
                background-color: {variant_styles['hover']};
            }}
            QPushButton:disabled {{
                background-color: #e0e0e0;
                color: #9e9e9e;
            }}
        """)


class ModernCard(QFrame):
    """Modern kart widget'ı"""

    def __init__(self, title="", subtitle="", parent=None, show_frame=True, background_color=None):
        super().__init__(parent)
        self.show_frame = show_frame
        self.setFrameShape(QFrame.StyledPanel if show_frame else QFrame.NoFrame)
        border_style = (
            f"border: {modern_theme.CARD_BORDER_WIDTH}px solid {modern_theme.CARD_BORDER_COLOR};"
            if show_frame
            else "border: none;"
        )
        radius = modern_theme.RADIUS_LG if show_frame else 0
        if background_color is not None:
            background = background_color
        else:
            background = modern_theme.CARD_BACKGROUND if show_frame else "transparent"
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {background};
                {border_style}
                border-radius: {radius}px;
            }}
        """)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setObjectName("cardMainLayout")
        self.main_layout.setContentsMargins(
            modern_theme.CARD_PADDING, modern_theme.CARD_PADDING,
            modern_theme.CARD_PADDING, modern_theme.CARD_PADDING
        )
        self.main_layout.setSpacing(modern_theme.SPACING_MD)

        if title or subtitle:
            header_layout = QVBoxLayout()
            header_layout.setObjectName("cardHeaderLayout")
            header_layout.setSpacing(modern_theme.SPACING_XS)

            if title:
                title_label = QLabel(title)
                title_font = QFont()
                title_font.setPointSize(16)
                title_font.setBold(True)
                title_label.setFont(title_font)
                title_label.setStyleSheet(f"color: {modern_theme.TEXT_PRIMARY};")
                header_layout.addWidget(title_label)

            if subtitle:
                subtitle_label = QLabel(subtitle)
                subtitle_label.setFont(QFont("", modern_theme.FONT_SIZE_BODY_SMALL))
                subtitle_label.setStyleSheet(f"color: {modern_theme.TEXT_SECONDARY};")
                header_layout.addWidget(subtitle_label)

            self.main_layout.addLayout(header_layout)
            self.main_layout.addSpacing(modern_theme.SPACING_MD)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("cardContentWidget")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setObjectName("cardContentLayout")
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(modern_theme.SPACING_MD)
        self.main_layout.addWidget(self.content_widget)

    def get_content_layout(self):
        return self.content_layout


class ChoiceButton(QPushButton):
    """Sade ve modern seçim butonu"""

    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(modern_theme.BUTTON_HEIGHT_LG)
        self._apply_style()

    def _apply_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {modern_theme.BACKGROUND_SECONDARY};
                color: {modern_theme.TEXT_PRIMARY};
                border: 1px solid {modern_theme.BORDER_LIGHT};
                border-radius: {modern_theme.RADIUS_MD}px;
                text-align: left;
                padding: {modern_theme.SPACING_MD}px;
                font-size: {modern_theme.FONT_SIZE_BODY_SMALL}px;
            }}
            QPushButton:hover {{
                background-color: {modern_theme.CARD_BACKGROUND};
            }}
            QPushButton:checked {{
                border: 2px solid {modern_theme.PRIMARY};
                background-color: {modern_theme.BACKGROUND};
                font-weight: 600;
            }}
            QPushButton:disabled {{
                color: {modern_theme.TEXT_TERTIARY};
                border-color: {modern_theme.BORDER_LIGHT};
            }}
        """)


class PreviewLabel(QLabel):
    """Önizleme görüntüsünü boyuta göre ölçekleyen etiket."""

    def __init__(self, placeholder_text="", parent=None):
        super().__init__(parent)
        self.placeholder_text = placeholder_text
        self._pixmap: Optional[QPixmap] = None
        self.setAlignment(Qt.AlignCenter)
        if placeholder_text:
            self.setText(placeholder_text)

    def set_image_from_path(self, file_path: str) -> bool:
        pixmap = QPixmap(file_path)
        if pixmap.isNull():
            self.clear_image("Görsel yüklenemedi")
            return False
        self._pixmap = pixmap
        self._update_scaled_pixmap()
        self.setText("")
        return True

    def clear_image(self, placeholder: str | None = None):
        self._pixmap = None
        self.setPixmap(QPixmap())
        self.setText(placeholder or self.placeholder_text)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._pixmap is not None and not self._pixmap.isNull():
            self._update_scaled_pixmap()

    def _update_scaled_pixmap(self):
        if not self._pixmap:
            return
        if self.width() <= 0 or self.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.setPixmap(scaled)


def show_styled_message(
    parent,
    title: str,
    text: str,
    icon: QMessageBox.Icon = QMessageBox.Information,
    buttons: QMessageBox.StandardButtons = QMessageBox.Ok,
):
    """Tek tip tema ile mesaj kutusu gösterir"""

    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)
    box.setStandardButtons(buttons)
    box.setStyleSheet(f"""
        QMessageBox {{
            background-color: {modern_theme.BACKGROUND};
            color: {modern_theme.TEXT_PRIMARY};
        }}
        QLabel {{
            color: {modern_theme.TEXT_PRIMARY};
            font-size: {modern_theme.FONT_SIZE_BODY}px;
        }}
        QPushButton {{
            background-color: {modern_theme.PRIMARY};
            color: #ffffff;
            border: none;
            border-radius: {modern_theme.RADIUS_MD}px;
            padding: 6px 16px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {modern_theme.PRIMARY_HOVER};
        }}
        QPushButton:disabled {{
            background-color: #d0d0d0;
            color: {modern_theme.TEXT_SECONDARY};
        }}
    """)
    return box.exec()
