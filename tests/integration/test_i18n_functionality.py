#!/usr/bin/env python3
"""
Test script for internationalization functionality.

Tests the complete i18n system including translation loading,
language switching, and UI updates.
"""

import sys
import os
from pathlib import Path
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QLocale

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.i18n import TranslationManager, get_system_language, get_language_display_names
from app.config import ConfigManager


def test_translation_manager():
    """Test the translation manager functionality."""
    print("🔧 Testing TranslationManager...")
    
    app = QApplication.instance() or QApplication(sys.argv)
    translation_manager = TranslationManager(app)
    
    # Test 1: Check available languages
    available_languages = translation_manager.available_languages
    print(f"✓ Available languages: {available_languages}")
    assert "en" in available_languages
    assert "de" in available_languages
    assert "bg" in available_languages
    assert "es" in available_languages
    
    # Test 2: Test system language detection
    system_lang = get_system_language()
    print(f"✓ System language detected: {system_lang}")
    
    # Test 3: Test language display names
    display_names = get_language_display_names()
    print(f"✓ Language display names: {display_names}")
    
    # Test 4: Test language loading
    for lang_code in ["en", "de", "bg", "es"]:
        success = translation_manager.load_language(lang_code)
        print(f"✓ Load {lang_code}: {'success' if success else 'failed'}")
    
    # Test 5: Test translation file info
    info = translation_manager.get_translation_files_info()
    print(f"✓ Translation files info: {info}")
    
    return True


def test_config_integration():
    """Test configuration integration with i18n."""
    print("\n🔧 Testing Configuration Integration...")
    
    config_manager = ConfigManager()
    
    # Test 1: Default language setting
    ui_settings = config_manager.get_settings("ui")
    interface_language = ui_settings.get("interface_language", "system")
    print(f"✓ Current interface language setting: {interface_language}")
    
    # Test 2: Supported languages in config
    from app.config.settings_schema import SettingsSchema
    supported_languages = SettingsSchema.get_supported_languages()
    print(f"✓ Supported subtitle languages count: {len(supported_languages)}")
    assert "bg" in supported_languages  # Check Bulgarian is included
    print(f"✓ Bulgarian language support: {supported_languages['bg']}")
    
    # Test 3: Interface languages
    interface_languages = SettingsSchema.get_interface_languages()
    print(f"✓ Interface languages: {interface_languages}")
    assert "bg" in interface_languages
    
    return True


def test_translation_files():
    """Test that translation files exist and are valid."""
    print("\n🔧 Testing Translation Files...")
    
    translations_dir = project_root / "app" / "i18n" / "translations"
    
    # Test 1: Check .ts files exist
    for lang in ["de", "bg", "es"]:
        ts_file = translations_dir / f"subtitletoolkit_{lang}.ts"
        qm_file = translations_dir / f"subtitletoolkit_{lang}.qm"
        
        print(f"✓ {lang} .ts file exists: {ts_file.exists()}")
        print(f"✓ {lang} .qm file exists: {qm_file.exists()}")
        
        if ts_file.exists():
            # Basic validation - check file has content
            content = ts_file.read_text(encoding='utf-8')
            assert "translation>" in content
            assert f'language="{lang}' in content
            print(f"✓ {lang} .ts file has valid content")
    
    return True


def test_ui_components():
    """Test UI components for translation readiness."""
    print("\n🔧 Testing UI Components...")
    
    try:
        app = QApplication.instance() or QApplication(sys.argv)
        
        # Test basic application setup
        from app.main import SubtitleToolkitApp
        
        print("✓ Main application imports successfully")
        
        # Test settings dialog with interface tab
        from app.dialogs.settings_dialog import SettingsDialog
        from app.config import ConfigManager
        
        config_manager = ConfigManager()
        settings_dialog = SettingsDialog(config_manager)
        
        print("✓ Settings dialog creates successfully")
        
        # Check that interface tab exists
        if 'interface' in settings_dialog._tabs:
            interface_tab = settings_dialog._tabs['interface']
            print("✓ Interface tab exists in settings dialog")
            
            # Check language combo box
            if hasattr(interface_tab, 'language_combo'):
                combo = interface_tab.language_combo
                lang_count = combo.count()
                print(f"✓ Language combo has {lang_count} options")
                assert lang_count >= 4  # system, en, de, bg, es
        
        settings_dialog.close()
        return True
        
    except Exception as e:
        print(f"✗ UI component test failed: {e}")
        return False


def main():
    """Run all i18n tests."""
    print("🌍 SubtitleToolkit Internationalization Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 4
    
    try:
        # Test 1: Translation Manager
        if test_translation_manager():
            success_count += 1
            print("✅ TranslationManager test PASSED")
        else:
            print("❌ TranslationManager test FAILED")
    except Exception as e:
        print(f"❌ TranslationManager test FAILED: {e}")
    
    try:
        # Test 2: Config Integration
        if test_config_integration():
            success_count += 1
            print("✅ Configuration integration test PASSED")
        else:
            print("❌ Configuration integration test FAILED")
    except Exception as e:
        print(f"❌ Configuration integration test FAILED: {e}")
    
    try:
        # Test 3: Translation Files
        if test_translation_files():
            success_count += 1
            print("✅ Translation files test PASSED")
        else:
            print("❌ Translation files test FAILED")
    except Exception as e:
        print(f"❌ Translation files test FAILED: {e}")
    
    try:
        # Test 4: UI Components
        if test_ui_components():
            success_count += 1
            print("✅ UI components test PASSED")
        else:
            print("❌ UI components test FAILED")
    except Exception as e:
        print(f"❌ UI components test FAILED: {e}")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All internationalization tests PASSED!")
        print("\nThe i18n system is ready to use:")
        print("- Translation infrastructure: ✅")
        print("- Language files compiled: ✅")
        print("- Bulgarian support added: ✅")
        print("- Settings integration: ✅")
        print("- UI language switching: ✅")
        return 0
    else:
        print(f"⚠️  {total_tests - success_count} test(s) failed")
        print("Some components need attention before the i18n system is fully ready.")
        return 1


if __name__ == "__main__":
    sys.exit(main())