"""
Advanced tab for settings dialog.

Provides interface for configuring system settings, performance options,
logging levels, and application behavior settings.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QSpinBox, QComboBox, QCheckBox, QLineEdit, QPushButton,
    QFileDialog, QFormLayout, QFrame, QTextEdit, QSlider, QProgressBar,
    QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer, QStandardPaths
from PySide6.QtGui import QFont

from ...config import ConfigManager, ValidationResult, LogLevel


class SystemInfoWidget(QWidget):
    """Widget displaying system information and statistics."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._update_info()
        
        # Update timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_info)
        self.update_timer.start(5000)  # Update every 5 seconds
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QFormLayout(self)
        
        # System info labels
        self.cpu_count_label = QLabel()
        layout.addRow("CPU Cores:", self.cpu_count_label)
        
        self.memory_label = QLabel()
        layout.addRow("Available Memory:", self.memory_label)
        
        self.temp_dir_label = QLabel()
        layout.addRow("Temp Directory:", self.temp_dir_label)
        
        self.config_dir_label = QLabel()
        layout.addRow("Config Directory:", self.config_dir_label)
    
    def _update_info(self):
        """Update system information display."""
        try:
            import psutil
            
            # CPU cores
            self.cpu_count_label.setText(str(psutil.cpu_count()))
            
            # Memory
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            total_gb = memory.total / (1024**3)
            self.memory_label.setText(f"{available_gb:.1f} GB / {total_gb:.1f} GB")
            
        except ImportError:
            # Fallback without psutil
            import multiprocessing
            self.cpu_count_label.setText(str(multiprocessing.cpu_count()))
            self.memory_label.setText("Unknown (install psutil for details)")
        
        # Directories
        self.temp_dir_label.setText(tempfile.gettempdir())
        
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        self.config_dir_label.setText(config_dir or "~/.subtitletoolkit")


