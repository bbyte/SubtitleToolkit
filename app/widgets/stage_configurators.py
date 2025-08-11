"""
Stage Configurators Widget

This widget contains expandable configuration panels for each processing stage:
- ExtractConfig: Language selection, output directory
- TranslateConfig: Source/target languages, engine selection
- SyncConfig: Naming template, dry-run toggle
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QSlider, QFileDialog, QGroupBox, QFormLayout,
    QSpinBox, QTextEdit, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from ..config.settings_schema import SettingsSchema


class QCollapsibleGroupBox(QGroupBox):
    """A collapsible group box widget."""
    
    def __init__(self, title: str = "", parent: QWidget = None):
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(False)
        self.toggled.connect(self._on_toggled)
        self._content_widget = None
        
        # Style for collapsible appearance
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2a82da;
            }
            QGroupBox::indicator {
                width: 13px;
                height: 13px;
                margin-right: 5px;
            }
            QGroupBox::indicator:unchecked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYuNSAyVjExTTIgNi41SDExIiBzdHJva2U9IiM1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QGroupBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIgNi41SDExIiBzdHJva2U9IiMyYTgyZGEiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
        """)
    
    def _on_toggled(self, checked: bool) -> None:
        """Handle toggle state change."""
        if self._content_widget:
            self._content_widget.setVisible(checked)
            # Animate the expansion/collapse
            if checked:
                self.setMaximumHeight(16777215)  # Remove height restriction
            else:
                self.setMaximumHeight(50)  # Collapse to title height
    
    def setContentWidget(self, widget: QWidget) -> None:
        """Set the content widget to show/hide."""
        self._content_widget = widget
        self._content_widget.setVisible(self.isChecked())
        # Set initial state
        if not self.isChecked():
            self.setMaximumHeight(50)


