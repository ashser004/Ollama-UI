# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
manager.py — Manages stable-diffusion.cpp engine lifecycle.

Handles downloading the sd-cli binary, spawning per-generation
subprocesses, GPU detection, and cleanup.
"""

import os
import io
import sys
import glob
import time
import shutil
import zipfile
import subprocess
import base64
import requests

from PIL import Image
from PySide6.QtCore import QObject, QThread, Signal

from app import config


def _has_nvidia_gpu() -> bool:
    """Detect if an NVIDIA GPU is available via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi"], capture_output=True, timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return result.returncode == 0
    except Exception:
        return False


class EngineDownloadWorker(QThread):
    """Downloads and extracts the sd-cli binary from GitHub releases."""

    progress = Signal(int, int)      # bytes_downloaded, total_bytes
    finished = Signal(bool, str)     # success, message

    def __init__(self, parent=None):
        super().__init__(parent)
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            # Fetch latest release info
            resp = requests.get(config.SD_CPP_RELEASES_API, timeout=15)
            resp.raise_for_status()
            release = resp.json()

            assets = release.get("assets", [])
            imagegen_dir = config.get_imagegen_dir()
            os.makedirs(imagegen_dir, exist_ok=True)

            has_gpu = _has_nvidia_gpu()

            # ── Pick the right Windows build ─────────────────────────────────
            # Priority: CUDA12 (GPU) → AVX2 (CPU) → any Windows zip
            def _find_asset(keyword):
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "win" in name and keyword in name and name.endswith(".zip"):
                        return asset.get("browser_download_url"), asset.get("name")
                return None, None

            if has_gpu:
                asset_url, asset_name = _find_asset("cuda12")
            else:
                asset_url, asset_name = None, None

            if not asset_url:
                asset_url, asset_name = _find_asset("avx2")
            if not asset_url:
                asset_url, asset_name = _find_asset("")   # any win zip

            if not asset_url:
                self.finished.emit(False, "Could not find a Windows binary in the latest release.")
                return

            # ── Helper: download a zip and extract all files flat ────────────
            def _download_and_extract(url, name, total_offset=0, total_override=0):
                dl = requests.get(url, stream=True, timeout=30)
                dl.raise_for_status()
                file_total = int(dl.headers.get("content-length", 0))
                zip_path = os.path.join(imagegen_dir, name)
                downloaded = 0
                with open(zip_path, "wb") as f:
                    for chunk in dl.iter_content(chunk_size=65536):
                        if self._abort:
                            f.close()
                            try:
                                os.remove(zip_path)
                            except Exception:
                                pass
                            return False
                        f.write(chunk)
                        downloaded += len(chunk)
                        # Emit combined progress when total_override is set
                        if total_override:
                            self.progress.emit(total_offset + downloaded, total_override)
                        else:
                            self.progress.emit(downloaded, file_total)

                with zipfile.ZipFile(zip_path, "r") as zf:
                    for member in zf.namelist():
                        if member.endswith("/"):
                            continue
                        basename = os.path.basename(member)
                        if not basename:
                            continue
                        target = os.path.join(imagegen_dir, basename)
                        with zf.open(member) as src, open(target, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                try:
                    os.remove(zip_path)
                except Exception:
                    pass
                return True

            # ── Download main binary ─────────────────────────────────────────
            ok = _download_and_extract(asset_url, asset_name)
            if not ok:
                self.finished.emit(False, "Download cancelled.")
                return

            # ── If CUDA build: also download cudart DLLs ─────────────────────
            if has_gpu:
                cudart_url, cudart_name = None, None
                for asset in assets:
                    name = asset.get("name", "").lower()
                    if "cudart" in name and "win" in name and name.endswith(".zip"):
                        cudart_url = asset.get("browser_download_url")
                        cudart_name = asset.get("name")
                        break
                if cudart_url:
                    ok = _download_and_extract(cudart_url, cudart_name)
                    if not ok:
                        self.finished.emit(False, "Download cancelled.")
                        return

            # ── Rename sd.exe → sd-cli.exe if needed ────────────────────────
            sd_exe = os.path.join(imagegen_dir, "sd.exe")
            target_exe = os.path.join(imagegen_dir, "sd-cli.exe")
            if os.path.isfile(sd_exe) and not os.path.isfile(target_exe):
                shutil.move(sd_exe, target_exe)

            found_exe = os.path.isfile(target_exe)

            if found_exe and config.is_imagegen_installed():
                backend = "GPU (CUDA)" if has_gpu else "CPU"
                self.finished.emit(True, f"Image generation engine installed ({backend} mode).")
            else:
                self.finished.emit(False, "Could not find sd-cli.exe in the downloaded archive.")

        except requests.RequestException as e:
            self.finished.emit(False, f"Download failed: {e}")
        except Exception as e:
            self.finished.emit(False, f"Installation failed: {e}")


class ImageGenWorker(QThread):
    """Runs a single image generation via sd-cli subprocess."""

    finished = Signal(bool, str)   # success, result_path_or_error

    def __init__(self, model_path: str, prompt: str, output_path: str,
                 width: int = 512, height: int = 512, steps: int = 20,
                 parent=None):
        super().__init__(parent)
        self._model_path = model_path
        self._prompt = prompt
        self._output_path = output_path
        self._width = width
        self._height = height
        self._steps = steps
        self._process: subprocess.Popen | None = None
        self._abort = False

    def abort(self):
        """Request abort — will kill the subprocess."""
        self._abort = True
        if self._process and self._process.poll() is None:
            try:
                self._process.kill()
            except Exception:
                pass

    def run(self):
        exe = config.get_imagegen_engine_exe()
        if not exe or not os.path.isfile(exe):
            self.finished.emit(False, "Image generation engine not found.")
            return

        # The engine directory contains the exe AND companion DLLs
        # (including CUDA runtime DLLs if GPU build was installed).
        # We set cwd + prepend PATH so all DLLs are found at load time.
        engine_dir = os.path.dirname(exe)

        # Build command — CUDA is automatic if the CUDA build was
        # downloaded (no --cuda flag exists; GPU is used at compile level)
        cmd = [
            exe,
            "-m", self._model_path,
            "-p", self._prompt,
            "-o", self._output_path,
            "-W", str(self._width),
            "-H", str(self._height),
            "--steps", str(self._steps),
        ]

        # Set thread count for CPU (also used as fallback in CUDA builds)
        cpu_count = os.cpu_count() or 4
        threads = max(1, cpu_count - 1)  # Leave one core free for the UI
        cmd.extend(["-t", str(threads)])

        # Prepare environment: prepend engine dir to PATH so CUDA DLLs
        # (cudart64_12.dll, cublas64_12.dll, etc.) are found
        env = os.environ.copy()
        env["PATH"] = engine_dir + os.pathsep + env.get("PATH", "")

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=engine_dir,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            # Wait for completion
            self._process.wait()

            if self._abort:
                self.finished.emit(False, "Generation cancelled.")
                return

            if self._process.returncode != 0:
                stderr_out = self._process.stderr.read().decode(errors="replace") if self._process.stderr else ""
                self.finished.emit(False, f"Generation failed (code {self._process.returncode}): {stderr_out[:200]}")
                return

            if os.path.isfile(self._output_path):
                self.finished.emit(True, self._output_path)
            else:
                self.finished.emit(False, "Output image was not created.")

        except Exception as e:
            self.finished.emit(False, f"Generation error: {e}")
        finally:
            self._process = None


class ImageGenManager(QObject):
    """High-level manager for the image generation engine."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_worker: ImageGenWorker | None = None
        self._download_worker: EngineDownloadWorker | None = None

    @property
    def is_installed(self) -> bool:
        return config.is_imagegen_installed()

    @property
    def is_generating(self) -> bool:
        return self._current_worker is not None and self._current_worker.isRunning()

    def download_engine(self) -> EngineDownloadWorker:
        """Start downloading the engine binary. Returns the worker for signal connections."""
        self._download_worker = EngineDownloadWorker(self)
        return self._download_worker

    def generate_image(self, model_path: str, prompt: str,
                       width: int = 512, height: int = 512,
                       steps: int = 20) -> ImageGenWorker:
        """Start an image generation. Returns the worker for signal connections."""
        output_dir = config.get_imagegen_output_dir()
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"gen_{int(time.time())}.png")

        self._current_worker = ImageGenWorker(
            model_path, prompt, output_path, width, height, steps, parent=self
        )
        return self._current_worker

    def abort_generation(self):
        """Abort any active generation."""
        if self._current_worker:
            self._current_worker.abort()

    def cleanup(self):
        """Kill any active process and clean up temp output files."""
        self.abort_generation()
        self.cleanup_output_dir()

    @staticmethod
    def cleanup_output_dir():
        """Remove all temp PNG files from the output directory."""
        output_dir = config.get_imagegen_output_dir()
        if output_dir and os.path.isdir(output_dir):
            for f in glob.glob(os.path.join(output_dir, "*.png")):
                try:
                    os.remove(f)
                except Exception:
                    pass

    @staticmethod
    def png_to_base64(png_path: str, max_size: int = 512) -> str | None:
        """Convert a PNG file to a base64 string, resizing if needed.
        Returns the base64 string, or None on failure.
        Deletes the source PNG after successful conversion."""
        try:
            with Image.open(png_path) as img:
                # Resize if larger than max_size
                w, h = img.size
                if max(w, h) > max_size:
                    if w > h:
                        new_w = max_size
                        new_h = int(h * max_size / w)
                    else:
                        new_h = max_size
                        new_w = int(w * max_size / h)
                    img = img.resize((new_w, new_h), Image.LANCZOS)

                if img.mode != "RGB":
                    img = img.convert("RGB")

                buf = io.BytesIO()
                img.save(buf, format="PNG", optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")

            # Delete the temp PNG
            try:
                os.remove(png_path)
            except Exception:
                pass

            return b64
        except Exception:
            return None

    @staticmethod
    def get_installed_models() -> list[dict]:
        """Scan AIUI/imagegen/models/ for .gguf files and return info dicts."""
        models_dir = config.get_imagegen_models_dir()
        if not models_dir or not os.path.isdir(models_dir):
            return []

        installed = []
        for f in os.listdir(models_dir):
            if f.lower().endswith((".gguf", ".safetensors")):
                full_path = os.path.join(models_dir, f)
                size_gb = os.path.getsize(full_path) / (1024 ** 3)
                # Derive a tag from the filename (strip extension)
                tag = os.path.splitext(f)[0]
                installed.append({
                    "tag": tag,
                    "filename": f,
                    "path": full_path,
                    "size_gb": round(size_gb, 2),
                })
        return installed

    @staticmethod
    def get_installed_tags() -> set[str]:
        """Return a set of installed image-gen model tags."""
        return {m["tag"] for m in ImageGenManager.get_installed_models()}
