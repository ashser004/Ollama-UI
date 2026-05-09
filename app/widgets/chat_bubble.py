# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
chat_bubble.py — Individual chat message bubble.
"""

import random
import base64
import os

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QCursor, QPixmap, QImage

from app.theme import COLORS

# ── Loading phrase pools ──────────────────────────────────────────────────────
_TEXT_PHRASES = [
    "Thinking",
    "Analyzing context",
    "Generating response",
    "Processing request",
    "Crafting reply",
    "Reasoning through this",
    "Working on it",
]

_IMAGE_PHRASES = [
    "Processing image",
    "Analyzing pixels",
    "Extracting visual data",
    "Looking closely",
    "Identifying objects",
    "Analyzing the image",
    "Inspecting details",
]
# ─────────────────────────────────────────────────────────────────────────────


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
        self._status_label: QLabel | None = None
        self._copy_btn: QPushButton | None = None

        # Timers (created lazily, only for assistant bubbles)
        self._loading_timer: QTimer | None = None
        self._copy_reset_timer: QTimer | None = None
        self._dot_count = 0
        self._current_phrase = ""

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
            for img_data in images[:5]:  # match the chat attachment limit
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

        # Bottom row: model label + status text + copy button
        bottom = QHBoxLayout()
        self._bottom_layout = bottom

        if not is_user and model:
            self.set_model_label(model)

        # Status / loading label (assistant only, hidden by default)
        if not is_user:
            status_label = QLabel("")
            status_label.setVisible(False)
            status_label.setStyleSheet(f"""
                font-size: 11px;
                color: {COLORS.accent_primary};
                background: transparent;
                padding: 0px;
            """)
            bottom.addWidget(status_label)
            self._status_label = status_label

        bottom.addStretch()

        # Copy button
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
        copy_btn.clicked.connect(self._on_copy_clicked)
        bottom.addWidget(copy_btn)
        self._copy_btn = copy_btn

        bubble_layout.addLayout(bottom)

        layout.addWidget(bubble)

        if not is_user:
            layout.addStretch()

    # ── Copy button logic ─────────────────────────────────────────────────────

    def _on_copy_clicked(self):
        """Emit copy signal and show 3-second 'Copied!' feedback."""
        self.copy_requested.emit(self._content)

        if self._copy_btn is None:
            return

        self._copy_btn.setText("Copied!")
        self._copy_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS.success};
                border: none;
                font-size: 11px;
                padding: 2px 8px;
                border-radius: 6px;
            }}
        """)

        if self._copy_reset_timer is None:
            self._copy_reset_timer = QTimer(self)
            self._copy_reset_timer.setSingleShot(True)
            self._copy_reset_timer.timeout.connect(self._reset_copy_btn)

        self._copy_reset_timer.start(3000)

    def _reset_copy_btn(self):
        """Restore Copy button to its default state."""
        if self._copy_btn is None:
            return
        self._copy_btn.setText("Copy")
        self._copy_btn.setStyleSheet(f"""
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

    # ── Loading animation logic ────────────────────────────────────────────────

    def start_loading(self, has_images: bool = False):
        """Start the animated loading status text. Call before streaming begins."""
        if self._is_user or self._status_label is None:
            return

        pool = _IMAGE_PHRASES if has_images else _TEXT_PHRASES
        self._current_phrase = random.choice(pool)
        self._dot_count = 0

        self._status_label.setText(self._current_phrase + ".")
        self._status_label.setVisible(True)

        if self._loading_timer is None:
            self._loading_timer = QTimer(self)
            self._loading_timer.timeout.connect(self._tick_loading)

        self._loading_timer.start(400)

    def _tick_loading(self):
        """Cycle through dot animation and randomly rotate phrases."""
        if self._status_label is None:
            return

        self._dot_count = (self._dot_count + 1) % 3

        # Every full dot cycle (3 ticks), pick a new phrase for variety
        if self._dot_count == 0:
            pool = _IMAGE_PHRASES if "pixel" in self._current_phrase.lower() \
                                   or "image" in self._current_phrase.lower() \
                                   or "visual" in self._current_phrase.lower() \
                                   or "object" in self._current_phrase.lower() \
                                   or "detail" in self._current_phrase.lower() \
                                  else _TEXT_PHRASES
            self._current_phrase = random.choice(pool)

        dots = "." * (self._dot_count + 1)
        self._status_label.setText(self._current_phrase + dots)

    def stop_loading(self):
        """Stop the loading animation and hide the status label."""
        if self._loading_timer is not None:
            self._loading_timer.stop()
        if self._status_label is not None:
            self._status_label.setVisible(False)
            self._status_label.setText("")

    # ── Content helpers ───────────────────────────────────────────────────────

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
