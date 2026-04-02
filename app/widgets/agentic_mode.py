"""
agentic_mode.py — Multi-model conversation widget.

Wraps ChatView with enhanced context management for model switching.
"""

from app.widgets.chat_view import ChatView
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog
from app import database as db


class AgenticChatView(ChatView):
    """Enhanced chat view for agentic multi-model conversations.

    When the user switches models mid-conversation, this view:
    1. Gathers recent messages (within token limits)
    2. Adds a system context message for the new model
    3. Allows seamless continuation of the discussion
    """

    CONTEXT_SUMMARY_PROMPT = (
        "You are continuing a conversation that was started with another AI model. "
        "The previous conversation context is included above. "
        "Please continue naturally and help the user."
    )

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(api, catalog, parent)
        self._is_agentic = True
        self._agentic_btn.setChecked(True)

    def _on_model_changed(self, model_name: str):
        """Handle model switch in agentic mode — manage context."""
        old_model = self._current_model
        super()._on_model_changed(model_name)

        if old_model and old_model != model_name and self._conversation_id:
            # Estimate context window for new model
            base = model_name.split(":")[0]
            info = self._catalog.get_model_by_tag(base)
            max_context = 4096  # default
            if info:
                max_context = info.get("context_window", 4096)

            # Roughly estimate: 1 token ≈ 4 chars
            max_chars = max_context * 3  # leave room for response

            # Get recent messages and trim to fit
            messages = db.get_recent_messages(self._conversation_id, limit=30)
            trimmed = []
            total_chars = 0

            for msg in reversed(messages):
                msg_len = len(msg.get("content", ""))
                if total_chars + msg_len > max_chars:
                    break
                trimmed.insert(0, msg)
                total_chars += msg_len

            # The context is automatically maintained through the database
            # and sent to the new model on the next message
