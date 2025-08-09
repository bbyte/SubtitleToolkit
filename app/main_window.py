"""
MainWindow implementation for SubtitleToolkit Desktop Application.

This module contains the main window class that orchestrates all UI components
according to the workflow specifications.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QMenuBar, QStatusBar, QMessageBox, QLabel
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence

from app.widgets.project_selector import ProjectSelector
from app.widgets.stage_toggles import StageToggles
from app.widgets.stage_configurators import StageConfigurators
from app.widgets.progress_section import ProgressSection
from app.widgets.log_panel import LogPanel
from app.widgets.results_panel import ResultsPanel
from app.widgets.action_buttons import ActionButtons

from app.dialogs.settings_dialog import SettingsDialog
from app.config.config_manager import ConfigManager
from app.runner import ScriptRunner, ExtractConfig, TranslateConfig, SyncConfig, Stage, EventType
from app.zoom_manager import ZoomManager
from app.window_state_manager import WindowStateManager


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
        
        # Zoom manager for browser-style zoom functionality
        self.zoom_manager = ZoomManager(self.config_manager, self)
        
        # Window state manager for window geometry persistence
        self.window_state_manager = WindowStateManager(self, self.config_manager, self)
        
        # Script runner for subprocess management
        self.script_runner = ScriptRunner(self)
        
        # Window properties
        self.setWindowTitle("SubtitleToolkit")
        self.setMinimumSize(1000, 700)
        
        # Try to restore window state, otherwise use defaults
        if not self.window_state_manager.restore_window_state():
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
        
        # Register UI components with zoom manager and apply initial zoom
        self._setup_zoom_integration()
    
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
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        # Add zoom actions to View menu
        zoom_actions = self.zoom_manager.create_zoom_actions(self)
        view_menu.addAction(zoom_actions["zoom_in"])
        view_menu.addAction(zoom_actions["zoom_out"])
        view_menu.addAction(zoom_actions["reset_zoom"])
        
        view_menu.addSeparator()
        
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
        
        # Add zoom indicator to status bar
        self.zoom_status_label = QLabel()
        self.zoom_status_label.setMinimumWidth(80)
        self.zoom_status_label.setAlignment(Qt.AlignCenter)
        self.status_bar.addPermanentWidget(self.zoom_status_label)
        
        # Register zoom status label with zoom manager
        self.zoom_manager.register_status_label(self.zoom_status_label)
    
    def _setup_zoom_integration(self) -> None:
        """Set up zoom integration with UI components."""
        # Register key UI components for zoom scaling
        widgets_to_register = [
            self.project_selector,
            self.stage_toggles,
            self.stage_configurators,
            self.progress_section,
            self.log_panel,
            self.results_panel,
            self.action_buttons,
            self.menuBar(),
            self.status_bar
        ]
        
        for widget in widgets_to_register:
            if widget:
                self.zoom_manager.register_widget(widget)
        
        # Auto-register child widgets for comprehensive zoom support
        self.zoom_manager.auto_register_children(self, recursive=True)
        
        # Apply initial zoom level
        self.zoom_manager.apply_initial_zoom()
        
        # Connect zoom signals for UI updates
        self.zoom_manager.zoom_changed.connect(self._on_zoom_changed)
        self.zoom_manager.zoom_reset.connect(self._on_zoom_reset)
    
    def _on_zoom_changed(self, zoom_factor: float) -> None:
        """Handle zoom level changes."""
        percentage = int(zoom_factor * 100)
        self.log_panel.add_message("info", f"Zoom level changed to {percentage}%")
    
    def _on_zoom_reset(self) -> None:
        """Handle zoom reset to default."""
        self.log_panel.add_message("info", "Zoom level reset to 100%")
    
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
        
        # Script runner signals
        self._connect_runner_signals()
        
        # Window state manager signals
        self.window_state_manager.validation_failed.connect(self._on_window_state_error)
    
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
        
        try:
            self._start_processing_pipeline()
        except Exception as e:
            QMessageBox.critical(
                self, "Pipeline Error",
                f"Failed to start processing pipeline:\n\n{str(e)}"
            )
            self.log_panel.add_message("error", f"Pipeline start failed: {str(e)}")
    
    def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        if self.script_runner.is_running:
            self.script_runner.cancel_current_process()
            self.log_panel.add_message("info", "Processing cancelled by user")
        else:
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
    
    def _on_window_state_error(self, error_message: str) -> None:
        """Handle window state management errors."""
        self.log_panel.add_message("warning", f"Window state: {error_message}")
    
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
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.config_manager, self)
            self._settings_dialog.settings_applied.connect(self._on_settings_applied)
        
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()
    
    def _check_dependencies(self) -> None:
        """Check for required dependencies."""
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.config_manager, self)
            self._settings_dialog.settings_applied.connect(self._on_settings_applied)
        
        # Show settings dialog on Tools tab and refresh detection
        self._settings_dialog.show_tab("tools")
        self._settings_dialog.refresh_tool_detection()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()
    
    def _on_settings_applied(self) -> None:
        """Handle when settings are applied."""
        self.log_panel.add_message("info", "Settings updated successfully")
        
        # Refresh UI elements that depend on settings
        self._update_ui_from_settings()
        
        # Update zoom manager with new settings
        ui_settings = self.config_manager.get_settings("ui")
        new_zoom = ui_settings.get("zoom_level", 1.0)
        if new_zoom != self.zoom_manager.current_zoom:
            self.zoom_manager.set_zoom(new_zoom)
    
    def _update_ui_from_settings(self) -> None:
        """Update UI elements based on current settings."""
        # This method can be used to update UI elements when settings change
        # For example, updating language defaults, UI behavior, etc.
        settings = self.config_manager.get_settings()
        
        # Update stage configurators with new settings
        if hasattr(self.stage_configurators, 'update_from_settings'):
            self.stage_configurators.update_from_settings(settings)
    
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
        if self.script_runner.is_running:
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
            self.script_runner.cancel_current_process()
        
        # Save current zoom level and window state to settings before closing
        ui_settings = self.config_manager.get_settings("ui")
        ui_settings["zoom_level"] = self.zoom_manager.current_zoom
        self.config_manager.update_settings("ui", ui_settings, save=True)
        
        # Clean up window state manager and save final state
        self.window_state_manager.cleanup()
        
        event.accept()
    
    def _connect_runner_signals(self) -> None:
        """Connect ScriptRunner signals to UI handlers."""
        signals = self.script_runner.signals
        
        # Process lifecycle signals
        signals.process_started.connect(self._on_process_started)
        signals.process_finished.connect(self._on_process_finished)
        signals.process_failed.connect(self._on_process_failed)
        signals.process_cancelled.connect(self._on_process_cancelled)
        
        # Event signals from JSONL stream
        signals.info_received.connect(self._on_info_received)
        signals.progress_updated.connect(self._on_progress_updated)
        signals.warning_received.connect(self._on_warning_received)
        signals.error_received.connect(self._on_error_received)
        signals.result_received.connect(self._on_result_received)
    
    def _start_processing_pipeline(self) -> None:
        """Start the processing pipeline based on enabled stages."""
        stages = self.stage_toggles.get_enabled_stages()
        project_dir = self.project_selector.selected_directory
        
        if not project_dir:
            raise ValueError("No project directory selected")
        
        self.log_panel.add_message("info", "Starting processing pipeline...")
        self._set_running_state(True)
        
        # Start with the first enabled stage
        if stages.get('extract', False):
            self._run_extract_stage()
        elif stages.get('translate', False):
            self._run_translate_stage() 
        elif stages.get('sync', False):
            self._run_sync_stage()
    
    def _run_extract_stage(self) -> None:
        """Run the extraction stage."""
        try:
            config = self._build_extract_config()
            self.script_runner.run_extract(config)
        except Exception as e:
            self.log_panel.add_message("error", f"Failed to start extraction: {str(e)}")
            self._set_running_state(False)
            raise
    
    def _run_translate_stage(self) -> None:
        """Run the translation stage."""
        try:
            config = self._build_translate_config()
            self.script_runner.run_translate(config)
        except Exception as e:
            self.log_panel.add_message("error", f"Failed to start translation: {str(e)}")
            self._set_running_state(False)
            raise
    
    def _run_sync_stage(self) -> None:
        """Run the sync stage."""
        try:
            config = self._build_sync_config()
            self.script_runner.run_sync(config)
        except Exception as e:
            self.log_panel.add_message("error", f"Failed to start sync: {str(e)}")
            self._set_running_state(False)
            raise
    
    def _build_extract_config(self) -> ExtractConfig:
        """Build extraction configuration from UI settings."""
        project_dir = self.project_selector.selected_directory
        
        # Get configuration from stage configurators
        extract_settings = self.stage_configurators.get_extract_config()
        
        # Get tool paths from settings
        settings = self.config_manager.get_settings()
        tools_config = settings.get('tools', {})
        
        return ExtractConfig(
            input_directory=project_dir,
            language_code=extract_settings.get('language_code', 'eng'),
            output_directory=extract_settings.get('output_directory'),
            recursive=extract_settings.get('recursive', True),
            overwrite_existing=extract_settings.get('overwrite_existing', False),
            ffmpeg_path=tools_config.get('ffmpeg_path') or None,
            ffprobe_path=tools_config.get('ffprobe_path') or None,
        )
    
    def _build_translate_config(self) -> TranslateConfig:
        """Build translation configuration from UI settings."""
        project_dir = self.project_selector.selected_directory
        
        # Get configuration from stage configurators
        translate_settings = self.stage_configurators.get_translate_config()
        
        # Get settings
        settings = self.config_manager.get_settings()
        translators_config = settings.get('translators', {})
        advanced_config = settings.get('advanced', {})
        
        provider = translate_settings.get('provider', 'openai')
        provider_config = translators_config.get(provider, {})
        
        return TranslateConfig(
            input_directory=project_dir,
            output_directory=translate_settings.get('output_directory'),
            source_language=translate_settings.get('source_language', 'auto'),
            target_language=translate_settings.get('target_language', 'en'),
            provider=provider,
            model=translate_settings.get('model') or provider_config.get('default_model', ''),
            api_key=provider_config.get('api_key', ''),
            base_url=provider_config.get('base_url') if provider == 'lm_studio' else None,
            max_workers=advanced_config.get('max_concurrent_workers', 3),
            temperature=provider_config.get('temperature', 0.3),
            max_tokens=provider_config.get('max_tokens', 4096),
            timeout=provider_config.get('timeout', 30),
            overwrite_existing=translate_settings.get('overwrite_existing', False),
        )
    
    def _build_sync_config(self) -> SyncConfig:
        """Build sync configuration from UI settings."""
        project_dir = self.project_selector.selected_directory
        
        # Get configuration from stage configurators
        sync_settings = self.stage_configurators.get_sync_config()
        
        # Get settings
        settings = self.config_manager.get_settings()
        translators_config = settings.get('translators', {})
        
        provider = sync_settings.get('provider', 'openai')
        provider_config = translators_config.get(provider, {})
        
        return SyncConfig(
            input_directory=project_dir,
            provider=provider,
            model=sync_settings.get('model') or provider_config.get('default_model', ''),
            confidence_threshold=sync_settings.get('confidence_threshold', 0.8),
            api_key=provider_config.get('api_key', ''),
            dry_run=sync_settings.get('dry_run', True),
            recursive=sync_settings.get('recursive', True),
            naming_template=sync_settings.get('naming_template', "{show_title} - S{season:02d}E{episode:02d} - {episode_title}"),
        )
    
    # ScriptRunner signal handlers
    def _on_process_started(self, stage: Stage) -> None:
        """Handle process started signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("info", f"{stage_name} stage started")
        self.progress_section.set_stage_active(stage.value)
        self.progress_section.set_progress(0, f"Starting {stage_name.lower()}...")
    
    def _on_process_finished(self, result) -> None:  # result is ProcessResult
        """Handle process finished signal."""
        stage_name = result.stage.value.capitalize()
        
        if result.success:
            self.log_panel.add_message("info", 
                f"{stage_name} stage completed successfully in {result.duration_seconds:.1f}s")
            self.progress_section.set_progress(100, f"{stage_name} completed")
            
            # Update results panel
            if result.output_files:
                self.results_panel.add_results(result.stage.value, result.output_files)
            
            # Check if we need to run next stage
            self._check_next_stage(result.stage)
        else:
            error_msg = result.error_message or f"Process failed with exit code {result.exit_code}"
            self.log_panel.add_message("error", f"{stage_name} stage failed: {error_msg}")
            self.progress_section.set_error(f"{stage_name} failed")
            self._set_running_state(False)
    
    def _on_process_failed(self, stage: Stage, error_message: str) -> None:
        """Handle process failed signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("error", f"{stage_name} stage failed: {error_message}")
        self.progress_section.set_error(f"{stage_name} failed")
        self._set_running_state(False)
    
    def _on_process_cancelled(self, stage: Stage) -> None:
        """Handle process cancelled signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("info", f"{stage_name} stage cancelled")
        self.progress_section.set_cancelled(f"{stage_name} cancelled")
        self._set_running_state(False)
    
    def _on_info_received(self, stage: Stage, message: str) -> None:
        """Handle info message from process."""
        self.log_panel.add_message("info", message)
    
    def _on_progress_updated(self, stage: Stage, progress: int, message: str) -> None:
        """Handle progress update from process."""
        self.progress_section.set_progress(progress, message)
    
    def _on_warning_received(self, stage: Stage, message: str) -> None:
        """Handle warning message from process."""
        self.log_panel.add_message("warning", message)
    
    def _on_error_received(self, stage: Stage, message: str) -> None:
        """Handle error message from process."""
        self.log_panel.add_message("error", message)
    
    def _on_result_received(self, stage: Stage, data: dict) -> None:
        """Handle result data from process."""
        # Extract useful information from result data
        if 'outputs' in data:
            self.results_panel.add_results(stage.value, data['outputs'])
        
        # Log summary information
        if 'files_processed' in data:
            files_processed = data['files_processed']
            files_successful = data.get('files_successful', 0)
            self.log_panel.add_message("info", 
                f"Processed {files_processed} files, {files_successful} successful")
    
    def _check_next_stage(self, completed_stage: Stage) -> None:
        """Check if we need to run the next stage in the pipeline."""
        stages = self.stage_toggles.get_enabled_stages()
        
        # Determine next stage to run
        if completed_stage == Stage.EXTRACT and stages.get('translate', False):
            self._run_translate_stage()
        elif completed_stage == Stage.TRANSLATE and stages.get('sync', False):
            self._run_sync_stage()
        else:
            # Pipeline complete
            self.log_panel.add_message("info", "Processing pipeline completed")
            self._set_running_state(False)