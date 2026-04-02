"""
logs_view.py — Error logs viewer widget.
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QScrollArea)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from app.theme import COLORS
from app import config


class LogsView(QWidget):
    """View and manage application error logs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()

        title = QLabel("Logs")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        header.addWidget(title)

        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.setFixedHeight(32)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        header.addWidget(refresh_btn)

        # Clear button
        clear_btn = QPushButton("🗑 Clear Logs")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setFixedHeight(32)
        clear_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                color: {COLORS.error};
                border: 1px solid {COLORS.error}44;
                border-radius: 8px;
                padding: 4px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.error}18;
            }}
        """)
        clear_btn.clicked.connect(self._clear_logs)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        subtitle = QLabel("Installation errors, server crashes, and other issues are logged here")
        subtitle.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;")
        layout.addWidget(subtitle)

        # Log content
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Consolas", 11))
        self._log_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS.bg_darkest};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 12px;
                padding: 16px;
                font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;
            }}
        """)
        layout.addWidget(self._log_view, 1)

    def refresh(self):
        """Load logs from file."""
        log_path = config.get_error_log_path()
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    content = f.read()
                if content.strip():
                    self._log_view.setPlainText(content)
                else:
                    self._log_view.setPlainText("No errors logged. Everything is running smoothly! 🎉")
            except IOError:
                self._log_view.setPlainText("Could not read log file.")
        else:
            self._log_view.setPlainText("No log file found. Logs will appear here when errors occur.")

    def _clear_logs(self):
        """Clear the log file."""
        log_path = config.get_error_log_path()
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except IOError:
                pass
        self._log_view.setPlainText("Logs cleared.")
