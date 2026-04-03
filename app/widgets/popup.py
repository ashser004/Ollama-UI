"""
popup.py — Reusable popup / toast notifications, shutdown dialog, cache cleanup dialog.
"""

import os
import time

from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                                QPushButton, QGraphicsOpacityEffect, QProgressBar)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal, QThread
from PySide6.QtGui import QFont

from app.theme import COLORS


class ToastNotification(QWidget):
    """Animated toast notification that auto-dismisses."""

    def __init__(self, message: str, toast_type: str = "info",
                 duration_ms: int = 4000, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setFixedWidth(400)

        # Colors by type
        type_colors = {
            "info": COLORS.info,
            "success": COLORS.success,
            "warning": COLORS.warning,
            "error": COLORS.error,
        }
        color = type_colors.get(toast_type, COLORS.info)

        # Icons by type
        type_icons = {
            "info": "i",
            "success": "✓",
            "warning": "!",
            "error": "✕",
        }
        icon = type_icons.get(toast_type, "i")

        # Human-readable title by type
        type_titles = {
            "info": "Info",
            "success": "Success",
            "warning": "Warning",
            "error": "Error",
        }
        title = type_titles.get(toast_type, "Info")

        # Container
        shadow_host = QWidget()
        shadow_host.setObjectName("toastCard")
        shadow_host.setStyleSheet(f"""
            QWidget#toastCard {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
            }}
        """)

        layout = QHBoxLayout(shadow_host)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        accent_badge = QWidget()
        accent_badge.setObjectName("toastBadge")
        accent_badge.setFixedSize(40, 40)
        accent_badge.setStyleSheet(f"""
            QWidget#toastBadge {{
                background-color: {color}22;
                border: 1px solid {color}66;
                border-radius: 20px;
            }}
        """)
        badge_layout = QVBoxLayout(accent_badge)
        badge_layout.setContentsMargins(0, 0, 0, 0)
        badge_layout.setAlignment(Qt.AlignCenter)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"font-size: 16px; font-weight: 900; color: {color}; background: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)
        badge_layout.addWidget(icon_label)
        layout.addWidget(accent_badge)

        text_column = QWidget()
        text_column.setObjectName("toastTextColumn")
        text_column.setAutoFillBackground(False)
        text_column.setAttribute(Qt.WA_StyledBackground, False)
        text_column.setStyleSheet("background-color: transparent; border: none;")
        text_layout = QVBoxLayout(text_column)
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title_label = QLabel(title)
        title_label.setObjectName("toastTitle")
        title_label.setStyleSheet(f"""
            QLabel#toastTitle {{
                color: {color};
                font-size: 12px;
                font-weight: 800;
                letter-spacing: 0.4px;
                background-color: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setObjectName("toastMessage")
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"""
            QLabel#toastMessage {{
                color: {COLORS.text_primary};
                font-size: 13px;
                background-color: transparent;
                border: none;
            }}
        """)
        text_layout.addWidget(msg_label)
        layout.addWidget(text_column, 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(shadow_host)

        # Opacity effect for fade animation
        self._opacity = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity)
        self._opacity.setOpacity(0)

        # Auto dismiss
        QTimer.singleShot(100, self._fade_in)
        QTimer.singleShot(duration_ms, self._fade_out)

    def _fade_in(self):
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(0)
        anim.setEndValue(1)
        anim.setEasingCurve(QEasingCurve.OutCubic)
        anim.start()

    def _fade_out(self):
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(300)
        anim.setStartValue(1)
        anim.setEndValue(0)
        anim.setEasingCurve(QEasingCurve.InCubic)
        anim.finished.connect(self.close)
        anim.finished.connect(self.deleteLater)
        anim.start()

    def show_at(self, parent_widget: QWidget):
        """Show toast horizontally centered, 20% up from bottom of parent."""
        if not parent_widget:
            return

        if not parent_widget.isVisible() or parent_widget.isMinimized():
            return

        self.setParent(parent_widget)

        self.adjustSize()  # Ensure widget computes its height

        x = (parent_widget.width() - self.width()) // 2
        y = int(parent_widget.height() * 0.8)
        self.move(x, y)
        self.raise_()
        self.show()


class ConfirmDialog(QWidget):
    """Modal confirmation popup."""

    def __init__(self, title: str, message: str, on_confirm=None,
                 on_cancel=None, confirm_text="Confirm", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 200)
        self._on_confirm = on_confirm
        self._on_cancel = on_cancel

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"""
            font-size: 16px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(title_label)

        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;")
        layout.addWidget(msg_label)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                padding: 8px 20px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        cancel_btn.clicked.connect(self._cancel)
        btn_layout.addWidget(cancel_btn)

        confirm_btn = QPushButton(confirm_text)
        confirm_btn.setCursor(Qt.PointingHandCursor)
        confirm_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.error};
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: #ef4444;
            }}
        """)
        confirm_btn.clicked.connect(self._confirm)
        btn_layout.addWidget(confirm_btn)

        layout.addLayout(btn_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _confirm(self):
        if self._on_confirm:
            self._on_confirm()
        self.close()
        self.deleteLater()

    def _cancel(self):
        if self._on_cancel:
            self._on_cancel()
        self.close()
        self.deleteLater()

    def show_centered(self, parent_widget: QWidget = None):
        """Show popup centered on parent."""
        if parent_widget:
            geo = parent_widget.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        self.show()


# ─────────────────────────────────────────────────────────────
# Shutdown Dialog
# ─────────────────────────────────────────────────────────────

class ShutdownDialog(QWidget):
    """Non-closable modal popup showing graceful shutdown progress."""

    shutdown_complete = Signal()

    def __init__(self, tasks: list[str], parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(440, min(200 + len(tasks) * 36, 380))

        self._status_icons: list[QLabel] = []
        self._task_labels: list[QLabel] = []
        self._completed = 0
        self._total = len(tasks)

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(10)

        title = QLabel("Closing safely...")
        title.setStyleSheet(f"""
            font-size: 18px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(title)

        subtitle = QLabel("Please wait while processes are being stopped")
        subtitle.setStyleSheet(
            f"color: {COLORS.text_secondary}; font-size: 12px; background: transparent;"
        )
        layout.addWidget(subtitle)

        layout.addSpacing(8)

        for task_name in tasks:
            row = QHBoxLayout()
            row.setSpacing(10)

            icon = QLabel("◦")
            icon.setFixedWidth(20)
            icon.setAlignment(Qt.AlignCenter)
            icon.setStyleSheet(
                f"font-size: 14px; color: {COLORS.text_muted}; background: transparent;"
            )
            row.addWidget(icon)
            self._status_icons.append(icon)

            label = QLabel(task_name)
            label.setStyleSheet(
                f"color: {COLORS.text_muted}; font-size: 13px; background: transparent;"
            )
            row.addWidget(label, 1)
            self._task_labels.append(label)

            layout.addLayout(row)

        layout.addStretch()

        # Animated dots
        self._dots_label = QLabel("●○○")
        self._dots_label.setAlignment(Qt.AlignCenter)
        self._dots_label.setStyleSheet(
            f"color: {COLORS.accent_primary}; font-size: 16px; "
            f"background: transparent; letter-spacing: 4px;"
        )
        layout.addWidget(self._dots_label)

        self._dot_idx = 0
        self._dot_timer = QTimer(self)
        self._dot_timer.timeout.connect(self._animate_dots)
        self._dot_timer.start(350)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

    def _animate_dots(self):
        self._dot_idx = (self._dot_idx + 1) % 3
        dots = ""
        for i in range(3):
            dots += "●" if i == self._dot_idx else "○"
        self._dots_label.setText(dots)

    def mark_task_active(self, index: int):
        """Mark a task as currently being stopped."""
        if 0 <= index < self._total:
            self._status_icons[index].setText("⏳")
            self._status_icons[index].setStyleSheet(
                f"font-size: 14px; color: {COLORS.warning}; background: transparent;"
            )
            self._task_labels[index].setStyleSheet(
                f"color: {COLORS.text_primary}; font-size: 13px; "
                f"font-weight: 600; background: transparent;"
            )

    def mark_task_done(self, index: int):
        """Mark a task as completed."""
        if 0 <= index < self._total:
            self._status_icons[index].setText("✓")
            self._status_icons[index].setStyleSheet(
                f"font-size: 14px; color: {COLORS.success}; background: transparent;"
            )
            self._task_labels[index].setStyleSheet(
                f"color: {COLORS.success}; font-size: 13px; background: transparent;"
            )
            self._completed += 1

            if self._completed >= self._total:
                self._dot_timer.stop()
                self._dots_label.setText("✓")
                self._dots_label.setStyleSheet(
                    f"color: {COLORS.success}; font-size: 18px; "
                    f"font-weight: 700; background: transparent;"
                )
                QTimer.singleShot(600, self.shutdown_complete.emit)

    def show_centered(self, parent_widget=None):
        if parent_widget:
            geo = parent_widget.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        self.show()


