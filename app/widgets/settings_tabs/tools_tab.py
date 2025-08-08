"""
Tools tab for settings dialog.

Provides interface for configuring tool paths, dependency detection,
and system tool management.
"""

from typing import Dict
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QPalette

from ...config import ConfigManager, ValidationResult
from ...utils import ToolStatus, ToolInfo


class StatusIndicator(QLabel):
    """Visual status indicator for tool detection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(16, 16)
        self.setAlignment(Qt.AlignCenter)
        self._set_status(ToolStatus.NOT_FOUND)
    
    def set_status(self, status: ToolStatus, version: str = ""):
        """Update the status indicator."""
        self._set_status(status)
        if version:
            self.setToolTip(f"Version: {version}")
        else:
            self.setToolTip(self._get_status_text(status))
    
    def _set_status(self, status: ToolStatus):
        """Set the visual status."""
        if status == ToolStatus.FOUND:
            self.setStyleSheet("""
                QLabel {
                    background-color: #4CAF50;
                    border-radius: 8px;
                    border: 1px solid #45a049;
                }
            """)
            self.setText("✓")
        elif status == ToolStatus.NOT_FOUND:
            self.setStyleSheet("""
                QLabel {
                    background-color: #f44336;
                    border-radius: 8px;
                    border: 1px solid #da190b;
                }
            """)
            self.setText("✗")
        elif status == ToolStatus.ERROR:
            self.setStyleSheet("""
                QLabel {
                    background-color: #ff9800;
                    border-radius: 8px;
                    border: 1px solid #f57c00;
                }
            """)
            self.setText("!")
        elif status == ToolStatus.TESTING:
            self.setStyleSheet("""
                QLabel {
                    background-color: #2196F3;
                    border-radius: 8px;
                    border: 1px solid #1976D2;
                }
            """)
            self.setText("⟳")
        elif status == ToolStatus.VERSION_MISMATCH:
            self.setStyleSheet("""
                QLabel {
                    background-color: #ff9800;
                    border-radius: 8px;
                    border: 1px solid #f57c00;
                }
            """)
            self.setText("⚠")
        else:  # INVALID
            self.setStyleSheet("""
                QLabel {
                    background-color: #9e9e9e;
                    border-radius: 8px;
                    border: 1px solid #757575;
                }
            """)
            self.setText("?")
    
    def _get_status_text(self, status: ToolStatus) -> str:
        """Get status description text."""
        status_texts = {
            ToolStatus.FOUND: "Tool found and working",
            ToolStatus.NOT_FOUND: "Tool not found",
            ToolStatus.ERROR: "Error detecting tool",
            ToolStatus.INVALID: "Tool found but invalid",
            ToolStatus.TESTING: "Currently testing tool...",
            ToolStatus.VERSION_MISMATCH: "Tool found but version too old"
        }
        return status_texts.get(status, "Unknown status")


class ToolsTab(QWidget):
    """
    Tools configuration tab.
    
    Provides interface for:
    - Automatic tool detection with visual status
    - Manual path configuration with file browsers
    - Tool validation and testing
    - Installation guidance for missing tools
    """
    
    settings_changed = Signal(str)  # section name
    
    def __init__(self, config_manager: ConfigManager, parent=None):
        super().__init__(parent)
        
        self.config_manager = config_manager
        self._tool_info = {}  # Cache for tool detection results
        self._path_inputs = {}  # Path input widgets
        self._status_indicators = {}  # Status indicator widgets
        self._test_buttons = {}  # Test button widgets
        
        self._init_ui()
        self._connect_signals()
        
        # Connect to config manager signals for real-time updates
        self.config_manager.tool_detected.connect(self._on_tool_detected)
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Auto-detection settings
        auto_detect_group = self._create_auto_detect_group()
        layout.addWidget(auto_detect_group)
        
        # Tool configuration
        tools_group = self._create_tools_group()
        layout.addWidget(tools_group)
        
        # Installation guide
        guide_group = self._create_guide_group()
        layout.addWidget(guide_group)
        
        layout.addStretch()
    
    def _create_auto_detect_group(self) -> QGroupBox:
        """Create auto-detection settings group."""
        group = QGroupBox("Tool Detection")
        layout = QVBoxLayout(group)
        
        # Auto-detect checkbox
        self.auto_detect_check = QCheckBox("Automatically detect tools in system PATH")
        self.auto_detect_check.setChecked(True)
        layout.addWidget(self.auto_detect_check)
        
        # Detection controls
        detect_layout = QHBoxLayout()
        
        self.detect_button = QPushButton("Detect Tools")
        self.detect_button.clicked.connect(self._detect_all_tools)
        detect_layout.addWidget(self.detect_button)
        
        self.detection_progress = QProgressBar()
        self.detection_progress.setVisible(False)
        detect_layout.addWidget(self.detection_progress)
        
        detect_layout.addStretch()
        layout.addLayout(detect_layout)
        
        return group
    
    def _create_tools_group(self) -> QGroupBox:
        """Create tools configuration group."""
        group = QGroupBox("Tool Paths")
        grid = QGridLayout(group)
        grid.setSpacing(10)
        
        # Tool configurations
        tools = [
            ("ffmpeg", "FFmpeg", "Required for MKV subtitle extraction"),
            ("ffprobe", "FFprobe", "Required for MKV file analysis (included with FFmpeg)"),
            ("mkvextract", "MKVextract", "Alternative tool for MKV subtitle extraction (optional)")
        ]
        
        # Headers
        grid.addWidget(QLabel("Tool"), 0, 0)
        grid.addWidget(QLabel("Status"), 0, 1)
        grid.addWidget(QLabel("Path"), 0, 2)
        grid.addWidget(QLabel("Actions"), 0, 3)
        
        # Add separator
        separator = QFrame()
        separator.setFrameStyle(QFrame.HLine | QFrame.Sunken)
        grid.addWidget(separator, 1, 0, 1, 4)
        
        for i, (tool_key, tool_name, description) in enumerate(tools):
            row = i + 2
            
            # Tool name and description
            name_widget = QWidget()
            name_layout = QVBoxLayout(name_widget)
            name_layout.setContentsMargins(0, 0, 0, 0)
            name_layout.setSpacing(2)
            
            name_label = QLabel(tool_name)
            name_font = QFont()
            name_font.setBold(True)
            name_label.setFont(name_font)
            name_layout.addWidget(name_label)
            
            desc_label = QLabel(description)
            desc_label.setStyleSheet("color: #666; font-size: 10px;")
            desc_label.setWordWrap(True)
            name_layout.addWidget(desc_label)
            
            grid.addWidget(name_widget, row, 0)
            
            # Status indicator
            status_indicator = StatusIndicator()
            self._status_indicators[tool_key] = status_indicator
            grid.addWidget(status_indicator, row, 1, Qt.AlignCenter)
            
            # Path input
            path_layout = QHBoxLayout()
            path_input = QLineEdit()
            path_input.setPlaceholderText(f"Auto-detected or manual path to {tool_key}")
            self._path_inputs[tool_key] = path_input
            path_layout.addWidget(path_input)
            
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(lambda checked, tool=tool_key: self._browse_tool_path(tool))
            path_layout.addWidget(browse_button)
            
            path_widget = QWidget()
            path_widget.setLayout(path_layout)
            grid.addWidget(path_widget, row, 2)
            
            # Action buttons
            action_layout = QHBoxLayout()
            
            test_button = QPushButton("Test")
            test_button.clicked.connect(lambda checked, tool=tool_key: self._test_tool(tool))
            self._test_buttons[tool_key] = test_button
            action_layout.addWidget(test_button)
            
            action_widget = QWidget()
            action_widget.setLayout(action_layout)
            grid.addWidget(action_widget, row, 3)
        
        # Set column stretches
        grid.setColumnStretch(0, 1)  # Tool name column
        grid.setColumnStretch(2, 2)  # Path column (wider)
        
        return group
    
    def _create_guide_group(self) -> QGroupBox:
        """Create installation guide group."""
        group = QGroupBox("Installation Guide")
        layout = QVBoxLayout(group)
        
        # Guide text
        self.guide_text = QTextEdit()
        self.guide_text.setReadOnly(True)
        self.guide_text.setMaximumHeight(150)
        self.guide_text.setPlainText(
            "Select a tool above to see installation instructions for your platform."
        )
        layout.addWidget(self.guide_text)
        
        return group
    
    def _connect_signals(self):
        """Connect widget signals."""
        # Auto-detect checkbox
        self.auto_detect_check.toggled.connect(self._on_auto_detect_changed)
        
        # Path input changes
        for tool, input_widget in self._path_inputs.items():
            input_widget.textChanged.connect(
                lambda text, t=tool: self._on_path_changed(t, text)
            )
            # Show installation guide when input is focused
            input_widget.focusInEvent = lambda event, t=tool: (
                self._show_installation_guide(t),
                QLineEdit.focusInEvent(input_widget, event)
            )
    
    def _detect_all_tools(self):
        """Detect all tools using enhanced background detection."""
        # Show progress
        self.detection_progress.setVisible(True)
        self.detection_progress.setRange(0, 100)
        self.detection_progress.setValue(0)
        self.detect_button.setEnabled(False)
        
        # Connect progress signals
        self.config_manager.detection_progress.connect(self._on_detection_progress)
        self.config_manager.detection_complete.connect(self._on_detection_complete)
        
        # Start background detection
        self.config_manager.detect_all_tools_background(force_refresh=True)
    
    def _on_tool_detected(self, tool_name: str, tool_info: ToolInfo):
        """Handle individual tool detection completion."""
        self._tool_info[tool_name] = tool_info
        
        # Update status indicator
        if tool_name in self._status_indicators:
            self._status_indicators[tool_name].set_status(tool_info.status, tool_info.version)
        
        # Update path input if auto-detection found the tool
        if tool_info.status == ToolStatus.FOUND and tool_name in self._path_inputs:
            current_path = self._path_inputs[tool_name].text()
            if not current_path:  # Only update if empty
                self._path_inputs[tool_name].setText(tool_info.path)
    
    def _on_detection_progress(self, tool_name: str, percentage: int):
        """Handle detection progress updates."""
        if tool_name == "complete":
            self.detection_progress.setValue(100)
        else:
            self.detection_progress.setValue(percentage)
            # Show which tool is being tested
            if percentage < 100:
                self.detect_button.setText(f"Testing {tool_name}...")
    
    def _on_detection_complete(self, results: Dict[str, ToolInfo]):
        """Handle detection completion."""
        # Update tool info cache
        self._tool_info.update(results)
        
        # Hide progress and re-enable button
        self.detection_progress.setVisible(False)
        self.detect_button.setEnabled(True)
        self.detect_button.setText("Detect Tools")
        
        # Disconnect signals to prevent duplicate connections
        self.config_manager.detection_progress.disconnect(self._on_detection_progress)
        self.config_manager.detection_complete.disconnect(self._on_detection_complete)
        
        # Update installation guide with missing or problematic tools
        problematic_tools = [
            tool for tool, info in results.items()
            if info.status not in [ToolStatus.FOUND]
        ]
        
        if problematic_tools:
            guide_text = "Tool status summary:\n\n"
            for tool in problematic_tools:
                info = results[tool]
                guide_text += f"{tool.upper()}: {info.status_description}\n"
                if info.error_message:
                    guide_text += f"  Error: {info.error_message}\n"
                guide_text += f"  Installation: {self.config_manager.get_installation_guide(tool)}\n\n"
            self.guide_text.setPlainText(guide_text)
        else:
            # Show success summary with versions
            guide_text = "✅ All tools detected successfully!\n\n"
            for tool, info in results.items():
                if info.status == ToolStatus.FOUND:
                    guide_text += f"{tool.upper()}: {info.version}"
                    if info.installation_method:
                        guide_text += f" (via {info.installation_method})"
                    guide_text += "\n"
            self.guide_text.setPlainText(guide_text)
    
    def _browse_tool_path(self, tool_name: str):
        """Browse for tool executable path."""
        file_dialog = QFileDialog(self)
        file_dialog.setFileMode(QFileDialog.ExistingFile)
        file_dialog.setNameFilter("Executable files (*)")
        
        if file_dialog.exec():
            selected_files = file_dialog.selectedFiles()
            if selected_files:
                path = selected_files[0]
                self._path_inputs[tool_name].setText(path)
                # Test the selected path
                self._test_tool(tool_name)
    
    def _test_tool(self, tool_name: str):
        """Test a specific tool path."""
        path = self._path_inputs[tool_name].text().strip()
        if not path:
            QMessageBox.warning(
                self, "No Path",
                f"Please specify a path for {tool_name} first."
            )
            return
        
        # Show testing status immediately
        self._status_indicators[tool_name].set_status(ToolStatus.TESTING)
        
        # Disable test button during testing
        self._test_buttons[tool_name].setEnabled(False)
        self._test_buttons[tool_name].setText("Testing...")
        
        # Validate the path using enhanced checker
        tool_info = self.config_manager.validate_tool_path(path, tool_name)
        self._tool_info[tool_name] = tool_info
        
        # Update status indicator
        self._status_indicators[tool_name].set_status(tool_info.status, tool_info.version)
        
        # Re-enable button
        self._test_buttons[tool_name].setEnabled(True)
        self._test_buttons[tool_name].setText("Test")
        
        # Show detailed result message
        if tool_info.status == ToolStatus.FOUND:
            message = f"{tool_name} is working correctly!\n\n"
            message += f"Version: {tool_info.version}\n"
            message += f"Path: {tool_info.path}\n"
            if tool_info.installation_method:
                message += f"Installation: {tool_info.installation_method}\n"
            if tool_info.minimum_version:
                message += f"Minimum required: {tool_info.minimum_version}\n"
                message += f"Requirements met: {'✓' if tool_info.meets_requirements else '✗'}"
            
            QMessageBox.information(self, "Tool Valid", message)
        elif tool_info.status == ToolStatus.VERSION_MISMATCH:
            message = f"{tool_name} was found but doesn't meet version requirements.\n\n"
            message += f"Found version: {tool_info.version}\n"
            message += f"Required version: {tool_info.minimum_version}\n\n"
            message += "Please update to a newer version."
            
            QMessageBox.warning(self, "Version Too Old", message)
        else:
            message = f"{tool_name} test failed:\n\n{tool_info.error_message}"
            if tool_info.path:
                message += f"\n\nPath tested: {tool_info.path}"
            
            QMessageBox.warning(self, "Tool Invalid", message)
    
    def _on_auto_detect_changed(self, checked: bool):
        """Handle auto-detect setting change."""
        # Enable/disable manual path inputs based on auto-detect
        for input_widget in self._path_inputs.values():
            input_widget.setEnabled(not checked or input_widget.text().strip() != "")
        
        if checked:
            # Re-run detection
            self._detect_all_tools()
    
    def _on_path_changed(self, tool_name: str, path: str):
        """Handle manual path change."""
        # Clear status if path is changed
        if tool_name in self._status_indicators:
            self._status_indicators[tool_name].set_status(ToolStatus.NOT_FOUND)
        
        # Update tool info
        if path.strip():
            self._tool_info[tool_name] = ToolInfo(status=ToolStatus.NOT_FOUND, path=path)
        
        self.settings_changed.emit("tools")
    
    def _show_installation_guide(self, tool_name: str):
        """Show installation guide for a specific tool."""
        guide = self.config_manager.get_installation_guide(tool_name)
        self.guide_text.setPlainText(f"Installation guide for {tool_name.upper()}:\n\n{guide}")
    
    def load_settings(self, settings: dict):
        """Load settings into the tab."""
        # Auto-detect setting
        self.auto_detect_check.setChecked(settings.get("auto_detect_tools", True))
        
        # Tool paths
        for tool in ["ffmpeg", "ffprobe", "mkvextract"]:
            path_key = f"{tool}_path"
            if path_key in settings and tool in self._path_inputs:
                self._path_inputs[tool].setText(settings[path_key])
        
        # Run initial detection if auto-detect is enabled
        if self.auto_detect_check.isChecked():
            self._detect_all_tools()
    
    def get_settings(self) -> dict:
        """Get current settings from the tab."""
        settings = {
            "auto_detect_tools": self.auto_detect_check.isChecked(),
        }
        
        # Tool paths
        for tool in ["ffmpeg", "ffprobe", "mkvextract"]:
            path_key = f"{tool}_path"
            if tool in self._path_inputs:
                settings[path_key] = self._path_inputs[tool].text().strip()
        
        return settings
    
    def validate_settings(self) -> ValidationResult:
        """Validate current settings."""
        errors = []
        warnings = []
        
        # Check for required tools if not auto-detecting
        if not self.auto_detect_check.isChecked():
            for tool in ["ffmpeg", "ffprobe"]:  # mkvextract is optional
                path = self._path_inputs[tool].text().strip()
                if not path:
                    errors.append(f"{tool} path is required when auto-detection is disabled")
                elif tool in self._tool_info:
                    tool_info = self._tool_info[tool]
                    if tool_info.status != ToolStatus.FOUND:
                        warnings.append(f"{tool} may not be working correctly: {tool_info.error_message}")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def refresh_detection(self):
        """Refresh tool detection."""
        self._detect_all_tools()