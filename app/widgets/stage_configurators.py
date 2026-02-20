"""
Stage Configurators Widget

This widget contains expandable configuration panels for each processing stage:
- ExtractConfig: Language selection, output directory
- TranslateConfig: Source/target languages, engine selection
- SyncConfig: Naming template, dry-run toggle
"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Tuple

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QComboBox, QCheckBox, QSlider, QFileDialog, QGroupBox, QFormLayout,
    QSpinBox, QTextEdit, QFrame
)
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QFont

from ..config.settings_schema import SettingsSchema
from ..utils.mkv_language_detector import LanguageDetectionResult
from ..dialogs.track_selection_dialog import TrackSelectionDialog


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
            QGroupBox:disabled {
                color: #666;
                border-color: #333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px 0 8px;
                color: #2a82da;
            }
            QGroupBox::title:disabled {
                color: #666;
            }
            QGroupBox::indicator {
                width: 13px;
                height: 13px;
                margin-right: 5px;
            }
            QGroupBox::indicator:unchecked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYuNSAyVjExTTIgNi41SDExIiBzdHJva2U9IiM1NTUiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QGroupBox::indicator:unchecked:disabled {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYuNSAyVjExTTIgNi41SDExIiBzdHJva2U9IiMzMzMiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QGroupBox::indicator:checked {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIgNi41SDExIiBzdHJva2U9IiMyYTgyZGEiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
            QGroupBox::indicator:checked:disabled {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTMiIGhlaWdodD0iMTMiIHZpZXdCb3g9IjAgMCAxMyAxMyIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTIgNi41SDExIiBzdHJva2U9IiM2NjYiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIi8+Cjwvc3ZnPg==);
            }
        """)
    
    def _on_toggled(self, checked: bool) -> None:
        """Handle toggle state change."""
        if self._content_widget:
            # Only hide/show content if the group box is enabled
            # If disabled, always keep content visible
            if self.isEnabled():
                self._content_widget.setVisible(checked)
                # Animate the expansion/collapse
                if checked:
                    self.setMaximumHeight(16777215)  # Remove height restriction
                else:
                    self.setMaximumHeight(50)  # Collapse to title height
            else:
                # When disabled, always show content (but keep it grayed out)
                self._content_widget.setVisible(True)
                self.setMaximumHeight(16777215)  # Always expanded when disabled
    
    def setContentWidget(self, widget: QWidget) -> None:
        """Set the content widget to show/hide."""
        self._content_widget = widget
        self._update_content_visibility()
    
    def setEnabled(self, enabled: bool) -> None:
        """Override setEnabled to handle content visibility."""
        super().setEnabled(enabled)
        self._update_content_visibility()
    
    def _update_content_visibility(self) -> None:
        """Update content visibility based on enabled and checked state."""
        if self._content_widget:
            if self.isEnabled():
                # Normal collapsible behavior when enabled
                self._content_widget.setVisible(self.isChecked())
                if self.isChecked():
                    self.setMaximumHeight(16777215)
                else:
                    self.setMaximumHeight(50)
            else:
                # Always visible when disabled (for our requirement)
                self._content_widget.setVisible(True)
                self.setMaximumHeight(16777215)  # Always expanded when disabled


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

    def __init__(self, config_manager=None, parent: QWidget = None):
        super().__init__(parent)
        self._project_directory = ""
        self._config_manager = config_manager
        self._detected_languages = []  # Store detected languages from MKV files
        self._has_language_detection = False  # Track if language detection has been performed
        self._detection_result: Optional[LanguageDetectionResult] = None  # Full detection result
        self._selected_track_indices: List[int] = []  # User-selected track indices
        self._setup_ui()
        self._connect_signals()
        self._load_saved_language_preference()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)
        
        # Language selection
        self.language_combo = QComboBox()
        self._populate_default_languages()  # Initially populate with default languages
        layout.addRow("Subtitle Language:", self.language_combo)
        
        # Error/status label for language detection issues
        self.language_status_label = QLabel()
        self.language_status_label.setWordWrap(True)
        self.language_status_label.hide()  # Initially hidden
        layout.addRow("", self.language_status_label)
        
        # Output directory selection
        output_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Default: same as project directory")
        self.output_dir_browse = QPushButton("Browse...")
        self.output_dir_browse.setMaximumWidth(100)
        output_layout.addWidget(self.output_dir_edit)
        output_layout.addWidget(self.output_dir_browse)
        layout.addRow("Output Directory:", output_layout)
        
        # Subtitle format - fixed to SRT only
        format_label = QLabel("SRT (SubRip)")
        format_label.setStyleSheet("color: #888; font-style: italic;")
        layout.addRow("Output Format:", format_label)
        
        # Advanced options
        self.extract_all_checkbox = QCheckBox("Extract all subtitle tracks")
        self.extract_all_checkbox.setToolTip("Extract all available subtitle tracks, not just the first one")
        layout.addRow("", self.extract_all_checkbox)
        
        self.overwrite_checkbox = QCheckBox("Overwrite existing files")
        self.overwrite_checkbox.setToolTip("Overwrite existing subtitle files")
        self.overwrite_checkbox.setChecked(True)  # Default to checked
        layout.addRow("", self.overwrite_checkbox)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.language_combo.currentTextChanged.connect(self._on_language_changed)
        self.output_dir_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.extract_all_checkbox.toggled.connect(lambda: self.config_changed.emit())
        self.overwrite_checkbox.toggled.connect(lambda: self.config_changed.emit())
        
        self.output_dir_browse.clicked.connect(self._browse_output_directory)
    
    def _on_language_changed(self) -> None:
        """Handle language selection change."""
        self._save_language_preference()

        # Check if we have detection result and if multiple tracks exist for this language
        language_code = self.language_combo.currentData()
        if language_code and self._detection_result:
            if self._detection_result.has_multiple_tracks_for_language(language_code):
                # Show track selection dialog
                self._show_track_selection_dialog(language_code)
            else:
                # Single track - auto-select it
                tracks = self._detection_result.get_unique_tracks_for_language(language_code)
                if tracks:
                    self._selected_track_indices = [tracks[0].index]
                else:
                    self._selected_track_indices = []

        self.config_changed.emit()

    def _show_track_selection_dialog(self, language_code: str) -> None:
        """Show dialog for selecting which track(s) to extract."""
        if not self._detection_result:
            return

        tracks = self._detection_result.get_unique_tracks_for_language(language_code)
        if not tracks:
            return

        language_name = self.language_combo.currentText().split(" (")[0]  # Get display name
        selected = TrackSelectionDialog.select_tracks(tracks, language_name, self)

        if selected is not None:
            self._selected_track_indices = selected
        else:
            # User cancelled - keep previous selection or select first track
            if not self._selected_track_indices:
                self._selected_track_indices = [tracks[0].index]
    
    def _load_saved_language_preference(self) -> None:
        """Load saved language preference from settings."""
        if self._config_manager:
            languages_settings = self._config_manager.get_settings("languages")
            saved_language = languages_settings.get("default_extract_language", "eng")
            self._set_language_combo_by_code(self.language_combo, saved_language)
    
    def _save_language_preference(self) -> None:
        """Save current language selection to settings."""
        if self._config_manager:
            current_language = self.language_combo.currentData() or "eng"
            languages_settings = self._config_manager.get_settings("languages")
            languages_settings["default_extract_language"] = current_language
            self._config_manager.update_settings("languages", languages_settings, save=True)
    
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
    
    def _populate_default_languages(self) -> None:
        """Populate language combo with default supported languages."""
        self.language_combo.clear()
        supported_languages = SettingsSchema.get_supported_languages()
        for code, name in sorted(supported_languages.items(), key=lambda x: x[1]):
            display_text = f"{name} ({code})" if code != "auto" else name
            self.language_combo.addItem(display_text, code)
        # Set default to English
        self._set_language_combo_by_code(self.language_combo, "eng")
        self._has_language_detection = False
    
    def update_detected_languages(self, detection_result: LanguageDetectionResult) -> None:
        """Update the language dropdown with detected languages from MKV files."""
        self._has_language_detection = True
        self._detection_result = detection_result  # Store full result for track selection

        # Handle errors first
        if detection_result.errors:
            error_msg = "Language detection issues: " + "; ".join(detection_result.errors[:2])
            self._show_language_status("warning", error_msg)

        # Check if no languages were detected
        if not detection_result.available_languages:
            if detection_result.total_files > 0:
                self._show_language_status("error",
                    f"No subtitle tracks found in {detection_result.total_files} MKV file(s). "
                    "Subtitle extraction is not possible.")
                self.language_combo.setEnabled(False)
                return
            else:
                self._show_language_status("warning", "No MKV files found for language detection.")
                return

        # Store detected languages
        self._detected_languages = detection_result.available_languages.copy()

        # Get current selection to preserve it if possible
        current_selection = self.language_combo.currentData()

        # Block signals while updating combo to avoid triggering dialog
        self.language_combo.blockSignals(True)

        # Update combo box with detected languages
        self.language_combo.clear()
        self.language_combo.setEnabled(True)

        # Add detected languages with track count info
        for code, name in self._detected_languages:
            tracks = detection_result.get_unique_tracks_for_language(code)
            track_count = len(tracks)
            if track_count > 1:
                display_text = f"{name} ({code}) - {track_count} tracks"
            else:
                display_text = f"{name} ({code})"
            self.language_combo.addItem(display_text, code)

        # Try to restore previous selection if it's available in detected languages
        available_codes = [code for code, _ in self._detected_languages]
        if current_selection and current_selection in available_codes:
            self._set_language_combo_by_code(self.language_combo, current_selection)
        elif "eng" in available_codes:
            # Default to English if available
            self._set_language_combo_by_code(self.language_combo, "eng")
        elif self._detected_languages:
            # Otherwise, select the first detected language
            self.language_combo.setCurrentIndex(0)

        # Re-enable signals
        self.language_combo.blockSignals(False)

        # Pre-select track(s) for the current language (without showing dialog)
        # Dialog will only show when user actively changes language selection
        selected_code = self.language_combo.currentData()
        if selected_code:
            tracks = detection_result.get_unique_tracks_for_language(selected_code)
            if tracks:
                # Auto-select first track by default (or default track if flagged)
                default_track = next((t for t in tracks if t.default), tracks[0])
                self._selected_track_indices = [default_track.index]

        # Show success status
        lang_count = len(self._detected_languages)
        files_with_subs = detection_result.files_with_subtitles
        total_files = detection_result.total_files

        if files_with_subs == total_files:
            status_msg = f"Found {lang_count} subtitle language(s) in {total_files} MKV file(s)"
        else:
            status_msg = f"Found {lang_count} subtitle language(s) in {files_with_subs}/{total_files} MKV file(s)"

        self._show_language_status("info", status_msg)
    
    def clear_detected_languages(self) -> None:
        """Clear detected languages and revert to default language list."""
        self._detected_languages = []
        self._has_language_detection = False
        self._detection_result = None
        self._selected_track_indices = []
        self.language_combo.setEnabled(True)
        self._populate_default_languages()
        self._hide_language_status()
    
    def _show_language_status(self, level: str, message: str) -> None:
        """Show status message for language detection."""
        self.language_status_label.setText(message)
        self.language_status_label.show()
        
        # Apply styling based on level
        if level == "error":
            self.language_status_label.setStyleSheet("color: #ff6b6b; font-weight: bold;")
        elif level == "warning":
            self.language_status_label.setStyleSheet("color: #ffa726; font-weight: bold;")
        elif level == "info":
            self.language_status_label.setStyleSheet("color: #66bb6a; font-weight: bold;")
        else:
            self.language_status_label.setStyleSheet("")
    
    def _hide_language_status(self) -> None:
        """Hide the language status label."""
        self.language_status_label.hide()
    
    def has_detected_languages(self) -> bool:
        """Check if language detection has been performed and languages are available."""
        return self._has_language_detection and bool(self._detected_languages)
    
    def get_detected_languages(self) -> List[Tuple[str, str]]:
        """Get the list of detected languages."""
        return self._detected_languages.copy()
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        return {
            'language_code': self.language_combo.currentData() or 'eng',
            'output_directory': self.output_dir_edit.text() or self._project_directory,
            'format': 'srt',  # Fixed to SRT format only
            'extract_all': self.extract_all_checkbox.isChecked(),
            'overwrite_existing': self.overwrite_checkbox.isChecked(),
            'track_indices': self._selected_track_indices.copy() if self._selected_track_indices else []
        }

    def get_selected_track_indices(self) -> List[int]:
        """Get the list of user-selected track indices."""
        return self._selected_track_indices.copy()
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()
        
        # Check if language combo is disabled (no subtitles found)
        if not self.language_combo.isEnabled():
            return ValidationResult(False, "No subtitle tracks found in MKV file(s). Cannot extract subtitles.")
        
        # Check if a language is selected
        if not config['language_code']:
            return ValidationResult(False, "Please select a subtitle language to extract.")
        
        # Check output directory
        output_dir = config['output_directory']
        if output_dir and not Path(output_dir).exists():
            return ValidationResult(False, f"Output directory does not exist: {output_dir}")
        
        return ValidationResult(True)


