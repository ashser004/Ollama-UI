# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
home_page.py — Main dashboard after setup.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QFrame, QGridLayout,
                                QGraphicsDropShadowEffect, QSizePolicy,
                                QLineEdit, QComboBox)
from PySide6.QtCore import Qt, Signal, Slot, QPropertyAnimation, Property, QEasingCurve
from PySide6.QtGui import QFont, QCursor, QColor, QPainter, QBrush, QPen

from app.theme import COLORS, accent_button_style, card_style, search_bar_style
from app.ollama.api import OllamaAPI
from app.services.system_monitor import SystemMonitor
from app import config, database as db


class StatCard(QWidget):
    """Small stat card widget."""

    def __init__(self, accent_color: str, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(112)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(26)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(8, 15, 30, 160))
        self.setGraphicsEffect(shadow)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self._card = QFrame()
        self._card.setObjectName("statCardFrame")
        self._card.setStyleSheet(f"""
            QFrame#statCardFrame {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
            }}
            QFrame#statCardFrame:hover {{
                border: 1px solid {accent_color};
                background-color: {COLORS.bg_hover};
            }}
        """)

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        accent_bar = QFrame()
        accent_bar.setFixedHeight(3)
        accent_bar.setStyleSheet(f"background-color: {accent_color}; border-radius: 1px;")
        card_layout.addWidget(accent_bar)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            font-size: 24px; font-weight: 900;
            color: {accent_color}; background: transparent;
        """)
        card_layout.addWidget(self._value)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")
        card_layout.addWidget(title_label)

        card_layout.addStretch()
        outer_layout.addWidget(self._card)

    def set_value(self, value: str):
        self._value.setText(value)


class ToggleSwitch(QWidget):
    """Custom painted toggle switch with sliding circle animation."""

    toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 26)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self._checked = False
        self._circle_x = 4.0  # starting x of the circle

        self._anim = QPropertyAnimation(self, b"circle_x", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.InOutCubic)

    def _get_circle_x(self) -> float:
        return self._circle_x

    def _set_circle_x(self, val: float):
        self._circle_x = val
        self.update()

    circle_x = Property(float, _get_circle_x, _set_circle_x)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, on: bool):
        self._checked = on
        self._circle_x = 24.0 if on else 4.0
        self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        end = 24.0 if self._checked else 4.0
        self._anim.stop()
        self._anim.setStartValue(self._circle_x)
        self._anim.setEndValue(end)
        self._anim.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        # Track background
        if self._checked:
            track_color = QColor(COLORS.tag_imagegen)
        else:
            track_color = QColor(COLORS.bg_hover)

        p.setPen(QPen(QColor(COLORS.border_default), 1))
        p.setBrush(QBrush(track_color))
        p.drawRoundedRect(0, 0, 48, 26, 13, 13)

        # Circle knob
        knob_color = QColor("#ffffff") if self._checked else QColor(COLORS.text_muted)
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(knob_color))
        p.drawEllipse(int(self._circle_x), 4, 18, 18)

        p.end()


class HomePage(QWidget):
    """Main dashboard page."""

    navigate_to = Signal(str)  # page key
    open_chat = Signal(str)  # model name
    open_chat_conv = Signal(int)  # conversation id
    imagegen_toggled = Signal(bool)  # True = enabled

    def __init__(self, api: OllamaAPI, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self._api = api
        self._monitor = monitor
        self._imagegen_enabled = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(20)

        # Welcome header row (greeting left, imagegen toggle right)
        header_row = QHBoxLayout()
        header_row.setSpacing(16)

        # Left: greeting
        greeting_col = QVBoxLayout()
        greeting_col.setSpacing(4)

        greeting = QLabel("Welcome back")
        greeting.setStyleSheet(f"""
            font-size: 32px; font-weight: 900;
            color: {COLORS.text_primary}; background: transparent;
        """)
        greeting_col.addWidget(greeting)

        subtitle = QLabel("Your offline AI workspace is ready")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary}; background: transparent;")
        greeting_col.addWidget(subtitle)

        header_row.addLayout(greeting_col)
        header_row.addStretch()

        # Right: Image Generation toggle
        toggle_card = QFrame()
        toggle_card.setObjectName("imagegenToggleCard")
        toggle_card.setFixedSize(260, 64)
        toggle_card.setStyleSheet(f"""
            QFrame#imagegenToggleCard {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
            QFrame#imagegenToggleCard:hover {{
                border-color: {COLORS.tag_imagegen}55;
            }}
        """)

        toggle_layout = QHBoxLayout(toggle_card)
        toggle_layout.setContentsMargins(14, 8, 14, 8)
        toggle_layout.setSpacing(10)

        # Icon + labels
        toggle_info = QVBoxLayout()
        toggle_info.setSpacing(2)

        toggle_title = QLabel("🎨 Image Generation")
        toggle_title.setStyleSheet(f"font-size: 12px; font-weight: 700; color: {COLORS.text_primary}; background: transparent;")
        toggle_info.addWidget(toggle_title)

        self._imagegen_status = QLabel("Disabled")
        self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.text_muted}; background: transparent;")
        toggle_info.addWidget(self._imagegen_status)

        # Download progress (hidden by default)
        self._imagegen_progress = QLabel("")
        self._imagegen_progress.setStyleSheet(f"font-size: 10px; color: {COLORS.accent_primary}; background: transparent;")
        self._imagegen_progress.setVisible(False)
        toggle_info.addWidget(self._imagegen_progress)

        toggle_layout.addLayout(toggle_info, 1)

        # Toggle switch (custom painted sliding circle)
        self._imagegen_toggle_btn = ToggleSwitch()
        self._imagegen_toggle_btn.setChecked(False)
        self._imagegen_toggle_btn.toggled.connect(self._on_imagegen_toggle_raw)
        toggle_layout.addWidget(self._imagegen_toggle_btn)

        header_row.addWidget(toggle_card)

        layout.addLayout(header_row)

        # Stats row
        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)
        stats_grid.setColumnStretch(0, 1)
        stats_grid.setColumnStretch(1, 1)
        stats_grid.setColumnStretch(2, 1)
        stats_grid.setColumnStretch(3, 1)

        self._models_stat = StatCard(COLORS.accent_primary, "Models Installed", "0")
        stats_grid.addWidget(self._models_stat, 0, 0)

        self._chats_stat = StatCard(COLORS.success, "Conversations", "0")
        stats_grid.addWidget(self._chats_stat, 0, 1)

        self._storage_stat = StatCard(COLORS.warning, "Storage Free", "--")
        stats_grid.addWidget(self._storage_stat, 0, 2)

        self._ram_stat = StatCard("#e879f9", "System RAM", "--")
        stats_grid.addWidget(self._ram_stat, 0, 3)

        layout.addLayout(stats_grid)

        # Quick actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(14)

        new_chat_btn = self._make_action_card(
            "New Chat", "Start a conversation with an AI model",
            self._on_new_chat_click,
            COLORS.accent_primary
        )
        actions_layout.addWidget(new_chat_btn)

        discover_btn = self._make_action_card(
            "Discover Models", "Browse and install AI models",
            lambda: self.navigate_to.emit("discover"),
            COLORS.info
        )
        actions_layout.addWidget(discover_btn)

        manage_btn = self._make_action_card(
            "Manage Models", "View and manage installed models",
            lambda: self.navigate_to.emit("manage"),
            COLORS.success
        )
        actions_layout.addWidget(manage_btn)

        layout.addLayout(actions_layout)

        # Recent conversations
        recent_header = QHBoxLayout()
        recent_title = QLabel("Recent Conversations")
        recent_title.setStyleSheet(f"""
            font-size: 16px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        recent_header.addWidget(recent_title)
        recent_header.addStretch()
        layout.addLayout(recent_header)

        recent_controls = QHBoxLayout()
        recent_controls.setSpacing(12)

        self._recent_search = QLineEdit()
        self._recent_search.setPlaceholderText("Search recent chats or messages...")
        self._recent_search.setFixedHeight(42)
        self._recent_search.setStyleSheet(search_bar_style())
        self._recent_search.textChanged.connect(self._refresh_recent_conversations)
        recent_controls.addWidget(self._recent_search, 1)

        filter_shell = QWidget()
        filter_shell.setFixedHeight(42)
        filter_shell.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_hover};
                border-radius: 12px;
            }}
        """)
        filter_layout = QHBoxLayout(filter_shell)
        filter_layout.setContentsMargins(12, 0, 10, 0)
        filter_layout.setSpacing(8)

        self._recent_model_filter = QComboBox()
        self._recent_model_filter.setFixedHeight(30)
        self._recent_model_filter.setMinimumWidth(180)
        self._recent_model_filter.setStyleSheet(f"""
            QComboBox {{
                background: transparent;
                color: {COLORS.text_primary};
                border: none;
                padding: 0px;
                font-size: 13px;
                font-weight: 600;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                selection-background-color: {COLORS.bg_hover};
                selection-color: {COLORS.text_primary};
                outline: none;
            }}
        """)
        self._recent_model_filter.currentTextChanged.connect(self._refresh_recent_conversations)
        filter_layout.addWidget(self._recent_model_filter, 1)

        filter_arrow = QLabel("▾")
        filter_arrow.setStyleSheet(f"""
            color: {COLORS.accent_primary};
            background: transparent;
            font-size: 14px;
            font-weight: 700;
        """)
        filter_arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        filter_layout.addWidget(filter_arrow)

        filter_shell.mousePressEvent = lambda event, combo=self._recent_model_filter: combo.showPopup()
        recent_controls.addWidget(filter_shell)

        layout.addLayout(recent_controls)

        self._recent_container = QVBoxLayout()
        self._recent_container.setSpacing(8)
        layout.addLayout(self._recent_container)

        layout.addStretch()

    def _make_action_card(self, title: str, desc: str, callback, accent_color: str) -> QWidget:
        """Create a clickable action card — text only, no emoji icons."""
        card = QPushButton()
        card.setCursor(QCursor(Qt.PointingHandCursor))
        card.setFixedHeight(80)
        card.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {accent_color}66;
                border-radius: 14px;
                text-align: center;
                padding: 18px;
            }}
            QPushButton:hover {{
                border: 1px solid {accent_color};
                background-color: {accent_color}1a;
            }}
        """)
        card.clicked.connect(callback)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(4)
        card_layout.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 15px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        card_layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"font-size: 12px; color: {accent_color}; background: transparent;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        card_layout.addWidget(desc_label)

        return card

    def _on_new_chat_click(self):
        """Navigate to chat if models installed, otherwise to discover."""
        models = self._api.list_models()
        if models:
            self.navigate_to.emit("chat")
        else:
            self.navigate_to.emit("discover")

    def refresh(self):
        """Update dashboard data."""
        # Models count
        models = self._api.list_models()
        self._models_stat.set_value(str(len(models)))

        # Conversations count
        try:
            convs = db.get_conversations()
            self._chats_stat.set_value(str(len(convs)))
        except Exception:
            self._chats_stat.set_value("0")
            convs = []

        # Storage
        disk_free = self._monitor.get_available_disk_gb()
        self._storage_stat.set_value(f"{disk_free:.1f} GB")

        # RAM
        ram_total = self._monitor.get_available_ram_gb()
        self._ram_stat.set_value(f"{ram_total:.0f} GB")

        self._populate_recent_filters()
        self._refresh_recent_conversations()

    def _populate_recent_filters(self):
        """Populate the recent-chat model filter from installed models."""
        current = self._recent_model_filter.currentText() if hasattr(self, "_recent_model_filter") else "All Models"
        models = []
        for item in self._api.list_models():
            name = item.get("name")
            if name:
                models.append(name)

        self._recent_model_filter.blockSignals(True)
        self._recent_model_filter.clear()
        self._recent_model_filter.addItem("All Models")
        for name in models:
            self._recent_model_filter.addItem(name)

        idx = self._recent_model_filter.findText(current)
        self._recent_model_filter.setCurrentIndex(idx if idx >= 0 else 0)
        self._recent_model_filter.blockSignals(False)

    def _refresh_recent_conversations(self):
        """Refresh the recent conversation cards based on search and model filter."""
        while self._recent_container.count():
            item = self._recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self._recent_search.text().strip() if hasattr(self, "_recent_search") else ""
        selected_model = self._recent_model_filter.currentText() if hasattr(self, "_recent_model_filter") else "All Models"
        conversations = db.search_conversations(query, selected_model)

        if not conversations:
            if query or selected_model != "All Models":
                empty_text = "No recent chats match your search or filter."
            else:
                empty_text = "No conversations yet. Start a chat to get going!"

            empty = QLabel(empty_text)
            empty.setWordWrap(True)
            empty.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 13px; background: transparent; padding: 16px;")
            self._recent_container.addWidget(empty)
            return

        for conv in conversations[:5]:
            row = QPushButton(f"  {conv['title']}  —  {conv['model']}  ·  {conv['created_at'][:10]}")
            row.setCursor(QCursor(Qt.PointingHandCursor))
            row.setFixedHeight(50)
            row.setStyleSheet(f"""
                QPushButton {{
                    background: {COLORS.bg_elevated};
                    color: {COLORS.text_secondary};
                    border: 1px solid {COLORS.border_default};
                    border-radius: 12px;
                    text-align: left;
                    padding: 8px 16px;
                    font-size: 12px;
                }}
                QPushButton:hover {{
                    background: {COLORS.bg_hover};
                    color: {COLORS.text_primary};
                    border-color: {COLORS.accent_primary};
                }}
            """)
            row.clicked.connect(lambda checked, cid=conv["id"]: self.open_chat_conv.emit(cid))
            self._recent_container.addWidget(row)

    # ─── Image Generation Toggle ──────────────────────────────────

    def _update_toggle_style(self, enabled: bool):
        """Update the toggle switch visual state."""
        self._imagegen_toggle_btn.setChecked(enabled)

    def _on_imagegen_toggle_raw(self, is_checked: bool):
        """Intercept raw toggle signal to handle engine download on first enable."""
        if is_checked:
            from app import config as cfg
            if not cfg.is_imagegen_installed():
                # Revert toggle — download first
                self._imagegen_toggle_btn.setChecked(False)
                self._start_engine_download()
                return

            # Engine installed — enable
            self._imagegen_enabled = True
            self._imagegen_status.setText("Enabled")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.success}; background: transparent;")
            self.imagegen_toggled.emit(True)
        else:
            self._imagegen_enabled = False
            self._imagegen_status.setText("Disabled")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.text_muted}; background: transparent;")
            self.imagegen_toggled.emit(False)


    def _start_engine_download(self):
        """Download the sd-cli engine binary for the first time."""
        from app.imagegen.manager import ImageGenManager
        from app.widgets.popup import ConfirmDialog

        # Show warning dialog first
        msg = (
            "⚠️ Image generation on CPU is slow.\n\n"
            "A 512×512 image typically takes 3–8 minutes on a modern CPU.\n"
            "If your PC has an NVIDIA GPU, it will be used automatically.\n\n"
            "This will download a small engine binary (~8 MB).\n\n"
            "Continue?"
        )

        self._engine_confirm = ConfirmDialog(
            title="Enable Image Generation",
            message=msg,
            confirm_text="Download & Enable",
            on_confirm=self._do_engine_download,
            parent=self.window(),
        )
        self._engine_confirm.show_centered(self.window())

    def _do_engine_download(self):
        """Actually start the engine download after confirmation."""
        from app.imagegen.manager import ImageGenManager

        self._imagegen_status.setText("Downloading engine...")
        self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.accent_primary}; background: transparent;")
        self._imagegen_progress.setVisible(True)
        self._imagegen_toggle_btn.setEnabled(False)

        mgr = ImageGenManager(self)
        self._engine_dl_worker = mgr.download_engine()
        self._engine_dl_worker.progress.connect(self._on_engine_dl_progress)
        self._engine_dl_worker.finished.connect(self._on_engine_dl_finished)
        self._engine_dl_worker.start()

    def _on_engine_dl_progress(self, downloaded: int, total: int):
        """Update engine download progress."""
        if total > 0:
            pct = int(downloaded / total * 100)
            mb_done = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self._imagegen_progress.setText(f"{mb_done:.1f} / {mb_total:.1f} MB ({pct}%)")
        else:
            mb_done = downloaded / (1024 * 1024)
            self._imagegen_progress.setText(f"{mb_done:.1f} MB downloaded")

    def _on_engine_dl_finished(self, success: bool, message: str):
        """Handle engine download completion."""
        self._imagegen_progress.setVisible(False)
        self._imagegen_toggle_btn.setEnabled(True)

        if success:
            self._imagegen_enabled = True
            self._imagegen_toggle_btn.setChecked(True)
            self._update_toggle_style(True)
            self._imagegen_status.setText("Enabled")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.success}; background: transparent;")
            self.imagegen_toggled.emit(True)
        else:
            self._imagegen_toggle_btn.setChecked(False)
            self._update_toggle_style(False)
            self._imagegen_status.setText("Download failed")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.error}; background: transparent;")

    @property
    def is_imagegen_enabled(self) -> bool:
        return self._imagegen_enabled

    def set_imagegen_enabled(self, enabled: bool):
        """Programmatically set the toggle state (e.g. on app startup = always OFF)."""
        self._imagegen_enabled = enabled
        self._imagegen_toggle_btn.setChecked(enabled)
        self._update_toggle_style(enabled)
        if enabled:
            self._imagegen_status.setText("Enabled")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.success}; background: transparent;")
        else:
            self._imagegen_status.setText("Disabled")
            self._imagegen_status.setStyleSheet(f"font-size: 10px; color: {COLORS.text_muted}; background: transparent;")
