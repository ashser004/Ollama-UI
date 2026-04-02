"""
model_card.py — Individual model card widget for discovery grid.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QProgressBar, QFrame)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QCursor

from app.theme import COLORS, accent_button_style, danger_button_style, tag_badge_style, get_tag_color


class ModelCard(QWidget):
    """Card widget showing model info with install/open/delete actions."""

    install_requested = Signal(dict)  # model data
    open_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, model: dict, parent=None):
        super().__init__(parent)
        self._model = model
        self._is_downloading = False

        self.setFixedHeight(180)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet(f"""
            QWidget#modelCard {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
            QWidget#modelCard:hover {{
                border-color: {COLORS.border_hover};
                background-color: {COLORS.bg_elevated};
            }}
        """)
        self.setObjectName("modelCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 14)
        layout.setSpacing(6)

        # Top row: name + size
        top_row = QHBoxLayout()

        name_label = QLabel(model.get("name", "Unknown"))
        name_label.setStyleSheet(f"""
            font-size: 15px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        top_row.addWidget(name_label)

        top_row.addStretch()

        size = model.get("size_gb", 0)
        size_label = QLabel(f"{size:.1f} GB")
        size_label.setStyleSheet(f"""
            font-size: 11px; font-weight: 600;
            color: {COLORS.text_muted}; background: transparent;
            padding: 2px 8px;
            border: 1px solid {COLORS.border_default};
            border-radius: 8px;
        """)
        top_row.addWidget(size_label)

        layout.addLayout(top_row)

        # Description
        desc = model.get("description", "")
        desc_label = QLabel(desc)
        desc_label.setWordWrap(True)
        desc_label.setFixedHeight(36)
        desc_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 12px; background: transparent;")
        layout.addWidget(desc_label)

        # Capability tags
        tags_layout = QHBoxLayout()
        tags_layout.setSpacing(6)
        for cap in model.get("capabilities", []):
            tag = QLabel(cap.capitalize())
            tag.setStyleSheet(tag_badge_style(get_tag_color(cap)))
            tag.setFixedHeight(22)
            tags_layout.addWidget(tag)

        # Vision indicator
        if model.get("supports_images"):
            vision_tag = QLabel("Vision")
            vision_tag.setStyleSheet(tag_badge_style(COLORS.tag_vision))
            vision_tag.setFixedHeight(22)
            tags_layout.addWidget(vision_tag)

        tags_layout.addStretch()
        layout.addLayout(tags_layout)

        layout.addStretch()

        # Bottom: progress bar (hidden) + action button
        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setFixedHeight(10)
        self._progress.setRange(0, 100)
        layout.addWidget(self._progress)

        self._progress_label = QLabel("")
        self._progress_label.setVisible(False)
        self._progress_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 10px; background: transparent;")
        self._progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._progress_label)

        # Action buttons row
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        is_installed = model.get("is_installed", False)
        can_install = model.get("can_install", True)
        warning = model.get("install_warning", "")

        if is_installed:
            open_btn = QPushButton("Open Chat")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setFixedHeight(32)
            open_btn.setStyleSheet(accent_button_style())
            open_btn.clicked.connect(lambda: self.open_requested.emit(self._model))
            action_layout.addWidget(open_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedHeight(32)
            del_btn.setStyleSheet(danger_button_style())
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self._model))
            action_layout.addWidget(del_btn)
        else:
            self._install_btn = QPushButton("Install" if can_install else "⚠️ " + warning)
            self._install_btn.setCursor(Qt.PointingHandCursor)
            self._install_btn.setFixedHeight(32)
            self._install_btn.setEnabled(can_install)
            if can_install:
                self._install_btn.setStyleSheet(accent_button_style())
            else:
                self._install_btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS.bg_elevated};
                        color: {COLORS.warning};
                        border: 1px solid {COLORS.warning}44;
                        border-radius: 8px;
                        padding: 6px 16px;
                        font-size: 11px;
                    }}
                """)
            self._install_btn.clicked.connect(lambda: self._on_install_click())
            action_layout.addWidget(self._install_btn)

        layout.addLayout(action_layout)

    def _on_install_click(self):
        """Handle install button click."""
        if not self._is_downloading:
            self.install_requested.emit(self._model)

    @Slot(int, int, str)
    def update_progress(self, completed: int, total: int, status: str):
        """Update download progress."""
        self._is_downloading = True
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        if hasattr(self, '_install_btn'):
            self._install_btn.setVisible(False)

        if total > 0:
            pct = int((completed / total) * 100)
            self._progress.setValue(pct)
            mb = completed / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._progress_label.setText(f"{status} — {mb:.0f}/{mb_total:.0f} MB")
        else:
            self._progress_label.setText(status)

    @Slot(bool, str)
    def install_finished(self, success: bool, message: str):
        """Handle install completion."""
        self._is_downloading = False
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        if hasattr(self, '_install_btn'):
            if success:
                self._install_btn.setText("✅ Installed")
                self._install_btn.setEnabled(False)
            else:
                self._install_btn.setText("Retry Install")
                self._install_btn.setVisible(True)
                self._install_btn.setEnabled(True)
