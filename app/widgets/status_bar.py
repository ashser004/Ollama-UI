"""
status_bar.py — Bottom status bar showing system resources.
"""

from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt, Slot

from app.theme import COLORS


class StatusBar(QWidget):
    """Bottom status bar showing CPU, RAM, disk, and Ollama status."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_darkest};
                border-top: 1px solid {COLORS.border_default};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)
        layout.setSpacing(20)

        # Ollama status
        self._ollama_dot = QLabel("●")
        self._ollama_dot.setFixedWidth(12)
        self._ollama_dot.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 10px; background: transparent;")
        layout.addWidget(self._ollama_dot)

        self._ollama_label = QLabel("Ollama: Offline")
        self._ollama_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
        layout.addWidget(self._ollama_label)

        self._add_separator(layout)

        # CPU
        self._cpu_label = QLabel("CPU: --")
        self._cpu_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")
        layout.addWidget(self._cpu_label)

        self._add_separator(layout)

        # RAM
        self._ram_label = QLabel("RAM: --")
        self._ram_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")
        layout.addWidget(self._ram_label)

        self._add_separator(layout)

        # Disk
        self._disk_label = QLabel("Disk: --")
        self._disk_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")
        layout.addWidget(self._disk_label)

        layout.addStretch()

        # App version
        self._version_label = QLabel("v1.0.0")
        self._version_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
        layout.addWidget(self._version_label)

    def _add_separator(self, layout):
        sep = QFrame()
        sep.setFixedSize(2, 14)
        sep.setStyleSheet("""
            QFrame {
                background-color: rgba(56, 189, 248, 120);
                border-radius: 1px;
            }
        """)
        layout.addWidget(sep)

    @Slot(dict)
    def update_stats(self, stats: dict):
        """Update display with new stats."""
        cpu = stats.get("cpu_percent", 0)
        ram_used = stats.get("ram_used_gb", 0)
        ram_total = stats.get("ram_total_gb", 0)
        disk_free = stats.get("disk_free_gb", 0)
        disk_total = stats.get("disk_total_gb", 0)

        self._cpu_label.setText(f"CPU: {cpu:.0f}%")
        self._ram_label.setText(f"RAM: {ram_used:.1f}/{ram_total:.0f} GB")
        self._disk_label.setText(f"Disk: {disk_free:.1f} GB free")

        # Color code based on severity
        if cpu > 80:
            self._cpu_label.setStyleSheet(f"color: {COLORS.error}; font-size: 11px; background: transparent;")
        elif cpu > 60:
            self._cpu_label.setStyleSheet(f"color: {COLORS.warning}; font-size: 11px; background: transparent;")
        else:
            self._cpu_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")

        ram_pct = stats.get("ram_percent", 0)
        if ram_pct > 90:
            self._ram_label.setStyleSheet(f"color: {COLORS.error}; font-size: 11px; background: transparent;")
        elif ram_pct > 70:
            self._ram_label.setStyleSheet(f"color: {COLORS.warning}; font-size: 11px; background: transparent;")
        else:
            self._ram_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")

        if disk_free < 2:
            self._disk_label.setStyleSheet(f"color: {COLORS.error}; font-size: 11px; background: transparent;")
        elif disk_free < 5:
            self._disk_label.setStyleSheet(f"color: {COLORS.warning}; font-size: 11px; background: transparent;")
        else:
            self._disk_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 11px; background: transparent;")

    @Slot(bool)
    def update_ollama_status(self, is_running: bool):
        """Update Ollama server status indicator."""
        if is_running:
            self._ollama_dot.setStyleSheet(f"color: {COLORS.success}; font-size: 10px; background: transparent;")
            self._ollama_label.setText("Ollama: Online")
            self._ollama_label.setStyleSheet(f"color: {COLORS.success}; font-size: 11px; background: transparent;")
        else:
            self._ollama_dot.setStyleSheet(f"color: {COLORS.error}; font-size: 10px; background: transparent;")
            self._ollama_label.setText("Ollama: Offline")
            self._ollama_label.setStyleSheet(f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;")
