"""
chat_view.py — Main chat interface widget.
"""

import os
import base64
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                                QPushButton, QTextEdit, QScrollArea,
                                QComboBox, QFileDialog, QFrame, QSplitter,
                                QApplication)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QFont, QCursor, QKeyEvent

from app.theme import COLORS, accent_button_style
from app.widgets.chat_bubble import ChatBubble
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

    def __init__(self, api: OllamaAPI, catalog: ModelCatalog, parent=None):
        super().__init__(parent)
        self._api = api
        self._catalog = catalog
        self._conversation_id: int | None = None
        self._current_model: str = ""
        self._is_streaming = False
        self._current_bubble: ChatBubble | None = None
        self._current_response = ""
        self._is_agentic = False
        self._attached_images: list[str] = []

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

        # Agentic mode toggle
        self._agentic_btn = QPushButton("~ Agentic Mode")
        self._agentic_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._agentic_btn.setFixedHeight(32)
        self._agentic_btn.setCheckable(True)
        self._agentic_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_elevated};
                color: {COLORS.text_secondary};
                border: 1px solid {COLORS.border_default};
                border-radius: 16px;
                padding: 4px 16px;
                font-size: 12px;
            }}
            QPushButton:checked {{
                background: {COLORS.accent_primary}22;
                color: {COLORS.accent_primary};
                border-color: {COLORS.accent_primary}44;
            }}
            QPushButton:hover {{
                background: {COLORS.bg_hover};
            }}
        """)
        self._agentic_btn.toggled.connect(self._toggle_agentic)
        top_layout.addWidget(self._agentic_btn)

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

        # Attachment buttons
        self._img_btn = QPushButton("□")
        self._img_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._img_btn.setFixedSize(36, 36)
        self._img_btn.setToolTip("Attach image")
        self._img_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 18px;
                font-size: 16px;
            }}
            QPushButton:hover {{ background: {COLORS.bg_hover}; }}
        """)
        self._img_btn.clicked.connect(self._attach_image)
        input_layout.addWidget(self._img_btn)

        self._file_btn = QPushButton("⎘")
        self._file_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._file_btn.setFixedSize(36, 36)
        self._file_btn.setToolTip("Attach file")
        self._file_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.bg_surface};
                border: 1px solid {COLORS.border_default};
                border-radius: 18px;
                font-size: 16px;
            }}
            QPushButton:hover {{ background: {COLORS.bg_hover}; }}
        """)
        self._file_btn.clicked.connect(self._attach_file)
        input_layout.addWidget(self._file_btn)

        # Text input
        self._input = ChatInput()
        self._input.send_requested.connect(self._send_message)
        input_layout.addWidget(self._input, 1)

        # Send button
        self._send_btn = QPushButton("➤")
        self._send_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._send_btn.setFixedSize(44, 44)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {COLORS.accent_gradient_start}, stop:1 {COLORS.accent_gradient_end});
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 22px;
                font-size: 18px;
            }}
            QPushButton:hover {{
                background: {COLORS.accent_hover};
            }}
        """)
        self._send_btn.clicked.connect(lambda: self._send_message(self._input.toPlainText().strip()))
        input_layout.addWidget(self._send_btn)

        # Stop button (hidden by default)
        self._stop_btn = QPushButton("⬛")
        self._stop_btn.setCursor(QCursor(Qt.PointingHandCursor))
        self._stop_btn.setFixedSize(44, 44)
        self._stop_btn.setVisible(False)
        self._stop_btn.setToolTip("Stop generating")
        self._stop_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS.error};
                color: {COLORS.text_on_accent};
                border: none;
                border-radius: 22px;
                font-size: 14px;
            }}
            QPushButton:hover {{ background: #ef4444; }}
        """)
        self._stop_btn.clicked.connect(self._stop_generation)
        input_layout.addWidget(self._stop_btn)

        msg_layout.addWidget(input_area)
        splitter.addWidget(msg_area)

        splitter.setSizes([220, 600])
        layout.addWidget(splitter, 1)

        # Attachment indicator
        self._attach_label = QLabel("")
        self._attach_label.setVisible(False)
        self._attach_label.setStyleSheet(f"""
            color: {COLORS.accent_primary}; font-size: 11px;
            background: {COLORS.bg_surface}; padding: 4px 12px;
            border-radius: 8px;
        """)

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

    def load_models(self):
        """Populate model selector with installed models."""
        self._model_combo.blockSignals(True)
        self._model_combo.clear()

        models = self._api.list_models()
        for m in models:
            name = m.get("name", "Unknown")
            self._model_combo.addItem(name)

        if self._current_model:
            idx = self._model_combo.findText(self._current_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)

        self._model_combo.blockSignals(False)
        self._update_input_capabilities()

        # Show/hide empty state overlay
        has_models = self._model_combo.count() > 0
        self._empty_overlay.setVisible(not has_models)

    def resizeEvent(self, event):
        """Keep empty overlay sized to fill the widget."""
        super().resizeEvent(event)
        self._empty_overlay.setGeometry(self.rect())

    def open_conversation(self, conv_id: int):
        """Open an existing conversation."""
        self._conversation_id = conv_id
        conv = db.get_conversation(conv_id)
        if conv:
            self._current_model = conv["model"]
            self._is_agentic = bool(conv["is_agentic"])
            self._agentic_btn.setChecked(self._is_agentic)

            # Set model in combo
            idx = self._model_combo.findText(self._current_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)

        self._load_messages()
        self._refresh_history()

    def start_new_chat(self, model: str = None):
        """Start a fresh conversation."""
        if model:
            self._current_model = model
            idx = self._model_combo.findText(model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
        elif self._model_combo.count() > 0:
            self._current_model = self._model_combo.currentText()

        self._conversation_id = None
        self._clear_messages()
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
        if not text or self._is_streaming:
            return

        if not self._current_model or self._model_combo.count() == 0:
            return

        # Create conversation if needed
        if self._conversation_id is None:
            title = text[:40] + "..." if len(text) > 40 else text
            self._conversation_id = db.create_conversation(
                self._current_model, title, self._is_agentic
            )

        # Save user message
        db.add_message(
            self._conversation_id, "user", text,
            model=self._current_model,
            images=self._attached_images if self._attached_images else None
        )

        # Add user bubble
        user_bubble = ChatBubble("user", text, images=self._attached_images)
        self._msg_list.insertWidget(self._msg_list.count() - 1, user_bubble)

        # Prepare API messages
        recent = db.get_recent_messages(self._conversation_id, limit=20)
        api_messages = []
        for msg in recent:
            api_msg = {"role": msg["role"], "content": msg["content"]}
            api_messages.append(api_msg)

        # Start streaming response
        self._is_streaming = True
        self._current_response = ""
        self._send_btn.setVisible(False)
        self._stop_btn.setVisible(True)
        self._input.clear()

        # Create placeholder assistant bubble
        self._current_bubble = ChatBubble(
            "assistant", "▊",
            model=self._current_model if self._is_agentic else None
        )
        self._current_bubble.copy_requested.connect(self._copy_text)
        self._msg_list.insertWidget(self._msg_list.count() - 1, self._current_bubble)
        self._scroll_to_bottom()

        # Start stream
        images_b64 = self._attached_images.copy() if self._attached_images else None
        self._attached_images.clear()

        worker = self._api.chat_stream(self._current_model, api_messages, images_b64)
        worker.chunk_received.connect(self._on_chunk)
        worker.finished_signal.connect(self._on_stream_done)
        worker.start()

    @Slot(str)
    def _on_chunk(self, text: str):
        """Handle incoming text chunk from stream."""
        self._current_response += text
        # Update bubble content
        if self._current_bubble:
            # Re-create the content label
            content_label = self._current_bubble.findChild(QLabel)
            if content_label:
                # Get all QLabels and update the content one
                labels = self._current_bubble.findChildren(QLabel)
                for label in labels:
                    if label.text().endswith("▊") or label.textInteractionFlags() & Qt.TextSelectableByMouse:
                        label.setText(self._current_response + " ▊")
                        break
        self._scroll_to_bottom()

    @Slot(bool, str)
    def _on_stream_done(self, success: bool, full_response: str):
        """Handle stream completion."""
        self._is_streaming = False
        self._send_btn.setVisible(True)
        self._stop_btn.setVisible(False)

        if success and self._current_response:
            # Save assistant message
            db.add_message(
                self._conversation_id, "assistant",
                self._current_response, model=self._current_model
            )

            # Update bubble to remove cursor
            if self._current_bubble:
                labels = self._current_bubble.findChildren(QLabel)
                for label in labels:
                    if label.textInteractionFlags() & Qt.TextSelectableByMouse:
                        label.setText(self._current_response)
                        break
        elif not success:
            if self._current_bubble:
                labels = self._current_bubble.findChildren(QLabel)
                for label in labels:
                    if label.textInteractionFlags() & Qt.TextSelectableByMouse:
                        label.setText(f"Error: {full_response}")
                        label.setStyleSheet(f"color: {COLORS.error}; font-size: 13px; background: transparent;")
                        break

        self._current_bubble = None
        self._current_response = ""
        self._refresh_history()

    def _stop_generation(self):
        """Stop the current streaming response."""
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

    def _on_model_changed(self, model_name: str):
        """Handle model selection change."""
        if model_name:
            self._current_model = model_name
            if self._is_agentic and self._conversation_id:
                db.update_conversation_model(self._conversation_id, model_name)
            self._update_input_capabilities()

    def _toggle_agentic(self, checked: bool):
        """Toggle agentic mode."""
        self._is_agentic = checked
        if self._conversation_id:
            # Re-create conversation as agentic if toggled mid-chat
            conv = db.get_conversation(self._conversation_id)
            if conv:
                pass  # Allow toggling

    def _update_input_capabilities(self):
        """Show/hide image and file buttons based on model capabilities."""
        if self._current_model:
            base = self._current_model.split(":")[0]
            info = self._catalog.get_model_by_tag(base) or self._catalog.get_model_by_tag(self._current_model)
            if info:
                self._img_btn.setVisible(info.get("supports_images", False))
                self._file_btn.setVisible(info.get("supports_files", False))
                return

        self._img_btn.setVisible(False)
        self._file_btn.setVisible(False)

    def _attach_image(self):
        """Open image file picker."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "",
            "Images (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if path:
            try:
                with open(path, "rb") as f:
                    b64 = base64.b64encode(f.read()).decode("utf-8")
                    self._attached_images.append(b64)
            except Exception:
                pass

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
