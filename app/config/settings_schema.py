"""
Settings schema and validation for SubtitleToolkit.

Defines the structure and validation rules for all application settings.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class LogLevel(Enum):
    """Logging levels for the application."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class TranslationProvider(Enum):
    """Available translation providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LM_STUDIO = "lm_studio"


@dataclass
class ValidationResult:
    """Result of settings validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    
    def __post_init__(self):
        if not self.errors:
            self.errors = []
        if not self.warnings:
            self.warnings = []
    
    @property
    def error_message(self) -> str:
        """Get formatted error message."""
        messages = []
        if self.errors:
            messages.extend([f"Error: {error}" for error in self.errors])
        if self.warnings:
            messages.extend([f"Warning: {warning}" for warning in self.warnings])
        return "\n".join(messages)


class SettingsSchema:
    """Schema definition and validation for application settings."""
    
    @staticmethod
    def get_default_settings() -> Dict[str, Any]:
        """Get default settings structure."""
        return {
            "version": "1.0.0",
            "tools": {
                "ffmpeg_path": "",
                "ffprobe_path": "",
                "mkvextract_path": "",
                "auto_detect_tools": True,
                "last_detection_time": None,
            },
            "translators": {
                "default_provider": TranslationProvider.OPENAI.value,
                "openai": {
                    "api_key": "",
                    "default_model": "gpt-4o-mini",
                    "custom_models": [],  # User-added custom models
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "timeout": 30,
                },
                "anthropic": {
                    "api_key": "",
                    "default_model": "claude-3-haiku-20240307",
                    "custom_models": [],  # User-added custom models
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "timeout": 30,
                },
                "lm_studio": {
                    "base_url": "http://localhost:1234/v1",
                    "api_key": "lm-studio",
                    "default_model": "local-model",
                    "custom_models": [],  # User-added custom models
                    "temperature": 0.3,
                    "max_tokens": 4096,
                    "timeout": 30,
                },
            },
            "languages": {
                "default_source": "auto",
                "default_target": "en",
                "recent_source_languages": ["auto", "es", "fr", "de"],
                "recent_target_languages": ["en", "es", "fr", "de", "bg"],
                "language_detection_confidence": 0.8,
                "default_extract_language": "eng",  # Default extraction language
            },
            "advanced": {
                "max_concurrent_workers": 4,
                "log_level": LogLevel.INFO.value,
                "temp_dir": "",  # Empty means use system default
                "cleanup_temp_files": True,
                "progress_update_interval": 100,  # milliseconds
                "auto_save_settings": True,
                "check_updates_on_startup": True,
            },
            "ui": {
                "remember_window_size": True,
                "remember_window_position": True,
                "window_geometry": {
                    "x": 100,
                    "y": 100,
                    "width": 1200,
                    "height": 800,
                    "is_maximized": False,
                    "is_minimized": False,
                },
                "default_log_filter": "info",
                "show_advanced_options": False,
                "zoom_level": 1.0,
                "zoom_smooth_transitions": True,
                "interface_language": "system",  # "system", "en", "de", "bg", "es"
            }
        }
    
    @staticmethod
    def validate_settings(settings: Dict[str, Any]) -> ValidationResult:
        """Validate settings structure and values."""
        result = ValidationResult(is_valid=True, errors=[], warnings=[])
        
        # Check required top-level keys
        required_keys = ["tools", "translators", "languages", "advanced"]
        for key in required_keys:
            if key not in settings:
                result.errors.append(f"Missing required section: {key}")
        
        if result.errors:
            result.is_valid = False
            return result
        
        # Validate tools section
        SettingsSchema._validate_tools_section(settings["tools"], result)
        
        # Validate translators section
        SettingsSchema._validate_translators_section(settings["translators"], result)
        
        # Validate languages section
        SettingsSchema._validate_languages_section(settings["languages"], result)
        
        # Validate advanced section
        SettingsSchema._validate_advanced_section(settings["advanced"], result)
        
        # Validate UI section
        if "ui" in settings:
            SettingsSchema._validate_ui_section(settings["ui"], result)
        
        # Set overall validity
        result.is_valid = len(result.errors) == 0
        return result
    
    @staticmethod
    def _validate_tools_section(tools: Dict[str, Any], result: ValidationResult) -> None:
        """Validate tools configuration section."""
        # Tool paths should be strings
        path_keys = ["ffmpeg_path", "ffprobe_path", "mkvextract_path"]
        for key in path_keys:
            if key in tools and not isinstance(tools[key], str):
                result.errors.append(f"tools.{key} must be a string")
        
        # Auto detect should be boolean
        if "auto_detect_tools" in tools and not isinstance(tools["auto_detect_tools"], bool):
            result.errors.append("tools.auto_detect_tools must be a boolean")
    
    @staticmethod
    def _validate_translators_section(translators: Dict[str, Any], result: ValidationResult) -> None:
        """Validate translators configuration section."""
        # Check default provider is valid
        if "default_provider" in translators:
            valid_providers = [p.value for p in TranslationProvider]
            if translators["default_provider"] not in valid_providers:
                result.errors.append(f"Invalid default_provider: {translators['default_provider']}")
        
        # Validate provider sections
        for provider in ["openai", "anthropic", "lm_studio"]:
            if provider in translators:
                SettingsSchema._validate_provider_config(
                    translators[provider], provider, result
                )
    
    @staticmethod
    def _validate_provider_config(config: Dict[str, Any], provider: str, result: ValidationResult) -> None:
        """Validate individual translation provider configuration."""
        # API key should be string
        if "api_key" in config and not isinstance(config["api_key"], str):
            result.errors.append(f"translators.{provider}.api_key must be a string")
        
        # Model should be string
        if "default_model" in config and not isinstance(config["default_model"], str):
            result.errors.append(f"translators.{provider}.default_model must be a string")
        
        # Temperature should be float between 0 and 2
        if "temperature" in config:
            temp = config["temperature"]
            if not isinstance(temp, (int, float)) or not (0 <= temp <= 2):
                result.errors.append(f"translators.{provider}.temperature must be a number between 0 and 2")
        
        # Max tokens should be positive integer
        if "max_tokens" in config:
            tokens = config["max_tokens"]
            if not isinstance(tokens, int) or tokens <= 0:
                result.errors.append(f"translators.{provider}.max_tokens must be a positive integer")
        
        # Timeout should be positive number
        if "timeout" in config:
            timeout = config["timeout"]
            if not isinstance(timeout, (int, float)) or timeout <= 0:
                result.errors.append(f"translators.{provider}.timeout must be a positive number")
    
    @staticmethod
    def _validate_languages_section(languages: Dict[str, Any], result: ValidationResult) -> None:
        """Validate languages configuration section."""
        # Language codes should be strings
        lang_keys = ["default_source", "default_target"]
        for key in lang_keys:
            if key in languages and not isinstance(languages[key], str):
                result.errors.append(f"languages.{key} must be a string")
        
        # Recent languages should be lists of strings
        recent_keys = ["recent_source_languages", "recent_target_languages"]
        for key in recent_keys:
            if key in languages:
                if not isinstance(languages[key], list):
                    result.errors.append(f"languages.{key} must be a list")
                elif not all(isinstance(lang, str) for lang in languages[key]):
                    result.errors.append(f"languages.{key} must contain only strings")
        
        # Confidence should be float between 0 and 1
        if "language_detection_confidence" in languages:
            conf = languages["language_detection_confidence"]
            if not isinstance(conf, (int, float)) or not (0 <= conf <= 1):
                result.errors.append("languages.language_detection_confidence must be between 0 and 1")
    
    @staticmethod
    def _validate_advanced_section(advanced: Dict[str, Any], result: ValidationResult) -> None:
        """Validate advanced configuration section."""
        # Max workers should be positive integer
        if "max_concurrent_workers" in advanced:
            workers = advanced["max_concurrent_workers"]
            if not isinstance(workers, int) or workers <= 0:
                result.errors.append("advanced.max_concurrent_workers must be a positive integer")
            elif workers > 32:
                result.warnings.append("advanced.max_concurrent_workers > 32 may impact performance")
        
        # Log level should be valid
        if "log_level" in advanced:
            valid_levels = [level.value for level in LogLevel]
            if advanced["log_level"] not in valid_levels:
                result.errors.append(f"Invalid log_level: {advanced['log_level']}")
        
        # Temp dir should be string
        if "temp_dir" in advanced and not isinstance(advanced["temp_dir"], str):
            result.errors.append("advanced.temp_dir must be a string")
        
        # Boolean settings
        bool_keys = ["cleanup_temp_files", "auto_save_settings", "check_updates_on_startup"]
        for key in bool_keys:
            if key in advanced and not isinstance(advanced[key], bool):
                result.errors.append(f"advanced.{key} must be a boolean")
        
        # Progress update interval should be positive integer
        if "progress_update_interval" in advanced:
            interval = advanced["progress_update_interval"]
            if not isinstance(interval, int) or interval <= 0:
                result.errors.append("advanced.progress_update_interval must be a positive integer")
    
    @staticmethod
    def _validate_ui_section(ui: Dict[str, Any], result: ValidationResult) -> None:
        """Validate UI configuration section."""
        # Boolean settings
        bool_keys = ["remember_window_size", "remember_window_position", "show_advanced_options", "zoom_smooth_transitions"]
        for key in bool_keys:
            if key in ui and not isinstance(ui[key], bool):
                result.errors.append(f"ui.{key} must be a boolean")
        
        # Default log filter should be string
        if "default_log_filter" in ui and not isinstance(ui["default_log_filter"], str):
            result.errors.append("ui.default_log_filter must be a string")
        
        # Zoom level should be float between 0.5 and 2.0
        if "zoom_level" in ui:
            zoom = ui["zoom_level"]
            if not isinstance(zoom, (int, float)) or not (0.5 <= zoom <= 2.0):
                result.errors.append("ui.zoom_level must be a number between 0.5 and 2.0")
        
        # Interface language validation
        if "interface_language" in ui:
            valid_languages = ["system", "en", "de", "bg", "es"]
            if ui["interface_language"] not in valid_languages:
                result.errors.append(f"ui.interface_language must be one of: {', '.join(valid_languages)}")
        
        # Validate window geometry
        if "window_geometry" in ui:
            SettingsSchema._validate_window_geometry(ui["window_geometry"], result)
    
    @staticmethod
    def _validate_window_geometry(geometry: Dict[str, Any], result: ValidationResult) -> None:
        """Validate window geometry configuration."""
        if not isinstance(geometry, dict):
            result.errors.append("ui.window_geometry must be a dictionary")
            return
        
        # Position coordinates should be integers
        for coord in ["x", "y"]:
            if coord in geometry:
                value = geometry[coord]
                if not isinstance(value, int):
                    result.errors.append(f"ui.window_geometry.{coord} must be an integer")
                elif value < -10000 or value > 10000:  # Reasonable bounds
                    result.warnings.append(f"ui.window_geometry.{coord} is outside reasonable range")
        
        # Size dimensions should be positive integers
        for dim in ["width", "height"]:
            if dim in geometry:
                value = geometry[dim]
                if not isinstance(value, int):
                    result.errors.append(f"ui.window_geometry.{dim} must be an integer")
                elif value < 400:  # Minimum reasonable window size
                    result.errors.append(f"ui.window_geometry.{dim} must be at least 400 pixels")
                elif value > 10000:  # Maximum reasonable window size
                    result.warnings.append(f"ui.window_geometry.{dim} is very large (>10000px)")
        
        # Window state flags should be boolean
        for flag in ["is_maximized", "is_minimized"]:
            if flag in geometry and not isinstance(geometry[flag], bool):
                result.errors.append(f"ui.window_geometry.{flag} must be a boolean")
    
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """Get supported language codes and names."""
        return {
            "auto": "Auto-detect",
            "en": "English",
            "es": "Spanish",
            "fr": "French",
            "de": "German",
            "it": "Italian",
            "pt": "Portuguese",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese (Simplified)",
            "zh-TW": "Chinese (Traditional)",
            "ar": "Arabic",
            "hi": "Hindi",
            "th": "Thai",
            "vi": "Vietnamese",
            "nl": "Dutch",
            "sv": "Swedish",
            "da": "Danish",
            "no": "Norwegian",
            "fi": "Finnish",
            "pl": "Polish",
            "cs": "Czech",
            "hu": "Hungarian",
            "ro": "Romanian",
            "bg": "Bulgarian",
            "hr": "Croatian",
            "sk": "Slovak",
            "sl": "Slovenian",
            "et": "Estonian",
            "lv": "Latvian",
            "lt": "Lithuanian",
            "uk": "Ukrainian",
            "be": "Belarusian",
            "mk": "Macedonian",
            "sq": "Albanian",
            "sr": "Serbian",
            "bs": "Bosnian",
            "me": "Montenegrin",
        }
    
    @staticmethod
    def get_openai_models() -> List[str]:
        """Get available OpenAI models."""
        return [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-4",
            "gpt-3.5-turbo",
        ]
    
    @staticmethod
    def get_anthropic_models() -> List[str]:
        """Get available Anthropic models."""
        return [
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
        ]
    
    @staticmethod
    def get_interface_languages() -> Dict[str, str]:
        """Get supported interface languages."""
        return {
            "system": "System Default",
            "en": "English",
            "de": "Deutsch",
            "bg": "Български", 
            "es": "Español"
        }