#!/usr/bin/env python3
"""
Debug config loading to see why interface_language is being reset.
"""

import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def debug_config_loading():
    """Debug the config loading process."""
    print("🔧 Debug Config Loading Process...")
    
    try:
        from app.config.config_manager import ConfigManager
        
        # Create config manager
        config = ConfigManager()
        
        # Get the config file path
        config_file = config.get_config_file_path()
        print(f"✓ Config file path: {config_file}")
        
        # Read raw file content
        with open(config_file, 'r', encoding='utf-8') as f:
            raw_content = f.read()
        
        print(f"✓ Raw file contains 'interface_language': {'interface_language' in raw_content}")
        
        # Parse JSON manually
        raw_data = json.loads(raw_content)
        ui_section = raw_data.get('ui', {})
        raw_interface_lang = ui_section.get('interface_language', 'NOT_FOUND')
        print(f"✓ Raw JSON interface_language: {raw_interface_lang}")
        
        # Get through ConfigManager
        ui_settings = config.get_settings("ui")
        cm_interface_lang = ui_settings.get('interface_language', 'NOT_FOUND')
        print(f"✓ ConfigManager interface_language: {cm_interface_lang}")
        
        # Check if they match
        if raw_interface_lang == cm_interface_lang:
            print("✅ Raw JSON and ConfigManager match!")
        else:
            print("❌ Mismatch between raw JSON and ConfigManager!")
            print(f"   Raw: {raw_interface_lang}")
            print(f"   ConfigManager: {cm_interface_lang}")
        
        # Test the loading process step by step
        print("\n🔍 Testing loading process...")
        config2 = ConfigManager()  # Create a fresh instance
        ui_settings2 = config2.get_settings("ui")
        cm2_interface_lang = ui_settings2.get('interface_language', 'NOT_FOUND')
        print(f"✓ Fresh ConfigManager interface_language: {cm2_interface_lang}")
        
        return True
        
    except Exception as e:
        print(f"✗ Debug config loading failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    debug_config_loading()