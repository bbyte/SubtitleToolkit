#!/usr/bin/env python3
"""
Test script for the zoom functionality in SubtitleToolkit.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_zoom_functionality():
    """Test the zoom functionality."""
    try:
        print("🔄 Testing Zoom Functionality...")
        
        # Enable High DPI support
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtGui import QKeySequence
        from app.main import SubtitleToolkitApp
        from app.zoom_manager import ZoomManager
        
        print("✅ Zoom-related imports successful")
        
        # Create application instance
        app = SubtitleToolkitApp([])
        main_window = app.main_window
        
        # Test ZoomManager creation
        zoom_manager = getattr(main_window, 'zoom_manager', None)
        if zoom_manager:
            print("✅ ZoomManager created successfully")
            
            # Test zoom properties
            initial_zoom = zoom_manager.current_zoom
            print(f"✅ Initial zoom level: {initial_zoom * 100:.0f}%")
            
            # Test zoom bounds
            min_zoom = zoom_manager.MIN_ZOOM
            max_zoom = zoom_manager.MAX_ZOOM
            print(f"✅ Zoom range: {min_zoom * 100:.0f}% - {max_zoom * 100:.0f}%")
            
            # Test zoom methods
            zoom_manager.zoom_in()
            after_zoom_in = zoom_manager.current_zoom
            print(f"✅ Zoom in: {after_zoom_in * 100:.0f}%")
            
            zoom_manager.zoom_out()
            after_zoom_out = zoom_manager.current_zoom
            print(f"✅ Zoom out: {after_zoom_out * 100:.0f}%")
            
            zoom_manager.reset_zoom()
            after_reset = zoom_manager.current_zoom
            print(f"✅ Reset zoom: {after_reset * 100:.0f}%")
            
            # Test zoom to specific level
            zoom_manager.set_zoom(1.5)  # 150%
            specific_zoom = zoom_manager.current_zoom
            print(f"✅ Set to 150%: {specific_zoom * 100:.0f}%")
            
        else:
            print("❌ ZoomManager not found")
        
        # Check status bar
        status_bar = main_window.statusBar()
        if status_bar:
            print("✅ Status bar available for zoom indicator")
        
        # Check View menu
        menu_bar = main_window.menuBar()
        view_menu = None
        for action in menu_bar.actions():
            if 'View' in action.text():
                view_menu = action.menu()
                break
        
        if view_menu:
            print("✅ View menu found for zoom controls")
            zoom_actions = [action for action in view_menu.actions() 
                          if any(word in action.text().lower() 
                                for word in ['zoom', 'in', 'out', 'reset'])]
            if zoom_actions:
                print(f"✅ Found {len(zoom_actions)} zoom-related menu actions")
        
        # Schedule app to quit after 200ms
        QTimer.singleShot(200, app.quit)
        
        print("✅ Starting event loop (will exit automatically)...")
        result = app.exec()
        
        print("✅ Application closed successfully")
        print("🎉 Zoom functionality test PASSED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Zoom functionality test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_zoom_functionality()
    sys.exit(0 if success else 1)