@dataclass
class ValidationResult:
    """Result of configuration validation."""
    is_valid: bool
    error_message: str = ""
    warnings: list = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ExtractConfigWidget(QFrame):
    """Configuration widget for the Extract stage."""
    
    config_changed = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._project_directory = ""
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        # Language selection
        self.language_combo = QComboBox()
        # Populate with all supported languages from schema
        supported_languages = SettingsSchema.get_supported_languages()
        for code, name in sorted(supported_languages.items(), key=lambda x: x[1]):
            display_text = f"{name} ({code})" if code != "auto" else name
            self.language_combo.addItem(display_text, code)
        # Set default to English
        self._set_language_combo_by_code(self.language_combo, "eng")
        layout.addRow("Subtitle Language:", self.language_combo)
        
        # Output directory selection
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Default: same as project directory")
        self.output_dir_browse = QPushButton("Browse...")
        self.output_dir_browse.setMaximumWidth(100)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.output_dir_browse)
        layout.addRow("Output Directory:", output_layout)
        
        # Subtitle format options
        self.format_combo = QComboBox()
        self.format_combo.addItems(["SRT (SubRip)", "VTT (WebVTT)", "ASS (Advanced SSA)"])
        self.format_combo.setCurrentText("SRT (SubRip)")
        layout.addRow("Output Format:", self.format_combo)
        
        # Advanced options
        self.extract_all_checkbox = QCheckBox("Extract all subtitle tracks")
        self.extract_all_checkbox.setToolTip("Extract all available subtitle tracks, not just the first one")
        layout.addRow("", self.extract_all_checkbox)
        
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.overwrite_checkbox.setToolTip("Overwrite existing subtitle files")
        layout.addRow("", self.overwrite_checkbox)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.language_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.output_dir_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.format_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.extract_all_checkbox.toggled.connect(lambda: self.config_changed.emit())
        self.overwrite_checkbox.toggled.connect(lambda: self.config_changed.emit())
        
        self.output_dir_browse.clicked.connect(self._browse_output_directory)
    
    def _browse_output_directory(self) -> None:
        """Browse for output directory."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        dialog.setOption(QFileDialog.ShowDirsOnly, True)
        dialog.setWindowTitle("Select Output Directory")
        
        if self._project_directory:
            dialog.setDirectory(self._project_directory)
        
        if dialog.exec():
            selected_dirs = dialog.selectedFiles()
            if selected_dirs:
                self.output_dir_edit.setText(selected_dirs[0])
    
    def set_project_directory(self, directory: str) -> None:
        """Set the project directory for relative path resolution."""
        self._project_directory = directory
    
    def _set_language_combo_by_code(self, combo: QComboBox, code: str) -> None:
        """Set combo box selection by language code."""
        for i in range(combo.count()):
            if combo.itemData(i) == code:
                combo.setCurrentIndex(i)
                break
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return {
            'language_code': self.language_combo.currentData() or 'eng',
            'output_directory': self.output_dir_edit.text() or self._project_directory,
            'format': self.format_combo.currentText().split(' (')[0].lower(),
            'extract_all': self.extract_all_checkbox.isChecked(),
            'overwrite_existing': self.overwrite_checkbox.isChecked()
        }
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()
        
        # Check output directory
        output_dir = config['output_directory']
        if output_dir and not Path(output_dir).exists():
            return ValidationResult(False, f"Output directory does not exist: {output_dir}")
        
        return ValidationResult(True)


class TranslateConfigWidget(QFrame):
    """Configuration widget for the Translate stage."""
    
    config_changed = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        # Source language
        self.source_lang_combo = QComboBox()
        supported_languages = SettingsSchema.get_supported_languages()
        for code, name in sorted(supported_languages.items(), key=lambda x: x[1]):
            display_text = f"{name} ({code})" if code != "auto" else name
            self.source_lang_combo.addItem(display_text, code)
        layout.addRow("Source Language:", self.source_lang_combo)
        
        # Target language
        self.target_lang_combo = QComboBox()
        for code, name in sorted(supported_languages.items(), key=lambda x: x[1]):
            if code != "auto":  # Target language can't be auto-detect
                display_text = f"{name} ({code})"
                self.target_lang_combo.addItem(display_text, code)
        layout.addRow("Target Language:", self.target_lang_combo)
        
        # Set defaults
        self._set_language_combo_by_code(self.source_lang_combo, "auto")
        self._set_language_combo_by_code(self.target_lang_combo, "en")
        
        # Translation engine
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["OpenAI", "Claude", "LM Studio"])
        layout.addRow("Translation Engine:", self.engine_combo)
        
        # Model selection (engine-specific)
        self.model_combo = QComboBox()
        layout.addRow("Model:", self.model_combo)
        
        # API key field
        api_key_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Enter API key or set in environment")
        self.show_key_button = QPushButton(self.tr("Show"))
        self.show_key_button.setMaximumWidth(60)
        self.show_key_button.setCheckable(True)
        api_key_layout.addWidget(self.api_key_edit)
        api_key_layout.addWidget(self.show_key_button)
        layout.addRow("API Key:", api_key_layout)
        
        # Advanced options
        self.chunk_size_spin = QSpinBox()
        self.chunk_size_spin.setRange(5, 50)
        self.chunk_size_spin.setValue(20)
        self.chunk_size_spin.setSuffix(" subtitles")
        layout.addRow("Chunk Size:", self.chunk_size_spin)
        
        self.context_edit = QTextEdit()
        self.context_edit.setMaximumHeight(80)
        self.context_edit.setPlaceholderText("Optional: Movie/show context for better translations")
        layout.addRow("Context:", self.context_edit)
        
        # Update model options based on engine
        self._update_model_options()
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.source_lang_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.target_lang_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.engine_combo.currentTextChanged.connect(self._on_engine_changed)
        self.model_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.api_key_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.chunk_size_spin.valueChanged.connect(lambda: self.config_changed.emit())
        self.context_edit.textChanged.connect(lambda: self.config_changed.emit())
        
        self.show_key_button.toggled.connect(self._toggle_api_key_visibility)
    
    def _on_engine_changed(self) -> None:
        """Handle engine selection change."""
        self._update_model_options()
        self.config_changed.emit()
    
    def _update_model_options(self) -> None:
        """Update available models based on selected engine."""
        engine = self.engine_combo.currentText()
        self.model_combo.clear()
        
        if engine == "OpenAI":
            self.model_combo.addItems([
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
            ])
            self.api_key_edit.setPlaceholderText("OpenAI API key")
        elif engine == "Claude":
            self.model_combo.addItems([
                "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-haiku-20240307", "claude-3-opus-20240229"
            ])
            self.api_key_edit.setPlaceholderText("Anthropic API key")
        elif engine == "LM Studio":
            self.model_combo.addItems([
                "Local Model (LM Studio)", "Custom Endpoint"
            ])
            self.api_key_edit.setPlaceholderText("Optional: API key for custom endpoint")
    
    def _toggle_api_key_visibility(self, show: bool) -> None:
        """Toggle API key visibility."""
        if show:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.show_key_button.setText(self.tr("Hide"))
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.show_key_button.setText(self.tr("Show"))
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        # Map UI display names to script provider names
        provider_mapping = {
            'openai': 'openai',
            'claude': 'claude',  # Claude UI name maps to claude script provider
            'lm_studio': 'local'  # LM Studio UI name maps to local script provider
        }
        
        engine_text = self.engine_combo.currentText().lower().replace(' ', '_')
        provider = provider_mapping.get(engine_text, engine_text)
        
        return {
            'source_language': self.source_lang_combo.currentData() or 'auto',
            'target_language': self.target_lang_combo.currentData() or 'en',
            'provider': provider,
            'model': self.model_combo.currentText(),
            'api_key': self.api_key_edit.text(),
            'chunk_size': self.chunk_size_spin.value(),
            'context': self.context_edit.toPlainText().strip()
        }
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()
        
        # Check if API key is required
        provider = config['provider']
        if provider in ['openai', 'anthropic'] and not config['api_key']:
            provider_display = 'Claude' if provider == 'anthropic' else provider.upper()
            return ValidationResult(False, f"{provider_display} API key is required")
        
        # Check language selection
        if config['source_language'] == config['target_language'] and config['source_language'] != 'auto':
            return ValidationResult(False, "Source and target languages cannot be the same")
        
        return ValidationResult(True)
    
    def _set_language_combo_by_code(self, combo: QComboBox, code: str) -> None:
        """Set combo box selection by language code."""
        for i in range(combo.count()):
            if combo.itemData(i) == code:
                combo.setCurrentIndex(i)
                break


class SyncConfigWidget(QFrame):
    """Configuration widget for the Sync stage."""
    
    config_changed = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        # Naming template
        self.template_edit = QLineEdit()
        self.template_edit.setText("{video_name}.{language}.srt")
        self.template_edit.setPlaceholderText("{video_name}.{language}.srt")
        layout.addRow("Naming Template:", self.template_edit)
        
        # Template help
        template_help = QLabel(self.tr("Available placeholders: {video_name}, {language}, {original_name}"))
        template_help.setStyleSheet("color: #bbb; font-size: 10px;")
        template_help.setWordWrap(True)
        layout.addRow("", template_help)
        
        # Dry run toggle
        self.dry_run_checkbox = QCheckBox("Dry run (preview changes without renaming)")
        self.dry_run_checkbox.setChecked(True)  # Default to safe mode
        layout.addRow("", self.dry_run_checkbox)
        
        # Confidence threshold
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(50, 100)
        self.confidence_slider.setValue(80)
        self.confidence_label = QLabel("80%")
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(self.confidence_slider)
        confidence_layout.addWidget(self.confidence_label)
        layout.addRow("Confidence Threshold:", confidence_layout)
        
        # Backup option
        self.backup_checkbox = QCheckBox("Create backup of original filenames")
        self.backup_checkbox.setChecked(True)
        layout.addRow("", self.backup_checkbox)
        
        # Case sensitivity
        self.case_sensitive_checkbox = QCheckBox("Case-sensitive matching")
        layout.addRow("", self.case_sensitive_checkbox)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.template_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.dry_run_checkbox.toggled.connect(lambda: self.config_changed.emit())
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)
        self.backup_checkbox.toggled.connect(lambda: self.config_changed.emit())
        self.case_sensitive_checkbox.toggled.connect(lambda: self.config_changed.emit())
    
    def _on_confidence_changed(self, value: int) -> None:
        """Handle confidence threshold change."""
        self.confidence_label.setText(f"{value}%")
        self.config_changed.emit()
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return {
            'naming_template': self.template_edit.text(),
            'dry_run': self.dry_run_checkbox.isChecked(),
            'confidence_threshold': self.confidence_slider.value() / 100.0,
            'create_backup': self.backup_checkbox.isChecked(),
            'case_sensitive': self.case_sensitive_checkbox.isChecked()
        }
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()
        
        # Check template validity
        template = config['naming_template']
        if not template.strip():
            return ValidationResult(False, "Naming template cannot be empty")
        
        # Check for invalid characters in template
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in template:
                return ValidationResult(False, f"Invalid character '{char}' in naming template")
        
        return ValidationResult(True)


class StageConfigurators(QFrame):
    """
    Container widget for all stage configuration panels.
    
    Manages expandable configuration sections for Extract, Translate, and Sync stages.
    """
    
    config_changed = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        self._project_directory = ""
        self._enabled_stages = {'extract': False, 'translate': False, 'sync': False}
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel(self.tr("Stage Configuration"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Extract configuration
        self.extract_group = QCollapsibleGroupBox(self.tr("Extract Configuration"))
        self.extract_config = ExtractConfigWidget()
        extract_layout = QVBoxLayout(self.extract_group)
        extract_layout.addWidget(self.extract_config)
        self.extract_group.setContentWidget(self.extract_config)
        layout.addWidget(self.extract_group)
        
        # Translate configuration
        self.translate_group = QCollapsibleGroupBox(self.tr("Translate Configuration"))
        self.translate_config = TranslateConfigWidget()
        translate_layout = QVBoxLayout(self.translate_group)
        translate_layout.addWidget(self.translate_config)
        self.translate_group.setContentWidget(self.translate_config)
        layout.addWidget(self.translate_group)
        
        # Sync configuration
        self.sync_group = QCollapsibleGroupBox(self.tr("Sync Configuration"))
        self.sync_config = SyncConfigWidget()
        sync_layout = QVBoxLayout(self.sync_group)
        sync_layout.addWidget(self.sync_config)
        self.sync_group.setContentWidget(self.sync_config)
        layout.addWidget(self.sync_group)
        
        # Add stretch to push everything to top
        layout.addStretch()
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.extract_config.config_changed.connect(self.config_changed.emit)
        self.translate_config.config_changed.connect(self.config_changed.emit)
        self.sync_config.config_changed.connect(self.config_changed.emit)
    
    def update_enabled_stages(self, stages: Dict[str, bool]) -> None:
        """Update which stage configurations are enabled/visible."""
        self._enabled_stages = stages.copy()
        
        # Enable/disable and expand/collapse based on stage selection
        self.extract_group.setEnabled(stages.get('extract', False))
        self.extract_group.setVisible(stages.get('extract', False))
        
        self.translate_group.setEnabled(stages.get('translate', False))
        self.translate_group.setVisible(stages.get('translate', False))
        
        self.sync_group.setEnabled(stages.get('sync', False))
        self.sync_group.setVisible(stages.get('sync', False))
        
        # Auto-expand enabled stages
        if stages.get('extract', False):
            self.extract_group.setChecked(True)
        if stages.get('translate', False):
            self.translate_group.setChecked(True)
        if stages.get('sync', False):
            self.sync_group.setChecked(True)
    
    def set_project_directory(self, directory: str) -> None:
        """Set the project directory for all configurations."""
        self._project_directory = directory
        self.extract_config.set_project_directory(directory)
    
    def get_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get all stage configurations."""
        return {
            'extract': self.extract_config.get_config(),
            'translate': self.translate_config.get_config(),
            'sync': self.sync_config.get_config()
        }
    
    def validate_configurations(self, enabled_stages: Dict[str, bool]) -> ValidationResult:
        """Validate all enabled stage configurations."""
        for stage, enabled in enabled_stages.items():
            if not enabled:
                continue
            
            if stage == 'extract':
                result = self.extract_config.validate()
            elif stage == 'translate':
                result = self.translate_config.validate()
            elif stage == 'sync':
                result = self.sync_config.validate()
            else:
                continue
            
            if not result.is_valid:
                return ValidationResult(False, f"{stage.title()} configuration error: {result.error_message}")
        
        return ValidationResult(True)
    
    def get_extract_config(self) -> Dict[str, Any]:
        """Get extract stage configuration."""
        return self.extract_config.get_config()
    
    def get_translate_config(self) -> Dict[str, Any]:
        """Get translate stage configuration."""
        return self.translate_config.get_config()
    
    def get_sync_config(self) -> Dict[str, Any]:
        """Get sync stage configuration."""
        return self.sync_config.get_config()
    
    def update_from_settings(self, settings: Dict[str, Any]) -> None:
        """Update configurators from settings."""
        # This method can be used to update the configurators when settings change
        # For now, it's a placeholder - individual config widgets manage their own state
        pass