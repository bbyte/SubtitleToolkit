#!/usr/bin/env python3
"""
Test script to verify the settings dialog works correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    """Test the settings dialog functionality."""
    print("🔧 Testing Settings Dialog Fix...")
    
    # Set QT environment for testing
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    try:
        from PySide6.QtWidgets import QApplication
        from app.config import ConfigManager
        from app.dialogs.settings_dialog import SettingsDialog
        
        # Create application
        app = QApplication(sys.argv) if not QApplication.instance() else QApplication.instance()
        
        # Create config manager
        config_manager = ConfigManager()
        
        # Create settings dialog (this was failing before)
        print("Creating settings dialog...")
        settings_dialog = SettingsDialog(config_manager)
        
        print("✅ Settings dialog created successfully!")
        print("✅ No AttributeError occurred!")
        print("✅ The currentDataChanged → currentIndexChanged fix worked!")
        
        # Check interface tab exists
        if 'interface' in settings_dialog._tabs:
            interface_tab = settings_dialog._tabs['interface']
            print("✅ Interface tab exists")
            
            # Check language combo
            if hasattr(interface_tab, 'language_combo'):
                combo = interface_tab.language_combo
                print(f"✅ Language combo has {combo.count()} options")
                
                # List available languages
                languages = []
                for i in range(combo.count()):
                    text = combo.itemText(i)
                    data = combo.itemData(i)
                    languages.append(f"{text} ({data})")
                
                print("✅ Available languages:")
                for lang in languages:
                    print(f"   - {lang}")
            
        settings_dialog.close()
        
        print("\n🎉 Settings dialog test PASSED!")
        print("You can now use File → Settings → Interface to change language!")
        
        return 0
        
    except Exception as e:
        print(f"❌ Settings dialog test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())