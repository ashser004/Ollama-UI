"""
sidebar.py — Navigation sidebar with collapsible icons.
"""

from pathlib import Path

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton,
                                QLabel, QSizePolicy, QSpacerItem,
                                QStackedLayout, QGraphicsOpacityEffect)
from PySide6.QtCore import Qt, Signal, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QCursor, QPixmap

from app.theme import COLORS


class SidebarLogo(QWidget):
    """Animated app logo that swaps between expanded and collapsed assets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._expanded = True
        self._label_path = Path(__file__).resolve().parents[1] / "icon" / "label-icon.png"
        self._collapsed_path = Path(__file__).resolve().parents[1] / "icon" / "icon-ui.png"

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.setSpacing(0)
        self._stack.setStackingMode(QStackedLayout.StackAll)

        self._label_logo = QLabel()
        self._label_logo.setAlignment(Qt.AlignCenter)
        self._label_logo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._label_logo.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._collapsed_logo = QLabel()
        self._collapsed_logo.setAlignment(Qt.AlignCenter)
        self._collapsed_logo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._collapsed_logo.setAttribute(Qt.WA_TransparentForMouseEvents)

        self._label_effect = QGraphicsOpacityEffect(self._label_logo)
        self._label_logo.setGraphicsEffect(self._label_effect)

        self._collapsed_effect = QGraphicsOpacityEffect(self._collapsed_logo)
        self._collapsed_logo.setGraphicsEffect(self._collapsed_effect)

        self._label_effect.setOpacity(1.0)
        self._collapsed_effect.setOpacity(0.0)

        self._label_anim = None
        self._collapsed_anim = None

        self._stack.addWidget(self._label_logo)
        self._stack.addWidget(self._collapsed_logo)
        self._update_pixmaps()

    def set_expanded(self, expanded: bool):
        if self._expanded == expanded:
            return

        self._expanded = expanded
        self._update_pixmaps()
        self._animate_swap()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmaps()

    def _update_pixmaps(self):
        size = self.size()
        if size.width() <= 0 or size.height() <= 0:
            return

        for label, path in ((self._label_logo, self._label_path), (self._collapsed_logo, self._collapsed_path)):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                label.setPixmap(
                    pixmap.scaled(
                        size,
                        Qt.IgnoreAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

    def _animate_swap(self):
        self._label_anim = QPropertyAnimation(self._label_effect, b"opacity", self)
        self._label_anim.setDuration(200)
        self._label_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._label_anim.setStartValue(self._label_effect.opacity())

        self._collapsed_anim = QPropertyAnimation(self._collapsed_effect, b"opacity", self)
        self._collapsed_anim.setDuration(200)
        self._collapsed_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._collapsed_anim.setStartValue(self._collapsed_effect.opacity())

        if self._expanded:
            self._label_anim.setEndValue(1.0)
            self._collapsed_anim.setEndValue(0.0)
        else:
            self._label_anim.setEndValue(0.0)
            self._collapsed_anim.setEndValue(1.0)

        self._label_anim.start()
        self._collapsed_anim.start()


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
        self._apply_style()

    def _update_display(self):
        if self._expanded:
            self.setText(f"  {self._icon_text}   {self._label_text}")
            self.setMinimumWidth(200)
        else:
            self.setText(self._icon_text)
            self.setMinimumWidth(56)

    def _apply_style(self):
        text_align = "left" if self._expanded else "center"
        padding_left = "16px" if self._expanded else "0px"
        margin = "2px 10px" if self._expanded else "2px 4px"

        if self._is_active:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS.sidebar_active};
                    color: {COLORS.accent_primary};
                    border: 1px solid {COLORS.accent_primary};
                    border-radius: 12px;
                    text-align: {text_align};
                    padding-left: {padding_left};
                    margin: {margin};
                    font-size: 13px;
                    font-weight: 600;
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {COLORS.text_secondary};
                    border: 1px solid transparent;
                    border-radius: 12px;
                    text-align: {text_align};
                    padding-left: {padding_left};
                    margin: {margin};
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
        ("⌂", "Home", "home"),
        ("⚲", "Discover", "discover"),
        ("💬", "Chat", "chat"),
        ("⚙", "Manage", "manage"),
        ("≡", "Logs", "logs"),
        ("ℹ", "About", "about"),
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
                border-right: 2px solid {COLORS.border_hover};
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
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setAlignment(Qt.AlignCenter)

        self._logo_widget = SidebarLogo()
        self._logo_widget.setFixedHeight(64)
        self._logo_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        logo_layout.addWidget(self._logo_widget)

        layout.addWidget(logo_container)

        # Separator
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background-color: {COLORS.border_default};")
        layout.addWidget(sep)

        layout.addSpacing(8)

        # Navigation buttons
        for index, (icon, label, key) in enumerate(self.NAV_ITEMS):
            btn = SidebarButton(icon, label)
            btn.clicked.connect(lambda checked, k=key: self._on_nav_click(k))
            self._buttons[key] = btn
            layout.addWidget(btn)

            if index < len(self.NAV_ITEMS) - 1:
                nav_sep = QWidget()
                nav_sep.setFixedHeight(1)
                nav_sep.setStyleSheet("""
                    QWidget {
                        background-color: rgba(56, 189, 248, 90);
                    }
                """)
                layout.addWidget(nav_sep)

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

        self._logo_widget.set_expanded(self._expanded)

        if self._expanded:
            self._collapse_btn.setText("◀  Collapse")
            pad = "2px 12px"
        else:
            self._collapse_btn.setText("▶")
            pad = "2px 5px"

        self._collapse_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {COLORS.text_muted};
                border: 1px solid {COLORS.border_default};
                border-radius: 6px;
                font-size: 11px;
                padding: {pad};
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)

    def set_page(self, page_key: str):
        """Programmatically set the active page."""
        self._on_nav_click(page_key)
