# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
logs_page.py — Logs page wrapper.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from app.widgets.logs_view import LogsView


class LogsPage(QWidget):
    """Wraps the LogsView widget as a page."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._logs = LogsView()
        layout.addWidget(self._logs)

    def refresh(self):
        self._logs.refresh()
