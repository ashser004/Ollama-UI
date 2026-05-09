# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
download_manager.py — Resumable file download manager.

Handles large downloads with resume via HTTP Range headers,
progress tracking, and partial file cleanup.
"""

import os
import requests
from PySide6.QtCore import QObject, QThread, Signal


class _DownloadThread(QThread):
    """Worker thread for file downloads."""
    progress = Signal(int, int)  # downloaded, total
    status = Signal(str)
    finished_signal = Signal(bool, str)  # success, message

    def __init__(self, url: str, dest: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.dest = dest
        self._abort = False

    def run(self):
        partial_path = self.dest + ".partial"
        downloaded = 0

        # Check for existing partial download
        if os.path.exists(partial_path):
            downloaded = os.path.getsize(partial_path)
            self.status.emit(f"Resuming from {downloaded / (1024*1024):.1f} MB...")

        try:
            headers = {}
            if downloaded > 0:
                headers["Range"] = f"bytes={downloaded}-"

            resp = requests.get(self.url, stream=True, headers=headers, timeout=30)

            # If server doesn't support Range, start over
            if resp.status_code == 200 and downloaded > 0:
                downloaded = 0
                mode = "wb"
            elif resp.status_code == 206:
                mode = "ab"
            elif resp.status_code == 200:
                mode = "wb"
            else:
                self.finished_signal.emit(False, f"HTTP error {resp.status_code}")
                return

            content_length = resp.headers.get("content-length")
            if content_length:
                total = downloaded + int(content_length)
            else:
                total = 0

            with open(partial_path, mode) as f:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if self._abort:
                        self.finished_signal.emit(False, "Download cancelled")
                        return
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)

            # Move partial to final
            if os.path.exists(self.dest):
                os.remove(self.dest)
            os.rename(partial_path, self.dest)
            self.finished_signal.emit(True, "Download complete")

        except Exception as e:
            self.finished_signal.emit(False, f"Download error: {e}")

    def abort(self):
        self._abort = True


class DownloadManager(QObject):
    """Manages file downloads with resume support."""

    progress = Signal(int, int)  # downloaded, total
    status = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: _DownloadThread | None = None

    def download(self, url: str, dest: str):
        """Start downloading a file."""
        if self._worker and self._worker.isRunning():
            self._worker.abort()
            self._worker.wait(3000)

        # Ensure destination directory exists
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        self._worker = _DownloadThread(url, dest, self)
        self._worker.progress.connect(self.progress.emit)
        self._worker.status.connect(self.status.emit)
        self._worker.finished_signal.connect(self.finished.emit)
        self._worker.start()

    def cancel(self):
        """Cancel the current download."""
        if self._worker and self._worker.isRunning():
            self._worker.abort()

    def cleanup_partial(self, dest: str):
        """Remove partial download file."""
        partial = dest + ".partial"
        if os.path.exists(partial):
            os.remove(partial)

    @property
    def is_downloading(self) -> bool:
        return self._worker is not None and self._worker.isRunning()