# ─────────────────────────────────────────────────────────────
# Cache Cleanup Dialog
# ─────────────────────────────────────────────────────────────

class _CacheCleanupWorker(QThread):
    """Background worker for cache scan and cleanup."""
    scan_status = Signal(str)
    scan_complete = Signal(int, int)      # count, total_bytes
    cleanup_progress = Signal(int, int)   # current, total
    cleanup_complete = Signal(int, int)   # removed_count, freed_bytes

    def __init__(self, aiui_path: str, parent=None):
        super().__init__(parent)
        self._aiui_path = aiui_path

    def run(self):
        files = []

        # Scan ollama dir
        ollama_dir = os.path.join(self._aiui_path, "ollama")
        if os.path.isdir(ollama_dir):
            self.scan_status.emit("Scanning ollama directory...")
            time.sleep(0.35)
            for name in os.listdir(ollama_dir):
                path = os.path.join(ollama_dir, name)
                if os.path.isfile(path):
                    ext = os.path.splitext(name)[1].lower()
                    if ext in (".zip", ".partial", ".tmp"):
                        try:
                            files.append((path, os.path.getsize(path)))
                        except OSError:
                            pass

        # Scan models dir
        models_dir = os.path.join(self._aiui_path, "models")
        if os.path.isdir(models_dir):
            self.scan_status.emit("Scanning models directory...")
            time.sleep(0.35)
            for root, _, fnames in os.walk(models_dir):
                for name in fnames:
                    if name.endswith(".partial") or name.endswith(".tmp"):
                        path = os.path.join(root, name)
                        try:
                            files.append((path, os.path.getsize(path)))
                        except OSError:
                            pass

        # Scan data dir
        data_dir = os.path.join(self._aiui_path, "data")
        if os.path.isdir(data_dir):
            self.scan_status.emit("Scanning data directory...")
            time.sleep(0.35)
            for root, _, fnames in os.walk(data_dir):
                for name in fnames:
                    if name.endswith(".tmp"):
                        path = os.path.join(root, name)
                        try:
                            files.append((path, os.path.getsize(path)))
                        except OSError:
                            pass

        total_size = sum(s for _, s in files)
        self.scan_complete.emit(len(files), total_size)

        if not files:
            self.cleanup_complete.emit(0, 0)
            return

        time.sleep(0.5)

        # Delete files
        freed = 0
        removed = 0
        for i, (path, size) in enumerate(files):
            try:
                os.remove(path)
                freed += size
                removed += 1
            except OSError:
                pass
            self.cleanup_progress.emit(i + 1, len(files))
            time.sleep(0.08)

        self.cleanup_complete.emit(removed, freed)


