#!/usr/bin/env python3
"""
Debug Qt application name settings and paths.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def debug_app_names():
    """Debug Qt application name and path differences."""
    try:
        print("🔧 Debug Qt Application Names and Paths...")
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import QStandardPaths
        
        # Test 1: Create app without setting names
        app1 = QApplication([])
        path1 = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        print(f"✓ Without app name - AppDataLocation: {path1}")
        print(f"✓ Application name: '{app1.applicationName()}'")
        print(f"✓ Organization name: '{app1.organizationName()}'")
        app1.quit()
        
        # Test 2: Create app with names set (like in main.py)
        app2 = QApplication([])
        app2.setApplicationName("SubtitleToolkit")
        app2.setOrganizationName("SubtitleToolkit")
        app2.setOrganizationDomain("subtitletoolkit.local")
        
        path2 = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        print(f"✓ With app name - AppDataLocation: {path2}")
        print(f"✓ Application name: '{app2.applicationName()}'")
        print(f"✓ Organization name: '{app2.organizationName()}'")
        
        # Show the difference
        if path1 != path2:
            print("❌ PATHS ARE DIFFERENT!")
            print(f"   Path without name: {path1}")
            print(f"   Path with name: {path2}")
        else:
            print("✅ Paths are the same")
        
        app2.quit()
        
        return True
        
    except Exception as e:
        print(f"✗ Debug app names failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_app_names()