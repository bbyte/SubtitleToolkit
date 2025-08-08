"""
Configuration manager for SubtitleToolkit.

Handles loading, saving, and managing application settings with
platform-appropriate storage locations and secure credential handling.
"""

import json
import os
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta

from PySide6.QtCore import QObject, Signal, QStandardPaths, QThread

from .settings_schema import SettingsSchema, ValidationResult, TranslationProvider, LogLevel
from ..utils import DependencyChecker, ToolStatus, ToolInfo


class BackgroundDetectionWorker(QObject):
    """Worker for background tool detection."""
    
    detection_progress = Signal(str, int)  # tool_name, percentage
    tool_detected = Signal(str, ToolInfo)  # tool_name, tool_info
    detection_complete = Signal(dict)  # results dictionary
    
    def __init__(self, dependency_checker: DependencyChecker, tools: List[str]):
        super().__init__()
        self.dependency_checker = dependency_checker
        self.tools = tools
        self.should_stop = False
    
    def run(self):
        """Run background detection for all tools."""
        results = {}
        total_tools = len(self.tools)
        
        for i, tool in enumerate(self.tools):
            if self.should_stop:
                break
            
            # Emit progress
            progress = int((i / total_tools) * 100)
            self.detection_progress.emit(tool, progress)
            
            # Detect tool
            if tool == "ffmpeg":
                info = self.dependency_checker.detect_ffmpeg(use_cache=False)
            elif tool == "ffprobe":
                info = self.dependency_checker.detect_ffprobe(use_cache=False)
            elif tool == "mkvextract":
                info = self.dependency_checker.detect_mkvextract(use_cache=False)
            else:
                info = ToolInfo(status=ToolStatus.NOT_FOUND, error_message=f"Unknown tool: {tool}")
            
            results[tool] = info
            self.tool_detected.emit(tool, info)
        
        # Final progress update
        if not self.should_stop:
            self.detection_progress.emit("complete", 100)
            self.detection_complete.emit(results)
    
    def stop(self):
        """Stop the detection process."""
        self.should_stop = True


class ConfigManager(QObject):
    """Manages application configuration with persistence and validation."""
    
    # Signals for configuration changes
    settings_changed = Signal(str)  # section name
    tool_detected = Signal(str, ToolInfo)  # tool name, tool info
    detection_progress = Signal(str, int)  # tool_name, percentage
    detection_complete = Signal(dict)  # results dictionary
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = {}
        self._config_file = self._get_config_file_path()
        self._load_settings()
        
        # Enhanced dependency checker with caching
        self._dependency_checker = DependencyChecker(cache_ttl_minutes=10)
        
        # Background detection threading
        self._detection_thread = None
        self._detection_worker = None
        
        # Tool detection cache with persistence
        self._tool_detection_cache_file = self._config_file.parent / "tool_cache.json"
    
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
        # Check if manual path is configured first
        tools_config = self.get_settings("tools")
        manual_path = tools_config.get(f"{tool_name}_path", "")
        
        if manual_path:
            # Validate manual path
            info = self._dependency_checker.validate_tool_path(manual_path, tool_name)
            self.tool_detected.emit(tool_name, info)
            return info
        
        # Use enhanced dependency checker with caching
        if force_refresh:
            self._dependency_checker.clear_cache()
        
        # Auto-detection if enabled
        if tools_config.get("auto_detect_tools", True):
            if tool_name == "ffmpeg":
                info = self._dependency_checker.detect_ffmpeg(use_cache=not force_refresh)
            elif tool_name == "ffprobe":
                info = self._dependency_checker.detect_ffprobe(use_cache=not force_refresh)
            elif tool_name == "mkvextract":
                info = self._dependency_checker.detect_mkvextract(use_cache=not force_refresh)
            else:
                info = ToolInfo(status=ToolStatus.NOT_FOUND, error_message=f"Unknown tool: {tool_name}")
        else:
            info = ToolInfo(status=ToolStatus.NOT_FOUND, error_message="Auto-detection disabled")
        
        self.tool_detected.emit(tool_name, info)
        return info
    
    def detect_all_tools_background(
        self, 
        tools: Optional[List[str]] = None, 
        force_refresh: bool = False
    ) -> None:
        """
        Detect all tools in background thread with progress updates.
        
        Args:
            tools: List of tool names to detect (default: all supported tools)
            force_refresh: Force fresh detection ignoring cache
        """
        if tools is None:
            tools = ["ffmpeg", "ffprobe", "mkvextract"]
        
        # Stop any existing detection
        self.stop_background_detection()
        
        if force_refresh:
            self._dependency_checker.clear_cache()
        
        # Create new worker and thread
        self._detection_worker = BackgroundDetectionWorker(self._dependency_checker, tools)
        self._detection_thread = QThread()
        self._detection_worker.moveToThread(self._detection_thread)
        
        # Connect signals
        self._detection_thread.started.connect(self._detection_worker.run)
        self._detection_worker.detection_progress.connect(self.detection_progress.emit)
        self._detection_worker.tool_detected.connect(self.tool_detected.emit)
        self._detection_worker.detection_complete.connect(self._on_background_detection_complete)
        
        # Start detection
        self._detection_thread.start()
    
    def stop_background_detection(self) -> None:
        """Stop any ongoing background detection."""
        if self._detection_worker:
            self._detection_worker.stop()
        
        if self._detection_thread and self._detection_thread.isRunning():
            self._detection_thread.quit()
            self._detection_thread.wait(5000)  # Wait up to 5 seconds
        
        self._detection_worker = None
        self._detection_thread = None
    
    def _on_background_detection_complete(self, results: Dict[str, ToolInfo]) -> None:
        """Handle background detection completion."""
        # Save detection results to cache file
        self._save_tool_detection_cache(results)
        
        # Update last detection time in settings
        tools_settings = self.get_settings("tools")
        tools_settings["last_detection_time"] = datetime.now().isoformat()
        self.update_settings("tools", tools_settings, save=True)
        
        # Clean up thread
        if self._detection_thread:
            self._detection_thread.quit()
            self._detection_thread.wait()
        
        self._detection_worker = None
        self._detection_thread = None
        
        # Emit completion signal
        self.detection_complete.emit(results)
    
    def get_installation_guide(self, tool_name: str) -> str:
        """Get installation guide for a tool."""
        return self._dependency_checker.get_installation_guide(tool_name)
    
    def validate_tool_path(self, path: str, tool_name: str) -> ToolInfo:
        """Validate a tool path."""
        return self._dependency_checker.validate_tool_path(path, tool_name)
    
    def _save_tool_detection_cache(self, results: Dict[str, ToolInfo]) -> None:
        """Save tool detection results to cache file."""
        try:
            cache_data = {
                "timestamp": datetime.now().isoformat(),
                "results": {
                    tool: info.to_dict() for tool, info in results.items()
                }
            }
            
            with open(self._tool_detection_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Failed to save tool detection cache: {e}")
    
    def _load_tool_detection_cache(self) -> Optional[Dict[str, ToolInfo]]:
        """Load tool detection results from cache file."""
        try:
            if not self._tool_detection_cache_file.exists():
                return None
            
            with open(self._tool_detection_cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check if cache is still valid (within 1 hour)
            cache_time = datetime.fromisoformat(cache_data["timestamp"])
            if datetime.now() - cache_time > timedelta(hours=1):
                return None
            
            # Convert back to ToolInfo objects
            results = {}
            for tool, info_dict in cache_data["results"].items():
                results[tool] = ToolInfo.from_dict(info_dict)
            
            return results
            
        except Exception as e:
            print(f"Failed to load tool detection cache: {e}")
            return None
    
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