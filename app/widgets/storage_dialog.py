"""
storage_dialog.py — First-launch directory picker.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QFileDialog, QFrame)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.theme import COLORS, accent_button_style
from app.services.system_monitor import SystemMonitor
from app import config


class StorageDialog(QWidget):
    """Full-screen first-launch storage directory picker."""

    directory_selected = Signal(str)  # emits the AIUI path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._selected_path = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Center card
        card = QWidget()
        card.setFixedSize(520, 420)
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 20px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(8)

        # Welcome icon
        icon = QLabel("◆")
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet(f"font-size: 40px; color: {COLORS.accent_primary}; background: transparent;")
        card_layout.addWidget(icon)

        card_layout.addSpacing(8)

        # Title
        title = QLabel("Welcome to Local AI(UI)")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 22px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        card_layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Choose where to store your AI workspace.\nEverything stays in one folder — fully portable.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"""
            font-size: 13px; color: {COLORS.text_secondary};
            background: transparent; padding: 4px 0;
        """)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(16)

        # Path display
        self._path_frame = QFrame()
        self._path_frame.setFixedHeight(50)
        self._path_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.bg_dark};
                border: 1px dashed {COLORS.border_hover};
                border-radius: 10px;
            }}
        """)
        path_layout = QHBoxLayout(self._path_frame)
        path_layout.setContentsMargins(16, 0, 8, 0)

        self._path_label = QLabel("No folder selected")
        self._path_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 12px; background: transparent;")
        path_layout.addWidget(self._path_label, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.setFixedSize(80, 34)
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
        """)
        browse_btn.clicked.connect(self._browse)
        path_layout.addWidget(browse_btn)

        card_layout.addWidget(self._path_frame)

        # Space info
        self._space_label = QLabel("")
        self._space_label.setAlignment(Qt.AlignCenter)
        self._space_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
        card_layout.addWidget(self._space_label)

        card_layout.addSpacing(12)

        # Continue button
        self._continue_btn = QPushButton("Set Up Workspace")
        self._continue_btn.setCursor(Qt.PointingHandCursor)
        self._continue_btn.setFixedHeight(44)
        self._continue_btn.setEnabled(False)
        self._continue_btn.setStyleSheet(accent_button_style())
        self._continue_btn.clicked.connect(self._continue)
        card_layout.addWidget(self._continue_btn)

        # Warning label
        self._warning_label = QLabel("")
        self._warning_label.setAlignment(Qt.AlignCenter)
        self._warning_label.setWordWrap(True)
        self._warning_label.setStyleSheet(f"color: {COLORS.error}; font-size: 11px; background: transparent;")
        card_layout.addWidget(self._warning_label)

        layout.addWidget(card, alignment=Qt.AlignCenter)

    def _browse(self):
        """Open directory picker."""
        path = QFileDialog.getExistingDirectory(
            self, "Choose Storage Location", "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )
        if path:
            self._selected_path = path
            self._path_label.setText(path)
            self._path_label.setStyleSheet(f"color: {COLORS.text_primary}; font-size: 12px; background: transparent;")
            self._path_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS.bg_dark};
                    border: 1px solid {COLORS.accent_primary}44;
                    border-radius: 10px;
                }}
            """)

            # Check space
            space = SystemMonitor.check_drive_space(path)
            free = space["free_gb"]
            total = space["total_gb"]
            self._space_label.setText(f"{free:.1f} GB free of {total:.0f} GB")

            if free < config.MIN_DISK_FOR_SETUP_GB:
                self._warning_label.setText(
                    f"Need at least {config.MIN_DISK_FOR_SETUP_GB} GB free space."
                )
                self._continue_btn.setEnabled(False)
            else:
                self._warning_label.setText("")
                self._continue_btn.setEnabled(True)

                if free < config.MIN_DISK_FOR_MODELS_GB:
                    self._space_label.setText(
                        f"{free:.1f} GB free — models need at least {config.MIN_DISK_FOR_MODELS_GB} GB"
                    )
                    self._space_label.setStyleSheet(
                        f"color: {COLORS.warning}; font-size: 11px; background: transparent;"
                    )

    def _continue(self):
        """Set up AIUI directory and emit signal."""
        if self._selected_path:
            aiui_path = config.set_aiui_base_dir(self._selected_path)
            self.directory_selected.emit(aiui_path)
