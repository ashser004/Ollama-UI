"""
image_preview.py — Image attachment thumbnails and overlay viewer.
"""

import os

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QPixmap

from app.theme import COLORS


def _load_scaled_pixmap(image_path: str, max_width: int, max_height: int) -> QPixmap:
    pixmap = QPixmap(image_path)
    if pixmap.isNull():
        return QPixmap()
    return pixmap.scaled(
        max_width,
        max_height,
        Qt.KeepAspectRatio,
        Qt.SmoothTransformation,
    )


class AttachmentThumbnail(QWidget):
    """Clickable attachment preview card with order badge and remove button."""

    clicked = Signal(str)
    remove_requested = Signal(int)

    def __init__(self, image_path: str, index: int, parent=None):
        super().__init__(parent)
        self._image_path = image_path
        self._index = index
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedSize(114, 132)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
            QWidget:hover {{
                border-color: {COLORS.accent_primary};
                background-color: {COLORS.bg_hover};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        badge = QLabel(str(index + 1))
        badge.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        badge.setAlignment(Qt.AlignCenter)
        badge.setFixedSize(26, 18)
        badge.setStyleSheet(f"""
            QLabel {{
                color: {COLORS.text_on_accent};
                background-color: {COLORS.accent_primary};
                border-radius: 9px;
                font-size: 11px;
                font-weight: 700;
            }}
        """)
        top_row.addWidget(badge)
        top_row.addStretch()

        remove_btn = QPushButton("×")
        remove_btn.setCursor(QCursor(Qt.PointingHandCursor))
        remove_btn.setFixedSize(20, 20)
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 10px;
                font-size: 12px;
                font-weight: 700;
                padding: 0px;
            }}
            QPushButton:hover {{
                background: {COLORS.error};
                color: {COLORS.text_on_accent};
                border-color: {COLORS.error};
            }}
        """)
        remove_btn.clicked.connect(lambda: self.remove_requested.emit(self._index))
        top_row.addWidget(remove_btn)
        layout.addLayout(top_row)

        thumb = QLabel()
        thumb.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        thumb.setAlignment(Qt.AlignCenter)
        thumb.setFixedSize(94, 86)
        thumb.setStyleSheet(f"""
            QLabel {{
                background: {COLORS.bg_dark};
                border-radius: 10px;
                color: {COLORS.text_muted};
                font-size: 11px;
            }}
        """)

        if os.path.isfile(image_path):
            pixmap = _load_scaled_pixmap(image_path, 94, 86)
            if not pixmap.isNull():
                thumb.setPixmap(pixmap)
            else:
                thumb.setText("Preview\nunavailable")
        else:
            thumb.setText("Missing\nfile")

        layout.addWidget(thumb, alignment=Qt.AlignCenter)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._image_path)
        super().mousePressEvent(event)


class AttachmentPreviewStrip(QWidget):
    """Horizontal preview strip for queued image attachments."""

    open_requested = Signal(str)
    remove_requested = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setStyleSheet("background: transparent;")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(20, 6, 20, 6)
        self._layout.setSpacing(10)
        self._layout.addStretch(1)
        self.setVisible(False)

    def set_attachments(self, image_paths: list[str]):
        """Replace the preview cards with the provided ordered paths."""
        self._clear_items()

        if not image_paths:
            self.setVisible(False)
            return

        for index, image_path in enumerate(image_paths):
            item = AttachmentThumbnail(image_path, index)
            item.clicked.connect(self.open_requested.emit)
            item.remove_requested.connect(self.remove_requested.emit)
            self._layout.insertWidget(self._layout.count() - 1, item)

        self.setVisible(True)

    def _clear_items(self):
        while self._layout.count() > 1:
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


class ImagePreviewOverlay(QDialog):
    """Simple modal overlay for viewing a selected image."""

    def __init__(self, image_path: str, title: str = "", parent=None):
        super().__init__(parent)
        self._image_path = image_path
        self._title_text = title or os.path.basename(image_path)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint)
        self.setModal(True)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("QDialog { background-color: rgba(5, 10, 20, 210); }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignCenter)

        self._title = QLabel(self._title_text)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet(f"""
            QLabel {{
                color: {COLORS.text_secondary};
                background: transparent;
                font-size: 12px;
                font-weight: 600;
            }}
        """)
        layout.addWidget(self._title)

        self._image_label = QLabel()
        self._image_label.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self._image_label.setAlignment(Qt.AlignCenter)
        self._image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
                color: {COLORS.text_muted};
                padding: 16px;
            }}
        """)
        layout.addWidget(self._image_label, alignment=Qt.AlignCenter)

    def show_for_parent(self, parent_widget):
        """Resize and show the overlay on top of a parent widget."""
        if parent_widget:
            self.setGeometry(parent_widget.geometry())
        else:
            screen = QApplication.primaryScreen()
            if screen:
                self.setGeometry(screen.availableGeometry())

        self._update_pixmap()
        self.show()
        self.raise_()
        self.activateWindow()

    def _update_pixmap(self):
        pixmap = QPixmap(self._image_path)
        if pixmap.isNull():
            self._image_label.setPixmap(QPixmap())
            self._image_label.setText("Unable to load image")
            return

        max_width = max(320, int(self.width() * 0.82))
        max_height = max(240, int(self.height() * 0.82))
        scaled = pixmap.scaled(max_width, max_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._image_label.setPixmap(scaled)
        self._image_label.setText("")

    def mousePressEvent(self, event):
        self.close()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.deleteLater()