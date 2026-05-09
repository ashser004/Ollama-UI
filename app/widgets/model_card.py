# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
model_card.py — Individual model card widget for discovery grid.

Supports install, pause, resume (from cache), open chat, and delete.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QProgressBar, QFrame)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QCursor

from app.theme import COLORS, accent_button_style, danger_button_style, tag_badge_style, get_tag_color


class ModelCard(QWidget):
    """Card widget showing model info with install/pause/resume/open/delete actions."""

    install_requested = Signal(dict)  # model data
    open_requested = Signal(dict)
    delete_requested = Signal(dict)
    pause_requested = Signal(dict)    # model data — pause active download

    def __init__(self, model: dict, parent=None):
        super().__init__(parent)
        self._model = model
        self._is_downloading = False
        self._is_paused = model.get("is_paused", False)
        self._last_pct = model.get("paused_progress_pct", 0)

        self.setFixedHeight(190)
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

        # Min RAM tag
        min_ram = model.get("min_ram_gb", 0)
        if min_ram > 0:
            ram_label = QLabel(f"{min_ram:.0f} GB RAM")
            ram_color = COLORS.success if min_ram <= 4 else COLORS.warning if min_ram <= 8 else COLORS.error
            ram_label.setStyleSheet(f"""
                font-size: 10px; font-weight: 600;
                color: {ram_color}; background: transparent;
                padding: 2px 8px;
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
            """)
            top_row.addWidget(ram_label)

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
        capabilities = [cap.lower() for cap in model.get("capabilities", [])]
        for cap in model.get("capabilities", []):
            tag = QLabel(cap.capitalize())
            tag.setStyleSheet(tag_badge_style(get_tag_color(cap)))
            tag.setFixedHeight(22)
            tags_layout.addWidget(tag)

        # Vision indicator
        if model.get("supports_images") and "vision" not in capabilities:
            vision_tag = QLabel("Vision")
            vision_tag.setStyleSheet(tag_badge_style(COLORS.tag_vision))
            vision_tag.setFixedHeight(22)
            tags_layout.addWidget(vision_tag)

        tags_layout.addStretch()
        layout.addLayout(tags_layout)

        layout.addStretch()

        # ── Progress row: [ProgressBar] [PauseBtn] ──
        progress_row = QHBoxLayout()
        progress_row.setSpacing(6)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(10)
        self._progress.setRange(0, 100)
        progress_row.addWidget(self._progress, 1)

        self._pause_btn = QPushButton("Pause")
        self._pause_btn.setFixedSize(58, 28)
        self._pause_btn.setCursor(Qt.PointingHandCursor)
        self._pause_btn.setToolTip("Pause download")
        self._pause_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 10px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.warning};
                border-color: {COLORS.warning}55;
            }}
        """)
        self._pause_btn.clicked.connect(self._on_pause_click)
        self._pause_btn.setVisible(False)
        progress_row.addWidget(self._pause_btn)

        layout.addLayout(progress_row)

        self._progress_label = QLabel("")
        self._progress_label.setStyleSheet(f"color: {COLORS.text_primary}; font-size: 10px; font-weight: 600; background: transparent;")
        self._progress_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._progress_label)

        # ── Action buttons row ──
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        is_installed = model.get("is_installed", False)
        can_install = model.get("can_install", True)
        warning = model.get("install_warning", "")

        if is_installed:
            # ── Installed: Chat + Delete ──
            self._progress.setVisible(False)
            self._progress_label.setVisible(False)

            open_btn = QPushButton("Chat")
            open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setFixedSize(88, 34)
            open_btn.setStyleSheet(accent_button_style())
            open_btn.clicked.connect(lambda: self.open_requested.emit(self._model))
            action_layout.addWidget(open_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(88, 34)
            del_btn.setStyleSheet(danger_button_style())
            del_btn.clicked.connect(lambda: self.delete_requested.emit(self._model))
            action_layout.addWidget(del_btn)

        elif self._is_paused:
            # ── Paused: show saved progress + Resume ──
            self._progress.setValue(self._last_pct)
            self._progress.setVisible(True)
            self._progress_label.setText(f"Paused — {self._last_pct}%")
            self._progress_label.setVisible(True)
            self._pause_btn.setVisible(False)

            self._install_btn = QPushButton("▶  Resume")
            self._install_btn.setCursor(Qt.PointingHandCursor)
            self._install_btn.setFixedHeight(32)
            self._install_btn.setStyleSheet(accent_button_style())
            self._install_btn.clicked.connect(self._on_resume_click)
            action_layout.addWidget(self._install_btn)

        else:
            # ── Not installed: Install button ──
            self._progress.setVisible(False)
            self._progress_label.setVisible(False)

            self._install_btn = QPushButton("Install" if can_install else "! " + warning)
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
            self._install_btn.clicked.connect(self._on_install_click)
            action_layout.addWidget(self._install_btn)

        layout.addLayout(action_layout)

    # ─── Interactions ────────────────────────────────

    def set_downloading(self):
        """Set the card into downloading state (for reconnection after tab switch)."""
        self._is_downloading = True
        self._is_paused = False
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._progress_label.setText("Downloading — 0%")
        self._pause_btn.setVisible(True)
        if hasattr(self, '_install_btn'):
            self._install_btn.setVisible(False)

    def _on_install_click(self):
        """Handle install button click."""
        if not self._is_downloading:
            self.install_requested.emit(self._model)

    def _on_resume_click(self):
        """Handle resume button click — re-triggers install (Ollama handles cache)."""
        self._is_paused = False
        self.install_requested.emit(self._model)

    def _on_pause_click(self):
        """Handle pause button click."""
        self._is_downloading = False
        self._is_paused = True
        self._pause_btn.setVisible(False)
        self._progress_label.setText(f"Paused — {self._last_pct}%")
        if hasattr(self, '_install_btn'):
            self._install_btn.setText("▶  Resume")
            self._install_btn.setVisible(True)
            self._install_btn.setEnabled(True)
            self._install_btn.setStyleSheet(accent_button_style())
            try:
                self._install_btn.clicked.disconnect()
            except RuntimeError:
                pass
            self._install_btn.clicked.connect(self._on_resume_click)
        self.pause_requested.emit(self._model)

    @Slot(float, float, str)
    def update_progress(self, completed: float, total: float, status: str):
        """Update download progress."""
        self._is_downloading = True
        self._is_paused = False
        self._progress.setVisible(True)
        self._progress_label.setVisible(True)
        self._pause_btn.setVisible(True)
        if hasattr(self, '_install_btn'):
            self._install_btn.setVisible(False)

        if total > 0:
            pct = int((completed / total) * 100)
            # Clamp to 99% during download — 100% is only set by install_finished
            pct = min(pct, 99)
            self._last_pct = pct
            self._progress.setValue(pct)
            mb = completed / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._progress_label.setText(f"{status} — {pct}% ({mb:.0f}/{mb_total:.0f} MB)")
        else:
            # Phases like "verifying sha256 digest" have no total
            if "verif" in status.lower():
                self._progress.setValue(99)
                self._progress_label.setText("Verifying download...")
            else:
                self._progress_label.setText(status)

    @Slot(bool, str)
    def install_finished(self, success: bool, message: str):
        """Handle install completion."""
        self._is_downloading = False
        self._is_paused = False
        self._progress.setVisible(False)
        self._progress_label.setVisible(False)
        self._pause_btn.setVisible(False)
        if hasattr(self, '_install_btn'):
            if success:
                self._install_btn.setText("Installed ✓")
                self._install_btn.setEnabled(False)
            else:
                self._install_btn.setText("Retry Install")
                self._install_btn.setVisible(True)
                self._install_btn.setEnabled(True)
