"""
Enhanced dependency checker for SubtitleToolkit.

Provides comprehensive tool detection, version validation, and installation
guidance with cross-platform support and robust error handling.
"""

import subprocess
import shutil
import re
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Tuple
from datetime import datetime, timedelta

from .tool_status import ToolStatus, ToolInfo, ToolRequirement, TOOL_REQUIREMENTS
from .platform_utils import PlatformUtils


class DependencyChecker:
    """
    Enhanced dependency checker with comprehensive tool detection and validation.
    
    Features:
    - Automatic PATH scanning and common location detection
    - Version parsing and minimum requirement validation
    - Cross-platform installation guidance
    - Caching with TTL for performance
    - Background detection with progress callbacks
    - Security validation for user-provided paths
    """
    
    def __init__(self, cache_ttl_minutes: int = 10):
        """
        Initialize dependency checker.
        
        Args:
            cache_ttl_minutes: Cache time-to-live in minutes
        """
        self.cache_ttl = timedelta(minutes=cache_ttl_minutes)
        self._cache: Dict[str, ToolInfo] = {}
        self._detection_lock = threading.Lock()
    
    def detect_ffmpeg(self, use_cache: bool = True) -> ToolInfo:
        """Detect ffmpeg installation with comprehensive validation."""
        return self._detect_tool("ffmpeg", ["-version"], use_cache)
    
    def detect_ffprobe(self, use_cache: bool = True) -> ToolInfo:
        """Detect ffprobe installation with comprehensive validation."""
        return self._detect_tool("ffprobe", ["-version"], use_cache)
    
    def detect_mkvextract(self, use_cache: bool = True) -> ToolInfo:
        """Detect mkvextract installation with comprehensive validation."""
        return self._detect_tool("mkvextract", ["--version"], use_cache)
    
    def detect_all_tools(
        self, 
        progress_callback: Optional[Callable[[str, int], None]] = None,
        use_cache: bool = True
    ) -> Dict[str, ToolInfo]:
        """
        Detect all required tools with progress reporting.
        
        Args:
            progress_callback: Callback function (tool_name, percentage)
            use_cache: Whether to use cached results
            
        Returns:
            Dictionary mapping tool names to ToolInfo objects
        """
        tools = ["ffmpeg", "ffprobe", "mkvextract"]
        results = {}
        
        for i, tool in enumerate(tools):
            if progress_callback:
                progress_callback(tool, int((i / len(tools)) * 100))
            
            if tool == "ffmpeg":
                results[tool] = self.detect_ffmpeg(use_cache)
            elif tool == "ffprobe":
                results[tool] = self.detect_ffprobe(use_cache)
            elif tool == "mkvextract":
                results[tool] = self.detect_mkvextract(use_cache)
        
        if progress_callback:
            progress_callback("complete", 100)
        
        return results
    
    def validate_tool_path(self, path: str, tool_name: str) -> ToolInfo:
        """
        Validate a specific tool path with security checks.
        
        Args:
            path: Path to the tool executable
            tool_name: Name of the tool being validated
            
        Returns:
            ToolInfo with validation results
        """
        # Security validation
        is_safe, security_message = PlatformUtils.validate_path_security(path)
        if not is_safe:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message=f"Security validation failed: {security_message}"
            )
        
        # Check if file exists and is executable
        path_obj = Path(path)
        if not path_obj.exists():
            return ToolInfo(
                status=ToolStatus.NOT_FOUND,
                path=path,
                error_message="File does not exist"
            )
        
        if not path_obj.is_file():
            return ToolInfo(
                status=ToolStatus.INVALID,
                path=path,
                error_message="Path is not a file"
            )
        
        # Try to execute and validate
        return self._validate_tool_execution(path, tool_name)
    
    def get_installation_guide(self, tool_name: str) -> str:
        """Get comprehensive installation guide for a tool."""
        base_guide = PlatformUtils.get_installation_guide(tool_name)
        
        # Add tool-specific notes and requirements
        requirement = TOOL_REQUIREMENTS.get(tool_name)
        if requirement:
            additional_info = f"\n\nTool Information:\n"
            additional_info += f"- Description: {requirement.description}\n"
            if requirement.minimum_version:
                additional_info += f"- Minimum Version: {requirement.minimum_version}\n"
            if not requirement.required:
                additional_info += f"- Optional: This tool is optional\n"
            if requirement.alternatives:
                additional_info += f"- Alternatives: {', '.join(requirement.alternatives)}\n"
            
            base_guide += additional_info
        
        return base_guide
    
    def clear_cache(self) -> None:
        """Clear the detection cache."""
        with self._detection_lock:
            self._cache.clear()
    
    def get_cached_result(self, tool_name: str) -> Optional[ToolInfo]:
        """Get cached detection result if still valid."""
        with self._detection_lock:
            if tool_name in self._cache:
                cached_info = self._cache[tool_name]
                if cached_info.detected_at and \
                   (datetime.now() - cached_info.detected_at) < self.cache_ttl:
                    return cached_info
                else:
                    # Remove expired cache entry
                    del self._cache[tool_name]
        return None
    
    def _detect_tool(self, tool_name: str, version_args: List[str], use_cache: bool = True) -> ToolInfo:
        """
        Internal method for comprehensive tool detection.
        
        Args:
            tool_name: Name of the tool to detect
            version_args: Arguments to get version information
            use_cache: Whether to use cached results
            
        Returns:
            ToolInfo with detection results
        """
        # Check cache first
        if use_cache:
            cached_result = self.get_cached_result(tool_name)
            if cached_result:
                return cached_result
        
        tool_info = None
        
        # Try PATH detection first
        path_executables = PlatformUtils.find_executables_in_path(tool_name)
        for exe_path in path_executables:
            tool_info = self._validate_tool_execution(exe_path, tool_name)
            if tool_info.status == ToolStatus.FOUND:
                break
        
        # If not found in PATH, try common locations
        if not tool_info or tool_info.status != ToolStatus.FOUND:
            common_paths = PlatformUtils.get_common_tool_paths(tool_name)
            for common_path in common_paths:
                if Path(common_path).exists():
                    test_info = self._validate_tool_execution(common_path, tool_name)
                    if test_info.status == ToolStatus.FOUND:
                        tool_info = test_info
                        break
        
        # If still not found, create not found result
        if not tool_info:
            tool_info = ToolInfo(
                status=ToolStatus.NOT_FOUND,
                error_message=f"{tool_name} not found in PATH or common installation locations"
            )
        
        # Cache the result
        with self._detection_lock:
            self._cache[tool_name] = tool_info
        
        return tool_info
    
    def _validate_tool_execution(self, path: str, tool_name: str) -> ToolInfo:
        """
        Validate tool by executing it and parsing version information.
        
        Args:
            path: Path to the tool executable
            tool_name: Name of the tool
            
        Returns:
            ToolInfo with execution validation results
        """
        try:
            # Determine version arguments
            if tool_name == "mkvextract":
                version_args = ["--version"]
            else:
                version_args = ["-version"]
            
            # Execute tool to get version
            result = subprocess.run(
                [path] + version_args,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            if result.returncode != 0:
                return ToolInfo(
                    status=ToolStatus.INVALID,
                    path=path,
                    error_message=f"Tool execution failed with return code {result.returncode}"
                )
            
            # Parse version information
            version_output = result.stdout + result.stderr
            version = self._extract_version(version_output, tool_name)
            
            # Validate version requirements
            requirement = TOOL_REQUIREMENTS.get(tool_name)
            meets_requirements = True
            minimum_version = ""
            
            if requirement and requirement.minimum_version:
                minimum_version = requirement.minimum_version
                meets_requirements = self._compare_versions(version, minimum_version) >= 0
                
                if not meets_requirements:
                    return ToolInfo(
                        status=ToolStatus.VERSION_MISMATCH,
                        path=path,
                        version=version,
                        minimum_version=minimum_version,
                        meets_requirements=False,
                        error_message=f"Version {version} does not meet minimum requirement {minimum_version}"
                    )
            
            # Detect installation method
            installation_method = self._detect_installation_method(path)
            
            return ToolInfo(
                status=ToolStatus.FOUND,
                path=path,
                version=version,
                minimum_version=minimum_version,
                meets_requirements=meets_requirements,
                installation_method=installation_method
            )
            
        except subprocess.TimeoutExpired:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message="Tool validation timed out after 10 seconds"
            )
        except subprocess.SubprocessError as e:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message=f"Subprocess error: {str(e)}"
            )
        except Exception as e:
            return ToolInfo(
                status=ToolStatus.ERROR,
                path=path,
                error_message=f"Unexpected error during validation: {str(e)}"
            )
    
    def _extract_version(self, output: str, tool_name: str) -> str:
        """
        Extract version information from tool output with robust parsing.
        
        Args:
            output: Raw output from tool version command
            tool_name: Name of the tool
            
        Returns:
            Version string or "Unknown" if not found
        """
        if not output:
            return "Unknown"
        
        lines = output.split('\n')
        
        # Tool-specific version extraction patterns
        patterns = {
            "ffmpeg": [
                r"ffmpeg version (\S+)",
                r"version (\d+\.\d+(?:\.\d+)?)"
            ],
            "ffprobe": [
                r"ffprobe version (\S+)", 
                r"version (\d+\.\d+(?:\.\d+)?)"
            ],
            "mkvextract": [
                r"mkvextract v(\d+\.\d+\.\d+)",
                r"v(\d+\.\d+\.\d+)",
                r"(\d+\.\d+\.\d+)"
            ]
        }
        
        tool_patterns = patterns.get(tool_name, [r"(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)"])
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('Copyright'):
                continue
            
            for pattern in tool_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    version = match.group(1)
                    # Clean up version string
                    version = re.sub(r'[^\d\.]', '', version.split()[0])
                    return version
        
        # Fallback: look for any version-like pattern
        version_pattern = r"(\d+\.\d+(?:\.\d+)?(?:\.\d+)?)"
        for line in lines[:5]:  # Check first few lines only
            match = re.search(version_pattern, line)
            if match:
                return match.group(1)
        
        return "Unknown"
    
    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.
        
        Args:
            version1: First version string
            version2: Second version string
            
        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        def normalize_version(v: str) -> List[int]:
            """Normalize version string to list of integers."""
            if v.lower() == "unknown":
                return [0]
            
            # Remove non-numeric characters except dots
            v_clean = re.sub(r'[^\d\.]', '', v)
            parts = v_clean.split('.')
            
            # Convert to integers, handling empty parts
            normalized = []
            for part in parts:
                try:
                    normalized.append(int(part) if part else 0)
                except ValueError:
                    normalized.append(0)
            
            return normalized
        
        v1_parts = normalize_version(version1)
        v2_parts = normalize_version(version2)
        
        # Pad shorter version with zeros
        max_len = max(len(v1_parts), len(v2_parts))
        v1_parts.extend([0] * (max_len - len(v1_parts)))
        v2_parts.extend([0] * (max_len - len(v2_parts)))
        
        # Compare part by part
        for i in range(max_len):
            if v1_parts[i] < v2_parts[i]:
                return -1
            elif v1_parts[i] > v2_parts[i]:
                return 1
        
        return 0
    
    def _detect_installation_method(self, path: str) -> str:
        """
        Detect how the tool was likely installed based on its path.
        
        Args:
            path: Path to the tool executable
            
        Returns:
            String describing likely installation method
        """
        path_str = str(path).lower()
        
        # Platform-specific detection
        platform = PlatformUtils.get_platform()
        
        if platform == "windows":
            if "chocolatey" in path_str:
                return "chocolatey"
            elif "scoop" in path_str:
                return "scoop"
            elif "program files" in path_str:
                return "installer"
            else:
                return "manual"
        
        elif platform == "macos":
            if "/opt/homebrew" in path_str or "/usr/local" in path_str:
                return "homebrew"
            elif "/opt/local" in path_str:
                return "macports"
            elif ".app/contents/macos" in path_str:
                return "app_bundle"
            else:
                return "manual"
        
        else:  # Linux and others
            if "/snap/" in path_str:
                return "snap"
            elif "flatpak" in path_str:
                return "flatpak"
            elif ".appimage" in path_str:
                return "appimage"
            elif "/usr/bin" in path_str or "/usr/local/bin" in path_str:
                return "package_manager"
            else:
                return "manual"