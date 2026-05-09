# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
about_page.py — About page wrapper and updates view.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QScrollArea
from PySide6.QtCore import Qt, Signal

from app.widgets.about_dialog import AboutView
from app.widgets.update_card import UpdateCard

class AboutPage(QWidget):
    """Wraps the AboutView and UpdateCard inside a scrollable page."""

    toast_requested = Signal(str, str) # message, type

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Container inside scroll area
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        container_layout.setContentsMargins(0, 40, 0, 40)
        container_layout.setSpacing(40)

        # About Card
        self._about = AboutView()
        container_layout.addWidget(self._about, alignment=Qt.AlignCenter)

        # Updates Card
        self._update_card = UpdateCard()
        # Route toast signals from the card up to the page
        self._update_card.toast_requested.connect(self.toast_requested.emit)
        container_layout.addWidget(self._update_card, alignment=Qt.AlignCenter)

        scroll.setWidget(container)
        layout.addWidget(scroll)
