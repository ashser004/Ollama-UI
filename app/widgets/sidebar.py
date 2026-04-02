"""
sidebar.py — Navigation sidebar with collapsible icons.
"""

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                                QLabel, QSizePolicy, QSpacerItem)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCursor

from app.theme import COLORS


class SidebarButton(QPushButton):
    """Individual sidebar navigation button."""

    def __init__(self, icon_text: str, label: str, parent=None):
        super().__init__(parent)
        self._icon_text = icon_text
        self._label_text = label
        self._is_active = False
        self._expanded = True
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setFixedHeight(44)
        self.setFont(QFont("Segoe UI", 13))
        self._update_display()
        self._apply_style()

    def set_active(self, active: bool):
        self._is_active = active
        self._apply_style()

    def set_expanded(self, expanded: bool):
        self._expanded = expanded
        self._update_display()

    def _update_display(self):
        if self._expanded:
            self.setText(f"  {self._icon_text}   {self._label_text}")
            self.setMinimumWidth(200)
        else:
            self.setText(self._icon_text)
            self.setMinimumWidth(56)

    def _apply_style(self):
        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.sidebar_active};
                    color: {COLORS.accent_primary};
                    border: none;
                    border-left: 3px solid {COLORS.accent_primary};
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 16px;
                    font-size: 13px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS.text_secondary};
                    border: none;
                    border-left: 3px solid transparent;
                    border-radius: 0px;
                    text-align: left;
                    padding-left: 16px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS.sidebar_hover};
                    color: {COLORS.text_primary};
                }}
            """)


class Sidebar(QWidget):
    """Main navigation sidebar."""

    page_changed = Signal(str)  # emits page name

    # Navigation items: (icon, label, page_key)
    NAV_ITEMS = [
        ("▣", "Home", "home"),
        ("◈", "Discover", "discover"),
        ("▸", "Chat", "chat"),
        ("◫", "Manage", "manage"),
        ("≡", "Logs", "logs"),
        ("◉", "About", "about"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._buttons: dict[str, SidebarButton] = {}
        self._current_page = "home"

        self.setFixedWidth(220)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.sidebar_bg};
                border-right: 1px solid {COLORS.border_default};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        # App logo / title
        logo_container = QWidget()
        logo_container.setFixedHeight(64)
        logo_container.setStyleSheet("background: transparent;")
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(20, 16, 20, 8)

        self._title_label = QLabel("Local AI(UI)")
        self._title_label.setStyleSheet(f"""
            font-size: 18px;
            font-weight: 800;
            color: {COLORS.accent_primary};
            background: transparent;
        """)
        self._title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logo_layout.addWidget(self._title_label)

        layout.addWidget(logo_container)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Navigation buttons
        for icon, label, key in self.NAV_ITEMS:
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_click(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

        layout.addStretch()

        # Collapse button
        self._collapse_btn = QPushButton("◀  Collapse")
        self._collapse_btn.setFixedHeight(30)
        self._collapse_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS.text_muted};
                border: 1px solid {COLORS.border_default};
                border-radius: 6px;
                font-size: 11px;
                padding: 2px 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        self._collapse_btn.clicked.connect(self._toggle_collapse)

        collapse_container = QWidget()
        collapse_container.setStyleSheet("background: transparent;")
        collapse_layout = QVBoxLayout(collapse_container)
        collapse_layout.setContentsMargins(10, 0, 10, 12)
        collapse_layout.addWidget(self._collapse_btn, alignment=Qt.AlignCenter)
        layout.addWidget(collapse_container)

        # Set initial active
        self._buttons["home"].set_active(True)

    def _on_nav_click(self, page_key: str):
        if page_key == self._current_page:
            return
        # Update active states
        if self._current_page in self._buttons:
            self._buttons[self._current_page].set_active(False)
        self._current_page = page_key
        self._buttons[page_key].set_active(True)
        self.page_changed.emit(page_key)

    def _toggle_collapse(self):
        self._expanded = not self._expanded
        target_width = 220 if self._expanded else 64

        anim = QPropertyAnimation(self, b"minimumWidth", self)
        anim.setDuration(200)
        anim.setEndValue(target_width)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        anim.start()

        anim2 = QPropertyAnimation(self, b"maximumWidth", self)
        anim2.setDuration(200)
        anim2.setEndValue(target_width)
        anim2.setEasingCurve(QEasingCurve.InOutCubic)
        anim2.start()

        for btn in self._buttons.values():
            btn.set_expanded(self._expanded)

        self._collapse_btn.setText("◀  Collapse" if self._expanded else "▶")
        self._title_label.setVisible(self._expanded)

    def set_page(self, page_key: str):
        """Programmatically set the active page."""
        self._on_nav_click(page_key)
