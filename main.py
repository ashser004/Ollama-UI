"""
main.py — Local AI(UI) entry point.

Initializes the application, manages page navigation, and
coordinates all major components.
"""

import sys
import atexit
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                                QHBoxLayout, QVBoxLayout, QStackedWidget,
                                QMessageBox)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon

from app import config
from app import database as db
from app.theme import get_stylesheet, COLORS
from app.ollama.manager import OllamaManager
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog
from app.services.system_monitor import SystemMonitor
from app.widgets.sidebar import Sidebar
from app.widgets.status_bar import StatusBar
from app.widgets.popup import ToastNotification
from app.pages.setup_page import SetupPage
from app.pages.home_page import HomePage
from app.pages.discover_page import DiscoverPage
from app.pages.chat_page import ChatPage
from app.pages.manage_page import ManagePage
from app.pages.logs_page import LogsPage
from app.pages.about_page import AboutPage


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(config.APP_NAME)
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)

        # ─── Core services ────────────────────────
        self._ollama_manager = OllamaManager(self)
        self._api = OllamaAPI()
        self._catalog = ModelCatalog()
        self._monitor = SystemMonitor(parent=self)

        # Active model downloads: tag -> PullWorker
        self._active_pulls: dict = {}

        # ─── Central widget ───────────────────────
        central = QWidget()
        self.setCentralWidget(central)

        # Root layout (wraps everything)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Main content area (sidebar + pages)
        self._content_area = QWidget()
        content_layout = QHBoxLayout(self._content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # Sidebar
        self._sidebar = Sidebar()
        self._sidebar.page_changed.connect(self._on_page_changed)
        self._sidebar.setVisible(False)  # hidden during setup
        content_layout.addWidget(self._sidebar)

        # Page stack
        self._pages = QStackedWidget()
        content_layout.addWidget(self._pages, 1)

        root_layout.addWidget(self._content_area, 1)

        # Status bar
        self._status_bar = StatusBar()
        self._status_bar.setVisible(False)  # hidden during setup
        root_layout.addWidget(self._status_bar)

        # ─── Pages ────────────────────────────────

        # Setup page (shown on first launch)
        self._setup_page = SetupPage(self._ollama_manager)
        self._setup_page.setup_complete.connect(self._on_setup_complete)
        self._pages.addWidget(self._setup_page)

        # Home
        self._home_page = HomePage(self._api, self._monitor)
        self._home_page.navigate_to.connect(self._navigate)
        self._home_page.open_chat.connect(self._open_chat_model)
        self._home_page.open_chat_conv.connect(self._open_chat_conv)
        self._pages.addWidget(self._home_page)

        # Discover
        self._discover_page = DiscoverPage(self._api, self._catalog, self._monitor)
        self._discover_page.install_requested.connect(self._install_model)
        self._discover_page.open_chat_requested.connect(
            lambda m: self._open_chat_model(m.get("tag", ""))
        )
        self._discover_page.delete_requested.connect(self._delete_model)
        self._pages.addWidget(self._discover_page)

        # Chat
        self._chat_page = ChatPage(self._api, self._catalog)
        self._chat_page.back_requested.connect(lambda: self._navigate("home"))
        self._chat_page.navigate_to_discover.connect(lambda: self._navigate("discover"))
        self._pages.addWidget(self._chat_page)

        # Manage
        self._manage_page = ManagePage(self._api, self._catalog)
        self._manage_page.open_chat_requested.connect(self._open_chat_model)
        self._manage_page.model_deleted.connect(self._on_model_deleted)
        self._pages.addWidget(self._manage_page)

        # Logs
        self._logs_page = LogsPage()
        self._pages.addWidget(self._logs_page)

        # About
        self._about_page = AboutPage()
        self._pages.addWidget(self._about_page)

        # Page map for navigation
        self._page_map = {
            "home": self._home_page,
            "discover": self._discover_page,
            "chat": self._chat_page,
            "manage": self._manage_page,
            "logs": self._logs_page,
            "about": self._about_page,
        }

        # ─── Signal connections ───────────────────
        self._monitor.stats_updated.connect(self._status_bar.update_stats)
        self._monitor.disk_warning.connect(lambda msg: self._show_toast(msg, "warning"))
        self._monitor.ram_warning.connect(lambda msg: self._show_toast(msg, "warning"))
        self._ollama_manager.server_started.connect(self._on_server_started)
        self._ollama_manager.server_stopped.connect(
            lambda: self._status_bar.update_ollama_status(False)
        )
        self._ollama_manager.server_error.connect(
            lambda msg: self._show_toast(msg, "error")
        )
        self._ollama_manager.health_status.connect(
            self._status_bar.update_ollama_status
        )

        # ─── Initialize ──────────────────────────
        self._decide_initial_page()

    def _decide_initial_page(self):
        """Show setup or home based on state."""
        if config.is_first_launch() or not config.is_ollama_installed():
            self._pages.setCurrentWidget(self._setup_page)
        else:
            self._show_main_app()

    def _show_main_app(self):
        """Switch to the main app interface."""
        # Initialize database
        db.init_db()

        # Clean up any partial downloads from previous interrupted sessions
        self._ollama_manager.cleanup_partial_downloads()

        # Show sidebar and status bar
        self._sidebar.setVisible(True)
        self._status_bar.setVisible(True)

        # Start system monitor
        self._monitor.start()

        # Start Ollama server
        self._ollama_manager.start_server()

        # Update API base URL with correct port
        self._api.base_url = self._ollama_manager.base_url

        # Navigate to home
        self._pages.setCurrentWidget(self._home_page)
        self._home_page.refresh()

    @Slot()
    def _on_setup_complete(self):
        """Setup wizard finished."""
        self._show_toast("Setup complete! Welcome to Local AI(UI)!", "success")
        self._show_main_app()

    @Slot()
    def _on_server_started(self):
        """Ollama server is ready."""
        self._status_bar.update_ollama_status(True)
        self._api.base_url = self._ollama_manager.base_url
        self._show_toast("Ollama server is running", "success")

        # Refresh current page
        current = self._pages.currentWidget()
        if hasattr(current, 'refresh'):
            current.refresh()

    @Slot(str)
    def _on_page_changed(self, page_key: str):
        """Handle sidebar navigation."""
        self._navigate(page_key)

    def _navigate(self, page_key: str):
        """Navigate to a page."""
        page = self._page_map.get(page_key)
        if page:
            self._pages.setCurrentWidget(page)
            self._sidebar.set_page(page_key)
            if hasattr(page, 'refresh'):
                page.refresh()
            if page_key == "chat":
                self._chat_page.load_models()
            if page_key == "discover":
                self._reconnect_active_downloads()

    def _open_chat_model(self, model_name: str):
        """Open chat with a specific model."""
        self._navigate("chat")
        self._chat_page.load_models()
        self._chat_page.start_new_chat(model_name)

    def _open_chat_conv(self, conv_id: int):
        """Open a specific conversation."""
        self._navigate("chat")
        self._chat_page.load_models()
        self._chat_page.open_conversation(conv_id)

    def _install_model(self, model: dict):
        """Install a model from the catalog."""
        tag = model.get("tag", "")
        size_gb = model.get("size_gb", 0)
        min_ram = model.get("min_ram_gb", 0)

        # Already downloading?
        if tag in self._active_pulls:
            self._show_toast(f"{model.get('name', tag)} is already downloading", "info")
            return

        # Check compatibility
        can_install, reason = self._monitor.can_install_model(size_gb, min_ram)
        if not can_install:
            self._show_toast(reason, "error")
            return

        self._show_toast(f"Installing {model.get('name', tag)}...", "info")

        # Start pull
        worker = self._api.pull_model(tag)

        # Track the active download
        self._active_pulls[tag] = worker

        # Connect to current card (may be None if page not visible)
        card = self._discover_page.get_card_by_tag(tag)
        if card:
            worker.progress.connect(card.update_progress)
            worker.finished_signal.connect(card.install_finished)

        worker.finished_signal.connect(
            lambda success, msg: self._on_model_installed(success, msg, model)
        )
        worker.start()

    def _reconnect_active_downloads(self):
        """Reconnect active download workers to newly created cards."""
        for tag, worker in list(self._active_pulls.items()):
            if not worker.isRunning():
                # Worker finished while we were away — clean up
                del self._active_pulls[tag]
                continue
            card = self._discover_page.get_card_by_tag(tag)
            if card:
                # Connect signals to the new card
                worker.progress.connect(card.update_progress)
                worker.finished_signal.connect(card.install_finished)
                # Set the card into downloading state immediately
                card.set_downloading()

    def _on_model_installed(self, success: bool, message: str, model: dict):
        """Handle model installation completion."""
        tag = model.get("tag", "")
        name = model.get("name", tag)

        # Remove from active pulls
        self._active_pulls.pop(tag, None)

        if success:
            self._show_toast(f"{name} installed successfully!", "success")
            self._log_event(f"Model installed: {name}")
        else:
            self._show_toast(f"Failed to install {name}: {message}", "error")
            self._log_event(f"Model install failed: {name} — {message}")

    def _delete_model(self, model: dict):
        """Delete a model."""
        tag = model.get("tag", "")
        name = model.get("name", tag)
        success, msg = self._api.delete_model(tag)
        if success:
            self._show_toast(f"{name} deleted", "success")
            self._discover_page.refresh()
        else:
            self._show_toast(f"Failed to delete {name}: {msg}", "error")

    def _on_model_deleted(self, name: str):
        """Handle model deletion from manage page."""
        self._show_toast(f"{name} deleted", "success")

    def _show_toast(self, message: str, toast_type: str = "info"):
        """Show a toast notification."""
        toast = ToastNotification(message, toast_type, parent=self)
        toast.show_at(self)

    def _log_event(self, message: str):
        """Log an event to the error log."""
        import time
        log_path = config.get_error_log_path()
        if log_path:
            import os
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")

    def _is_busy_downloading(self) -> bool:
        """Check if any download is currently in progress."""
        if self._ollama_manager.is_downloading:
            return True
        # Check active model pulls
        for tag, worker in list(self._active_pulls.items()):
            if worker.isRunning():
                return True
            else:
                del self._active_pulls[tag]
        return False

    def closeEvent(self, event):
        """Clean shutdown — warn if download is in progress."""
        if self._is_busy_downloading():
            msg = QMessageBox(self)
            msg.setWindowTitle("Download in Progress")
            msg.setText(
                "A download is still in progress.\n\n"
                "Closing now will cancel it and you may need\n"
                "to restart it next time. Continue closing?"
            )
            msg.setIcon(QMessageBox.Warning)
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.setDefaultButton(QMessageBox.No)
            msg.setStyleSheet(f"""
                QMessageBox {{
                    background-color: {COLORS.bg_base};
                }}
                QMessageBox QLabel {{
                    color: {COLORS.text_primary};
                    font-size: 13px;
                }}
                QPushButton {{
                    min-width: 80px;
                }}
            """)

            if msg.exec() == QMessageBox.No:
                event.ignore()
                return

        self._monitor.stop()
        self._ollama_manager.stop_server()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())

    window = MainWindow()
    window.show()

    # Ensure cleanup on exit
    atexit.register(lambda: window._ollama_manager.stop_server()
                    if window._ollama_manager.is_running else None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
