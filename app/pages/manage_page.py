# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
manage_page.py — Model management page wrapper.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from app.widgets.model_manager import ModelManager
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog


class ManagePage(QWidget):
    """Wraps the ModelManager widget as a page."""

    open_chat_requested = Signal(str)
    model_deleted = Signal(str)
    cache_cleared = Signal()

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._manager = ModelManager(api, catalog)
        self._manager.open_chat_requested.connect(self.open_chat_requested.emit)
        self._manager.model_deleted.connect(self.model_deleted.emit)
        self._manager.cache_cleared.connect(self.cache_cleared.emit)
        layout.addWidget(self._manager)

    def refresh(self):
        self._manager.refresh()
