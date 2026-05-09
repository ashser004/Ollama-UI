# Copyright (c) 2026 Ashmith
# Licensed under the MIT License. See LICENSE in the project root for license information.
"""
chat_view.py — Main chat interface widget.
"""

import os
import io
import base64
from PIL import Image
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QScrollArea,
                                QComboBox, QFileDialog, QFrame, QSplitter,
                                QApplication)
from PySide6.QtCore import Qt, Signal, Slot, QTimer, QStandardPaths
from PySide6.QtGui import QFont, QCursor, QKeyEvent

from app.theme import COLORS, accent_button_style
from app.widgets.chat_bubble import ChatBubble
from app.widgets.image_preview import AttachmentPreviewStrip, ImagePreviewOverlay
from app.ollama.api import OllamaAPI
from app.ollama.model_catalog import ModelCatalog
from app import database as db


class ChatInput(QTextEdit):
    """Custom text input that sends on Enter (Shift+Enter for newline)."""

    send_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type your message...")
        self.setFixedHeight(60)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS.bg_surface};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                border-radius: 14px;
                padding: 10px 16px;
                font-size: 13px;
            }}
            QTextEdit:focus {{
                border-color: {COLORS.accent_primary};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                text = self.toPlainText().strip()
                if text:
                    self.send_requested.emit(text)
                    self.clear()
        else:
            super().keyPressEvent(event)


class ChatView(QWidget):
    """Full chat interface with message history and streaming responses."""

    back_requested = Signal()
    navigate_to_discover = Signal()
    navigate_to_home = Signal()

    # Smart context budget caps (tokens) — prevents excessive RAM usage
    # We don't fill the entire context window; we use practical, efficient limits
    _SMALL_CTX_BUDGET = 4096      # for models with ≤8K context
    _MEDIUM_CTX_BUDGET = 8192     # for models with ≤32K context
    _LARGE_CTX_BUDGET = 16384     # for models with >32K context
    _RESPONSE_RESERVE_RATIO = 0.4 # reserve 40% of budget for the model's response

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(parent)
        self._api = api
        self._catalog = catalog
        self._conversation_id: int | None = None
        self._current_model: str = ""
        self._is_streaming = False
        self._is_generating_image = False
        self._current_bubble: ChatBubble | None = None
        self._current_response = ""
        self._attached_images: list[str] = []
        self._image_overlay: ImagePreviewOverlay | None = None
        self._imagegen_enabled = False
        self._imagegen_worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = QWidget()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_surface};
                border-bottom: 1px solid {COLORS.border_default};
            }}
        """)

        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(16, 0, 16, 0)

        # Back button
        back_btn = QPushButton("← Back")
        back_btn.setCursor(QCursor(Qt.PointingHandCursor))
        back_btn.setFixedSize(90, 36)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_hover};
                border-radius: 10px;
                font-size: 13px;
                font-weight: 600;
                padding: 0 12px;
                text-align: left;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
                border-color: {COLORS.accent_primary};
            }}
        """)
        back_btn.clicked.connect(self.back_requested.emit)
        top_layout.addWidget(back_btn)

        top_layout.addSpacing(12)

        # Model selector
        model_picker = QWidget()
        model_picker.setFixedHeight(36)
        model_picker.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_elevated};
                border: 1px solid {COLORS.border_hover};
                border-radius: 12px;
            }}
        """)
        model_picker_layout = QHBoxLayout(model_picker)
        model_picker_layout.setContentsMargins(12, 0, 10, 0)
        model_picker_layout.setSpacing(8)

        self._model_combo = QComboBox()
        self._model_combo.setFixedHeight(30)
        self._model_combo.setMinimumWidth(180)
        self._model_combo.setStyleSheet(f"""
            QComboBox {{
                background: transparent;
                color: {COLORS.text_primary};
                border: none;
                padding: 0px;
                font-size: 13px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 0px;
            }}
            QComboBox::down-arrow {{
                image: none;
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_default};
                selection-background-color: {COLORS.bg_hover};
                selection-color: {COLORS.text_primary};
                outline: none;
            }}
        """)
        self._model_combo.currentTextChanged.connect(self._on_model_changed)
        model_picker_layout.addWidget(self._model_combo, 1)

        model_arrow = QLabel("▾")
        model_arrow.setStyleSheet(f"""
            color: {COLORS.accent_primary};
            background: transparent;
            font-size: 14px;
            font-weight: 700;
        """)
        model_arrow.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        model_picker_layout.addWidget(model_arrow)

        model_picker.mousePressEvent = lambda event, combo=self._model_combo: combo.showPopup()
        top_layout.addWidget(model_picker)

        top_layout.addStretch()

        # New chat button
        new_btn = QPushButton("+ New")
        new_btn.setCursor(QCursor(Qt.PointingHandCursor))
        new_btn.setFixedHeight(32)
        new_btn.setStyleSheet(accent_button_style())
        new_btn.clicked.connect(self._new_chat)
        top_layout.addWidget(new_btn)

        layout.addWidget(top_bar)

        # Main area: chat history sidebar + message area
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {COLORS.border_default}; width: 1px; }}")

        # Chat history sidebar
        history_panel = QWidget()
        history_panel.setFixedWidth(220)
        history_panel.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_dark};
                border-right: 1px solid {COLORS.border_default};
            }}
        """)

        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(8, 12, 8, 8)
        history_layout.setSpacing(4)

        history_title = QLabel("Chat History")
        history_title.setStyleSheet(f"""
            font-size: 12px; font-weight: 600;
            color: {COLORS.text_muted}; background: transparent;
            padding: 4px 8px;
        """)
        history_layout.addWidget(history_title)

        self._history_scroll = QScrollArea()
        self._history_scroll.setWidgetResizable(True)
        self._history_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._history_container = QWidget()
        self._history_container.setStyleSheet("background: transparent;")
        self._history_list = QVBoxLayout(self._history_container)
        self._history_list.setSpacing(2)
        self._history_list.setContentsMargins(0, 0, 0, 0)
        self._history_list.addStretch()

        self._history_scroll.setWidget(self._history_container)
        history_layout.addWidget(self._history_scroll, 1)

        splitter.addWidget(history_panel)

        # Message area
        msg_area = QWidget()
        msg_area.setStyleSheet("background: transparent;")
        msg_layout = QVBoxLayout(msg_area)
        msg_layout.setContentsMargins(0, 0, 0, 0)
        msg_layout.setSpacing(0)

        # Messages scroll
        self._msg_scroll = QScrollArea()
        self._msg_scroll.setWidgetResizable(True)
        self._msg_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._msg_container = QWidget()
        self._msg_container.setStyleSheet("background: transparent;")
        self._msg_list = QVBoxLayout(self._msg_container)
        self._msg_list.setSpacing(4)
        self._msg_list.setContentsMargins(24, 16, 24, 16)
        self._msg_list.addStretch()

        self._msg_scroll.setWidget(self._msg_container)
        msg_layout.addWidget(self._msg_scroll, 1)

        self._attachments_strip = AttachmentPreviewStrip()
        self._attachments_strip.remove_requested.connect(self._remove_attachment)
        self._attachments_strip.open_requested.connect(self._open_attachment_preview)
        msg_layout.addWidget(self._attachments_strip)

        # Input area
        input_area = QWidget()
        input_area.setFixedHeight(90)
        input_area.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS.bg_dark};
                border-top: 1px solid {COLORS.border_default};
            }}
        """)

        input_layout = QHBoxLayout(input_area)
        input_layout.setContentsMargins(20, 10, 20, 10)
        input_layout.setSpacing(10)

        # Text input
        self._input = ChatInput()
        self._input.send_requested.connect(self._send_message)
        input_layout.addWidget(self._input, 1)

        # Image attachment button
        self._clip_btn = QPushButton("📎")
        self._clip_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._clip_btn.setFixedSize(38, 38)
        self._clip_btn.setToolTip("Attach up to 5 images")
        self._clip_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_primary};
                border: 1px solid {COLORS.border_hover};
                border-radius: 19px;
                padding: 0px;
                font-size: 18px;
                font-weight: 700;
            }}
            QPushButton:hover {{ background: {COLORS.bg_hover}; border-color: {COLORS.accent_primary}; }}
        """)
        self._clip_btn.clicked.connect(self._attach_image)
        input_layout.addWidget(self._clip_btn)

        # Send button
        self._send_btn = QPushButton("Send")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._send_btn.setFixedSize(74, 44)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.accent_gradient_start}, stop:1 {COLORS.accent_gradient_end});
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 22px;
                font-size: 13px;
                font-weight: 700;
                padding: 0 18px;
            }}
            QPushButton:hover {{
                background: {COLORS.accent_hover};
            }}
        """)
        self._send_btn.clicked.connect(lambda: self._send_message(self._input.toPlainText().strip()))
        input_layout.addWidget(self._send_btn)

        # Stop button (hidden by default)
        self._stop_btn = QPushButton("STOP")
        self._stop_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._stop_btn.setFixedSize(72, 44)
        self._stop_btn.setVisible(False)
        self._stop_btn.setToolTip("Stop generating")
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.error};
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 22px;
                font-size: 11px;
                font-weight: 800;
                padding: 0 12px;
            }}
            QPushButton:hover {{ background: #f87171; }}
        """)
        self._stop_btn.clicked.connect(self._stop_generation)
        input_layout.addWidget(self._stop_btn)

        msg_layout.addWidget(input_area)
        splitter.addWidget(msg_area)

        splitter.setSizes([220, 600])
        layout.addWidget(splitter, 1)

        # ═══ Empty state overlay (shown when no models installed) ═══
        self._empty_overlay = QWidget(self)
        self._empty_overlay.setVisible(False)
        self._empty_overlay.setStyleSheet(f"background-color: {COLORS.bg_base};")

        overlay_layout = QVBoxLayout(self._empty_overlay)
        overlay_layout.setContentsMargins(32, 32, 32, 32)
        overlay_layout.setAlignment(Qt.AlignCenter)

        empty_card = QWidget()
        empty_card.setMaximumWidth(420)
        empty_card.setStyleSheet("background: transparent;")

        empty_card_layout = QVBoxLayout(empty_card)
        empty_card_layout.setContentsMargins(24, 12, 24, 12)
        empty_card_layout.setSpacing(12)
        empty_card_layout.setAlignment(Qt.AlignCenter)

        empty_icon = QLabel("◇")
        empty_icon.setAlignment(Qt.AlignCenter)
        empty_icon.setStyleSheet(f"font-size: 42px; color: {COLORS.accent_primary}; background: transparent;")
        empty_card_layout.addWidget(empty_icon)

        empty_title = QLabel("No Models Installed")
        empty_title.setAlignment(Qt.AlignCenter)
        empty_title.setStyleSheet(f"""
            font-size: 20px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        empty_card_layout.addWidget(empty_title)

        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setFrameShadow(QFrame.Plain)
        divider.setFixedHeight(1)
        divider.setMaximumWidth(240)
        divider.setStyleSheet(f"background-color: {COLORS.border_default}; border: none;")
        empty_card_layout.addWidget(divider)

        empty_desc = QLabel("You need to download an AI model before\nyou can start chatting.")
        empty_desc.setAlignment(Qt.AlignCenter)
        empty_desc.setWordWrap(True)
        empty_desc.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent; line-height: 1.5;")
        empty_card_layout.addWidget(empty_desc)

        empty_card_layout.addSpacing(12)

        discover_btn = QPushButton("Browse & Install Models")
        discover_btn.setCursor(QCursor(Qt.PointingHandCursor))
        discover_btn.setFixedHeight(44)
        discover_btn.setStyleSheet(accent_button_style())
        discover_btn.clicked.connect(self.navigate_to_discover.emit)
        empty_card_layout.addWidget(discover_btn)

        overlay_layout.addWidget(empty_card, alignment=Qt.AlignCenter)

        # ═══ Imagegen-not-enabled overlay ═══
        self._imagegen_overlay = QWidget(self)
        self._imagegen_overlay.setVisible(False)
        self._imagegen_overlay.setStyleSheet(f"background-color: {COLORS.bg_base};")

        ig_overlay_layout = QVBoxLayout(self._imagegen_overlay)
        ig_overlay_layout.setContentsMargins(32, 32, 32, 32)
        ig_overlay_layout.setAlignment(Qt.AlignCenter)

        ig_card = QWidget()
        ig_card.setMaximumWidth(420)
        ig_card.setStyleSheet("background: transparent;")

        ig_card_layout = QVBoxLayout(ig_card)
        ig_card_layout.setContentsMargins(24, 12, 24, 12)
        ig_card_layout.setSpacing(12)
        ig_card_layout.setAlignment(Qt.AlignCenter)

        ig_icon = QLabel("🎨")
        ig_icon.setAlignment(Qt.AlignCenter)
        ig_icon.setStyleSheet(f"font-size: 42px; background: transparent;")
        ig_card_layout.addWidget(ig_icon)

        ig_title = QLabel("Image Generation Engine Not Enabled")
        ig_title.setAlignment(Qt.AlignCenter)
        ig_title.setStyleSheet(f"""
            font-size: 20px; font-weight: 700;
            color: {COLORS.text_primary}; background: transparent;
        """)
        ig_card_layout.addWidget(ig_title)

        ig_divider = QFrame()
        ig_divider.setFrameShape(QFrame.HLine)
        ig_divider.setFrameShadow(QFrame.Plain)
        ig_divider.setFixedHeight(1)
        ig_divider.setMaximumWidth(240)
        ig_divider.setStyleSheet(f"background-color: {COLORS.border_default}; border: none;")
        ig_card_layout.addWidget(ig_divider)

        ig_desc = QLabel("Enable the image generation engine from\nthe Home page to use image models.")
        ig_desc.setAlignment(Qt.AlignCenter)
        ig_desc.setWordWrap(True)
        ig_desc.setStyleSheet(f"color: {COLORS.text_secondary}; font-size: 13px; background: transparent; line-height: 1.5;")
        ig_card_layout.addWidget(ig_desc)

        ig_card_layout.addSpacing(12)

        go_home_btn = QPushButton("← Go to Home")
        go_home_btn.setCursor(QCursor(Qt.PointingHandCursor))
        go_home_btn.setFixedHeight(44)
        go_home_btn.setStyleSheet(accent_button_style())
        go_home_btn.clicked.connect(self.navigate_to_home.emit)
        ig_card_layout.addWidget(go_home_btn)

        ig_overlay_layout.addWidget(ig_card, alignment=Qt.AlignCenter)

    def load_models(self):
        """Populate model selector with installed models."""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()

        # Ollama models (always shown)
        models = self._api.list_models()
        for m in models:
            name = m.get("name", "Unknown")
            self._model_combo.addItem(name)

        # Image-gen models (only shown when engine is enabled)
        if self._imagegen_enabled:
            from app.services.imagegen_download import is_imagegen_model_installed
            for cat_model in self._catalog.get_imagegen_models():
                tag = cat_model.get("tag", "")
                if tag and is_imagegen_model_installed(tag):
                    display_name = f"🎨 {cat_model.get('name', tag)}"
                    self._model_combo.addItem(display_name, tag)

        self._model_combo.blockSignals(False)
        self._sync_current_model_selection()

        # Show/hide empty state overlay
        has_models = self._model_combo.count() > 0
        self._empty_overlay.setVisible(not has_models)

    def _sync_current_model_selection(self, preferred_model: str | None = None):
        """Keep the combo box and active model state aligned."""
        if self._model_combo.count() == 0:
            self._current_model = ""
            self._update_input_capabilities()
            return

        target_model = preferred_model or self._current_model
        index = self._model_combo.findText(target_model) if target_model else -1
        if index < 0:
            index = 0

        self._model_combo.blockSignals(True)
        self._model_combo.setCurrentIndex(index)
        self._model_combo.blockSignals(False)

        self._current_model = self._model_combo.currentText()
        self._update_input_capabilities()

    def resizeEvent(self, event):
        """Keep empty overlay sized to fill the widget."""
        super().resizeEvent(event)
        self._empty_overlay.setGeometry(self.rect())
        self._imagegen_overlay.setGeometry(self.rect())

    def open_conversation(self, conv_id: int):
        """Open an existing conversation."""
        self._clear_attachments()
        self._conversation_id = conv_id
        conv = db.get_conversation(conv_id)
        if conv:
            self._current_model = conv["model"]

        self._sync_current_model_selection(self._current_model)
        self._load_messages()
        self._refresh_history()

    def start_new_chat(self, model: str = None):
        """Start a fresh conversation."""
        if model:
            self._current_model = model

        self._clear_attachments()
        self._conversation_id = None
        self._clear_messages()
        self._sync_current_model_selection(model)
        self._refresh_history()

    def _new_chat(self):
        """Create a new chat."""
        if self._model_combo.count() == 0:
            return  # empty state overlay handles this
        self.start_new_chat()

    def _load_messages(self):
        """Load messages for current conversation."""
        self._clear_messages()
        if self._conversation_id:
            messages = db.get_messages(self._conversation_id)
            for msg in messages:
                bubble = ChatBubble(
                    msg["role"], msg["content"],
                    model=msg.get("model"),
                    images=msg.get("images")
                )
                bubble.copy_requested.connect(self._copy_text)
                self._msg_list.insertWidget(self._msg_list.count() - 1, bubble)
            self._scroll_to_bottom()

    def _clear_messages(self):
        """Remove all message bubbles."""
        while self._msg_list.count() > 1:  # Keep the stretch
            item = self._msg_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _send_message(self, text: str):
        """Send a message to the AI."""
        if not text or self._is_streaming or self._is_generating_image:
            return

        if self._model_combo.count() == 0:
            return

        if not self._current_model or self._model_combo.findText(self._current_model) < 0:
            self._sync_current_model_selection(self._current_model or None)

        # Check if current model is an image-gen model
        if self._is_imagegen_model(self._current_model):
            self._send_to_imagegen(text)
            return

        if self._attached_images and not self._current_model_supports_images():
            self._show_toast(
                "The selected model does not support images. Switch to a vision-capable model first.",
                "warning",
            )
            return

        attachment_paths = self._attached_images.copy()
        try:
            attachment_images = self._encode_attachment_images(attachment_paths)
        except OSError:
            self._show_toast("One or more attached images could not be read.", "error")
            return

        # Create conversation if needed
        if self._conversation_id is None:
            title = text[:40] + "..." if len(text) > 40 else text
            self._conversation_id = db.create_conversation(
                self._current_model, title, False
            )

        # Save user message
        db.add_message(
            self._conversation_id, "user", text,
            model=self._current_model,
            images=attachment_images if attachment_images else None
        )

        # Add user bubble
        user_bubble = ChatBubble("user", text, images=attachment_paths)
        self._msg_list.insertWidget(self._msg_list.count() - 1, user_bubble)

        # ── Smart context management ──
        # Look up model's context window from catalog
        model_ctx_window = self._get_model_context_window()
        ctx_budget = self._compute_context_budget(model_ctx_window)
        num_ctx_for_api = ctx_budget  # tell Ollama how much context to allocate

        # Build messages that fit within the budget (reserve space for response)
        available_tokens = int(ctx_budget * (1.0 - self._RESPONSE_RESERVE_RATIO))
        api_messages = self._build_context_messages(available_tokens)

        # Start streaming response
        self._is_streaming = True
        self._current_response = ""
        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._input.clear()

        # Create placeholder assistant bubble
        self._current_bubble = ChatBubble("assistant", "")
        self._current_bubble.copy_requested.connect(self._copy_text)
        self._current_bubble.set_content("", show_cursor=True)
        self._msg_list.insertWidget(self._msg_list.count() - 1, self._current_bubble)
        self._scroll_to_bottom()

        # Start the loading animation (image-aware)
        self._current_bubble.start_loading(has_images=bool(attachment_images))

        # Start stream
        images_b64 = attachment_images if attachment_images else None
        self._clear_attachments()

        worker = self._api.chat_stream(
            self._current_model, api_messages, images_b64,
            num_ctx=num_ctx_for_api
        )
        worker.chunk_received.connect(self._on_chunk)
        worker.finished_signal.connect(self._on_stream_done)
        worker.start()

    # ─── Image Generation Send Path ─────────────────────────────────

    def _send_to_imagegen(self, prompt: str):
        """Handle sending a prompt to the image generation engine."""
        from app.imagegen.manager import ImageGenManager
        from app.services.imagegen_download import get_model_path_by_tag

        # Resolve model tag from display name
        model_tag = self._get_imagegen_tag(self._current_model)
        if not model_tag:
            self._show_toast("Could not find the image model.", "error")
            return

        model_path = get_model_path_by_tag(model_tag)
        if not model_path:
            self._show_toast("Image model file not found on disk.", "error")
            return

        # Create conversation if needed
        if self._conversation_id is None:
            title = f"🎨 {prompt[:36]}..." if len(prompt) > 36 else f"🎨 {prompt}"
            self._conversation_id = db.create_conversation(
                self._current_model, title, False
            )

        # Save user message
        db.add_message(
            self._conversation_id, "user", prompt,
            model=self._current_model
        )

        # Add user bubble
        user_bubble = ChatBubble("user", prompt)
        self._msg_list.insertWidget(self._msg_list.count() - 1, user_bubble)

        # Create assistant placeholder with imagegen loading animation
        self._is_generating_image = True
        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._input.clear()

        self._current_bubble = ChatBubble("assistant", "")
        self._current_bubble.copy_requested.connect(self._copy_text)
        self._current_bubble.set_content("", show_cursor=False)
        self._msg_list.insertWidget(self._msg_list.count() - 1, self._current_bubble)
        self._scroll_to_bottom()

        # Start the imagegen-specific loading animation
        self._current_bubble.start_loading(mode="imagegen")

        # Spawn the generation worker
        mgr = ImageGenManager(self)
        worker = mgr.generate_image(
            model_path=model_path,
            prompt=prompt,
            width=512,
            height=512,
            steps=20
        )
        worker.finished.connect(self._on_imagegen_done)
        self._imagegen_worker = worker
        worker.start()

    @Slot(bool, str)
    def _on_imagegen_done(self, success: bool, result: str):
        """Handle image generation completion."""
        from app.imagegen.manager import ImageGenManager

        self._is_generating_image = False
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)
        self._imagegen_worker = None

        if self._current_bubble:
            self._current_bubble.stop_loading()

        if success:
            # Convert PNG to base64 and clean up temp file
            b64 = ImageGenManager.png_to_base64(result, max_size=512)
            if b64:
                # Save assistant message with generated image
                db.add_message(
                    self._conversation_id, "assistant",
                    "Here is your generated image:",
                    model=self._current_model,
                    images=[b64]
                )

                # Update the bubble to show the image
                if self._current_bubble:
                    self._current_bubble.set_content("Here is your generated image:", show_cursor=False)
                    self._current_bubble.set_model_label(self._current_model)
                    # We need to rebuild the bubble to show the image
                    # Simplest approach: remove placeholder, add a proper bubble
                    idx = self._msg_list.indexOf(self._current_bubble)
                    if idx >= 0:
                        self._current_bubble.deleteLater()
                        new_bubble = ChatBubble(
                            "assistant", "Here is your generated image:",
                            model=self._current_model, images=[b64]
                        )
                        new_bubble.copy_requested.connect(self._copy_text)
                        self._msg_list.insertWidget(idx, new_bubble)
            else:
                if self._current_bubble:
                    self._current_bubble.set_content("Failed to process the generated image.", show_cursor=False)
        else:
            if self._current_bubble:
                error_msg = f"Image generation failed: {result}" if "cancel" not in result.lower() else "Image generation was cancelled."
                self._current_bubble.set_content(error_msg, show_cursor=False)
                content_label = self._current_bubble._content_label
                if content_label:
                    content_label.setStyleSheet(f"color: {COLORS.error}; font-size: 13px; background: transparent;")

        self._current_bubble = None
        self._refresh_history()
        self._scroll_to_bottom()

    @Slot(str)
    def _on_chunk(self, text: str):
        """Handle incoming text chunk from stream."""
        self._current_response += text
        # Stop loading animation on the very first chunk
        if self._current_bubble:
            self._current_bubble.stop_loading()
            self._current_bubble.set_content(self._current_response, show_cursor=True)
        self._scroll_to_bottom()

    @Slot(bool, str)
    def _on_stream_done(self, success: bool, full_response: str):
        """Handle stream completion."""
        self._is_streaming = False
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)

        # Always stop loading animation
        if self._current_bubble:
            self._current_bubble.stop_loading()

        if success and self._current_response:
            # Save assistant message
            db.add_message(
                self._conversation_id, "assistant",
                self._current_response, model=self._current_model
            )

            # Update bubble to remove cursor
            if self._current_bubble:
                self._current_bubble.set_model_label(self._current_model)
                self._current_bubble.set_content(self._current_response, show_cursor=False)
                self._scroll_to_bottom()
        elif not success:
            if self._current_bubble:
                self._current_bubble.set_content(f"Error: {full_response}", show_cursor=False)
                content_label = self._current_bubble._content_label
                if content_label:
                    content_label.setStyleSheet(f"color: {COLORS.error}; font-size: 13px; background: transparent;")

        self._current_bubble = None
        self._current_response = ""
        self._refresh_history()

    def _stop_generation(self):
        """Stop the current streaming response or image generation."""
        if self._is_generating_image and self._imagegen_worker:
            self._imagegen_worker.abort()
        else:
            self._api.stop_chat()

    def _scroll_to_bottom(self):
        """Scroll message area to bottom."""
        QTimer.singleShot(50, lambda: self._msg_scroll.verticalScrollBar().setValue(
            self._msg_scroll.verticalScrollBar().maximum()
        ))

    def refresh(self):
        """Refresh models and chat history from storage."""
        self.load_models()
        self._refresh_history()

    def refresh_history(self):
        """Refresh only the chat history sidebar."""
        self._refresh_history()

    def _current_model_supports_images(self) -> bool:
        """Check whether the currently selected model supports image inputs."""
        if not self._current_model:
            return False

        base = self._current_model.split(":")[0]
        info = self._catalog.get_model_by_tag(self._current_model)
        if not info:
            info = self._catalog.get_model_by_tag(base)
        return bool(info and info.get("supports_images", False))

    def _refresh_attachment_preview(self):
        """Rebuild the attachment preview strip from the current queue."""
        self._attachments_strip.set_attachments(self._attached_images)

    def _clear_attachments(self):
        """Clear queued attachments and hide the preview strip."""
        self._attached_images.clear()
        self._refresh_attachment_preview()

    def _remove_attachment(self, index: int):
        """Remove a queued attachment by index and refresh preview order."""
        if 0 <= index < len(self._attached_images):
            del self._attached_images[index]
            self._refresh_attachment_preview()

    def _open_attachment_preview(self, image_path: str):
        """Open a modal overlay for the selected attachment."""
        if self._image_overlay is not None:
            self._image_overlay.close()
            self._image_overlay = None

        overlay = ImagePreviewOverlay(image_path, parent=self.window())
        overlay.destroyed.connect(lambda *_: setattr(self, "_image_overlay", None))
        self._image_overlay = overlay
        overlay.show_for_parent(self.window())

    def _encode_attachment_images(self, image_paths: list[str]) -> list[str]:
        """Convert selected attachment file paths into optimized base64 strings for Ollama."""
        encoded_images: list[str] = []
        MAX_SIZE = 800

        for image_path in image_paths:
            try:
                with Image.open(image_path) as img:
                    # Convert GIF or specialized formats to standard RGB
                    if img.mode != "RGB":
                        img = img.convert("RGB")

                    # Calculate aspect ratio and resize if needed
                    width, height = img.size
                    if max(width, height) > MAX_SIZE:
                        if width > height:
                            new_width = MAX_SIZE
                            new_height = int(MAX_SIZE * (height / width))
                        else:
                            new_height = MAX_SIZE
                            new_width = int(MAX_SIZE * (width / height))
                        
                        img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

                    # Save optimized image to a temporary RAM buffer
                    buffer = io.BytesIO()
                    img.save(buffer, format="PNG", optimize=True)
                    buffer.seek(0)

                    # Convert the RAM buffer to base64
                    encoded_images.append(base64.b64encode(buffer.read()).decode("utf-8"))
            except Exception as e:
                print(f"Failed to process image {image_path}: {e}")
                
        return encoded_images

    def _on_model_changed(self, model_name: str):
        """Handle model selection change.

        When switching models mid-chat, unloads the old model from
        memory to free RAM before loading the new one.
        """
        if model_name:
            old_model = self._current_model
            self._current_model = model_name

            # Abort any active image generation when switching models
            if self._is_generating_image and self._imagegen_worker:
                self._imagegen_worker.abort()
                self._is_generating_image = False

            # Unload old model from RAM if switching to a different one
            # (only for Ollama models, not imagegen)
            if old_model and old_model != model_name and not self._is_imagegen_model(old_model):
                self._api.unload_model(old_model)

            # Update conversation record so it tracks the active model
            if self._conversation_id:
                db.update_conversation_model(self._conversation_id, model_name)

            self._update_input_capabilities()

            # Hide imagegen overlay when switching to a non-imagegen model
            if self._is_imagegen_model(model_name) and not self._imagegen_enabled:
                self._imagegen_overlay.setVisible(True)
            else:
                self._imagegen_overlay.setVisible(False)

    # ── Smart Context Helpers ──────────────────────────

    def _get_model_context_window(self) -> int:
        """Look up the current model's context window from the catalog."""
        if not self._current_model:
            return 4096

        base = self._current_model.split(":")[0]
        info = (
            self._catalog.get_model_by_tag(base)
            or self._catalog.get_model_by_tag(self._current_model)
        )
        if info:
            return info.get("context_window", 4096)
        return 4096

    def _compute_context_budget(self, model_ctx_window: int) -> int:
        """Choose a practical context budget that balances quality vs RAM.

        We don't fill the entire window (e.g. 128K) — that would waste
        RAM for no real benefit. Instead we pick a sensible cap.
        """
        if model_ctx_window <= 8192:
            return min(model_ctx_window, self._SMALL_CTX_BUDGET)
        if model_ctx_window <= 32768:
            return min(model_ctx_window, self._MEDIUM_CTX_BUDGET)
        return min(model_ctx_window, self._LARGE_CTX_BUDGET)

    def _build_context_messages(self, available_tokens: int) -> list[dict]:
        """Build the message history that fits within the token budget.

        Works newest-first to always include the latest exchange,
        then fills backwards with as much history as fits.
        Assumes ~4 characters per token (rough estimate for English).
        """
        if not self._conversation_id:
            return []

        # Fetch a generous number of recent messages from DB
        all_recent = db.get_recent_messages(self._conversation_id, limit=50)
        if not all_recent:
            return []

        chars_budget = available_tokens * 4  # ~4 chars per token
        selected: list[dict] = []
        used_chars = 0

        # Walk from newest to oldest, picking messages that fit
        for msg in reversed(all_recent):
            content = msg.get("content", "")
            msg_chars = len(content) + 20  # +20 for role/overhead
            if used_chars + msg_chars > chars_budget and selected:
                break  # budget exhausted (but always keep at least 1 message)
            selected.insert(0, {"role": msg["role"], "content": content})
            used_chars += msg_chars

        return selected

    def _update_input_capabilities(self):
        """Show/hide image and file buttons based on model capabilities."""
        if self._current_model:
            # Image-gen models: hide clip button, change placeholder
            if self._is_imagegen_model(self._current_model):
                self._clip_btn.setVisible(False)
                self._input.setPlaceholderText("Describe the image you want to generate...")
                return

            # Restore default placeholder for Ollama models
            self._input.setPlaceholderText("Type your message...")

            base = self._current_model.split(":")[0]
            info = self._catalog.get_model_by_tag(base) or self._catalog.get_model_by_tag(self._current_model)
            if info:
                self._clip_btn.setVisible(info.get("supports_images", False))
                return

        self._clip_btn.setVisible(False)
        self._input.setPlaceholderText("Type your message...")

    # ─── Image Generation Helpers ──────────────────────────────────

    def _is_imagegen_model(self, model_name: str) -> bool:
        """Check if a model name corresponds to an image-gen model."""
        if not model_name:
            return False
        # Strip the 🎨 prefix if present
        clean_name = model_name.replace("🎨 ", "").strip()
        for cat_model in self._catalog.get_imagegen_models():
            if cat_model.get("name") == clean_name or cat_model.get("tag") == clean_name:
                return True
        return False

    def _get_imagegen_tag(self, model_name: str) -> str | None:
        """Get the catalog tag for an image-gen model from its display name."""
        if not model_name:
            return None
        clean_name = model_name.replace("🎨 ", "").strip()
        for cat_model in self._catalog.get_imagegen_models():
            if cat_model.get("name") == clean_name or cat_model.get("tag") == clean_name:
                return cat_model.get("tag")
        # Check combo box data (we store tag as userData)
        idx = self._model_combo.findText(model_name)
        if idx >= 0:
            data = self._model_combo.itemData(idx)
            if data:
                return data
        return None

    def set_imagegen_enabled(self, enabled: bool):
        """Called by MainWindow when the home toggle changes."""
        self._imagegen_enabled = enabled

        if not enabled:
            # If currently using an imagegen model, switch away
            if self._is_imagegen_model(self._current_model):
                # Abort any active generation
                if self._is_generating_image and self._imagegen_worker:
                    self._imagegen_worker.abort()
                    self._is_generating_image = False

                # Switch to first Ollama model
                if self._model_combo.count() > 0:
                    for i in range(self._model_combo.count()):
                        name = self._model_combo.itemText(i)
                        if not self._is_imagegen_model(name):
                            self._model_combo.setCurrentIndex(i)
                            break

            self._imagegen_overlay.setVisible(False)

        # Reload models to add/remove imagegen models from selector
        self.load_models()

    def _attach_image(self):
        """Open a multi-select image picker and queue up to five images."""
        if not self._current_model_supports_images():
            self._show_toast(
                "The selected model does not support images. Switch to a vision-capable model first.",
                "warning",
            )
            return

        remaining_slots = max(0, 5 - len(self._attached_images))
        if remaining_slots == 0:
            self._show_toast("You can attach up to 5 images per message.", "warning")
            return

        start_dir = QStandardPaths.writableLocation(QStandardPaths.DownloadLocation) or os.path.expanduser("~")
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images",
            start_dir,
            "Images (*.jpg *.jpeg *.png *.ico *.gif)",
        )
        if not paths:
            return

        accepted_paths: list[str] = []
        for path in paths:
            if len(accepted_paths) >= remaining_slots:
                break
            if os.path.isfile(path):
                accepted_paths.append(path)

        if not accepted_paths:
            return

        self._attached_images.extend(accepted_paths)
        self._refresh_attachment_preview()

        if len(paths) > len(accepted_paths):
            self._show_toast("Only the first five selected images were attached.", "warning")

    def _show_toast(self, message: str, toast_type: str = "info"):
        """Show a toast notification via the parent window."""
        from app.widgets.popup import ToastNotification
        parent_window = self.window()
        if parent_window and parent_window.isVisible():
            toast = ToastNotification(message, toast_type, parent=parent_window)
            toast.show_at(parent_window)

    def _attach_file(self):
        """Open file picker — shows popup if model doesn't support it."""
        from app.widgets.popup import ToastNotification
        toast = ToastNotification(
            "File upload is not supported by this model.",
            "warning", parent=self.window()
        )
        toast.show_at(self.window())

    def _copy_text(self, text: str):
        """Copy text to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def _refresh_history(self):
        """Refresh chat history sidebar."""
        # Clear
        while self._history_list.count() > 1:
            item = self._history_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        conversations = db.get_conversations()
        for conv in conversations[:30]:  # Max 30 shown
            btn = QPushButton(conv["title"])
            btn.setCursor(QCursor(Qt.PointingHandCursor))
            btn.setFixedHeight(48)
            btn.setToolTip(f"{conv['model']} • {conv['created_at'][:10]}")

            is_active = conv["id"] == self._conversation_id
            if is_active:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {COLORS.bg_elevated};
                        color: {COLORS.text_primary};
                        border: 1px solid {COLORS.accent_primary}66;
                        border-radius: 10px;
                        text-align: left;
                        padding: 8px 14px;
                        font-size: 13px;
                        font-weight: 600;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        color: {COLORS.text_secondary};
                        border: none;
                        border-radius: 10px;
                        text-align: left;
                        padding: 8px 14px;
                        font-size: 13px;
                    }}
                    QPushButton:hover {{
                        background: {COLORS.bg_surface};
                        color: {COLORS.text_primary};
                    }}
                """)

            btn.clicked.connect(lambda checked, cid=conv["id"]: self.open_conversation(cid))
            self._history_list.insertWidget(self._history_list.count() - 1, btn)
