"""
Event system for JSONL stream processing in SubtitleToolkit.

Defines event models and Qt signals for real-time process communication.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List

from PySide6.QtCore import QObject, Signal


class EventType(Enum):
    """Types of events that can be emitted during script execution."""
    INFO = "info"
    PROGRESS = "progress"
    WARNING = "warning"
    ERROR = "error"
    RESULT = "result"


class Stage(Enum):
    """Processing stages in the SubtitleToolkit pipeline."""
    EXTRACT = "extract"
    TRANSLATE = "translate"
    SYNC = "sync"


@dataclass
class Event:
    """
    Represents a single event from the JSONL stream.
    
    Matches the schema defined in WORKFLOW.md:
    {
      "ts": "2025-08-08T07:42:01Z",           # ISO 8601 UTC timestamp
      "stage": "extract|translate|sync",       # Pipeline stage identifier
      "type": "info|progress|warning|error|result",  # Event type
      "msg": "human-readable message",         # User-facing message
      "progress": 0,                          # Integer 0-100 (optional)
      "data": {}                              # Stage-specific payload
    }
    """
    
    timestamp: datetime
    stage: Stage
    event_type: EventType
    message: str
    progress: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_jsonl(cls, json_data: Dict[str, Any]) -> 'Event':
        """Create an Event from parsed JSON data."""
        try:
            # Parse timestamp
            timestamp = datetime.fromisoformat(json_data['ts'].replace('Z', '+00:00'))
            
            # Parse stage
            stage = Stage(json_data['stage'])
            
            # Parse event type
            event_type = EventType(json_data['type'])
            
            # Extract message
            message = json_data['msg']
            
            # Optional fields
            progress = json_data.get('progress')
            data = json_data.get('data')
            
            return cls(
                timestamp=timestamp,
                stage=stage,
                event_type=event_type,
                message=message,
                progress=progress,
                data=data
            )
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f"Invalid JSONL event format: {e}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event back to dictionary format."""
        result = {
            'ts': self.timestamp.isoformat().replace('+00:00', 'Z'),
            'stage': self.stage.value,
            'type': self.event_type.value,
            'msg': self.message,
        }
        
        if self.progress is not None:
            result['progress'] = self.progress
            
        if self.data is not None:
            result['data'] = self.data
            
        return result


@dataclass
class ProcessResult:
    """
    Result of a completed script execution.
    
    Contains summary information and any outputs from the process.
    """
    
    success: bool
    exit_code: int
    stage: Stage
    duration_seconds: float
    
    # Summary information
    files_processed: int = 0
    files_successful: int = 0
    files_failed: int = 0
    
    # Output information
    output_files: List[str] = None
    error_message: Optional[str] = None
    
    # Additional data from result events
    result_data: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.output_files is None:
            self.output_files = []
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        if self.files_processed == 0:
            return 0.0
        return (self.files_successful / self.files_processed) * 100


class ScriptRunnerSignals(QObject):
    """
    Qt signals for communicating script execution events.
    
    These signals are emitted by the ScriptRunner and can be connected
    to UI components for real-time updates.
    """
    
    # Process lifecycle signals
    process_started = Signal(Stage)  # stage
    process_finished = Signal(ProcessResult)  # result
    process_failed = Signal(Stage, str)  # stage, error_message
    
    # Event signals (from JSONL stream)
    info_received = Signal(Stage, str)  # stage, message
    progress_updated = Signal(Stage, int, str)  # stage, percentage, message
    warning_received = Signal(Stage, str)  # stage, message
    error_received = Signal(Stage, str)  # stage, message
    result_received = Signal(Stage, dict)  # stage, result_data
    
    # Raw event signal for debugging/logging
    event_received = Signal(Event)  # raw event
    
    # Stream parsing signals
    stream_data_received = Signal(str)  # raw_line
    parse_error = Signal(str, str)  # raw_line, error_message
    
    # Process management signals
    process_output_received = Signal(str)  # stdout line
    process_error_received = Signal(str)  # stderr line
    process_cancelled = Signal(Stage)  # stage


class EventAggregator:
    """
    Aggregates events for progress tracking and result collection.
    
    This class maintains state about the running process and can provide
    summary information for UI updates.
    """
    
    def __init__(self, stage: Stage):
        self.stage = stage
        self.reset()
    
    def reset(self):
        """Reset all aggregated data."""
        self.events: List[Event] = []
        self.current_progress = 0
        self.last_message = ""
        self.warnings: List[str] = []
        self.errors: List[str] = []
        self.result_data: Optional[Dict[str, Any]] = None
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def add_event(self, event: Event):
        """Add an event to the aggregator."""
        self.events.append(event)
        
        # Track start time from first event
        if self.start_time is None:
            self.start_time = event.timestamp
        
        # Update current state based on event type
        if event.event_type == EventType.PROGRESS:
            if event.progress is not None:
                self.current_progress = event.progress
            self.last_message = event.message
            
        elif event.event_type == EventType.INFO:
            self.last_message = event.message
            
        elif event.event_type == EventType.WARNING:
            self.warnings.append(event.message)
            self.last_message = event.message
            
        elif event.event_type == EventType.ERROR:
            self.errors.append(event.message)
            self.last_message = event.message
            
        elif event.event_type == EventType.RESULT:
            self.result_data = event.data
            self.end_time = event.timestamp
    
    def get_progress_info(self) -> Dict[str, Any]:
        """Get current progress information."""
        return {
            'stage': self.stage.value,
            'progress': self.current_progress,
            'message': self.last_message,
            'warnings_count': len(self.warnings),
            'errors_count': len(self.errors),
            'total_events': len(self.events),
        }
    
    def get_summary(self) -> Dict[str, Any]:
        """Get complete summary of the process."""
        duration = None
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()
        elif self.start_time:
            # Make sure we compare timezone-aware datetimes
            now = datetime.now(timezone.utc)
            duration = (now - self.start_time).total_seconds()
        
        return {
            'stage': self.stage.value,
            'total_events': len(self.events),
            'final_progress': self.current_progress,
            'warnings': self.warnings,
            'errors': self.errors,
            'result_data': self.result_data,
            'duration_seconds': duration,
            'start_time': self.start_time,
            'end_time': self.end_time,
        }
    
    def has_errors(self) -> bool:
        """Check if any errors were recorded."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings were recorded."""
        return len(self.warnings) > 0