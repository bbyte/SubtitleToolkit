#!/usr/bin/env python3
"""
Test script for window state persistence functionality.

This script can be used to test the WindowStateManager independently
and verify that window geometry persistence works correctly.
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTextEdit
from PySide6.QtCore import QTimer

from app.config.config_manager import ConfigManager
from app.window_state_manager import WindowStateManager, WindowGeometry


class TestMainWindow(QMainWindow):
    """Test window for window state persistence."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Window State Test")
        self.setMinimumSize(600, 400)
        
        # Create config manager
        self.config_manager = ConfigManager(self)
        
        # Create window state manager
        self.window_state_manager = WindowStateManager(self, self.config_manager, self)
        
        # Connect signals for debugging
        self.window_state_manager.state_saved.connect(self._on_state_saved)
        self.window_state_manager.state_restored.connect(self._on_state_restored)
        self.window_state_manager.validation_failed.connect(self._on_validation_failed)
        
        # Create UI
        self._create_ui()
        
        # Try to restore window state
        if not self.window_state_manager.restore_window_state():
            self.resize(800, 600)
            self._log("No saved window state found. Using default size.")
        
        # Show current geometry info
        self._show_current_geometry()
    
    def _create_ui(self):
        """Create the test UI."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("Window State Persistence Test")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Instructions
        instructions = QLabel(
            "Test window state persistence by:\n"
            "1. Moving and resizing this window\n"
            "2. Maximizing/restoring the window\n"
            "3. Closing and reopening the application\n"
            "4. The window should return to its last position and size"
        )
        instructions.setStyleSheet("margin: 10px; padding: 10px; background-color: #f0f0f0;")
        layout.addWidget(instructions)
        
        # Control buttons
        button_layout = QVBoxLayout()
        
        save_button = QPushButton("Save Window State Now")
        save_button.clicked.connect(self.window_state_manager.save_window_state)
        button_layout.addWidget(save_button)
        
        reset_button = QPushButton("Reset to Default")
        reset_button.clicked.connect(self.window_state_manager.reset_to_defaults)
        button_layout.addWidget(reset_button)
        
        geometry_button = QPushButton("Show Current Geometry")
        geometry_button.clicked.connect(self._show_current_geometry)
        button_layout.addWidget(geometry_button)
        
        layout.addLayout(button_layout)
        
        # Log area
        self.log_area = QTextEdit()
        self.log_area.setMaximumHeight(200)
        layout.addWidget(self.log_area)
        
        layout.addStretch()
    
    def _log(self, message: str):
        """Add a message to the log area."""
        self.log_area.append(f"[{QTimer().currentTime().toString()}] {message}")
    
    def _on_state_saved(self, geometry: WindowGeometry):
        """Handle state saved signal."""
        self._log(f"Window state saved: {geometry.width}x{geometry.height} at ({geometry.x}, {geometry.y}) "
                 f"[Max: {geometry.is_maximized}, Min: {geometry.is_minimized}]")
    
    def _on_state_restored(self, geometry: WindowGeometry):
        """Handle state restored signal."""
        self._log(f"Window state restored: {geometry.width}x{geometry.height} at ({geometry.x}, {geometry.y}) "
                 f"[Max: {geometry.is_maximized}, Min: {geometry.is_minimized}]")
    
    def _on_validation_failed(self, error_message: str):
        """Handle validation failed signal."""
        self._log(f"Validation failed: {error_message}")
    
    def _show_current_geometry(self):
        """Show current window geometry in the log."""
        geometry = self.window_state_manager._get_current_geometry()
        self._log(f"Current geometry: {geometry.width}x{geometry.height} at ({geometry.x}, {geometry.y}) "
                 f"[Max: {geometry.is_maximized}, Min: {geometry.is_minimized}]")
        
        # Also show screen info
        screens = QApplication.screens()
        for i, screen in enumerate(screens):
            screen_geom = screen.geometry()
            self._log(f"Screen {i}: {screen_geom.width()}x{screen_geom.height()} at ({screen_geom.x()}, {screen_geom.y()})")
    
    def closeEvent(self, event):
        """Handle close event."""
        self._log("Closing application - saving final window state...")
        self.window_state_manager.cleanup()
        event.accept()


def main():
    """Main function to run the test."""
    app = QApplication(sys.argv)
    
    # Create and show the test window
    window = TestMainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()