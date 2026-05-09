# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
imagegen_download.py — QThread worker for downloading image-gen models from HuggingFace.

Downloads GGUF model files to AIUI/imagegen/models/ with progress reporting.
"""

import os
import requests
from PySide6.QtCore import QThread, Signal

from app import config


class ImageGenModelDownloadWorker(QThread):
    """Downloads an image-gen model GGUF file from a direct URL."""

    progress = Signal(int, int, str)       # completed_bytes, total_bytes, status
    finished_signal = Signal(bool, str)    # success, message

    def __init__(self, model: dict, parent=None):
        super().__init__(parent)
        self._model = model
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        tag = self._model.get("tag", "unknown")
        name = self._model.get("name", tag)
        url = self._model.get("download_url", "")

        if not url:
            self.finished_signal.emit(False, f"No download URL for {name}")
            return

        models_dir = config.get_imagegen_models_dir()
        if not models_dir:
            self.finished_signal.emit(False, "Image generation directory not configured.")
            return

        os.makedirs(models_dir, exist_ok=True)

        # Determine filename from URL
        filename = url.rsplit("/", 1)[-1] if "/" in url else f"{tag}.gguf"
        target_path = os.path.join(models_dir, filename)

        # Also create a tag-mapping file so we can look up tag -> filename
        tag_map_path = os.path.join(models_dir, f"{tag}.tag")

        try:
            resp = requests.get(url, stream=True, timeout=30)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))

            downloaded = 0
            self.progress.emit(0, total, "downloading")

            with open(target_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=131072):
                    if self._abort:
                        f.close()
                        # Clean up partial file
                        try:
                            os.remove(target_path)
                        except Exception:
                            pass
                        self.finished_signal.emit(False, "Cancelled")
                        return

                    f.write(chunk)
                    downloaded += len(chunk)
                    self.progress.emit(downloaded, total, "downloading")

            # Write the tag mapping so we can find the model by tag later
            with open(tag_map_path, "w", encoding="utf-8") as f:
                f.write(filename)

            self.finished_signal.emit(True, f"{name} downloaded successfully!")

        except requests.RequestException as e:
            # Clean up partial file
            try:
                if os.path.exists(target_path):
                    os.remove(target_path)
            except Exception:
                pass
            self.finished_signal.emit(False, f"Download failed: {e}")

        except Exception as e:
            self.finished_signal.emit(False, f"Error: {e}")


def get_model_path_by_tag(tag: str) -> str | None:
    """Look up the local file path of an installed image-gen model by its catalog tag."""
    models_dir = config.get_imagegen_models_dir()
    if not models_dir:
        return None

    # Check for a .tag mapping file
    tag_map_path = os.path.join(models_dir, f"{tag}.tag")
    if os.path.isfile(tag_map_path):
        try:
            with open(tag_map_path, "r", encoding="utf-8") as f:
                filename = f.read().strip()
            full_path = os.path.join(models_dir, filename)
            if os.path.isfile(full_path):
                return full_path
        except Exception:
            pass

    # Fallback: scan directory for matching files
    for f in os.listdir(models_dir):
        if f.lower().endswith((".gguf", ".safetensors")):
            # Check if the tag appears in the filename
            if tag.replace("-", "").lower() in f.replace("-", "").lower():
                return os.path.join(models_dir, f)

    return None


def is_imagegen_model_installed(tag: str) -> bool:
    """Check if a specific image-gen model is downloaded."""
    return get_model_path_by_tag(tag) is not None
