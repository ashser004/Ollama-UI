"""
chat_page.py — Chat page wrapper.
"""

from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal

from app.widgets.chat_view import ChatView
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog


class ChatPage(QWidget):
    """Wraps the ChatView widget as a page."""

    back_requested = Signal()

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._chat_view = ChatView(api, catalog)
        self._chat_view.back_requested.connect(self.back_requested.emit)
        layout.addWidget(self._chat_view)

    def load_models(self):
        self._chat_view.load_models()

    def start_new_chat(self, model: str = None):
        self._chat_view.start_new_chat(model)

    def open_conversation(self, conv_id: int):
        self._chat_view.open_conversation(conv_id)
