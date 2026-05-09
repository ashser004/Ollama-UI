# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
model_discovery.py — Model discovery grid with filters and search.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QLineEdit, QPushButton, QScrollArea,
                                QGridLayout, QFrame, QComboBox)
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
    pause_requested = Signal(dict)

    def __init__(self, catalog: ModelCatalog, api: OllamaAPI,
                 monitor: SystemMonitor, parent=None):
        super().__init__(parent)
        self._catalog = catalog
        self._api = api
        self._monitor = monitor
        self._active_filter = "all"
        self._sort_mode = "installed_first"
        self._active_downloads: set[str] = set()
        self._cards: list[ModelCard] = []
        self._paused_states: dict = {}  # tag -> {progress_pct, ...}

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
        self._storage_label = QLabel("Checking storage...")
        self._storage_label.setStyleSheet(f"""
            font-size: 12px; color: {COLORS.text_secondary};
            background: {COLORS.bg_surface};
            border: 1px solid {COLORS.border_default};
            border-radius: 16px; padding: 6px 14px;
        """)
        header.addWidget(self._storage_label)

        layout.addLayout(header)

        # Search + sort row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(12)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Search models by name, capability, or keyword...")
        self._search.setFixedHeight(44)
        self._search.setStyleSheet(search_bar_style())
        self._search.textChanged.connect(self._on_search)
        controls_layout.addWidget(self._search, 1)

        sort_shell = QWidget()
        sort_shell.setFixedHeight(44)
        sort_shell.setMinimumWidth(240)
        sort_shell.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_hover};
                border-radius: 12px;
            }}
        """)
        sort_layout = QHBoxLayout(sort_shell)
        sort_layout.setContentsMargins(12, 0, 10, 0)
        sort_layout.setSpacing(8)

        self._sort_combo = QComboBox()
        self._sort_combo.setFixedHeight(30)
        self._sort_combo.setMinimumWidth(188)
        self._sort_combo.setStyleSheet(f"""
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
        self._sort_combo.currentIndexChanged.connect(self._on_sort_changed)
        sort_layout.addWidget(self._sort_combo, 1)

        sort_arrow = QLabel("▾")
        sort_arrow.setStyleSheet(f"""
            color: {COLORS.accent_primary};
            background: transparent;
            font-size: 14px;
            font-weight: 700;
        """)
        sort_arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        sort_layout.addWidget(sort_arrow)

        sort_shell.mousePressEvent = lambda event, combo=self._sort_combo: combo.showPopup()
        controls_layout.addWidget(sort_shell)

        layout.addLayout(controls_layout)

        # Filter chips
        filters_layout = QHBoxLayout()
        filters_layout.setSpacing(8)
        self._filters_layout = filters_layout
        self._filter_buttons: dict[str, QPushButton] = {}
        self._refresh_capability_filters()

        layout.addLayout(filters_layout)

        self._build_sort_options()
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

    def set_download_states(self, states: dict):
        """Set paused/persisted download states for card creation."""
        self._paused_states = states

    def set_active_downloads(self, active_tags: set[str]):
        """Set tags that are currently downloading."""
        self._active_downloads = set(active_tags)

    def _clear_layout(self, layout):
        """Remove all widgets/items from a layout."""
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _build_sort_options(self):
        """Populate the sort selector."""
        self._sort_combo.blockSignals(True)
        self._sort_combo.clear()
        self._sort_combo.addItem("Installed first", "installed_first")
        self._sort_combo.addItem("Size: small → large", "size_asc")
        self._sort_combo.addItem("Size: large → small", "size_desc")
        self._sort_combo.addItem("Name: A → Z", "name_asc")
        self._sort_combo.addItem("Name: Z → A", "name_desc")

        index = self._sort_combo.findData(self._sort_mode)
        self._sort_combo.setCurrentIndex(index if index >= 0 else 0)
        self._sort_combo.blockSignals(False)

    def _refresh_capability_filters(self):
        """Rebuild the top filter chips from the current catalog."""
        capabilities = self._catalog.get_capabilities()
        desired_keys = ["all"] + [cap.lower() for cap in capabilities]
        if list(self._filter_buttons.keys()) == desired_keys:
            return

        current_filter = self._active_filter

        self._clear_layout(self._filters_layout)
        self._filter_buttons.clear()

        for cap in ["All"] + capabilities:
            btn = QPushButton(cap.capitalize())
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(32)
            btn.clicked.connect(lambda checked, c=cap: self._set_filter(c))
            self._filter_buttons[cap.lower()] = btn
            self._filters_layout.addWidget(btn)

        self._filters_layout.addStretch()

        if current_filter not in self._filter_buttons:
            self._active_filter = "all"

        self._update_filter_styles()

    def _on_sort_changed(self, index: int):
        """Handle sort selection changes."""
        mode = self._sort_combo.itemData(index)
        if mode:
            self._sort_mode = mode
            self.refresh()

    def _sort_models(self, models: list[dict]) -> list[dict]:
        """Return models ordered by the selected sort mode."""
        if self._sort_mode == "size_asc":
            return sorted(models, key=lambda model: (model.get("size_gb", 0), model.get("name", "").lower(), model.get("tag", "").lower()))
        if self._sort_mode == "size_desc":
            return sorted(models, key=lambda model: (model.get("size_gb", 0), model.get("name", "").lower(), model.get("tag", "").lower()), reverse=True)
        if self._sort_mode == "name_desc":
            return sorted(models, key=lambda model: (model.get("name", "").lower(), model.get("tag", "").lower()), reverse=True)
        if self._sort_mode == "name_asc":
            return sorted(models, key=lambda model: (model.get("name", "").lower(), model.get("tag", "").lower()))

        def installed_first_key(model: dict):
            tag = model.get("tag", "")
            is_installed = bool(model.get("is_installed"))
            is_working = tag in self._active_downloads or tag in self._paused_states
            group = 0 if is_installed else 1 if is_working else 2
            return (group, model.get("name", "").lower(), tag.lower())

        return sorted(models, key=installed_first_key)

    def refresh(self):
        """Refresh the model grid."""
        self._refresh_capability_filters()

        # Update storage info
        disk_free = self._monitor.get_available_disk_gb()
        self._storage_label.setText(f"{disk_free:.1f} GB free")

        if disk_free < 10:
            self._warning_bar.setVisible(True)
            self._warning_text.setText(
                f"Only {disk_free:.1f} GB free. You need at least 10 GB to install models. "
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

        # Also check installed image-gen models
        from app.services.imagegen_download import is_imagegen_model_installed
        for cat_model in self._catalog.get_imagegen_models():
            tag = cat_model.get("tag", "")
            if tag and is_imagegen_model_installed(tag):
                installed_tags.append(tag)

        # Filter models
        ram_total = self._monitor.get_available_ram_gb()
        models = self._catalog.filter_models(
            capability=self._active_filter,
            search_query=self._search.text() if self._search.text() else None,
            available_disk_gb=disk_free,
            available_ram_gb=ram_total,
            installed_tags=installed_tags,
        )

        for model in models:
            tag = model.get("tag", "")
            model["is_pulling"] = tag in self._active_downloads or tag in self._paused_states

        models = self._sort_models(models)

        # Clear existing cards
        self._clear_grid()

        # Add cards
        cols = 2
        for i, model in enumerate(models):
            # Inject paused state if applicable
            tag = model.get("tag", "")
            if tag in self._active_downloads and not model.get("is_installed"):
                card = ModelCard(model)
                card.install_requested.connect(self.install_requested.emit)
                card.open_requested.connect(self.open_chat_requested.emit)
                card.delete_requested.connect(self.delete_requested.emit)
                card.pause_requested.connect(self.pause_requested.emit)
                card.set_downloading()
            elif not model.get("is_installed") and tag in self._paused_states:
                state = self._paused_states[tag]
                model["is_paused"] = True
                model["paused_progress_pct"] = state.get("progress_pct", 0)
                card = ModelCard(model)
                card.install_requested.connect(self.install_requested.emit)
                card.open_requested.connect(self.open_chat_requested.emit)
                card.delete_requested.connect(self.delete_requested.emit)
                card.pause_requested.connect(self.pause_requested.emit)
            else:
                card = ModelCard(model)
                card.install_requested.connect(self.install_requested.emit)
                card.open_requested.connect(self.open_chat_requested.emit)
                card.delete_requested.connect(self.delete_requested.emit)
                card.pause_requested.connect(self.pause_requested.emit)
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
            color = get_tag_color(key) if key != "all" else COLORS.accent_secondary
            if key == self._active_filter:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {color};
                        color: {COLORS.text_on_accent};
                        border: none;
                        border-radius: 16px;
                        padding: 5px 16px;
                        font-size: 12px;
                        font-weight: 700;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {color}26;
                        color: {COLORS.text_primary};
                        border: 1px solid {color}66;
                        border-radius: 16px;
                        padding: 5px 16px;
                        font-size: 12px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background: {color}3a;
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
