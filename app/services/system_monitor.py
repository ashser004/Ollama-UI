# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
system_monitor.py — Real-time system resource monitoring.

Uses psutil to track CPU, RAM, and disk usage.
Emits warnings when resources are critically low.
"""

import psutil
from PySide6.QtCore import QObject, QTimer, Signal

from app import config


class SystemMonitor(QObject):
    """Monitors system resources and emits alerts."""

    # Signals
    stats_updated = Signal(dict)  # {cpu, ram_used, ram_total, disk_used, disk_total, disk_free}
    disk_warning = Signal(str)  # warning message
    ram_warning = Signal(str)  # warning message

    # Thresholds
    DISK_WARNING_GB = 2.0
    RAM_WARNING_PERCENT = 90

    def __init__(self, poll_interval_ms: int = 3000, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update)
        self._poll_interval = poll_interval_ms
        self._last_disk_warning = False
        self._last_ram_warning = False

    def start(self):
        """Start monitoring."""
        self._update()  # immediate first update
        self._timer.start(self._poll_interval)

    def stop(self):
        """Stop monitoring."""
        self._timer.stop()

    def get_stats(self) -> dict:
        """Get current system stats."""
        stats = {
            "cpu_percent": psutil.cpu_percent(interval=0),
            "ram_used_gb": 0,
            "ram_total_gb": 0,
            "ram_percent": 0,
            "disk_used_gb": 0,
            "disk_total_gb": 0,
            "disk_free_gb": 0,
            "disk_percent": 0,
        }

        # RAM
        mem = psutil.virtual_memory()
        stats["ram_used_gb"] = round(mem.used / (1024 ** 3), 1)
        stats["ram_total_gb"] = round(mem.total / (1024 ** 3), 1)
        stats["ram_percent"] = mem.percent

        # Disk — check the drive where AIUI is stored
        aiui_path = config.get_aiui_base_dir()
        if aiui_path:
            try:
                usage = psutil.disk_usage(aiui_path)
                stats["disk_used_gb"] = round(usage.used / (1024 ** 3), 1)
                stats["disk_total_gb"] = round(usage.total / (1024 ** 3), 1)
                stats["disk_free_gb"] = round(usage.free / (1024 ** 3), 1)
                stats["disk_percent"] = usage.percent
            except (OSError, FileNotFoundError):
                pass

        return stats

    def get_available_disk_gb(self) -> float:
        """Get available disk space in GB on the AIUI drive."""
        aiui_path = config.get_aiui_base_dir()
        if aiui_path:
            try:
                usage = psutil.disk_usage(aiui_path)
                return round(usage.free / (1024 ** 3), 1)
            except (OSError, FileNotFoundError):
                pass
        return 0.0

    def get_available_ram_gb(self) -> float:
        """Get total system RAM in GB."""
        return round(psutil.virtual_memory().total / (1024 ** 3), 1)

    def can_install_model(self, size_gb: float, min_ram_gb: float) -> tuple[bool, str]:
        """
        Check if a model can be installed.
        Returns (can_install, reason).
        """
        disk_free = self.get_available_disk_gb()
        ram_total = self.get_available_ram_gb()

        if size_gb > disk_free:
            return False, f"Need {size_gb:.1f} GB disk space, only {disk_free:.1f} GB free"

        if min_ram_gb > ram_total:
            return False, f"Need {min_ram_gb:.0f} GB RAM, system has {ram_total:.0f} GB"

        if disk_free < config.MIN_DISK_FOR_MODELS_GB:
            return False, f"Less than {config.MIN_DISK_FOR_MODELS_GB} GB free. Free up space or use another drive."

        return True, "OK"

    def has_enough_space_for_models(self) -> bool:
        """Check if there's at least 10GB free for model installation."""
        return self.get_available_disk_gb() >= config.MIN_DISK_FOR_MODELS_GB

    def _update(self):
        """Update stats and emit signals."""
        stats = self.get_stats()
        self.stats_updated.emit(stats)

        # Disk warning
        disk_low = stats["disk_free_gb"] < self.DISK_WARNING_GB
        if disk_low and not self._last_disk_warning:
            self.disk_warning.emit(
                f"Storage critically low! Only {stats['disk_free_gb']:.1f} GB free."
            )
        self._last_disk_warning = disk_low

        # RAM warning
        ram_high = stats["ram_percent"] > self.RAM_WARNING_PERCENT
        if ram_high and not self._last_ram_warning:
            self.ram_warning.emit(
                f"RAM usage critically high ({stats['ram_percent']:.0f}%). "
                f"Models may run slowly."
            )
        self._last_ram_warning = ram_high

    @staticmethod
    def check_drive_space(path: str) -> dict:
        """Check disk space for any arbitrary path."""
        try:
            usage = psutil.disk_usage(path)
            return {
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "free_gb": round(usage.free / (1024 ** 3), 1),
                "percent": usage.percent,
            }
        except (OSError, FileNotFoundError):
            return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent": 0}
