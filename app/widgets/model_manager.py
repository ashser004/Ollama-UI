"""
model_manager.py — Installed model management view.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QScrollArea, QFrame)
from PySide6.QtCore import Qt, Signal

from app.theme import COLORS, accent_button_style, danger_button_style, tag_badge_style, get_tag_color
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog


class ModelManager(QWidget):
    """View and manage installed models."""

    open_chat_requested = Signal(str)  # model tag
    model_deleted = Signal(str)  # model tag

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(parent)
        self._api = api
        self._catalog = catalog

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 12)
        layout.setSpacing(16)

        # Header
        title = QLabel("Installed Models")
        title.setStyleSheet(f"""
            font-size: 24px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Manage your downloaded AI models")
        subtitle.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;")
        layout.addWidget(subtitle)

        # Scrollable list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setSpacing(10)
        self._list_layout.setContentsMargins(0, 0, 0, 0)

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, 1)

    def refresh(self):
        """Refresh the installed models list."""
        # Clear
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        models = self._api.list_models()

        if not models:
            empty = QLabel("No models installed yet.\nHead to Discover to find and install models.")
            empty.setAlignment(Qt.AlignCenter)
            empty.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 14px; padding: 60px; background: transparent;")
            self._list_layout.addWidget(empty)
            self._list_layout.addStretch()
            return

        for model_data in models:
            name = model_data.get("name", "Unknown")
            size = model_data.get("size", 0)
            size_gb = size / (1024 ** 3) if size else 0

            # Try to find in catalog for extra info
            base_name = name.split(":")[0]
            catalog_info = self._catalog.get_model_by_tag(base_name) or self._catalog.get_model_by_tag(name)

            row = QFrame()
            row.setFixedHeight(72)
            row.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS.bg_surface};
                    border: 1px solid {COLORS.border_default};
                    border-radius: 12px;
                }}
                QFrame:hover {{
                    border-color: {COLORS.border_hover};
                }}
            """)

            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(18, 10, 18, 10)

            # Model info
            info_layout = QVBoxLayout()
            info_layout.setSpacing(2)

            display_name = catalog_info.get("name", name) if catalog_info else name
            name_label = QLabel(display_name)
            name_label.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {COLORS.text_primary}; background: transparent;")
            info_layout.addWidget(name_label)

            tag_label = QLabel(f"{name}  •  {size_gb:.1f} GB")
            tag_label.setStyleSheet(f"font-size: 11px; color: {COLORS.text_muted}; background: transparent;")
            info_layout.addWidget(tag_label)

            row_layout.addLayout(info_layout, 1)

            # Capability tags
            if catalog_info:
                for cap in catalog_info.get("capabilities", [])[:3]:
                    cap_label = QLabel(cap.capitalize())
                    cap_label.setStyleSheet(tag_badge_style(get_tag_color(cap)))
                    cap_label.setFixedHeight(22)
                    row_layout.addWidget(cap_label)

            row_layout.addSpacing(12)

            # Actions
            chat_btn = QPushButton("Chat")
            chat_btn.setCursor(Qt.PointingHandCursor)
            chat_btn.setFixedSize(72, 32)
            chat_btn.setStyleSheet(accent_button_style())
            chat_btn.clicked.connect(lambda checked, n=name: self.open_chat_requested.emit(n))
            row_layout.addWidget(chat_btn)

            del_btn = QPushButton("Delete")
            del_btn.setCursor(Qt.PointingHandCursor)
            del_btn.setFixedSize(72, 32)
            del_btn.setStyleSheet(danger_button_style())
            del_btn.clicked.connect(lambda checked, n=name: self._delete_model(n))
            row_layout.addWidget(del_btn)

            self._list_layout.addWidget(row)

        self._list_layout.addStretch()

    def _delete_model(self, name: str):
        """Delete a model."""
        success, msg = self._api.delete_model(name)
        if success:
            self.model_deleted.emit(name)
            self.refresh()
