# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
discover_page.py — Model discovery page wrapper.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from app.widgets.model_discovery import ModelDiscovery
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog
from app.services.system_monitor import SystemMonitor


class DiscoverPage(QWidget):
    """Wraps the ModelDiscovery widget as a page."""

    install_requested = Signal(dict)
    open_chat_requested = Signal(dict)
    delete_requested = Signal(dict)
    pause_requested = Signal(dict)

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog,
                 monitor: SystemMonitor, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._discovery = ModelDiscovery(catalog, api, monitor)
        self._discovery.install_requested.connect(self.install_requested.emit)
        self._discovery.open_chat_requested.connect(self.open_chat_requested.emit)
        self._discovery.delete_requested.connect(self.delete_requested.emit)
        self._discovery.pause_requested.connect(self.pause_requested.emit)

        layout.addWidget(self._discovery)

    def set_download_states(self, states: dict):
        self._discovery.set_download_states(states)

    def set_active_downloads(self, active_tags: set[str]):
        self._discovery.set_active_downloads(active_tags)

    def refresh(self):
        self._discovery.refresh()

    def get_card_by_tag(self, tag):
        return self._discovery.get_card_by_tag(tag)