class PerformanceWidget(QWidget):
    """Widget for performance-related settings."""
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        # Max concurrent workers
        worker_layout = QHBoxLayout()
        
        self.max_workers_spin = QSpinBox()
        self.max_workers_spin.setRange(1, 32)
        self.max_workers_spin.setValue(4)
        self.max_workers_spin.setToolTip("Maximum number of concurrent translation workers")
        worker_layout.addWidget(self.max_workers_spin)
        
        # Auto-detect button
        self.auto_detect_button = QPushButton("Auto")
        self.auto_detect_button.clicked.connect(self._auto_detect_workers)
        self.auto_detect_button.setMaximumWidth(50)
        worker_layout.addWidget(self.auto_detect_button)
        
        worker_layout.addStretch()
        worker_widget = QWidget()
        worker_widget.setLayout(worker_layout)
        layout.addRow("Max Concurrent Workers:", worker_widget)
        
        # Help text for workers
        worker_help = QLabel("Higher values may improve performance but use more system resources. Recommended: 2-4 for most systems.")
        worker_help.setStyleSheet("color: #666; font-size: 10px;")
        worker_help.setWordWrap(True)
        layout.addRow("", worker_help)
        
        # Progress update interval
        self.progress_interval_spin = QSpinBox()
        self.progress_interval_spin.setRange(50, 5000)
        self.progress_interval_spin.setValue(100)
        self.progress_interval_spin.setSuffix(" ms")
        self.progress_interval_spin.setToolTip("How often to update progress indicators")
        layout.addRow("Progress Update Interval:", self.progress_interval_spin)
        
        interval_help = QLabel("Lower values provide smoother progress updates but may impact performance.")
        interval_help.setStyleSheet("color: #666; font-size: 10px;")
        interval_help.setWordWrap(True)
        layout.addRow("", interval_help)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.max_workers_spin.valueChanged.connect(self.settings_changed.emit)
        self.progress_interval_spin.valueChanged.connect(self.settings_changed.emit)
    
    def _auto_detect_workers(self):
        """Auto-detect optimal number of workers."""
        try:
            import multiprocessing
            cpu_count = multiprocessing.cpu_count()
            # Use CPU count but cap at reasonable limits
            optimal = min(max(cpu_count // 2, 1), 8)
            self.max_workers_spin.setValue(optimal)
            
            QMessageBox.information(
                self, "Auto-Detection",
                f"Set workers to {optimal} based on {cpu_count} CPU cores."
            )
        except Exception as e:
            QMessageBox.warning(
                self, "Auto-Detection Failed",
                f"Could not detect CPU count: {str(e)}"
            )
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the widget."""
        self.max_workers_spin.setValue(settings.get("max_concurrent_workers", 4))
        self.progress_interval_spin.setValue(settings.get("progress_update_interval", 100))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from the widget."""
        return {
            "max_concurrent_workers": self.max_workers_spin.value(),
            "progress_update_interval": self.progress_interval_spin.value(),
        }


class LoggingWidget(QWidget):
    """Widget for logging configuration."""
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        # Log level
        self.log_level_combo = QComboBox()
        log_levels = [
            (LogLevel.DEBUG.value, "Debug", "Show all messages including detailed debugging information"),
            (LogLevel.INFO.value, "Info", "Show informational messages and above"),
            (LogLevel.WARNING.value, "Warning", "Show only warnings and errors"),
            (LogLevel.ERROR.value, "Error", "Show only error messages"),
        ]
        
        for value, display, tooltip in log_levels:
            self.log_level_combo.addItem(display, value)
        
        self.log_level_combo.setCurrentText("Info")
        layout.addRow("Log Level:", self.log_level_combo)
        
        # Log level description
        self.log_level_desc = QLabel()
        self.log_level_desc.setStyleSheet("color: #666; font-size: 10px;")
        self.log_level_desc.setWordWrap(True)
        layout.addRow("", self.log_level_desc)
        
        # Update description when selection changes
        self.log_level_combo.currentIndexChanged.connect(self._update_log_level_description)
        self._update_log_level_description()
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.log_level_combo.currentDataChanged.connect(self.settings_changed.emit)
    
    def _update_log_level_description(self):
        """Update log level description."""
        descriptions = {
            LogLevel.DEBUG.value: "Show all messages including detailed debugging information",
            LogLevel.INFO.value: "Show informational messages and above (recommended)",
            LogLevel.WARNING.value: "Show only warnings and errors",
            LogLevel.ERROR.value: "Show only error messages",
        }
        
        current_level = self.log_level_combo.currentData()
        desc = descriptions.get(current_level, "")
        self.log_level_desc.setText(desc)
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the widget."""
        log_level = settings.get("log_level", LogLevel.INFO.value)
        index = self.log_level_combo.findData(log_level)
        if index >= 0:
            self.log_level_combo.setCurrentIndex(index)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from the widget."""
        return {
            "log_level": self.log_level_combo.currentData()
        }


class FileHandlingWidget(QWidget):
    """Widget for file and directory handling settings."""
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QFormLayout(self)
        layout.setSpacing(15)
        
        # Temporary directory
        temp_layout = QHBoxLayout()
        
        self.temp_dir_edit = QLineEdit()
        self.temp_dir_edit.setPlaceholderText("Leave empty to use system default")
        temp_layout.addWidget(self.temp_dir_edit)
        
        self.temp_dir_browse = QPushButton("Browse")
        self.temp_dir_browse.clicked.connect(self._browse_temp_dir)
        temp_layout.addWidget(self.temp_dir_browse)
        
        self.temp_dir_default = QPushButton("Default")
        self.temp_dir_default.clicked.connect(self._use_default_temp_dir)
        temp_layout.addWidget(self.temp_dir_default)
        
        temp_widget = QWidget()
        temp_widget.setLayout(temp_layout)
        layout.addRow("Temporary Directory:", temp_widget)
        
        # Temp directory info
        temp_info = QLabel("Custom directory for temporary files. Leave empty to use system default.")
        temp_info.setStyleSheet("color: #666; font-size: 10px;")
        temp_info.setWordWrap(True)
        layout.addRow("", temp_info)
        
        # Cleanup settings
        self.cleanup_temp_check = QCheckBox("Automatically clean up temporary files on exit")
        self.cleanup_temp_check.setChecked(True)
        layout.addRow("", self.cleanup_temp_check)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.temp_dir_edit.textChanged.connect(self.settings_changed.emit)
        self.cleanup_temp_check.toggled.connect(self.settings_changed.emit)
    
    def _browse_temp_dir(self):
        """Browse for temporary directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Temporary Directory",
            self.temp_dir_edit.text() or tempfile.gettempdir()
        )
        
        if directory:
            self.temp_dir_edit.setText(directory)
    
    def _use_default_temp_dir(self):
        """Use system default temporary directory."""
        self.temp_dir_edit.clear()
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the widget."""
        self.temp_dir_edit.setText(settings.get("temp_dir", ""))
        self.cleanup_temp_check.setChecked(settings.get("cleanup_temp_files", True))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from the widget."""
        return {
            "temp_dir": self.temp_dir_edit.text().strip(),
            "cleanup_temp_files": self.cleanup_temp_check.isChecked(),
        }


class BehaviorWidget(QWidget):
    """Widget for application behavior settings."""
    
    settings_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self._init_ui()
        self._connect_signals()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Auto-save settings
        self.auto_save_check = QCheckBox("Automatically save settings when changed")
        self.auto_save_check.setChecked(True)
        self.auto_save_check.setToolTip("Save settings immediately when modified, without requiring Apply/OK")
        layout.addWidget(self.auto_save_check)
        
        # Check for updates
        self.check_updates_check = QCheckBox("Check for updates on startup")
        self.check_updates_check.setChecked(True)
        self.check_updates_check.setToolTip("Automatically check for application updates when starting")
        layout.addWidget(self.check_updates_check)
        
        # Remember window state
        self.remember_window_check = QCheckBox("Remember window size and position")
        self.remember_window_check.setChecked(True)
        self.remember_window_check.setToolTip("Restore window size and position from previous session")
        layout.addWidget(self.remember_window_check)
        
        # Show advanced options
        self.show_advanced_check = QCheckBox("Show advanced options in main interface")
        self.show_advanced_check.setChecked(False)
        self.show_advanced_check.setToolTip("Display advanced configuration options in the main window")
        layout.addWidget(self.show_advanced_check)
    
    def _connect_signals(self):
        """Connect widget signals."""
        self.auto_save_check.toggled.connect(self.settings_changed.emit)
        self.check_updates_check.toggled.connect(self.settings_changed.emit)
        self.remember_window_check.toggled.connect(self.settings_changed.emit)
        self.show_advanced_check.toggled.connect(self.settings_changed.emit)
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the widget."""
        self.auto_save_check.setChecked(settings.get("auto_save_settings", True))
        self.check_updates_check.setChecked(settings.get("check_updates_on_startup", True))
        
        # UI settings
        ui_settings = settings.get("ui", {})  # This might come from a different section
        self.remember_window_check.setChecked(ui_settings.get("remember_window_size", True))
        self.show_advanced_check.setChecked(ui_settings.get("show_advanced_options", False))
    
    def get_settings(self) -> Dict[str, Any]:
        """Get settings from the widget."""
        return {
            "auto_save_settings": self.auto_save_check.isChecked(),
            "check_updates_on_startup": self.check_updates_check.isChecked(),
            # UI settings would normally go in a separate section
            "_ui_settings": {
                "remember_window_size": self.remember_window_check.isChecked(),
                "show_advanced_options": self.show_advanced_check.isChecked(),
            }
        }


class AdvancedTab(QWidget):
    """
    Advanced configuration tab.
    
    Provides interface for:
    - Performance settings (concurrency, update intervals)
    - Logging configuration
    - File handling and temporary directory settings
    - Application behavior options
    - System information display
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
        
        # Create sections
        sections = [
            ("Performance", self._create_performance_group()),
            ("Logging", self._create_logging_group()),
            ("File Handling", self._create_file_handling_group()),
            ("Application Behavior", self._create_behavior_group()),
            ("System Information", self._create_system_info_group()),
        ]
        
        for title, widget in sections:
            layout.addWidget(widget)
        
        layout.addStretch()
    
    def _create_performance_group(self) -> QGroupBox:
        """Create performance settings group."""
        group = QGroupBox("Performance Settings")
        layout = QVBoxLayout(group)
        
        self.performance_widget = PerformanceWidget()
        layout.addWidget(self.performance_widget)
        
        return group
    
    def _create_logging_group(self) -> QGroupBox:
        """Create logging settings group."""
        group = QGroupBox("Logging Configuration")
        layout = QVBoxLayout(group)
        
        self.logging_widget = LoggingWidget()
        layout.addWidget(self.logging_widget)
        
        return group
    
    def _create_file_handling_group(self) -> QGroupBox:
        """Create file handling settings group."""
        group = QGroupBox("File Handling")
        layout = QVBoxLayout(group)
        
        self.file_handling_widget = FileHandlingWidget()
        layout.addWidget(self.file_handling_widget)
        
        return group
    
    def _create_behavior_group(self) -> QGroupBox:
        """Create application behavior settings group."""
        group = QGroupBox("Application Behavior")
        layout = QVBoxLayout(group)
        
        self.behavior_widget = BehaviorWidget()
        layout.addWidget(self.behavior_widget)
        
        return group
    
    def _create_system_info_group(self) -> QGroupBox:
        """Create system information group."""
        group = QGroupBox("System Information")
        layout = QVBoxLayout(group)
        
        self.system_info_widget = SystemInfoWidget()
        layout.addWidget(self.system_info_widget)
        
        return group
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Connect all sub-widgets to emit settings changed
        widgets = [
            self.performance_widget,
            self.logging_widget,
            self.file_handling_widget,
            self.behavior_widget,
        ]
        
        for widget in widgets:
            if hasattr(widget, 'settings_changed'):
                widget.settings_changed.connect(
                    lambda: self.settings_changed.emit("advanced")
                )
    
    def load_settings(self, settings: Dict[str, Any]):
        """Load settings into the tab."""
        self.performance_widget.load_settings(settings)
        self.logging_widget.load_settings(settings)
        self.file_handling_widget.load_settings(settings)
        self.behavior_widget.load_settings(settings)
    
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from the tab."""
        settings = {}
        
        # Collect settings from all widgets
        settings.update(self.performance_widget.get_settings())
        settings.update(self.logging_widget.get_settings())
        settings.update(self.file_handling_widget.get_settings())
        
        behavior_settings = self.behavior_widget.get_settings()
        ui_settings = behavior_settings.pop("_ui_settings", {})
        settings.update(behavior_settings)
        
        # UI settings would go to a separate section in a full implementation
        # For now, we'll include them in advanced
        if ui_settings:
            settings["ui"] = ui_settings
        
        return settings
    
    def validate_settings(self) -> ValidationResult:
        """Validate current settings."""
        errors = []
        warnings = []
        
        # Validate performance settings
        max_workers = self.performance_widget.max_workers_spin.value()
        if max_workers > 16:
            warnings.append("Very high worker count may impact system performance")
        
        progress_interval = self.performance_widget.progress_interval_spin.value()
        if progress_interval < 100:
            warnings.append("Very fast progress updates may impact performance")
        
        # Validate temp directory
        temp_dir = self.file_handling_widget.temp_dir_edit.text().strip()
        if temp_dir:
            temp_path = Path(temp_dir)
            if not temp_path.exists():
                errors.append(f"Temporary directory does not exist: {temp_dir}")
            elif not temp_path.is_dir():
                errors.append(f"Temporary directory path is not a directory: {temp_dir}")
            elif not os.access(temp_path, os.W_OK):
                errors.append(f"No write permission for temporary directory: {temp_dir}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )