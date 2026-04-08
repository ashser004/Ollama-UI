"""
logs_view.py — Error logs viewer widget.

Optimized with color-coded entries, search, tail-read,
auto-scroll, and entry count.
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QLineEdit)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor

from app.theme import COLORS
from app import config


# Maximum lines to load (tail-read for performance)
_MAX_LINES = 500


class LogsView(QWidget):
    """View and manage application error logs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_lines: list[str] = []  # raw log lines

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(12)

        # Header
        header = QHBoxLayout()

        title = QLabel("Logs")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        header.addWidget(title)

        self._count_label = QLabel("")
        self._count_label.setStyleSheet(f"""
            font-size: 12px; font-weight: 600;
            color: {COLORS.text_muted}; background: {COLORS.bg_surface};
            padding: 4px 12px; border-radius: 10px;
            border: 1px solid {COLORS.border_default};
        """)
        header.addWidget(self._count_label)

        header.addStretch()

        # Refresh button
        refresh_btn = QPushButton("Refresh")
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
        clear_btn = QPushButton("Clear Logs")
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

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search logs...")
        self._search.setFixedHeight(36)
        self._search.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS.bg_surface};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-radius: 10px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS.accent_primary};
            }}
        """)
        self._search.textChanged.connect(self._apply_filter)
        layout.addWidget(self._search)

        # Legend row
        legend = QHBoxLayout()
        legend.setSpacing(16)
        for label_text, color in [
            ("● Errors", COLORS.error),
            ("● Installs", COLORS.success),
            ("● Warnings", COLORS.warning),
            ("● Info", COLORS.text_muted),
        ]:
            lbl = QLabel(label_text)
            lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 600; background: transparent;")
            legend.addWidget(lbl)
        legend.addStretch()
        layout.addLayout(legend)

        # Log content
        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setFont(QFont("Cascadia Code", 10))
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
        """Load logs from file (tail-read for performance)."""
        log_path = config.get_error_log_path()
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    all_lines = f.readlines()

                # Tail-read: only keep the last N lines
                self._all_lines = all_lines[-_MAX_LINES:]

                total = len(all_lines)
                showing = len(self._all_lines)
                if total > _MAX_LINES:
                    self._count_label.setText(f"Showing {showing} of {total} entries")
                else:
                    self._count_label.setText(f"{total} entries")

                self._apply_filter()

            except IOError:
                self._log_view.setPlainText("Could not read log file.")
                self._count_label.setText("")
        else:
            self._log_view.setPlainText("No log file found. Logs will appear here when events occur.")
            self._count_label.setText("0 entries")
            self._all_lines.clear()

    def _apply_filter(self):
        """Filter and color-code log lines, then display."""
        query = self._search.text().strip().lower()
        lines = self._all_lines

        if query:
            lines = [line for line in lines if query in line.lower()]

        self._log_view.clear()
        cursor = self._log_view.textCursor()

        if not lines:
            if query:
                self._log_view.setPlainText(f'No log entries matching "{self._search.text()}"')
            elif not self._all_lines:
                self._log_view.setPlainText("No errors logged. Everything is running smoothly.")
            else:
                self._log_view.setPlainText("No matching entries.")
            return

        for line in lines:
            fmt = QTextCharFormat()
            fmt.setFontFamily("Cascadia Code, Consolas, Courier New, monospace")

            text = line.rstrip("\n")
            lower = text.lower()

            if any(kw in lower for kw in ("error", "fail", "crash", "exception", "traceback")):
                fmt.setForeground(QColor(COLORS.error))
                fmt.setFontWeight(QFont.Bold)
            elif "model installed" in lower:
                fmt.setForeground(QColor(COLORS.success))
                fmt.setFontWeight(QFont.Bold)
            elif any(kw in lower for kw in ("warning", "warn", "retry", "timeout")):
                fmt.setForeground(QColor(COLORS.warning))
            elif any(kw in lower for kw in ("started safely", "stopped safely")):
                fmt.setForeground(QColor("#64748b"))  # muted slate for routine events
            else:
                fmt.setForeground(QColor(COLORS.text_secondary))

            cursor.movePosition(QTextCursor.End)
            cursor.insertText(text + "\n", fmt)

        # Auto-scroll to bottom
        self._log_view.moveCursor(QTextCursor.End)
        self._log_view.ensureCursorVisible()

    def _clear_logs(self):
        """Clear the log file."""
        log_path = config.get_error_log_path()
        if log_path and os.path.exists(log_path):
            try:
                with open(log_path, "w", encoding="utf-8") as f:
                    f.write("")
            except IOError:
                pass
        self._all_lines.clear()
        self._log_view.setPlainText("Logs cleared.")
        self._count_label.setText("0 entries")
