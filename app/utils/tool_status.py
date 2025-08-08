"""
Tool status data classes for dependency management.

Defines the status tracking and information structures for system tools
used by SubtitleToolkit.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class ToolStatus(Enum):
    """Status of tool detection and validation."""
    NOT_FOUND = "not_found"
    FOUND = "found"
    INVALID = "invalid"
    ERROR = "error"
    TESTING = "testing"
    VERSION_MISMATCH = "version_mismatch"


@dataclass
class ToolInfo:
    """Comprehensive information about a detected tool."""
    status: ToolStatus
    path: str = ""
    version: str = ""
    error_message: str = ""
    detected_at: Optional[datetime] = None
    minimum_version: str = ""
    meets_requirements: bool = True
    installation_method: str = ""  # e.g., "brew", "apt", "manual"
    
    def __post_init__(self):
        """Set detected_at timestamp if not provided."""
        if self.detected_at is None:
            self.detected_at = datetime.now()
    
    @property
    def is_usable(self) -> bool:
        """Check if tool is in a usable state."""
        return self.status == ToolStatus.FOUND and self.meets_requirements
    
    @property
    def status_description(self) -> str:
        """Get human-readable status description."""
        status_map = {
            ToolStatus.NOT_FOUND: "Not found in system PATH or common locations",
            ToolStatus.FOUND: f"Found and working (v{self.version})",
            ToolStatus.INVALID: "Found but not working properly",
            ToolStatus.ERROR: "Error during detection",
            ToolStatus.TESTING: "Currently testing...",
            ToolStatus.VERSION_MISMATCH: f"Version {self.version} does not meet minimum requirement ({self.minimum_version})"
        }
        return status_map.get(self.status, "Unknown status")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "status": self.status.value,
            "path": self.path,
            "version": self.version,
            "error_message": self.error_message,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "minimum_version": self.minimum_version,
            "meets_requirements": self.meets_requirements,
            "installation_method": self.installation_method
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolInfo":
        """Create from dictionary data."""
        detected_at = None
        if data.get("detected_at"):
            detected_at = datetime.fromisoformat(data["detected_at"])
        
        return cls(
            status=ToolStatus(data.get("status", ToolStatus.NOT_FOUND.value)),
            path=data.get("path", ""),
            version=data.get("version", ""),
            error_message=data.get("error_message", ""),
            detected_at=detected_at,
            minimum_version=data.get("minimum_version", ""),
            meets_requirements=data.get("meets_requirements", True),
            installation_method=data.get("installation_method", "")
        )


@dataclass
class ToolRequirement:
    """Tool requirement specification."""
    name: str
    minimum_version: str = ""
    required: bool = True
    alternatives: list = None
    description: str = ""
    
    def __post_init__(self):
        """Initialize alternatives list."""
        if self.alternatives is None:
            self.alternatives = []


# Tool requirements configuration
TOOL_REQUIREMENTS = {
    "ffmpeg": ToolRequirement(
        name="ffmpeg",
        minimum_version="4.0.0",
        required=True,
        description="Required for MKV subtitle extraction and video processing"
    ),
    "ffprobe": ToolRequirement(
        name="ffprobe", 
        minimum_version="4.0.0",
        required=True,
        description="Required for MKV file analysis (included with FFmpeg)"
    ),
    "mkvextract": ToolRequirement(
        name="mkvextract",
        minimum_version="50.0.0",
        required=False,
        alternatives=["ffmpeg"],
        description="Alternative tool for MKV subtitle extraction (optional)"
    )
}