"""
MainWindow implementation for SubtitleToolkit Desktop Application.

This module contains the main window class that orchestrates all UI components
according to the workflow specifications.
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTabWidget, QMenuBar, QStatusBar, QMessageBox, QLabel, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QAction, QKeySequence
from typing import List, Dict

from app.widgets.project_selector import ProjectSelector
from app.widgets.stage_toggles import StageToggles
from app.widgets.stage_configurators import StageConfigurators
from app.widgets.progress_section import ProgressSection
from app.widgets.processing_banner import ProcessingBanner
from app.widgets.log_panel import LogPanel
from app.widgets.results_panel import ResultsPanel
from app.widgets.action_buttons import ActionButtons

from app.dialogs.settings_dialog import SettingsDialog
from app.dialogs.sync_confirmation_dialog import SyncConfirmationDialog
from app.dialogs.video_preview_dialog import VideoPreviewDialog
from app.config.config_manager import ConfigManager
from app.runner import ScriptRunner, ExtractConfig, TranslateConfig, SyncConfig, FpsSyncConfig, Stage, EventType
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
    
    def __init__(self, parent: QWidget = None, config_manager: ConfigManager = None):
        super().__init__(parent)

        # Configuration manager — use the provided one (from the app) to ensure a
        # single shared instance. If none is provided fall back to creating one.
        self.config_manager = config_manager if config_manager is not None else ConfigManager(self)
        
        # Zoom manager for browser-style zoom functionality
        self.zoom_manager = ZoomManager(self.config_manager, self)
        
        # Window state manager for window geometry persistence
        self.window_state_manager = WindowStateManager(self, self.config_manager, self)
        
        # Script runner for subprocess management
        self.script_runner = ScriptRunner(self)
        
        # Window properties
        self.setWindowTitle(self.tr("SubtitleToolkit"))
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
        
        # Set initial state - disable all controls until project/file is selected
        self._set_initial_disabled_state()
        
        # Settings dialog (created on demand)
        self._settings_dialog = None

        # Alias kept for existing call sites — points to the inline banner
        self._progress_dialog = self.processing_banner

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
        self.stage_configurators = StageConfigurators(self.config_manager)
        self.progress_section = ProgressSection()
        self.processing_banner = ProcessingBanner()
        self.log_panel = LogPanel()
        self.results_panel = ResultsPanel()
        self.action_buttons = ActionButtons()
    
    def _create_layout(self) -> None:
        """Create the main window layout structure with scroll support."""
        # Central widget - this will contain the scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create a minimal layout for the central widget
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        
        # Create scroll area for main content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        
        # Create scrollable content widget
        scrollable_widget = QWidget()
        scroll_area.setWidget(scrollable_widget)
        
        # Main vertical layout for scrollable content
        main_layout = QVBoxLayout(scrollable_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Top section: Project and Stage selection
        main_layout.addWidget(self.project_selector)
        main_layout.addWidget(self.stage_toggles)
        
        # Configuration section
        main_layout.addWidget(self.stage_configurators)
        
        # Legacy progress section — hidden, kept for reference only
        self.progress_section.setVisible(False)

        # Inline processing banner (non-modal; replaces the old modal dialog)
        main_layout.addWidget(self.processing_banner)

        # Create tab widget for log and results - expands to fill space
        tab_widget = QTabWidget()
        # Results tab first, then Log
        tab_widget.addTab(self.results_panel, self.tr("Results"))
        tab_widget.addTab(self.log_panel, self.tr("Log"))
        tab_widget.setMinimumHeight(150)  # Minimum for usability

        # Add to layout with stretch factor to fill available space
        main_layout.addWidget(tab_widget, 1)  # Stretch factor of 1 = fills space

        # Action buttons at bottom (no stretch, fixed height)
        main_layout.addWidget(self.action_buttons, 0)  # Stretch factor 0 = fixed size
        
        # Add scroll area to central layout
        central_layout.addWidget(scroll_area)
        
        # Store reference to scroll area for potential future use
        self.scroll_area = scroll_area
        self.scrollable_widget = scrollable_widget
        
        # Configure scroll area for smooth scrolling
        self._configure_scroll_behavior()
    
    def _set_initial_disabled_state(self) -> None:
        """Set initial disabled state for all controls until project/file is selected."""
        # Disable stage toggles and configurators on startup
        self.stage_toggles.setEnabled(False)
        self.stage_configurators.setEnabled(False)
        
        # Disable action buttons (except cancel)
        self.action_buttons.set_run_enabled(False)
        
        # Set status message
        self.status_bar.showMessage(self.tr("Please select a project directory or file to get started"))
    
    def _configure_scroll_behavior(self) -> None:
        """Configure scroll area for optimal behavior."""
        # Enable smooth scrolling
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Set scroll speed and behavior
        vertical_scrollbar = self.scroll_area.verticalScrollBar()
        horizontal_scrollbar = self.scroll_area.horizontalScrollBar()
        
        # Set single step for smooth scrolling (adjust based on font size)
        vertical_scrollbar.setSingleStep(20)
        horizontal_scrollbar.setSingleStep(20)
        
        # Set page step for larger jumps
        vertical_scrollbar.setPageStep(200)
        horizontal_scrollbar.setPageStep(200)
        
        # Enable focus on scroll area for keyboard navigation
        self.scroll_area.setFocusPolicy(Qt.StrongFocus)
    
    def _create_menu_bar(self) -> None:
        """Create the application menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(self.tr("&File"))
        
        # New Project action
        new_project_action = QAction(self.tr("&New Project..."), self)
        new_project_action.setShortcut(QKeySequence.New)
        new_project_action.setStatusTip(self.tr("Select a new project directory"))
        new_project_action.triggered.connect(self.project_selector.select_directory)
        file_menu.addAction(new_project_action)
        
        file_menu.addSeparator()
        
        # Settings action
        settings_action = QAction(self.tr("&Settings..."), self)
        settings_action.setShortcut(QKeySequence.Preferences)
        settings_action.setStatusTip(self.tr("Open application settings"))
        settings_action.triggered.connect(self._show_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = QAction(self.tr("E&xit"), self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.setStatusTip(self.tr("Exit the application"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu(self.tr("&Edit"))
        
        # Clear Log action
        clear_log_action = QAction(self.tr("&Clear Log"), self)
        clear_log_action.setShortcut(QKeySequence("Ctrl+L"))
        clear_log_action.setStatusTip(self.tr("Clear the log panel"))
        clear_log_action.triggered.connect(self.log_panel.clear)
        edit_menu.addAction(clear_log_action)
        
        # View menu
        view_menu = menubar.addMenu(self.tr("&View"))
        
        # Add zoom actions to View menu
        zoom_actions = self.zoom_manager.create_zoom_actions(self)
        view_menu.addAction(zoom_actions["zoom_in"])
        view_menu.addAction(zoom_actions["zoom_out"])
        view_menu.addAction(zoom_actions["reset_zoom"])
        
        view_menu.addSeparator()
        
        # Add scroll actions to View menu
        scroll_up_action = QAction(self.tr("Scroll &Up"), self)
        scroll_up_action.setShortcut(QKeySequence("Ctrl+Up"))
        scroll_up_action.setStatusTip(self.tr("Scroll content up"))
        scroll_up_action.triggered.connect(self._scroll_up)
        view_menu.addAction(scroll_up_action)
        
        scroll_down_action = QAction(self.tr("Scroll &Down"), self)
        scroll_down_action.setShortcut(QKeySequence("Ctrl+Down"))
        scroll_down_action.setStatusTip(self.tr("Scroll content down"))
        scroll_down_action.triggered.connect(self._scroll_down)
        view_menu.addAction(scroll_down_action)
        
        scroll_to_top_action = QAction(self.tr("Scroll to &Top"), self)
        scroll_to_top_action.setShortcut(QKeySequence("Ctrl+Home"))
        scroll_to_top_action.setStatusTip(self.tr("Scroll to top of content"))
        scroll_to_top_action.triggered.connect(self._scroll_to_top)
        view_menu.addAction(scroll_to_top_action)
        
        scroll_to_bottom_action = QAction(self.tr("Scroll to &Bottom"), self)
        scroll_to_bottom_action.setShortcut(QKeySequence("Ctrl+End"))
        scroll_to_bottom_action.setStatusTip(self.tr("Scroll to bottom of content"))
        scroll_to_bottom_action.triggered.connect(self._scroll_to_bottom)
        view_menu.addAction(scroll_to_bottom_action)
        
        view_menu.addSeparator()
        
        # Tools menu
        tools_menu = menubar.addMenu(self.tr("&Tools"))
        
        # Calibrate Model action
        calibrate_action = QAction(self.tr("&Calibrate Model…"), self)
        calibrate_action.setShortcut(QKeySequence("Ctrl+Shift+C"))
        calibrate_action.setStatusTip(
            self.tr("Probe an AI model to find optimal chunk size and worker settings")
        )
        calibrate_action.triggered.connect(self._show_calibration_dialog)
        tools_menu.addAction(calibrate_action)

        tools_menu.addSeparator()

        # Check Dependencies action
        check_deps_action = QAction(self.tr("Check &Dependencies"), self)
        check_deps_action.setStatusTip(self.tr("Check for required dependencies"))
        check_deps_action.triggered.connect(self._check_dependencies)
        tools_menu.addAction(check_deps_action)

        tools_menu.addSeparator()

        # Preview Video action
        preview_video_action = QAction(self.tr("&Preview Video with Subtitles..."), self)
        preview_video_action.setShortcut(QKeySequence("Ctrl+P"))
        preview_video_action.setStatusTip(self.tr("Preview video with subtitles"))
        preview_video_action.triggered.connect(self._show_video_preview)
        tools_menu.addAction(preview_video_action)

        # Help menu
        help_menu = menubar.addMenu(self.tr("&Help"))
        
        # About action
        about_action = QAction(self.tr("&About"), self)
        about_action.setStatusTip(self.tr("About SubtitleToolkit"))
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self) -> None:
        """Create the application status bar."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage(self.tr("Ready"))
        
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
            self.status_bar,
            self.scroll_area,
            self.scrollable_widget
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
    
    # Scroll management methods
    def _scroll_up(self) -> None:
        """Scroll content up."""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        scrollbar.setValue(current_value - scrollbar.pageStep())
    
    def _scroll_down(self) -> None:
        """Scroll content down."""
        scrollbar = self.scroll_area.verticalScrollBar()
        current_value = scrollbar.value()
        scrollbar.setValue(current_value + scrollbar.pageStep())
    
    def _scroll_to_top(self) -> None:
        """Scroll to top of content."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.minimum())
    
    def _scroll_to_bottom(self) -> None:
        """Scroll to bottom of content."""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def eventFilter(self, source, event) -> bool:
        """Filter events for scroll area content updates."""
        from PySide6.QtCore import QEvent
        
        # Handle resize events for the scrollable widget
        if source == self.scrollable_widget and event.type() == QEvent.Resize:
            # Update scroll area's widget size constraints
            self.scroll_area.updateGeometry()
            
        return super().eventFilter(source, event)
    
    def wheelEvent(self, event) -> None:
        """Handle wheel events for smooth scrolling."""
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QWheelEvent
        
        # Check if Ctrl is pressed for zoom, otherwise handle scroll
        if event.modifiers() & Qt.ControlModifier:
            # Let the zoom manager handle Ctrl+wheel events
            super().wheelEvent(event)
        else:
            # Handle normal scrolling
            scrollbar = self.scroll_area.verticalScrollBar()
            
            # Calculate scroll amount (negative for up, positive for down)
            scroll_amount = -event.angleDelta().y() // 120 * scrollbar.singleStep() * 3
            
            current_value = scrollbar.value()
            new_value = current_value + scroll_amount
            
            # Clamp to valid range
            new_value = max(scrollbar.minimum(), min(scrollbar.maximum(), new_value))
            scrollbar.setValue(new_value)
            
            event.accept()
    
    def ensure_widget_visible(self, widget: QWidget) -> None:
        """Ensure a widget is visible in the scroll area."""
        if not widget or not widget.isVisible():
            return
            
        # Get widget's position relative to the scrollable content
        widget_rect = widget.geometry()
        scrollable_rect = self.scrollable_widget.geometry()
        
        # Calculate relative position
        relative_pos = widget.mapTo(self.scrollable_widget, widget_rect.topLeft())
        widget_bottom = relative_pos.y() + widget_rect.height()
        
        # Get current scroll position and visible area
        scrollbar = self.scroll_area.verticalScrollBar()
        current_scroll = scrollbar.value()
        visible_height = self.scroll_area.viewport().height()
        
        # Check if widget is fully visible
        if relative_pos.y() < current_scroll:
            # Widget is above visible area, scroll up
            scrollbar.setValue(relative_pos.y())
        elif widget_bottom > current_scroll + visible_height:
            # Widget is below visible area, scroll down
            new_scroll = widget_bottom - visible_height
            scrollbar.setValue(max(0, new_scroll))
    
    def _connect_signals(self) -> None:
        """Connect all signal/slot relationships."""
        # Project selector signals
        self.project_selector.directory_selected.connect(self._on_project_changed)
        self.project_selector.file_selected.connect(self._on_project_changed)
        self.project_selector.selection_cleared.connect(self._on_project_cleared)
        self.project_selector.languages_detected.connect(self._on_languages_detected)
        
        # Connect mode changes to stage availability
        self.project_selector.mode_group.buttonToggled.connect(self._on_selection_mode_changed)
        
        # Stage toggles signals
        self.stage_toggles.stages_changed.connect(self._on_stages_changed)
        self.stage_toggles.stages_changed.connect(self.stage_configurators.update_enabled_stages)
        self.stage_toggles.stages_changed.connect(self._on_configuration_changed)
        
        # Action buttons signals
        self.action_buttons.run_clicked.connect(self._on_run_clicked)
        self.action_buttons.cancel_clicked.connect(self._on_cancel_clicked)
        self.action_buttons.open_output_clicked.connect(self._on_open_output_clicked)
        self.action_buttons.preview_clicked.connect(self._on_preview_clicked)
        self.action_buttons.find_subtitles_clicked.connect(self._on_find_subtitles_clicked)
        
        # Internal signals
        self.project_changed.connect(self._update_project_dependent_ui)
        self.stages_changed.connect(self._update_stage_dependent_ui)
        
        # Processing banner signals
        self.processing_banner.cancel_requested.connect(self._on_progress_dialog_cancel)

        # Log panel signals
        self.log_panel.message_logged.connect(self._on_log_message)

        # Script runner signals
        self._connect_runner_signals()
        
        # Window state manager signals
        self.window_state_manager.validation_failed.connect(self._on_window_state_error)
        
        # Connect scroll area resize events for dynamic content handling
        self.scrollable_widget.installEventFilter(self)
    
    def _on_project_changed(self, path: str) -> None:
        """Handle project directory or file change."""
        self.project_changed.emit(path)

        # Determine if it's a directory or file
        from pathlib import Path
        path_obj = Path(path)
        if path_obj.is_dir():
            self.log_panel.add_message("info", f"Project directory selected: {path}")
            # Clear file type constraints for directory mode
            self.stage_toggles.set_file_type_constraints("")
        else:
            self.log_panel.add_message("info", f"Single file selected: {path}")
            # Apply file type constraints based on selected file
            self.stage_toggles.set_file_type_constraints(path)

        # Update translate cost estimate with the selected path
        self.stage_configurators.update_translate_cost_estimate(path)

        # Enable preview button when a file or directory is selected
        self.action_buttons.set_preview_enabled(True)

        # Enable find subtitles button for directories
        self.action_buttons.set_find_subtitles_enabled(path_obj.is_dir())
    
    def _on_project_cleared(self) -> None:
        """Handle project selection being cleared."""
        self.project_changed.emit("")
        self.log_panel.add_message("info", "Project selection cleared")

        # Clear detected languages in extract configuration
        self.stage_configurators.clear_extract_languages()

        # Clear file type constraints
        self.stage_toggles.set_file_type_constraints("")

        # Clear translate cost estimate
        self.stage_configurators.update_translate_cost_estimate("")

        # Disable preview button when no project is selected
        self.action_buttons.set_preview_enabled(False)
        self.action_buttons.set_find_subtitles_enabled(False)
    
    def _on_languages_detected(self, detection_result) -> None:
        """Handle subtitle language detection results."""
        from app.utils.mkv_language_detector import LanguageDetectionResult
        
        # Type check for safety
        if not isinstance(detection_result, LanguageDetectionResult):
            return
        
        # Forward the detection result to the ExtractConfigWidget
        self.stage_configurators.update_extract_languages(detection_result)
        
        # Log language detection results
        if detection_result.errors:
            for error in detection_result.errors[:3]:  # Show first 3 errors
                self.log_panel.add_message("warning", f"Language detection: {error}")
        
        if detection_result.available_languages:
            lang_names = [name for _, name in detection_result.available_languages]
            self.log_panel.add_message("info", 
                f"Found subtitle languages in {detection_result.files_with_subtitles}/{detection_result.total_files} files: {', '.join(lang_names)}")
        elif detection_result.total_files > 0:
            self.log_panel.add_message("warning", 
                f"No subtitle languages found in {detection_result.total_files} MKV file(s)")
    
    def _on_selection_mode_changed(self, button, checked: bool) -> None:
        """Handle selection mode change between directory and file."""
        if not checked:  # Only respond to button being checked
            return
        
        # Update stage toggles based on mode
        is_single_file_mode = (button == self.project_selector.file_radio)
        self.stage_toggles.set_single_file_mode(is_single_file_mode)
        
        # Log the mode change
        mode_name = "Single File" if is_single_file_mode else "Directory"
        self.log_panel.add_message("info", f"Selection mode changed to: {mode_name}")
    
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
            # Ensure progress dialog shows error state
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="Pipeline failed to start")
            self._set_running_state(False)
    
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
    
    def _on_configuration_changed(self) -> None:
        """Handle configuration changes that might affect layout."""
        # Use a timer to update scroll after layout changes have been processed
        QTimer.singleShot(50, self._update_scroll_after_layout_change)
    
    def _update_scroll_after_layout_change(self) -> None:
        """Update scroll area after layout changes."""
        # Update the scrollable widget's size
        self.scrollable_widget.updateGeometry()
        self.scroll_area.updateGeometry()
        
        # If any configuration panels are now visible, ensure they're in view
        if hasattr(self.stage_configurators, 'get_visible_configurators'):
            visible_configurators = self.stage_configurators.get_visible_configurators()
            if visible_configurators:
                # Ensure the first visible configurator is in view
                first_visible = visible_configurators[0]
                self.ensure_widget_visible(first_visible)
    
    def _update_project_dependent_ui(self, path: str) -> None:
        """Update UI elements that depend on project selection."""
        has_selection = bool(path)
        
        # Enable/disable relevant UI elements
        self.stage_toggles.setEnabled(has_selection)
        self.stage_configurators.setEnabled(has_selection)
        
        if has_selection:
            # Determine if it's a directory or file
            from pathlib import Path
            path_obj = Path(path)
            if path_obj.is_dir():
                self.status_bar.showMessage(f"Project: {path}")
            else:
                self.status_bar.showMessage(f"File: {path_obj.name}")
            
            # Update configurators with project path
            # For single files, use parent directory for configurators
            from pathlib import Path
            config_path = Path(path)
            if config_path.is_file():
                self.stage_configurators.set_project_directory(str(config_path.parent))
            else:
                self.stage_configurators.set_project_directory(path)
        else:
            self.status_bar.showMessage("No project selected")
    
    def _update_stage_dependent_ui(self, stages: dict) -> None:
        """Update UI elements that depend on stage selection."""
        has_enabled_stages = any(stages.values())
        
        # Enable/disable run button - check for either directory or file selection
        has_selection = bool(self.project_selector.get_selected_path())
        self.action_buttons.set_run_enabled(has_selection and has_enabled_stages)
    
    def _validate_configuration(self) -> bool:
        """Validate current configuration before running."""
        # Check if project/file is selected
        selected_path = self.project_selector.get_selected_path()
        if not selected_path:
            if self.project_selector.is_file_mode():
                QMessageBox.warning(
                    self, self.tr("No File Selected"),
                    self.tr("Please select a file before running.")
                )
            else:
                QMessageBox.warning(
                    self, self.tr("No Project Selected"),
                    self.tr("Please select a project directory before running.")
                )
            return False
        
        # Check if at least one stage is enabled
        stages = self.stage_toggles.get_enabled_stages()
        if not any(stages.values()):
            QMessageBox.warning(
                self, self.tr("No Stages Enabled"),
                self.tr("Please enable at least one processing stage.")
            )
            return False
        
        # Validate stage configurations
        validation_result = self.stage_configurators.validate_configurations(stages)
        if not validation_result.is_valid:
            QMessageBox.warning(
                self, self.tr("Configuration Error"),
                self.tr("Configuration validation failed:\n\n{0}").format(validation_result.error_message)
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
            self.status_bar.showMessage(self.tr("Processing..."))
            # Clear previous results
            self.results_panel.clear()
        else:
            self.status_bar.showMessage(self.tr("Ready"))
    
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
            self._settings_dialog.language_change_requested.connect(self._on_language_change_requested)
        
        self._settings_dialog._load_current_settings()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()
    
    def _show_calibration_dialog(self) -> None:
        """Open the Calibrate Model dialog, pre-filled from the current translate settings."""
        from app.dialogs.calibration_dialog import CalibrationDialog

        translate_settings = self.stage_configurators.get_translate_config()
        dialog = CalibrationDialog(
            model          = translate_settings.get("model", ""),
            provider       = translate_settings.get("provider", ""),
            api_key        = translate_settings.get("api_key", ""),
            config_manager = self.config_manager,
            parent         = self,
        )
        dialog.calibration_saved.connect(self._on_calibration_saved)
        dialog.show()

    def _on_calibration_saved(self, model: str) -> None:
        """Refresh the calibration indicator in the translate widget after calibration."""
        self.log_panel.add_message("info", f"Calibration saved for model: {model}")
        if hasattr(self.stage_configurators, "translate_config"):
            self.stage_configurators.translate_config._update_cal_status()

    def _check_dependencies(self) -> None:
        """Check for required dependencies."""
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(self.config_manager, self)
            self._settings_dialog.settings_applied.connect(self._on_settings_applied)
            self._settings_dialog.language_change_requested.connect(self._on_language_change_requested)

        # Show settings dialog on Tools tab and refresh detection
        self._settings_dialog.show_tab("tools")
        self._settings_dialog.refresh_tool_detection()

    def _show_video_preview(self) -> None:
        """Show video preview dialog with subtitle selection."""
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path

        # Select video file
        selected_path = self.project_selector.get_selected_path()
        video_file, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select Video File"),
            selected_path or "",
            self.tr("Video Files (*.mkv *.mp4 *.avi *.mov *.wmv *.flv);;All Files (*)")
        )

        if not video_file:
            return

        # Find subtitle files in the same directory with the same base name
        video_path = Path(video_file)
        subtitle_dir = video_path.parent
        base_name = video_path.stem

        # Look for subtitle files
        subtitle_files = []
        for pattern in ['*.srt', '*.ass', '*.ssa', '*.sub']:
            for sub_file in subtitle_dir.glob(pattern):
                # Match files with same base name or base name + language code
                if sub_file.stem == base_name or sub_file.stem.startswith(f"{base_name}."):
                    subtitle_files.append(str(sub_file))

        # If no subtitles found, allow user to manually select
        if not subtitle_files:
            reply = QMessageBox.question(
                self,
                self.tr("No Subtitles Found"),
                self.tr("No subtitle files were found for this video.\n\nWould you like to select subtitle files manually?"),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )

            if reply == QMessageBox.Yes:
                subtitle_files, _ = QFileDialog.getOpenFileNames(
                    self,
                    self.tr("Select Subtitle Files"),
                    str(subtitle_dir),
                    self.tr("Subtitle Files (*.srt *.ass *.ssa *.sub);;All Files (*)")
                )

        # Open video preview dialog
        dialog = VideoPreviewDialog(video_file, subtitle_files, self)
        dialog.show()

    def _on_find_subtitles_clicked(self) -> None:
        """Open the Find Subtitles dialog for the selected directory."""
        from app.dialogs.find_subtitles_dialog import FindSubtitlesDialog

        selected_path = self.project_selector.get_selected_path()
        if not selected_path:
            QMessageBox.warning(
                self,
                self.tr("No Selection"),
                self.tr("Please select a project directory first.")
            )
            return

        from pathlib import Path
        if not Path(selected_path).is_dir():
            QMessageBox.warning(
                self,
                self.tr("Directory Required"),
                self.tr("Please select a directory (not a single file) to use Find Subtitles.")
            )
            return

        dialog = FindSubtitlesDialog(selected_path, self.config_manager, self)
        dialog.exec()

    def _on_preview_clicked(self) -> None:
        """Handle preview button click from action buttons."""
        from pathlib import Path
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QListWidget, QDialogButtonBox, QLabel

        selected_path = self.project_selector.get_selected_path()
        if not selected_path:
            QMessageBox.warning(
                self,
                self.tr("No Selection"),
                self.tr("Please select a project directory or video file first.")
            )
            return

        path_obj = Path(selected_path)

        # If it's a file, preview it directly
        if path_obj.is_file():
            if path_obj.suffix.lower() in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv']:
                self._preview_video_file(str(path_obj))
            else:
                QMessageBox.warning(
                    self,
                    self.tr("Invalid File"),
                    self.tr("Selected file is not a supported video format.")
                )
            return

        # If it's a directory, show video selection dialog
        video_files = []
        for pattern in ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv']:
            video_files.extend(path_obj.glob(pattern))

        if not video_files:
            QMessageBox.information(
                self,
                self.tr("No Videos Found"),
                self.tr("No video files found in the selected directory.")
            )
            return

        # Show selection dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("Select Video to Preview"))
        dialog.setMinimumSize(500, 400)

        layout = QVBoxLayout(dialog)

        label = QLabel(self.tr("Select a video file to preview:"))
        layout.addWidget(label)

        list_widget = QListWidget()
        for video_file in sorted(video_files):
            list_widget.addItem(video_file.name)
        list_widget.setCurrentRow(0)  # Select first item by default
        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)

        if dialog.exec() == QDialog.Accepted:
            selected_index = list_widget.currentRow()
            if selected_index >= 0:
                selected_video = sorted(video_files)[selected_index]
                self._preview_video_file(str(selected_video))

    def _preview_video_file(self, video_path: str) -> None:
        """Preview a specific video file with auto-detected subtitles."""
        from pathlib import Path

        video_path_obj = Path(video_path)
        subtitle_dir = video_path_obj.parent
        base_name = video_path_obj.stem

        # Look for subtitle files
        subtitle_files = []
        for pattern in ['*.srt', '*.ass', '*.ssa', '*.sub']:
            for sub_file in subtitle_dir.glob(pattern):
                # Match files with same base name or base name + language code
                if sub_file.stem == base_name or sub_file.stem.startswith(f"{base_name}."):
                    subtitle_files.append(str(sub_file))

        # Open video preview dialog
        dialog = VideoPreviewDialog(video_path, subtitle_files, self)
        dialog.show()
    
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
    
    def _on_language_change_requested(self, language_code: str) -> None:
        """Handle language change request from settings dialog."""
        # Get the main application instance and delegate to it
        app = QApplication.instance()
        if hasattr(app, 'handle_language_change'):
            app.handle_language_change(language_code)
        else:
            # Fallback: direct restart notification
            from PySide6.QtWidgets import QMessageBox
            from app.i18n.language_utils import get_language_display_names
            
            lang_names = get_language_display_names()
            lang_name = lang_names.get(language_code, language_code)
            reply = QMessageBox.question(
                self,
                self.tr("Restart Required"),
                self.tr("Language changed to {0}.\n\nThe application needs to restart to apply the new language.\n\nPlease restart the application manually.").format(lang_name),
                QMessageBox.Ok
            )
            
            # Save the setting anyway
            ui_settings = self.config_manager.get_settings("ui")
            ui_settings["interface_language"] = language_code
            self.config_manager.update_settings("ui", ui_settings, save=True)
    
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
            self, self.tr("About SubtitleToolkit"),
            self.tr("SubtitleToolkit v1.0.0\n\n"
                   "A comprehensive desktop application for subtitle processing.\n\n"
                   "Features:\n"
                   "• Extract subtitles from MKV files\n"
                   "• Translate SRT files using AI\n"
                   "• Intelligently sync subtitle filenames\n\n"
                   "Built with PySide6 and Qt6")
        )
    
    def retranslateUi(self) -> None:
        """Retranslate UI elements when language changes."""
        # This method would be called after translation files are loaded
        # to update all UI text. However, since we restart the app for language
        # changes, this is mainly for reference and future use.
        self.setWindowTitle(self.tr("SubtitleToolkit"))
        
        # The UI components will automatically get new translations
        # when they are recreated on app restart
        pass
    
    def closeEvent(self, event) -> None:
        """Handle application close event."""
        # Check if processing is running
        if self.script_runner.is_running:
            reply = QMessageBox.question(
                self, self.tr("Confirm Exit"),
                self.tr("Processing is currently running. Are you sure you want to exit?"),
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
    
    def _show_progress_dialog(self, stages: list) -> None:
        """Show the inline processing banner and start progress tracking."""
        self.processing_banner.start_processing(stages)

    def _on_progress_dialog_cancel(self) -> None:
        """Handle cancel request from the processing banner."""
        if self.script_runner.is_running:
            self.script_runner.cancel_current_process()
            self.log_panel.add_message("info", "Processing cancellation requested")

    def _connect_runner_signals(self) -> None:
        """Connect ScriptRunner signals to UI handlers."""
        signals = self.script_runner.signals

        # Process lifecycle signals
        signals.process_started.connect(self._on_process_started)
        signals.process_finished.connect(self._on_process_finished)
        signals.process_failed.connect(self._on_process_failed)
        signals.process_cancelled.connect(self._on_process_cancelled)

        # Event signals from JSONL stream
        signals.debug_received.connect(self._on_debug_received)
        signals.info_received.connect(self._on_info_received)
        signals.info_data_received.connect(self._on_info_data_received)
        signals.progress_updated.connect(self._on_progress_updated)
        signals.warning_received.connect(self._on_warning_received)
        signals.error_received.connect(self._on_error_received)
        signals.result_received.connect(self._on_result_received)
    
    def _start_processing_pipeline(self) -> None:
        """Start the processing pipeline based on enabled stages."""
        stages = self.stage_toggles.get_enabled_stages()
        selected_path = self.project_selector.get_selected_path()

        if not selected_path:
            raise ValueError("No project or file selected")

        self.log_panel.add_message("info", "Starting processing pipeline...")
        self._set_running_state(True)

        # Create and show progress dialog
        enabled_stage_list = [stage for stage, enabled in stages.items() if enabled]
        self._show_progress_dialog(enabled_stage_list)

        # Start with the first enabled stage
        if stages.get('extract', False):
            self._run_extract_stage()
        elif stages.get('fps_sync', False):
            self._run_fps_sync_stage()
        elif stages.get('translate', False):
            self._run_translate_stage()
        elif stages.get('sync', False):
            self._run_sync_stage()
    
    def _run_extract_stage(self) -> None:
        """Run the extraction stage."""
        try:
            config = self._build_extract_config()

            # Pre-flight: check write permission on output directory
            import os
            from pathlib import Path
            _out_dir = config.output_directory or config.input_directory
            if _out_dir and not os.access(str(_out_dir), os.W_OK):
                from PySide6.QtWidgets import QFileDialog
                new_dir = QFileDialog.getExistingDirectory(
                    self,
                    self.tr("Output directory is not writable — choose another directory"),
                    str(_out_dir),
                )
                if not new_dir:
                    return
                config.output_directory = new_dir

            self.script_runner.run_extract(config)
        except Exception as e:
            error_msg = f"Failed to start extraction: {str(e)}"
            self.log_panel.add_message("error", error_msg)
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="Extract stage failed to start")
            self._set_running_state(False)
            # Re-raise so caller knows the stage failed
            raise RuntimeError(error_msg) from e
    
    def _run_fps_sync_stage(self) -> None:
        """Run the FPS frame-rate conversion stage."""
        try:
            config = self._build_fps_sync_config()
            self.script_runner.run_fps_sync(config)
        except Exception as e:
            error_msg = f"Failed to start FPS conversion: {str(e)}"
            self.log_panel.add_message("error", error_msg)
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="FPS sync stage failed to start")
            self._set_running_state(False)
            raise RuntimeError(error_msg) from e

    def _run_translate_stage(self) -> None:
        """Run the translation stage."""
        try:
            config = self._build_translate_config()

            # Warn if source and target language appear to be the same
            source = config.source_language or ''
            target = config.target_language or ''
            if source.lower() != 'auto' and source.strip() and target.strip():
                if source.strip().lower()[:2] == target.strip().lower()[:2]:
                    reply = QMessageBox.question(
                        self,
                        self.tr("Same Language Warning"),
                        self.tr(
                            f"Source and target language appear to be the same "
                            f"({source} \u2192 {target}). This will translate without "
                            f"changing language, which is usually not intended. Proceed anyway?"
                        ),
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No,
                    )
                    if reply == QMessageBox.No:
                        return

            # Pre-flight: check write permission on translation output directory
            import os
            from pathlib import Path
            _translate_out_dir = config.output_directory
            if not _translate_out_dir:
                # Fall back to directory of first input file or input_directory
                if config.input_files:
                    _translate_out_dir = str(Path(config.input_files[0]).parent)
                elif config.input_directory:
                    _translate_out_dir = config.input_directory
            if _translate_out_dir and not os.access(str(_translate_out_dir), os.W_OK):
                from PySide6.QtWidgets import QFileDialog
                new_dir = QFileDialog.getExistingDirectory(
                    self,
                    self.tr("Output directory is not writable — choose another directory"),
                    str(_translate_out_dir),
                )
                if not new_dir:
                    return
                config.output_directory = new_dir

            self.script_runner.run_translate(config)
        except Exception as e:
            error_msg = f"Failed to start translation: {str(e)}"
            self.log_panel.add_message("error", error_msg)
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="Translate stage failed to start")
            self._set_running_state(False)
            # Re-raise so caller knows the stage failed
            raise RuntimeError(error_msg) from e
    
    def _run_sync_stage(self) -> None:
        """
        Run the sync stage with confirmation.

        This runs in two phases:
        1. Preview mode to get list of operations
        2. Show confirmation dialog
        3. If confirmed, execute the operations
        """
        try:
            # Phase 1: Run in preview mode first
            self.log_panel.add_message("info", "Running sync preview to get operations list...")

            # Build config with dry_run=True for preview
            config = self._build_sync_config()
            config.dry_run = True  # Force preview mode

            # Store the config for later use
            self._pending_sync_config = config

            # Connect to result signal to handle preview completion
            self.script_runner.signals.process_finished.disconnect()
            self.script_runner.signals.process_finished.connect(self._on_sync_preview_complete)

            # Run preview
            self.script_runner.run_sync(config)

        except Exception as e:
            import traceback
            error_msg = f"Failed to start sync: {str(e)}"
            error_details = traceback.format_exc()
            self.log_panel.add_message("error", error_msg)
            self.log_panel.add_message("debug", f"Sync error details:\n{error_details}")
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message=f"Sync failed: {str(e)}")
            self._set_running_state(False)
            # Re-raise so caller knows the stage failed
            raise RuntimeError(error_msg) from e

    def _on_sync_preview_complete(self, result) -> None:
        """Handle sync preview completion and show confirmation dialog."""
        # Reconnect normal handler
        self.script_runner.signals.process_finished.disconnect()
        self.script_runner.signals.process_finished.connect(self._on_process_finished)

        if not result.success:
            self.log_panel.add_message("error", "Sync preview failed")
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="Sync preview failed")
            self._set_running_state(False)
            return

        # Parse operations from result
        operations = self._parse_sync_operations(result)

        if not operations or all(op.get('action') == 'skip' for op in operations):
            # No operations to perform
            self.log_panel.add_message("info", "No files need to be renamed")
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=True, message="No operations needed")
            self._set_running_state(False)
            return

        # Show confirmation dialog
        confirmation_dialog = SyncConfirmationDialog(operations, self)

        # Hide banner temporarily while confirmation dialog is shown
        if self._progress_dialog:
            self._progress_dialog.hide()

        # Show confirmation
        if confirmation_dialog.exec() == SyncConfirmationDialog.Accepted:
            # User confirmed - execute the operations
            self.log_panel.add_message("info", "User confirmed sync operations, executing...")

            # Restore banner
            if self._progress_dialog:
                self._progress_dialog.show()
                self._progress_dialog.update_stage("sync", "Executing rename operations...")

            # Run with execute flag
            self._pending_sync_config.dry_run = False
            self.script_runner.run_sync(self._pending_sync_config)
        else:
            # User cancelled
            self.log_panel.add_message("info", "Sync operations cancelled by user")
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message="Cancelled by user")
            self._set_running_state(False)

    def _parse_sync_operations(self, result) -> List[Dict]:
        """
        Parse sync operations from the result data.

        Returns:
            List of operation dictionaries with action, from, to, reason
        """
        operations = []

        # The sync script returns operations in the result data under 'renames' key
        if hasattr(result, 'result_data') and result.result_data:
            renames = result.result_data.get('renames', [])

            for rename in renames:
                operations.append({
                    'action': rename.get('action', 'rename'),
                    'from_file': rename.get('from', ''),
                    'to_file': rename.get('to', ''),
                    'reason': rename.get('reason', ''),
                    'confidence': rename.get('confidence', 0.0)
                })

        # Also try to parse from output if result_data is empty
        if not operations and hasattr(result, 'output'):
            # Parse JSONL output for operations
            import json
            for line in result.output.splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    if event.get('type') in ['info', 'warning'] and 'data' in event:
                        data = event['data']
                        action = data.get('action')
                        if action in ['backup', 'rename', 'skip']:
                            operations.append({
                                'action': action,
                                'from_file': data.get('from', data.get('file', '')),
                                'to_file': data.get('to', data.get('target', '')),
                                'reason': data.get('reason', event.get('msg', ''))
                            })
                except json.JSONDecodeError:
                    continue

        return operations
    
    def _build_extract_config(self) -> ExtractConfig:
        """Build extraction configuration from UI settings."""
        selected_path = self.project_selector.get_selected_path()

        # Get configuration from stage configurators
        extract_settings = self.stage_configurators.get_extract_config()

        # Get tool paths from settings
        settings = self.config_manager.get_settings()
        tools_config = settings.get('tools', {})

        config = ExtractConfig(
            input_directory=selected_path,
            language_code=extract_settings.get('language_code', 'eng'),
            output_directory=extract_settings.get('output_directory'),
            track_indices=extract_settings.get('track_indices', []),
            recursive=extract_settings.get('recursive', True),
            overwrite_existing=extract_settings.get('overwrite_existing', False),
            ffmpeg_path=tools_config.get('ffmpeg_path') or None,
            ffprobe_path=tools_config.get('ffprobe_path') or None,
        )

        # Apply file filter if set
        filtered = self.project_selector.get_filtered_files()
        if filtered is not None:
            config.specific_files = filtered

        return config
    
    def _build_fps_sync_config(self) -> FpsSyncConfig:
        """Build FPS sync configuration from UI settings."""
        selected_path = self.project_selector.get_selected_path()
        fps_settings = self.stage_configurators.get_fps_sync_config()

        settings = self.config_manager.get_settings()
        tools_config = settings.get('tools', {})

        from pathlib import Path
        selected_path_obj = Path(selected_path)

        if selected_path_obj.is_file():
            if selected_path_obj.suffix.lower() == '.srt':
                input_files = [selected_path]
                input_directory = None
            else:
                input_files = []
                input_directory = str(selected_path_obj.parent)
        else:
            input_files = []
            input_directory = selected_path

        return FpsSyncConfig(
            input_files=input_files,
            input_directory=input_directory,
            source_fps=fps_settings.get('source_fps', 25.0),
            target_fps=fps_settings.get('target_fps'),
            auto_detect=fps_settings.get('auto_detect', False),
            output_directory=fps_settings.get('output_directory'),
            overwrite_existing=fps_settings.get('overwrite_existing', True),
            ffprobe_path=tools_config.get('ffprobe_path') or None,
        )

    def _build_translate_config(self) -> TranslateConfig:
        """Build translation configuration from UI settings."""
        selected_path = self.project_selector.get_selected_path()
        
        # Get configuration from stage configurators
        translate_settings = self.stage_configurators.get_translate_config()
        
        # Debug: Show what we got from stage configurators
        self.log_panel.add_message("debug", f"Stage configurator settings: {translate_settings}")
        
        # Get settings
        settings = self.config_manager.get_settings()
        translators_config = settings.get('translators', {})
        advanced_config = settings.get('advanced', {})
        
        provider = translate_settings.get('provider', 'openai')

        # Normalize provider name for settings lookup
        # Map script provider names to settings keys
        provider_to_settings = {
            'openai': 'openai',
            'claude': 'anthropic',  # Script uses 'claude', settings uses 'anthropic'
            'openrouter': 'openrouter',
            'local': 'lm_studio',  # Script uses 'local', settings uses 'lm_studio'
        }
        settings_provider = provider_to_settings.get(provider, provider)
        provider_config = translators_config.get(settings_provider, {})

        # Debug: Show what's in the config
        self.log_panel.add_message("debug", f"translators_config keys: {list(translators_config.keys())}")
        self.log_panel.add_message("debug", f"Looking for provider: {provider} (settings key: {settings_provider})")
        self.log_panel.add_message("debug", f"provider_config keys: {list(provider_config.keys())}")
        if 'api_key' in provider_config:
            masked = f"{provider_config['api_key'][:8]}***" if len(provider_config['api_key']) > 8 else "***"
            self.log_panel.add_message("debug", f"provider_config has api_key: {masked}")

        # Load API key with fallback to environment variables and .env files
        def get_api_key(provider: str) -> str:
            # First check UI field (from stage configurator)
            ui_api_key = translate_settings.get('api_key', '').strip()
            if ui_api_key:
                self.log_panel.add_message("debug", "Using API key from UI field")
                return ui_api_key

            # Then check settings (from Settings dialog)
            settings_api_key = provider_config.get('api_key', '').strip()
            self.log_panel.add_message("debug", f"Settings API key empty: {not bool(settings_api_key)}")
            if settings_api_key:
                self.log_panel.add_message("debug", "Using API key from Settings")
                return settings_api_key

            # Fallback to environment variables
            import os
            from dotenv import load_dotenv

            # Load .env file if it exists
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_file):
                load_dotenv(env_file)

            if provider in ['claude', 'anthropic']:
                env_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Using API key from environment variable")
                    return env_key
            elif provider == 'openai':
                env_key = os.getenv('OPENAI_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Using API key from environment variable")
                    return env_key
            elif provider == 'openrouter':
                env_key = os.getenv('OPENROUTER_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Using API key from environment variable")
                    return env_key

            return ''
        
        api_key = get_api_key(provider)
        
        # Debug: Show final API key (masked)
        if api_key:
            masked_key = f"{api_key[:8]}***{api_key[-4:]}" if len(api_key) > 12 else "***"
            self.log_panel.add_message("debug", f"Using API key: {masked_key} for provider: {provider}")
        else:
            self.log_panel.add_message("debug", f"No API key found for provider: {provider}")
        
        # Determine if single file or directory mode
        from pathlib import Path
        selected_path_obj = Path(selected_path)
        
        if selected_path_obj.is_file():
            # Single file mode - for translation, we need to find the corresponding SRT file
            # If this is called after extraction, look for the SRT file in the same directory
            _VIDEO_EXTS = {'.mkv', '.mp4', '.avi', '.mov', '.m4v', '.webm', '.ts', '.m2ts'}
            if selected_path_obj.suffix.lower() in _VIDEO_EXTS:
                # Look for corresponding SRT file from extraction
                srt_file = selected_path_obj.with_suffix('.srt')
                if srt_file.exists():
                    input_files = [str(srt_file)]
                else:
                    # SRT file doesn't exist yet - use directory mode to scan for SRT files
                    input_files = []
                    selected_path = str(selected_path_obj.parent)
            else:
                # It's already an SRT file
                input_files = [selected_path]
            
            if input_files:
                return TranslateConfig(
                    input_files=input_files,
                    output_directory=translate_settings.get('output_directory'),
                    source_language=translate_settings.get('source_language', 'auto'),
                    target_language=translate_settings.get('target_language', 'en'),
                    provider=provider,
                    model=translate_settings.get('model') or provider_config.get('default_model', ''),
                    api_key=api_key,
                    base_url=provider_config.get('base_url') if provider == 'lm_studio' else None,
                    max_workers=translate_settings.get('max_workers', 2),
                    chunk_size=translate_settings.get('chunk_size', 20),
                    temperature=provider_config.get('temperature', 0.3),
                    max_tokens=provider_config.get('max_tokens', 4096),
                    timeout=provider_config.get('timeout', 30),
                    overwrite_existing=translate_settings.get('overwrite_existing', False),
                    price_input=translate_settings.get('price_input', 0.0),
                    price_output=translate_settings.get('price_output', 0.0),
                )

        # Check for an active file filter in directory mode
        filtered = self.project_selector.get_filtered_files()
        if filtered is not None and self.project_selector.is_directory_mode():
            # Use the filtered list as explicit input files instead of scanning the directory
            return TranslateConfig(
                input_files=filtered,
                input_directory=None,
                output_directory=translate_settings.get('output_directory'),
                source_language=translate_settings.get('source_language', 'auto'),
                target_language=translate_settings.get('target_language', 'en'),
                provider=provider,
                model=translate_settings.get('model') or provider_config.get('default_model', ''),
                api_key=api_key,
                base_url=provider_config.get('base_url') if provider == 'lm_studio' else None,
                max_workers=translate_settings.get('max_workers', 2),
                chunk_size=translate_settings.get('chunk_size', 20),
                temperature=provider_config.get('temperature', 0.3),
                max_tokens=provider_config.get('max_tokens', 4096),
                timeout=provider_config.get('timeout', 30),
                overwrite_existing=translate_settings.get('overwrite_existing', False),
                price_input=translate_settings.get('price_input', 0.0),
                price_output=translate_settings.get('price_output', 0.0),
            )

        # Directory mode (or fallback for single file) - use input_directory
        return TranslateConfig(
            input_directory=selected_path,
            output_directory=translate_settings.get('output_directory'),
            source_language=translate_settings.get('source_language', 'auto'),
            target_language=translate_settings.get('target_language', 'en'),
            provider=provider,
            model=translate_settings.get('model') or provider_config.get('default_model', ''),
            api_key=api_key,
            base_url=provider_config.get('base_url') if provider == 'lm_studio' else None,
            max_workers=translate_settings.get('max_workers', 2),
            chunk_size=translate_settings.get('chunk_size', 20),
            temperature=provider_config.get('temperature', 0.3),
            max_tokens=provider_config.get('max_tokens', 4096),
            timeout=provider_config.get('timeout', 30),
            overwrite_existing=translate_settings.get('overwrite_existing', False),
            price_input=translate_settings.get('price_input', 0.0),
            price_output=translate_settings.get('price_output', 0.0),
        )
    
    def _build_sync_config(self) -> SyncConfig:
        """Build sync configuration from UI settings."""
        selected_path = self.project_selector.get_selected_path()

        # Sync requires a directory - if a file was selected, use its parent directory
        from pathlib import Path
        selected_path_obj = Path(selected_path)
        if selected_path_obj.is_file():
            sync_directory = str(selected_path_obj.parent)
            self.log_panel.add_message("debug", f"Sync: Using parent directory {sync_directory} (file was selected)")
        else:
            sync_directory = selected_path

        # Get configuration from stage configurators
        sync_settings = self.stage_configurators.get_sync_config()

        # Get settings
        settings = self.config_manager.get_settings()
        translators_config = settings.get('translators', {})

        # Check if we should use translate settings
        use_translate_settings = sync_settings.get('use_translate_settings', False)

        if use_translate_settings:
            # Use provider settings from translate stage
            translate_settings = self.stage_configurators.get_translate_config()
            provider = translate_settings.get('provider', 'openai')
            model = translate_settings.get('model', '')
            api_key = translate_settings.get('api_key', '')
        else:
            # Use sync-specific provider settings
            provider = sync_settings.get('provider', 'openai')
            model = sync_settings.get('model', '')
            api_key = sync_settings.get('api_key', '')

        # Get provider config from settings
        # Map script provider names to settings keys
        provider_to_settings = {
            'openai': 'openai',
            'claude': 'anthropic',  # Script uses 'claude', settings uses 'anthropic'
            'openrouter': 'openrouter',
            'local': 'lm_studio',  # Script uses 'local', settings uses 'lm_studio'
        }
        settings_provider = provider_to_settings.get(provider, provider)
        provider_config = translators_config.get(settings_provider, {})

        # Load API key with fallback logic
        def get_sync_api_key(provider: str, ui_api_key: str) -> str:
            # First check UI-provided key (strip whitespace)
            ui_key_clean = ui_api_key.strip() if ui_api_key else ''
            if ui_key_clean:
                self.log_panel.add_message("debug", "Sync using API key from UI field")
                return ui_key_clean

            # Then check settings
            settings_key = provider_config.get('api_key', '').strip()
            if settings_key:
                self.log_panel.add_message("debug", "Sync using API key from Settings")
                return settings_key

            # Fallback to environment variables
            import os
            from dotenv import load_dotenv

            # Load .env file if it exists
            env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
            if os.path.exists(env_file):
                load_dotenv(env_file)

            if provider in ['claude', 'anthropic']:
                env_key = os.getenv('ANTHROPIC_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Sync using API key from environment")
                    return env_key
            elif provider == 'openai':
                env_key = os.getenv('OPENAI_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Sync using API key from environment")
                    return env_key
            elif provider == 'openrouter':
                env_key = os.getenv('OPENROUTER_API_KEY', '').strip()
                if env_key:
                    self.log_panel.add_message("debug", "Sync using API key from environment")
                    return env_key

            return ''

        # Get final model (with fallback to default)
        final_model = model or provider_config.get('default_model', '')

        return SyncConfig(
            input_directory=sync_directory,
            provider=provider,
            model=final_model,
            confidence_threshold=sync_settings.get('confidence_threshold', 0.8),
            language_filter=sync_settings.get('language_filter', ''),
            api_key=get_sync_api_key(provider, api_key),
            dry_run=sync_settings.get('dry_run', True),
            auto_backup_existing=sync_settings.get('auto_backup_existing', True),
            recursive=sync_settings.get('recursive', True),
            naming_template=sync_settings.get('naming_template', "{show_title} - S{season:02d}E{episode:02d} - {episode_title}"),
        )
    
    # ScriptRunner signal handlers
    def _on_process_started(self, stage: Stage) -> None:
        """Handle process started signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("info", f"{stage_name} stage started")

        # Update progress dialog
        if self._progress_dialog:
            self._progress_dialog.update_stage(stage.value, f"Starting {stage_name.lower()}...")
            self._progress_dialog.update_progress(0, stage.value, f"Starting {stage_name.lower()}...")
            self._progress_dialog.add_log_message("info", f"{stage_name} stage started")
    
    def _on_process_finished(self, result) -> None:  # result is ProcessResult
        """Handle process finished signal."""
        stage_name = result.stage.value.capitalize()
        
        if result.success:
            self.log_panel.add_message("info",
                f"{stage_name} stage completed successfully in {result.duration_seconds:.1f}s")

            # Update progress dialog
            if self._progress_dialog:
                self._progress_dialog.update_progress(100, result.stage.value, f"{stage_name} completed")
                self._progress_dialog.add_log_message("success", f"{stage_name} completed in {result.duration_seconds:.1f}s")

            # Update results panel
            if result.output_files:
                for output_file in result.output_files:
                    if isinstance(output_file, dict):
                        file_path = output_file.get('output_file', str(output_file))
                    else:
                        file_path = str(output_file)
                    self.results_panel.add_result(
                        file_path=file_path,
                        result_type=result.stage.value,
                        status="success",
                        message=f"{result.stage.value.capitalize()} completed successfully"
                    )
            
            # Check if we need to run next stage
            self._check_next_stage(result.stage, result)
        else:
            error_msg = result.error_message or f"Process failed with exit code {result.exit_code}"
            self.log_panel.add_message("error", f"{stage_name} stage failed: {error_msg}")

            # Update progress dialog
            if self._progress_dialog:
                self._progress_dialog.stop_processing(success=False, message=f"{stage_name} failed: {error_msg}")
                self._progress_dialog.add_log_message("error", error_msg)

            self._set_running_state(False)
    
    def _on_process_failed(self, stage: Stage, error_message: str) -> None:
        """Handle process failed signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("error", f"{stage_name} stage failed: {error_message}")

        # Update progress dialog
        if self._progress_dialog:
            self._progress_dialog.stop_processing(success=False, message=f"{stage_name} failed: {error_message}")
            self._progress_dialog.add_log_message("error", error_message)

        self._set_running_state(False)
    
    def _on_process_cancelled(self, stage: Stage) -> None:
        """Handle process cancelled signal."""
        stage_name = stage.value.capitalize()
        self.log_panel.add_message("info", f"{stage_name} stage cancelled")

        # Update progress dialog
        if self._progress_dialog:
            self._progress_dialog.stop_processing(success=False, message=f"{stage_name} cancelled")
            self._progress_dialog.add_log_message("warning", f"{stage_name} cancelled")

        self._set_running_state(False)
    
    def _on_debug_received(self, stage: Stage, message: str) -> None:
        """Handle debug message from process."""
        self.log_panel.add_message("debug", message)
        if self._progress_dialog:
            self._progress_dialog.add_log_message("debug", message)

    def _on_info_received(self, stage: Stage, message: str) -> None:
        """Handle info message from process."""
        self.log_panel.add_message("info", message)
        if self._progress_dialog:
            self._progress_dialog.add_log_message("info", message)

    def _on_info_data_received(self, stage: Stage, data: dict) -> None:
        """Handle info event with structured data. Used to surface translation stats in the UI."""
        if stage == Stage.TRANSLATE and 'api_calls_ok' in data:
            self.results_panel.show_translate_stats(data)

    def _on_progress_updated(self, stage: Stage, progress: int, message: str) -> None:
        """Handle progress update from process."""
        if self._progress_dialog:
            self._progress_dialog.update_progress(progress, stage.value, message)
    
    def _on_warning_received(self, stage: Stage, message: str) -> None:
        """Handle warning message from process."""
        self.log_panel.add_message("warning", message)
        if self._progress_dialog:
            self._progress_dialog.add_log_message("warning", message)

    def _on_error_received(self, stage: Stage, message: str) -> None:
        """Handle error message from process."""
        self.log_panel.add_message("error", message)
        if self._progress_dialog:
            self._progress_dialog.add_log_message("error", message)
    
    def _on_result_received(self, stage: Stage, data: dict) -> None:
        """Handle result data from process."""
        # Determine validation status for the results panel
        vr = data.get('validation')
        if vr is not None:
            if vr.get('valid') and not vr.get('warnings'):
                val_status = "success"
            elif vr.get('valid'):
                val_status = "warning"
            else:
                val_status = "error"
        else:
            val_status = "success"
            vr = None

        # Extract useful information from result data
        if 'outputs' in data:
            for output_file in data['outputs']:
                if isinstance(output_file, dict):
                    file_path = output_file.get('output_file', str(output_file))
                else:
                    file_path = str(output_file)

                if vr is not None:
                    stats = vr.get('stats', {})
                    n = vr.get('subtitle_count', 0)
                    nerr = len(vr.get('errors', []))
                    nwarn = len(vr.get('warnings', []))
                    dur = stats.get('duration_seconds', 0)
                    if val_status == "success":
                        val_msg = f"{n} subtitles · {dur:.0f}s · OK"
                    elif val_status == "warning":
                        val_msg = f"{n} subtitles · {nwarn} warning(s)"
                    else:
                        val_msg = f"{nerr} validation error(s)"
                    result_msg = f"{stage.value.capitalize()} result  [{val_msg}]"
                else:
                    result_msg = f"{stage.value.capitalize()} result"

                self.results_panel.add_result(
                    file_path=file_path,
                    result_type=stage.value,
                    status=val_status,
                    message=result_msg
                )

        # Log summary information
        if 'files_processed' in data:
            files_processed = data['files_processed']
            files_successful = data.get('files_successful', 0)
            self.log_panel.add_message("info",
                f"Processed {files_processed} files, {files_successful} successful")
    
    def _check_next_stage(self, completed_stage: Stage, result=None) -> None:
        """Check if we need to run the next stage in the pipeline."""
        stages = self.stage_toggles.get_enabled_stages()

        try:
            # Determine next stage to run based on pipeline order:
            # EXTRACT → FPS_SYNC → TRANSLATE → SYNC
            if completed_stage == Stage.EXTRACT:
                if stages.get('fps_sync', False):
                    self._run_fps_sync_stage()
                elif stages.get('translate', False):
                    if result and hasattr(result, 'output_files') and result.output_files:
                        self._run_translate_stage()
                    else:
                        self.log_panel.add_message("warning", "Skipping translation stage - no subtitle files were extracted")
                        if stages.get('sync', False):
                            self._run_sync_stage()
                        else:
                            self.log_panel.add_message("info", "Processing pipeline completed")
                            if self._progress_dialog:
                                self._progress_dialog.stop_processing(success=True, message="Pipeline completed with warnings")
                            self._set_running_state(False)
                elif stages.get('sync', False):
                    self._run_sync_stage()
                else:
                    self.log_panel.add_message("info", "Processing pipeline completed")
                    if self._progress_dialog:
                        self._progress_dialog.stop_processing(success=True, message="Pipeline completed successfully")
                    self._set_running_state(False)

            elif completed_stage == Stage.FPS_SYNC:
                if stages.get('translate', False):
                    self._run_translate_stage()
                elif stages.get('sync', False):
                    self._run_sync_stage()
                else:
                    self.log_panel.add_message("info", "Processing pipeline completed")
                    if self._progress_dialog:
                        self._progress_dialog.stop_processing(success=True, message="Pipeline completed successfully")
                    self._set_running_state(False)

            elif completed_stage == Stage.TRANSLATE and stages.get('sync', False):
                self._run_sync_stage()

            else:
                # Pipeline complete
                self.log_panel.add_message("info", "Processing pipeline completed")
                if self._progress_dialog:
                    self._progress_dialog.stop_processing(success=True, message="Pipeline completed successfully")
                self._set_running_state(False)
        except Exception as e:
            # Stage failed to start - error already logged and progress stopped by _run_*_stage methods
            # Nothing more to do, just catch the exception to prevent crash
            pass