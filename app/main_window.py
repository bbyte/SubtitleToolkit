"""
MainWindow implementation for SubtitleToolkit Desktop Application.

This module contains the main window class that orchestrates all UI components
according to the workflow specifications.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QMenuBar, QStatusBar, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence

from widgets.project_selector import ProjectSelector
from widgets.stage_toggles import StageToggles
from widgets.stage_configurators import StageConfigurators
from widgets.progress_section import ProgressSection
from widgets.log_panel import LogPanel
from widgets.results_panel import ResultsPanel
from widgets.action_buttons import ActionButtons

from dialogs.settings_dialog import SettingsDialog
from config import ConfigManager


class MainWindow(QMainWindow):
    """
    Main application window implementing the complete UI layout specified
    in the workflow documentation.
    
    Layout Structure:
    MainWindow
    ├── ProjectSelector (folder picker)
    ├── StageToggles (checkboxes for Extract/Translate/Sync)
    ├── StageConfigurators (expandable configuration panels)
    │   ├── ExtractConfig (language selection, output directory)
    │   ├── TranslateConfig (source/target lang, engine selection)
    │   └── SyncConfig (naming template, dry-run toggle)
    ├── ProgressSection (progress bar, status text)
    ├── LogPanel (filterable by info/warn/error)
    ├── ResultsPanel (tabular results, rename preview)
    └── ActionButtons (Run/Cancel/Open Output)
    """
    
    # Signals for inter-component communication
    project_changed = Signal(str)  # project directory path
    stages_changed = Signal(dict)  # {stage: bool} mapping
    run_requested = Signal()
    cancel_requested = Signal()
    open_output_requested = Signal()
    
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        
        # Configuration manager
        self.config_manager = ConfigManager(self)
        
        # Window properties
        self.setWindowTitle("SubtitleToolkit")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Initialize UI components
        self._init_components()
        self._create_layout()
        self._create_menu_bar()
        self._create_status_bar()
        self._connect_signals()
        
        # Settings dialog (created on demand)
        self._settings_dialog = None
        
        # Status update timer
        self._status_timer = QTimer()
        self._status_timer.timeout.connect(self._update_status)
        self._status_timer.start(1000)  # Update every second
    
    def _init_components(self) -> None:
        """Initialize all UI components."""
        # Main UI components
        self.project_selector = ProjectSelector()
        self.stage_toggles = StageToggles()
        self.stage_configurators = StageConfigurators()
        self.progress_section = ProgressSection()
        self.log_panel = LogPanel()
        self.results_panel = ResultsPanel()
        self.action_buttons = ActionButtons()
    
    def _create_layout(self) -> None:
        """Create the main window layout structure."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top section: Project and Stage selection
        main_layout.addWidget(self.project_selector)
        main_layout.addWidget(self.stage_toggles)
        
        # Configuration section
        main_layout.addWidget(self.stage_configurators)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Vertical)
        
        # Progress section (fixed height)
        splitter.addWidget(self.progress_section)
        
        # Create tab widget for log and results
        tab_widget = QTabWidget()
        tab_widget.addTab(self.log_panel, "Log")
        tab_widget.addTab(self.results_panel, "Results")
        splitter.addWidget(tab_widget)
        
        # Set splitter proportions
        splitter.setStretchFactor(0, 0)  # Progress section: no stretch
        splitter.setStretchFactor(1, 1)  # Tab widget: stretch to fill
        
        main_layout.addWidget(splitter)
        
        # Action buttons at bottom
        main_layout.addWidget(self.action_buttons)
        
        # Set layout stretch factors
        main_layout.setStretchFactor(splitter, 1)
    
    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # New Project action
        new_project_action = QAction("&New Project...", self)
        new_project_action.setShortcut(QKeySequence.New)
        new_project_action.setStatusTip("Select a new project directory")
        new_project_action.triggered.connect(self.project_selector.select_directory)
        file_menu.addAction(new_project_action)
        
        file_menu.addSeparator()
        
        # Settings action
        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.setStatusTip("Open application settings")
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip("Exit the application")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        # Clear Log action
        clear_log_action = QAction("&Clear Log", self)
        clear_log_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_log_action.setStatusTip("Clear the log panel")
        clear_log_action.triggered.connect(self.log_panel.clear)
        edit_menu.addAction(clear_log_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        # Check Dependencies action
        check_deps_action = QAction("Check &Dependencies", self)
        check_deps_action.setStatusTip("Check for required dependencies")
        check_deps_action.triggered.connect(self._check_dependencies)
        tools_menu.addAction(check_deps_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        # About action
        about_action = QAction("&About", self)
        about_action.setStatusTip("About SubtitleToolkit")
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self) -> None:
        """Create the application status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")
    
    def _connect_signals(self) -> None:
        """Connect all signal/slot relationships."""
        # Project selector signals
        self.project_selector.directory_selected.connect(self._on_project_changed)
        
        # Stage toggles signals
        self.stage_toggles.stages_changed.connect(self._on_stages_changed)
        self.stage_toggles.stages_changed.connect(self.stage_configurators.update_enabled_stages)
        
        # Action buttons signals
        self.action_buttons.run_clicked.connect(self._on_run_clicked)
        self.action_buttons.cancel_clicked.connect(self._on_cancel_clicked)
        self.action_buttons.open_output_clicked.connect(self._on_open_output_clicked)
        
        # Internal signals
        self.project_changed.connect(self._update_project_dependent_ui)
        self.stages_changed.connect(self._update_stage_dependent_ui)
        
        # Log panel signals
        self.log_panel.message_logged.connect(self._on_log_message)
    
    def _on_project_changed(self, directory: str) -> None:
        """Handle project directory change."""
        self.project_changed.emit(directory)
        self.log_panel.add_message("info", f"Project directory selected: {directory}")
    
    def _on_stages_changed(self, stages: dict) -> None:
        """Handle stage selection changes."""
        self.stages_changed.emit(stages)
        
        # Log stage changes
        enabled_stages = [stage for stage, enabled in stages.items() if enabled]
        if enabled_stages:
            self.log_panel.add_message("info", f"Enabled stages: {', '.join(enabled_stages)}")
        else:
            self.log_panel.add_message("info", "No stages enabled")
    
    def _on_run_clicked(self) -> None:
        """Handle run button click."""
        # Validate configuration before running
        if not self._validate_configuration():
            return
        
        self.run_requested.emit()
        self.log_panel.add_message("info", "Starting processing pipeline...")
        self._set_running_state(True)
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        self.cancel_requested.emit()
        self.log_panel.add_message("info", "Processing cancelled by user")
        self._set_running_state(False)
    
    def _on_open_output_clicked(self) -> None:
        """Handle open output button click."""
        self.open_output_requested.emit()
    
    def _on_log_message(self, level: str, message: str) -> None:
        """Handle log messages for status bar updates."""
        if level == "error":
            self.status_bar.showMessage(f"Error: {message}", 5000)
        elif level == "warning":
            self.status_bar.showMessage(f"Warning: {message}", 3000)
    
    def _update_project_dependent_ui(self, directory: str) -> None:
        """Update UI elements that depend on project selection."""
        has_project = bool(directory)
        
        # Enable/disable relevant UI elements
        self.stage_toggles.setEnabled(has_project)
        self.stage_configurators.setEnabled(has_project)
        
        if has_project:
            # Update status
            self.status_bar.showMessage(f"Project: {directory}")
            
            # Update configurators with project path
            self.stage_configurators.set_project_directory(directory)
        else:
            self.status_bar.showMessage("No project selected")
    
    def _update_stage_dependent_ui(self, stages: dict) -> None:
        """Update UI elements that depend on stage selection."""
        has_enabled_stages = any(stages.values())
        
        # Enable/disable run button
        has_project = bool(self.project_selector.selected_directory)
        self.action_buttons.set_run_enabled(has_project and has_enabled_stages)
    
    def _validate_configuration(self) -> bool:
        """Validate current configuration before running."""
        # Check if project is selected
        if not self.project_selector.selected_directory:
            QMessageBox.warning(
                self, "No Project Selected",
                "Please select a project directory before running."
            )
            return False
        
        # Check if at least one stage is enabled
        stages = self.stage_toggles.get_enabled_stages()
        if not any(stages.values()):
            QMessageBox.warning(
                self, "No Stages Enabled",
                "Please enable at least one processing stage."
            )
            return False
        
        # Validate stage configurations
        validation_result = self.stage_configurators.validate_configurations(stages)
        if not validation_result.is_valid:
            QMessageBox.warning(
                self, "Configuration Error",
                f"Configuration validation failed:\n\n{validation_result.error_message}"
            )
            return False
        
        return True
    
    def _set_running_state(self, running: bool) -> None:
        """Update UI to reflect running/idle state."""
        # Update action buttons
        self.action_buttons.set_running_state(running)
        
        # Disable/enable configuration during run
        self.project_selector.setEnabled(not running)
        self.stage_toggles.setEnabled(not running)
        self.stage_configurators.setEnabled(not running)
        
        if running:
            self.status_bar.showMessage("Processing...")
            # Clear previous results
            self.results_panel.clear()
        else:
            self.status_bar.showMessage("Ready")
    
    def _update_status(self) -> None:
        """Update status bar with current information."""
        # This is called periodically to update status
        # Implementation depends on backend integration
        pass
    
    def _show_settings(self) -> None:
        """Show application settings dialog."""
        # Placeholder for settings dialog
        QMessageBox.information(
            self, "Settings",
            "Settings dialog will be implemented in Phase 3.\n\n"
            "This will include:\n"
            "• Tool path detection (ffmpeg/mkvextract)\n"
            "• API key management\n"
            "• Language defaults\n"
            "• Advanced options"
        )
    
    def _check_dependencies(self) -> None:
        """Check for required dependencies."""
        # Placeholder for dependency checking
        QMessageBox.information(
            self, "Dependencies",
            "Dependency checking will be implemented in Phase 3.\n\n"
            "This will check for:\n"
            "• ffmpeg and ffprobe\n"
            "• mkvextract (optional)\n"
            "• Python packages\n"
            "• API connectivity"
        )
    
    def _show_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self, "About SubtitleToolkit",
            "SubtitleToolkit v1.0.0\n\n"
            "A comprehensive desktop application for subtitle processing.\n\n"
            "Features:\n"
            "• Extract subtitles from MKV files\n"
            "• Translate SRT files using AI\n"
            "• Intelligently sync subtitle filenames\n\n"
            "Built with PySide6 and Qt6"
        )
    
    def closeEvent(self, event) -> None:
        """Handle application close event."""
        # Check if processing is running
        if self.action_buttons.is_running:
            reply = QMessageBox.question(
                self, "Confirm Exit",
                "Processing is currently running. Are you sure you want to exit?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                event.ignore()
                return
            
            # Cancel running processes
            self.cancel_requested.emit()
        
        # Save settings here if needed
        event.accept()