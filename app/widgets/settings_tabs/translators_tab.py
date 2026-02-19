"""
Translators tab for settings dialog.

Provides interface for configuring translation providers, API keys,
model selection, and provider-specific options.
"""

import asyncio
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox, QDoubleSpinBox,
    QSpinBox, QCheckBox, QTabWidget, QFormLayout, QTextEdit,
    QMessageBox, QProgressBar, QListWidget, QListWidgetItem
)
from PySide6.QtCore import Qt, Signal, QThread, QObject, QTimer
from PySide6.QtGui import QFont, QPixmap, QIcon

from app.config import ConfigManager, ValidationResult, TranslationProvider, SettingsSchema


class ConnectionTestWorker(QObject):
    """Worker for testing API connections."""
    
    test_complete = Signal(str, bool, str)  # provider, success, message
    
    def __init__(self, provider: str, api_key: str, model: str, base_url: str = ""):
        super().__init__()
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
    
    def run(self):
        """Test the API connection."""
        try:
            success, message = self._test_connection()
            self.test_complete.emit(self.provider, success, message)
        except Exception as e:
            self.test_complete.emit(self.provider, False, str(e))
    
    def _test_connection(self) -> tuple[bool, str]:
        """Test the actual API connection."""
        # This is a placeholder - actual implementation would test the APIs
        # For now, just validate that required fields are filled
        
        if not self.api_key:
            return False, "API key is required"
        
        if self.provider == TranslationProvider.OPENAI.value:
            if len(self.api_key) < 10 or not self.api_key.startswith(('sk-', 'pk-')):
                return False, "Invalid OpenAI API key format"
            return True, "Connection successful (simulated)"
            
        elif self.provider == TranslationProvider.ANTHROPIC.value:
            if len(self.api_key) < 10 or not self.api_key.startswith('sk-'):
                return False, "Invalid Anthropic API key format"
            return True, "Connection successful (simulated)"

        elif self.provider == TranslationProvider.OPENROUTER.value:
            if len(self.api_key) < 10 or not self.api_key.startswith('sk-or-'):
                return False, "Invalid OpenRouter API key format"
            return True, "Connection successful (simulated)"

        elif self.provider == TranslationProvider.LM_STUDIO.value:
            if not self.base_url:
                return False, "Base URL is required for LM Studio"
            if not self.base_url.startswith(('http://', 'https://')):
                return False, "Base URL must start with http:// or https://"
            return True, "Connection successful (simulated)"
        
        return False, "Unknown provider"


