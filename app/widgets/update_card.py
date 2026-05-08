"""
update_card.py — Widget for checking and downloading app updates.
"""

import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QCursor

from app.theme import COLORS
from app import config
from app.services.update_manager import UpdateCheckerWorker, UpdateDownloaderWorker

class UpdateCard(QWidget):
    """Card interface for the update checking system."""
    
    # Signals for Toast notifications
    toast_requested = Signal(str, str) # message, type

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # State variables
        self._latest_version = None
        self._download_url = None
        self._downloaded_exe_path = None
        self._checker_worker = None
        self._downloader_worker = None
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Main wrapper to match the About card width
        wrapper = QWidget()
        wrapper.setFixedWidth(460)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(16)

        # Header Title
        title = QLabel("Updates")
        title.setStyleSheet(f"font-size: 22px; font-weight: 800; color: {COLORS.text_primary};")
        wrapper_layout.addWidget(title)

        subtitle = QLabel("Check GitHub for the latest app release")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary};")
        wrapper_layout.addWidget(subtitle)

        # Inner Card
        inner_card = QWidget()
        inner_card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 12px;
            }}
        """)
        
        inner_layout = QVBoxLayout(inner_card)
        inner_layout.setContentsMargins(20, 20, 20, 20)
        inner_layout.setSpacing(12)

        # Version Info
        self._version_label = QLabel(f"Current version: v{config.APP_VERSION}")
        self._version_label.setStyleSheet(f"""
            font-size: 14px; font-weight: 700; color: {COLORS.text_primary}; border: none;
        """)
        inner_layout.addWidget(self._version_label)

        self._status_label = QLabel("Press Check for Updates to fetch the latest release.")
        self._status_label.setStyleSheet(f"""
            font-size: 13px; color: {COLORS.text_muted}; border: none;
        """)
        inner_layout.addWidget(self._status_label)
        
        # Progress Bar (Hidden initially)
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(8)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setVisible(False)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS.bg_dark};
                border: none;
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS.accent_primary};
                border-radius: 4px;
            }}
        """)
        inner_layout.addWidget(self._progress_bar)

        # Main Action Button
        self._action_btn = QPushButton("Check for Updates")
        self._action_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._action_btn.setFixedHeight(40)
        self._action_btn.setStyleSheet(self._get_btn_style("blue"))
        self._action_btn.clicked.connect(self._handle_button_click)
        inner_layout.addWidget(self._action_btn)

        wrapper_layout.addWidget(inner_card)
        layout.addWidget(wrapper)
        
        # Timer for cooldown
        self._cooldown_timer = QTimer(self)
        self._cooldown_timer.setSingleShot(True)
        self._cooldown_timer.timeout.connect(self._on_cooldown_end)

    def _get_btn_style(self, color_theme: str) -> str:
        """Returns the stylesheet for the button based on its state."""
        base = f"""
            QPushButton {{
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:disabled {{
                background-color: {COLORS.bg_hover};
                color: {COLORS.text_muted};
            }}
        """
        if color_theme == "blue":
            return base + f"""
                QPushButton {{ background-color: {COLORS.accent_primary}; }}
                QPushButton:hover {{ background-color: {COLORS.accent_hover}; }}
            """
        elif color_theme == "green":
            return base + f"""
                QPushButton {{ background-color: {COLORS.success}; }}
                QPushButton:hover {{ background-color: #34d399; }}
            """
        return base

    def _handle_button_click(self):
        """State machine for the primary button."""
        text = self._action_btn.text()
        
        if text == "Check for Updates":
            self._start_checking()
        elif text.startswith("Download"):
            self._start_downloading()
        elif text == "Install":
            self._start_install()

    # --- Checking Phase ---
    def _start_checking(self):
        # UI state
        self._action_btn.setEnabled(False)
        self._action_btn.setText("Checking...")
        self.toast_requested.emit("Checking for updates...", "info")
        
        # Start worker
        self._checker_worker = UpdateCheckerWorker()
        self._checker_worker.update_found.connect(self._on_update_found)
        self._checker_worker.no_update_found.connect(self._on_no_update)
        self._checker_worker.error_occurred.connect(self._on_check_error)
        self._checker_worker.start()
        
        # 10s cooldown to prevent spam
        self._cooldown_timer.start(10000)

    def _on_update_found(self, latest_tag: str, download_url: str):
        self._latest_version = latest_tag
        self._download_url = download_url
        
        self._version_label.setText(f"Current: v{config.APP_VERSION}  |  Latest: {latest_tag}")
        self._status_label.setText("A new version is available!")
        self._action_btn.setText(f"Download {latest_tag}")
        self._action_btn.setEnabled(True)
        self.toast_requested.emit("New version found!", "success")

    def _on_no_update(self):
        self._status_label.setText("You are currently on the latest version.")
        self.toast_requested.emit("Currently on latest version", "info")
        # Let cooldown handle the button re-enablement

    def _on_check_error(self, msg: str):
        self._status_label.setText("Failed to check for updates.")
        self.toast_requested.emit(msg, "error")

    def _on_cooldown_end(self):
        """Re-enables the button if it's still in the 'checking' state."""
        if self._action_btn.text() == "Checking...":
            self._action_btn.setText("Check for Updates")
            self._action_btn.setEnabled(True)

    # --- Downloading Phase ---
    def _start_downloading(self):
        self._action_btn.setEnabled(False)
        self._progress_bar.setVisible(True)
        self._progress_bar.setValue(0)
        self._status_label.setText("Starting download...")
        
        self._downloader_worker = UpdateDownloaderWorker(self._download_url)
        self._downloader_worker.progress_updated.connect(self._on_download_progress)
        self._downloader_worker.download_complete.connect(self._on_download_complete)
        self._downloader_worker.error_occurred.connect(self._on_download_error)
        self._downloader_worker.start()

    def _on_download_progress(self, downloaded: int, total: int):
        if total > 0:
            pct = int((downloaded / total) * 100)
            self._progress_bar.setValue(pct)
            
            dl_mb = downloaded / (1024 * 1024)
            tot_mb = total / (1024 * 1024)
            self._status_label.setText(f"Downloading... ({dl_mb:.1f} MB / {tot_mb:.1f} MB)")
            self._action_btn.setText(f"Downloading {pct}%")

    def _on_download_complete(self, filepath: str):
        self._downloaded_exe_path = filepath
        self._status_label.setText("Download complete! Ready to install.")
        self._progress_bar.setVisible(False)
        
        self._action_btn.setText("Install")
        self._action_btn.setStyleSheet(self._get_btn_style("green"))
        self._action_btn.setEnabled(True)
        self.toast_requested.emit("Update downloaded successfully!", "success")

    def _on_download_error(self, msg: str):
        self._status_label.setText("Download failed.")
        self._progress_bar.setVisible(False)
        self._action_btn.setText("Check for Updates")
        self._action_btn.setEnabled(True)
        self.toast_requested.emit(msg, "error")

    # --- Install Phase ---
    def _start_install(self):
        if self._downloaded_exe_path and os.path.exists(self._downloaded_exe_path):
            try:
                os.startfile(self._downloaded_exe_path)
            except Exception as e:
                self.toast_requested.emit(f"Failed to launch installer: {e}", "error")
        else:
            self.toast_requested.emit("Installer file not found.", "error")
