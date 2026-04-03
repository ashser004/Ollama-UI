"""
home_page.py — Main dashboard after setup.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QFrame, QGridLayout,
                                QGraphicsDropShadowEffect, QSizePolicy,
                                QLineEdit, QComboBox)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QCursor, QColor

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


class HomePage(QWidget):
    """Main dashboard page."""

    navigate_to = Signal(str)  # page key
    open_chat = Signal(str)  # model name
    open_chat_conv = Signal(int)  # conversation id

    def __init__(self, api: OllamaAPI, monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self._api = api
        self._monitor = monitor

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 16)
        layout.setSpacing(20)

        # Welcome header
        header = QVBoxLayout()
        header.setSpacing(4)

        greeting = QLabel("Welcome back")
        greeting.setStyleSheet(f"""
            font-size: 32px; font-weight: 900;
            color: {COLORS.text_primary}; background: transparent;
        """)
        header.addWidget(greeting)

        subtitle = QLabel("Your offline AI workspace is ready")
        subtitle.setStyleSheet(f"font-size: 14px; color: {COLORS.text_secondary}; background: transparent;")
        header.addWidget(subtitle)

        layout.addLayout(header)

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
