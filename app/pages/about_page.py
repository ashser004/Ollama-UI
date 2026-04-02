"""
about_page.py — About page wrapper.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout

from app.widgets.about_dialog import AboutView


class AboutPage(QWidget):
    """Wraps the AboutView widget as a page."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._about = AboutView()
        layout.addWidget(self._about)
