"""
Language utilities for internationalization support.
"""

import locale
from enum import Enum
from typing import Dict, Optional
try:
    from PySide6.QtCore import QLocale
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False


class LanguageCode(Enum):
    """Supported interface language codes."""
    SYSTEM = "system"
    ENGLISH = "en"
    GERMAN = "de" 
    BULGARIAN = "bg"
    SPANISH = "es"


def get_system_language() -> str:
    """
    Get the system's default language code.
    
    Returns:
        str: Language code (e.g., 'en', 'de', 'bg', 'es')
    """
    try:
        supported_languages = {code.value for code in LanguageCode if code != LanguageCode.SYSTEM}
        
        # Try Qt's locale detection first (if available)
        if PYSIDE6_AVAILABLE:
            qt_locale = QLocale.system()
            lang_code = qt_locale.name().split('_')[0]
            if lang_code in supported_languages:
                return lang_code
        
        # Fallback to Python's locale
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            lang_code = system_locale.split('_')[0]
            if lang_code in supported_languages:
                return lang_code
    except Exception:
        pass
    
    # Default to English if detection fails
    return LanguageCode.ENGLISH.value


def get_language_display_names() -> Dict[str, str]:
    """
    Get display names for supported interface languages.
    
    Returns:
        Dict mapping language codes to display names
    """
    return {
        LanguageCode.SYSTEM.value: "System Default",
        LanguageCode.ENGLISH.value: "English",
        LanguageCode.GERMAN.value: "Deutsch",
        LanguageCode.BULGARIAN.value: "Български",
        LanguageCode.SPANISH.value: "Español"
    }


def get_qt_translation_file(language_code: str) -> str:
    """
    Get the Qt translation file name for a language code.
    
    Args:
        language_code: Language code (e.g., 'en', 'de')
        
    Returns:
        str: Qt translation file name (e.g., 'qt_de.qm')
    """
    if language_code == LanguageCode.SYSTEM.value:
        language_code = get_system_language()
    
    return f"qt_{language_code}.qm"


def get_app_translation_file(language_code: str) -> str:
    """
    Get the application translation file name for a language code.
    
    Args:
        language_code: Language code (e.g., 'en', 'de')
        
    Returns:
        str: Application translation file name (e.g., 'subtitletoolkit_de.qm')
    """
    if language_code == LanguageCode.SYSTEM.value:
        language_code = get_system_language()
    
    return f"subtitletoolkit_{language_code}.qm"


def is_rtl_language(language_code: str) -> bool:
    """
    Check if a language is right-to-left.
    
    Args:
        language_code: Language code to check
        
    Returns:
        bool: True if language is RTL
    """
    rtl_languages = {'ar', 'he', 'fa', 'ur'}
    return language_code in rtl_languages