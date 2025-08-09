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
    QMessageBox, QProgressBar
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
            
        elif self.provider == TranslationProvider.LM_STUDIO.value:
            if not self.base_url:
                return False, "Base URL is required for LM Studio"
            if not self.base_url.startswith(('http://', 'https://')):
                return False, "Base URL must start with http:// or https://"
            return True, "Connection successful (simulated)"
        
        return False, "Unknown provider"


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
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI for this provider."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
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
        
        # API Key
        self._widgets['api_key'] = SecureLineEdit()
        self._widgets['api_key'].setPlaceholderText(self._get_api_key_placeholder())
        form_layout.addRow("API Key:", self._widgets['api_key'])
        
        # Base URL (for LM Studio)
        if self.provider == TranslationProvider.LM_STUDIO:
            self._widgets['base_url'] = QLineEdit()
            self._widgets['base_url'].setPlaceholderText("http://localhost:1234/v1")
            form_layout.addRow("Base URL:", self._widgets['base_url'])
        
        # Model selection
        self._widgets['default_model'] = QComboBox()
        self._widgets['default_model'].setEditable(True)
        self._populate_models()
        form_layout.addRow("Default Model:", self._widgets['default_model'])
        
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
        for widget in self._widgets.values():
            if isinstance(widget, QLineEdit):
                widget.textChanged.connect(self.settings_changed.emit)
            elif isinstance(widget, QComboBox):
                widget.currentTextChanged.connect(self.settings_changed.emit)
            elif isinstance(widget, (QSpinBox, QDoubleSpinBox)):
                widget.valueChanged.connect(self.settings_changed.emit)
    
    def _populate_models(self):
        """Populate model dropdown with provider-specific models."""
        models = []
        
        if self.provider == TranslationProvider.OPENAI:
            models = SettingsSchema.get_openai_models()
        elif self.provider == TranslationProvider.ANTHROPIC:
            models = SettingsSchema.get_anthropic_models()
        elif self.provider == TranslationProvider.LM_STUDIO:
            models = ["local-model", "custom-model"]  # Placeholder
        
        self._widgets['default_model'].addItems(models)
    
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
            TranslationProvider.LM_STUDIO: "LM Studio (Local)"
        }
        return names.get(self.provider, self.provider.value)
    
    def _get_provider_description(self) -> str:
        """Get description for provider."""
        descriptions = {
            TranslationProvider.OPENAI: "High-quality translation using GPT models. Requires OpenAI API account.",
            TranslationProvider.ANTHROPIC: "Advanced translation using Claude models. Requires Anthropic API account.",
            TranslationProvider.LM_STUDIO: "Local translation using self-hosted models. Free but requires local setup."
        }
        return descriptions.get(self.provider, "Translation provider")
    
    def _get_api_key_placeholder(self) -> str:
        """Get API key placeholder text."""
        placeholders = {
            TranslationProvider.OPENAI: "sk-...",
            TranslationProvider.ANTHROPIC: "sk-ant-...",
            TranslationProvider.LM_STUDIO: "lm-studio"
        }
        return placeholders.get(self.provider, "Enter API key")
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into this provider widget."""
        for key, widget in self._widgets.items():
            if key in settings:
                value = settings[key]
                if isinstance(widget, QLineEdit):
                    widget.setText(str(value))
                elif isinstance(widget, QComboBox):
                    widget.setCurrentText(str(value))
                elif isinstance(widget, QSpinBox):
                    widget.setValue(int(value))
                elif isinstance(widget, QDoubleSpinBox):
                    widget.setValue(float(value))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from this provider widget."""
        settings = {}
        
        for key, widget in self._widgets.items():
            if isinstance(widget, QLineEdit):
                settings[key] = widget.text()
            elif isinstance(widget, QComboBox):
                settings[key] = widget.currentText()
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
        self.default_provider_combo.currentDataChanged.connect(
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