class CacheCleanupDialog(QWidget):
    """Modal dialog for cache scanning and cleanup with animated progress."""

    cache_cleared = Signal()

    def __init__(self, aiui_path: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 280)
        self._worker = None

        container = QWidget()
        container.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
            }}
        """)

        layout = QVBoxLayout(container)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        title = QLabel("Clear Cache")
        title.setStyleSheet(f"""
            font-size: 18px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        layout.addWidget(title)

        self._status_label = QLabel("Starting scan...")
        self._status_label.setWordWrap(True)
        self._status_label.setStyleSheet(
            f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;"
        )
        layout.addWidget(self._status_label)

        layout.addSpacing(4)

        self._progress = QProgressBar()
        self._progress.setFixedHeight(12)
        self._progress.setRange(0, 0)  # indeterminate initially
        layout.addWidget(self._progress)

        self._detail_label = QLabel("")
        self._detail_label.setStyleSheet(
            f"color: {COLORS.text_muted}; font-size: 11px; background: transparent;"
        )
        self._detail_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._detail_label)

        layout.addStretch()

        # Result area (hidden initially)
        self._result_label = QLabel("")
        self._result_label.setWordWrap(True)
        self._result_label.setAlignment(Qt.AlignCenter)
        self._result_label.setVisible(False)
        self._result_label.setStyleSheet(
            f"color: {COLORS.success}; font-size: 14px; "
            f"font-weight: 600; background: transparent;"
        )
        layout.addWidget(self._result_label)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.setCursor(Qt.PointingHandCursor)
        self._close_btn.setFixedSize(80, 34)
        self._close_btn.setVisible(False)
        self._close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 8px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                color: {COLORS.text_primary};
            }}
        """)
        self._close_btn.clicked.connect(self._on_close)
        btn_layout.addWidget(self._close_btn)
        layout.addLayout(btn_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(container)

        # Start
        self._worker = _CacheCleanupWorker(aiui_path, self)
        self._worker.scan_status.connect(self._on_scan_status)
        self._worker.scan_complete.connect(self._on_scan_complete)
        self._worker.cleanup_progress.connect(self._on_cleanup_progress)
        self._worker.cleanup_complete.connect(self._on_cleanup_complete)
        QTimer.singleShot(300, self._worker.start)

    def _on_scan_status(self, text):
        self._status_label.setText(text)

    def _on_scan_complete(self, count, total_bytes):
        if count == 0:
            self._status_label.setText("No cache files found")
            self._detail_label.setText("Your storage is already clean!")
        else:
            mb = total_bytes / (1024 * 1024)
            self._status_label.setText(f"Found {count} file{'s' if count != 1 else ''} ({mb:.1f} MB)")
            self._detail_label.setText("Removing files...")
            self._progress.setRange(0, count)
            self._progress.setValue(0)

    def _on_cleanup_progress(self, current, total):
        self._progress.setValue(current)
        self._detail_label.setText(f"Removing {current}/{total}...")

    def _on_cleanup_complete(self, removed, freed):
        self._progress.setVisible(False)
        self._detail_label.setVisible(False)
        self._result_label.setVisible(True)
        self._close_btn.setVisible(True)

        if removed == 0:
            self._result_label.setText("✓  No cache files found\nYour storage is already clean!")
            self._result_label.setStyleSheet(
                f"color: {COLORS.success}; font-size: 14px; "
                f"font-weight: 600; background: transparent;"
            )
        else:
            mb = freed / (1024 * 1024)
            self._status_label.setText("Cache cleared successfully!")
            self._status_label.setStyleSheet(
                f"color: {COLORS.success}; font-size: 14px; "
                f"font-weight: 600; background: transparent;"
            )
            self._result_label.setText(
                f"Removed {removed} file{'s' if removed != 1 else ''}\n"
                f"Freed {mb:.1f} MB of disk space"
            )
            self._result_label.setStyleSheet(
                f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent;"
            )

        self.cache_cleared.emit()

    def _on_close(self):
        self.close()
        self.deleteLater()

    def show_centered(self, parent_widget=None):
        if parent_widget:
            geo = parent_widget.geometry()
            x = geo.x() + (geo.width() - self.width()) // 2
            y = geo.y() + (geo.height() - self.height()) // 2
            self.move(x, y)
        self.show()
