#!/usr/bin/env python3
"""
Quick test to verify the GUI launches properly without keeping it open.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_gui_launch():
    """Test that the GUI can be imported and initialized."""
    try:
        print("🔄 Testing GUI launch...")
        
        # Enable High DPI support
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QTimer
        from app.main import main, SubtitleToolkitApp
        
        print("✅ All imports successful")
        
        # Create application instance
        app = SubtitleToolkitApp([])
        print("✅ Application created successfully")
        
        # Create main window
        main_window = app.main_window
        print("✅ Main window created successfully")
        
        # Check window properties
        print(f"✅ Window title: {main_window.windowTitle()}")
        print(f"✅ Window size: {main_window.size().width()}x{main_window.size().height()}")
        
        # Schedule app to quit after 100ms
        QTimer.singleShot(100, app.quit)
        
        print("✅ Starting event loop (will exit automatically)...")
        result = app.exec()
        
        print("✅ Application closed successfully")
        print("🎉 GUI launch test PASSED!")
        
        return True
        
    except Exception as e:
        print(f"❌ GUI launch test FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_gui_launch()
    sys.exit(0 if success else 1)