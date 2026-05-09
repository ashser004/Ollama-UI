# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
setup_page.py — First-launch setup flow.

Step 1: Pick storage directory
Step 2: Install Ollama
Then transitions to home.
"""

from PySide6.QtWidgets import QWidget, QStackedWidget, QVBoxLayout
from PySide6.QtCore import Signal, Slot

from app.widgets.storage_dialog import StorageDialog
from app.widgets.install_ollama import InstallOllamaWidget
from app.ollama.manager import OllamaManager
from app import config


class SetupPage(QWidget):
    """First-launch setup wizard."""

    setup_complete = Signal()

    def __init__(self, ollama_manager: OllamaManager, parent=None):
        super().__init__(parent)
        self._manager = ollama_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # Step 1: Storage picker
        self._storage = StorageDialog()
        self._storage.directory_selected.connect(self._on_dir_selected)
        self._stack.addWidget(self._storage)

        # Step 2: Ollama installer
        self._installer = InstallOllamaWidget(self._manager)
        self._installer.install_complete.connect(self._on_install_complete)
        self._stack.addWidget(self._installer)

        layout.addWidget(self._stack)

        # If already has a dir but no Ollama, skip to step 2
        if not config.is_first_launch() and not config.is_ollama_installed():
            self._stack.setCurrentWidget(self._installer)

    @Slot(str)
    def _on_dir_selected(self, aiui_path: str):
        """Storage directory selected — move to Ollama install."""
        self._stack.setCurrentWidget(self._installer)

    @Slot()
    def _on_install_complete(self):
        """Ollama installed — emit setup complete."""
        self.setup_complete.emit()
