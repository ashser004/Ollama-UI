"""
about_dialog.py — About section showing app info and developer credits.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QDesktopServices, QCursor
from PySide6.QtCore import QUrl

from app.theme import COLORS
from app import config


class AboutView(QWidget):
    """About page showing app version and developer info."""

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(0)

        # Center card
        card = QWidget()
        card.setFixedSize(460, 440)
        card.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 20px;
            }}
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(40, 36, 40, 36)
        card_layout.setSpacing(8)
        card_layout.setAlignment(Qt.AlignCenter)

        # App icon
        icon = QLabel("🧠")
        icon.setFont(QFont("Segoe UI Emoji", 48))
        icon.setAlignment(Qt.AlignCenter)
        icon.setStyleSheet("background: transparent;")
        card_layout.addWidget(icon)

        card_layout.addSpacing(8)

        # App name
        name = QLabel(config.APP_NAME)
        name.setAlignment(Qt.AlignCenter)
        name.setStyleSheet(f"""
            font-size: 26px; font-weight: 800;
            color: {COLORS.text_primary}; background: transparent;
        """)
        card_layout.addWidget(name)

        # Version
        version = QLabel(f"Version {config.APP_VERSION}")
        version.setAlignment(Qt.AlignCenter)
        version.setStyleSheet(f"""
            font-size: 13px; color: {COLORS.text_muted};
            background: transparent;
        """)
        card_layout.addWidget(version)

        card_layout.addSpacing(20)

        # Description
        desc = QLabel(
            "A fully offline AI workspace powered by Ollama.\n"
            "Portable, private, and completely under your control.\n"
            "All data stays in one folder — delete it to remove everything."
        )
        desc.setAlignment(Qt.AlignCenter)
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent; line-height: 1.6;")
        card_layout.addWidget(desc)

        card_layout.addSpacing(20)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS.border_default};")
        card_layout.addWidget(sep)

        card_layout.addSpacing(16)

        # Developer info
        dev_label = QLabel("Developed by")
        dev_label.setAlignment(Qt.AlignCenter)
        dev_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
        card_layout.addWidget(dev_label)

        dev_name = QLabel(config.DEVELOPER)
        dev_name.setAlignment(Qt.AlignCenter)
        dev_name.setStyleSheet(f"""
            font-size: 16px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        card_layout.addWidget(dev_name)

        card_layout.addSpacing(12)

        # GitHub button
        github_btn = QPushButton("⭐  View on GitHub")
        github_btn.setCursor(QCursor(Qt.PointingHandCursor))
        github_btn.setFixedHeight(40)
        github_btn.setFixedWidth(200)
        github_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                border-color: {COLORS.accent_primary}44;
            }}
        """)
        github_btn.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(config.DEVELOPER_GITHUB))
        )
        card_layout.addWidget(github_btn, alignment=Qt.AlignCenter)

        layout.addWidget(card, alignment=Qt.AlignCenter)
