#!/usr/bin/env python3
"""
Settings Dialog Usage Examples for SubtitleToolkit.

This file demonstrates how to use the settings dialog and configuration
management system in various scenarios.
"""

# NOTE: This is a documentation/example file showing usage patterns.
# It requires PySide6 to be installed to run.

from pathlib import Path
import sys

# Add the app directory to Python path (for standalone running)
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))


def example_basic_usage():
    """Basic usage of settings dialog from main application."""
    
    from PySide6.QtWidgets import QApplication
    from config import ConfigManager
    from dialogs.settings_dialog import SettingsDialog
    
    app = QApplication(sys.argv)
    
    # Initialize configuration manager
    config_manager = ConfigManager()
    
    # Create settings dialog
    settings_dialog = SettingsDialog(config_manager)
    
    # Show dialog
    settings_dialog.show()
    
    # Run application
    app.exec()


def example_programmatic_configuration():
    """Examples of programmatic configuration management."""
    
    from config import ConfigManager, TranslationProvider
    
    # Initialize configuration
    config_manager = ConfigManager()
    
    # Example 1: Update translator settings
    translator_settings = {
        "default_provider": TranslationProvider.OPENAI.value,
        "openai": {
            "api_key": "sk-your-api-key-here",
            "default_model": "gpt-4o-mini",
            "temperature": 0.3,
            "max_tokens": 4096
        }
    }
    
    # Validate and save
    validation = config_manager.update_settings("translators", translator_settings)
    if validation.is_valid:
        print("✅ Translator settings updated successfully")
    else:
        print(f"❌ Validation failed: {validation.errors}")
    
    # Example 2: Configure tool paths
    tool_settings = {
        "ffmpeg_path": "/usr/local/bin/ffmpeg",
        "ffprobe_path": "/usr/local/bin/ffprobe", 
        "auto_detect_tools": False
    }
    
    validation = config_manager.update_settings("tools", tool_settings)
    if validation.is_valid:
        print("✅ Tool settings updated successfully")
    
    # Example 3: Set language preferences
    language_settings = {
        "default_source": "auto",
        "default_target": "en",
        "recent_source_languages": ["auto", "es", "fr", "de"],
        "recent_target_languages": ["en", "es", "fr", "zh"],
        "language_detection_confidence": 0.85
    }
    
    validation = config_manager.update_settings("languages", language_settings)
    if validation.is_valid:
        print("✅ Language settings updated successfully")


def example_tool_detection():
    """Example of using tool detection system."""
    
    from config import ConfigManager, ToolStatus
    
    config_manager = ConfigManager()
    
    # Check individual tools
    tools = ["ffmpeg", "ffprobe", "mkvextract"]
    
    for tool_name in tools:
        tool_info = config_manager.get_tool_info(tool_name)
        
        status_symbol = {
            ToolStatus.FOUND: "✅",
            ToolStatus.NOT_FOUND: "❌", 
            ToolStatus.INVALID: "⚠️",
            ToolStatus.ERROR: "🔥"
        }.get(tool_info.status, "❓")
        
        print(f"{status_symbol} {tool_name}: {tool_info.status.value}")
        if tool_info.path:
            print(f"   Path: {tool_info.path}")
        if tool_info.version:
            print(f"   Version: {tool_info.version}")
        if tool_info.error_message:
            print(f"   Error: {tool_info.error_message}")


def example_settings_validation():
    """Example of settings validation."""
    
    from config import ConfigManager, SettingsSchema
    
    # Test with valid settings
    valid_settings = SettingsSchema.get_default_settings()
    validation = SettingsSchema.validate_settings(valid_settings)
    
    print(f"Default settings valid: {validation.is_valid}")
    if validation.warnings:
        print(f"Warnings: {validation.warnings}")
    
    # Test with invalid settings
    invalid_settings = {
        "tools": {"auto_detect_tools": "not_a_boolean"},
        "translators": {"default_provider": "invalid_provider"},
        "languages": {"language_detection_confidence": 1.5},  # > 1.0
        "advanced": {"max_concurrent_workers": -1}  # negative
    }
    
    validation = SettingsSchema.validate_settings(invalid_settings)
    print(f"\nInvalid settings test:")
    print(f"Valid: {validation.is_valid}")
    print(f"Errors: {validation.errors}")


def example_settings_import_export():
    """Example of importing/exporting settings."""
    
    import json
    import tempfile
    from config import ConfigManager
    
    config_manager = ConfigManager()
    
    # Export current settings
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        export_success = config_manager.export_settings(f.name)
        if export_success:
            print(f"✅ Settings exported to {f.name}")
            
            # Show exported content
            with open(f.name, 'r') as read_f:
                exported_data = json.load(read_f)
                print(f"Exported sections: {list(exported_data.keys())}")
        
        # Import settings back
        validation = config_manager.import_settings(f.name)
        if validation.is_valid:
            print("✅ Settings imported successfully")
        else:
            print(f"❌ Import failed: {validation.errors}")


def example_custom_settings_dialog():
    """Example of opening settings dialog to specific tabs."""
    
    from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget
    from config import ConfigManager
    from dialogs.settings_dialog import SettingsDialog
    
    class ExampleMainWindow(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("Settings Dialog Example")
            
            self.config_manager = ConfigManager()
            self.settings_dialog = None
            
            # Create UI
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            layout = QVBoxLayout(central_widget)
            
            # Buttons to open different tabs
            buttons = [
                ("Open General Settings", lambda: self.open_settings()),
                ("Configure Tools", lambda: self.open_settings("tools")),
                ("Setup Translators", lambda: self.open_settings("translators")), 
                ("Language Preferences", lambda: self.open_settings("languages")),
                ("Advanced Options", lambda: self.open_settings("advanced"))
            ]
            
            for text, handler in buttons:
                button = QPushButton(text)
                button.clicked.connect(handler)
                layout.addWidget(button)
        
        def open_settings(self, tab=None):
            if self.settings_dialog is None:
                self.settings_dialog = SettingsDialog(self.config_manager, self)
                self.settings_dialog.settings_applied.connect(self.on_settings_applied)
            
            if tab:
                self.settings_dialog.show_tab(tab)
            
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()
        
        def on_settings_applied(self):
            print("Settings were applied - updating UI...")
    
    app = QApplication(sys.argv)
    window = ExampleMainWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    print("SubtitleToolkit Settings Usage Examples")
    print("=" * 50)
    
    print("\n1. Tool Detection Example:")
    try:
        example_tool_detection()
    except ImportError as e:
        print(f"Skipped (missing dependency): {e}")
    
    print("\n2. Programmatic Configuration Example:")
    try:
        example_programmatic_configuration()
    except ImportError as e:
        print(f"Skipped (missing dependency): {e}")
    
    print("\n3. Settings Validation Example:")
    try:
        example_settings_validation()
    except ImportError as e:
        print(f"Skipped (missing dependency): {e}")
    
    print("\n4. Import/Export Example:")
    try:
        example_settings_import_export()
    except ImportError as e:
        print(f"Skipped (missing dependency): {e}")
    
    print("\nTo run GUI examples:")
    print("python examples/settings_usage_example.py")
    print("(Requires PySide6 installation)")