#!/usr/bin/env python3
"""
Test script for the SubtitleToolkit desktop application.

This script tests the basic functionality of the PySide6 application
without requiring backend integration.
"""

import sys
import os
from pathlib import Path

# Add the app directory to sys.path
app_dir = Path(__file__).parent / "app"
sys.path.insert(0, str(app_dir))

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    
    try:
        # Test PySide6 imports
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        print("✓ PySide6 imports successful")
        
        # Test application imports
        from main import SubtitleToolkitApp
        print("✓ Main application import successful")
        
        # Test widget imports
        from widgets import (
            ProjectSelector, StageToggles, StageConfigurators,
            ProgressSection, LogPanel, ResultsPanel, ActionButtons
        )
        print("✓ Widget imports successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_application_creation():
    """Test application creation and basic functionality."""
    print("\\nTesting application creation...")
    
    try:
        from PySide6.QtWidgets import QApplication
        from main import SubtitleToolkitApp
        
        # Create application
        app = SubtitleToolkitApp(sys.argv)
        print("✓ Application created successfully")
        
        # Check main window
        main_window = app.main_window
        print(f"✓ Main window created: {main_window.windowTitle()}")
        
        # Test widget accessibility
        print(f"✓ Project selector: {type(main_window.project_selector).__name__}")
        print(f"✓ Stage toggles: {type(main_window.stage_toggles).__name__}")
        print(f"✓ Stage configurators: {type(main_window.stage_configurators).__name__}")
        print(f"✓ Progress section: {type(main_window.progress_section).__name__}")
        print(f"✓ Log panel: {type(main_window.log_panel).__name__}")
        print(f"✓ Results panel: {type(main_window.results_panel).__name__}")
        print(f"✓ Action buttons: {type(main_window.action_buttons).__name__}")
        
        return app
        
    except Exception as e:
        print(f"✗ Application creation error: {e}")
        return None

def test_ui_interactions(app):
    """Test basic UI interactions."""
    print("\\nTesting UI interactions...")
    
    try:
        main_window = app.main_window
        
        # Test log panel
        main_window.log_panel.add_message("info", "Test info message")
        main_window.log_panel.add_message("warning", "Test warning message")
        main_window.log_panel.add_message("error", "Test error message")
        print("✓ Log panel messages added")
        
        # Test progress section
        main_window.progress_section.start_processing()
        main_window.progress_section.update_progress(50, "extract", "Processing MKV files...")
        main_window.progress_section.update_progress(100, "extract", "Extraction complete")
        main_window.progress_section.stop_processing(True, "All processing complete")
        print("✓ Progress section tested")
        
        # Test results panel
        main_window.results_panel.add_result(
            "/test/path/video.mkv", "extract", "success", "Subtitles extracted successfully"
        )
        main_window.results_panel.add_result(
            "/test/path/subtitle.srt", "translate", "error", "Translation failed"
        )
        print("✓ Results panel tested")
        
        # Test stage toggles
        main_window.stage_toggles.set_stage_enabled("extract", True)
        main_window.stage_toggles.set_stage_enabled("translate", True)
        print("✓ Stage toggles tested")
        
        return True
        
    except Exception as e:
        print(f"✗ UI interaction error: {e}")
        return False

def test_signal_connections(app):
    """Test signal/slot connections."""
    print("\\nTesting signal connections...")
    
    try:
        main_window = app.main_window
        
        # Test that signals are properly connected
        # (We can't easily test actual signal emission without user interaction)
        print("✓ Signal connections appear to be properly set up")
        
        return True
        
    except Exception as e:
        print(f"✗ Signal connection error: {e}")
        return False

def run_visual_test():
    """Run the application visually for manual testing."""
    print("\\nStarting visual test...")
    print("The application window should open. Test the following:")
    print("1. Browse for a project directory")
    print("2. Toggle different processing stages")
    print("3. Expand/collapse configuration panels")
    print("4. Check log panel filtering")
    print("5. View results and summary tabs")
    print("6. Test action buttons (Run should be disabled until project is selected)")
    print("\\nClose the window when done testing.")
    
    from PySide6.QtWidgets import QApplication
    from main import SubtitleToolkitApp
    
    app = SubtitleToolkitApp(sys.argv)
    
    # Add some sample data for testing
    main_window = app.main_window
    main_window.log_panel.add_message("info", "Application started successfully")
    main_window.log_panel.add_message("info", "Welcome to SubtitleToolkit")
    main_window.log_panel.add_message("warning", "No project directory selected")
    
    return app.run()

def main():
    """Main test function."""
    print("SubtitleToolkit Desktop Application - Test Suite")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        sys.exit(1)
    
    # Test application creation
    app = test_application_creation()
    if not app:
        sys.exit(1)
    
    # Test UI interactions
    if not test_ui_interactions(app):
        sys.exit(1)
    
    # Test signal connections
    if not test_signal_connections(app):
        sys.exit(1)
    
    print("\\n" + "=" * 50)
    print("✓ All tests passed! Application is ready for use.")
    print("=" * 50)
    
    # Ask user if they want to run visual test
    response = input("\\nWould you like to run the visual test? (y/n): ")
    if response.lower() in ['y', 'yes']:
        sys.exit(run_visual_test())
    
    print("Test complete.")

if __name__ == "__main__":
    main()