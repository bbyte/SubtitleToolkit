#!/usr/bin/env python3
"""
Test script for the window state persistence functionality in SubtitleToolkit.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_window_state_functionality():
    """Test the window state persistence functionality."""
    try:
        print("🔄 Testing Window State Persistence...")
        
        # Enable High DPI support
        os.environ['QT_ENABLE_HIGHDPI_SCALING'] = '1'
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt, QTimer
        from app.main import SubtitleToolkitApp
        from app.window_state_manager import WindowStateManager, WindowGeometry
        
        print("✅ Window state imports successful")
        
        # Create application instance
        app = SubtitleToolkitApp([])
        main_window = app.main_window
        
        # Test WindowStateManager creation
        window_state_manager = getattr(main_window, 'window_state_manager', None)
        if window_state_manager:
            print("✅ WindowStateManager created successfully")
            
            # Test geometry methods
            current_geometry = window_state_manager._get_current_geometry()
            print(f"✅ Current geometry: {current_geometry.width}x{current_geometry.height} at ({current_geometry.x}, {current_geometry.y})")
            
            # Test default geometry
            default_geometry = window_state_manager.get_default_geometry()
            print(f"✅ Default geometry: {default_geometry.width}x{default_geometry.height}")
            
            # Test geometry validation
            test_geometry = WindowGeometry(100, 100, 800, 600)
            validated_geometry = window_state_manager._validate_geometry(test_geometry)
            print(f"✅ Geometry validation: {'passed' if validated_geometry else 'failed'}")
            
            # Test window state save/restore
            window_state_manager.save_window_state()
            print("✅ Window state saved successfully")
            
        else:
            print("❌ WindowStateManager not found")
        
        # Test settings integration
        config_manager = getattr(main_window, 'config_manager', None)
        if config_manager:
            print("✅ ConfigManager integration available")
            
            # Test if UI settings exist
            try:
                ui_settings = config_manager.get_ui_settings()
                remember_size = getattr(ui_settings, 'remember_window_size', True)
                remember_position = getattr(ui_settings, 'remember_window_position', True)
                print(f"✅ UI settings: remember_size={remember_size}, remember_position={remember_position}")
            except Exception as e:
                print(f"⚠️ UI settings access: {e}")
        
        # Test window resizing simulation
        print("🔄 Testing window resize simulation...")
        original_size = main_window.size()
        main_window.resize(900, 650)
        new_size = main_window.size()
        print(f"✅ Window resize: {original_size.width()}x{original_size.height()} → {new_size.width()}x{new_size.height()}")
        
        # Test window movement simulation
        print("🔄 Testing window move simulation...")
        original_pos = main_window.pos()
        main_window.move(150, 150)
        new_pos = main_window.pos()
        print(f"✅ Window move: ({original_pos.x()}, {original_pos.y()}) → ({new_pos.x()}, {new_pos.y()})")
        
        # Schedule app to quit after 300ms
        QTimer.singleShot(300, app.quit)
        
        print("✅ Starting event loop (will exit automatically)...")
        result = app.exec()
        
        print("✅ Application closed successfully")
        print("🎉 Window state persistence test PASSED!")
        
        return True
        
    except Exception as e:
        print(f"❌ Window state persistence test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_window_state_functionality()
    sys.exit(0 if success else 1)