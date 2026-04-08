"""
chat_bubble.py — Individual chat message bubble.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QSizePolicy)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QCursor, QPixmap, QImage
import base64
import os

from app.theme import COLORS


class ChatBubble(QWidget):
    """A single chat message bubble."""

    copy_requested = Signal(str)

    def __init__(self, role: str, content: str, model: str = None,
                 images: list[str] = None, parent=None):
        super().__init__(parent)
        self._content = content
        self._role = role
        self._is_user = role == "user"
        self._content_label: QLabel | None = None
        self._model_label: QLabel | None = None
        self._bottom_layout: QHBoxLayout | None = None

        is_user = self._is_user

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 4, 0, 4)

        if is_user:
            layout.addStretch()

        # Bubble container
        bubble = QWidget()
        bubble.setMaximumWidth(620)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)

        if is_user:
            bg = COLORS.chat_user_bg
            border = f"{COLORS.accent_primary}30"
        else:
            bg = COLORS.chat_assistant_bg
            border = COLORS.border_default

        bubble.setStyleSheet(f"""
            QWidget {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 14px;
            }}
        """)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 10)
        bubble_layout.setSpacing(6)

        # Images (for messages with image attachments)
        if images:
            for img_data in images[:3]:  # max 3 images
                try:
                    if os.path.isfile(img_data):
                        pixmap = QPixmap(img_data)
                    else:
                        # base64 decode
                        raw = base64.b64decode(img_data)
                        qimg = QImage()
                        qimg.loadFromData(raw)
                        pixmap = QPixmap.fromImage(qimg)

                    if not pixmap.isNull():
                        pixmap = pixmap.scaledToWidth(
                            min(400, pixmap.width()),
                            Qt.SmoothTransformation
                        )
                        img_label = QLabel()
                        img_label.setPixmap(pixmap)
                        img_label.setStyleSheet("border-radius: 8px; background: transparent;")
                        bubble_layout.addWidget(img_label)
                except Exception:
                    pass

        # Content
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setTextFormat(Qt.PlainText)
        content_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        content_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        content_label.setStyleSheet(f"""
            color: {COLORS.text_primary};
            font-size: 13px;
            line-height: 1.5;
            background: transparent;
            padding: 0px;
        """)
        bubble_layout.addWidget(content_label)
        self._content_label = content_label

        # Bottom row: model label + copy button
        bottom = QHBoxLayout()
        self._bottom_layout = bottom

        if not is_user and model:
            self.set_model_label(model)

        bottom.addStretch()

        copy_btn = QPushButton("Copy")
        copy_btn.setCursor(QCursor(Qt.PointingHandCursor))
        copy_btn.setFixedHeight(24)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS.text_muted};
                border: none;
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        copy_btn.clicked.connect(lambda: self.copy_requested.emit(self._content))
        bottom.addWidget(copy_btn)

        bubble_layout.addLayout(bottom)

        layout.addWidget(bubble)

        if not is_user:
            layout.addStretch()

    def set_content(self, content: str, show_cursor: bool = False):
        """Update the bubble text and keep copy content in sync."""
        self._content = content
        if self._content_label:
            self._content_label.setText(content + (" ▊" if show_cursor else ""))

    def set_model_label(self, model: str):
        """Show or update the assistant model label in the footer row."""
        if self._is_user or not model:
            return

        if self._model_label is None:
            self._model_label = QLabel()
            self._model_label.setStyleSheet(f"""
                font-size: 10px; font-weight: 500;
                color: {COLORS.text_muted}; background: transparent;
                padding: 0px;
            """)

            if self._bottom_layout is not None:
                self._bottom_layout.insertWidget(0, self._model_label)

        self._model_label.setText(model)
        self._model_label.setVisible(True)
