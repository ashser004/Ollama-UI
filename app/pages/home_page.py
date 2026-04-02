"""
home_page.py — Main dashboard after setup.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QFrame, QGridLayout)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont, QCursor

from app.theme import COLORS, accent_button_style, card_style
from app.ollama.api import OllamaAPI
from app.services.system_monitor import SystemMonitor
from app import config, database as db


class StatCard(QWidget):
    """Small stat card widget."""

    def __init__(self, icon: str, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QWidget#statCard {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
        """)
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 20))
        icon_label.setStyleSheet("background: transparent;")
        top.addWidget(icon_label)
        top.addStretch()
        layout.addLayout(top)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            font-size: 22px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(self._value)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
        layout.addWidget(title_label)

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

        greeting = QLabel("Welcome back 👋")
        greeting.setStyleSheet(f"""
            font-size: 28px; font-weight: 800;
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

        self._models_stat = StatCard("📦", "Models Installed", "0")
        stats_grid.addWidget(self._models_stat, 0, 0)

        self._chats_stat = StatCard("💬", "Conversations", "0")
        stats_grid.addWidget(self._chats_stat, 0, 1)

        self._storage_stat = StatCard("💾", "Storage Free", "--")
        stats_grid.addWidget(self._storage_stat, 0, 2)

        self._ram_stat = StatCard("🧠", "System RAM", "--")
        stats_grid.addWidget(self._ram_stat, 0, 3)

        layout.addLayout(stats_grid)

        # Quick actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(14)

        new_chat_btn = self._make_action_card(
            "💬", "New Chat", "Start a conversation with an AI model",
            lambda: self.navigate_to.emit("chat")
        )
        actions_layout.addWidget(new_chat_btn)

        discover_btn = self._make_action_card(
            "🔍", "Discover Models", "Browse and install AI models",
            lambda: self.navigate_to.emit("discover")
        )
        actions_layout.addWidget(discover_btn)

        manage_btn = self._make_action_card(
            "📦", "Manage Models", "View and manage installed models",
            lambda: self.navigate_to.emit("manage")
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

        self._recent_container = QVBoxLayout()
        self._recent_container.setSpacing(8)
        layout.addLayout(self._recent_container)

        layout.addStretch()

    def _make_action_card(self, icon: str, title: str, desc: str, callback) -> QWidget:
        """Create a clickable action card."""
        card = QPushButton()
        card.setCursor(QCursor(Qt.PointingHandCursor))
        card.setFixedHeight(110)
        card.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
                text-align: left;
                padding: 18px;
            }}
            QPushButton:hover {{
                border-color: {COLORS.accent_primary}44;
                background-color: {COLORS.bg_elevated};
            }}
        """)
        card.clicked.connect(callback)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(6)

        icon_label = QLabel(icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 22))
        icon_label.setStyleSheet("background: transparent;")
        card_layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 14px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        card_layout.addWidget(title_label)

        desc_label = QLabel(desc)
        desc_label.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted}; background: transparent;")
        card_layout.addWidget(desc_label)

        return card

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

        # Recent conversations
        while self._recent_container.count():
            item = self._recent_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not convs:
            empty = QLabel("No conversations yet. Start a chat to get going!")
            empty.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 13px; background: transparent; padding: 16px;")
            self._recent_container.addWidget(empty)
        else:
            for conv in convs[:5]:
                row = QPushButton(f"  💬  {conv['title']}    —    {conv['model']}    •    {conv['created_at'][:10]}")
                row.setCursor(QCursor(Qt.PointingHandCursor))
                row.setFixedHeight(44)
                row.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS.bg_surface};
                        color: {COLORS.text_secondary};
                        border: 1px solid {COLORS.border_default};
                        border-radius: 10px;
                        text-align: left;
                        padding: 0 16px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background: {COLORS.bg_elevated};
                        color: {COLORS.text_primary};
                        border-color: {COLORS.border_hover};
                    }}
                """)
                row.clicked.connect(lambda checked, cid=conv["id"]: self.open_chat_conv.emit(cid))
                self._recent_container.addWidget(row)
