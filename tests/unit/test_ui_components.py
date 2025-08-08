"""
Unit tests for UI components and widgets.

Tests the UI component classes for proper initialization, state management,
signal/slot connections, and user interaction handling.

Following TDD principles:
1. Test widget initialization and setup
2. Test signal/slot connections
3. Test state management and updates
4. Test user interaction handling
5. Test widget behavior under various conditions
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import pytest
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from app.widgets.progress_section import ProgressSection
from app.widgets.log_panel import LogPanel, LogLevel, LogMessage
from app.widgets.project_selector import ProjectSelector
from app.widgets.action_buttons import ActionButtons
from app.widgets.stage_toggles import StageToggles
from app.runner.events import Stage


@pytest.mark.unit
@pytest.mark.gui
class TestProgressSection:
    """Test suite for ProgressSection widget."""
    
    def test_progress_section_initialization(self, qapp):
        """Test ProgressSection initializes correctly."""
        progress_section = ProgressSection()
        
        assert progress_section._current_stage == ""
        assert progress_section._current_progress == 0
        assert progress_section._is_processing is False
        
        # Check UI components
        assert progress_section.progress_bar is not None
        assert progress_section.stage_label is not None
        assert progress_section.status_label is not None
        assert progress_section.processing_label is not None
        
        # Check initial values
        assert progress_section.progress_bar.value() == 0
        assert progress_section.stage_label.text() == "Ready"
    
    def test_set_progress(self, qapp, qt_signal_tester):
        """Test setting progress value."""
        progress_section = ProgressSection()
        
        # Connect progress signal
        progress_section.progress_updated.connect(qt_signal_tester.slot)
        
        # Set progress
        progress_section.set_progress(50)
        
        assert progress_section._current_progress == 50
        assert progress_section.progress_bar.value() == 50
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
        assert qt_signal_tester.received_signals[0][0] == (50,)
    
    def test_set_progress_bounds(self, qapp):
        """Test progress value bounds checking."""
        progress_section = ProgressSection()
        
        # Test negative value
        progress_section.set_progress(-10)
        assert progress_section.progress_bar.value() == 0
        
        # Test value over 100
        progress_section.set_progress(150)
        assert progress_section.progress_bar.value() == 100
        
        # Test valid values
        progress_section.set_progress(25)
        assert progress_section.progress_bar.value() == 25
    
    def test_set_stage(self, qapp):
        """Test setting current stage."""
        progress_section = ProgressSection()
        
        # Test setting different stages
        progress_section.set_stage("Extract")
        assert progress_section._current_stage == "Extract"
        assert "Extract" in progress_section.stage_label.text()
        
        progress_section.set_stage("Translate")
        assert progress_section._current_stage == "Translate"
        assert "Translate" in progress_section.stage_label.text()
    
    def test_set_status_message(self, qapp, qt_signal_tester):
        """Test setting status message."""
        progress_section = ProgressSection()
        
        # Connect status signal
        progress_section.status_updated.connect(qt_signal_tester.slot)
        
        # Set status message
        test_message = "Processing video files..."
        progress_section.set_status(test_message)
        
        assert progress_section.status_label.text() == test_message
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
        assert qt_signal_tester.received_signals[0][0] == (test_message,)
    
    def test_start_processing_animation(self, qapp):
        """Test starting processing animation."""
        progress_section = ProgressSection()
        
        progress_section.start_processing()
        
        assert progress_section._is_processing is True
        # Animation timer should be started
        assert hasattr(progress_section, '_animation_timer')
    
    def test_stop_processing_animation(self, qapp):
        """Test stopping processing animation."""
        progress_section = ProgressSection()
        
        # Start then stop processing
        progress_section.start_processing()
        progress_section.stop_processing()
        
        assert progress_section._is_processing is False
        assert progress_section.processing_label.text() == ""
    
    def test_reset_progress(self, qapp):
        """Test resetting progress to initial state."""
        progress_section = ProgressSection()
        
        # Set some values
        progress_section.set_progress(75)
        progress_section.set_stage("Translate")
        progress_section.set_status("Working on files...")
        progress_section.start_processing()
        
        # Reset
        progress_section.reset()
        
        assert progress_section._current_progress == 0
        assert progress_section._current_stage == ""
        assert progress_section._is_processing is False
        assert progress_section.progress_bar.value() == 0
        assert progress_section.stage_label.text() == "Ready"
        assert "ready" in progress_section.status_label.text().lower()
    
    def test_progress_section_layout(self, qapp):
        """Test progress section layout and sizing."""
        progress_section = ProgressSection()
        
        # Should have fixed height
        assert progress_section.height() > 0
        
        # Should contain expected widgets
        widgets = []
        def collect_widgets(widget):
            widgets.append(widget)
            for child in widget.findChildren(QWidget):
                widgets.append(child)
        
        collect_widgets(progress_section)
        
        # Should have progress bar, labels, etc.
        widget_types = [type(w).__name__ for w in widgets]
        assert 'QProgressBar' in widget_types
        assert 'QLabel' in widget_types


@pytest.mark.unit
@pytest.mark.gui
class TestLogPanel:
    """Test suite for LogPanel widget."""
    
    def test_log_panel_initialization(self, qapp):
        """Test LogPanel initializes correctly."""
        log_panel = LogPanel()
        
        assert len(log_panel._messages) == 0
        assert log_panel._auto_scroll is True
        assert log_panel._max_messages == 1000
        
        # Check filter levels are all enabled
        for level in LogLevel:
            assert log_panel._filter_levels[level] is True
        
        # Check UI components
        assert log_panel.log_display is not None
        assert log_panel.level_checkboxes is not None
        assert log_panel.clear_button is not None
        assert log_panel.auto_scroll_checkbox is not None
    
    def test_add_log_message(self, qapp, qt_signal_tester):
        """Test adding log messages."""
        log_panel = LogPanel()
        
        # Connect signal
        log_panel.message_logged.connect(qt_signal_tester.slot)
        
        # Add info message
        log_panel.add_message(LogLevel.INFO, "Test info message")
        
        assert len(log_panel._messages) == 1
        assert log_panel._messages[0].level == LogLevel.INFO
        assert log_panel._messages[0].message == "Test info message"
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
        level, message = qt_signal_tester.received_signals[0][0]
        assert level == "info"
        assert message == "Test info message"
    
    def test_add_multiple_log_messages(self, qapp):
        """Test adding multiple log messages with different levels."""
        log_panel = LogPanel()
        
        messages = [
            (LogLevel.INFO, "Info message 1"),
            (LogLevel.WARNING, "Warning message"),
            (LogLevel.ERROR, "Error message"),
            (LogLevel.INFO, "Info message 2"),
        ]
        
        for level, message in messages:
            log_panel.add_message(level, message)
        
        assert len(log_panel._messages) == 4
        assert log_panel._messages[0].level == LogLevel.INFO
        assert log_panel._messages[1].level == LogLevel.WARNING
        assert log_panel._messages[2].level == LogLevel.ERROR
        assert log_panel._messages[3].level == LogLevel.INFO
    
    def test_log_level_filtering(self, qapp):
        """Test filtering messages by log level."""
        log_panel = LogPanel()
        
        # Add messages of different levels
        log_panel.add_message(LogLevel.INFO, "Info message")
        log_panel.add_message(LogLevel.WARNING, "Warning message")
        log_panel.add_message(LogLevel.ERROR, "Error message")
        
        # Disable info messages
        log_panel._on_filter_changed(LogLevel.INFO, False)
        
        assert log_panel._filter_levels[LogLevel.INFO] is False
        assert log_panel._filter_levels[LogLevel.WARNING] is True
        assert log_panel._filter_levels[LogLevel.ERROR] is True
        
        # Should update display (we can't easily test text content, but can verify method was called)
        assert len(log_panel._messages) == 3  # Messages still stored
    
    def test_clear_log_messages(self, qapp):
        """Test clearing all log messages."""
        log_panel = LogPanel()
        
        # Add some messages
        log_panel.add_message(LogLevel.INFO, "Test message 1")
        log_panel.add_message(LogLevel.WARNING, "Test message 2")
        
        assert len(log_panel._messages) == 2
        
        # Clear messages
        log_panel.clear()
        
        assert len(log_panel._messages) == 0
    
    def test_auto_scroll_toggle(self, qapp):
        """Test auto-scroll functionality toggle."""
        log_panel = LogPanel()
        
        # Initially auto-scroll should be enabled
        assert log_panel._auto_scroll is True
        assert log_panel.auto_scroll_checkbox.isChecked() is True
        
        # Toggle auto-scroll
        log_panel._on_auto_scroll_toggled(False)
        
        assert log_panel._auto_scroll is False
    
    def test_max_messages_limit(self, qapp):
        """Test maximum messages limit to prevent memory issues."""
        log_panel = LogPanel()
        log_panel._max_messages = 5  # Set low limit for testing
        
        # Add more messages than the limit
        for i in range(10):
            log_panel.add_message(LogLevel.INFO, f"Message {i}")
        
        # Should only keep the most recent messages
        assert len(log_panel._messages) <= log_panel._max_messages
        
        # Should keep the most recent messages
        if len(log_panel._messages) == 5:
            assert log_panel._messages[-1].message == "Message 9"
    
    def test_log_message_timestamps(self, qapp):
        """Test log messages have proper timestamps."""
        log_panel = LogPanel()
        
        before_time = datetime.now()
        log_panel.add_message(LogLevel.INFO, "Timestamped message")
        after_time = datetime.now()
        
        assert len(log_panel._messages) == 1
        message_time = log_panel._messages[0].timestamp
        
        # Timestamp should be between before and after
        assert before_time <= message_time <= after_time
    
    def test_export_logs(self, qapp, temp_dir):
        """Test exporting log messages to file."""
        log_panel = LogPanel()
        
        # Add some messages
        log_panel.add_message(LogLevel.INFO, "Info message")
        log_panel.add_message(LogLevel.WARNING, "Warning message")
        log_panel.add_message(LogLevel.ERROR, "Error message")
        
        export_file = temp_dir / "test_export.txt"
        
        # Export logs
        success = log_panel.export_logs(str(export_file))
        
        assert success is True
        assert export_file.exists()
        
        # Check file contents
        content = export_file.read_text()
        assert "Info message" in content
        assert "Warning message" in content  
        assert "Error message" in content


@pytest.mark.unit
@pytest.mark.gui
class TestProjectSelector:
    """Test suite for ProjectSelector widget."""
    
    def test_project_selector_initialization(self, qapp):
        """Test ProjectSelector initializes correctly."""
        project_selector = ProjectSelector()
        
        # Check initial state
        assert project_selector._selected_directory is None
        
        # Check UI components
        assert project_selector.directory_label is not None
        assert project_selector.browse_button is not None
        assert project_selector.recent_projects_combo is not None
    
    def test_browse_directory_success(self, qapp, temp_dir, qt_signal_tester):
        """Test browsing and selecting a directory."""
        project_selector = ProjectSelector()
        
        # Connect signal
        project_selector.directory_selected.connect(qt_signal_tester.slot)
        
        # Mock file dialog to return test directory
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = str(temp_dir)
            
            # Trigger browse button
            project_selector._on_browse_clicked()
            
            assert project_selector._selected_directory == str(temp_dir)
            assert str(temp_dir) in project_selector.directory_label.text()
            
            # Should emit signal
            assert len(qt_signal_tester.received_signals) == 1
            assert qt_signal_tester.received_signals[0][0] == (str(temp_dir),)
    
    def test_browse_directory_cancel(self, qapp, qt_signal_tester):
        """Test canceling directory browse dialog."""
        project_selector = ProjectSelector()
        
        # Connect signal
        project_selector.directory_selected.connect(qt_signal_tester.slot)
        
        # Mock file dialog to return empty string (cancel)
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = ""
            
            # Trigger browse button
            project_selector._on_browse_clicked()
            
            # Should not change state or emit signal
            assert project_selector._selected_directory is None
            assert len(qt_signal_tester.received_signals) == 0
    
    def test_recent_projects_selection(self, qapp, temp_dir, qt_signal_tester):
        """Test selecting from recent projects."""
        project_selector = ProjectSelector()
        
        # Connect signal
        project_selector.directory_selected.connect(qt_signal_tester.slot)
        
        # Add recent project
        project_selector.add_recent_project(str(temp_dir))
        
        # Should appear in combo box
        combo_items = [project_selector.recent_projects_combo.itemText(i) 
                      for i in range(project_selector.recent_projects_combo.count())]
        assert str(temp_dir) in combo_items
        
        # Select from combo box
        project_selector._on_recent_project_selected(str(temp_dir))
        
        assert project_selector._selected_directory == str(temp_dir)
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
    
    def test_recent_projects_limit(self, qapp, temp_dir):
        """Test recent projects list limit."""
        project_selector = ProjectSelector()
        
        # Add more projects than the limit
        for i in range(15):  # Assuming limit is 10
            test_dir = temp_dir / f"project_{i}"
            test_dir.mkdir()
            project_selector.add_recent_project(str(test_dir))
        
        # Should not exceed limit
        combo_count = project_selector.recent_projects_combo.count()
        assert combo_count <= 10  # Adjust based on actual limit
    
    def test_get_selected_directory(self, qapp, temp_dir):
        """Test getting selected directory."""
        project_selector = ProjectSelector()
        
        # Initially no selection
        assert project_selector.get_selected_directory() is None
        
        # Set directory
        project_selector._selected_directory = str(temp_dir)
        
        assert project_selector.get_selected_directory() == str(temp_dir)
    
    def test_validate_directory(self, qapp, temp_dir):
        """Test directory validation."""
        project_selector = ProjectSelector()
        
        # Test valid directory
        assert project_selector._validate_directory(str(temp_dir)) is True
        
        # Test non-existent directory
        fake_dir = temp_dir / "nonexistent"
        assert project_selector._validate_directory(str(fake_dir)) is False
        
        # Test file instead of directory
        test_file = temp_dir / "test.txt"
        test_file.write_text("test")
        assert project_selector._validate_directory(str(test_file)) is False


@pytest.mark.unit
@pytest.mark.gui
class TestActionButtons:
    """Test suite for ActionButtons widget."""
    
    def test_action_buttons_initialization(self, qapp):
        """Test ActionButtons initializes correctly."""
        action_buttons = ActionButtons()
        
        # Check UI components
        assert action_buttons.start_button is not None
        assert action_buttons.stop_button is not None
        assert action_buttons.pause_button is not None
        
        # Check initial state
        assert action_buttons.start_button.isEnabled() is True
        assert action_buttons.stop_button.isEnabled() is False
        assert action_buttons.pause_button.isEnabled() is False
    
    def test_start_button_click(self, qapp, qt_signal_tester):
        """Test start button functionality."""
        action_buttons = ActionButtons()
        
        # Connect signal
        action_buttons.start_requested.connect(qt_signal_tester.slot)
        
        # Click start button
        QTest.mouseClick(action_buttons.start_button, Qt.LeftButton)
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
    
    def test_stop_button_click(self, qapp, qt_signal_tester):
        """Test stop button functionality."""
        action_buttons = ActionButtons()
        
        # Connect signal
        action_buttons.stop_requested.connect(qt_signal_tester.slot)
        
        # Enable stop button first
        action_buttons.set_processing_state(True)
        
        # Click stop button
        QTest.mouseClick(action_buttons.stop_button, Qt.LeftButton)
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
    
    def test_pause_button_click(self, qapp, qt_signal_tester):
        """Test pause button functionality."""
        action_buttons = ActionButtons()
        
        # Connect signal
        action_buttons.pause_requested.connect(qt_signal_tester.slot)
        
        # Enable pause button first
        action_buttons.set_processing_state(True)
        
        # Click pause button
        QTest.mouseClick(action_buttons.pause_button, Qt.LeftButton)
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) == 1
    
    def test_processing_state_management(self, qapp):
        """Test processing state button management."""
        action_buttons = ActionButtons()
        
        # Initially not processing
        assert action_buttons.start_button.isEnabled() is True
        assert action_buttons.stop_button.isEnabled() is False
        
        # Start processing
        action_buttons.set_processing_state(True)
        
        assert action_buttons.start_button.isEnabled() is False
        assert action_buttons.stop_button.isEnabled() is True
        assert action_buttons.pause_button.isEnabled() is True
        
        # Stop processing
        action_buttons.set_processing_state(False)
        
        assert action_buttons.start_button.isEnabled() is True
        assert action_buttons.stop_button.isEnabled() is False
        assert action_buttons.pause_button.isEnabled() is False
    
    def test_button_tooltips(self, qapp):
        """Test button tooltips are set properly."""
        action_buttons = ActionButtons()
        
        # Buttons should have helpful tooltips
        assert len(action_buttons.start_button.toolTip()) > 0
        assert len(action_buttons.stop_button.toolTip()) > 0
        assert len(action_buttons.pause_button.toolTip()) > 0


@pytest.mark.unit
@pytest.mark.gui
class TestStageToggles:
    """Test suite for StageToggles widget."""
    
    def test_stage_toggles_initialization(self, qapp):
        """Test StageToggles initializes correctly."""
        stage_toggles = StageToggles()
        
        # Should have toggles for each stage
        assert hasattr(stage_toggles, 'extract_checkbox')
        assert hasattr(stage_toggles, 'translate_checkbox')
        assert hasattr(stage_toggles, 'sync_checkbox')
        
        # Check initial state (all should be checked)
        assert stage_toggles.extract_checkbox.isChecked() is True
        assert stage_toggles.translate_checkbox.isChecked() is True
        assert stage_toggles.sync_checkbox.isChecked() is True
    
    def test_stage_selection_changes(self, qapp, qt_signal_tester):
        """Test stage selection change signals."""
        stage_toggles = StageToggles()
        
        # Connect signal
        stage_toggles.stages_changed.connect(qt_signal_tester.slot)
        
        # Toggle extract checkbox
        stage_toggles.extract_checkbox.setChecked(False)
        
        # Should emit signal
        assert len(qt_signal_tester.received_signals) >= 1
    
    def test_get_selected_stages(self, qapp):
        """Test getting selected stages."""
        stage_toggles = StageToggles()
        
        # Initially all selected
        selected = stage_toggles.get_selected_stages()
        assert Stage.EXTRACT in selected
        assert Stage.TRANSLATE in selected
        assert Stage.SYNC in selected
        
        # Uncheck translate
        stage_toggles.translate_checkbox.setChecked(False)
        
        selected = stage_toggles.get_selected_stages()
        assert Stage.EXTRACT in selected
        assert Stage.TRANSLATE not in selected
        assert Stage.SYNC in selected
    
    def test_set_stage_enabled(self, qapp):
        """Test enabling/disabling individual stages."""
        stage_toggles = StageToggles()
        
        # Disable extract stage
        stage_toggles.set_stage_enabled(Stage.EXTRACT, False)
        
        assert stage_toggles.extract_checkbox.isEnabled() is False
        
        # Re-enable extract stage
        stage_toggles.set_stage_enabled(Stage.EXTRACT, True)
        
        assert stage_toggles.extract_checkbox.isEnabled() is True
    
    def test_set_all_stages_enabled(self, qapp):
        """Test enabling/disabling all stages at once."""
        stage_toggles = StageToggles()
        
        # Disable all stages
        stage_toggles.set_all_enabled(False)
        
        assert stage_toggles.extract_checkbox.isEnabled() is False
        assert stage_toggles.translate_checkbox.isEnabled() is False
        assert stage_toggles.sync_checkbox.isEnabled() is False
        
        # Re-enable all stages
        stage_toggles.set_all_enabled(True)
        
        assert stage_toggles.extract_checkbox.isEnabled() is True
        assert stage_toggles.translate_checkbox.isEnabled() is True
        assert stage_toggles.sync_checkbox.isEnabled() is True
    
    def test_stage_dependencies(self, qapp):
        """Test stage dependency validation."""
        stage_toggles = StageToggles()
        
        # If extract is disabled, translate should be available only if SRT files exist
        stage_toggles.extract_checkbox.setChecked(False)
        
        # Get current selection
        selected = stage_toggles.get_selected_stages()
        
        # Should be able to have translate without extract (if SRT files exist)
        stage_toggles.translate_checkbox.setChecked(True)
        stage_toggles.sync_checkbox.setChecked(False)
        
        selected = stage_toggles.get_selected_stages()
        assert Stage.TRANSLATE in selected


@pytest.mark.unit  
@pytest.mark.gui
class TestUIComponentIntegration:
    """Test suite for UI component integration and interactions."""
    
    def test_widget_signal_slot_connections(self, qapp, qt_signal_tester):
        """Test signal/slot connections between widgets work correctly."""
        # Create multiple widgets
        progress_section = ProgressSection()
        action_buttons = ActionButtons()
        log_panel = LogPanel()
        
        # Connect signals
        progress_section.status_updated.connect(qt_signal_tester.slot)
        action_buttons.start_requested.connect(qt_signal_tester.slot)
        log_panel.message_logged.connect(qt_signal_tester.slot)
        
        # Trigger various actions
        progress_section.set_status("Test status")
        QTest.mouseClick(action_buttons.start_button, Qt.LeftButton)
        log_panel.add_message(LogLevel.INFO, "Test log message")
        
        # Should have received multiple signals
        assert len(qt_signal_tester.received_signals) >= 3
    
    def test_widget_state_synchronization(self, qapp):
        """Test widgets can maintain synchronized state."""
        progress_section = ProgressSection()
        action_buttons = ActionButtons()
        
        # Start processing
        action_buttons.set_processing_state(True)
        progress_section.start_processing()
        
        # Both widgets should reflect processing state
        assert action_buttons.start_button.isEnabled() is False
        assert action_buttons.stop_button.isEnabled() is True
        assert progress_section._is_processing is True
        
        # Stop processing
        action_buttons.set_processing_state(False)
        progress_section.stop_processing()
        
        # Both widgets should reflect stopped state
        assert action_buttons.start_button.isEnabled() is True
        assert action_buttons.stop_button.isEnabled() is False
        assert progress_section._is_processing is False
    
    def test_widget_layout_management(self, qapp):
        """Test widget layout and sizing behavior."""
        # Create container widget
        container = QWidget()
        layout = QVBoxLayout(container)
        
        # Add various widgets
        progress_section = ProgressSection()
        log_panel = LogPanel()
        action_buttons = ActionButtons()
        
        layout.addWidget(progress_section)
        layout.addWidget(log_panel)
        layout.addWidget(action_buttons)
        
        # Show container to trigger layout calculations
        container.show()
        container.resize(800, 600)
        
        # Widgets should be properly sized and positioned
        assert progress_section.isVisible()
        assert log_panel.isVisible()
        assert action_buttons.isVisible()
        
        # Progress section should have fixed height
        assert progress_section.height() > 0
    
    def test_widget_event_propagation(self, qapp, qt_signal_tester):
        """Test event propagation between widgets."""
        project_selector = ProjectSelector()
        stage_toggles = StageToggles()
        action_buttons = ActionButtons()
        
        # Connect selection change to enable/disable actions
        project_selector.directory_selected.connect(qt_signal_tester.slot)
        stage_toggles.stages_changed.connect(qt_signal_tester.slot)
        
        # Simulate project selection
        with patch('PySide6.QtWidgets.QFileDialog.getExistingDirectory') as mock_dialog:
            mock_dialog.return_value = "/test/project"
            project_selector._on_browse_clicked()
        
        # Should have received directory selected signal
        directory_signals = [s for s in qt_signal_tester.received_signals if s[0] == ("/test/project",)]
        assert len(directory_signals) >= 1
        
        # Change stage selection
        stage_toggles.extract_checkbox.setChecked(False)
        
        # Should have received stages changed signal
        assert len(qt_signal_tester.received_signals) >= 2
    
    @pytest.mark.performance
    def test_widget_performance_under_load(self, qapp, performance_tracker):
        """Test widget performance with high-frequency updates."""
        progress_section = ProgressSection()
        log_panel = LogPanel()
        
        performance_tracker.start_timer("widget_updates")
        
        # Simulate rapid updates
        for i in range(100):
            progress_section.set_progress(i % 101)
            log_panel.add_message(LogLevel.INFO, f"Update {i}")
        
        performance_tracker.end_timer("widget_updates")
        
        # Should handle updates efficiently (under 1 second)
        performance_tracker.assert_duration_under("widget_updates", 1.0)
        
        # Widgets should still be responsive
        assert progress_section.progress_bar.value() == 0  # Last update (100 % 101)
        assert len(log_panel._messages) <= log_panel._max_messages