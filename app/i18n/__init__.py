"""
Internationalization (i18n) support for SubtitleToolkit.

This module provides translation infrastructure and language management.
"""

from .translation_manager import TranslationManager
from .language_utils import LanguageCode, get_system_language

__all__ = ['TranslationManager', 'LanguageCode', 'get_system_language']