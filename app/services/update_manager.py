"""
update_manager.py — Background workers for checking and downloading app updates.
"""

import os
import requests
from PySide6.QtCore import QThread, Signal
from app import config

class UpdateCheckerWorker(QThread):
    """Checks the GitHub API for the latest release."""
    
    update_found = Signal(str, str) # version_tag, download_url
    no_update_found = Signal()
    error_occurred = Signal(str)

    def run(self):
        try:
            response = requests.get(config.APP_RELEASES_API, timeout=10)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "").lstrip("v")
                current_version = config.APP_VERSION.lstrip("v")
                
                # Simple version comparison (assumes semver format x.y.z)
                if self._is_newer_version(latest_tag, current_version):
                    download_url = None
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                    
                    if download_url:
                        self.update_found.emit(f"v{latest_tag}", download_url)
                    else:
                        self.error_occurred.emit("No installer found in the latest release.")
                else:
                    self.no_update_found.emit()
            elif response.status_code == 404:
                # This could happen if there are no releases yet
                self.no_update_found.emit()
            else:
                self.error_occurred.emit(f"GitHub API Error: {response.status_code}")
                
        except requests.exceptions.RequestException:
            self.error_occurred.emit("Check your connection and try again..")
        except Exception as e:
            self.error_occurred.emit(str(e))

    def _is_newer_version(self, latest: str, current: str) -> bool:
        """Helper to compare semver strings safely."""
        try:
            latest_parts = [int(x) for x in latest.split(".")]
            current_parts = [int(x) for x in current.split(".")]
            # Pad with 0s if length differs
            length = max(len(latest_parts), len(current_parts))
            latest_parts += [0] * (length - len(latest_parts))
            current_parts += [0] * (length - len(current_parts))
            
            for l, c in zip(latest_parts, current_parts):
                if l > c:
                    return True
                if l < c:
                    return False
            return False
        except ValueError:
            # Fallback to simple string comparison if not valid semver
            return latest > current


class UpdateDownloaderWorker(QThread):
    """Downloads the installer executable in the background."""
    
    progress_updated = Signal(int, int) # downloaded_bytes, total_bytes
    download_complete = Signal(str) # file_path
    error_occurred = Signal(str)

    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._abort = False

    def abort(self):
        self._abort = True

    def run(self):
        try:
            # Prepare destination
            updates_dir = config.get_updates_dir()
            if not updates_dir:
                self.error_occurred.emit("Updates directory not configured.")
                return
                
            os.makedirs(updates_dir, exist_ok=True)
            filename = self.url.split("/")[-1] or "LOCAL_AI_Setup.exe"
            dest_path = os.path.join(updates_dir, filename)

            with requests.get(self.url, stream=True, timeout=15) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                downloaded = 0
                
                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._abort:
                            return
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                self.progress_updated.emit(downloaded, total_size)
                                
            if not self._abort:
                self.download_complete.emit(dest_path)
                
        except requests.exceptions.RequestException:
            self.error_occurred.emit("Network error while downloading the update.")
        except Exception as e:
            self.error_occurred.emit(str(e))