class ModelFetchWorker(QObject):
    """Worker for fetching available models from a provider API."""

    models_fetched = Signal(list)   # list of (id, display_name) tuples
    fetch_failed = Signal(str)      # error message

    def __init__(self, provider: str, api_key: str):
        super().__init__()
        self.provider = provider
        self.api_key = api_key

    def run(self):
        try:
            models = self._fetch_models()
            self.models_fetched.emit(models)
        except Exception as e:
            self.fetch_failed.emit(str(e))

    def _fetch_models(self) -> list:
        import urllib.request
        import json

        headers = {"Authorization": f"Bearer {self.api_key}"}

        if self.provider == TranslationProvider.OPENAI.value:
            req = urllib.request.Request(
                "https://api.openai.com/v1/models",
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            # Keep only chat-capable models; exclude embeddings, TTS, Whisper, DALL-E, etc.
            exclude = ("embedding", "whisper", "tts", "dall-e", "audio",
                       "transcribe", "realtime", "babbage", "davinci", "ada", "curie")
            models = [
                (m["id"], m["id"])
                for m in data["data"]
                if not any(ex in m["id"].lower() for ex in exclude)
            ]
            return sorted(models, key=lambda x: x[0])

        elif self.provider == TranslationProvider.OPENROUTER.value:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/models",
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            models = [
                (m["id"], m.get("name", m["id"]))
                for m in data["data"]
            ]
            return sorted(models, key=lambda x: x[0])

        return []


class SecureLineEdit(QLineEdit):
    """Secure password-style line edit for API keys."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self._is_revealed = False
        
        # Add reveal button
        self._create_reveal_button()
        
    def _create_reveal_button(self):
        """Create the reveal/hide button."""
        self.reveal_action = self.addAction(
            QIcon(),  # Would use actual icons in production
            QLineEdit.TrailingPosition
        )
        self.reveal_action.setText("👁")
        self.reveal_action.setToolTip("Show/Hide API key")
        self.reveal_action.triggered.connect(self._toggle_reveal)
    
    def _toggle_reveal(self):
        """Toggle password reveal."""
        if self._is_revealed:
            self.setEchoMode(QLineEdit.Password)
            self.reveal_action.setText("👁")
            self.reveal_action.setToolTip("Show API key")
        else:
            self.setEchoMode(QLineEdit.Normal)
            self.reveal_action.setText("🙈")
            self.reveal_action.setToolTip("Hide API key")
        
        self._is_revealed = not self._is_revealed


class ProviderConfigWidget(QWidget):
    """Configuration widget for a single translation provider."""
    
    settings_changed = Signal()
    test_requested = Signal(str)  # provider name
    
    def __init__(self, provider: TranslationProvider, parent=None):
        super().__init__(parent)

        self.provider = provider
        self._widgets = {}
        self._fetched_models = []       # list of (id, name) tuples
        self._model_list = None         # QListWidget (openai/openrouter only)
        self._fetch_button = None
        self._fetch_status_label = None
        self._sel_count_label = None
        self._selection_updating = False

        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI for this provider."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        self.setMinimumWidth(700)
        
        # Provider info header
        header = self._create_header()
        layout.addWidget(header)
        
        # Configuration form
        form_group = self._create_config_form()
        layout.addWidget(form_group)
        
        # Test connection section
        test_group = self._create_test_section()
        layout.addWidget(test_group)
        
        layout.addStretch()
    
    def _create_header(self) -> QWidget:
        """Create provider information header."""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 10)
        
        # Provider icon/logo placeholder
        icon_label = QLabel("🤖")  # Would use actual provider icons
        icon_label.setFixedSize(48, 48)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                border: 2px solid #ddd;
                border-radius: 8px;
                background-color: #f5f5f5;
            }
        """)
        layout.addWidget(icon_label)
        
        # Provider info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(self._get_provider_name())
        name_font = QFont()
        name_font.setPointSize(14)
        name_font.setBold(True)
        name_label.setFont(name_font)
        info_layout.addWidget(name_label)
        
        desc_label = QLabel(self._get_provider_description())
        desc_label.setStyleSheet("color: #666;")
        desc_label.setWordWrap(True)
        info_layout.addWidget(desc_label)
        
        layout.addLayout(info_layout)
        layout.addStretch()
        
        return header
    
    def _create_config_form(self) -> QGroupBox:
        """Create configuration form."""
        group = QGroupBox("Configuration")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(10)
        form_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form_layout.setLabelAlignment(Qt.AlignRight)
        
        # API Key
        self._widgets['api_key'] = SecureLineEdit()
        self._widgets['api_key'].setPlaceholderText(self._get_api_key_placeholder())
        self._widgets['api_key'].setMinimumWidth(350)
        form_layout.addRow("API Key:", self._widgets['api_key'])
        
        # Base URL (for LM Studio)
        if self.provider == TranslationProvider.LM_STUDIO:
            self._widgets['base_url'] = QLineEdit()
            self._widgets['base_url'].setPlaceholderText("http://localhost:1234/v1")
            self._widgets['base_url'].setMinimumWidth(350)
            form_layout.addRow("Base URL:", self._widgets['base_url'])

        # --- Live model fetch + selection (OpenAI and OpenRouter only) ---
        if self.provider in (TranslationProvider.OPENAI, TranslationProvider.OPENROUTER):
            # Fetch button row
            fetch_row = QHBoxLayout()
            self._fetch_button = QPushButton("Fetch Available Models")
            self._fetch_button.setToolTip(
                "Fetch all models from the provider API using the API key above.\n"
                "Check the models you want to appear in the main window."
            )
            self._fetch_button.clicked.connect(self._fetch_models)
            fetch_row.addWidget(self._fetch_button)

            self._fetch_status_label = QLabel("Enter an API key above, then click Fetch.")
            self._fetch_status_label.setStyleSheet("color: #888; font-size: 9pt;")
            self._fetch_status_label.setWordWrap(True)
            fetch_row.addWidget(self._fetch_status_label, stretch=1)
            form_layout.addRow("", fetch_row)

            # Model checklist
            self._model_list = QListWidget()
            self._model_list.setMaximumHeight(190)
            self._model_list.setMinimumHeight(120)
            self._model_list.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self._model_list.itemChanged.connect(self._on_model_item_changed)
            form_layout.addRow("Available Models:", self._model_list)

            # Select All / Deselect All / count
            sel_row = QHBoxLayout()
            sel_all_btn = QPushButton("Select All")
            sel_all_btn.setMaximumWidth(85)
            sel_all_btn.clicked.connect(self._select_all_models)
            desel_all_btn = QPushButton("Deselect All")
            desel_all_btn.setMaximumWidth(95)
            desel_all_btn.clicked.connect(self._deselect_all_models)
            self._sel_count_label = QLabel("")
            self._sel_count_label.setStyleSheet("color: #888; font-size: 9pt;")
            sel_row.addWidget(sel_all_btn)
            sel_row.addWidget(desel_all_btn)
            sel_row.addWidget(self._sel_count_label)
            sel_row.addStretch()
            form_layout.addRow("", sel_row)

        # Model selection with management buttons
        model_layout = QHBoxLayout()
        self._widgets['default_model'] = QComboBox()
        self._widgets['default_model'].setEditable(True)
        self._widgets['default_model'].setMinimumWidth(400)
        self._widgets['default_model'].setMaxVisibleItems(10)
        self._widgets['default_model'].setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self._widgets['default_model'].view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        # Make dropdown arrow more visible
        self._widgets['default_model'].setStyleSheet("""
            QComboBox {
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid #ccc;
            }
            QComboBox::down-arrow {
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #666;
            }
        """)
        self._populate_models()
        model_layout.addWidget(self._widgets['default_model'], stretch=1)

        # Add custom model button
        add_model_btn = QPushButton("+")
        add_model_btn.setToolTip("Add current model to custom models list")
        add_model_btn.setMaximumWidth(30)
        add_model_btn.clicked.connect(self._add_custom_model)
        model_layout.addWidget(add_model_btn)

        # Remove custom model button
        remove_model_btn = QPushButton("-")
        remove_model_btn.setToolTip("Remove selected model from custom models")
        remove_model_btn.setMaximumWidth(30)
        remove_model_btn.clicked.connect(self._remove_custom_model)
        model_layout.addWidget(remove_model_btn)

        form_layout.addRow("Default Model:", model_layout)

        # Advanced settings in collapsible section
        advanced_group = QGroupBox("Advanced Settings")
        advanced_group.setCheckable(True)
        advanced_group.setChecked(False)
        advanced_layout = QFormLayout(advanced_group)
        
        # Temperature
        self._widgets['temperature'] = QDoubleSpinBox()
        self._widgets['temperature'].setRange(0.0, 2.0)
        self._widgets['temperature'].setSingleStep(0.1)
        self._widgets['temperature'].setDecimals(1)
        self._widgets['temperature'].setValue(0.3)
        self._widgets['temperature'].setToolTip("Controls randomness in responses (0.0 = deterministic, 2.0 = very random)")
        advanced_layout.addRow("Temperature:", self._widgets['temperature'])
        
        # Max tokens
        self._widgets['max_tokens'] = QSpinBox()
        self._widgets['max_tokens'].setRange(1, 32000)
        self._widgets['max_tokens'].setValue(4096)
        self._widgets['max_tokens'].setToolTip("Maximum number of tokens in response")
        advanced_layout.addRow("Max Tokens:", self._widgets['max_tokens'])
        
        # Timeout
        self._widgets['timeout'] = QSpinBox()
        self._widgets['timeout'].setRange(5, 300)
        self._widgets['timeout'].setValue(30)
        self._widgets['timeout'].setSuffix(" seconds")
        self._widgets['timeout'].setToolTip("Request timeout in seconds")
        advanced_layout.addRow("Timeout:", self._widgets['timeout'])
        
        form_layout.addRow(advanced_group)
        
        return group
    
    def _create_test_section(self) -> QGroupBox:
        """Create connection test section."""
        group = QGroupBox("Connection Test")
        layout = QVBoxLayout(group)
        
        # Test controls
        test_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Connection")
        self.test_button.clicked.connect(self._test_connection)
        test_layout.addWidget(self.test_button)
        
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        test_layout.addWidget(self.test_progress)
        
        test_layout.addStretch()
        layout.addLayout(test_layout)
        
        # Test result
        self.test_result = QLabel()
        self.test_result.setWordWrap(True)
        self.test_result.setVisible(False)
        layout.addWidget(self.test_result)
        
        return group
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Connect all input widgets to settings changed signal
        # Use lambdas to discard the arguments passed by widget signals
        for widget in self._widgets.values():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(lambda: self.settings_changed.emit())
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(lambda: self.settings_changed.emit())
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(lambda: self.settings_changed.emit())
    
    def _populate_models(self, custom_models: list = None, selected_model_ids: list = None):
        """Populate model dropdown with provider-specific models and custom models.

        For OpenAI/OpenRouter, when *selected_model_ids* is non-empty those IDs are
        used as the built-in list instead of the hardcoded defaults.
        """
        self._widgets['default_model'].clear()

        # Determine built-in model list
        if self.provider == TranslationProvider.OPENAI:
            builtin_models = (selected_model_ids if selected_model_ids
                              else SettingsSchema.get_openai_models())
        elif self.provider == TranslationProvider.ANTHROPIC:
            builtin_models = SettingsSchema.get_anthropic_models()
        elif self.provider == TranslationProvider.OPENROUTER:
            builtin_models = (selected_model_ids if selected_model_ids
                              else SettingsSchema.get_openrouter_models())
        elif self.provider == TranslationProvider.LM_STUDIO:
            builtin_models = ["local-model", "custom-model"]
        else:
            builtin_models = []

        if custom_models is None:
            custom_models = []

        if builtin_models and custom_models:
            self._widgets['default_model'].addItems(builtin_models)
            self._widgets['default_model'].insertSeparator(len(builtin_models))
            for model in custom_models:
                self._widgets['default_model'].addItem(f"★ {model}")
        elif builtin_models:
            self._widgets['default_model'].addItems(builtin_models)
        elif custom_models:
            for model in custom_models:
                self._widgets['default_model'].addItem(f"★ {model}")

    def _add_custom_model(self):
        """Add the current text as a custom model."""
        current_text = self._widgets['default_model'].currentText().strip()

        # Remove star prefix if it exists
        if current_text.startswith("★ "):
            current_text = current_text[2:].strip()

        if not current_text:
            QMessageBox.warning(self, "Invalid Model", "Please enter a model name")
            return

        # Get current custom models from settings
        current_settings = self.get_settings()
        custom_models = current_settings.get('custom_models', [])

        # Check if already exists
        if current_text in custom_models:
            QMessageBox.information(self, "Already Exists", f"Model '{current_text}' already in custom models")
            return

        # Add to list
        custom_models.append(current_text)

        # Repopulate dropdown
        self._populate_models(custom_models)

        # Select the newly added model
        for i in range(self._widgets['default_model'].count()):
            item_text = self._widgets['default_model'].itemText(i)
            if item_text == f"★ {current_text}" or item_text == current_text:
                self._widgets['default_model'].setCurrentIndex(i)
                break

        # Emit settings changed
        self.settings_changed.emit()

        QMessageBox.information(self, "Model Added", f"Custom model '{current_text}' added successfully")

    def _remove_custom_model(self):
        """Remove the selected model from custom models."""
        current_text = self._widgets['default_model'].currentText().strip()

        # Remove star prefix if it exists
        if current_text.startswith("★ "):
            current_text = current_text[2:].strip()

        if not current_text:
            return

        # Get current custom models from settings
        current_settings = self.get_settings()
        custom_models = current_settings.get('custom_models', [])

        # Check if model is in custom models
        if current_text not in custom_models:
            QMessageBox.warning(self, "Not a Custom Model",
                              "This is a built-in model and cannot be removed.\nOnly custom models (marked with ★) can be removed.")
            return

        # Confirm removal
        reply = QMessageBox.question(self, "Confirm Removal",
                                     f"Remove custom model '{current_text}'?",
                                     QMessageBox.Yes | QMessageBox.No,
                                     QMessageBox.No)

        if reply == QMessageBox.Yes:
            custom_models.remove(current_text)

            # Repopulate dropdown
            self._populate_models(custom_models)

            # Emit settings changed
            self.settings_changed.emit()

            QMessageBox.information(self, "Model Removed", f"Custom model '{current_text}' removed successfully")
    
    # ------------------------------------------------------------------ #
    #  Model fetch / checklist helpers (OpenAI & OpenRouter only)        #
    # ------------------------------------------------------------------ #

    def _fetch_models(self):
        """Start fetching models from the provider API in a background thread."""
        api_key = self._widgets['api_key'].text().strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required",
                                "Please enter an API key before fetching models.")
            return

        self._fetch_button.setEnabled(False)
        self._fetch_button.setText("Fetching…")
        self._fetch_status_label.setText("Contacting API…")
        self._fetch_status_label.setStyleSheet("color: #888; font-size: 9pt;")

        self._fetch_thread = QThread()
        self._fetch_worker = ModelFetchWorker(self.provider.value, api_key)
        self._fetch_worker.moveToThread(self._fetch_thread)

        self._fetch_thread.started.connect(self._fetch_worker.run)
        self._fetch_worker.models_fetched.connect(self._on_models_fetched)
        self._fetch_worker.fetch_failed.connect(self._on_fetch_failed)

        self._fetch_thread.start()

    def _on_models_fetched(self, models: list):
        """Handle successfully fetched model list."""
        self._fetch_thread.quit()
        self._fetch_thread.wait()

        self._fetch_button.setEnabled(True)
        self._fetch_button.setText("Fetch Available Models")

        self._fetched_models = models

        # Preserve existing selection if any, otherwise pre-check the built-in presets
        current_selected = self._get_selected_model_ids()
        if not current_selected:
            if self.provider == TranslationProvider.OPENAI:
                preset_ids = set(SettingsSchema.get_openai_models())
            else:
                preset_ids = set(SettingsSchema.get_openrouter_models())
            current_selected = [m_id for m_id, _ in models if m_id in preset_ids]

        self._populate_model_list(models, current_selected)
        self._fetch_status_label.setText(f"✅ {len(models)} models loaded")
        self._fetch_status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")

        self._update_default_model_from_selection()
        self.settings_changed.emit()

    def _on_fetch_failed(self, error: str):
        """Handle fetch error."""
        self._fetch_thread.quit()
        self._fetch_thread.wait()

        self._fetch_button.setEnabled(True)
        self._fetch_button.setText("Fetch Available Models")
        self._fetch_status_label.setText(f"❌ {error}")
        self._fetch_status_label.setStyleSheet("color: #f44336; font-size: 9pt;")

    def _populate_model_list(self, models: list, selected_ids: list):
        """Fill the QListWidget with models and their check state."""
        if self._model_list is None:
            return
        self._selection_updating = True
        self._model_list.clear()
        selected_set = set(selected_ids)
        for model_id, model_name in models:
            item = QListWidgetItem()
            if model_name and model_name != model_id:
                item.setText(model_name)
                item.setToolTip(model_id)
            else:
                item.setText(model_id)
            item.setData(Qt.UserRole, model_id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if model_id in selected_set else Qt.Unchecked)
            self._model_list.addItem(item)
        self._selection_updating = False
        self._update_selection_count()

    def _on_model_item_changed(self, item: QListWidgetItem):
        """Called when a model checkbox is toggled by the user."""
        if self._selection_updating:
            return
        self._update_selection_count()
        self._update_default_model_from_selection()
        self.settings_changed.emit()

    def _get_selected_model_ids(self) -> list:
        """Return the IDs of all checked models."""
        if self._model_list is None:
            return []
        result = []
        for i in range(self._model_list.count()):
            item = self._model_list.item(i)
            if item.checkState() == Qt.Checked:
                result.append(item.data(Qt.UserRole))
        return result

    def _update_selection_count(self):
        """Refresh the 'X / N selected' label."""
        if self._model_list is None or self._sel_count_label is None:
            return
        total = self._model_list.count()
        checked = sum(
            1 for i in range(total)
            if self._model_list.item(i).checkState() == Qt.Checked
        )
        self._sel_count_label.setText(f"{checked} / {total} selected")

    def _update_default_model_from_selection(self):
        """Sync the Default Model combo to only show currently selected models."""
        selected_ids = self._get_selected_model_ids()

        # Preserve the currently chosen default model if it's still selected
        current = self._widgets['default_model'].currentText()
        if current.startswith("★ "):
            current = current[2:].strip()

        # Collect custom models from the existing combo
        custom_models = []
        for i in range(self._widgets['default_model'].count()):
            text = self._widgets['default_model'].itemText(i)
            if text.startswith("★ "):
                custom_models.append(text[2:].strip())

        self._populate_models(custom_models=custom_models, selected_model_ids=selected_ids)

        # Try to restore previous selection
        if current:
            idx = self._widgets['default_model'].findText(current)
            if idx >= 0:
                self._widgets['default_model'].setCurrentIndex(idx)
            else:
                idx = self._widgets['default_model'].findText(f"★ {current}")
                if idx >= 0:
                    self._widgets['default_model'].setCurrentIndex(idx)

    def _select_all_models(self):
        """Check all models in the list."""
        if self._model_list is None:
            return
        self._selection_updating = True
        for i in range(self._model_list.count()):
            self._model_list.item(i).setCheckState(Qt.Checked)
        self._selection_updating = False
        self._update_selection_count()
        self._update_default_model_from_selection()
        self.settings_changed.emit()

    def _deselect_all_models(self):
        """Uncheck all models in the list."""
        if self._model_list is None:
            return
        self._selection_updating = True
        for i in range(self._model_list.count()):
            self._model_list.item(i).setCheckState(Qt.Unchecked)
        self._selection_updating = False
        self._update_selection_count()
        self._update_default_model_from_selection()
        self.settings_changed.emit()

    def _test_connection(self):
        """Test the API connection."""
        # Show progress
        self.test_button.setEnabled(False)
        self.test_button.setText("Testing...")
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # Indeterminate
        self.test_result.setVisible(False)
        
        # Get current settings
        api_key = self._widgets['api_key'].text()
        model = self._widgets['default_model'].currentText()
        base_url = self._widgets.get('base_url', QLineEdit()).text()
        
        # Create test worker
        self._test_thread = QThread()
        self._test_worker = ConnectionTestWorker(
            self.provider.value, api_key, model, base_url
        )
        self._test_worker.moveToThread(self._test_thread)
        
        # Connect signals
        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.test_complete.connect(self._on_test_complete)
        
        # Start test
        self._test_thread.start()
    
    def _on_test_complete(self, provider: str, success: bool, message: str):
        """Handle test completion."""
        # Hide progress and restore button
        self.test_progress.setVisible(False)
        self.test_button.setEnabled(True)
        self.test_button.setText("Test Connection")
        
        # Show result
        self.test_result.setVisible(True)
        if success:
            self.test_result.setText(f"✅ {message}")
            self.test_result.setStyleSheet("color: #4CAF50;")
        else:
            self.test_result.setText(f"❌ {message}")
            self.test_result.setStyleSheet("color: #f44336;")
        
        # Clean up thread
        self._test_thread.quit()
        self._test_thread.wait()
        
        # Hide result after 5 seconds
        QTimer.singleShot(5000, lambda: self.test_result.setVisible(False))
    
    def _get_provider_name(self) -> str:
        """Get display name for provider."""
        names = {
            TranslationProvider.OPENAI: "OpenAI",
            TranslationProvider.ANTHROPIC: "Anthropic (Claude)",
            TranslationProvider.OPENROUTER: "OpenRouter",
            TranslationProvider.LM_STUDIO: "LM Studio (Local)"
        }
        return names.get(self.provider, self.provider.value)
    
    def _get_provider_description(self) -> str:
        """Get description for provider."""
        descriptions = {
            TranslationProvider.OPENAI: "High-quality translation using GPT models. Requires OpenAI API account.",
            TranslationProvider.ANTHROPIC: "Advanced translation using Claude models. Requires Anthropic API account.",
            TranslationProvider.OPENROUTER: "Access multiple AI models through a single API. Supports Claude, GPT, Gemini, Llama, and more.",
            TranslationProvider.LM_STUDIO: "Local translation using self-hosted models. Free but requires local setup."
        }
        return descriptions.get(self.provider, "Translation provider")
    
    def _get_api_key_placeholder(self) -> str:
        """Get API key placeholder text."""
        placeholders = {
            TranslationProvider.OPENAI: "sk-...",
            TranslationProvider.ANTHROPIC: "sk-ant-...",
            TranslationProvider.OPENROUTER: "sk-or-v1-...",
            TranslationProvider.LM_STUDIO: "lm-studio"
        }
        return placeholders.get(self.provider, "Enter API key")
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into this provider widget."""
        custom_models = settings.get('custom_models', [])
        selected_models = settings.get('selected_models', [])
        fetched_models_data = settings.get('fetched_models', [])

        # Restore the model checklist from cached fetch data (openai/openrouter only)
        if self._model_list is not None and fetched_models_data:
            models = [
                (m.get('id', ''), m.get('name', m.get('id', '')))
                for m in fetched_models_data
            ]
            self._fetched_models = models
            self._populate_model_list(models, selected_models)
            self._fetch_status_label.setText(
                f"✅ {len(models)} models (cached — click Fetch to refresh)"
            )
            self._fetch_status_label.setStyleSheet("color: #4CAF50; font-size: 9pt;")

        # Populate the Default Model combo using selected_models (if any)
        self._populate_models(custom_models, selected_model_ids=selected_models or None)

        for key, widget in self._widgets.items():
            if key in settings:
                value = settings[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    text_value = str(value)
                    if text_value.startswith("★ "):
                        text_value = text_value[2:].strip()
                    index = widget.findText(text_value)
                    if index >= 0:
                        widget.setCurrentIndex(index)
                    else:
                        index = widget.findText(f"★ {text_value}")
                        if index >= 0:
                            widget.setCurrentIndex(index)
                        else:
                            widget.setCurrentText(text_value)
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from this provider widget."""
        settings = {}

        # Collect custom models from dropdown
        custom_models = []
        for i in range(self._widgets['default_model'].count()):
            item_text = self._widgets['default_model'].itemText(i)
            if item_text.startswith("★ "):
                custom_models.append(item_text[2:].strip())
        settings['custom_models'] = custom_models

        # Persist selected models and fetched model cache (openai/openrouter only)
        if self._model_list is not None:
            settings['selected_models'] = self._get_selected_model_ids()
            settings['fetched_models'] = [
                {"id": m_id, "name": name}
                for m_id, name in self._fetched_models
            ]

        for key, widget in self._widgets.items():
            if isinstance(widget, QLineEdit):
                settings[key] = widget.text()
            elif isinstance(widget, QComboBox):
                text = widget.currentText()
                if text.startswith("★ "):
                    text = text[2:].strip()
                settings[key] = text
            elif isinstance(widget, QSpinBox):
                settings[key] = widget.value()
            elif isinstance(widget, QDoubleSpinBox):
                settings[key] = widget.value()

        return settings
    
    def validate_settings(self) -> ValidationResult:
        """Validate this provider's settings."""
        errors = []
        warnings = []
        
        api_key = self._widgets['api_key'].text()
        if not api_key:
            errors.append(f"API key is required for {self._get_provider_name()}")
        
        if self.provider == TranslationProvider.LM_STUDIO:
            base_url = self._widgets.get('base_url', QLineEdit()).text()
            if not base_url:
                errors.append("Base URL is required for LM Studio")
            elif not base_url.startswith(('http://', 'https://')):
                errors.append("Base URL must start with http:// or https://")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


