"""
Translation manager for handling application internationalization.
"""

import os
import logging
from typing import Optional, List
from pathlib import Path
try:
    from PySide6.QtCore import QTranslator, QLocale, QCoreApplication, QLibraryInfo
    from PySide6.QtWidgets import QApplication
    PYSIDE6_AVAILABLE = True
except ImportError:
    PYSIDE6_AVAILABLE = False

from .language_utils import LanguageCode, get_system_language, get_app_translation_file, get_qt_translation_file


class TranslationManager:
    """
    Manages application translations and language switching.
    """
    
    def __init__(self, app=None):
        """
        Initialize the translation manager.
        
        Args:
            app: The QApplication instance (optional)
        """
        self.app = app
        self.logger = logging.getLogger(__name__)
        
        # Translation objects (only if PySide6 is available)
        if PYSIDE6_AVAILABLE:
            self.qt_translator: Optional[QTranslator] = None
            self.app_translator: Optional[QTranslator] = None
        else:
            self.qt_translator = None
            self.app_translator = None
        
        # Current language
        self._current_language = LanguageCode.SYSTEM.value
        
        # Translation directories
        self.translations_dir = Path(__file__).parent / "translations"
        if PYSIDE6_AVAILABLE:
            self.qt_translations_dir = Path(QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath))
        else:
            self.qt_translations_dir = Path("/usr/share/qt6/translations")  # Fallback path
        
        # Ensure translations directory exists
        self.translations_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def current_language(self) -> str:
        """Get the currently active language code."""
        return self._current_language
    
    @property
    def available_languages(self) -> List[str]:
        """Get list of available language codes."""
        return [code.value for code in LanguageCode]
    
    def load_language(self, language_code: str) -> bool:
        """
        Load translations for the specified language.
        
        Args:
            language_code: Language code to load (e.g., 'en', 'de', 'bg', 'es')
            
        Returns:
            bool: True if translations were loaded successfully
        """
        if language_code == LanguageCode.SYSTEM.value:
            language_code = get_system_language()
        
        self.logger.info(f"Loading translations for language: {language_code}")
        
        # If PySide6 is not available, just track the language
        if not PYSIDE6_AVAILABLE:
            self._current_language = language_code
            self.logger.info(f"PySide6 not available, language set to {language_code}")
            return True
        
        # Remove existing translators
        self._remove_translators()
        
        # Don't load translators for English (base language)
        if language_code == LanguageCode.ENGLISH.value:
            self._current_language = language_code
            return True
        
        # Load Qt translations (for standard dialogs, buttons, etc.)
        qt_success = self._load_qt_translator(language_code)
        
        # Load application translations
        app_success = self._load_app_translator(language_code)
        
        if app_success or qt_success:
            self._current_language = language_code
            self.logger.info(f"Successfully loaded translations for {language_code}")
            return True
        else:
            self.logger.warning(f"Failed to load translations for {language_code}, falling back to English")
            self._current_language = LanguageCode.ENGLISH.value
            return False
    
    def _load_qt_translator(self, language_code: str) -> bool:
        """
        Load Qt's built-in translations.
        
        Args:
            language_code: Language code to load
            
        Returns:
            bool: True if loaded successfully
        """
        if not PYSIDE6_AVAILABLE:
            return False
            
        self.qt_translator = QTranslator()
        
        # Try to load Qt translations from system
        qt_file = get_qt_translation_file(language_code)
        qt_path = self.qt_translations_dir / qt_file
        
        if qt_path.exists():
            success = self.qt_translator.load(str(qt_path))
            if success:
                self.app.installTranslator(self.qt_translator)
                self.logger.debug(f"Loaded Qt translations from: {qt_path}")
                return True
        
        # Try alternative Qt file names
        alt_names = [f"qtbase_{language_code}.qm", f"qt_{language_code}_base.qm"]
        for alt_name in alt_names:
            alt_path = self.qt_translations_dir / alt_name
            if alt_path.exists():
                success = self.qt_translator.load(str(alt_path))
                if success:
                    self.app.installTranslator(self.qt_translator)
                    self.logger.debug(f"Loaded Qt translations from: {alt_path}")
                    return True
        
        self.logger.debug(f"No Qt translations found for {language_code}")
        return False
    
    def _load_app_translator(self, language_code: str) -> bool:
        """
        Load application-specific translations.
        
        Args:
            language_code: Language code to load
            
        Returns:
            bool: True if loaded successfully
        """
        if not PYSIDE6_AVAILABLE:
            return False
            
        self.app_translator = QTranslator()
        
        app_file = get_app_translation_file(language_code)
        app_path = self.translations_dir / app_file
        
        if app_path.exists():
            success = self.app_translator.load(str(app_path))
            if success:
                self.app.installTranslator(self.app_translator)
                self.logger.debug(f"Loaded app translations from: {app_path}")
                return True
            else:
                self.logger.warning(f"Failed to load app translations from: {app_path}")
        else:
            self.logger.debug(f"No app translations file found: {app_path}")
        
        return False
    
    def _remove_translators(self) -> None:
        """Remove currently installed translators."""
        if not PYSIDE6_AVAILABLE or not self.app:
            return
            
        if self.qt_translator:
            self.app.removeTranslator(self.qt_translator)
            self.qt_translator = None
        
        if self.app_translator:
            self.app.removeTranslator(self.app_translator)
            self.app_translator = None
    
    def switch_language(self, language_code: str) -> bool:
        """
        Switch to a different language.
        
        Args:
            language_code: Language code to switch to
            
        Returns:
            bool: True if language was switched successfully
        """
        if language_code == self._current_language:
            return True
        
        return self.load_language(language_code)
    
    def get_translation_files_info(self) -> dict:
        """
        Get information about available translation files.
        
        Returns:
            dict: Information about translation files
        """
        info = {
            "translations_dir": str(self.translations_dir),
            "qt_translations_dir": str(self.qt_translations_dir),
            "available_app_translations": [],
            "available_qt_translations": []
        }
        
        # Check for app translation files
        for lang_code in [code.value for code in LanguageCode if code != LanguageCode.SYSTEM]:
            app_file = get_app_translation_file(lang_code)
            if (self.translations_dir / app_file).exists():
                info["available_app_translations"].append(lang_code)
        
        # Check for Qt translation files
        for lang_code in [code.value for code in LanguageCode if code != LanguageCode.SYSTEM]:
            qt_file = get_qt_translation_file(lang_code)
            if (self.qt_translations_dir / qt_file).exists():
                info["available_qt_translations"].append(lang_code)
        
        return info
    
    def create_template_files(self) -> bool:
        """
        Create template translation files for all supported languages.
        
        Returns:
            bool: True if templates were created successfully
        """
        try:
            # This would typically be done with lupdate
            # For now, create placeholder files
            for lang_code in [code.value for code in LanguageCode if code != LanguageCode.SYSTEM and code != LanguageCode.ENGLISH]:
                ts_file = self.translations_dir / f"subtitletoolkit_{lang_code}.ts"
                if not ts_file.exists():
                    self._create_template_ts_file(ts_file, lang_code)
            
            self.logger.info("Template translation files created")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create template files: {e}")
            return False
    
    def _create_template_ts_file(self, file_path: Path, language_code: str) -> None:
        """
        Create a template .ts file for a language.
        
        Args:
            file_path: Path where to create the file
            language_code: Language code for the file
        """
        template_content = f'''<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="{language_code}">
<context>
    <name>MainWindow</name>
    <message>
        <source>SubtitleToolkit</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>&amp;File</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>&amp;Settings</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>&amp;Help</source>
        <translation type="unfinished"></translation>
    </message>
    <message>
        <source>&amp;About</source>
        <translation type="unfinished"></translation>
    </message>
</context>
</TS>'''
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
    
    def retranslate_ui(self) -> None:
        """
        Trigger retranslation of all UI elements.
        This should be called after switching languages.
        """
        # This will be implemented when we update UI components to use tr()
        # For now, just emit a signal that UI should retranslate
        pass