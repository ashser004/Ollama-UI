"""
main.py — Local AI(UI) entry point.

Initializes the application, manages page navigation, and
coordinates all major components.
"""

import sys
import os
import atexit
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget,
                                QHBoxLayout, QVBoxLayout, QStackedWidget,
                                QMessageBox, QSplashScreen)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QIcon, QPixmap

from app import config
from app import database as db
from app.theme import get_stylesheet, COLORS
from app.ollama.manager import OllamaManager
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog
from app.services.system_monitor import SystemMonitor
from app.services import wake_lock
from app.services.download_state import (
    load_states as load_download_states,
    save_states as save_download_states,
    remove_state as remove_download_state,
)
from app.widgets.sidebar import Sidebar
from app.widgets.status_bar import StatusBar
from app.widgets.popup import ToastNotification, ShutdownDialog
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
        self._startup_started = False

        # ─── Core services ────────────────────────
        self._ollama_manager = OllamaManager(self)
        self._api = OllamaAPI()
        self._catalog = ModelCatalog()
        self._monitor = SystemMonitor(parent=self)

        # Active model downloads: tag -> PullWorker
        self._active_pulls: dict = {}

        # Persisted download states (paused/interrupted): tag -> {name, progress_pct, ...}
        self._download_states: dict = {}

        # Real-time progress cache for active downloads: tag -> {pct, completed, total, status}
        self._progress_cache: dict = {}

        # Shutdown state
        self._shutdown_in_progress = False
        self._ready_to_close = False

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
        self._discover_page.pause_requested.connect(self._pause_model)
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
        self._manage_page.cache_cleared.connect(
            lambda: self._show_toast("Cache cleared successfully!", "success")
        )
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

    def begin_startup(self):
        """Run the initial page selection and startup sequence once."""
        if self._startup_started:
            return
        self._startup_started = True
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

        # Load persisted download states
        self._download_states = load_download_states()

        # Show sidebar and status bar
        self._sidebar.setVisible(True)
        self._status_bar.setVisible(True)

        # Start system monitor
        self._monitor.start()

        # Start Ollama server
        self._ollama_manager.start_server()

        # Update API base URL with correct port
        self._api.base_url = self._ollama_manager.base_url

        # Acquire wake lock — keep screen on while app is running
        wake_lock.acquire()

        # Navigate to home
        self._pages.setCurrentWidget(self._home_page)
        # Home refresh happens when the Ollama server reports ready.

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

            if page_key == "discover":
                # Pass paused download states so cards show resume UI
                self._discover_page.set_download_states(self._download_states)
                self._reconnect_active_downloads()

            if hasattr(page, 'refresh'):
                page.refresh()

            if page_key == "chat":
                self._chat_page.load_models()

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

    # ─── Model Install / Pause / Resume ────────────────

    def _install_model(self, model: dict):
        """Install (or resume) a model from the catalog."""
        tag = model.get("tag", "")
        size_gb = model.get("size_gb", 0)
        min_ram = model.get("min_ram_gb", 0)

        # Already downloading?
        if tag in self._active_pulls:
            self._show_toast(f"{model.get('name', tag)} is already downloading", "info")
            return

        # Check compatibility (skip for resumes — already checked first time)
        is_resume = tag in self._download_states
        if not is_resume:
            can_install, reason = self._monitor.can_install_model(size_gb, min_ram)
            if not can_install:
                self._show_toast(reason, "error")
                return

        # Remove from paused states since it's now active
        self._download_states.pop(tag, None)
        save_download_states(self._download_states)

        action = "Resuming" if is_resume else "Installing"
        self._show_toast(f"{action} {model.get('name', tag)}...", "info")

        # Start pull
        worker = self._api.pull_model(tag)

        # Track the active download
        self._active_pulls[tag] = worker

        # Track progress for persistence
        worker.progress.connect(
            lambda c, t, s, _tag=tag: self._on_pull_progress(_tag, c, t, s)
        )

        # Connect to current card (may be None if page not visible)
        card = self._discover_page.get_card_by_tag(tag)
        if card:
            worker.progress.connect(card.update_progress)
            worker.finished_signal.connect(card.install_finished)

        worker.finished_signal.connect(
            lambda success, msg: self._on_model_installed(success, msg, model)
        )
        worker.start()

    def _on_pull_progress(self, tag: str, completed: int, total: int, status: str):
        """Track download progress for persistence."""
        pct = int((completed / total) * 100) if total > 0 else 0
        self._progress_cache[tag] = {
            "progress_pct": pct,
            "completed": completed,
            "total": total,
            "status": status,
        }

    def _pause_model(self, model: dict):
        """Pause an active model download."""
        tag = model.get("tag", "")
        name = model.get("name", tag)

        # Abort the worker
        worker = self._active_pulls.pop(tag, None)
        if worker and worker.isRunning():
            worker.abort()

        # Save progress state
        progress = self._progress_cache.get(tag, {})
        self._download_states[tag] = {
            "name": name,
            "progress_pct": progress.get("progress_pct", 0),
            "completed": progress.get("completed", 0),
            "total": progress.get("total", 0),
            "status": "paused",
        }
        save_download_states(self._download_states)

        self._show_toast(f"{name} download paused", "info")

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

        # Remove from active pulls and progress cache
        self._active_pulls.pop(tag, None)
        self._progress_cache.pop(tag, None)

        # Remove from persisted states (fully done or failed)
        self._download_states.pop(tag, None)
        save_download_states(self._download_states)

        if success:
            self._show_toast(f"{name} installed successfully!", "success")
            self._log_event(f"Model installed: {name}")
        else:
            # If it was cancelled by user (pause), don't show error
            if "Cancelled" not in message:
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

    # ─── UI Helpers ──────────────────────────────────

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

    # ─── Shutdown ────────────────────────────────────

    def _is_busy(self) -> bool:
        """Check if any process is currently running."""
        # Check active model pulls
        for tag, worker in list(self._active_pulls.items()):
            if worker.isRunning():
                return True
            else:
                del self._active_pulls[tag]

        # Check Ollama manager downloading
        if self._ollama_manager.is_downloading:
            return True

        return False

    def _has_running_processes(self) -> list[str]:
        """Get list of currently running process names."""
        tasks = []

        # Active model downloads
        active_downloads = []
        for tag, worker in list(self._active_pulls.items()):
            if worker.isRunning():
                active_downloads.append(tag)
            else:
                del self._active_pulls[tag]
        if active_downloads:
            tasks.append(f"Stopping downloads ({len(active_downloads)})...")

        # Ollama binary download
        if self._ollama_manager.is_downloading:
            tasks.append("Stopping Ollama installation...")

        # Ollama server
        if self._ollama_manager.is_running:
            tasks.append("Stopping Ollama server...")

        return tasks

    def closeEvent(self, event):
        """Clean shutdown — save state, stop processes with UI feedback."""
        # Phase 3: Shutdown completed, actually close the window
        if self._ready_to_close:
            event.accept()
            super().closeEvent(event)
            return

        # Phase 2: Shutdown in progress, ignore repeated close clicks
        if self._shutdown_in_progress:
            event.ignore()
            return

        # Phase 1: Initial close request
        has_active_downloads = self._is_busy()

        if has_active_downloads:
            # Show confirmation dialog first
            msg = QMessageBox(self)
            msg.setWindowTitle("Processes Running")
            msg.setText(
                "Active processes are still running.\n\n"
                "Closing will pause your downloads and they can\n"
                "be resumed next time you open the app.\n\n"
                "Continue closing?"
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

        # Begin shutdown sequence
        event.ignore()
        self._shutdown_in_progress = True

        tasks = self._has_running_processes()

        if tasks:
            # Show the shutdown progress dialog
            self._shutdown_dialog = ShutdownDialog(tasks, parent=None)
            self._shutdown_dialog.shutdown_complete.connect(self._final_close)
            self._shutdown_dialog.show_centered(self)

            # Execute shutdown steps
            self._execute_shutdown(tasks)
        else:
            # No tracked tasks — do a quick direct shutdown
            self._final_close()

    def _execute_shutdown(self, tasks: list[str]):
        """Execute shutdown steps sequentially with UI feedback."""
        self._shutdown_tasks = tasks
        self._shutdown_step = 0
        self._do_next_shutdown_step()

    def _do_next_shutdown_step(self):
        """Process the next shutdown step."""
        if self._shutdown_step >= len(self._shutdown_tasks):
            return

        task = self._shutdown_tasks[self._shutdown_step]
        self._shutdown_dialog.mark_task_active(self._shutdown_step)

        if "downloads" in task.lower():
            # Save progress for all active downloads before aborting
            for tag, worker in list(self._active_pulls.items()):
                progress = self._progress_cache.get(tag, {})
                self._download_states[tag] = {
                    "name": tag,
                    "progress_pct": progress.get("progress_pct", 0),
                    "completed": progress.get("completed", 0),
                    "total": progress.get("total", 0),
                    "status": "paused",
                }
                if worker.isRunning():
                    worker.abort()
            save_download_states(self._download_states)
            self._active_pulls.clear()
            self._shutdown_dialog.mark_task_done(self._shutdown_step)
            self._shutdown_step += 1
            QTimer.singleShot(300, self._do_next_shutdown_step)

        elif "installation" in task.lower():
            self._shutdown_dialog.mark_task_done(self._shutdown_step)
            self._shutdown_step += 1
            QTimer.singleShot(300, self._do_next_shutdown_step)

        elif "server" in task.lower():
            self._monitor.stop()
            self._ollama_manager.stop_server()
            self._shutdown_dialog.mark_task_done(self._shutdown_step)
            self._shutdown_step += 1
            QTimer.singleShot(300, self._do_next_shutdown_step)

    def _final_close(self):
        """Final cleanup and close the application."""
        # Release wake lock
        wake_lock.release()

        # Stop anything still running
        self._monitor.stop()
        if self._ollama_manager.is_running:
            self._ollama_manager.stop_server()

        # Close shutdown dialog if it exists
        if hasattr(self, '_shutdown_dialog') and self._shutdown_dialog:
            self._shutdown_dialog.close()
            self._shutdown_dialog.deleteLater()
            self._shutdown_dialog = None

        # Set flag so closeEvent accepts, then close the window
        self._ready_to_close = True
        self.close()  # triggers closeEvent → accepted → window closes → app exits


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(get_stylesheet())

    app_icon_path = os.path.join(config.get_project_root(), "app", "icon", "icon-ui.png")
    app_icon = QIcon(app_icon_path)
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    splash_path = os.path.join(config.get_project_root(), "app", "icon", "splash-screen.png")
    splash_pixmap = QPixmap(splash_path)
    if not splash_pixmap.isNull() and app.primaryScreen():
        screen_size = app.primaryScreen().availableGeometry().size()
        target_width = min(splash_pixmap.width(), int(screen_size.width() * 0.8))
        target_height = min(splash_pixmap.height(), int(screen_size.height() * 0.8))
        splash_pixmap = splash_pixmap.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )

    splash = QSplashScreen(splash_pixmap, Qt.WindowStaysOnTopHint)
    splash.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
    splash.show()

    if app.primaryScreen():
        screen_geometry = app.primaryScreen().availableGeometry()
        splash.move(screen_geometry.center() - splash.rect().center())

    app.processEvents()

    window = MainWindow()
    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    def _finish_startup():
        window.show()
        window.raise_()
        window.activateWindow()
        splash.finish(window)

    QTimer.singleShot(0, window.begin_startup)
    QTimer.singleShot(6000, _finish_startup)

    # Ensure cleanup on exit
    atexit.register(lambda: wake_lock.release())
    atexit.register(lambda: window._ollama_manager.stop_server()
                    if window._ollama_manager.is_running else None)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
