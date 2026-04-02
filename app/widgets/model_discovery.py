"""
model_discovery.py — Model discovery grid with filters and search.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QPushButton, QScrollArea,
                                QGridLayout, QFrame)
from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtGui import QFont

from app.theme import COLORS, search_bar_style, tag_badge_style, get_tag_color
from app.widgets.model_card import ModelCard
from app.ollama.model_catalog import ModelCatalog
from app.ollama.api import OllamaAPI
from app.services.system_monitor import SystemMonitor


class ModelDiscovery(QWidget):
    """Model discovery page with search, filters, and card grid."""

    install_requested = Signal(dict)
    open_chat_requested = Signal(dict)
    delete_requested = Signal(dict)

    def __init__(self, catalog: ModelCatalog, api: OllamaAPI,
                 monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self._catalog = catalog
        self._api = api
        self._monitor = monitor
        self._active_filter = "all"
        self._cards: list[ModelCard] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title = QLabel("Discover Models")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        header.addWidget(title)
        header.addStretch()

        # Storage indicator
        self._storage_label = QLabel("💾 Checking storage...")
        self._storage_label.setStyleSheet(f"""
            font-size: 12px; color: {COLORS.text_secondary};
            background: {COLORS.bg_surface};
            border: 1px solid {COLORS.border_default};
            border-radius: 16px; padding: 6px 14px;
        """)
        header.addWidget(self._storage_label)

        layout.addLayout(header)

        # Search bar
        self._search = QLineEdit()
        self._search.setPlaceholderText("🔍  Search models by name, capability, or keyword...")
        self._search.setFixedHeight(44)
        self._search.setStyleSheet(search_bar_style())
        self._search.textChanged.connect(self._on_search)
        layout.addWidget(self._search)

        # Filter chips
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(8)

        all_caps = ["All", "Chat", "Coding", "Reasoning", "Vision", "Math"]
        self._filter_buttons: dict[str, QPushButton] = {}

        for cap in all_caps:
            btn = QPushButton(cap)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, c=cap: self._set_filter(c))
            self._filter_buttons[cap.lower()] = btn
            filters_layout.addWidget(btn)

        filters_layout.addStretch()
        layout.addLayout(filters_layout)

        self._update_filter_styles()

        # Warning bar (hidden by default)
        self._warning_bar = QFrame()
        self._warning_bar.setVisible(False)
        self._warning_bar.setFixedHeight(44)
        self._warning_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS.warning}18;
                border: 1px solid {COLORS.warning}44;
                border-radius: 10px;
            }}
        """)
        warning_layout = QHBoxLayout(self._warning_bar)
        warning_layout.setContentsMargins(16, 0, 16, 0)
        self._warning_text = QLabel("")
        self._warning_text.setStyleSheet(f"color: {COLORS.warning}; font-size: 12px; background: transparent;")
        warning_layout.addWidget(self._warning_text)
        layout.addWidget(self._warning_bar)

        # Scrollable grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._grid_container = QWidget()
        self._grid_container.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(16)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._grid_container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        """Refresh the model grid."""
        # Update storage info
        disk_free = self._monitor.get_available_disk_gb()
        self._storage_label.setText(f"💾 {disk_free:.1f} GB free")

        if disk_free < 10:
            self._warning_bar.setVisible(True)
            self._warning_text.setText(
                f"⚠️ Only {disk_free:.1f} GB free. You need at least 10 GB to install models. "
                f"Free up space or choose another drive."
            )
        else:
            self._warning_bar.setVisible(False)

        # Get installed model tags
        installed = self._api.list_models()
        installed_tags = []
        for m in installed:
            name = m.get("name", "")
            # Ollama returns names like "mistral:latest", normalize
            base = name.split(":")[0] if ":" in name else name
            installed_tags.append(base)
            installed_tags.append(name)

        # Filter models
        ram_total = self._monitor.get_available_ram_gb()
        models = self._catalog.filter_models(
            capability=self._active_filter,
            search_query=self._search.text() if self._search.text() else None,
            available_disk_gb=disk_free,
            available_ram_gb=ram_total,
            installed_tags=installed_tags,
        )

        # Clear existing cards
        self._clear_grid()

        # Add cards
        cols = 2
        for i, model in enumerate(models):
            card = ModelCard(model)
            card.install_requested.connect(self.install_requested.emit)
            card.open_requested.connect(self.open_chat_requested.emit)
            card.delete_requested.connect(self.delete_requested.emit)
            self._grid_layout.addWidget(card, i // cols, i % cols)
            self._cards.append(card)

        # Empty state
        if not models:
            empty = QLabel("No models found matching your criteria")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 14px; padding: 40px; background: transparent;")
            self._grid_layout.addWidget(empty, 0, 0, 1, 2)

    def _clear_grid(self):
        """Remove all widgets from grid."""
        self._cards.clear()
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _set_filter(self, capability: str):
        """Set the active capability filter."""
        self._active_filter = capability.lower()
        self._update_filter_styles()
        self.refresh()

    def _update_filter_styles(self):
        """Update filter button visual states."""
        for key, btn in self._filter_buttons.items():
            if key == self._active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS.accent_primary};
                        color: {COLORS.text_on_accent};
                        border: none;
                        border-radius: 16px;
                        padding: 4px 16px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                """)
            else:
                color = get_tag_color(key) if key != "all" else COLORS.text_secondary
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS.bg_surface};
                        color: {color};
                        border: 1px solid {COLORS.border_default};
                        border-radius: 16px;
                        padding: 4px 16px;
                        font-size: 12px;
                    }}
                    QPushButton:hover {{
                        background: {COLORS.bg_elevated};
                        border-color: {color};
                    }}
                """)

    @Slot(str)
    def _on_search(self, text: str):
        """Handle search input changes."""
        self.refresh()

    def get_card_by_tag(self, tag: str) -> ModelCard | None:
        """Get a model card by its tag."""
        for card in self._cards:
            if card._model.get("tag") == tag:
                return card
        return None
