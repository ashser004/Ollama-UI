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

    def __init__(self, accent_color: str, title: str, value: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            QWidget#statCard {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
            QWidget#statCard:hover {{
                border: 1px solid {accent_color}80;
            }}
        """)
        self.setObjectName("statCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        # Colored accent dot
        dot = QLabel("●")
        dot.setStyleSheet(f"color: {accent_color}; font-size: 10px; background: transparent;")
        layout.addWidget(dot)

        self._value = QLabel(value)
        self._value.setStyleSheet(f"""
            font-size: 22px; font-weight: 800;
            color: {accent_color}; background: transparent;
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
                row = QPushButton(f"  {conv['title']}  —  {conv['model']}  ·  {conv['created_at'][:10]}")
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
