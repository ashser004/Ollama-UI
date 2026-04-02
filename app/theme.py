"""
theme.py — Premium dark theme for Local AI(UI).

Provides a centralized color palette, QSS stylesheet, and helper utilities.
Uses the Fusion style for consistent cross-platform theming.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Colors:
    """Central color palette — single source of truth."""

    # Backgrounds
    bg_darkest: str = "#07070d"
    bg_dark: str = "#0c0c14"
    bg_base: str = "#10101c"
    bg_surface: str = "#16162a"
    bg_elevated: str = "#1c1c38"
    bg_hover: str = "#222248"
    bg_active: str = "#2a2a58"

    # Accents
    accent_primary: str = "#7c5cfc"
    accent_secondary: str = "#5c8afc"
    accent_hover: str = "#9478ff"
    accent_gradient_start: str = "#7c5cfc"
    accent_gradient_end: str = "#5c8afc"

    # Text
    text_primary: str = "#e8e6f0"
    text_secondary: str = "#9996b0"
    text_muted: str = "#6b6880"
    text_on_accent: str = "#ffffff"

    # Borders
    border_default: str = "#1e1e3a"
    border_hover: str = "#2e2e5a"
    border_accent: str = "#7c5cfc"

    # Semantic
    success: str = "#34d399"
    warning: str = "#fbbf24"
    error: str = "#f87171"
    info: str = "#60a5fa"

    # Scrollbar
    scrollbar_bg: str = "#0c0c14"
    scrollbar_handle: str = "#2a2a58"
    scrollbar_hover: str = "#3a3a68"

    # Sidebar
    sidebar_bg: str = "#0a0a16"
    sidebar_hover: str = "#14142a"
    sidebar_active: str = "#1a1a38"

    # Chat
    chat_user_bg: str = "#1e1e50"
    chat_assistant_bg: str = "#16162a"

    # Tags / badges
    tag_coding: str = "#34d399"
    tag_chat: str = "#60a5fa"
    tag_reasoning: str = "#fbbf24"
    tag_vision: str = "#f472b6"
    tag_math: str = "#a78bfa"
    tag_embedding: str = "#94a3b8"


COLORS = Colors()

# ─── Tag color helper ─────────────────────────────────────────

TAG_COLORS = {
    "coding": COLORS.tag_coding,
    "chat": COLORS.tag_chat,
    "reasoning": COLORS.tag_reasoning,
    "vision": COLORS.tag_vision,
    "math": COLORS.tag_math,
    "embedding": COLORS.tag_embedding,
}


def get_tag_color(tag: str) -> str:
    return TAG_COLORS.get(tag.lower(), COLORS.text_muted)


# ─── Master QSS stylesheet ───────────────────────────────────

def get_stylesheet() -> str:
    c = COLORS
    return f"""
    /* ─── Global ─────────────────────────────────── */
    QWidget {{
        background-color: {c.bg_base};
        color: {c.text_primary};
        font-family: 'Segoe UI', 'Inter', 'Roboto', sans-serif;
        font-size: 13px;
        border: none;
    }}

    QMainWindow {{
        background-color: {c.bg_darkest};
    }}

    /* ─── Labels ─────────────────────────────────── */
    QLabel {{
        background-color: transparent;
        padding: 0px;
    }}

    /* ─── Buttons ────────────────────────────────── */
    QPushButton {{
        background-color: {c.bg_elevated};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 8px;
        padding: 8px 20px;
        font-weight: 500;
        min-height: 18px;
    }}
    QPushButton:hover {{
        background-color: {c.bg_hover};
        border-color: {c.border_hover};
    }}
    QPushButton:pressed {{
        background-color: {c.bg_active};
    }}
    QPushButton:disabled {{
        color: {c.text_muted};
        background-color: {c.bg_surface};
        border-color: {c.border_default};
    }}

    /* Accent button variant via object name */
    QPushButton#accentBtn {{
        background-color: {c.accent_primary};
        color: {c.text_on_accent};
        border: none;
        font-weight: 600;
    }}
    QPushButton#accentBtn:hover {{
        background-color: {c.accent_hover};
    }}

    /* ─── Line edits / inputs ────────────────────── */
    QLineEdit {{
        background-color: {c.bg_surface};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 8px;
        padding: 8px 14px;
        selection-background-color: {c.accent_primary};
        selection-color: {c.text_on_accent};
    }}
    QLineEdit:focus {{
        border-color: {c.accent_primary};
    }}
    QLineEdit::placeholder {{
        color: {c.text_muted};
    }}

    QTextEdit {{
        background-color: {c.bg_surface};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 8px;
        padding: 8px;
        selection-background-color: {c.accent_primary};
    }}
    QTextEdit:focus {{
        border-color: {c.accent_primary};
    }}

    /* ─── Scroll areas ───────────────────────────── */
    QScrollArea {{
        background-color: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background-color: transparent;
    }}

    /* ─── Scrollbar ──────────────────────────────── */
    QScrollBar:vertical {{
        background: {c.scrollbar_bg};
        width: 8px;
        margin: 0px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {c.scrollbar_handle};
        border-radius: 4px;
        min-height: 30px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c.scrollbar_hover};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: none;
    }}

    QScrollBar:horizontal {{
        background: {c.scrollbar_bg};
        height: 8px;
        margin: 0px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c.scrollbar_handle};
        border-radius: 4px;
        min-width: 30px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {c.scrollbar_hover};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* ─── Progress bars ──────────────────────────── */
    QProgressBar {{
        background-color: {c.bg_surface};
        border: 1px solid {c.border_default};
        border-radius: 6px;
        text-align: center;
        color: {c.text_secondary};
        min-height: 14px;
        max-height: 14px;
        font-size: 10px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
        border-radius: 5px;
    }}

    /* ─── Combo boxes ────────────────────────────── */
    QComboBox {{
        background-color: {c.bg_surface};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 8px;
        padding: 6px 14px;
        min-height: 20px;
    }}
    QComboBox:hover {{
        border-color: {c.border_hover};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 24px;
    }}
    QComboBox QAbstractItemView {{
        background-color: {c.bg_elevated};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        selection-background-color: {c.bg_hover};
        selection-color: {c.text_primary};
        outline: none;
    }}

    /* ─── Tab widget ─────────────────────────────── */
    QTabWidget::pane {{
        border: 1px solid {c.border_default};
        border-radius: 8px;
        background-color: {c.bg_base};
    }}
    QTabBar::tab {{
        background-color: {c.bg_surface};
        color: {c.text_secondary};
        padding: 8px 20px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {c.bg_base};
        color: {c.accent_primary};
        font-weight: 600;
    }}
    QTabBar::tab:hover {{
        color: {c.text_primary};
    }}

    /* ─── Splitter ───────────────────────────────── */
    QSplitter::handle {{
        background-color: {c.border_default};
    }}
    QSplitter::handle:horizontal {{
        width: 1px;
    }}
    QSplitter::handle:vertical {{
        height: 1px;
    }}

    /* ─── Group box ──────────────────────────────── */
    QGroupBox {{
        border: 1px solid {c.border_default};
        border-radius: 8px;
        margin-top: 12px;
        padding-top: 16px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 14px;
        padding: 0 6px;
        color: {c.text_secondary};
    }}

    /* ─── Tool tips ──────────────────────────────── */
    QToolTip {{
        background-color: {c.bg_elevated};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 12px;
    }}

    /* ─── Menu ───────────────────────────────────── */
    QMenu {{
        background-color: {c.bg_elevated};
        color: {c.text_primary};
        border: 1px solid {c.border_default};
        border-radius: 8px;
        padding: 4px;
    }}
    QMenu::item {{
        padding: 6px 24px;
        border-radius: 4px;
    }}
    QMenu::item:selected {{
        background-color: {c.bg_hover};
    }}

    /* ─── Message box ────────────────────────────── */
    QMessageBox {{
        background-color: {c.bg_base};
    }}
    QMessageBox QLabel {{
        color: {c.text_primary};
    }}

    /* ─── Stacked widget ─────────────────────────── */
    QStackedWidget {{
        background-color: transparent;
    }}

    /* ─── Frame ──────────────────────────────────── */
    QFrame {{
        background-color: transparent;
    }}
    """


# ─── Component-level style helpers ────────────────────────────

def card_style() -> str:
    """Style for card-like containers."""
    c = COLORS
    return f"""
        background-color: {c.bg_surface};
        border: 1px solid {c.border_default};
        border-radius: 12px;
        padding: 16px;
    """


def sidebar_style() -> str:
    """Style for the sidebar."""
    c = COLORS
    return f"""
        background-color: {c.sidebar_bg};
        border-right: 1px solid {c.border_default};
    """


def heading_style(size: int = 22) -> str:
    """Style for heading labels."""
    c = COLORS
    return f"""
        font-size: {size}px;
        font-weight: 700;
        color: {c.text_primary};
        background: transparent;
    """


def subheading_style(size: int = 14) -> str:
    """Style for subheading / secondary labels."""
    c = COLORS
    return f"""
        font-size: {size}px;
        color: {c.text_secondary};
        background: transparent;
    """


def accent_button_style() -> str:
    """Style for primary accent buttons."""
    c = COLORS
    return f"""
        QPushButton {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c.accent_gradient_start}, stop:1 {c.accent_gradient_end});
            color: {c.text_on_accent};
            border: none;
            border-radius: 8px;
            padding: 10px 24px;
            font-weight: 600;
            font-size: 13px;
        }}
        QPushButton:hover {{
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {c.accent_hover}, stop:1 {c.accent_secondary});
        }}
        QPushButton:pressed {{
            background: {c.accent_primary};
        }}
        QPushButton:disabled {{
            background: {c.bg_elevated};
            color: {c.text_muted};
        }}
    """


def danger_button_style() -> str:
    """Style for destructive action buttons."""
    c = COLORS
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {c.error};
            border: 1px solid {c.error};
            border-radius: 8px;
            padding: 8px 20px;
            font-weight: 500;
        }}
        QPushButton:hover {{
            background-color: {c.error};
            color: {c.text_on_accent};
        }}
    """


def tag_badge_style(color: str) -> str:
    """Style for capability tag badges."""
    return f"""
        background-color: {color}22;
        color: {color};
        border: 1px solid {color}44;
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 11px;
        font-weight: 600;
    """


def search_bar_style() -> str:
    """Style for search input fields."""
    c = COLORS
    return f"""
        QLineEdit {{
            background-color: {c.bg_surface};
            color: {c.text_primary};
            border: 1px solid {c.border_default};
            border-radius: 20px;
            padding: 10px 20px;
            font-size: 14px;
        }}
        QLineEdit:focus {{
            border-color: {c.accent_primary};
        }}
    """