class TranslatorsTab(QWidget):
    """
    Translators configuration tab.
    
    Provides interface for:
    - Default translation provider selection
    - Provider-specific configuration (API keys, models, etc.)
    - Connection testing for each provider
    - Advanced provider settings
    """
    
    settings_changed = Signal(str)  # section name
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self._provider_widgets = {}
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Default provider selection
        default_group = self._create_default_provider_group()
        layout.addWidget(default_group)
        
        # Provider tabs
        provider_tabs = self._create_provider_tabs()
        layout.addWidget(provider_tabs)
    
    def _create_default_provider_group(self) -> QGroupBox:
        """Create default provider selection group."""
        group = QGroupBox("Default Translation Provider")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Default Provider:"))
        
        self.default_provider_combo = QComboBox()
        providers = [
            (TranslationProvider.OPENAI.value, "OpenAI (GPT)"),
            (TranslationProvider.ANTHROPIC.value, "Anthropic (Claude)"),
            (TranslationProvider.OPENROUTER.value, "OpenRouter"),
            (TranslationProvider.LM_STUDIO.value, "LM Studio (Local)")
        ]
        
        for value, display in providers:
            self.default_provider_combo.addItem(display, value)
        
        layout.addWidget(self.default_provider_combo)
        
        layout.addStretch()
        
        return group
    
    def _create_provider_tabs(self) -> QTabWidget:
        """Create tabs for each translation provider."""
        tab_widget = QTabWidget()
        
        # Create tab for each provider
        providers = [
            TranslationProvider.OPENAI,
            TranslationProvider.ANTHROPIC,
            TranslationProvider.OPENROUTER,
            TranslationProvider.LM_STUDIO
        ]
        
        for provider in providers:
            provider_widget = ProviderConfigWidget(provider)
            self._provider_widgets[provider.value] = provider_widget
            
            # Add tab with appropriate name
            tab_name = provider_widget._get_provider_name()
            tab_widget.addTab(provider_widget, tab_name)
        
        return tab_widget
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Default provider combo
        self.default_provider_combo.currentIndexChanged.connect(
            lambda: self.settings_changed.emit("translators")
        )
        
        # Provider widget signals
        for provider_widget in self._provider_widgets.values():
            provider_widget.settings_changed.connect(
                lambda: self.settings_changed.emit("translators")
            )
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the tab."""
        # Default provider
        default_provider = settings.get("default_provider", TranslationProvider.OPENAI.value)
        index = self.default_provider_combo.findData(default_provider)
        if index >= 0:
            self.default_provider_combo.setCurrentIndex(index)
        
        # Provider-specific settings
        for provider_value, widget in self._provider_widgets.items():
            if provider_value in settings:
                widget.load_settings(settings[provider_value])
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from the tab."""
        settings = {
            "default_provider": self.default_provider_combo.currentData()
        }
        
        # Provider-specific settings
        for provider_value, widget in self._provider_widgets.items():
            settings[provider_value] = widget.get_settings()
        
        return settings
    
    def validate_settings(self) -> ValidationResult:
        """Validate current settings."""
        all_errors = []
        all_warnings = []
        
        # Validate each provider
        for provider_value, widget in self._provider_widgets.items():
            result = widget.validate_settings()
            if result.errors:
                all_errors.extend([f"{provider_value}: {error}" for error in result.errors])
            if result.warnings:
                all_warnings.extend([f"{provider_value}: {warning}" for warning in result.warnings])
        
        # Check that default provider is configured
        default_provider = self.default_provider_combo.currentData()
        if default_provider in self._provider_widgets:
            default_widget = self._provider_widgets[default_provider]
            api_key = default_widget._widgets['api_key'].text()
            if not api_key:
                all_warnings.append(f"Default provider ({default_provider}) is not configured")
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )