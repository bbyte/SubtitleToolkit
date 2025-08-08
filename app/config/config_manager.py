"""
Configuration manager for SubtitleToolkit.

Handles loading, saving, and managing application settings with
platform-appropriate storage locations and secure credential handling.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from PySide6.QtCore import QObject, Signal, QStandardPaths

from .settings_schema import SettingsSchema, ValidationResult, TranslationProvider, LogLevel


class ToolStatus(Enum):
    """Status of tool detection."""
    NOT_FOUND = "not_found"
    FOUND = "found"
    INVALID = "invalid"
    ERROR = "error"


@dataclass
class ToolInfo:
    """Information about a detected tool."""
    status: ToolStatus
    path: str = ""
    version: str = ""
    error_message: str = ""


class DependencyChecker:
    """Utility class for checking system dependencies."""
    
    @staticmethod
    def detect_ffmpeg() -> ToolInfo:
        """Detect ffmpeg installation."""
        return DependencyChecker._detect_tool("ffmpeg", ["-version"])
    
    @staticmethod
    def detect_ffprobe() -> ToolInfo:
        """Detect ffprobe installation."""
        return DependencyChecker._detect_tool("ffprobe", ["-version"])
    
    @staticmethod
    def detect_mkvextract() -> ToolInfo:
        """Detect mkvextract installation."""
        return DependencyChecker._detect_tool("mkvextract", ["--version"])
    
    @staticmethod
    def validate_tool_path(path: str, tool_name: str) -> ToolInfo:
        """Validate a specific tool path."""
        if not path or not Path(path).exists():
            return ToolInfo(
                status=ToolStatus.NOT_FOUND,
                error_message=f"Path does not exist: {path}"
            )
        
        try:
            # Try to run the tool to verify it works
            if tool_name == "mkvextract":
                args = ["--version"]
            else:
                args = ["-version"]
            
            result = subprocess.run(
                [path] + args,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                version = DependencyChecker._extract_version(result.stdout + result.stderr, tool_name)
                return ToolInfo(
                    status=ToolStatus.FOUND,
                    path=path,
                    version=version
                )
            else:
                return ToolInfo(
                    status=ToolStatus.INVALID,
                    path=path,
                    error_message=f"Tool returned error code {result.returncode}"
                )
                
        except subprocess.TimeoutExpired:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message="Tool validation timed out"
            )
        except Exception as e:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message=str(e)
            )
    
    @staticmethod
    def _detect_tool(tool_name: str, args: List[str]) -> ToolInfo:
        """Detect a tool using PATH lookup."""
        # First try to find in PATH
        tool_path = shutil.which(tool_name)
        if tool_path:
            return DependencyChecker.validate_tool_path(tool_path, tool_name)
        
        # Common installation locations by platform
        common_paths = DependencyChecker._get_common_tool_paths(tool_name)
        for path in common_paths:
            if Path(path).exists():
                result = DependencyChecker.validate_tool_path(path, tool_name)
                if result.status == ToolStatus.FOUND:
                    return result
        
        return ToolInfo(
            status=ToolStatus.NOT_FOUND,
            error_message=f"{tool_name} not found in PATH or common locations"
        )
    
    @staticmethod
    def _get_common_tool_paths(tool_name: str) -> List[str]:
        """Get common installation paths for tools by platform."""
        import platform
        system = platform.system().lower()
        
        paths = []
        
        if system == "windows":
            # Windows common paths
            program_files = [
                os.environ.get("ProgramFiles", r"C:\Program Files"),
                os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            ]
            
            for pf in program_files:
                if tool_name in ["ffmpeg", "ffprobe"]:
                    paths.extend([
                        f"{pf}\\ffmpeg\\bin\\{tool_name}.exe",
                        f"{pf}\\FFmpeg\\bin\\{tool_name}.exe",
                    ])
                elif tool_name == "mkvextract":
                    paths.extend([
                        f"{pf}\\MKVToolNix\\{tool_name}.exe",
                        f"{pf}\\mkvtoolnix\\{tool_name}.exe",
                    ])
        
        elif system == "darwin":
            # macOS common paths
            if tool_name in ["ffmpeg", "ffprobe"]:
                paths.extend([
                    f"/usr/local/bin/{tool_name}",
                    f"/opt/homebrew/bin/{tool_name}",
                    f"/opt/local/bin/{tool_name}",
                ])
            elif tool_name == "mkvextract":
                paths.extend([
                    f"/usr/local/bin/{tool_name}",
                    f"/opt/homebrew/bin/{tool_name}",
                    f"/Applications/MKVToolNix-*.app/Contents/MacOS/{tool_name}",
                ])
        
        else:
            # Linux common paths
            paths.extend([
                f"/usr/bin/{tool_name}",
                f"/usr/local/bin/{tool_name}",
                f"/opt/bin/{tool_name}",
            ])
        
        return paths
    
    @staticmethod
    def _extract_version(output: str, tool_name: str) -> str:
        """Extract version information from tool output."""
        lines = output.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('Copyright'):
                # Try to find version pattern
                if tool_name == "ffmpeg":
                    if line.startswith("ffmpeg version"):
                        return line.split()[2]
                elif tool_name == "ffprobe":
                    if line.startswith("ffprobe version"):
                        return line.split()[2]
                elif tool_name == "mkvextract":
                    if "mkvextract" in line and "v" in line:
                        parts = line.split()
                        for part in parts:
                            if part.startswith("v") and any(c.isdigit() for c in part):
                                return part[1:]  # Remove 'v' prefix
        
        return "Unknown"
    
    @staticmethod
    def get_installation_guide(tool_name: str) -> str:
        """Get installation instructions for a tool."""
        import platform
        system = platform.system().lower()
        
        guides = {
            "windows": {
                "ffmpeg": "Download from https://ffmpeg.org/download.html and add to PATH",
                "ffprobe": "Included with FFmpeg installation",
                "mkvextract": "Download MKVToolNix from https://mkvtoolnix.download/",
            },
            "darwin": {
                "ffmpeg": "Install with: brew install ffmpeg",
                "ffprobe": "Included with FFmpeg installation", 
                "mkvextract": "Install with: brew install mkvtoolnix",
            },
            "linux": {
                "ffmpeg": "Install with package manager: sudo apt install ffmpeg (Ubuntu/Debian)",
                "ffprobe": "Included with FFmpeg installation",
                "mkvextract": "Install with: sudo apt install mkvtoolnix (Ubuntu/Debian)",
            }
        }
        
        return guides.get(system, {}).get(tool_name, f"Please install {tool_name}")


class ConfigManager(QObject):
    """Manages application configuration with persistence and validation."""
    
    # Signals for configuration changes
    settings_changed = Signal(str)  # section name
    tool_detected = Signal(str, ToolInfo)  # tool name, tool info
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = {}
        self._config_file = self._get_config_file_path()
        self._load_settings()
        
        # Cache for tool detection
        self._tool_cache = {}
        self._last_detection_check = None
    
    def _get_config_file_path(self) -> Path:
        """Get platform-appropriate configuration file path."""
        config_dir = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        if not config_dir:
            # Fallback for older systems
            config_dir = os.path.expanduser("~/.subtitletoolkit")
        
        config_path = Path(config_dir)
        config_path.mkdir(parents=True, exist_ok=True)
        
        return config_path / "settings.json"
    
    def _load_settings(self) -> None:
        """Load settings from file or create defaults."""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                
                # Merge with defaults to handle new settings
                default_settings = SettingsSchema.get_default_settings()
                self._settings = self._merge_settings(default_settings, loaded_settings)
            else:
                self._settings = SettingsSchema.get_default_settings()
                self._save_settings()
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            self._settings = SettingsSchema.get_default_settings()
    
    def _merge_settings(self, defaults: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
        """Merge loaded settings with defaults to handle new keys."""
        result = defaults.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _save_settings(self) -> None:
        """Save current settings to file."""
        try:
            # Update last modified time
            self._settings["last_modified"] = datetime.now().isoformat()
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_settings(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get settings for a specific section or all settings."""
        if section:
            return self._settings.get(section, {}).copy()
        return self._settings.copy()
    
    def update_settings(self, section: str, settings: Dict[str, Any], save: bool = True) -> ValidationResult:
        """Update settings for a specific section."""
        # Create updated settings for validation
        updated_settings = self._settings.copy()
        updated_settings[section] = settings
        
        # Validate the updated settings
        validation = SettingsSchema.validate_settings(updated_settings)
        
        if validation.is_valid or not validation.errors:  # Allow warnings
            self._settings[section] = settings
            if save:
                self._save_settings()
            self.settings_changed.emit(section)
        
        return validation
    
    def get_tool_info(self, tool_name: str, force_refresh: bool = False) -> ToolInfo:
        """Get cached or fresh tool detection information."""
        if force_refresh or tool_name not in self._tool_cache:
            self._tool_cache[tool_name] = self._detect_tool(tool_name)
            self.tool_detected.emit(tool_name, self._tool_cache[tool_name])
        
        return self._tool_cache[tool_name]
    
    def _detect_tool(self, tool_name: str) -> ToolInfo:
        """Detect a specific tool."""
        # Check if manual path is configured
        tools_config = self.get_settings("tools")
        manual_path = tools_config.get(f"{tool_name}_path", "")
        
        if manual_path:
            return DependencyChecker.validate_tool_path(manual_path, tool_name)
        
        # Auto-detection
        if tools_config.get("auto_detect_tools", True):
            if tool_name == "ffmpeg":
                return DependencyChecker.detect_ffmpeg()
            elif tool_name == "ffprobe":
                return DependencyChecker.detect_ffprobe()
            elif tool_name == "mkvextract":
                return DependencyChecker.detect_mkvextract()
        
        return ToolInfo(status=ToolStatus.NOT_FOUND)
    
    def validate_current_settings(self) -> ValidationResult:
        """Validate current settings."""
        return SettingsSchema.validate_settings(self._settings)
    
    def reset_to_defaults(self, sections: Optional[List[str]] = None) -> None:
        """Reset settings to defaults for specified sections or all."""
        defaults = SettingsSchema.get_default_settings()
        
        if sections:
            for section in sections:
                if section in defaults:
                    self._settings[section] = defaults[section]
                    self.settings_changed.emit(section)
        else:
            self._settings = defaults
            self.settings_changed.emit("all")
        
        self._save_settings()
    
    def export_settings(self, file_path: str, sections: Optional[List[str]] = None) -> bool:
        """Export settings to a file."""
        try:
            export_data = {}
            if sections:
                for section in sections:
                    if section in self._settings:
                        export_data[section] = self._settings[section]
            else:
                export_data = self._settings.copy()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def import_settings(self, file_path: str) -> ValidationResult:
        """Import settings from a file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Merge with current settings
            merged_settings = self._merge_settings(self._settings, imported_settings)
            
            # Validate merged settings
            validation = SettingsSchema.validate_settings(merged_settings)
            
            if validation.is_valid or not validation.errors:
                self._settings = merged_settings
                self._save_settings()
                self.settings_changed.emit("all")
            
            return validation
            
        except Exception as e:
            return ValidationResult(
                is_valid=False,
                errors=[f"Import failed: {str(e)}"],
                warnings=[]
            )
    
    def get_config_file_path(self) -> str:
        """Get the path to the configuration file."""
        return str(self._config_file)