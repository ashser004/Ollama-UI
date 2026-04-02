"""
install_ollama.py — Ollama installation widget with progress.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel,
                                QPushButton, QProgressBar)
from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtGui import QFont

from app.theme import COLORS, accent_button_style
from app.ollama.manager import OllamaManager


class _InstallWorker(QThread):
    """Run Ollama download/install in a thread."""
    progress = Signal(int, int)
    extract = Signal(int, int)
    status = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, manager: OllamaManager, parent=None):
        super().__init__(parent)
        self.manager = manager

    def run(self):
        # Connect manager signals to our forwarding signals
        self.manager.download_progress.connect(self.progress.emit)
        self.manager.extract_progress.connect(self.extract.emit)
        self.manager.install_progress.connect(self.status.emit)
        self.manager.download_finished.connect(self.finished_signal.emit)
        self.manager.download_and_install()


class InstallOllamaWidget(QWidget):
    """Widget for downloading and installing Ollama."""

    install_complete = Signal()

    def __init__(self, ollama_manager: OllamaManager, parent=None):
        super().__init__(parent)
        self._manager = ollama_manager
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Center card
        card = QWidget()
        card.setFixedSize(480, 360)
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 20px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 32, 40, 32)
        card_layout.setSpacing(12)

        # Icon
        icon = QLabel("⚡")
        icon.setFont(QFont("Segoe UI Emoji", 36))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent;")
        card_layout.addWidget(icon)

        # Title
        title = QLabel("Install Ollama")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 20px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        card_layout.addWidget(title)

        # Description
        desc = QLabel("Ollama powers the AI models. We'll download and set it up\nautomatically — no manual steps needed.")
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(12)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(14)
        self._progress.setRange(0, 100)
        card_layout.addWidget(self._progress)

        # Status label
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignCenter)
        self._status.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px; background: transparent;")
        card_layout.addWidget(self._status)

        card_layout.addSpacing(8)

        # Install button
        self._install_btn = QPushButton("Install Ollama")
        self._install_btn.setCursor(Qt.PointingHandCursor)
        self._install_btn.setFixedHeight(44)
        self._install_btn.setStyleSheet(accent_button_style())
        self._install_btn.clicked.connect(self._start_install)
        card_layout.addWidget(self._install_btn)

        # Retry button (hidden initially)
        self._retry_btn = QPushButton("Retry Installation")
        self._retry_btn.setCursor(Qt.PointingHandCursor)
        self._retry_btn.setFixedHeight(44)
        self._retry_btn.setVisible(False)
        self._retry_btn.setStyleSheet(accent_button_style())
        self._retry_btn.clicked.connect(self._start_install)
        card_layout.addWidget(self._retry_btn)

        # Do-not-close warning (hidden until download starts)
        self._warning_label = QLabel("⚠️  Please do not close the app while downloading")
        self._warning_label.setAlignment(Qt.AlignCenter)
        self._warning_label.setVisible(False)
        self._warning_label.setStyleSheet(f"""
            color: {COLORS.warning};
            font-size: 11px;
            font-weight: 600;
            background: {COLORS.warning}12;
            border: 1px solid {COLORS.warning}30;
            border-radius: 8px;
            padding: 6px 12px;
        """)
        card_layout.addWidget(self._warning_label)

        layout.addWidget(card, alignment=Qt.AlignCenter)

    def _start_install(self):
        """Start the installation process."""
        self._install_btn.setVisible(False)
        self._retry_btn.setVisible(False)
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status.setText("Starting...")
        self._status.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px; background: transparent;")
        self._warning_label.setVisible(True)

        self._worker = _InstallWorker(self._manager, self)
        self._worker.progress.connect(self._on_progress)
        self._worker.extract.connect(self._on_extract_progress)
        self._worker.status.connect(self._on_status)
        self._worker.finished_signal.connect(self._on_finished)
        self._worker.start()

    @Slot(int, int)
    def _on_extract_progress(self, current: int, total: int):
        """Update progress bar during extraction."""
        if total > 0:
            pct = int((current / total) * 100)
            self._progress.setValue(pct)

    @Slot(int, int)
    def _on_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self._progress.setValue(pct)
            mb_down = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._status.setText(f"Downloading... {mb_down:.1f} / {mb_total:.1f} MB ({pct}%)")

    @Slot(str)
    def _on_status(self, text: str):
        self._status.setText(text)

    @Slot(bool, str)
    def _on_finished(self, success: bool, message: str):
        self._progress.setVisible(False)
        self._warning_label.setVisible(False)
        if success:
            self._status.setText("✅ " + message)
            self._status.setStyleSheet(f"color: {COLORS.success}; font-size: 13px; background: transparent; font-weight: 600;")
            self.install_complete.emit()
        else:
            self._status.setText("❌ " + message)
            self._status.setStyleSheet(f"color: {COLORS.error}; font-size: 12px; background: transparent;")
            self._retry_btn.setVisible(True)
