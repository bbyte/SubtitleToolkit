#!/usr/bin/env python3
"""
Test what happens when the app starts up with Bulgarian settings.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_app_startup():
    """Test app startup with current settings."""
    try:
        print("🌍 Testing App Startup with Current Settings...")
        
        # Import after path setup
        from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
        from app.config.config_manager import ConfigManager
        from app.i18n import TranslationManager
        
        # Create application with proper names (like in main.py)
        app = QApplication([])
        app.setApplicationName("SubtitleToolkit")
        app.setOrganizationName("SubtitleToolkit")
        app.setOrganizationDomain("subtitletoolkit.local")
        
        # Check current language setting
        config = ConfigManager()
        config_file_path = config.get_config_file_path()
        print(f"✓ Config file path: {config_file_path}")
        
        ui_settings = config.get_settings("ui")
        interface_language = ui_settings.get("interface_language", "system")
        print(f"✓ Interface language setting: {interface_language}")
        print(f"✓ Full UI settings: {ui_settings}")
        
        # Load translations (simulating app startup)
        tm = TranslationManager(app)
        success = tm.load_language(interface_language)
        print(f"✓ Translation loading success: {success}")
        print(f"✓ Current language: {tm.current_language}")
        
        # Create a simple widget to test translations
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Test some translations that should exist
        test_label = QLabel()
        test_label.setText(app.tr("Run"))  # This should be "Стартирай" in Bulgarian
        layout.addWidget(test_label)
        
        print(f"✓ Translated 'Run' text: '{test_label.text()}'")
        
        # Check if translation is actually working
        if test_label.text() == "Run":
            print("⚠️  Translation not working - still showing English")
        else:
            print("✅ Translation working - showing translated text")
        
        return True
        
    except Exception as e:
        print(f"✗ App startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_app_startup()