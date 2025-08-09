"""
Settings dialog for SubtitleToolkit.

Provides a comprehensive interface for configuring all application settings
including tools, translators, languages, and advanced options.
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton,
    QDialogButtonBox, QMessageBox, QLabel, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from app.config import ConfigManager, ValidationResult
from app.widgets.settings_tabs import (
    ToolsTab, TranslatorsTab, LanguagesTab, AdvancedTab, InterfaceTab
)


class SettingsDialog(QDialog):
    """
    Main settings dialog with tabbed interface.
    
    Provides access to all application settings organized in logical tabs:
    - Tools: ffmpeg/mkvextract detection and configuration
    - Translators: API keys and model selection for translation providers
    - Languages: Default language settings and preferences
    - Advanced: System settings, logging, and behavior options
    """
    
    settings_applied = Signal()  # Emitted when settings are successfully applied
    language_change_requested = Signal(str)  # Emitted when interface language should change
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self._original_settings = {}  # Backup for cancellation
        self._tabs = {}
        
        self._init_ui()
        self._connect_signals()
        self._load_current_settings()
        
    def _init_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("Settings - SubtitleToolkit")
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        self.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Header
        header = self._create_header()
        layout.addWidget(header)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.North)
        
        # Create tabs
        self._create_tabs()
        layout.addWidget(self.tab_widget)
        
        # Button box
        button_box = self._create_button_box()
        layout.addWidget(button_box)
        
    def _create_header(self) -> QFrame:
        """Create the dialog header."""
        header = QFrame()
        header.setFrameStyle(QFrame.StyledPanel)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(15, 15, 15, 15)
        
        # Title
        title = QLabel("Application Settings")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        # Description
        description = QLabel(
            "Configure SubtitleToolkit to work with your system and preferences. "
            "Changes are applied immediately and saved automatically."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #666;")
        header_layout.addWidget(description)
        
        return header
    
    def _create_tabs(self):
        """Create all settings tabs."""
        # Interface tab - UI language and appearance
        self._tabs['interface'] = InterfaceTab(self.config_manager, self)
        self.tab_widget.addTab(self._tabs['interface'], "Interface")
        
        # Tools tab - dependency detection and tool paths
        self._tabs['tools'] = ToolsTab(self.config_manager, self)
        self.tab_widget.addTab(self._tabs['tools'], "Tools")
        
        # Translators tab - API keys and model settings
        self._tabs['translators'] = TranslatorsTab(self.config_manager, self)
        self.tab_widget.addTab(self._tabs['translators'], "Translators")
        
        # Languages tab - default language settings
        self._tabs['languages'] = LanguagesTab(self.config_manager, self)
        self.tab_widget.addTab(self._tabs['languages'], "Languages")
        
        # Advanced tab - system and behavior settings
        self._tabs['advanced'] = AdvancedTab(self.config_manager, self)
        self.tab_widget.addTab(self._tabs['advanced'], "Advanced")
    
    def _create_button_box(self) -> QDialogButtonBox:
        """Create the dialog button box."""
        button_box = QDialogButtonBox()
        
        # Standard buttons
        button_box.setStandardButtons(
            QDialogButtonBox.Ok |
            QDialogButtonBox.Cancel |
            QDialogButtonBox.Apply |
            QDialogButtonBox.RestoreDefaults
        )
        
        # Custom button styling and behavior
        ok_button = button_box.button(QDialogButtonBox.Ok)
        ok_button.setDefault(True)
        
        apply_button = button_box.button(QDialogButtonBox.Apply)
        apply_button.setText("&Apply")
        
        defaults_button = button_box.button(QDialogButtonBox.RestoreDefaults)
        defaults_button.setText("Reset to &Defaults")
        
        # Connect button signals
        button_box.accepted.connect(self._on_ok_clicked)
        button_box.rejected.connect(self._on_cancel_clicked)
        apply_button.clicked.connect(self._on_apply_clicked)
        defaults_button.clicked.connect(self._on_reset_defaults_clicked)
        
        return button_box
    
    def _connect_signals(self):
        """Connect internal signals."""
        # Tab change validation
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        
        # Settings change tracking
        for tab in self._tabs.values():
            if hasattr(tab, 'settings_changed'):
                tab.settings_changed.connect(self._on_tab_settings_changed)
        
        # Connect interface tab language change signal
        if 'interface' in self._tabs:
            interface_tab = self._tabs['interface']
            if hasattr(interface_tab, 'language_change_requested'):
                interface_tab.language_change_requested.connect(self.language_change_requested)
    
    def _load_current_settings(self):
        """Load current settings into all tabs."""
        # Backup current settings for cancellation
        self._original_settings = self.config_manager.get_settings().copy()
        
        # Load settings into each tab
        for section, tab in self._tabs.items():
            tab.load_settings(self.config_manager.get_settings(section))
    
    def _on_tab_changed(self, index: int):
        """Handle tab change."""
        # Validate current tab before switching
        current_tab_name = list(self._tabs.keys())[index] if index >= 0 else None
        if current_tab_name and hasattr(self._tabs[current_tab_name], 'validate_settings'):
            validation = self._tabs[current_tab_name].validate_settings()
            if not validation.is_valid:
                # Show validation errors but don't prevent tab switch
                if validation.errors:
                    QMessageBox.warning(
                        self, "Validation Warning",
                        f"Current tab has validation issues:\n\n{validation.error_message}"
                    )
    
    def _on_tab_settings_changed(self, section: str):
        """Handle settings changes in tabs."""
        # This could be used for real-time validation or preview
        pass
    
    def _validate_all_settings(self) -> ValidationResult:
        """Validate settings from all tabs."""
        all_errors = []
        all_warnings = []
        
        for section, tab in self._tabs.items():
            if hasattr(tab, 'validate_settings'):
                validation = tab.validate_settings()
                if validation.errors:
                    all_errors.extend([f"{section}: {error}" for error in validation.errors])
                if validation.warnings:
                    all_warnings.extend([f"{section}: {warning}" for warning in validation.warnings])
        
        return ValidationResult(
            is_valid=len(all_errors) == 0,
            errors=all_errors,
            warnings=all_warnings
        )
    
    def _apply_all_settings(self) -> bool:
        """Apply settings from all tabs to the config manager."""
        try:
            # Collect settings from all tabs
            for section, tab in self._tabs.items():
                if hasattr(tab, 'get_settings'):
                    settings = tab.get_settings()
                    validation = self.config_manager.update_settings(section, settings, save=False)
                    
                    if not validation.is_valid and validation.errors:
                        # Show specific validation error
                        QMessageBox.critical(
                            self, "Settings Error",
                            f"Error in {section} settings:\n\n{validation.error_message}"
                        )
                        return False
            
            # Save all settings if validation passed
            self.config_manager._save_settings()
            return True
            
        except Exception as e:
            QMessageBox.critical(
                self, "Settings Error",
                f"Failed to apply settings:\n\n{str(e)}"
            )
            return False
    
    def _on_ok_clicked(self):
        """Handle OK button click."""
        if self._apply_all_settings():
            self.settings_applied.emit()
            self.accept()
    
    def _on_apply_clicked(self):
        """Handle Apply button click."""
        if self._apply_all_settings():
            self.settings_applied.emit()
            # Update original settings backup
            self._original_settings = self.config_manager.get_settings().copy()
            
            # Show confirmation
            QMessageBox.information(
                self, "Settings Applied",
                "Settings have been applied successfully."
            )
    
    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        # Check if settings have changed
        current_settings = {}
        for section, tab in self._tabs.items():
            if hasattr(tab, 'get_settings'):
                current_settings[section] = tab.get_settings()
        
        # Simple change detection - could be more sophisticated
        has_changes = False
        for section, settings in current_settings.items():
            if section in self._original_settings:
                if settings != self._original_settings[section]:
                    has_changes = True
                    break
        
        if has_changes:
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Are you sure you want to cancel?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
        
        self.reject()
    
    def _on_reset_defaults_clicked(self):
        """Handle Reset to Defaults button click."""
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "This will reset all settings to their default values. "
            "This action cannot be undone.\n\n"
            "Are you sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Reset config manager to defaults
            self.config_manager.reset_to_defaults()
            
            # Reload settings in all tabs
            self._load_current_settings()
            
            # Show confirmation
            QMessageBox.information(
                self, "Settings Reset",
                "All settings have been reset to their default values."
            )
    
    def show_tab(self, tab_name: str):
        """Show a specific tab by name."""
        tab_names = list(self._tabs.keys())
        if tab_name in tab_names:
            index = tab_names.index(tab_name)
            self.tab_widget.setCurrentIndex(index)
    
    def refresh_tool_detection(self):
        """Refresh tool detection in the Tools tab."""
        if 'tools' in self._tabs:
            self._tabs['tools'].refresh_detection()
    
    def closeEvent(self, event):
        """Handle dialog close event."""
        self._on_cancel_clicked()
        if not self.result():  # If dialog wasn't accepted
            event.ignore()
        else:
            event.accept()