"""
api.py — Ollama REST API wrapper.

Provides typed, streaming-aware methods for all Ollama endpoints.
Runs HTTP calls in QThreads to keep the UI responsive.
"""

import json
import requests
from PySide6.QtCore import QObject, Signal, QThread


class _StreamWorker(QThread):
    """Worker thread for streaming API calls."""
    chunk_received = Signal(str)  # text chunk
    finished_signal = Signal(bool, str)  # success, full_response or error

    def __init__(self, url, payload, parent=None):
        super().__init__(parent)
        self.url = url
        self.payload = payload
        self._abort = False

    def run(self):
        full_response = ""
        try:
            with requests.post(self.url, json=self.payload, stream=True, timeout=300) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if self._abort:
                        break
                    if line:
                        data = json.loads(line)
                        # Chat endpoint
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                full_response += content
                                self.chunk_received.emit(content)
                        # Generate endpoint
                        elif "response" in data:
                            content = data.get("response", "")
                            if content:
                                full_response += content
                                self.chunk_received.emit(content)
                        # Check done
                        if data.get("done", False):
                            break

            self.finished_signal.emit(True, full_response)
        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def abort(self):
        self._abort = True


class _PullWorker(QThread):
    """Worker thread for model pull with progress."""
    progress = Signal(int, int, str)  # completed, total, status
    finished_signal = Signal(bool, str)  # success, message

    def __init__(self, url, model_name, parent=None):
        super().__init__(parent)
        self.url = url
        self.model_name = model_name
        self._abort = False

    def run(self):
        try:
            payload = {"model": self.model_name, "stream": True}
            with requests.post(self.url, json=payload, stream=True, timeout=7200) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if self._abort:
                        self.finished_signal.emit(False, "Cancelled by user")
                        return
                    if line:
                        data = json.loads(line)
                        status = data.get("status", "")
                        total = data.get("total", 0)
                        completed = data.get("completed", 0)
                        self.progress.emit(completed, total, status)

                        if status == "success":
                            self.finished_signal.emit(True, "Model installed successfully!")
                            return

            self.finished_signal.emit(True, "Model pull completed")
        except Exception as e:
            self.finished_signal.emit(False, str(e))

    def abort(self):
        self._abort = True


class OllamaAPI(QObject):
    """High-level wrapper around Ollama's REST API."""

    def __init__(self, base_url: str = "http://127.0.0.1:11434", parent=None):
        super().__init__(parent)
        self._base_url = base_url
        self._current_stream: _StreamWorker | None = None
        self._current_pull: _PullWorker | None = None

    @property
    def base_url(self) -> str:
        return self._base_url

    @base_url.setter
    def base_url(self, value: str):
        self._base_url = value

    # ─── Model Management ─────────────────────────

    def list_models(self) -> list[dict]:
        """List locally installed models."""
        try:
            resp = requests.get(f"{self._base_url}/api/tags", timeout=10)
            resp.raise_for_status()
            return resp.json().get("models", [])
        except Exception:
            return []

    def show_model(self, name: str) -> dict | None:
        """Get detailed info about a model."""
        try:
            resp = requests.post(
                f"{self._base_url}/api/show",
                json={"name": name},
                timeout=10
            )
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return None

    def delete_model(self, name: str) -> tuple[bool, str]:
        """Delete a model. Returns (success, message)."""
        try:
            resp = requests.delete(
                f"{self._base_url}/api/delete",
                json={"name": name},
                timeout=30
            )
            if resp.status_code == 200:
                return True, f"Model '{name}' deleted successfully"
            else:
                return False, f"Delete failed: {resp.text}"
        except Exception as e:
            return False, str(e)

    # ─── Model Pull (with progress) ───────────────

    def pull_model(self, name: str) -> _PullWorker:
        """
        Start pulling a model. Returns a PullWorker thread.
        Connect to its .progress and .finished_signal signals.
        """
        if self._current_pull and self._current_pull.isRunning():
            self._current_pull.abort()
            self._current_pull.wait(3000)

        worker = _PullWorker(f"{self._base_url}/api/pull", name, self)
        self._current_pull = worker
        return worker

    def cancel_pull(self):
        """Cancel an ongoing model pull."""
        if self._current_pull and self._current_pull.isRunning():
            self._current_pull.abort()

    # ─── Chat (streaming) ─────────────────────────

    def chat_stream(self, model: str, messages: list[dict],
                    images: list[str] = None) -> _StreamWorker:
        """
        Start a streaming chat. Returns a StreamWorker thread.
        Connect to its .chunk_received and .finished_signal signals.

        messages: [{"role": "user"|"assistant"|"system", "content": "..."}]
        images: optional list of base64 image strings (for vision models)
        """
        if self._current_stream and self._current_stream.isRunning():
            self._current_stream.abort()
            self._current_stream.wait(3000)

        payload = {
            "model": model,
            "messages": messages,
            "stream": True
        }

        # Add images to the last user message if provided
        if images and messages:
            last_msg = payload["messages"][-1]
            if last_msg.get("role") == "user":
                last_msg["images"] = images

        worker = _StreamWorker(f"{self._base_url}/api/chat", payload, self)
        self._current_stream = worker
        return worker

    def stop_chat(self):
        """Stop the current streaming chat."""
        if self._current_stream and self._current_stream.isRunning():
            self._current_stream.abort()

    # ─── Generate (streaming) ─────────────────────

    def generate_stream(self, model: str, prompt: str,
                        images: list[str] = None) -> _StreamWorker:
        """Start a streaming generate request."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True
        }
        if images:
            payload["images"] = images

        worker = _StreamWorker(f"{self._base_url}/api/generate", payload, self)
        self._current_stream = worker
        return worker

    # ─── Health ───────────────────────────────────

    def is_available(self) -> bool:
        """Check if the Ollama server is reachable."""
        try:
            resp = requests.get(f"{self._base_url}/", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False
