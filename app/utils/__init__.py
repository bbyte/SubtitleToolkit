"""
Utility modules for SubtitleToolkit desktop application.

This package provides utility classes and functions for:
- Dependency detection and validation
- Platform-specific utilities
- Tool status management
- Configuration helpers
"""

from .dependency_checker import DependencyChecker
from .tool_status import ToolStatus, ToolInfo
from .platform_utils import PlatformUtils

__all__ = [
    'DependencyChecker',
    'ToolStatus', 
    'ToolInfo',
    'PlatformUtils'
]