"""
Tools tab for settings dialog.

Provides interface for configuring tool paths, dependency detection,
and system tool management.
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QCheckBox, QTextEdit,
    QFileDialog, QMessageBox, QProgressBar, QFrame
)
from PySide6.QtCore import Qt, Signal, QThread, QObject
from PySide6.QtGui import QFont, QPalette

from ...config import ConfigManager, ToolStatus, ToolInfo, ValidationResult, DependencyChecker


class ToolDetectionWorker(QObject):
    """Worker for background tool detection."""
    
    detection_complete = Signal(str, ToolInfo)  # tool_name, tool_info
    all_complete = Signal()
    
    def __init__(self, tools: list):
        super().__init__()
        self.tools = tools
    
    def run(self):
        """Run tool detection for all tools."""
        for tool in self.tools:
            if tool == "ffmpeg":
                info = DependencyChecker.detect_ffmpeg()
            elif tool == "ffprobe":
                info = DependencyChecker.detect_ffprobe()
            elif tool == "mkvextract":
                info = DependencyChecker.detect_mkvextract()
            else:
                info = ToolInfo(status=ToolStatus.NOT_FOUND)
            
            self.detection_complete.emit(tool, info)
        
        self.all_complete.emit()


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
            ToolStatus.INVALID: "Tool found but invalid"
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
        """Detect all tools in background."""
        # Show progress
        self.detection_progress.setVisible(True)
        self.detection_progress.setRange(0, 0)  # Indeterminate
        self.detect_button.setEnabled(False)
        
        # Create worker thread
        self._detection_thread = QThread()
        self._detection_worker = ToolDetectionWorker(["ffmpeg", "ffprobe", "mkvextract"])
        self._detection_worker.moveToThread(self._detection_thread)
        
        # Connect signals
        self._detection_thread.started.connect(self._detection_worker.run)
        self._detection_worker.detection_complete.connect(self._on_tool_detected)
        self._detection_worker.all_complete.connect(self._on_detection_complete)
        
        # Start detection
        self._detection_thread.start()
    
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
    
    def _on_detection_complete(self):
        """Handle detection completion."""
        # Hide progress and re-enable button
        self.detection_progress.setVisible(False)
        self.detect_button.setEnabled(True)
        
        # Clean up thread
        self._detection_thread.quit()
        self._detection_thread.wait()
        
        # Update installation guide with missing tools
        missing_tools = [
            tool for tool, info in self._tool_info.items()
            if info.status != ToolStatus.FOUND
        ]
        
        if missing_tools:
            guide_text = "Missing tools detected:\n\n"
            for tool in missing_tools:
                guide_text += f"{tool.upper()}:\n"
                guide_text += DependencyChecker.get_installation_guide(tool) + "\n\n"
            self.guide_text.setPlainText(guide_text)
        else:
            self.guide_text.setPlainText("All tools detected successfully!")
    
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
        
        # Disable test button during testing
        self._test_buttons[tool_name].setEnabled(False)
        self._test_buttons[tool_name].setText("Testing...")
        
        # Validate the path
        tool_info = DependencyChecker.validate_tool_path(path, tool_name)
        self._tool_info[tool_name] = tool_info
        
        # Update status indicator
        self._status_indicators[tool_name].set_status(tool_info.status, tool_info.version)
        
        # Re-enable button
        self._test_buttons[tool_name].setEnabled(True)
        self._test_buttons[tool_name].setText("Test")
        
        # Show result message
        if tool_info.status == ToolStatus.FOUND:
            QMessageBox.information(
                self, "Tool Valid",
                f"{tool_name} is working correctly.\n\nVersion: {tool_info.version}"
            )
        else:
            QMessageBox.warning(
                self, "Tool Invalid",
                f"{tool_name} test failed:\n\n{tool_info.error_message}"
            )
    
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
        guide = DependencyChecker.get_installation_guide(tool_name)
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