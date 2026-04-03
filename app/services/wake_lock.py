"""
wake_lock.py — Prevent Windows from sleeping or turning off the display.

Uses SetThreadExecutionState Win32 API via ctypes.
No additional dependencies required.
"""

import ctypes
import sys

# Windows constants
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001
ES_DISPLAY_REQUIRED = 0x00000002

_is_acquired = False


def acquire():
    """Prevent the system from sleeping and the display from turning off."""
    global _is_acquired
    if sys.platform == "win32" and not _is_acquired:
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
        )
        _is_acquired = True


def release():
    """Allow normal power management again."""
    global _is_acquired
    if sys.platform == "win32" and _is_acquired:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        _is_acquired = False