class TranslateConfigWidget(QFrame):
    """Configuration widget for the Translate stage."""

    config_changed = Signal()

    def __init__(self, config_manager=None, parent: QWidget = None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._setup_ui()
        self._connect_signals()
        self._load_api_key_from_settings()
        self._restore_last_used()
    
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
        self.engine_combo.addItems([
            "OpenAI", "Claude", "OpenRouter", "xAI",
            "Mistral", "Groq", "DeepSeek", "Kimi", "Gemini", "Z.ai", "LM Studio"
        ])
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
        self.chunk_size_spin.setRange(1, 9999)
        self.chunk_size_spin.setValue(200)
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
        self.model_combo.currentTextChanged.connect(self._save_last_used)
        self.api_key_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.chunk_size_spin.valueChanged.connect(lambda: self.config_changed.emit())
        self.context_edit.textChanged.connect(lambda: self.config_changed.emit())
        
        self.show_key_button.toggled.connect(self._toggle_api_key_visibility)
    
    def _on_engine_changed(self) -> None:
        """Handle engine selection change."""
        self._update_model_options()
        self._load_api_key_from_settings()
        self._save_last_used()
        self.config_changed.emit()

    def _load_api_key_from_settings(self) -> None:
        """Load API key from settings for the current engine.

        Always refreshes from settings so the field reflects what the user
        configured there. The user can still type a different key in the
        main window for a one-off task.
        """
        if not self._config_manager:
            return

        # Get current engine/provider
        engine_text = self.engine_combo.currentText().lower().replace(' ', '_')

        # Map engine names to settings keys
        engine_to_settings = {
            'openai': 'openai',
            'claude': 'anthropic',
            'openrouter': 'openrouter',
            'xai': 'xai',
            'mistral': 'mistral',
            'groq': 'groq',
            'deepseek': 'deepseek',
            'kimi': 'moonshot',
            'gemini': 'gemini',
            'z.ai': 'zai',
            'lm_studio': 'lm_studio',
        }
        settings_provider = engine_to_settings.get(engine_text, engine_text)

        # Load from settings
        settings = self._config_manager.get_settings()
        translators_config = settings.get('translators', {})
        provider_config = translators_config.get(settings_provider, {})
        api_key = provider_config.get('api_key', '').strip()

        self.api_key_edit.setText(api_key)

    def _update_model_options(self) -> None:
        """Update available models based on selected engine."""
        engine = self.engine_combo.currentText()
        self.model_combo.clear()

        # Load provider settings first so we can use selected_models
        custom_models = []
        default_model = ""
        selected_models = []

        if self._config_manager:
            engine_to_settings = {
                'OpenAI': 'openai',
                'Claude': 'anthropic',
                'OpenRouter': 'openrouter',
                'xAI': 'xai',
                'Mistral': 'mistral',
                'Groq': 'groq',
                'DeepSeek': 'deepseek',
                'Kimi': 'moonshot',
                'Gemini': 'gemini',
                'Z.ai': 'zai',
                'LM Studio': 'lm_studio',
            }
            settings_provider = engine_to_settings.get(engine, engine.lower())
            settings = self._config_manager.get_settings()
            translators_config = settings.get('translators', {})
            provider_config = translators_config.get(settings_provider, {})
            custom_models = provider_config.get('custom_models', [])
            default_model = provider_config.get('default_model', '')
            selected_models = provider_config.get('selected_models', [])

        # Determine built-in model list; for OpenAI/OpenRouter use user-selected models
        # when available, otherwise fall back to hardcoded defaults.
        builtin_models = []
        placeholder = ""

        if engine == "OpenAI":
            builtin_models = selected_models if selected_models else [
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
            ]
            placeholder = "OpenAI API key"
        elif engine == "Claude":
            builtin_models = [
                "claude-sonnet-4-5-20250929",
                "claude-haiku-4-5-20251001",
                "claude-opus-4-5-20251101",
            ]
            placeholder = "Anthropic API key"
        elif engine == "OpenRouter":
            builtin_models = selected_models if selected_models else [
                "anthropic/claude-sonnet-4-5-20250929",
                "anthropic/claude-haiku-4-5-20251001",
                "anthropic/claude-opus-4-5-20251101",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "google/gemini-pro-1.5",
                "meta-llama/llama-3.1-405b-instruct",
            ]
            placeholder = "OpenRouter API key"
        elif engine == "LM Studio":
            builtin_models = ["Local Model (LM Studio)", "Custom Endpoint"]
            placeholder = "Optional: API key for custom endpoint"
        elif engine == "xAI":
            builtin_models = selected_models if selected_models else [
                "grok-2-latest", "grok-2-mini-latest", "grok-beta"
            ]
            placeholder = "xAI API key"
        elif engine == "Mistral":
            builtin_models = selected_models if selected_models else [
                "mistral-large-latest", "mistral-small-latest", "codestral-latest"
            ]
            placeholder = "Mistral API key"
        elif engine == "Groq":
            builtin_models = selected_models if selected_models else [
                "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"
            ]
            placeholder = "Groq API key"
        elif engine == "DeepSeek":
            builtin_models = selected_models if selected_models else [
                "deepseek-chat", "deepseek-reasoner"
            ]
            placeholder = "DeepSeek API key"
        elif engine == "Kimi":
            builtin_models = selected_models if selected_models else [
                "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"
            ]
            placeholder = "Kimi (Moonshot) API key"
        elif engine == "Gemini":
            builtin_models = selected_models if selected_models else [
                "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"
            ]
            placeholder = "Google Gemini API key (AIza...)"
        elif engine == "Z.ai":
            builtin_models = selected_models if selected_models else [
                "glm-4.7", "glm-5", "glm-4.5-air", "glm-4-flash"
            ]
            placeholder = "Z.ai API key"

        self.api_key_edit.setPlaceholderText(placeholder)

        # Add built-in models
        self.model_combo.addItems(builtin_models)

        # Add custom models with separator if any
        if custom_models:
            self.model_combo.insertSeparator(len(builtin_models))
            for model in custom_models:
                self.model_combo.addItem(f"★ {model}")

        # Select the default model
        if default_model:
            index = self.model_combo.findText(default_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
            else:
                index = self.model_combo.findText(f"★ {default_model}")
                if index >= 0:
                    self.model_combo.setCurrentIndex(index)

    def _save_last_used(self, *_):
        """Persist the current engine + model to settings so they survive restarts."""
        if not self._config_manager:
            return
        model = self.model_combo.currentText()
        if model.startswith("★ "):
            model = model[2:].strip()
        ui_settings = self._config_manager.get_settings('ui')
        ui_settings['last_translate_engine'] = self.engine_combo.currentText()
        ui_settings['last_translate_model'] = model
        self._config_manager.update_settings('ui', ui_settings, save=True)

    def _restore_last_used(self):
        """Restore the last-used engine and model from settings."""
        if not self._config_manager:
            return
        ui_settings = self._config_manager.get_settings('ui')
        saved_engine = ui_settings.get('last_translate_engine', '')
        saved_model = ui_settings.get('last_translate_model', '')

        if saved_engine:
            idx = self.engine_combo.findText(saved_engine)
            if idx >= 0 and idx != self.engine_combo.currentIndex():
                # Triggers _on_engine_changed → _update_model_options
                self.engine_combo.setCurrentIndex(idx)

        if saved_model:
            idx = self.model_combo.findText(saved_model)
            if idx < 0:
                idx = self.model_combo.findText(f"★ {saved_model}")
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

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
            'openai':     'openai',
            'claude':     'claude',
            'openrouter': 'openrouter',
            'xai':        'xai',
            'mistral':    'mistral',
            'groq':       'groq',
            'deepseek':   'deepseek',
            'kimi':       'moonshot',
            'gemini':     'gemini',
            'z.ai':       'zai',
            'lm_studio':  'local',
        }

        engine_text = self.engine_combo.currentText().lower().replace(' ', '_')
        provider = provider_mapping.get(engine_text, engine_text)

        # Get model name, stripping star prefix from custom models
        model = self.model_combo.currentText()
        if model.startswith("★ "):
            model = model[2:].strip()

        return {
            'source_language': self.source_lang_combo.currentData() or 'auto',
            'target_language': self.target_lang_combo.currentData() or 'en',
            'provider': provider,
            'model': model,
            'api_key': self.api_key_edit.text(),
            'chunk_size': self.chunk_size_spin.value(),
            'context': self.context_edit.toPlainText().strip()
        }
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()
        
        # Check if API key is required
        provider = config['provider']
        _keyed = {'openai', 'anthropic', 'claude', 'openrouter',
                  'xai', 'mistral', 'groq', 'deepseek', 'moonshot', 'gemini', 'zai'}
        if provider in _keyed and not config['api_key']:
            _display = {
                'anthropic': 'Claude', 'claude': 'Claude',
                'openrouter': 'OpenRouter', 'xai': 'xAI',
                'mistral': 'Mistral', 'groq': 'Groq',
                'deepseek': 'DeepSeek', 'moonshot': 'Moonshot (Kimi)',
                'gemini': 'Gemini', 'zai': 'Z.ai',
            }
            provider_display = _display.get(provider, provider.upper())
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

    def __init__(self, config_manager=None, parent: QWidget = None):
        super().__init__(parent)
        self._translate_enabled = False
        self._config_manager = config_manager
        self._setup_ui()
        self._connect_signals()
        self._load_api_key_from_settings()
        self._restore_last_used()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QFormLayout(self)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(10)

        # "Use same as Translate" checkbox (will be shown only when translate is enabled)
        self.use_translate_settings_checkbox = QCheckBox("Use same provider settings as Translate stage")
        self.use_translate_settings_checkbox.setChecked(True)
        self.use_translate_settings_checkbox.setVisible(False)  # Hidden by default
        layout.addRow("", self.use_translate_settings_checkbox)

        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItems([
            "OpenAI", "Claude", "OpenRouter", "xAI",
            "Mistral", "Groq", "DeepSeek", "Kimi", "Gemini", "Z.ai"
        ])
        layout.addRow("AI Provider:", self.provider_combo)

        # Model selection (provider-specific)
        self.model_combo = QComboBox()
        layout.addRow("Model:", self.model_combo)

        # API key field
        api_key_layout = QHBoxLayout()
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("Enter API key or set in Settings")
        self.show_key_button = QPushButton(self.tr("Show"))
        self.show_key_button.setMaximumWidth(60)
        self.show_key_button.setCheckable(True)
        api_key_layout.addWidget(self.api_key_edit)
        api_key_layout.addWidget(self.show_key_button)
        layout.addRow("API Key:", api_key_layout)

        # Language filter for subtitle files
        language_filter_layout = QHBoxLayout()
        self.language_filter_edit = QLineEdit()
        self.language_filter_edit.setPlaceholderText("e.g., 'bg' for .bg.srt, 'en' for .en.srt (leave empty for all)")
        self.language_filter_edit.setMaximumWidth(150)
        language_filter_layout.addWidget(self.language_filter_edit)

        language_filter_help = QLabel(self.tr("Filter subtitles by language code"))
        language_filter_help.setStyleSheet("color: #bbb; font-size: 10px;")
        language_filter_layout.addWidget(language_filter_help)
        language_filter_layout.addStretch()

        layout.addRow("Language Filter:", language_filter_layout)

        # Explanation
        filter_explanation = QLabel(self.tr("Use this when you have multiple subtitle files (e.g., .srt and .bg.srt).\n"
                                            "Enter 'bg' to only sync Bulgarian subtitles, or leave empty to sync all."))
        filter_explanation.setStyleSheet("color: #888; font-size: 9pt; font-style: italic;")
        filter_explanation.setWordWrap(True)
        layout.addRow("", filter_explanation)

        # Naming template (currently not used by script)
        self.template_edit = QLineEdit()
        self.template_edit.setText("{video_name}.{language}.srt")
        self.template_edit.setPlaceholderText("{video_name}.{language}.srt")
        self.template_edit.setVisible(False)  # Hide since not currently used
        # layout.addRow("Naming Template:", self.template_edit)

        # Dry run toggle (hidden - always preview first then confirm)
        self.dry_run_checkbox = QCheckBox("Dry run (preview changes without renaming)")
        self.dry_run_checkbox.setChecked(False)  # Will show confirmation dialog instead
        self.dry_run_checkbox.setVisible(False)  # Hidden
        # layout.addRow("", self.dry_run_checkbox)

        # Confidence threshold
        self.confidence_slider = QSlider(Qt.Horizontal)
        self.confidence_slider.setRange(50, 100)
        self.confidence_slider.setValue(80)
        self.confidence_label = QLabel("80%")
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(self.confidence_slider)
        confidence_layout.addWidget(self.confidence_label)
        layout.addRow("Confidence Threshold:", confidence_layout)

        # Auto-backup existing files toggle
        self.auto_backup_existing_checkbox = QCheckBox("Auto-backup existing target files to .original.srt")
        self.auto_backup_existing_checkbox.setChecked(True)
        self.auto_backup_existing_checkbox.setToolTip(
            "When enabled, if target file already exists (e.g., movie.srt),\n"
            "it will be automatically renamed to movie.original.srt before renaming the source file.\n"
            "This is useful when syncing translated subtitles (.bg.srt) to match video names."
        )
        layout.addRow("", self.auto_backup_existing_checkbox)

        # Backup option (not currently used by script)
        self.backup_checkbox = QCheckBox("Create backup of original filenames")
        self.backup_checkbox.setChecked(True)
        self.backup_checkbox.setVisible(False)  # Hide as not implemented in script
        # layout.addRow("", self.backup_checkbox)

        # Case sensitivity (hidden - always case sensitive)
        self.case_sensitive_checkbox = QCheckBox("Case-sensitive matching")
        self.case_sensitive_checkbox.setChecked(True)  # Always case sensitive
        self.case_sensitive_checkbox.setVisible(False)  # Hidden
        # layout.addRow("", self.case_sensitive_checkbox)

        # Update model options based on provider
        self._update_model_options()
    
    def _load_api_key_from_settings(self) -> None:
        """Load API key from settings for the current provider.

        Always refreshes from settings so the field reflects what the user
        configured there. The user can still type a different key in the
        main window for a one-off task.
        """
        if not self._config_manager:
            return

        # Get current provider
        provider_text = self.provider_combo.currentText().lower()

        # Map to settings key (Sync uses 'claude', but settings uses 'anthropic')
        provider_map = {
            'claude': 'anthropic',
            'openrouter': 'openrouter',
            'xai': 'xai',
            'mistral': 'mistral',
            'groq': 'groq',
            'deepseek': 'deepseek',
            'kimi': 'moonshot',
            'gemini': 'gemini',
            'z.ai': 'zai',
        }
        settings_provider = provider_map.get(provider_text, provider_text)

        # Load from settings
        settings = self._config_manager.get_settings()
        translators_config = settings.get('translators', {})
        provider_config = translators_config.get(settings_provider, {})
        api_key = provider_config.get('api_key', '').strip()

        self.api_key_edit.setText(api_key)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.use_translate_settings_checkbox.toggled.connect(self._on_use_translate_toggled)
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        self.model_combo.currentTextChanged.connect(lambda: self.config_changed.emit())
        self.model_combo.currentTextChanged.connect(self._save_last_used)
        self.api_key_edit.textChanged.connect(lambda: self.config_changed.emit())
        self.show_key_button.toggled.connect(self._toggle_api_key_visibility)
        self.language_filter_edit.textChanged.connect(lambda: self.config_changed.emit())
        # self.template_edit.textChanged.connect(lambda: self.config_changed.emit())  # Hidden
        # self.dry_run_checkbox.toggled.connect(lambda: self.config_changed.emit())  # Hidden
        self.confidence_slider.valueChanged.connect(self._on_confidence_changed)
        self.auto_backup_existing_checkbox.toggled.connect(lambda: self.config_changed.emit())
        # self.backup_checkbox.toggled.connect(lambda: self.config_changed.emit())  # Hidden
        # self.case_sensitive_checkbox.toggled.connect(lambda: self.config_changed.emit())  # Hidden
    
    def _on_confidence_changed(self, value: int) -> None:
        """Handle confidence threshold change."""
        self.confidence_label.setText(f"{value}%")
        self.config_changed.emit()

    def _on_use_translate_toggled(self, checked: bool) -> None:
        """Handle 'Use same as Translate' checkbox toggle."""
        # Only disable provider settings if translate is actually enabled
        # If translate is not enabled, always enable these fields
        should_disable = checked and self._translate_enabled

        self.provider_combo.setEnabled(not should_disable)
        self.model_combo.setEnabled(not should_disable)
        self.api_key_edit.setEnabled(not should_disable)
        self.show_key_button.setEnabled(not should_disable)
        self.config_changed.emit()

    def _on_provider_changed(self) -> None:
        """Handle provider selection change."""
        self._update_model_options()
        self._load_api_key_from_settings()
        self._save_last_used()
        self.config_changed.emit()

    def _update_model_options(self) -> None:
        """Update available models based on selected provider."""
        provider = self.provider_combo.currentText()
        self.model_combo.clear()

        # Load selected_models from settings for OpenAI / OpenRouter and new providers
        selected_models = []
        if self._config_manager:
            provider_to_settings = {
                'OpenAI': 'openai',
                'Claude': 'anthropic',
                'OpenRouter': 'openrouter',
                'xAI': 'xai',
                'Mistral': 'mistral',
                'Groq': 'groq',
                'DeepSeek': 'deepseek',
                'Kimi': 'moonshot',
                'Gemini': 'gemini',
                'Z.ai': 'zai',
            }
            settings_key = provider_to_settings.get(provider, provider.lower())
            settings = self._config_manager.get_settings()
            provider_cfg = settings.get('translators', {}).get(settings_key, {})
            selected_models = provider_cfg.get('selected_models', [])

        if provider == "OpenAI":
            models = selected_models if selected_models else [
                "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("OpenAI API key or set in Settings")
        elif provider == "Claude":
            self.model_combo.addItems([
                "claude-sonnet-4-5-20250929", "claude-haiku-4-5-20251001", "claude-opus-4-5-20251101"
            ])
            self.api_key_edit.setPlaceholderText("Anthropic API key or set in Settings")
        elif provider == "OpenRouter":
            models = selected_models if selected_models else [
                "anthropic/claude-sonnet-4-5-20250929",
                "anthropic/claude-haiku-4-5-20251001",
                "anthropic/claude-opus-4-5-20251101",
                "openai/gpt-4o",
                "openai/gpt-4o-mini",
                "google/gemini-pro-1.5",
                "meta-llama/llama-3.1-405b-instruct",
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("OpenRouter API key or set in Settings")
        elif provider == "xAI":
            models = selected_models if selected_models else [
                "grok-2-latest", "grok-2-mini-latest", "grok-beta"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("xAI API key or set in Settings")
        elif provider == "Mistral":
            models = selected_models if selected_models else [
                "mistral-large-latest", "mistral-small-latest", "codestral-latest"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("Mistral API key or set in Settings")
        elif provider == "Groq":
            models = selected_models if selected_models else [
                "llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("Groq API key or set in Settings")
        elif provider == "DeepSeek":
            models = selected_models if selected_models else [
                "deepseek-chat", "deepseek-reasoner"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("DeepSeek API key or set in Settings")
        elif provider == "Kimi":
            models = selected_models if selected_models else [
                "moonshot-v1-128k", "moonshot-v1-32k", "moonshot-v1-8k"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("Kimi (Moonshot) API key or set in Settings")
        elif provider == "Gemini":
            models = selected_models if selected_models else [
                "gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-pro", "gemini-1.5-flash"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("Google Gemini API key or set in Settings")
        elif provider == "Z.ai":
            models = selected_models if selected_models else [
                "glm-4.7", "glm-5", "glm-4.5-air", "glm-4-flash"
            ]
            self.model_combo.addItems(models)
            self.api_key_edit.setPlaceholderText("Z.ai API key or set in Settings")

    def _save_last_used(self, *_):
        """Persist the current provider + model to settings so they survive restarts."""
        if not self._config_manager:
            return
        model = self.model_combo.currentText()
        if model.startswith("★ "):
            model = model[2:].strip()
        ui_settings = self._config_manager.get_settings('ui')
        ui_settings['last_sync_provider'] = self.provider_combo.currentText()
        ui_settings['last_sync_model'] = model
        self._config_manager.update_settings('ui', ui_settings, save=True)

    def _restore_last_used(self):
        """Restore the last-used provider and model from settings."""
        if not self._config_manager:
            return
        ui_settings = self._config_manager.get_settings('ui')
        saved_provider = ui_settings.get('last_sync_provider', '')
        saved_model = ui_settings.get('last_sync_model', '')

        if saved_provider:
            idx = self.provider_combo.findText(saved_provider)
            if idx >= 0 and idx != self.provider_combo.currentIndex():
                # Triggers _on_provider_changed → _update_model_options
                self.provider_combo.setCurrentIndex(idx)

        if saved_model:
            idx = self.model_combo.findText(saved_model)
            if idx < 0:
                idx = self.model_combo.findText(f"★ {saved_model}")
            if idx >= 0:
                self.model_combo.setCurrentIndex(idx)

    def _toggle_api_key_visibility(self, show: bool) -> None:
        """Toggle API key visibility."""
        if show:
            self.api_key_edit.setEchoMode(QLineEdit.Normal)
            self.show_key_button.setText(self.tr("Hide"))
        else:
            self.api_key_edit.setEchoMode(QLineEdit.Password)
            self.show_key_button.setText(self.tr("Show"))

    def set_translate_enabled(self, enabled: bool) -> None:
        """Set whether translate stage is enabled (shows/hides the 'Use same as Translate' checkbox)."""
        self._translate_enabled = enabled
        self.use_translate_settings_checkbox.setVisible(enabled)
        # Trigger the toggle handler to update UI state
        self._on_use_translate_toggled(self.use_translate_settings_checkbox.isChecked())
    
    def get_config(self) -> Dict[str, Any]:
        """Get the current configuration."""
        # Map UI display names to script provider names
        provider_mapping = {
            'openai':     'openai',
            'claude':     'claude',
            'openrouter': 'openrouter',
            'xai':        'xai',
            'mistral':    'mistral',
            'groq':       'groq',
            'deepseek':   'deepseek',
            'kimi':       'moonshot',
            'gemini':     'gemini',
            'z.ai':       'zai',
        }

        provider_text = self.provider_combo.currentText().lower()
        provider = provider_mapping.get(provider_text, provider_text)

        return {
            'use_translate_settings': self.use_translate_settings_checkbox.isChecked() and self._translate_enabled,
            'provider': provider,
            'model': self.model_combo.currentText(),
            'api_key': self.api_key_edit.text(),
            'language_filter': self.language_filter_edit.text().strip(),
            'naming_template': self.template_edit.text(),
            'dry_run': self.dry_run_checkbox.isChecked(),
            'confidence_threshold': self.confidence_slider.value() / 100.0,
            'auto_backup_existing': self.auto_backup_existing_checkbox.isChecked(),
            'create_backup': self.backup_checkbox.isChecked(),
            'case_sensitive': self.case_sensitive_checkbox.isChecked()
        }
    
    def validate(self) -> ValidationResult:
        """Validate the current configuration."""
        config = self.get_config()

        # Only validate provider settings if NOT using translate settings
        if not config['use_translate_settings']:
            # Check if API key is provided (either in UI or in Settings)
            provider = config['provider']
            has_ui_api_key = bool(config['api_key'])

            # Check Settings for API key if not provided in UI
            has_settings_api_key = False
            if self._config_manager and not has_ui_api_key:
                settings = self._config_manager.get_settings()
                translators_config = settings.get('translators', {})

                # Map provider to settings key
                # Sync script uses 'claude', but settings use 'anthropic'
                settings_provider = 'anthropic' if provider == 'claude' else provider
                provider_config = translators_config.get(settings_provider, {})
                has_settings_api_key = bool(provider_config.get('api_key', '').strip())

            # Also check environment variables
            has_env_api_key = False
            if not has_ui_api_key and not has_settings_api_key:
                import os
                from dotenv import load_dotenv

                # Load .env file if it exists
                env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
                if os.path.exists(env_file):
                    load_dotenv(env_file)

                if provider in ['openai', 'claude', 'openrouter']:
                    if provider == 'claude':
                        env_var = 'ANTHROPIC_API_KEY'
                    elif provider == 'openrouter':
                        env_var = 'OPENROUTER_API_KEY'
                    else:
                        env_var = 'OPENAI_API_KEY'
                    has_env_api_key = bool(os.getenv(env_var, '').strip())

            # Validate that API key is available from at least one source
            if provider in ['openai', 'claude', 'openrouter'] and not (has_ui_api_key or has_settings_api_key or has_env_api_key):
                provider_display = 'Claude' if provider == 'claude' else ('OpenRouter' if provider == 'openrouter' else 'OpenAI')
                return ValidationResult(False, f"{provider_display} API key is required for Sync stage. "
                                              f"Please enter it here, set it in Settings (File → Settings → Translators), "
                                              f"or set it in environment variables.")

            # Check model is specified
            if not config['model']:
                return ValidationResult(False, "Model must be specified for Sync stage")

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


class FpsSyncConfigWidget(QWidget):
    """Configuration widget for the FPS frame-rate conversion stage."""

    config_changed = Signal()

    # Common FPS presets
    FPS_PRESETS = [
        ("23.976 (NTSC Film)", 24000 / 1001),
        ("24 (Film)", 24.0),
        ("25 (PAL)", 25.0),
        ("29.97 (NTSC)", 30000 / 1001),
        ("30", 30.0),
        ("50 (PAL HD)", 50.0),
        ("59.94 (NTSC HD)", 60000 / 1001),
        ("60", 60.0),
    ]

    def __init__(self, config_manager=None, parent: QWidget = None):
        super().__init__(parent)
        self._config_manager = config_manager
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        # Source FPS
        self.source_fps_combo = QComboBox()
        self.source_fps_combo.setEditable(True)
        for label, _ in self.FPS_PRESETS:
            self.source_fps_combo.addItem(label)
        self.source_fps_combo.setCurrentText("25 (PAL)")
        self.source_fps_combo.setToolTip(self.tr("Frame rate the subtitles were authored for"))
        layout.addRow(self.tr("Source FPS:"), self.source_fps_combo)

        # Target FPS mode
        self.target_mode_combo = QComboBox()
        self.target_mode_combo.addItems([
            self.tr("Specify FPS"),
            self.tr("Auto-detect from video"),
        ])
        self.target_mode_combo.setToolTip(
            self.tr("How to determine the target frame rate")
        )
        layout.addRow(self.tr("Target FPS mode:"), self.target_mode_combo)

        # Target FPS (shown when mode = Specify FPS)
        self.target_fps_combo = QComboBox()
        self.target_fps_combo.setEditable(True)
        for label, _ in self.FPS_PRESETS:
            self.target_fps_combo.addItem(label)
        self.target_fps_combo.setCurrentText("23.976 (NTSC Film)")
        self.target_fps_combo.setToolTip(self.tr("Target frame rate for the output subtitles"))
        layout.addRow(self.tr("Target FPS:"), self.target_fps_combo)

        # Overwrite checkbox
        self.overwrite_check = QCheckBox(self.tr("Overwrite input file in-place"))
        self.overwrite_check.setChecked(True)
        self.overwrite_check.setToolTip(
            self.tr("When checked, the original SRT is replaced with the converted version.\n"
                    "Uncheck to write to the output directory instead.")
        )
        layout.addRow("", self.overwrite_check)

        # Output directory (optional, shown when not overwriting)
        self.output_dir_layout = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText(self.tr("Same directory as input (optional)"))
        self.output_dir_browse = QPushButton(self.tr("Browse…"))
        self.output_dir_browse.setFixedWidth(80)
        self.output_dir_layout.addWidget(self.output_dir_edit)
        self.output_dir_layout.addWidget(self.output_dir_browse)
        self.output_dir_widget = QWidget()
        self.output_dir_widget.setLayout(self.output_dir_layout)
        layout.addRow(self.tr("Output directory:"), self.output_dir_widget)

        # Initially hide output dir (overwrite is default)
        self.output_dir_widget.setVisible(False)

    def _connect_signals(self) -> None:
        self.source_fps_combo.currentTextChanged.connect(self.config_changed)
        self.target_mode_combo.currentIndexChanged.connect(self._on_target_mode_changed)
        self.target_fps_combo.currentTextChanged.connect(self.config_changed)
        self.overwrite_check.toggled.connect(self._on_overwrite_toggled)
        self.output_dir_edit.textChanged.connect(self.config_changed)
        self.output_dir_browse.clicked.connect(self._browse_output_dir)

    def _on_target_mode_changed(self, index: int) -> None:
        # index 0 = Specify FPS, index 1 = Auto-detect
        self.target_fps_combo.setVisible(index == 0)
        self.config_changed.emit()

    def _on_overwrite_toggled(self, checked: bool) -> None:
        self.output_dir_widget.setVisible(not checked)
        self.config_changed.emit()

    def _browse_output_dir(self) -> None:
        from PySide6.QtWidgets import QFileDialog
        directory = QFileDialog.getExistingDirectory(
            self, self.tr("Select Output Directory"), self.output_dir_edit.text()
        )
        if directory:
            self.output_dir_edit.setText(directory)

    def _parse_fps(self, text: str) -> float:
        """Extract numeric FPS from a combo-box label or plain number string."""
        # Try exact match to preset values first
        for label, value in self.FPS_PRESETS:
            if text.strip() == label:
                return value
        # Otherwise try to parse the leading number
        import re as _re
        m = _re.match(r"([\d.]+)", text.strip())
        if m:
            return float(m.group(1))
        return 25.0

    def get_config(self) -> dict:
        """Return current widget state as a plain dict."""
        auto_detect = self.target_mode_combo.currentIndex() == 1
        target_fps = None if auto_detect else self._parse_fps(self.target_fps_combo.currentText())
        return {
            "source_fps": self._parse_fps(self.source_fps_combo.currentText()),
            "target_fps": target_fps,
            "auto_detect": auto_detect,
            "overwrite_existing": self.overwrite_check.isChecked(),
            "output_directory": self.output_dir_edit.text().strip() or None,
        }

    def validate(self) -> "ValidationResult":
        cfg = self.get_config()
        if cfg["source_fps"] <= 0:
            return ValidationResult(False, "Source FPS must be positive")
        if not cfg["auto_detect"] and cfg["target_fps"] is not None and cfg["target_fps"] <= 0:
            return ValidationResult(False, "Target FPS must be positive")
        return ValidationResult(True)


class StageConfigurators(QFrame):
    """
    Container widget for all stage configuration panels.

    Manages expandable configuration sections for Extract, FPS Sync, Translate, and Sync stages.
    """
    
    config_changed = Signal()
    
    def __init__(self, config_manager=None, parent: QWidget = None):
        super().__init__(parent)
        
        self._project_directory = ""
        self._enabled_stages = {'extract': False, 'fps_sync': False, 'translate': False, 'sync': False}
        self._config_manager = config_manager
        
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setFrameStyle(QFrame.StyledPanel)
        self.setLineWidth(1)
        
        # Main vertical layout for title and configuration sections
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Title
        title_label = QLabel(self.tr("Stage Configuration"))
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Horizontal layout for configuration panels (side by side)
        config_layout = QHBoxLayout()
        config_layout.setSpacing(15)
        
        # Extract configuration
        self.extract_group = QCollapsibleGroupBox(self.tr("Extract Configuration"))
        self.extract_config = ExtractConfigWidget(self._config_manager)
        extract_layout = QVBoxLayout(self.extract_group)
        extract_layout.addWidget(self.extract_config)
        self.extract_group.setContentWidget(self.extract_config)
        config_layout.addWidget(self.extract_group)

        # FPS Sync configuration
        self.fps_sync_group = QCollapsibleGroupBox(self.tr("FPS Convert Configuration"))
        self.fps_sync_config = FpsSyncConfigWidget(self._config_manager)
        fps_sync_layout = QVBoxLayout(self.fps_sync_group)
        fps_sync_layout.addWidget(self.fps_sync_config)
        self.fps_sync_group.setContentWidget(self.fps_sync_config)
        config_layout.addWidget(self.fps_sync_group)

        # Translate configuration
        self.translate_group = QCollapsibleGroupBox(self.tr("Translate Configuration"))
        self.translate_config = TranslateConfigWidget(self._config_manager)
        translate_layout = QVBoxLayout(self.translate_group)
        translate_layout.addWidget(self.translate_config)
        self.translate_group.setContentWidget(self.translate_config)
        config_layout.addWidget(self.translate_group)

        # Sync configuration
        self.sync_group = QCollapsibleGroupBox(self.tr("Sync Configuration"))
        self.sync_config = SyncConfigWidget(self._config_manager)
        sync_layout = QVBoxLayout(self.sync_group)
        sync_layout.addWidget(self.sync_config)
        self.sync_group.setContentWidget(self.sync_config)
        config_layout.addWidget(self.sync_group)

        # Add the horizontal layout to the main layout
        main_layout.addLayout(config_layout)

        # Add stretch to push everything to top
        main_layout.addStretch()

        # Initialize all groups as visible but disabled by default
        self.extract_group.setEnabled(False)
        self.fps_sync_group.setEnabled(False)
        self.translate_group.setEnabled(False)
        self.sync_group.setEnabled(False)
    
    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.extract_config.config_changed.connect(self.config_changed.emit)
        self.fps_sync_config.config_changed.connect(self.config_changed.emit)
        self.translate_config.config_changed.connect(self.config_changed.emit)
        self.sync_config.config_changed.connect(self.config_changed.emit)
    
    def update_enabled_stages(self, stages: Dict[str, bool]) -> None:
        """Update which stage configurations are enabled/disabled."""
        self._enabled_stages = stages.copy()

        # Enable/disable based on stage selection (always visible)
        self.extract_group.setEnabled(stages.get('extract', False))
        self.fps_sync_group.setEnabled(stages.get('fps_sync', False))
        self.translate_group.setEnabled(stages.get('translate', False))
        self.sync_group.setEnabled(stages.get('sync', False))

        # Notify sync config whether translate is enabled (for "Use same as Translate" checkbox)
        self.sync_config.set_translate_enabled(stages.get('translate', False))

        # Auto-expand enabled stages and collapse disabled ones
        self.extract_group.setChecked(stages.get('extract', False))
        self.fps_sync_group.setChecked(stages.get('fps_sync', False))
        self.translate_group.setChecked(stages.get('translate', False))
        self.sync_group.setChecked(stages.get('sync', False))
    
    def set_project_directory(self, directory: str) -> None:
        """Set the project directory for all configurations."""
        self._project_directory = directory
        self.extract_config.set_project_directory(directory)
    
    def get_configurations(self) -> Dict[str, Dict[str, Any]]:
        """Get all stage configurations."""
        return {
            'extract': self.extract_config.get_config(),
            'fps_sync': self.fps_sync_config.get_config(),
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
            elif stage == 'fps_sync':
                result = self.fps_sync_config.validate()
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
    
    def get_fps_sync_config(self) -> Dict[str, Any]:
        """Get FPS sync stage configuration."""
        return self.fps_sync_config.get_config()

    def get_visible_configurators(self) -> list:
        """Get list of visible configurators (all configurators are always visible now)."""
        return [self.extract_group, self.fps_sync_group, self.translate_group, self.sync_group]
    
    def update_from_settings(self, settings: Dict[str, Any]) -> None:
        """Update configurators from settings (called after settings dialog is accepted)."""
        self.translate_config._update_model_options()
        self.translate_config._load_api_key_from_settings()
        self.sync_config._update_model_options()
        self.sync_config._load_api_key_from_settings()
    
    def get_extract_widget(self) -> ExtractConfigWidget:
        """Get the extract configuration widget for signal connections."""
        return self.extract_config
    
    def update_extract_languages(self, detection_result) -> None:
        """Update extract configuration with detected languages."""
        self.extract_config.update_detected_languages(detection_result)
    
    def clear_extract_languages(self) -> None:
        """Clear detected languages in extract configuration."""
        self.extract_config.clear_detected_languages()