"""
config.py — Application configuration, paths, and constants.

Handles first-launch detection, AIUI directory setup, and
persistent config storage in the user's home directory.
"""

import json
import os
import sys

APP_NAME = "Local AI(UI)"
APP_VERSION = "1.1.0"
DEVELOPER = "Ashmith Babu P S"
DEVELOPER_GITHUB = "https://github.com/ashser004"
OLLAMA_DEFAULT_HOST = "127.0.0.1"
OLLAMA_DEFAULT_PORT = 11434
OLLAMA_ZIP_FILENAME = "ollama-windows-amd64.zip"
OLLAMA_RELEASES_API = "https://api.github.com/repos/ollama/ollama/releases/latest"
MIN_DISK_FOR_MODELS_GB = 10
MIN_DISK_FOR_SETUP_GB = 2

# The ONLY file stored outside AIUI — remembers where AIUI lives
_HOME_CONFIG_PATH = os.path.join(os.path.expanduser("~"), ".localaiui_config.json")


def get_project_root() -> str:
    """Return the project source root (where main.py lives)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_models_json_path() -> str:
    """Return path to the bundled models.json catalog."""
    return os.path.join(get_project_root(), "models.json")


def get_assets_path() -> str:
    """Return path to the assets directory."""
    return os.path.join(get_project_root(), "assets")


# ─── Home config (stores AIUI location) ───────────────────────

def load_home_config() -> dict:
    """Load the tiny home config that remembers where AIUI is."""
    if os.path.exists(_HOME_CONFIG_PATH):
        try:
            with open(_HOME_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_home_config(config: dict):
    """Save the home config."""
    with open(_HOME_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def get_aiui_base_dir() -> str | None:
    """Return the AIUI base directory, or None if not set up yet."""
    cfg = load_home_config()
    path = cfg.get("aiui_path")
    if path and os.path.isdir(path):
        return path
    return None


def set_aiui_base_dir(parent_dir: str) -> str:
    """
    Set up the AIUI directory inside parent_dir.
    Creates the folder structure and saves config.
    Returns the AIUI path.
    """
    aiui_path = os.path.join(parent_dir, "AIUI")
    # Create folder structure
    dirs = [
        aiui_path,
        os.path.join(aiui_path, "ollama"),
        os.path.join(aiui_path, "models"),
        os.path.join(aiui_path, "data"),
        os.path.join(aiui_path, "logs"),
    ]
    for d in dirs:
        os.makedirs(d, exist_ok=True)

    # Save to home config
    save_home_config({"aiui_path": aiui_path})
    return aiui_path


def is_first_launch() -> bool:
    """Check if this is the first launch (no AIUI dir configured)."""
    return get_aiui_base_dir() is None


# ─── AIUI sub-paths ──────────────────────────────────────────

def get_ollama_dir() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "ollama") if base else None


def get_ollama_exe() -> str | None:
    d = get_ollama_dir()
    return os.path.join(d, "ollama.exe") if d else None


def get_models_dir() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "models") if base else None


def get_data_dir() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "data") if base else None


def get_db_path() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "chats.db") if base else None


def get_logs_dir() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "logs") if base else None


def get_error_log_path() -> str | None:
    d = get_logs_dir()
    return os.path.join(d, "errors.txt") if d else None


def get_app_config_path() -> str | None:
    base = get_aiui_base_dir()
    return os.path.join(base, "config.json") if base else None


# ─── App-level config inside AIUI ─────────────────────────────

def load_app_config() -> dict:
    """Load app config from AIUI/config.json."""
    path = get_app_config_path()
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_app_config(config: dict):
    """Save app config to AIUI/config.json."""
    path = get_app_config_path()
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)


def is_ollama_installed() -> bool:
    """Check if Ollama binary exists in AIUI/ollama/."""
    exe = get_ollama_exe()
    return exe is not None and os.path.isfile(exe)
