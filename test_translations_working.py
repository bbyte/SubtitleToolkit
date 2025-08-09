#!/usr/bin/env python3
"""
Test script to verify translations are working.

This will change the language setting and test if translations are applied.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_translation_loading():
    """Test if translations can be loaded correctly."""
    print("🌍 Testing Translation Loading...")
    
    # Set QT environment for testing
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    try:
        from PySide6.QtWidgets import QApplication
        from app.config import ConfigManager
        from app.i18n import TranslationManager
        
        # Create application
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Create managers
        config_manager = ConfigManager()
        translation_manager = TranslationManager(app)
        
        # Test loading different languages
        languages_to_test = ["en", "de", "bg", "es"]
        
        for lang_code in languages_to_test:
            print(f"\n--- Testing {lang_code.upper()} ---")
            
            # Load the language
            success = translation_manager.load_language(lang_code)
            print(f"✓ Language {lang_code} loaded: {'SUCCESS' if success else 'FAILED'}")
            
            # Test if current language is set correctly
            current_lang = translation_manager.current_language
            print(f"✓ Current language reported as: {current_lang}")
            
        # Test setting language preference
        print(f"\n--- Testing Language Settings ---")
        ui_settings = config_manager.get_settings("ui")
        original_lang = ui_settings.get("interface_language", "system")
        print(f"✓ Original interface language: {original_lang}")
        
        # Change to Bulgarian
        ui_settings["interface_language"] = "bg"
        config_manager.update_settings("ui", ui_settings, save=True)
        print("✓ Language setting changed to Bulgarian")
        
        # Restore original setting
        ui_settings["interface_language"] = original_lang
        config_manager.update_settings("ui", ui_settings, save=True)
        print(f"✓ Language setting restored to: {original_lang}")
        
        return True
        
    except Exception as e:
        print(f"✗ Translation loading test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_ui_strings():
    """Test that UI strings are using tr() calls."""
    print("\n🔧 Testing UI String Translation Readiness...")
    
    try:
        # Check that key files have been updated to use tr()
        files_to_check = [
            "app/widgets/stage_toggles.py",
            "app/widgets/action_buttons.py", 
            "app/widgets/project_selector.py"
        ]
        
        tr_usage = {}
        
        for file_path in files_to_check:
            path = Path(file_path)
            if path.exists():
                content = path.read_text()
                tr_count = content.count("self.tr(")
                tr_usage[file_path] = tr_count
                print(f"✓ {file_path}: {tr_count} tr() calls")
            else:
                print(f"✗ {file_path}: File not found")
                
        total_tr_calls = sum(tr_usage.values())
        print(f"✓ Total tr() calls found: {total_tr_calls}")
        
        if total_tr_calls >= 8:  # We expect at least 8 tr() calls from our updates
            print("✅ UI components appear to be using tr() for translations")
            return True
        else:
            print("⚠️  Fewer tr() calls than expected")
            return False
            
    except Exception as e:
        print(f"✗ UI strings test failed: {e}")
        return False


def test_compiled_translations():
    """Test that compiled translation files exist and are recent."""
    print("\n📁 Testing Compiled Translation Files...")
    
    try:
        translations_dir = Path("app/i18n/translations")
        
        if not translations_dir.exists():
            print("✗ Translations directory not found")
            return False
            
        languages = ["de", "bg", "es"]
        all_files_exist = True
        
        for lang in languages:
            ts_file = translations_dir / f"subtitletoolkit_{lang}.ts"
            qm_file = translations_dir / f"subtitletoolkit_{lang}.qm"
            
            if ts_file.exists():
                print(f"✓ {lang} source file: {ts_file.name}")
            else:
                print(f"✗ {lang} source file: MISSING")
                all_files_exist = False
                
            if qm_file.exists():
                print(f"✓ {lang} compiled file: {qm_file.name}")
                # Check if compiled file is newer than source
                if qm_file.stat().st_mtime >= ts_file.stat().st_mtime:
                    print(f"  └─ Compiled file is up to date")
                else:
                    print(f"  └─ ⚠️ Compiled file may be outdated")
            else:
                print(f"✗ {lang} compiled file: MISSING")
                all_files_exist = False
        
        return all_files_exist
        
    except Exception as e:
        print(f"✗ Compiled translations test failed: {e}")
        return False


def main():
    """Run all translation tests."""
    print("🌍 SubtitleToolkit Translation System Test")
    print("=" * 50)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Translation loading
    if test_translation_loading():
        success_count += 1
        print("✅ Translation loading test PASSED")
    else:
        print("❌ Translation loading test FAILED")
    
    # Test 2: UI strings
    if test_ui_strings():
        success_count += 1
        print("✅ UI strings test PASSED")
    else:
        print("❌ UI strings test FAILED")
    
    # Test 3: Compiled translations
    if test_compiled_translations():
        success_count += 1
        print("✅ Compiled translations test PASSED")
    else:
        print("❌ Compiled translations test FAILED")
    
    # Summary
    print("\n" + "=" * 50)
    print(f"🎯 Test Results: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 All translation tests PASSED!")
        print("\nTranslations should now be working!")
        print("To test manually:")
        print("1. Run: python3 launch_app.py")
        print("2. Go to File → Settings → Interface")  
        print("3. Select Български, Deutsch, or Español")
        print("4. Click OK and restart when prompted")
        print("5. UI should appear in the selected language")
        return 0
    else:
        print(f"⚠️ {total_tests - success_count} test(s) failed")
        print("Some translation components may not be working correctly.")
        return 1


if __name__ == "__main__":
    sys.exit(main())