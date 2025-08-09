#!/usr/bin/env python3
"""
SubtitleToolkit Desktop Application

Main application entry point for the PySide6 desktop GUI.
Provides a user-friendly interface for the SubtitleToolkit CLI scripts.
"""

import sys
import os
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtCore import Qt, QDir
from PySide6.QtGui import QIcon, QPalette, QColor

# Add the project root to sys.path for script imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.main_window import MainWindow


class SubtitleToolkitApp(QApplication):
    """Main application class for SubtitleToolkit."""
    
    def __init__(self, argv: list[str]):
        super().__init__(argv)
        
        # Application properties
        self.setApplicationName("SubtitleToolkit")
        self.setApplicationVersion("1.0.0")
        self.setApplicationDisplayName("SubtitleToolkit")
        self.setOrganizationName("SubtitleToolkit")
        self.setOrganizationDomain("subtitletoolkit.local")
        
        # Set application icon if available
        self._set_application_icon()
        
        # Apply modern styling
        self._apply_modern_style()
        
        # Create main window
        self.main_window = MainWindow()
    
    def _set_application_icon(self) -> None:
        """Set the application icon if available."""
        icon_paths = [
            Path(__file__).parent / "resources" / "icon.png",
            Path(__file__).parent / "resources" / "icon.ico",
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break
    
    def _apply_modern_style(self) -> None:
        """Apply modern styling to the application."""
        # Use Fusion style for cross-platform consistency
        self.setStyle(QStyleFactory.create("Fusion"))
        
        # Create a modern dark palette
        palette = QPalette()
        
        # Base colors for dark theme
        base_color = QColor(53, 53, 53)
        alternate_base_color = QColor(66, 66, 66)
        tooltip_base_color = QColor(0, 0, 0)
        text_color = QColor(255, 255, 255)
        disabled_text_color = QColor(127, 127, 127)
        button_color = QColor(53, 53, 53)
        button_text_color = QColor(255, 255, 255)
        bright_text_color = QColor(255, 0, 0)
        link_color = QColor(42, 130, 218)
        highlight_color = QColor(42, 130, 218)
        highlighted_text_color = QColor(0, 0, 0)
        
        # Set palette colors
        palette.setColor(QPalette.Window, base_color)
        palette.setColor(QPalette.WindowText, text_color)
        palette.setColor(QPalette.Base, alternate_base_color)
        palette.setColor(QPalette.AlternateBase, base_color)
        palette.setColor(QPalette.ToolTipBase, tooltip_base_color)
        palette.setColor(QPalette.ToolTipText, text_color)
        palette.setColor(QPalette.Text, text_color)
        palette.setColor(QPalette.Button, button_color)
        palette.setColor(QPalette.ButtonText, button_text_color)
        palette.setColor(QPalette.BrightText, bright_text_color)
        palette.setColor(QPalette.Link, link_color)
        palette.setColor(QPalette.Highlight, highlight_color)
        palette.setColor(QPalette.HighlightedText, highlighted_text_color)
        
        # Set disabled colors
        palette.setColor(QPalette.Disabled, QPalette.WindowText, disabled_text_color)
        palette.setColor(QPalette.Disabled, QPalette.Text, disabled_text_color)
        palette.setColor(QPalette.Disabled, QPalette.ButtonText, disabled_text_color)
        
        self.setPalette(palette)
        
        # Additional stylesheet for modern appearance
        self.setStyleSheet("""
            QMainWindow {
                background-color: #353535;
            }
            
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            
            QPushButton {
                border: 2px solid #555;
                border-radius: 6px;
                background-color: #555;
                padding: 5px 15px;
                min-width: 80px;
                font-weight: bold;
            }
            
            QPushButton:hover {
                background-color: #666;
                border-color: #777;
            }
            
            QPushButton:pressed {
                background-color: #444;
                border-color: #333;
            }
            
            QPushButton:disabled {
                background-color: #333;
                border-color: #333;
                color: #777;
            }
            
            QProgressBar {
                border: 2px solid #555;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            
            QProgressBar::chunk {
                background-color: #2a82da;
                border-radius: 3px;
            }
            
            QTabWidget::pane {
                border: 1px solid #555;
                background-color: #424242;
            }
            
            QTabBar::tab {
                background-color: #555;
                border: 1px solid #666;
                padding: 8px 16px;
                margin-right: 2px;
            }
            
            QTabBar::tab:selected {
                background-color: #2a82da;
                border-color: #2a82da;
            }
            
            QTabBar::tab:hover {
                background-color: #666;
            }
            
            QComboBox {
                border: 2px solid #555;
                border-radius: 4px;
                padding: 4px;
                background-color: #424242;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            
            QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOCIgdmlld0JveD0iMCAwIDEyIDgiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDFMNiA2TDExIDEiIHN0cm9rZT0iI0ZGRkZGRiIgc3Ryb2tlLXdpZHRoPSIyIiBzdHJva2UtbGluZWNhcD0icm91bmQiIHN0cm9rZS1saW5lam9pbj0icm91bmQiLz4KPC9zdmc+);
            }
            
            QLineEdit, QTextEdit {
                border: 2px solid #555;
                border-radius: 4px;
                padding: 4px;
                background-color: #424242;
                selection-background-color: #2a82da;
            }
            
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            
            QCheckBox::indicator:unchecked {
                border: 2px solid #555;
                background-color: #424242;
                border-radius: 3px;
            }
            
            QCheckBox::indicator:checked {
                border: 2px solid #2a82da;
                background-color: #2a82da;
                border-radius: 3px;
            }
            
            QScrollBar:vertical {
                border: none;
                background-color: #424242;
                width: 12px;
                margin: 0;
            }
            
            QScrollBar::handle:vertical {
                background-color: #666;
                border-radius: 6px;
                min-height: 20px;
            }
            
            QScrollBar::handle:vertical:hover {
                background-color: #777;
            }
        """)
    
    def run(self) -> int:
        """Run the application."""
        self.main_window.show()
        return self.exec()


def main():
    """Main entry point."""
    # Enable High DPI support
    os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    
    # Create and run application
    app = SubtitleToolkitApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()