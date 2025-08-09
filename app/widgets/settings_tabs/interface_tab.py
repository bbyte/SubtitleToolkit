"""
Interface tab for settings dialog.

Provides interface for configuring UI settings including language selection,
zoom preferences, and appearance options.
"""

from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QComboBox, QPushButton, QCheckBox, QDoubleSpinBox,
    QSlider, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...config import ConfigManager, ValidationResult, SettingsSchema


class InterfaceTab(QWidget):
    """
    Interface configuration tab.
    
    Provides interface for:
    - Language selection with restart handling
    - Zoom level preferences
    - Window behavior settings
    - UI appearance options
    """
    
    settings_changed = Signal(str)  # section name
    language_change_requested = Signal(str)  # language code
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Language group
        language_group = self._create_language_group()
        layout.addWidget(language_group)
        
        # Window behavior group
        window_group = self._create_window_group()
        layout.addWidget(window_group)
        
        # Appearance group
        appearance_group = self._create_appearance_group()
        layout.addWidget(appearance_group)
        
        layout.addStretch()
    
    def _create_language_group(self) -> QGroupBox:
        """Create language selection group."""
        group = QGroupBox("Interface Language")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(15)
        
        # Language selection
        self.language_combo = QComboBox()
        interface_languages = SettingsSchema.get_interface_languages()
        
        for code, name in interface_languages.items():
            self.language_combo.addItem(name, code)
        
        form_layout.addRow("Language:", self.language_combo)
        
        # Help text
        help_text = QLabel("Changes to interface language require an application restart.")
        help_text.setStyleSheet("color: #666; font-size: 10px;")
        help_text.setWordWrap(True)
        form_layout.addRow("", help_text)
        
        # Current language indicator
        self.current_language_label = QLabel()
        self.current_language_label.setStyleSheet("font-weight: bold; color: #2a82da;")
        form_layout.addRow("Current:", self.current_language_label)
        
        return group
    
    def _create_window_group(self) -> QGroupBox:
        """Create window behavior group."""
        group = QGroupBox("Window Behavior")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(15)
        
        # Remember window size
        self.remember_size_checkbox = QCheckBox("Remember window size")
        form_layout.addRow("", self.remember_size_checkbox)
        
        # Remember window position
        self.remember_position_checkbox = QCheckBox("Remember window position")
        form_layout.addRow("", self.remember_position_checkbox)
        
        return group
    
    def _create_appearance_group(self) -> QGroupBox:
        """Create appearance settings group."""
        group = QGroupBox("Appearance")
        form_layout = QFormLayout(group)
        form_layout.setSpacing(15)
        
        # Zoom level
        zoom_layout = QHBoxLayout()
        
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(50, 200)  # 50% to 200%
        self.zoom_slider.setValue(100)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)
        self.zoom_slider.setTickInterval(25)
        
        self.zoom_spinbox = QDoubleSpinBox()
        self.zoom_spinbox.setRange(0.5, 2.0)
        self.zoom_spinbox.setSingleStep(0.1)
        self.zoom_spinbox.setDecimals(1)
        self.zoom_spinbox.setSuffix("x")
        self.zoom_spinbox.setValue(1.0)
        self.zoom_spinbox.setMaximumWidth(80)
        
        zoom_layout.addWidget(self.zoom_slider)
        zoom_layout.addWidget(self.zoom_spinbox)
        
        form_layout.addRow("Zoom Level:", zoom_layout)
        
        # Smooth zoom transitions
        self.smooth_zoom_checkbox = QCheckBox("Enable smooth zoom transitions")
        self.smooth_zoom_checkbox.setChecked(True)
        form_layout.addRow("", self.smooth_zoom_checkbox)
        
        # Advanced options visibility
        self.show_advanced_checkbox = QCheckBox("Show advanced options by default")
        form_layout.addRow("", self.show_advanced_checkbox)
        
        return group
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Language selection - special handling for restart requirement
        self.language_combo.currentIndexChanged.connect(self._on_language_index_changed)
        
        # Window behavior
        self.remember_size_checkbox.toggled.connect(
            lambda: self.settings_changed.emit("ui")
        )
        self.remember_position_checkbox.toggled.connect(
            lambda: self.settings_changed.emit("ui")
        )
        
        # Appearance settings
        self.zoom_slider.valueChanged.connect(self._on_zoom_slider_changed)
        self.zoom_spinbox.valueChanged.connect(self._on_zoom_spinbox_changed)
        self.smooth_zoom_checkbox.toggled.connect(
            lambda: self.settings_changed.emit("ui")
        )
        self.show_advanced_checkbox.toggled.connect(
            lambda: self.settings_changed.emit("ui")
        )
    
    def _on_language_index_changed(self, index: int):
        """Handle language selection change."""
        if index < 0:
            return
        
        language_code = self.language_combo.itemData(index)
        if not language_code:
            return
        
        # Get current language from application
        current_ui_settings = self.config_manager.get_settings("ui")
        current_language = current_ui_settings.get("interface_language", "system")
        
        if language_code != current_language:
            # Emit signal for language change (handled by main application)
            self.language_change_requested.emit(language_code)
    
    def _on_zoom_slider_changed(self, value: int):
        """Handle zoom slider change."""
        zoom_level = value / 100.0
        self.zoom_spinbox.blockSignals(True)
        self.zoom_spinbox.setValue(zoom_level)
        self.zoom_spinbox.blockSignals(False)
        self.settings_changed.emit("ui")
    
    def _on_zoom_spinbox_changed(self, value: float):
        """Handle zoom spinbox change."""
        slider_value = int(value * 100)
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(slider_value)
        self.zoom_slider.blockSignals(False)
        self.settings_changed.emit("ui")
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the tab."""
        # Interface language
        interface_language = settings.get("interface_language", "system")
        for i in range(self.language_combo.count()):
            if self.language_combo.itemData(i) == interface_language:
                self.language_combo.setCurrentIndex(i)
                break
        
        # Update current language display
        self._update_current_language_display()
        
        # Window behavior
        self.remember_size_checkbox.setChecked(
            settings.get("remember_window_size", True)
        )
        self.remember_position_checkbox.setChecked(
            settings.get("remember_window_position", True)
        )
        
        # Appearance
        zoom_level = settings.get("zoom_level", 1.0)
        self.zoom_slider.setValue(int(zoom_level * 100))
        self.zoom_spinbox.setValue(zoom_level)
        
        self.smooth_zoom_checkbox.setChecked(
            settings.get("zoom_smooth_transitions", True)
        )
        self.show_advanced_checkbox.setChecked(
            settings.get("show_advanced_options", False)
        )
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from the tab."""
        return {
            "interface_language": self.language_combo.currentData(),
            "remember_window_size": self.remember_size_checkbox.isChecked(),
            "remember_window_position": self.remember_position_checkbox.isChecked(),
            "zoom_level": self.zoom_spinbox.value(),
            "zoom_smooth_transitions": self.smooth_zoom_checkbox.isChecked(),
            "show_advanced_options": self.show_advanced_checkbox.isChecked(),
        }
    
    def validate_settings(self) -> ValidationResult:
        """Validate current settings."""
        errors = []
        warnings = []
        
        # Validate language selection
        language_code = self.language_combo.currentData()
        interface_languages = SettingsSchema.get_interface_languages()
        if language_code not in interface_languages:
            errors.append(f"Invalid interface language: {language_code}")
        
        # Validate zoom level
        zoom_level = self.zoom_spinbox.value()
        if zoom_level < 0.5 or zoom_level > 2.0:
            errors.append("Zoom level must be between 0.5 and 2.0")
        elif zoom_level < 0.8:
            warnings.append("Very small zoom levels may make the interface hard to use")
        elif zoom_level > 1.5:
            warnings.append("Large zoom levels may cause UI elements to be clipped")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def _update_current_language_display(self):
        """Update the current language display label."""
        # This would ideally get the actual current language from the translation manager
        # For now, we'll use the setting
        ui_settings = self.config_manager.get_settings("ui")
        current_language = ui_settings.get("interface_language", "system")
        
        interface_languages = SettingsSchema.get_interface_languages()
        language_name = interface_languages.get(current_language, "Unknown")
        
        self.current_language_label.setText(language_name)
    
    def set_translation_manager(self, translation_manager):
        """Set reference to translation manager for current language display."""
        self.translation_manager = translation_manager
        
        # Update current language display with actual current language
        current_lang = translation_manager.get_current_language()
        current_name = translation_manager.get_current_language_name()
        self.current_language_label.setText(current_name)