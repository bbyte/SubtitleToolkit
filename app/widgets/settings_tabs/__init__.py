"""
Settings tab widgets for SubtitleToolkit.

Contains individual tab implementations for the settings dialog.
"""

from .tools_tab import ToolsTab
from .translators_tab import TranslatorsTab
from .languages_tab import LanguagesTab
from .advanced_tab import AdvancedTab
from .interface_tab import InterfaceTab

__all__ = ['ToolsTab', 'TranslatorsTab', 'LanguagesTab', 'AdvancedTab', 'InterfaceTab']