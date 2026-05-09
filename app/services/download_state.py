# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
download_state.py — Persist model download progress across app restarts.

Saves/loads download progress to AIUI/data/download_state.json so that
paused or interrupted downloads can show their last-known progress on
the next launch.
"""

import json
import os

from app import config

_STATE_FILENAME = "download_state.json"


def _get_state_path() -> str | None:
    base = config.get_aiui_base_dir()
    if base:
        return os.path.join(base, "data", _STATE_FILENAME)
    return None


def save_states(states: dict):
    """Save download states to disk.

    states: {tag: {name, progress_pct, completed, total, status}}
    """
    path = _get_state_path()
    if path:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=2)


def load_states() -> dict:
    """Load saved download states."""
    path = _get_state_path()
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def remove_state(tag: str):
    """Remove a specific download state."""
    states = load_states()
    if tag in states:
        del states[tag]
        save_states(states)


def clear_all():
    """Clear all download states."""
    path = _get_state_path()
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
