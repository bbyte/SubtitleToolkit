"""
Languages tab for settings dialog.

Provides interface for configuring default source and target languages,
managing language preferences, and setting up common language shortcuts.
"""

from typing import Dict, Any, List

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QListWidget, QListWidgetItem,
    QLineEdit, QDoubleSpinBox, QFormLayout, QSplitter, QFrame,
    QAbstractItemView, QMessageBox, QInputDialog
)
from PySide6.QtCore import Qt, Signal, QStringListModel
from PySide6.QtGui import QFont

from ...config import ConfigManager, ValidationResult, SettingsSchema


class LanguageComboBox(QComboBox):
    """Enhanced combo box for language selection with search and flags."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().setPlaceholderText("Type to search languages...")
        
        # Populate with supported languages
        self._populate_languages()
        
        # Enable search functionality
        self._setup_search()
    
    def _populate_languages(self):
        """Populate with all supported languages."""
        languages = SettingsSchema.get_supported_languages()
        
        for code, name in languages.items():
            display_text = f"{name} ({code})"
            self.addItem(display_text, code)
    
    def _setup_search(self):
        """Setup search functionality."""
        self.lineEdit().textChanged.connect(self._filter_languages)
    
    def _filter_languages(self, text: str):
        """Filter languages based on search text."""
        # This is a simplified implementation
        # In a full implementation, you might want more sophisticated filtering
        pass
    
    def set_language(self, language_code: str):
        """Set the current language by code."""
        for i in range(self.count()):
            if self.itemData(i) == language_code:
                self.setCurrentIndex(i)
                break
    
    def get_language(self) -> str:
        """Get the currently selected language code."""
        return self.currentData() or ""


class RecentLanguagesWidget(QWidget):
    """Widget for managing recent/favorite languages."""
    
    languages_changed = Signal()
    
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        
        self.title = title
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel(self.title)
        title_font = QFont()
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # Language list
        self.language_list = QListWidget()
        self.language_list.setMaximumHeight(150)
        self.language_list.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self.language_list)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.add_button = QPushButton("Add")
        self.add_button.clicked.connect(self._add_language)
        button_layout.addWidget(self.add_button)
        
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_language)
        self.remove_button.setEnabled(False)
        button_layout.addWidget(self.remove_button)
        
        self.move_up_button = QPushButton("▲")
        self.move_up_button.clicked.connect(self._move_up)
        self.move_up_button.setEnabled(False)
        self.move_up_button.setMaximumWidth(30)
        button_layout.addWidget(self.move_up_button)
        
        self.move_down_button = QPushButton("▼")
        self.move_down_button.clicked.connect(self._move_down)
        self.move_down_button.setEnabled(False)
        self.move_down_button.setMaximumWidth(30)
        button_layout.addWidget(self.move_down_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.language_list.itemSelectionChanged.connect(self._update_button_states)
        self.language_list.itemChanged.connect(lambda: self.languages_changed.emit())
    
    def _add_language(self):
        """Add a language to the list."""
        languages = SettingsSchema.get_supported_languages()
        
        # Create selection dialog
        language_codes = list(languages.keys())
        language_names = [f"{name} ({code})" for code, name in languages.items()]
        
        item, ok = QInputDialog.getItem(
            self, f"Add Language - {self.title}",
            "Select a language to add:",
            language_names, 0, False
        )
        
        if ok and item:
            # Extract language code
            code = item.split('(')[-1].rstrip(')')
            name = languages[code]
            
            # Check if already in list
            for i in range(self.language_list.count()):
                if self.language_list.item(i).data(Qt.UserRole) == code:
                    QMessageBox.information(
                        self, "Language Already Added",
                        f"{name} is already in the list."
                    )
                    return
            
            # Add to list
            list_item = QListWidgetItem(f"{name} ({code})")
            list_item.setData(Qt.UserRole, code)
            self.language_list.addItem(list_item)
            
            self.languages_changed.emit()
    
    def _remove_language(self):
        """Remove selected language from list."""
        current_item = self.language_list.currentItem()
        if current_item:
            row = self.language_list.row(current_item)
            self.language_list.takeItem(row)
            self.languages_changed.emit()
    
    def _move_up(self):
        """Move selected language up in list."""
        current_row = self.language_list.currentRow()
        if current_row > 0:
            item = self.language_list.takeItem(current_row)
            self.language_list.insertItem(current_row - 1, item)
            self.language_list.setCurrentRow(current_row - 1)
            self.languages_changed.emit()
    
    def _move_down(self):
        """Move selected language down in list."""
        current_row = self.language_list.currentRow()
        if current_row < self.language_list.count() - 1:
            item = self.language_list.takeItem(current_row)
            self.language_list.insertItem(current_row + 1, item)
            self.language_list.setCurrentRow(current_row + 1)
            self.languages_changed.emit()
    
    def _update_button_states(self):
        """Update button enabled states based on selection."""
        has_selection = self.language_list.currentItem() is not None
        current_row = self.language_list.currentRow()
        
        self.remove_button.setEnabled(has_selection)
        self.move_up_button.setEnabled(has_selection and current_row > 0)
        self.move_down_button.setEnabled(
            has_selection and current_row < self.language_list.count() - 1
        )
    
    def set_languages(self, language_codes: List[str]):
        """Set the list of languages."""
        self.language_list.clear()
        
        languages = SettingsSchema.get_supported_languages()
        for code in language_codes:
            if code in languages:
                name = languages[code]
                list_item = QListWidgetItem(f"{name} ({code})")
                list_item.setData(Qt.UserRole, code)
                self.language_list.addItem(list_item)
    
    def get_languages(self) -> List[str]:
        """Get the list of language codes."""
        codes = []
        for i in range(self.language_list.count()):
            item = self.language_list.item(i)
            code = item.data(Qt.UserRole)
            if code:
                codes.append(code)
        return codes


class LanguagesTab(QWidget):
    """
    Languages configuration tab.
    
    Provides interface for:
    - Default source and target language selection
    - Recent/favorite language management
    - Language detection confidence settings
    - Quick language access configuration
    """
    
    settings_changed = Signal(str)  # section name
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Default languages group
        defaults_group = self._create_defaults_group()
        layout.addWidget(defaults_group)
        
        # Create splitter for recent languages
        splitter = QSplitter(Qt.Horizontal)
        
        # Recent languages
        recent_frame = self._create_recent_languages_frame()
        splitter.addWidget(recent_frame)
        
        # Advanced settings
        advanced_frame = self._create_advanced_frame()
        splitter.addWidget(advanced_frame)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _create_defaults_group(self) -> QGroupBox:
        """Create default language selection group."""
        group = QGroupBox("Default Languages")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(15)
        
        # Source language
        self.source_language_combo = LanguageComboBox()
        self.source_language_combo.set_language("auto")  # Default to auto-detect
        form_layout.addRow("Default Source Language:", self.source_language_combo)
        
        # Help text for source
        source_help = QLabel("Source language for translation. Use 'Auto-detect' to automatically detect the language.")
        source_help.setStyleSheet("color: #666; font-size: 10px;")
        source_help.setWordWrap(True)
        form_layout.addRow("", source_help)
        
        # Target language
        self.target_language_combo = LanguageComboBox()
        self.target_language_combo.set_language("en")  # Default to English
        form_layout.addRow("Default Target Language:", self.target_language_combo)
        
        # Help text for target
        target_help = QLabel("Target language for translation output.")
        target_help.setStyleSheet("color: #666; font-size: 10px;")
        target_help.setWordWrap(True)
        form_layout.addRow("", target_help)
        
        return group
    
    def _create_recent_languages_frame(self) -> QFrame:
        """Create recent languages management frame."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Quick Access Languages")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Manage frequently used languages for quick access in dropdowns.")
        desc.setStyleSheet("color: #666;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Recent source languages
        self.recent_source = RecentLanguagesWidget("Recent Source Languages")
        layout.addWidget(self.recent_source)
        
        # Recent target languages
        self.recent_target = RecentLanguagesWidget("Recent Target Languages")
        layout.addWidget(self.recent_target)
        
        return frame
    
    def _create_advanced_frame(self) -> QFrame:
        """Create advanced language settings frame."""
        frame = QFrame()
        frame.setFrameStyle(QFrame.StyledPanel)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Advanced Settings")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Settings form
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        # Language detection confidence
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setDecimals(2)
        self.confidence_spin.setValue(0.80)
        self.confidence_spin.setToolTip("Minimum confidence required for automatic language detection")
        form_layout.addRow("Detection Confidence:", self.confidence_spin)
        
        confidence_help = QLabel("Higher values require more certainty for auto-detection but may fall back to manual selection more often.")
        confidence_help.setStyleSheet("color: #666; font-size: 10px;")
        confidence_help.setWordWrap(True)
        form_layout.addRow("", confidence_help)
        
        layout.addLayout(form_layout)
        
        # Language statistics (read-only info)
        stats_group = QGroupBox("Language Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.supported_count_label = QLabel()
        stats_layout.addRow("Supported Languages:", self.supported_count_label)
        
        self.common_languages_label = QLabel()
        stats_layout.addRow("Most Common:", self.common_languages_label)
        
        layout.addWidget(stats_group)
        
        # Update statistics
        self._update_statistics()
        
        layout.addStretch()
        
        return frame
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Default language changes
        self.source_language_combo.currentIndexChanged.connect(
            lambda: self.settings_changed.emit("languages")
        )
        self.target_language_combo.currentIndexChanged.connect(
            lambda: self.settings_changed.emit("languages")
        )
        
        # Recent languages changes
        self.recent_source.languages_changed.connect(
            lambda: self.settings_changed.emit("languages")
        )
        self.recent_target.languages_changed.connect(
            lambda: self.settings_changed.emit("languages")
        )
        
        # Advanced settings changes
        self.confidence_spin.valueChanged.connect(
            lambda: self.settings_changed.emit("languages")
        )
    
    def _update_statistics(self):
        """Update language statistics display."""
        languages = SettingsSchema.get_supported_languages()
        self.supported_count_label.setText(str(len(languages)))
        
        # Show most common languages
        common = ["English (en)", "Spanish (es)", "French (fr)", "German (de)", "Chinese (zh)"]
        self.common_languages_label.setText(", ".join(common))
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the tab."""
        # Default languages
        default_source = settings.get("default_source", "auto")
        self.source_language_combo.set_language(default_source)
        
        default_target = settings.get("default_target", "en")
        self.target_language_combo.set_language(default_target)
        
        # Recent languages
        recent_source = settings.get("recent_source_languages", ["auto", "es", "fr", "de"])
        self.recent_source.set_languages(recent_source)
        
        recent_target = settings.get("recent_target_languages", ["en", "es", "fr", "de"])
        self.recent_target.set_languages(recent_target)
        
        # Advanced settings
        confidence = settings.get("language_detection_confidence", 0.8)
        self.confidence_spin.setValue(confidence)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from the tab."""
        return {
            "default_source": self.source_language_combo.get_language(),
            "default_target": self.target_language_combo.get_language(),
            "recent_source_languages": self.recent_source.get_languages(),
            "recent_target_languages": self.recent_target.get_languages(),
            "language_detection_confidence": self.confidence_spin.value(),
        }
    
    def validate_settings(self) -> ValidationResult:
        """Validate current settings."""
        errors = []
        warnings = []
        
        # Check default languages are valid
        supported_languages = SettingsSchema.get_supported_languages()
        
        source_lang = self.source_language_combo.get_language()
        if source_lang and source_lang not in supported_languages:
            errors.append(f"Invalid source language: {source_lang}")
        
        target_lang = self.target_language_combo.get_language()
        if target_lang and target_lang not in supported_languages:
            errors.append(f"Invalid target language: {target_lang}")
        
        # Check confidence value
        confidence = self.confidence_spin.value()
        if confidence < 0.5:
            warnings.append("Low detection confidence may result in inaccurate language detection")
        elif confidence > 0.95:
            warnings.append("High detection confidence may frequently fall back to manual selection")
        
        # Check recent languages lists aren't too long
        if len(self.recent_source.get_languages()) > 10:
            warnings.append("Too many recent source languages may clutter the interface")
        
        if len(self.recent_target.get_languages()) > 10:
            warnings.append("Too many recent target languages may clutter the interface")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )