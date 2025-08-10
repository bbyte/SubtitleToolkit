#!/usr/bin/env python3
"""
Quick test to see if Bulgarian translations load properly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set QT environment for testing
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

def test_bulgarian_loading():
    """Test Bulgarian translation loading."""
    try:
        from PySide6.QtWidgets import QApplication
        from app.config import ConfigManager
        from app.i18n import TranslationManager
        
        print("🌍 Testing Bulgarian Translation Loading...")
        
        # Create application
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Create managers
        config_manager = ConfigManager()
        translation_manager = TranslationManager(app)
        
        # Load Bulgarian specifically
        print(f"Loading Bulgarian translations...")
        success = translation_manager.load_language("bg")
        print(f"✓ Bulgarian loading success: {success}")
        
        # Check current language
        current_lang = translation_manager.current_language
        print(f"✓ Current language reported as: {current_lang}")
        
        # Check translation files info
        files_info = translation_manager.get_translation_files_info()
        print(f"✓ Available app translations: {files_info['available_app_translations']}")
        
        # Test if translation files exist
        translations_dir = Path("app/i18n/translations")
        bg_ts = translations_dir / "subtitletoolkit_bg.ts"
        bg_qm = translations_dir / "subtitletoolkit_bg.qm"
        
        print(f"✓ BG .ts file exists: {bg_ts.exists()}")
        print(f"✓ BG .qm file exists: {bg_qm.exists()}")
        
        if bg_qm.exists():
            print(f"✓ BG .qm file size: {bg_qm.stat().st_size} bytes")
            
        return True
        
    except Exception as e:
        print(f"✗ Bulgarian loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_bulgarian_loading()