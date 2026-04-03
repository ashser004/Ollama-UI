"""
popup.py — Reusable popup / toast notifications.
"""

from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                                QPushButton, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont

from app.theme import COLORS


class ToastNotification(QWidget):
    """Animated toast notification that auto-dismisses."""

    def __init__(self, message: str, toast_type: str = "info",
                 duration_ms: int = 4000, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(400)

        # Colors by type
        type_colors = {
            "info": COLORS.info,
            "success": COLORS.success,
            "warning": COLORS.warning,
            "error": COLORS.error,
        }
        color = type_colors.get(toast_type, COLORS.info)

        # Icons by type
        type_icons = {
            "info": "i",
            "success": "✓",
            "warning": "!",
            "error": "✕",
        }
        icon = type_icons.get(toast_type, "i")

        # Container
        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {color}44;
                border-left: 4px solid {color};
                border-radius: 10px;
                padding: 12px 16px;
            }}
        """)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 10, 12, 10)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 16px; font-weight: 800; color: {color}; background: transparent;")
        icon_label.setFixedWidth(24)
        icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {COLORS.text_primary}; font-size: 13px; background: transparent;")
        layout.addWidget(msg_label, 1)

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS.text_muted};
                border: none;
                font-size: 14px;
                border-radius: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        close_btn.clicked.connect(self._fade_out)
        layout.addWidget(close_btn)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        # Opacity effect for fade animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)

        # Auto dismiss
        QTimer.singleShot(100, self._fade_in)
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_in(self):
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    def _fade_out(self):
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.finished.connect(self.deleteLater)
        anim.start()

    def show_at(self, parent_widget: QWidget):
        """Show toast at top-right of parent."""
        if parent_widget:
            parent_geo = parent_widget.geometry()
            x = parent_geo.x() + parent_geo.width() - self.width() - 20
            y = parent_geo.y() + 60
            self.move(x, y)
        self.show()


class ConfirmDialog(QWidget):
    """Modal confirmation popup."""

    def __init__(self, title: str, message: str, on_confirm=None,
                 on_cancel=None, confirm_text="Confirm", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 200)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;")
        layout.addWidget(msg_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.error};
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #ef4444;
            }}
        """)
        confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _confirm(self):
        if self._on_confirm:
            self._on_confirm()
        self.close()
        self.deleteLater()

    def _cancel(self):
        if self._on_cancel:
            self._on_cancel()
        self.close()
        self.deleteLater()

    def show_centered(self, parent_widget: QWidget = None):
        """Show popup centered on parent."""
        if parent_widget:
            geo = parent_widget.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        self.show()
