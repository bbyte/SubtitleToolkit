#!/usr/bin/env python3
"""
Basic test for internationalization functionality (no GUI required).

Tests core i18n components without requiring PySide6 to be available.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def test_language_utils():
    """Test language utility functions."""
    print("🔧 Testing Language Utils...")
    
    try:
        from app.i18n.language_utils import (
            LanguageCode, get_system_language, get_language_display_names,
            get_app_translation_file, get_qt_translation_file
        )
        
        # Test 1: Language codes
        available_codes = [code.value for code in LanguageCode]
        print(f"✓ Available language codes: {available_codes}")
        assert "en" in available_codes
        assert "de" in available_codes
        assert "bg" in available_codes
        assert "es" in available_codes
        
        # Test 2: System language detection
        system_lang = get_system_language()
        print(f"✓ System language: {system_lang}")
        assert system_lang in available_codes or system_lang == "system"
        
        # Test 3: Display names
        display_names = get_language_display_names()
        print(f"✓ Display names: {display_names}")
        assert "Български" in display_names.values()  # Bulgarian name
        
        # Test 4: Translation file names
        for lang in ["de", "bg", "es"]:
            app_file = get_app_translation_file(lang)
            qt_file = get_qt_translation_file(lang)
            print(f"✓ {lang}: app={app_file}, qt={qt_file}")
            assert f"subtitletoolkit_{lang}.qm" == app_file
            assert f"qt_{lang}.qm" == qt_file
        
        return True
        
    except Exception as e:
        print(f"✗ Language utils test failed: {e}")
        return False


def test_settings_schema():
    """Test settings schema for i18n support."""
    print("\n🔧 Testing Settings Schema...")
    
    try:
        from app.config.settings_schema import SettingsSchema
        
        # Test 1: Interface languages
        interface_langs = SettingsSchema.get_interface_languages()
        print(f"✓ Interface languages: {interface_langs}")
        assert "bg" in interface_langs
        assert interface_langs["bg"] == "Български"
        
        # Test 2: Supported subtitle languages
        subtitle_langs = SettingsSchema.get_supported_languages()
        print(f"✓ Supported subtitle languages count: {len(subtitle_langs)}")
        assert "bg" in subtitle_langs
        assert subtitle_langs["bg"] == "Bulgarian"
        
        # Test 3: Default settings structure
        defaults = SettingsSchema.get_default_settings()
        assert "ui" in defaults
        assert "interface_language" in defaults["ui"]
        print(f"✓ Default interface language: {defaults['ui']['interface_language']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Settings schema test failed: {e}")
        return False


def test_translation_files():
    """Test that translation files exist and are valid."""
    print("\n🔧 Testing Translation Files...")
    
    try:
        translations_dir = project_root / "app" / "i18n" / "translations"
        
        if not translations_dir.exists():
            print(f"✗ Translations directory does not exist: {translations_dir}")
            return False
        
        success_count = 0
        
        # Test each language
        for lang in ["de", "bg", "es"]:
            ts_file = translations_dir / f"subtitletoolkit_{lang}.ts"
            qm_file = translations_dir / f"subtitletoolkit_{lang}.qm"
            
            # Check .ts file
            if ts_file.exists():
                print(f"✓ {lang} .ts file exists")
                success_count += 1
                
                # Validate content
                content = ts_file.read_text(encoding='utf-8')
                if f'language="{lang}' in content and "<translation>" in content:
                    print(f"✓ {lang} .ts file has valid structure")
                else:
                    print(f"⚠ {lang} .ts file may have invalid structure")
            else:
                print(f"✗ {lang} .ts file missing")
            
            # Check .qm file
            if qm_file.exists():
                print(f"✓ {lang} .qm file exists")
                success_count += 1
            else:
                print(f"✗ {lang} .qm file missing (run compile_translations.py)")
        
        return success_count >= 6  # 3 languages × 2 file types
        
    except Exception as e:
        print(f"✗ Translation files test failed: {e}")
        return False


def test_config_integration():
    """Test configuration manager integration."""
    print("\n🔧 Testing Configuration Integration...")
    
    try:
        from app.config import ConfigManager
        
        config_manager = ConfigManager()
        
        # Test 1: Get UI settings
        ui_settings = config_manager.get_settings("ui")
        print(f"✓ UI settings loaded: {len(ui_settings)} keys")
        assert "interface_language" in ui_settings
        
        current_lang = ui_settings["interface_language"]
        print(f"✓ Current interface language: {current_lang}")
        
        # Test 2: Validate language setting
        valid_languages = ["system", "en", "de", "bg", "es"]
        assert current_lang in valid_languages
        print(f"✓ Interface language setting is valid")
        
        # Test 3: Get supported languages from schema
        from app.config.settings_schema import SettingsSchema
        supported = SettingsSchema.get_supported_languages()
        
        # Verify Bulgarian is in supported languages
        if "bg" in supported:
            print(f"✓ Bulgarian language supported: {supported['bg']}")
        else:
            print("✗ Bulgarian language not found in supported languages")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ Config integration test failed: {e}")
        return False


def main():
    """Run all basic i18n tests."""
    print("🌍 SubtitleToolkit I18N Basic Test")
    print("=" * 45)
    
    success_count = 0
    total_tests = 4
    
    # Test 1: Language Utils
    if test_language_utils():
        success_count += 1
        print("✅ Language utils test PASSED")
    else:
        print("❌ Language utils test FAILED")
    
    # Test 2: Settings Schema
    if test_settings_schema():
        success_count += 1
        print("✅ Settings schema test PASSED")
    else:
        print("❌ Settings schema test FAILED")
    
    # Test 3: Translation Files
    if test_translation_files():
        success_count += 1
        print("✅ Translation files test PASSED")
    else:
        print("❌ Translation files test FAILED")
    
    # Test 4: Config Integration
    if test_config_integration():
        success_count += 1
        print("✅ Config integration test PASSED")
    else:
        print("❌ Config integration test FAILED")
    
    # Summary
    print("\n" + "=" * 45)
    print(f"🎯 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All basic i18n tests PASSED!")
        print("\nCore i18n functionality verified:")
        print("- ✅ Language detection and utils")
        print("- ✅ Settings schema with Bulgarian support")
        print("- ✅ Translation files (German, Bulgarian, Spanish)")
        print("- ✅ Configuration integration")
        print("\nTo test full functionality:")
        print("1. Install dependencies: pip install -r requirements.txt")
        print("2. Run the desktop application: python3 launch_app.py")
        print("3. Go to File → Settings → Interface → Language")
        return 0
    else:
        print(f"⚠️ {total_tests - success_count} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())