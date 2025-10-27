#!/usr/bin/env python3
"""
Test translation contexts to see why tr() calls aren't working.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set environment for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_translation_contexts():
    """Test different translation contexts."""
    try:
        print("🌍 Testing Translation Contexts...")
        
        from PySide6.QtWidgets import QApplication, QWidget, QPushButton
        from PySide6.QtCore import QTranslator, QCoreApplication
        from app.config.config_manager import ConfigManager
        from app.i18n import TranslationManager
        
        # Create application with proper names
        app = QApplication([])
        app.setApplicationName("SubtitleToolkit")
        app.setOrganizationName("SubtitleToolkit")
        app.setOrganizationDomain("subtitletoolkit.local")
        
        # Load Bulgarian translations
        tm = TranslationManager(app)
        success = tm.load_language("bg")
        print(f"✓ Bulgarian loading success: {success}")
        
        # Test different translation methods
        print(f"\n🔧 Testing different tr() methods:")
        
        # Method 1: QApplication.tr()
        app_tr = app.tr("Run")
        print(f"✓ app.tr('Run'): '{app_tr}'")
        
        # Method 2: QCoreApplication.translate() with context
        core_tr = QCoreApplication.translate("MainWindow", "Run")
        print(f"✓ QCoreApplication.translate('MainWindow', 'Run'): '{core_tr}'")
        
        # Method 3: Test other contexts
        for context in ["SettingsDialog", "ActionButtons"]:
            context_tr = QCoreApplication.translate(context, "Run")
            print(f"✓ QCoreApplication.translate('{context}', 'Run'): '{context_tr}'")
        
        # Method 4: Create a widget and test its tr()
        class TestWidget(QWidget):
            def test_tr(self):
                return self.tr("Run")
        
        widget = TestWidget()
        widget_tr = widget.test_tr()
        print(f"✓ widget.tr('Run'): '{widget_tr}'")
        
        # Method 5: Test other strings
        for text in ["Cancel", "Extract Subtitles", "Settings"]:
            core_tr = QCoreApplication.translate("MainWindow", text)
            print(f"✓ QCoreApplication.translate('MainWindow', '{text}'): '{core_tr}'")
        
        return True
        
    except Exception as e:
        print(f"✗ Translation context test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_translation_contexts()