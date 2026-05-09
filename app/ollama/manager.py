# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
manager.py — Ollama binary lifecycle management.

Handles downloading, installing, starting, stopping, health-checking,
and crash-recovery of the portable Ollama server.
"""

import os
import sys
import json
import zipfile
import socket
import time
import requests
import psutil
from PySide6.QtCore import QObject, QProcess, QTimer, Signal, Slot, QProcessEnvironment

from app import config


class OllamaManager(QObject):
    """Manages the Ollama binary lifecycle."""

    # Signals
    download_progress = Signal(int, int)  # downloaded_bytes, total_bytes
    extract_progress = Signal(int, int)   # extracted_count, total_count
    download_finished = Signal(bool, str)  # success, message
    install_progress = Signal(str)  # status text
    server_started = Signal()
    server_stopped = Signal()
    server_error = Signal(str)
    health_status = Signal(bool)  # is_healthy

    def __init__(self, parent=None):
        super().__init__(parent)
        self._process: QProcess | None = None
        self._health_timer = QTimer(self)
        self._health_timer.timeout.connect(self._check_health)
        self._ready_timer = QTimer(self)
        self._ready_timer.timeout.connect(self._poll_ready)
        self._ready_attempts = 0
        self._restart_count = 0
        self._max_restarts = 3
        self._intentional_stop = False
        self._stop_in_progress = False
        self._stop_started_at: float | None = None
        self._stop_target_pids: set[int] = set()
        self._stop_forced = False
        self._last_stop_forced = False
        self._port = config.OLLAMA_DEFAULT_PORT
        self._downloading = False

    # ─── Properties ───────────────────────────────

    @property
    def port(self) -> int:
        return self._port

    @property
    def base_url(self) -> str:
        return f"http://{config.OLLAMA_DEFAULT_HOST}:{self._port}"

    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.state() == QProcess.Running

    @property
    def is_downloading(self) -> bool:
        return self._downloading

    # ─── Cleanup ──────────────────────────────────

    def cleanup_partial_downloads(self):
        """Remove leftover .partial files from interrupted downloads."""
        ollama_dir = config.get_ollama_dir()
        if ollama_dir and os.path.isdir(ollama_dir):
            for fname in os.listdir(ollama_dir):
                if fname.endswith(".partial"):
                    partial_path = os.path.join(ollama_dir, fname)
                    try:
                        os.remove(partial_path)
                        self._log_error(f"Cleaned up partial download: {fname}")
                    except OSError:
                        pass

    # ─── Download & Install ───────────────────────

    def download_and_install(self):
        """Download Ollama from GitHub and install to AIUI/ollama/."""
        if self._downloading:
            return
        self._downloading = True

        try:
            self.install_progress.emit("Fetching latest release info...")
            zip_url = self._get_download_url()
            if not zip_url:
                self.download_finished.emit(False, "Could not find Ollama download URL")
                self._downloading = False
                return

            ollama_dir = config.get_ollama_dir()
            if not ollama_dir:
                self.download_finished.emit(False, "AIUI directory not configured")
                self._downloading = False
                return

            zip_path = os.path.join(ollama_dir, config.OLLAMA_ZIP_FILENAME)

            # Download with progress
            self.install_progress.emit("Downloading Ollama...")
            success = self._download_file(zip_url, zip_path)
            if not success:
                self._downloading = False
                return

            # Extract
            self.install_progress.emit("Extracting Ollama...")
            self._extract_zip(zip_path, ollama_dir)

            # Cleanup zip
            self.install_progress.emit("Cleaning up...")
            if os.path.exists(zip_path):
                os.remove(zip_path)

            # Verify
            if config.is_ollama_installed():
                self.install_progress.emit("Ollama installed successfully!")
                self.download_finished.emit(True, "Ollama installed successfully!")
            else:
                self.download_finished.emit(False, "Installation failed — ollama.exe not found after extraction")

        except Exception as e:
            self._log_error(f"Installation error: {e}")
            self.download_finished.emit(False, f"Installation failed: {e}")
        finally:
            self._downloading = False

    def _get_download_url(self) -> str | None:
        """Get the download URL for the latest Ollama Windows zip."""
        try:
            resp = requests.get(config.OLLAMA_RELEASES_API, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            for asset in data.get("assets", []):
                if asset.get("name") == config.OLLAMA_ZIP_FILENAME:
                    return asset.get("browser_download_url")
        except Exception as e:
            self._log_error(f"Failed to fetch release info: {e}")
        return None

    def _download_file(self, url: str, dest: str) -> bool:
        """Download a file with progress reporting."""
        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(dest + ".partial", "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.download_progress.emit(downloaded, total)

            # Rename partial to final
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(dest + ".partial", dest)
            return True

        except Exception as e:
            self._log_error(f"Download failed: {e}")
            # Cleanup partial
            partial = dest + ".partial"
            if os.path.exists(partial):
                os.remove(partial)
            self.download_finished.emit(False, f"Download failed: {e}")
            return False

    def _extract_zip(self, zip_path: str, dest_dir: str):
        """Extract zip file to destination with progress reporting."""
        with zipfile.ZipFile(zip_path, 'r') as zf:
            members = zf.namelist()
            total = len(members)
            for i, member in enumerate(members, 1):
                zf.extract(member, dest_dir)
                self.extract_progress.emit(i, total)
                if i % 20 == 0 or i == total:  # throttle status text updates
                    self.install_progress.emit(
                        f"Extracting... {i}/{total} files ({int(i/total*100)}%)"
                    )

    # ─── Server Lifecycle ─────────────────────────

    def start_server(self):
        """Start the Ollama server."""
        if self._stop_in_progress:
            return

        if self.is_running:
            self.server_started.emit()
            return

        exe = config.get_ollama_exe()
        if not exe or not os.path.isfile(exe):
            self.server_error.emit("Ollama binary not found. Please install first.")
            return

        # Find an available port
        self._port = self._find_available_port()

        # Create process
        self._process = QProcess(self)
        self._process.setProgram(exe)
        self._process.setArguments(["serve"])

        # Set environment
        env = QProcessEnvironment.systemEnvironment()
        env.insert("OLLAMA_HOST", f"{config.OLLAMA_DEFAULT_HOST}:{self._port}")
        env.insert("OLLAMA_MODELS", config.get_models_dir() or "")
        env.insert("HOME", config.get_data_dir() or "")
        env.insert("USERPROFILE", config.get_data_dir() or "")

        # Prevent Ollama from using default system paths
        data_dir = config.get_data_dir() or ""
        env.insert("LOCALAPPDATA", os.path.join(data_dir, "AppData", "Local"))
        env.insert("APPDATA", os.path.join(data_dir, "AppData", "Roaming"))

        self._process.setProcessEnvironment(env)
        self._process.setWorkingDirectory(config.get_ollama_dir() or "")

        # Connect signals
        self._process.finished.connect(self._on_process_finished)
        self._process.errorOccurred.connect(self._on_process_error)

        self._intentional_stop = False
        self._stop_in_progress = False
        self._stop_started_at = None
        self._stop_target_pids.clear()
        self._stop_forced = False
        self._last_stop_forced = False
        self._process.start()

        # Wait for server to become ready (non-blocking polling)
        self._ready_attempts = 0
        self._ready_timer.start(500)  # poll every 500ms

    def _poll_ready(self):
        """Non-blocking poll: check if server is ready."""
        self._ready_attempts += 1
        try:
            resp = requests.get(f"{self.base_url}/", timeout=1)
            if resp.status_code == 200:
                self._ready_timer.stop()
                self._restart_count = 0
                self._log_info("Ollama server started safely")
                self.server_started.emit()
                self._health_timer.start(5000)
                return
        except requests.ConnectionError:
            pass
        except Exception:
            pass

        if self._ready_attempts >= 30:  # ~15 seconds
            self._ready_timer.stop()
            self.server_error.emit("Ollama server did not start in time.")

    def stop_server(self):
        """Stop the Ollama server gracefully."""
        if self._stop_in_progress:
            return

        self._intentional_stop = True
        self._stop_in_progress = True
        self._stop_forced = False
        self._last_stop_forced = False
        self._health_timer.stop()
        self._ready_timer.stop()

        self._stop_started_at = time.monotonic()
        self._stop_target_pids = self._capture_process_tree_pids()

        if not self._stop_target_pids:
            if self._process and self._process.state() == QProcess.Running:
                self._process.terminate()
                QTimer.singleShot(250, self._check_stop_progress)
                return

            self._finalize_stop("Ollama server stopped safely")
            return

        self._terminate_stop_targets(force=False)
        QTimer.singleShot(250, self._check_stop_progress)

    def _capture_process_tree_pids(self) -> set[int]:
        """Capture the parent Ollama PID and any current children."""
        pids: set[int] = set()
        if not self._process:
            return pids

        try:
            parent = psutil.Process(int(self._process.processId()))
            pids.add(parent.pid)
            for child in parent.children(recursive=True):
                pids.add(child.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, TypeError, ValueError):
            return pids

        return pids

    def _terminate_stop_targets(self, force: bool = False):
        """Terminate or kill the tracked Ollama process tree."""
        if not self._stop_target_pids:
            return

        for pid in list(self._stop_target_pids):
            try:
                proc = psutil.Process(pid)
                if force:
                    proc.kill()
                else:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                self._stop_target_pids.discard(pid)

    def _check_stop_progress(self):
        """Poll shutdown progress and escalate if the tree is still alive."""
        if not self._stop_in_progress:
            return

        alive_pids = {pid for pid in self._stop_target_pids if psutil.pid_exists(pid)}
        if not alive_pids:
            self._stop_target_pids.clear()
            self._finalize_stop()
            return

        self._stop_target_pids = alive_pids

        elapsed = time.monotonic() - self._stop_started_at if self._stop_started_at else 0.0
        if elapsed >= 5.0 or self._stop_forced:
            if not self._stop_forced:
                self._stop_forced = True
                self._last_stop_forced = True
                self._log_info("Force stopping Ollama process tree after timeout")
            self._terminate_stop_targets(force=True)
        else:
            self._terminate_stop_targets(force=False)

        QTimer.singleShot(250, self._check_stop_progress)

    def _find_available_port(self) -> int:
        """Find an available port starting from default."""
        for port in range(config.OLLAMA_DEFAULT_PORT, config.OLLAMA_DEFAULT_PORT + 10):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((config.OLLAMA_DEFAULT_HOST, port))
                    return port
                except OSError:
                    continue
        return config.OLLAMA_DEFAULT_PORT  # fallback

    # ─── Health & Recovery ────────────────────────

    @Slot()
    def _check_health(self):
        """Periodic health check."""
        try:
            resp = requests.get(f"{self.base_url}/", timeout=2)
            self.health_status.emit(resp.status_code == 200)
        except Exception:
            self.health_status.emit(False)

    @Slot(int, QProcess.ExitStatus)
    def _on_process_finished(self, exit_code, exit_status):
        """Handle unexpected process exit — auto-restart."""
        if self._intentional_stop or self._stop_in_progress:
            QTimer.singleShot(0, self._check_stop_progress)
            return

        self._health_timer.stop()

        if self._restart_count < self._max_restarts:
            self._restart_count += 1
            self._log_error(
                f"Ollama crashed (exit code {exit_code}). "
                f"Restarting... (attempt {self._restart_count}/{self._max_restarts})"
            )
            QTimer.singleShot(2000, self.start_server)
        else:
            msg = f"Ollama crashed {self._max_restarts} times. Giving up."
            self._log_error(msg)
            self.server_error.emit(msg)

    @Slot(QProcess.ProcessError)
    def _on_process_error(self, error):
        """Handle process errors."""
        if self._intentional_stop or self._stop_in_progress:
            return

        error_map = {
            QProcess.FailedToStart: "Failed to start Ollama",
            QProcess.Crashed: "Ollama crashed",
            QProcess.Timedout: "Ollama timed out",
            QProcess.WriteError: "Write error",
            QProcess.ReadError: "Read error",
        }
        msg = error_map.get(error, f"Unknown error: {error}")
        self._log_error(msg)
        self.server_error.emit(msg)

    # ─── Logging ──────────────────────────────────

    def _log_error(self, message: str):
        """Append error to the log file."""
        log_path = config.get_error_log_path()
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")

    def _log_info(self, message: str):
        """Append a non-error lifecycle message to the log file."""
        log_path = config.get_error_log_path()
        if log_path:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {message}\n")

    def _finalize_stop(self, message: str | None = None):
        """Reset stop state and emit the stopped signal once the process is gone."""
        self._health_timer.stop()
        self._ready_timer.stop()
        self._stop_in_progress = False
        self._intentional_stop = False
        self._stop_started_at = None
        self._stop_target_pids.clear()
        self._stop_forced = False

        if self._process is not None:
            self._process.deleteLater()
            self._process = None

        final_message = message
        if final_message is None:
            final_message = (
                "Ollama server stopped after force cleanup"
                if self._last_stop_forced
                else "Ollama server stopped safely"
            )

        if final_message:
            self._log_info(final_message)

        self.server_stopped.emit()
